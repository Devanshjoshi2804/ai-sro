"""The overview.

Every figure here is derived from rows somebody can open. The runs are the
mined jobs' runs (`workflow_runs`), counted by the outcome each one ended with.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sro.application.analytics.summary import ReadSummary
from sro.application.context import RequestContext
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.candidate import Episode, TaskCandidate
from sro.domain.shared.identifiers import BatchId, CandidateId, DeviceId
from sro.domain.skill.workflow import Step, Workflow
from sro.interface.http.schemas import SummaryModel
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
START = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
WEEK = START - timedelta(days=7)


def _workflow(workflow_id: str, title: str, *systems: str) -> Workflow:
    return Workflow(
        id=workflow_id,
        tenant=f.TENANT.value,
        title=title,
        narrative="",
        systems=list(systems),
        steps=[Step(order=0, says="open it", system=None)],
    )


def _run(
    run_id: str, *, outcome: str = "held", live: bool = True, at: datetime = START
) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant=f.TENANT.value,
        workflow_id="wfl-1",
        device_id="dev-1",
        values={},
        started_by="operator",
        live=live,
        allow_focus=True,
        started_at=at.isoformat(),
        outcome=outcome,
    )


async def _seeded(*, runs: int = 0) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    await uow.workflows.save(_workflow("wfl-1", "Create a supplier", "wms.test"))
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
        await uow.workflow_runs.save(_run(f"run-{index}"))
    return uow


async def test_hours_observed_is_the_span_of_the_work_not_the_number_of_uploads() -> None:
    # An extension that uploads every minute must not look like more work.
    uow = await _seeded()

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.watching.batches == 1
    assert summary.watching.events == 180
    assert summary.watching.hours == 0.5


async def test_the_tasks_noticed_are_the_jobs_the_miner_found() -> None:
    uow = await _seeded()
    await uow.workflows.save(_workflow("wfl-2", "Read the stock on hand", "wms.test", "erp.test"))
    await uow.workflows.retire(f.TENANT, "wfl-2", at=START)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.noticing.tasks == 1
    assert summary.noticing.by_kind == {"Create": 1}
    assert [(line.id, line.title, line.host, line.kind, line.steps) for line in summary.tasks] == [
        ("wfl-1", "Create a supplier", "wms.test", "Create", 1)
    ]


async def test_a_job_mined_before_the_window_is_not_a_task_noticed_in_it() -> None:
    uow = await _seeded()
    await uow.workflows.save(_workflow("wfl-old", "Read an old report", "wms.test"))
    uow.workflows.created_at["wfl-old"] = WEEK - timedelta(days=1)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.noticing.tasks == 1
    assert [line.id for line in summary.tasks] == ["wfl-1"]


async def test_a_job_mined_long_ago_and_re_saved_today_is_not_noticed_today() -> None:
    # A repeat of the job with a new value makes `learn_parameters` save it
    # again. That is using the job, not noticing it.
    uow = await _seeded()
    old = _workflow("wfl-old", "Read an old report", "wms.test")
    await uow.workflows.save(old)
    uow.workflows.created_at["wfl-old"] = WEEK - timedelta(days=14)
    old.parameters = [{"name": "client", "seen_values": ["NEW"]}]
    await uow.workflows.save(old)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert [line.id for line in summary.tasks] == ["wfl-1"]


async def test_the_tasks_listed_are_the_most_recent_ones() -> None:
    uow = FakeUnitOfWork()
    for n in range(12):
        await uow.workflows.save(_workflow(f"wfl-{n}", f"Create thing {n}", "wms.test"))
        uow.workflows.created_at[f"wfl-{n}"] = START + timedelta(hours=n)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.noticing.tasks == 12
    assert [line.id for line in summary.tasks] == [f"wfl-{n}" for n in range(11, 1, -1)]


async def test_a_candidate_from_the_old_miner_is_not_a_task_noticed() -> None:
    uow = FakeUnitOfWork()
    await uow.candidates.add(
        TaskCandidate(
            id=CandidateId("cnd-1"),
            tenant_id=f.TENANT,
            principal_id=f.OPERATOR,
            signature="POST api/suppliers",
            host="wms.test",
            title="Create suppliers on wms.test",
            episodes=(
                Episode(
                    started_at=START,
                    ended_at=START + timedelta(seconds=60),
                    host="wms.test",
                    batch_ids=(BatchId("bat-1"),),
                    gestures=1,
                    calls=1,
                ),
            ),
        )
    )

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.noticing.tasks == 0
    assert summary.tasks == ()


async def test_a_mined_job_s_run_in_the_window_is_done_and_one_before_it_is_not() -> None:
    # The old engine's `runs` table is not where the work is: every run the
    # deployment makes is a mined job's run, and counting only the other table
    # read zero on a day with twelve.
    uow = await _seeded(runs=2)
    await uow.workflow_runs.save(_run("run-old", at=WEEK - timedelta(hours=1)))

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.doing.runs == 2
    assert summary.doing.outcomes == {"held": 2}


async def test_the_runs_are_counted_without_loading_them() -> None:
    uow = await _seeded(runs=3)

    async def _loaded(*_: object, **__: object) -> object:
        raise AssertionError("the summary loaded every run to count them")

    uow.workflow_runs.since = _loaded  # type: ignore[method-assign, assignment]

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.doing.runs == 3


async def test_another_tenant_s_runs_are_not_counted() -> None:
    uow = await _seeded(runs=1)
    theirs = _run("run-theirs")
    theirs.tenant = "other-corp"
    await uow.workflow_runs.save(theirs)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.doing.runs == 1


async def test_runs_are_counted_by_how_they_ended_and_a_dry_run_is_a_rehearsal() -> None:
    uow = await _seeded()
    for run_id, outcome, live in (
        ("run-a", "held", True),
        ("run-b", "held", False),
        ("run-c", "stopped", True),
        ("run-d", "failed", True),
        ("run-e", "running", True),
    ):
        await uow.workflow_runs.save(_run(run_id, outcome=outcome, live=live))

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)

    assert summary.doing.runs == 5
    assert summary.doing.outcomes == {"held": 2, "stopped": 1, "failed": 1, "running": 1}
    assert summary.doing.rehearsed == 1


async def test_the_summary_serialises_to_the_wire_without_crashing() -> None:
    # SummaryModel.of() used to call vars() on frozen, slotted dataclasses,
    # which have no __dict__ -- every request to the endpoint 500ed.
    uow = await _seeded(runs=2)

    summary = await ReadSummary(uow).execute(CTX, since=WEEK)
    model = SummaryModel.of(summary)

    assert model.doing.runs == 2
    assert model.tasks[0].id == "wfl-1"
