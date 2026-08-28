"""Learning a task from evidence already stored, rather than asking again.

The point of the whole passive path: the operator did it on Tuesday, and what
they did is still here.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.observation.teach import DismissCandidate, NothingToTeach, TeachCandidate
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, Episode, TaskCandidate
from sro.domain.recording.recording import RecordingStatus
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, CandidateId, DeviceId, SkillId
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


def _teach(
    uow: FakeUnitOfWork,
    blobs: FakeBlobStore,
    understand: object,
    induce: object | None = None,
    now: datetime | None = None,
) -> TeachCandidate:
    return TeachCandidate(uow, blobs, FakeClock(now), FakeIdFactory(), understand, induce)  # type: ignore[arg-type]


class _Induces:
    """The two-run diff, stood in for. What it proves about parameters is
    tested where it lives; here what matters is that it is what gets used."""

    def __init__(self) -> None:
        self.pairs: list[tuple[str, str | None]] = []
        self.rest: list[tuple[str, ...]] = []

    async def execute(
        self,
        ctx: RequestContext,
        *,
        first: object,
        second: object | None = None,
        name: str | None = None,
        others: Sequence[object] = (),
    ) -> object:
        self.pairs.append((str(first), str(second) if second else None))
        self.rest.append(tuple(str(other) for other in others))

        class _Induced:
            skill_id = SkillId("skl-induced")

        return _Induced()


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


async def test_a_request_timestamp_missing_its_offset_does_not_crash_the_teach() -> None:
    # datetime.fromisoformat parses an offset-less string into a naive
    # datetime; comparing it against the episode's always-aware started_at in
    # _inside() used to raise instead of just excluding the one bad line.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    events = [
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
                "started_at": "2026-03-01T09:00:02",
                "status": 200,
            },
        },
    ]
    payload = b"".join(json.dumps(event).encode() + b"\n" for event in events)
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
            event_count=2,
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
    understand = _NoUnderstanding("the evidence is too thin")

    taught = await _teach(uow, blobs, understand).execute(CTX, candidate_id=candidate.id)

    # The malformed line is dropped, not raised through -- with no request
    # left to name the task by, this ends the same way genuinely thin
    # evidence always does, gracefully, rather than with an unhandled 500.
    assert taught.needs_demonstration is True
    assert taught.recording_id is None


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


async def test_a_dismissed_candidate_cannot_be_taught_out_from_under_the_dismissal() -> None:
    # A stale tab, or a retry, must not silently overrule what was decided.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)
    await DismissCandidate(uow).execute(CTX, candidate_id=candidate.id, reason="not worth it")

    with pytest.raises(NothingToTeach):
        await _teach(uow, blobs, _NoUnderstanding()).execute(CTX, candidate_id=candidate.id)

    assert uow.candidates.rows["cnd-1"].status is CandidateStatus.DISMISSED


async def test_an_already_taught_candidate_cannot_be_taught_again() -> None:
    # Re-teaching would replace skill_id and orphan any trigger pointed at
    # the original skill.
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)
    candidate.taught(SkillId("skl-1"))
    await uow.candidates.save(candidate)

    with pytest.raises(NothingToTeach):
        await _teach(uow, blobs, _NoUnderstanding()).execute(CTX, candidate_id=candidate.id)

    assert uow.candidates.rows["cnd-1"].skill_id == SkillId("skl-1")


async def test_a_taught_candidate_cannot_be_dismissed_out_from_under_the_skill() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)
    candidate.taught(SkillId("skl-1"))
    await uow.candidates.save(candidate)

    with pytest.raises(InvariantViolation):
        await DismissCandidate(uow).execute(CTX, candidate_id=candidate.id, reason="too late")

    assert uow.candidates.rows["cnd-1"].status is CandidateStatus.TAUGHT


async def _again(
    uow: FakeUnitOfWork, blobs: FakeBlobStore, candidate: TaskCandidate, *, days: int
) -> TaskCandidate:
    """The same task, done again some days later."""
    later = START + timedelta(days=days)
    key = f"acme/clerk/2026-03-0{1 + days}/bat-{1 + days}.ndjson"
    payload = b"".join(json.dumps(event).encode() + b"\n" for event in _events_at(later))
    blobs.objects[key] = payload
    await uow.observations.add(
        ObservationBatch(
            id=BatchId(f"bat-{1 + days}"),
            tenant_id=f.TENANT,
            device_id=DeviceId("dev-1"),
            principal_id=f.OPERATOR,
            mode=CaptureMode.PASSIVE,
            started_at=later,
            ended_at=later + timedelta(minutes=1),
            received_at=later,
            uri=f"s3://sro-artifacts/{key}",
            event_count=3,
            byte_count=len(payload),
        )
    )
    candidate.observed(
        Episode(
            started_at=later,
            ended_at=later + timedelta(seconds=10),
            host="wms.acme.test",
            batch_ids=(BatchId(f"bat-{1 + days}"),),
            gestures=1,
            calls=1,
        )
    )
    await uow.candidates.save(candidate)
    return candidate


async def _seen_twice(uow: FakeUnitOfWork, blobs: FakeBlobStore) -> TaskCandidate:
    """The same task, done on Tuesday and again on Wednesday."""
    return await _again(uow, blobs, await _stored(uow, blobs), days=1)


def _events_at(at: datetime) -> list[dict[str, object]]:
    shifted = at - START
    events = []
    for event in _events():
        if event["kind"] == "gesture":
            gesture = dict(event["gesture"])  # type: ignore[arg-type]
            gesture["at"] = float(gesture["at"]) + shifted.total_seconds()
            events.append({"kind": "gesture", "gesture": gesture})
        else:
            request = dict(event["request"])  # type: ignore[arg-type]
            request["started_at"] = (
                datetime.fromisoformat(str(request["started_at"])) + shifted
            ).isoformat()
            events.append({"kind": "request", "request": request})
    return events


async def test_a_task_watched_twice_is_learned_by_diffing_the_two_doings() -> None:
    """Which instrument reads the evidence is the whole difference between a
    skill and a recording of one afternoon.

    Two doings are diffed: what differs between them is a parameter, proved,
    and no model is asked. Seen once, the same creation yields a skill that
    would re-create the record it watched, by name.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _seen_twice(uow, blobs)
    understand = _NoUnderstanding()
    induce = _Induces()

    sealed_after = START + timedelta(days=2)
    taught = await _teach(uow, blobs, understand, induce, now=sealed_after).execute(
        CTX, candidate_id=candidate.id
    )

    assert taught.skill_id == SkillId("skl-induced")
    assert understand.asked == [], "a model was asked to read what two doings could prove"
    assert len(induce.pairs) == 1
    first, second = induce.pairs[0]
    assert second is not None, "the second doing was captured and not used"
    assert first != second, "one recording was diffed against itself"
    assert induce.rest == [()], "a third doing appeared from a candidate seen twice"


async def test_every_doing_is_handed_over_even_though_only_two_are_diffed() -> None:
    """The two freshest are the pair, because the screens move and the freshest
    doing is the one most likely to still find its controls. The rest go too,
    read for one thing: whether some doing left a field empty.

    An operator created the same kind of work area three times and left three
    priorities empty the first time. Built from the two most recent episodes
    alone, nothing induction looked at had ever seen those fields empty, and
    the skill demanded all three.
    """
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _again(uow, blobs, await _seen_twice(uow, blobs), days=2)
    induce = _Induces()

    await _teach(uow, blobs, _NoUnderstanding(), induce, now=START + timedelta(days=4)).execute(
        CTX, candidate_id=candidate.id
    )

    first, second = induce.pairs[0]
    rest = induce.rest[0]
    assert len(rest) == 1, "the oldest doing was built and then dropped on the floor"
    assert first not in rest and second not in rest, "a diffed run was handed over twice"
    # Freshest first, still: the pair is the two most recent, and the oldest is
    # the one read only for what somebody left empty.
    stored = [await uow.recordings.get(f.TENANT, ident) for ident in (first, second, *rest)]  # type: ignore[arg-type]
    watched = [recording.started_at for recording in stored]
    assert watched == sorted(watched, reverse=True), (
        "the oldest doing was diffed and a fresher one read only for emptiness"
    )


async def test_a_task_watched_once_is_read_rather_than_diffed() -> None:
    """Nothing to diff. The narrative is a model reading the evidence, and
    every part of it is marked as read rather than proven -- which is worth
    having, and is not the same thing."""
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored(uow, blobs)
    understand = _NoUnderstanding("the evidence is too thin")
    induce = _Induces()

    taught = await _teach(uow, blobs, understand, induce).execute(CTX, candidate_id=candidate.id)

    assert induce.pairs == [], "one doing was handed to a diff with nothing to diff it against"
    assert len(understand.asked) == 1
    assert taught.needs_demonstration is True
