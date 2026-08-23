"""Learning a task from evidence already stored, rather than asking again.

The point of the whole passive path: the operator did it on Tuesday, and what
they did is still here.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.observation.teach import DismissCandidate, TeachCandidate
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, Episode, TaskCandidate
from sro.domain.recording.recording import RecordingStatus
from sro.domain.shared.identifiers import BatchId, CandidateId, DeviceId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS = "https://wms.acme.test"
START = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
URI = "s3://sro-artifacts/acme/clerk/2026-03-01/bat-1.ndjson"


class _NoUnderstanding:
    """Induction, unavailable. Half of what is under test is what happens when
    the evidence will not turn into a skill."""

    def __init__(self, fails: str = "") -> None:
        self.fails = fails
        self.asked: list[str] = []

    async def execute(
        self, ctx: RequestContext, *, recording_id: object, name: str | None = None
    ) -> object:
        self.asked.append(str(recording_id))
        raise InductionFailed(self.fails or "there is no interpreter to read this")


def _events() -> list[dict[str, object]]:
    return [
        {
            "kind": "gesture",
            "gesture": {
                "kind": "click",
                "at": (START + timedelta(seconds=1)).timestamp(),
                "url": f"{WMS}/suppliers",
                "target": {"tag": "button", "name": "Save", "cssPath": "div > button"},
            },
        },
        {
            "kind": "request",
            "request": {
                "request_id": "r1",
                "method": "POST",
                "url": f"{WMS}/api/suppliers",
                "resource_type": "xhr",
                "started_at": (START + timedelta(seconds=2)).isoformat(),
                "status": 200,
                "request_headers": {"content-type": "application/json"},
            },
        },
        {
            "kind": "gesture",
            "gesture": {
                "kind": "click",
                "at": (START + timedelta(minutes=30)).timestamp(),
                "url": f"{WMS}/somewhere-else",
                "target": {"tag": "a", "cssPath": "a"},
            },
        },
    ]


async def _stored(uow: FakeUnitOfWork, blobs: FakeBlobStore) -> TaskCandidate:
    payload = b"".join(json.dumps(event).encode() + b"\n" for event in _events())
    blobs.objects["acme/clerk/2026-03-01/bat-1.ndjson"] = payload
    await uow.observations.add(
        ObservationBatch(
            id=BatchId("bat-1"),
            tenant_id=f.TENANT,
            device_id=DeviceId("dev-1"),
            principal_id=f.OPERATOR,
            mode=CaptureMode.PASSIVE,
            started_at=START,
            ended_at=START + timedelta(minutes=1),
            received_at=START,
            uri=URI,
            event_count=3,
            byte_count=len(payload),
        )
    )
    candidate = TaskCandidate(
        id=CandidateId("cnd-1"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature="POST api/suppliers",
        host="wms.acme.test",
        title="Create suppliers on wms.acme.test",
        episodes=(
            Episode(
                started_at=START,
                ended_at=START + timedelta(seconds=10),
                host="wms.acme.test",
                batch_ids=(BatchId("bat-1"),),
                gestures=1,
                calls=1,
            ),
        ),
    )
    await uow.candidates.add(candidate)
    return candidate


def _teach(uow: FakeUnitOfWork, blobs: FakeBlobStore, understand: object) -> TeachCandidate:
    return TeachCandidate(uow, blobs, FakeClock(), FakeIdFactory(), understand)  # type: ignore[arg-type]


async def test_the_demonstration_is_made_out_of_what_was_already_watched() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)
    understand = _NoUnderstanding("the evidence is too thin")

    taught = await _teach(uow, blobs, understand).execute(CTX, candidate_id=candidate.id)

    assert taught.recording_id is not None
    recording = await uow.recordings.get(f.TENANT, taught.recording_id)
    assert recording.status is RecordingStatus.SEALED
    # Whose work it was, not who pressed the button.
    assert recording.demonstrator == f.OPERATOR
    assert len(recording.frames) == 1
    assert recording.frames[0].requests[0].method == "POST"


async def test_events_outside_the_episode_are_not_part_of_the_demonstration() -> None:
    # The click half an hour later belongs to whatever they did next.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)

    taught = await _teach(uow, blobs, _NoUnderstanding()).execute(CTX, candidate_id=candidate.id)

    assert taught.recording_id is not None
    recording = await uow.recordings.get(f.TENANT, taught.recording_id)
    assert len(recording.frames) == 1


async def test_evidence_that_will_not_induce_asks_for_one_deliberate_repetition() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)

    taught = await _teach(uow, blobs, _NoUnderstanding()).execute(CTX, candidate_id=candidate.id)

    assert taught.needs_demonstration is True
    assert taught.skill_id is None
    # The recording is kept: it is evidence either way, and the repetition will
    # be diffed against it.
    assert taught.recording_id is not None
    assert uow.candidates.rows["cnd-1"].status is CandidateStatus.NEW


async def test_evidence_that_has_aged_out_says_so_rather_than_sealing_nothing() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)
    blobs.objects.clear()

    taught = await _teach(uow, blobs, _NoUnderstanding()).execute(CTX, candidate_id=candidate.id)

    assert taught.needs_demonstration is True
    assert taught.recording_id is None
    assert "aged out" in (taught.because or "")


async def test_a_dismissal_is_kept_so_it_is_not_offered_again_next_week() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)

    dismissed = await DismissCandidate(uow).execute(
        CTX, candidate_id=candidate.id, reason="it is two clicks, not worth it"
    )

    assert dismissed.status is CandidateStatus.DISMISSED
    assert dismissed.worth_offering is False
    assert "cnd-1" in uow.candidates.rows
