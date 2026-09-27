from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import Select, and_, case, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import WorkflowRunRepository
from sro.domain.execution.workflow_run import (
    ENDED,
    Executor,
    RunStep,
    WorkflowRun,
    already_running,
)
from sro.domain.observation.driving import Driving
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.db.codec import when
from sro.infrastructure.db.models import ApprovalRow, WorkflowRunRow, WorkflowRunStepRow
from sro.infrastructure.db.workflows import workflow_from_json, workflow_json


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
        "started_at": when(run.started_at),
        "finished_at": None if run.finished_at is None else when(run.finished_at),
        "outcome": run.outcome,
        "from_step": run.from_step,
        "items": [dict(item) for item in run.items],
        "withheld": list(run.withheld),
        "in_tokens": run.in_tokens,
        "out_tokens": run.out_tokens,
        "thought_tokens": run.thought_tokens,
        "cost_usd": run.cost_usd,
        "wrong_because": run.wrong_because,
        "watched": run.watched,
        "doing": run.doing,
        "gathered": {k: dict(v) for k, v in run.gathered.items()},
        "needs": list(run.needs),
        "unasked": list(run.unasked),
        "awaiting": dict(run.awaiting) if run.awaiting else None,
        "asked_the_asker": run.asked_the_asker,
        "undoes_run": run.undoes_run,
        "unpriced": run.unpriced,
        "progress": dict(run.progress),
        "executor": run.executor,
        "offer": run.offer,
        "pinned": None if run.pinned is None else workflow_json(run.pinned),
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
        "notes": list(step.notes),
        "unpriced": step.unpriced,
        "of_step": step.of_step,
        "item": step.item,
        "made": dict(step.made),
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
        notes=[note for note in (row.notes or []) if isinstance(note, str)],
        of_step=row.of_step,
        item=row.item,
        made=dict(row.made or {}),
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
        wrong_because=row.wrong_because,
        watched=bool(row.watched),
        doing=row.doing or "",
        gathered={
            str(k): {str(a): str(b) for a, b in v.items()}
            for k, v in (row.gathered or {}).items()
            if isinstance(v, dict)
        },
        needs=[str(one) for one in (row.needs or [])],
        unasked=[str(one) for one in (row.unasked or [])],
        asked_the_asker=bool(row.asked_the_asker),
        undoes_run=row.undoes_run,
        awaiting=(
            {str(key): str(value) for key, value in row.awaiting.items()}
            if isinstance(row.awaiting, dict)
            else None
        ),
        from_step=row.from_step,
        items=[dict(item) for item in (row.items or [])],
        steps=steps,
        withheld=list(row.withheld),
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
        progress=dict(row.progress or {}),
        executor=cast(Executor, row.executor),
        offer=row.offer,
        pinned=None if row.pinned is None else workflow_from_json(row.pinned),
    )


_ONE_RUNNING = "uq_workflow_runs_one_running_per_device"

_ONE_PER_OFFER = "uq_workflow_runs_one_per_offer"


class SqlWorkflowRunRepository(WorkflowRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: WorkflowRun) -> None:
        statement = pg_insert(WorkflowRunRow).values(**_run_values(run))
        ended = WorkflowRunRow.outcome.in_(ENDED)
        kept = {
            "outcome": case((ended, WorkflowRunRow.outcome), else_=statement.excluded.outcome),
            "finished_at": case(
                (ended, func.coalesce(WorkflowRunRow.finished_at, statement.excluded.finished_at)),
                else_=statement.excluded.finished_at,
            ),
        }
        try:
            await self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        column.name: kept.get(column.name, statement.excluded[column.name])
                        for column in WorkflowRunRow.__table__.columns
                        if column.name not in ("id", "progress", "pinned")
                    },
                )
            )
        except IntegrityError as clash:
            if _ONE_PER_OFFER in str(getattr(clash, "orig", clash)):
                await self._session.rollback()
                raise Conflict(f"the offer {run.offer} has already started a run") from clash
            if _ONE_RUNNING not in str(getattr(clash, "orig", clash)):
                raise
            await self._session.rollback()
            busy = await self.in_flight(TenantId(run.tenant), DeviceId(run.device_id))
            raise Conflict(already_running(run.device_id, busy)) from clash
        if run.steps:
            step_statement = pg_insert(WorkflowRunStepRow).values(
                [_step_values(run.id, step) for step in run.steps]
            )
            await self._session.execute(
                step_statement.on_conflict_do_update(
                    index_elements=["run_id", "ord"],
                    set_={
                        column.name: step_statement.excluded[column.name]
                        for column in WorkflowRunStepRow.__table__.columns
                        if column.name not in ("run_id", "ord")
                    },
                )
            )

    async def record_progress(
        self,
        tenant_id: TenantId,
        run_id: str,
        progress: dict[str, object],
        *,
        was: Mapping[str, object] | None = None,
    ) -> bool:
        query = update(WorkflowRunRow).where(
            WorkflowRunRow.id == run_id, WorkflowRunRow.tenant_id == tenant_id.value
        )
        if was is not None:
            query = query.where(WorkflowRunRow.progress == dict(was))
        result = await self._session.execute(
            query.values(progress=dict(progress)).returning(WorkflowRunRow.id)
        )
        return result.first() is not None

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
        rows = (
            await self._session.execute(
                query.order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            )
        ).scalars()
        return await self._with_steps(rows.all())

    async def recent(
        self,
        tenant_id: TenantId,
        *,
        limit: int,
        workflow_id: str | None = None,
        ids: frozenset[str] | None = None,
    ) -> tuple[WorkflowRun, ...]:
        query = self._rows().where(WorkflowRunRow.tenant_id == tenant_id.value)
        if workflow_id is not None:
            query = query.where(WorkflowRunRow.workflow_id == workflow_id)
        if ids is not None:
            query = query.where(WorkflowRunRow.id.in_(sorted(ids)))
        rows = (
            await self._session.execute(
                query.order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc()).limit(
                    limit
                )
            )
        ).scalars()
        return await self._with_steps(rows.all())

    async def taken_back_by(self, tenant_id: TenantId, run_id: str) -> str | None:
        found = await self._session.scalar(
            select(WorkflowRunRow.id).where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.undoes_run == run_id,
                WorkflowRunRow.outcome == "held",
            )
        )
        return str(found) if found else None

    async def failures(self, tenant_id: TenantId) -> Mapping[str, int]:
        query = (
            select(WorkflowRunRow.workflow_id, func.count())
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.outcome.in_(("failed", "refused")),
            )
            .group_by(WorkflowRunRow.workflow_id)
        )
        rows = (await self._session.execute(query)).all()
        return {workflow_id: int(count) for workflow_id, count in rows}

    async def tallies(self, tenant_id: TenantId) -> Mapping[str, tuple[int, int]]:
        query = (
            select(
                WorkflowRunRow.workflow_id,
                func.count(),
                func.count().filter(WorkflowRunRow.outcome == "held"),
            )
            .where(WorkflowRunRow.tenant_id == tenant_id.value)
            .group_by(WorkflowRunRow.workflow_id)
        )
        rows = (await self._session.execute(query)).all()
        return {workflow_id: (int(ran), int(held)) for workflow_id, ran, held in rows}

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[WorkflowRun, ...]:
        query = self._rows().where(
            WorkflowRunRow.tenant_id == tenant_id.value,
            WorkflowRunRow.started_at >= when(since),
        )
        rows = (
            await self._session.execute(
                query.order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc())
            )
        ).scalars()
        return await self._with_steps(rows.all())

    async def outcomes_since(
        self, tenant_id: TenantId, *, since: str
    ) -> tuple[tuple[str, bool, int], ...]:
        rows = await self._session.execute(
            select(WorkflowRunRow.outcome, WorkflowRunRow.live, func.count())
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.started_at >= when(since),
            )
            .group_by(WorkflowRunRow.outcome, WorkflowRunRow.live)
        )
        return tuple((outcome, live, count) for outcome, live, count in rows.all())

    async def driving_windows(self, tenant_id: TenantId) -> tuple[Driving, ...]:
        rows = await self._session.execute(
            select(
                WorkflowRunRow.device_id,
                WorkflowRunRow.started_at,
                WorkflowRunRow.finished_at,
            ).where(WorkflowRunRow.tenant_id == tenant_id.value)
        )
        return tuple(
            Driving(device_id=device_id, started_at=started_at, finished_at=finished_at)
            for device_id, started_at, finished_at in rows
        )

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        busy: str | None = await self._session.scalar(
            select(WorkflowRunRow.id)
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.device_id == device_id.value,
                WorkflowRunRow.outcome == "running",
                WorkflowRunRow.executor == "extension",
            )
            .order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            .limit(1)
        )
        return busy

    async def waiting_on(
        self, tenant_id: TenantId, *, server: str, thread: str
    ) -> WorkflowRun | None:
        if not server.strip() or not thread.strip():
            return None
        query = (
            self._rows()
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.awaiting.isnot(None),
                WorkflowRunRow.awaiting["server"].astext == server.strip(),
                WorkflowRunRow.awaiting["thread"].astext == thread.strip(),
                or_(
                    func.jsonb_array_length(WorkflowRunRow.needs) > 0,
                    and_(
                        WorkflowRunRow.outcome == "running",
                        WorkflowRunRow.progress["asking"]["id"].astext != "",
                    ),
                    and_(
                        WorkflowRunRow.outcome == "stopped",
                        WorkflowRunRow.progress["asking"]["kind"].astext == "recipient",
                    ),
                ),
            )
            .order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc())
            .limit(1)
        )
        rows = (await self._session.execute(query)).scalars().all()
        found = await self._with_steps(rows)
        return found[0] if found else None

    async def started_on(self, tenant_id: TenantId, *, server: str, thread: str) -> bool:
        if not server.strip() or not thread.strip():
            return False
        found = await self._session.scalar(
            select(WorkflowRunRow.id)
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.awaiting.isnot(None),
                WorkflowRunRow.awaiting["server"].astext == server.strip(),
                WorkflowRunRow.awaiting["thread"].astext == thread.strip(),
            )
            .limit(1)
        )
        return found is not None

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]:
        query = (
            select(WorkflowRunStepRow.run_id, WorkflowRunStepRow.ord, WorkflowRunStepRow.says)
            .join(WorkflowRunRow, WorkflowRunRow.id == WorkflowRunStepRow.run_id)
            .where(
                WorkflowRunRow.tenant_id == tenant_id.value,
                WorkflowRunRow.outcome == "running",
                WorkflowRunStepRow.verdict == "awaiting",
            )
            .order_by(WorkflowRunRow.started_at, WorkflowRunRow.id, WorkflowRunStepRow.ord)
        )
        rows = (await self._session.execute(query)).all()
        return tuple((run_id, ord_, says) for run_id, ord_, says in rows)

    async def approve(self, run_id: str, ord_: int, *, at: str, device_id: str | None) -> bool:
        tapped = await self._session.execute(
            pg_insert(ApprovalRow)
            .values(run_id=run_id, ord=ord_, at=when(at), device_id=device_id)
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
        query = self._rows().where(
            WorkflowRunRow.outcome == "running", WorkflowRunRow.executor == "extension"
        )
        rows = (
            await self._session.execute(
                query.order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            )
        ).scalars()
        orphans = await self._with_steps(rows.all())
        for run in orphans:
            if run.steps:
                last = run.steps[-1]
                last.verdict, last.verdict_by, last.reason = "failed", "none", reason
            else:
                run.steps.append(
                    RunStep(order=0, says="", verdict="failed", verdict_by="none", reason=reason)
                )
            run.outcome = "failed"
            run.finished_at = now
            await self.save(run)
        return len(orphans)

    @staticmethod
    def _rows() -> Select[tuple[WorkflowRunRow]]:
        return select(WorkflowRunRow).execution_options(populate_existing=True)

    async def _with_steps(self, rows: Sequence[WorkflowRunRow]) -> tuple[WorkflowRun, ...]:
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
