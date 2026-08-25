"""Two candidates a person has said are one job, taught as one skill.

An episode breaks on a host change, so "check the WMS, then record it in the
ERP" is two candidates and always will be. The miner already notices they go
together, a model already says why, and a person already answers. This is the
half that acts on the answer.

What the tests defend is which evidence becomes which demonstration: two
*occurrences* of the whole job are the pair induction diffs, and the two halves
are never diffed against each other -- that would compare a WMS call with an ERP
call and call the difference a parameter.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.observation.teach import NothingToTeach, TeachWorkflow
from sro.application.ports.interpretation import TaskName
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.candidate import (
    CandidateStatus,
    Episode,
    Join,
    JoinAnswer,
    JoinKind,
    TaskCandidate,
)
from sro.domain.shared.identifiers import BatchId, CandidateId, DeviceId, RecordingId, SkillId
from tests import factories as f
from tests.unit.fakes import FakeBlobStore, FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
WMS, ERP = "https://wms.acme.test", "https://erp.acme.test"
NINE = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)


class _Induction:
    """Stands in for the two-run diff. Writes down what it was handed, because
    which two recordings arrive here is the whole question."""

    def __init__(self, *, fails: str = "") -> None:
        self.fails = fails
        self.asked: list[tuple[RecordingId, RecordingId | None, str | None]] = []

    async def execute(
        self,
        ctx: RequestContext,
        *,
        first: RecordingId,
        second: RecordingId | None = None,
        name: str | None = None,
    ) -> object:
        self.asked.append((first, second, name))
        if self.fails:
            raise InductionFailed(self.fails)
        return type("Induced", (), {"skill_id": SkillId("skl-merged")})()


class _Namer:
    def __init__(self, title: str = "Receive a short shipment end to end") -> None:
        self._title = title
        self.asked: list[str] = []

    @property
    def available(self) -> bool:
        return True

    async def read(self, evidence: str) -> object:
        raise AssertionError("naming a merged task must not read a demonstration")

    async def name_task(self, evidence: str) -> TaskName:
        self.asked.append(evidence)
        return TaskName(title=self._title)

    async def judge_join(self, kind: str, first: str, second: str) -> object:
        raise AssertionError("not asked here")


def _half(host: str, at: datetime, path: str) -> list[dict[str, object]]:
    """One click and the write it caused, on one system."""
    return [
        {
            "kind": "gesture",
            "gesture": {
                "kind": "click",
                "at": (at + timedelta(seconds=1)).timestamp(),
                "url": f"{host}/screen",
                "target": {"tag": "button", "name": "Save", "cssPath": "div > button"},
            },
        },
        {
            "kind": "request",
            "request": {
                "request_id": f"{host}-{at.isoformat()}",
                "method": "POST",
                "url": f"{host}{path}",
                "resource_type": "xhr",
                "started_at": (at + timedelta(seconds=2)).isoformat(),
                "status": 200,
                "request_headers": {"content-type": "application/json"},
            },
        },
    ]


def _episode(host: str, at: datetime, batch: str) -> Episode:
    return Episode(
        started_at=at,
        ended_at=at + timedelta(minutes=1),
        host=host,
        batch_ids=(BatchId(batch),),
        gestures=1,
        calls=1,
    )


async def _batch(
    uow: FakeUnitOfWork, blobs: FakeBlobStore, batch_id: str, lines: list[dict[str, object]]
) -> None:
    payload = b"".join(json.dumps(line).encode() + b"\n" for line in lines)
    blobs.objects[f"{batch_id}.ndjson"] = payload
    await uow.observations.add(
        ObservationBatch(
            id=BatchId(batch_id),
            tenant_id=f.TENANT,
            device_id=DeviceId("dev-1"),
            principal_id=f.OPERATOR,
            mode=CaptureMode.PASSIVE,
            started_at=NINE,
            ended_at=NINE + timedelta(days=8),
            received_at=NINE,
            uri=f"s3://sro-artifacts/{batch_id}.ndjson",
            event_count=len(lines),
            byte_count=len(payload),
        )
    )


async def _world(
    uow: FakeUnitOfWork, blobs: FakeBlobStore, *, apart: timedelta = timedelta(minutes=2)
) -> tuple[TaskCandidate, TaskCandidate]:
    """Two systems, done one after the other, twice -- a week apart."""
    firsts = (NINE, NINE + timedelta(days=7))
    events: dict[str, list[dict[str, object]]] = {}
    for index, start in enumerate(firsts):
        events[f"bat-wms-{index}"] = _half(WMS, start, "/api/waves/close")
        events[f"bat-erp-{index}"] = _half(
            ERP, start + timedelta(minutes=1) + apart, "/api/receipts"
        )

    for batch_id, lines in events.items():
        payload = b"".join(json.dumps(line).encode() + b"\n" for line in lines)
        blobs.objects[f"{batch_id}.ndjson"] = payload
        await uow.observations.add(
            ObservationBatch(
                id=BatchId(batch_id),
                tenant_id=f.TENANT,
                device_id=DeviceId("dev-1"),
                principal_id=f.OPERATOR,
                mode=CaptureMode.PASSIVE,
                started_at=NINE,
                ended_at=NINE + timedelta(days=8),
                received_at=NINE,
                uri=f"s3://sro-artifacts/{batch_id}.ndjson",
                event_count=len(lines),
                byte_count=len(payload),
            )
        )

    wms = TaskCandidate(
        id=CandidateId("cnd-wms"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature="POST api/waves/close",
        host="wms.acme.test",
        title="Close waves on wms.acme.test",
        episodes=tuple(
            _episode("wms.acme.test", start, f"bat-wms-{index}")
            for index, start in enumerate(firsts)
        ),
    )
    erp = TaskCandidate(
        id=CandidateId("cnd-erp"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature="POST api/receipts",
        host="erp.acme.test",
        title="Create receipts on erp.acme.test",
        episodes=tuple(
            _episode("erp.acme.test", start + timedelta(minutes=1) + apart, f"bat-erp-{index}")
            for index, start in enumerate(firsts)
        ),
    )
    await uow.candidates.add(wms)
    await uow.candidates.add(erp)
    return wms, erp


def _teach(
    uow: FakeUnitOfWork, blobs: FakeBlobStore, induce: _Induction, namer: _Namer | None = None
) -> TeachWorkflow:
    return TeachWorkflow(
        uow, blobs, FakeClock(datetime(2026, 4, 1, tzinfo=UTC)), FakeIdFactory(), induce, namer
    )  # type: ignore[arg-type]


async def test_each_time_the_operator_did_both_halves_becomes_one_demonstration() -> None:
    uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
    wms, erp = await _world(uow, blobs)

    taught = await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)

    # Two occurrences, two recordings -- and they are what induction was given
    # to diff, rather than one candidate against the other.
    assert len(taught.recording_ids) == 2
    first, second, _ = induce.asked[0]
    assert (first, second) == taught.recording_ids

    async with uow:
        recordings = [await uow.recordings.get(f.TENANT, ident) for ident in taught.recording_ids]
    for recording in recordings:
        hosts = {
            request.url.split("/api/")[0]
            for frame in recording.frames
            for request in frame.requests
        }
        assert hosts == {WMS, ERP}, "a demonstration of this job is both halves"
    # Identical keys, which is the only reason the pair can induce at all. The
    # candidate's own host would have named whichever half came first.
    assert recordings[0].objective_key == recordings[1].objective_key

    # Freshest first: the screens move.
    assert recordings[0].started_at > recordings[1].started_at


async def test_both_candidates_are_spent_on_the_one_skill() -> None:
    uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
    wms, erp = await _world(uow, blobs)

    taught = await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)

    assert taught.skill_id == SkillId("skl-merged")
    async with uow:
        for ident in (wms.id, erp.id):
            candidate = await uow.candidates.get(f.TENANT, ident)
            assert candidate.status is CandidateStatus.TAUGHT
            assert candidate.skill_id == SkillId("skl-merged")


async def test_the_merged_skill_is_named_from_both_halves() -> None:
    uow, blobs, induce, namer = FakeUnitOfWork(), FakeBlobStore(), _Induction(), _Namer()
    wms, erp = await _world(uow, blobs)

    await _teach(uow, blobs, induce, namer).execute(CTX, first_id=wms.id, second_id=erp.id)

    assert "wms.acme.test" in namer.asked[0] and "erp.acme.test" in namer.asked[0]
    assert induce.asked[0][2] == "Receive a short shipment end to end"


async def test_without_a_model_the_two_titles_stand() -> None:
    uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
    wms, erp = await _world(uow, blobs)

    await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)

    assert (
        induce.asked[0][2]
        == "Close waves on wms.acme.test and then Create receipts on erp.acme.test"
    )


async def test_a_candidate_already_taught_is_refused_by_the_skill_it_became() -> None:
    uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
    wms, erp = await _world(uow, blobs)
    async with uow:
        stale = await uow.candidates.get(f.TENANT, erp.id)
        stale.taught(SkillId("skl-earlier"))
        await uow.candidates.save(stale)
        await uow.commit()

    with pytest.raises(NothingToTeach, match="skl-earlier"):
        await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)

    assert induce.asked == [], "a refusal must not cost an induction"


async def test_a_pair_somebody_said_was_different_is_not_merged_anyway() -> None:
    uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
    wms, erp = await _world(uow, blobs)
    async with uow:
        candidate = await uow.candidates.get(f.TENANT, wms.id)
        candidate.joins = (
            Join(
                other_id=erp.id,
                kind=JoinKind.WORKFLOW,
                because="both touch a shipment",
                answered=JoinAnswer.DIFFERENT,
                answered_by=f.OPERATOR,
            ),
        )
        await uow.candidates.save(candidate)
        await uow.commit()

    with pytest.raises(NothingToTeach, match="different"):
        await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)


async def test_halves_done_hours_apart_are_not_one_job() -> None:
    uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
    wms, erp = await _world(uow, blobs, apart=timedelta(hours=3))

    taught = await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)

    assert taught.needs_demonstration
    assert induce.asked == []


async def test_evidence_that_will_not_induce_asks_for_one_deliberate_repetition() -> None:
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    induce = _Induction(fails="the two runs do not agree on what the task is")
    wms, erp = await _world(uow, blobs)

    taught = await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)

    assert taught.needs_demonstration
    assert taught.because == "the two runs do not agree on what the task is"
    # Kept: it is the evidence the deliberate repetition gets diffed against.
    assert len(taught.recording_ids) == 2
    async with uow:
        for ident in (wms.id, erp.id):
            candidate = await uow.candidates.get(f.TENANT, ident)
            assert candidate.status is CandidateStatus.NEW


async def test_which_half_was_clicked_on_does_not_change_what_the_job_is() -> None:
    """The key comes off the frames, never off a candidate.

    `TeachCandidate` names the system from `candidate.host`, which for a pair
    would name whichever half the person happened to open -- so the same job
    taught from the WMS side and from the ERP side would be two skills that can
    never pair, and the second teach would induce a duplicate.
    """
    keys = []
    for order in (("cnd-wms", "cnd-erp"), ("cnd-erp", "cnd-wms")):
        uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
        await _world(uow, blobs)
        taught = await _teach(uow, blobs, induce).execute(
            CTX, first_id=CandidateId(order[0]), second_id=CandidateId(order[1])
        )
        async with uow:
            keys.append((await uow.recordings.get(f.TENANT, taught.recording_ids[0])).objective_key)

    assert keys[0] == keys[1]


async def test_one_doing_of_a_half_cannot_be_two_demonstrations() -> None:
    """Adjacency pairs episodes; it does not partition them.

    The operator closed the waves once and wrote two receipts against it. Both
    receipts are adjacent to the same closing, so both pairs are occurrences of
    it -- and taking both would hand induction two recordings whose WMS half is
    the same bytes twice. Every value the operator typed there would then be
    proved constant by evidence that never varied because it never repeated.
    """
    uow, blobs, induce = FakeUnitOfWork(), FakeBlobStore(), _Induction()
    wms, erp = await _world(uow, blobs)

    # A second receipt four minutes after the closing, with evidence of its own
    # -- so what stops it being a second demonstration is the rule, not thin
    # evidence.
    again = NINE + timedelta(minutes=4)
    await _batch(uow, blobs, "bat-erp-again", _half(ERP, again, "/api/receipts"))
    async with uow:
        closing = await uow.candidates.get(f.TENANT, wms.id)
        closing.episodes = (closing.episodes[0],)  # one doing of the first half
        await uow.candidates.save(closing)
        receipts = await uow.candidates.get(f.TENANT, erp.id)
        receipts.episodes = (
            receipts.episodes[0],
            _episode("erp.acme.test", again, "bat-erp-again"),
        )
        await uow.candidates.save(receipts)
        await uow.commit()

    taught = await _teach(uow, blobs, induce).execute(CTX, first_id=wms.id, second_id=erp.id)

    assert len(taught.recording_ids) == 1
    # Which is the honest outcome: one occurrence induces as a single
    # demonstration, values and all, exactly as teaching one candidate does.
    assert induce.asked[0][1] is None
