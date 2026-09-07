"""Runs of a mined workflow on Postgres: their steps, and the approvals on them.

The rules here are the rig's -- ``rig/runs.py`` plus the approval insert and
the awaiting query in ``rig/api.py`` -- and they were SQLite there. What had to
be translated rather than copied is marked where it happens:

* ``INSERT OR REPLACE`` on a run and ``INSERT OR IGNORE`` on an approval become
  ``ON CONFLICT DO UPDATE`` and ``ON CONFLICT DO NOTHING`` on a named conflict
  target. SQLite's forms swallow *every* constraint; naming the target means a
  different constraint failing is still an error rather than a silent no-op.
  On the approval it also buys the answer: ``RETURNING`` says whether this tap
  was the one that authorised the step, where SQLite gave a rowcount.
* The rig kept every clock as text. ``started_at`` and ``finished_at`` are
  ``timestamptz`` here because both indexes order on ``started_at`` and an
  offset-less string sorts beside an offset-bearing one with neither wrong. The
  records still carry ISO strings, so this converts on both edges.
* ``fail_orphans`` sweeps every tenant, which is not an oversight: it runs once
  at startup with nobody making the request, and a run left ``running`` in one
  tenant goes on 409-ing its browser however healthy the others are.

The row-to-record mapping lives here rather than in ``mappers.py``: a
repository's mapping belongs with the repository, and these three shapes are
read by nothing else.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import WorkflowRunRepository
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.db.models import ApprovalRow, WorkflowRunRow, WorkflowRunStepRow


def _when(moment: str) -> datetime:
    """An ISO instant as a real timestamp, in UTC when it said nothing.

    Every writer in the rig produces UTC; a naive one that slipped through is
    read as UTC rather than as the server's local time, because a naive local
    instant beside the UTC ones reads as a run that finished hours before it
    started.
    """
    parsed = datetime.fromisoformat(moment)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _run_values(run: WorkflowRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "tenant_id": run.tenant,
        "workflow_id": run.workflow_id,
        "device_id": run.device_id,
        "values": dict(run.values),
        "started_by": run.started_by,
        "live": run.live,
        "allow_focus": run.allow_focus,
        "started_at": _when(run.started_at),
        "finished_at": None if run.finished_at is None else _when(run.finished_at),
        "outcome": run.outcome,
        "withheld": list(run.withheld),
        "in_tokens": run.in_tokens,
        "out_tokens": run.out_tokens,
        "thought_tokens": run.thought_tokens,
        "cost_usd": run.cost_usd,
        "unpriced": run.unpriced,
    }


def _step_values(run_id: str, step: RunStep) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "ord": step.order,
        "says": step.says,
        "planned_by": step.planned_by,
        "sent": step.sent,
        "result": step.result,
        "verdict": step.verdict,
        "verdict_by": step.verdict_by,
        "reason": step.reason,
        "matched_by": step.matched_by,
        "stale": step.stale,
        "before_url": step.before_url,
        "after_url": step.after_url,
        "in_tokens": step.in_tokens,
        "out_tokens": step.out_tokens,
        "thought_tokens": step.thought_tokens,
        "cost_usd": step.cost_usd,
        "unpriced": step.unpriced,
    }


def _row_to_step(row: WorkflowRunStepRow) -> RunStep:
    return RunStep(
        order=row.ord,
        says=row.says,
        verdict=row.verdict,
        verdict_by=row.verdict_by,
        reason=row.reason,
        planned_by=row.planned_by,
        sent=row.sent,
        result=row.result,
        matched_by=row.matched_by,
        stale=row.stale,
        before_url=row.before_url,
        after_url=row.after_url,
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
    )


def _row_to_run(row: WorkflowRunRow, steps: list[RunStep]) -> WorkflowRun:
    return WorkflowRun(
        id=row.id,
        tenant=row.tenant_id,
        workflow_id=row.workflow_id,
        device_id=row.device_id,
        values=dict(row.values_),
        started_by=row.started_by,
        live=row.live,
        allow_focus=row.allow_focus,
        started_at=row.started_at.isoformat(),
        finished_at=None if row.finished_at is None else row.finished_at.isoformat(),
        outcome=row.outcome,
        steps=steps,
        withheld=list(row.withheld),
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
    )


class SqlWorkflowRunRepository(WorkflowRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: WorkflowRun) -> None:
        statement = pg_insert(WorkflowRunRow).values(**_run_values(run))
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["id"],
                # Every column but the key takes the new value, which is what
                # INSERT OR REPLACE did: a run is written whole after every
                # step, so the later write supersedes the earlier one.
                set_={
                    column.name: statement.excluded[column.name]
                    for column in WorkflowRunRow.__table__.columns
                    if column.name != "id"
                },
            )
        )
        # Deleted and reinserted rather than upserted one by one. A step
        # removed from the record has to leave the store with it, and an
        # upsert would leave it behind -- and this is the rule the second save
        # of a run depends on to not double its first step.
        await self._session.execute(
            delete(WorkflowRunStepRow).where(WorkflowRunStepRow.run_id == run.id)
        )
        if run.steps:
            await self._session.execute(
                pg_insert(WorkflowRunStepRow).values(
                    [_step_values(run.id, step) for step in run.steps]
                )
            )

    async def get(self, tenant_id: TenantId, run_id: str) -> WorkflowRun | None:
        query = self._rows().where(
            WorkflowRunRow.tenant_id == tenant_id.value, WorkflowRunRow.id == run_id
        )
        rows = (await self._session.execute(query)).scalars().all()
        found = await self._with_steps(rows)
        return found[0] if found else None

    async def for_workflow(self, tenant_id: TenantId, workflow_id: str) -> tuple[WorkflowRun, ...]:
        query = self._rows().where(
            WorkflowRunRow.tenant_id == tenant_id.value,
            WorkflowRunRow.workflow_id == workflow_id,
        )
        rows = (await self._session.execute(query.order_by(WorkflowRunRow.started_at))).scalars()
        return await self._with_steps(rows.all())

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        # ponytail: a read the caller acts on, not a lock -- sound while one
        # worker owns every run, as the rig required. A second worker needs a
        # UNIQUE partial index on (tenant_id, device_id) WHERE outcome =
        # 'running'.
        busy: str | None = await self._session.scalar(
            select(WorkflowRunRow.id)
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.device_id == device_id.value,
                WorkflowRunRow.outcome == "running",
            )
            .order_by(WorkflowRunRow.started_at)
            .limit(1)
        )
        return busy

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]:
        query = (
            select(WorkflowRunStepRow.run_id, WorkflowRunStepRow.ord, WorkflowRunStepRow.says)
            .join(WorkflowRunRow, WorkflowRunRow.id == WorkflowRunStepRow.run_id)
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                # Only a run still in flight. The rig gated this list on the
                # runner's in-process `Approvals.waiting()` set, which is plan
                # 3's half; the storage half is this predicate, and without it
                # a step left `awaiting` on a run that was aborted or failed
                # sits in the supervisor's queue forever, asking for a tap that
                # can no longer let anything out.
                WorkflowRunRow.outcome == "running",
                WorkflowRunStepRow.verdict == "awaiting",
            )
            # Oldest wait first: this is the queue a supervisor works down, and
            # the run that has been parked longest is the one holding up a job.
            .order_by(WorkflowRunRow.started_at, WorkflowRunStepRow.ord)
        )
        rows = (await self._session.execute(query)).all()
        return tuple((run_id, ord_, says) for run_id, ord_, says in rows)

    async def approve(self, run_id: str, ord_: int, *, at: str, device_id: str | None) -> bool:
        # DO NOTHING, the rig's OR IGNORE: a write rescued to the second rung
        # parks at the same step and takes a second tap, and the first
        # authorisation stands -- with the first approver's browser on it.
        # RETURNING rather than a rowcount, because whether this tap was the
        # one that authorised the step is the answer the caller wants.
        tapped = await self._session.execute(
            pg_insert(ApprovalRow)
            .values(run_id=run_id, ord=ord_, at=_when(at), device_id=device_id)
            .on_conflict_do_nothing(index_elements=["run_id", "ord"])
            .returning(ApprovalRow.run_id)
        )
        return tapped.first() is not None

    async def approvals(self, run_id: str) -> tuple[tuple[int, str, str | None], ...]:
        query = (
            select(ApprovalRow.ord, ApprovalRow.at, ApprovalRow.device_id)
            .where(ApprovalRow.run_id == run_id)
            .order_by(ApprovalRow.ord)
        )
        rows = (await self._session.execute(query)).all()
        return tuple((ord_, at.isoformat(), device_id) for ord_, at, device_id in rows)

    async def fail_orphans(self, reason: str) -> int:
        now = datetime.now(tz=UTC).isoformat()
        query = self._rows().where(WorkflowRunRow.outcome == "running")
        rows = (await self._session.execute(query.order_by(WorkflowRunRow.started_at))).scalars()
        orphans = await self._with_steps(rows.all())
        for run in orphans:
            if run.steps:
                last = run.steps[-1]
                last.verdict, last.verdict_by, last.reason = "failed", "none", reason
            else:
                # The reason has to land somewhere the panel shows it, and a
                # run that died before its first step has nowhere.
                run.steps.append(
                    RunStep(order=0, says="", verdict="failed", verdict_by="none", reason=reason)
                )
            run.outcome = "failed"
            run.finished_at = now
            await self.save(run)
        return len(orphans)

    @staticmethod
    def _rows() -> Select[tuple[WorkflowRunRow]]:
        # ``save`` upserts with a Core statement, so a row this session had
        # already loaded would otherwise come back at its pre-save state.
        return select(WorkflowRunRow).execution_options(populate_existing=True)

    async def _with_steps(self, rows: Sequence[WorkflowRunRow]) -> tuple[WorkflowRun, ...]:
        """One query for every run's steps rather than one per run."""
        if not rows:
            return ()
        query = (
            select(WorkflowRunStepRow)
            .where(WorkflowRunStepRow.run_id.in_([row.id for row in rows]))
            .order_by(WorkflowRunStepRow.run_id, WorkflowRunStepRow.ord)
            .execution_options(populate_existing=True)
        )
        steps: defaultdict[str, list[RunStep]] = defaultdict(list)
        for step in (await self._session.execute(query)).scalars().all():
            steps[step.run_id].append(_row_to_step(step))
        return tuple(_row_to_run(row, steps[row.id]) for row in rows)
