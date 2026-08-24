"""The overview, and the one number on it that is an estimate.

Every figure here is derived from rows somebody can open, and the run outcomes
are judged with the same function that judged them at finish -- so a screen and
the promotion ladder never say different words about the same afternoon.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.application.analytics.summary import ReadSummary
from sro.application.context import RequestContext
from sro.domain.execution.run import (
    Medium,
    Run,
    RunId,
    RunStatus,
    StepDisposition,
    StepOutcome,
)
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.candidate import Episode, TaskCandidate
from sro.domain.shared.identifiers import BatchId, CandidateId, DeviceId, SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.interface.http.schemas import SummaryModel
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
START = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
WEEK = START - timedelta(days=7)
TAUGHT = SkillId("skill-1")


def _candidate(*, taught: bool, seconds: int = 120) -> TaskCandidate:
    candidate = TaskCandidate(
        id=CandidateId("cnd-1"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature="POST api/suppliers",
        host="wms.test",
        title="Create suppliers on wms.test",
        episodes=tuple(
            Episode(
                started_at=START + timedelta(hours=hour),
                ended_at=START + timedelta(hours=hour, seconds=seconds),
                host="wms.test",
                batch_ids=(BatchId("bat-1"),),
                gestures=3,
                calls=2,
            )
            for hour in range(3)
        ),
    )
    if taught:
        candidate.taught(TAUGHT)
    return candidate


def _run(*, status: RunStatus, performed: bool = True) -> Run:
    run = Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=TAUGHT,
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=START,
        authorized_by=f.OPERATOR,
    )
    run.record(
        StepOutcome(
            index=0,
            medium=Medium.NETWORK,
            disposition=StepDisposition.PERFORMED if performed else StepDisposition.WITHHELD,
            intent="create it",
            idempotency_key="run-1:0",
        )
    )
    run.status = status
    run.ended_at = START + timedelta(seconds=8)
    return run


async def _seeded(*, taught: bool = True, runs: int = 0) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    await uow.candidates.add(_candidate(taught=taught))
    await uow.observations.add(
        ObservationBatch(
            id=BatchId("bat-1"),
            tenant_id=f.TENANT,
            device_id=DeviceId("dev-1"),
            principal_id=f.OPERATOR,
            mode=CaptureMode.PASSIVE,
            started_at=START,
            ended_at=START + timedelta(minutes=30),
            received_at=START,
            uri="s3://sro-artifacts/acme/a/b.ndjson",
            event_count=180,
            byte_count=4096,
        )
    )
    for index in range(runs):
        run = _run(status=RunStatus.SUCCEEDED)
        run.id = RunId(f"run-{index}")
        await uow.runs.add(run)
    return uow


async def test_hours_observed_is_the_span_of_the_work_not_the_number_of_uploads() -> None:
    # An extension that uploads every minute must not look like more work.
    uow = await _seeded()

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.watching.batches == 1
    assert summary.watching.events == 180
    assert summary.watching.hours == 0.5


async def test_a_task_is_counted_by_what_its_calls_do() -> None:
    uow = await _seeded()

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.noticing.tasks == 1
    assert summary.noticing.taught == 1
    assert summary.noticing.by_kind == {"Create": 1}


async def test_time_saved_is_what_the_person_used_to_spend_times_what_ran() -> None:
    uow = await _seeded(runs=4)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    # Two minutes by hand, four runs.
    assert summary.doing.runs == 4
    assert summary.doing.clean == 4
    assert summary.doing.minutes_saved == 8.0
    assert summary.tasks[0].runs == 4


async def test_a_rehearsal_saved_nobody_anything() -> None:
    # A withheld run produced the request and sent nothing. Counting it would
    # make a skill that has never written look like its best week.
    uow = await _seeded()
    rehearsal = _run(status=RunStatus.SUCCEEDED, performed=False)
    await uow.runs.add(rehearsal)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.doing.withheld == 1
    assert summary.doing.minutes_saved == 0.0


async def test_a_failed_run_saved_nobody_anything_either() -> None:
    uow = await _seeded()
    await uow.runs.add(_run(status=RunStatus.FAILED))

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.doing.failed == 1
    assert summary.doing.minutes_saved == 0.0


async def test_a_task_nobody_taught_shows_what_it_is_still_costing() -> None:
    uow = await _seeded(taught=False)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    line = summary.tasks[0]
    assert line.status == "new"
    assert line.times_seen == 3
    assert line.minutes_spent == 6.0
    assert line.minutes_saved == 0.0


async def test_a_candidate_last_seen_before_the_window_is_not_counted() -> None:
    # list_for_tenant has no window of its own; the summary has to apply one,
    # or the day-range control on the screen changes nothing it looks like it
    # should change.
    uow = FakeUnitOfWork()
    stale_time = WEEK - timedelta(days=1)
    await uow.candidates.add(
        TaskCandidate(
            id=CandidateId("cnd-stale"),
            tenant_id=f.TENANT,
            principal_id=f.OPERATOR,
            signature="GET api/old",
            host="wms.test",
            title="Read old on wms.test",
            episodes=(
                Episode(
                    started_at=stale_time,
                    ended_at=stale_time + timedelta(seconds=60),
                    host="wms.test",
                    batch_ids=(BatchId("bat-old"),),
                    gestures=1,
                    calls=1,
                ),
            ),
        )
    )

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.noticing.tasks == 0
    assert summary.tasks == ()


async def test_the_summary_serialises_to_the_wire_without_crashing() -> None:
    # SummaryModel.of() used to call vars() on frozen, slotted dataclasses,
    # which have no __dict__ -- every request to the endpoint 500ed.
    uow = await _seeded(runs=2)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)
    model = SummaryModel.of(summary)

    assert model.doing.runs == 2
    assert model.tasks[0].runs == 2
