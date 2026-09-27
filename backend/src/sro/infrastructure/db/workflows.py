from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import CursorResult, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import WorkflowRepository
from sro.domain.execution.belts import RunProof, state_verified
from sro.domain.execution.lanes import K_BROKEN_COOL_DOWN, Broken, Lane
from sro.domain.execution.learned_step import LearnedStep, Taught, changed_by
from sro.domain.execution.mail_job import JobRecipient
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.observation.identity import ShapeKey
from sro.domain.observation.mining import MiningPass
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.repeats import Repeat
from sro.domain.skill.workflow import Noticed, Step, Workflow
from sro.infrastructure.db.codec import when
from sro.infrastructure.db.models import (
    JobRecipientRow,
    KnownBrokenRow,
    LearnedWriteRow,
    MiningPassRow,
    WorkflowEffectRow,
    WorkflowLearnedHistoryRow,
    WorkflowLearnedRow,
    WorkflowPlacementRow,
    WorkflowRow,
    WorkflowRunRow,
    WorkflowRunStepRow,
    WorkflowStaleRow,
    WorkflowStepRow,
)


def _workflow_values(workflow: Workflow) -> dict[str, Any]:
    return {
        "id": workflow.id,
        "tenant_id": workflow.tenant,
        "pass_id": workflow.pass_id,
        "title": workflow.title,
        "narrative": workflow.narrative,
        "systems": list(workflow.systems),
        "parameters": list(workflow.parameters),
        "shape_key": [list(entry) for entry in workflow.shape_key],
        "repeat": (
            None
            if workflow.repeat is None
            else {
                "first_step": workflow.repeat.first_step,
                "last_step": workflow.repeat.last_step,
            }
        ),
        "signs_in": workflow.signs_in,
        "signs_out": workflow.signs_out,
        "created_at": datetime.now(tz=UTC),
    }


def _step_values(workflow_id: str, step: Step) -> dict[str, Any]:
    return {
        "workflow_id": workflow_id,
        "ord": step.order,
        "says": step.says,
        "system": step.system,
        "cites": list(step.cites),
        "parameters": list(step.parameters),
        "uses": list(step.uses),
        "tab": step.tab,
    }


def _row_to_step(row: WorkflowStepRow) -> Step:
    return Step(
        order=row.ord,
        says=row.says,
        system=row.system,
        cites=list(row.cites),
        parameters=list(row.parameters),
        uses=list(row.uses or []),
        tab=row.tab,
    )


def _row_to_workflow(row: WorkflowRow, steps: list[Step]) -> Workflow:
    return Workflow(
        id=row.id,
        tenant=row.tenant_id,
        title=row.title,
        narrative=row.narrative,
        systems=list(row.systems),
        steps=steps,
        parameters=list(row.parameters),
        shape_key=[list(entry) for entry in row.shape_key],
        pass_id=row.pass_id,
        repeat=(
            Repeat(
                first_step=int(row.repeat["first_step"]),
                last_step=int(row.repeat["last_step"]),
            )
            if isinstance(row.repeat, dict)
            else None
        ),
        signs_in=row.signs_in,
        signs_out=row.signs_out,
    )


def workflow_json(workflow: Workflow) -> dict[str, Any]:
    columns = _workflow_values(workflow)
    del columns["created_at"]
    return {
        "workflow": columns,
        "steps": [_step_values(workflow.id, step) for step in workflow.steps],
    }


def workflow_from_json(held: dict[str, Any]) -> Workflow:
    return _row_to_workflow(
        WorkflowRow(**_known(WorkflowRow, held["workflow"])),
        [_row_to_step(WorkflowStepRow(**_known(WorkflowStepRow, step))) for step in held["steps"]],
    )


def _known(table: type[Any], columns: dict[str, Any]) -> dict[str, Any]:
    names = table.__table__.columns.keys()
    return {name: value for name, value in columns.items() if name in names}


def _row_to_pass(row: MiningPassRow) -> MiningPass:
    return MiningPass(
        id=row.id,
        tenant=row.tenant_id,
        started_at=row.started_at.isoformat(),
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
        proposed=row.proposed,
        kept=row.kept,
        rejected=row.rejected,
        learned_parameters=row.learned_parameters,
        coverage=row.coverage,
        skew=row.skew,
        lopsided=row.lopsided,
        window_size=row.window_size,
        left_out=row.left_out,
        unplaced=row.unplaced,
        dropped=row.dropped,
        error=row.error,
    )


logger = logging.getLogger(__name__)


class SqlWorkflowRepository(WorkflowRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, workflow: Workflow) -> None:
        async with self._session.begin_nested():
            values = _workflow_values(workflow)
            statement = pg_insert(WorkflowRow).values(**values)
            await self._session.execute(
                statement.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        name: statement.excluded[name]
                        for name in values
                        if name not in ("id", "retired_at", "created_at", "signs_in", "signs_out")
                    },
                )
            )
            await self._session.execute(
                delete(WorkflowStepRow).where(WorkflowStepRow.workflow_id == workflow.id)
            )
            if workflow.steps:
                await self._session.execute(
                    pg_insert(WorkflowStepRow).values(
                        [_step_values(workflow.id, step) for step in workflow.steps]
                    )
                )

    async def known(self, tenant_id: TenantId) -> tuple[Workflow, ...]:
        query = (
            select(WorkflowRow)
            .where(WorkflowRow.tenant_id == tenant_id.value, WorkflowRow.retired_at.is_(None))
            .order_by(WorkflowRow.created_at, WorkflowRow.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(query)).scalars().all()
        if not rows:
            return ()
        steps = await self._steps_of([row.id for row in rows])
        return tuple(_row_to_workflow(row, steps[row.id]) for row in rows)

    async def noticed_since(self, tenant_id: TenantId, *, since: datetime) -> tuple[Noticed, ...]:
        steps = (
            select(func.count())
            .select_from(WorkflowStepRow)
            .where(WorkflowStepRow.workflow_id == WorkflowRow.id)
            .scalar_subquery()
        )
        query = (
            select(
                WorkflowRow.id,
                WorkflowRow.title,
                WorkflowRow.systems,
                steps,
            )
            .where(
                WorkflowRow.tenant_id == tenant_id.value,
                WorkflowRow.retired_at.is_(None),
                WorkflowRow.created_at >= since,
            )
            .order_by(WorkflowRow.created_at.desc(), WorkflowRow.id.desc())
        )
        return tuple(
            Noticed(
                id=row[0],
                title=row[1],
                systems=tuple(str(one) for one in row[2] or ()),
                steps=int(row[3]),
            )
            for row in (await self._session.execute(query)).all()
        )

    async def get(self, tenant_id: TenantId, workflow_id: str, *, lock: bool = False) -> Workflow:
        query = (
            select(WorkflowRow)
            .where(
                WorkflowRow.tenant_id == tenant_id.value,
                WorkflowRow.id == workflow_id,
                WorkflowRow.retired_at.is_(None),
            )
            .execution_options(populate_existing=True)
        )
        if lock:
            query = query.with_for_update()
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"workflow {workflow_id} was not found")
        steps = await self._steps_of([row.id])
        return _row_to_workflow(row, steps[row.id])

    async def retire(self, tenant_id: TenantId, workflow_id: str, *, at: datetime) -> None:
        done = await self._session.execute(
            update(WorkflowRow)
            .where(
                WorkflowRow.tenant_id == tenant_id.value,
                WorkflowRow.id == workflow_id,
                WorkflowRow.retired_at.is_(None),
            )
            .values(retired_at=at)
            .returning(WorkflowRow.id)
        )
        if done.first() is None:
            raise NotFound(f"workflow {workflow_id} was not found")

    async def place(
        self, tenant_id: TenantId, workflow_id: str, gesture_ids: tuple[str, ...]
    ) -> None:
        if not gesture_ids:
            return
        await self._session.execute(
            pg_insert(WorkflowPlacementRow)
            .values(
                [
                    {"tenant_id": tenant_id.value, "gesture_id": one, "workflow_id": workflow_id}
                    for one in dict.fromkeys(gesture_ids)
                ]
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "gesture_id"])
        )

    async def placed(self, tenant_id: TenantId) -> frozenset[str]:
        rows = await self._session.execute(
            select(WorkflowStepRow.cites)
            .join(WorkflowRow, WorkflowRow.id == WorkflowStepRow.workflow_id)
            .where(WorkflowRow.tenant_id == tenant_id.value)
        )
        folded = await self._session.execute(
            select(WorkflowPlacementRow.gesture_id).where(
                WorkflowPlacementRow.tenant_id == tenant_id.value
            )
        )
        return frozenset(str(one) for (cites,) in rows for one in cites or ()) | frozenset(
            folded.scalars()
        )

    async def rekey(self, tenant_id: TenantId, workflow_id: str, key: ShapeKey) -> None:
        await self._session.execute(
            update(WorkflowRow)
            .where(WorkflowRow.tenant_id == tenant_id.value, WorkflowRow.id == workflow_id)
            .values(shape_key=[list(entry) for entry in key])
        )

    async def undecided(self) -> tuple[Workflow, ...]:
        query = (
            select(WorkflowRow)
            .where(
                or_(WorkflowRow.signs_in.is_(None), WorkflowRow.signs_out.is_(None)),
                WorkflowRow.retired_at.is_(None),
            )
            .order_by(WorkflowRow.tenant_id, WorkflowRow.created_at, WorkflowRow.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(query)).scalars().all()
        if not rows:
            return ()
        steps = await self._steps_of([row.id for row in rows])
        return tuple(_row_to_workflow(row, steps[row.id]) for row in rows)

    async def decide(
        self, tenant_id: TenantId, workflow: Workflow, *, signs_in: bool, signs_out: bool
    ) -> bool:
        try:
            stored = await self.get(tenant_id, workflow.id, lock=True)
        except NotFound:
            return False
        if (stored.steps, stored.signs_in, stored.signs_out) != (
            workflow.steps,
            workflow.signs_in,
            workflow.signs_out,
        ):
            return False
        await self._session.execute(
            update(WorkflowRow)
            .where(WorkflowRow.tenant_id == tenant_id.value, WorkflowRow.id == workflow.id)
            .values(signs_in=signs_in, signs_out=signs_out)
        )
        return True

    async def tabs_undecided(self) -> tuple[Workflow, ...]:
        untabbed = select(WorkflowStepRow.workflow_id).where(WorkflowStepRow.tab.is_(None))
        query = (
            select(WorkflowRow)
            .where(WorkflowRow.id.in_(untabbed), WorkflowRow.retired_at.is_(None))
            .order_by(WorkflowRow.tenant_id, WorkflowRow.created_at, WorkflowRow.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(query)).scalars().all()
        if not rows:
            return ()
        steps = await self._steps_of([row.id for row in rows])
        return tuple(_row_to_workflow(row, steps[row.id]) for row in rows)

    async def decide_tab(self, tenant_id: TenantId, workflow_id: str, order: int, tab: str) -> bool:
        owned = select(WorkflowRow.id).where(
            WorkflowRow.tenant_id == tenant_id.value, WorkflowRow.id == workflow_id
        )
        decided = await self._session.execute(
            update(WorkflowStepRow)
            .where(
                WorkflowStepRow.workflow_id.in_(owned),
                WorkflowStepRow.ord == order,
                WorkflowStepRow.tab.is_(None),
            )
            .values(tab=tab)
        )
        return cast(CursorResult[Any], decided).rowcount > 0

    async def add_pass(self, mining_pass: MiningPass) -> None:
        try:
            await self._session.execute(
                pg_insert(MiningPassRow).values(
                    id=mining_pass.id,
                    tenant_id=mining_pass.tenant,
                    started_at=when(mining_pass.started_at),
                    in_tokens=mining_pass.in_tokens,
                    out_tokens=mining_pass.out_tokens,
                    thought_tokens=mining_pass.thought_tokens,
                    cost_usd=mining_pass.cost_usd,
                    unpriced=mining_pass.unpriced,
                    proposed=mining_pass.proposed,
                    kept=mining_pass.kept,
                    rejected=mining_pass.rejected,
                    learned_parameters=mining_pass.learned_parameters,
                    coverage=mining_pass.coverage,
                    skew=mining_pass.skew,
                    lopsided=mining_pass.lopsided,
                    window_size=mining_pass.window_size,
                    left_out=mining_pass.left_out,
                    unplaced=mining_pass.unplaced,
                    dropped=mining_pass.dropped,
                    error=mining_pass.error,
                )
            )
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"mining pass {mining_pass.id} is already stored") from clash

    async def passes(self, tenant_id: TenantId) -> tuple[MiningPass, ...]:
        query = (
            select(MiningPassRow)
            .where(MiningPassRow.tenant_id == tenant_id.value)
            .order_by(MiningPassRow.started_at, MiningPassRow.id)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(_row_to_pass(row) for row in rows)

    async def mark_stale(
        self, workflow_id: str, ord_: int, *, matched_by: str | None, noticed_at: str
    ) -> None:
        statement = pg_insert(WorkflowStaleRow).values(
            workflow_id=workflow_id,
            ord=ord_,
            matched_by=matched_by,
            noticed_at=when(noticed_at),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "ord"],
                set_={
                    "matched_by": statement.excluded.matched_by,
                    "noticed_at": statement.excluded.noticed_at,
                },
            )
        )

    async def remember_limit(
        self, workflow_id: str, ord_: int, holds: int, *, by_run: str = ""
    ) -> None:
        already = next(
            (one for one in await self.learned_for(workflow_id) if one.ord == ord_), None
        )
        await self._keep_what_changed(
            workflow_id,
            LearnedStep(
                ord=ord_,
                strategy=already.strategy if already else "",
                query=already.query if already else "",
                found_by="typed",
                holds=holds,
            ),
            by_run=by_run,
        )
        statement = pg_insert(WorkflowLearnedRow).values(
            workflow_id=workflow_id,
            ord=ord_,
            strategy="",
            query="",
            found_by="typed",
            holds=holds,
            learned_at=datetime.now(tz=UTC),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "ord"],
                set_={
                    "holds": statement.excluded.holds,
                    "learned_at": statement.excluded.learned_at,
                },
            )
        )

    async def remember_locator(
        self, workflow_id: str, learned: LearnedStep, *, by_run: str = ""
    ) -> None:
        await self._keep_what_changed(workflow_id, learned, by_run=by_run)
        statement = pg_insert(WorkflowLearnedRow).values(
            workflow_id=workflow_id,
            ord=learned.ord,
            strategy=learned.strategy,
            query=learned.query,
            found_by=learned.found_by,
            frame_path=learned.frame_path,
            learned_at=datetime.now(tz=UTC),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "ord"],
                set_={
                    "strategy": statement.excluded.strategy,
                    "query": statement.excluded.query,
                    "found_by": statement.excluded.found_by,
                    "frame_path": statement.excluded.frame_path,
                    "learned_at": statement.excluded.learned_at,
                },
            )
        )

    async def _keep_what_changed(
        self, workflow_id: str, now: LearnedStep, *, by_run: str = ""
    ) -> None:
        try:
            was = next(
                (one for one in await self.learned_for(workflow_id) if one.ord == now.ord),
                None,
            )
            at = datetime.now(tz=UTC)
            for change in changed_by(was, now, by_run=by_run):
                self._session.add(
                    WorkflowLearnedHistoryRow(
                        id=f"lrn_{workflow_id}_{change.ord}_{change.about}_{at.timestamp()}"[:64],
                        workflow_id=workflow_id,
                        ord=change.ord,
                        about=change.about,
                        was=change.was,
                        now=change.now,
                        by_run=change.by_run,
                        found_by=change.found_by,
                        at=at,
                    )
                )
        except Exception:
            logger.exception("what %s taught itself could not be written down", workflow_id)

    async def taught_itself(self, workflow_id: str, limit: int = 50) -> tuple[Taught, ...]:
        rows = (
            await self._session.execute(
                select(WorkflowLearnedHistoryRow)
                .where(WorkflowLearnedHistoryRow.workflow_id == workflow_id)
                .order_by(WorkflowLearnedHistoryRow.at.desc())
                .limit(limit)
            )
        ).scalars()
        return tuple(
            Taught(
                ord=row.ord,
                about=row.about,
                was=row.was,
                now=row.now,
                by_run=row.by_run,
                found_by=row.found_by,
            )
            for row in rows
        )

    async def break_lane(
        self, tenant_id: TenantId, workflow_id: str, broken: Broken, *, cites: str, at: datetime
    ) -> None:
        statement = pg_insert(KnownBrokenRow).values(
            tenant_id=tenant_id.value,
            workflow_id=workflow_id,
            ord=broken.step,
            lane=broken.lane.value,
            fingerprint=broken.fingerprint,
            cites=cites,
            at=at,
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["tenant_id", "workflow_id", "ord", "lane", "fingerprint"],
                set_={"cites": statement.excluded.cites, "at": statement.excluded.at},
            )
        )

    async def broken_for(
        self, tenant_id: TenantId, workflow_id: str, cites: Mapping[int, str], *, now: datetime
    ) -> tuple[Broken, ...]:
        rows = (
            await self._session.execute(
                select(KnownBrokenRow)
                .where(
                    KnownBrokenRow.tenant_id == tenant_id.value,
                    KnownBrokenRow.workflow_id == workflow_id,
                    KnownBrokenRow.at > now - K_BROKEN_COOL_DOWN,
                )
                .order_by(KnownBrokenRow.ord, KnownBrokenRow.lane, KnownBrokenRow.fingerprint)
            )
        ).scalars()
        return tuple(
            Broken(row.ord, Lane(row.lane), row.fingerprint)
            for row in rows
            if cites.get(row.ord) == row.cites
        )

    async def mend_lane(self, tenant_id: TenantId, workflow_id: str, step: int, lane: Lane) -> None:
        await self._session.execute(
            delete(KnownBrokenRow).where(
                KnownBrokenRow.tenant_id == tenant_id.value,
                KnownBrokenRow.workflow_id == workflow_id,
                KnownBrokenRow.ord == step,
                KnownBrokenRow.lane == lane.value,
            )
        )

    async def recipients_for(
        self, tenant_id: TenantId, workflow_id: str
    ) -> tuple[JobRecipient, ...]:
        rows = (
            await self._session.execute(
                select(JobRecipientRow)
                .where(
                    JobRecipientRow.tenant_id == tenant_id.value,
                    JobRecipientRow.workflow_id == workflow_id,
                )
                .order_by(JobRecipientRow.at, JobRecipientRow.address)
            )
        ).scalars()
        return tuple(JobRecipient(row.address, row.confirmed_by, row.at) for row in rows)

    async def confirm_recipient(
        self, tenant_id: TenantId, workflow_id: str, recipient: JobRecipient
    ) -> None:
        statement = pg_insert(JobRecipientRow).values(
            tenant_id=tenant_id.value,
            workflow_id=workflow_id,
            address=recipient.address,
            confirmed_by=recipient.confirmed_by,
            at=recipient.at,
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["tenant_id", "workflow_id", "address"],
                set_={
                    "confirmed_by": statement.excluded.confirmed_by,
                    "at": statement.excluded.at,
                },
            )
        )

    async def learned_for(self, workflow_id: str) -> tuple[LearnedStep, ...]:
        rows = (
            await self._session.execute(
                select(WorkflowLearnedRow).where(WorkflowLearnedRow.workflow_id == workflow_id)
            )
        ).scalars()
        return tuple(
            LearnedStep(
                ord=row.ord,
                strategy=row.strategy,
                query=row.query,
                found_by=row.found_by,
                holds=row.holds,
                frame_path=row.frame_path,
            )
            for row in rows
        )

    async def clear_stale(self, workflow_id: str, ord_: int) -> None:
        await self._session.execute(
            delete(WorkflowStaleRow).where(
                WorkflowStaleRow.workflow_id == workflow_id, WorkflowStaleRow.ord == ord_
            )
        )

    async def stale_count(self, workflow_id: str) -> int:
        found = await self._session.scalar(
            select(func.count())
            .select_from(WorkflowStaleRow)
            .where(WorkflowStaleRow.workflow_id == workflow_id)
        )
        return int(found or 0)

    async def grew(self, workflow: Workflow, *, moved: Mapping[int, int]) -> None:
        keyed_by_ord: tuple[type[Any], ...] = (
            WorkflowLearnedRow,
            WorkflowStaleRow,
            WorkflowLearnedHistoryRow,
            KnownBrokenRow,
        )
        for table in keyed_by_ord:
            rows = (
                (await self._session.execute(select(table).where(table.workflow_id == workflow.id)))
                .scalars()
                .all()
            )
            kept = [
                {
                    **{
                        column.name: getattr(row, column.name) for column in table.__table__.columns
                    },
                    "ord": moved[row.ord],
                }
                for row in rows
                if row.ord in moved
            ]
            await self._session.execute(delete(table).where(table.workflow_id == workflow.id))
            if kept:
                await self._session.execute(pg_insert(table).values(kept))
        await self.save(workflow)

    async def remember_write(
        self,
        tenant_id: TenantId,
        *,
        method: str,
        path_pattern: str,
        origin: str,
        run_id: str,
        workflow_id: str,
        verified_by: str,
        at: str,
    ) -> None:
        if not state_verified(verified_by):
            return
        statement = pg_insert(LearnedWriteRow).values(
            tenant_id=tenant_id.value,
            method=method.upper(),
            path_pattern=path_pattern,
            origin=origin,
            proved_by_run=run_id,
            workflow_id=workflow_id,
            verified_by=verified_by,
            at=when(at),
        )
        await self._session.execute(
            statement.on_conflict_do_nothing(index_elements=["tenant_id", "method", "path_pattern"])
        )

    async def learned_writes(self, tenant_id: TenantId) -> tuple[VerifiedWrite, ...]:
        rows = await self._session.execute(
            select(LearnedWriteRow.method, LearnedWriteRow.path_pattern).where(
                LearnedWriteRow.tenant_id == tenant_id.value
            )
        )
        return tuple(VerifiedWrite(method=method, path_pattern=pattern) for method, pattern in rows)

    async def record_effect(
        self, workflow_id: str, *, run_id: str, ord_: int, verified_by: str, at: str
    ) -> None:
        if not state_verified(verified_by):
            return
        statement = pg_insert(WorkflowEffectRow).values(
            workflow_id=workflow_id,
            run_id=run_id,
            ord=ord_,
            verified_by=verified_by,
            at=when(at),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["workflow_id", "run_id", "ord"],
                set_={
                    "verified_by": statement.excluded.verified_by,
                    "at": statement.excluded.at,
                },
            )
        )

    async def forget_effects(self, workflow_id: str) -> int:
        gone = await self._session.execute(
            delete(WorkflowEffectRow)
            .where(WorkflowEffectRow.workflow_id == workflow_id)
            .returning(WorkflowEffectRow.run_id)
        )
        return len(gone.all())

    async def proofs(self, tenant_id: TenantId, workflow_id: str) -> tuple[RunProof, ...]:
        runs = (
            await self._session.execute(
                select(WorkflowRunRow.id)
                .where(
                    WorkflowRunRow.tenant_id == tenant_id.value,
                    WorkflowRunRow.workflow_id == workflow_id,
                    WorkflowRunRow.live.is_(True),
                    WorkflowRunRow.outcome == "held",
                )
                .order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)
            )
        ).scalars()
        run_ids = list(runs.all())
        if not run_ids:
            return ()

        wrote: defaultdict[str, set[int]] = defaultdict(set)
        steps = await self._session.execute(
            select(
                WorkflowRunStepRow.run_id, WorkflowRunStepRow.ord, WorkflowRunStepRow.result
            ).where(WorkflowRunStepRow.run_id.in_(run_ids))
        )
        for run_id, ord_, result in steps.all():
            if result and result.get("wrote"):
                wrote[run_id].add(ord_)

        verified: defaultdict[str, set[int]] = defaultdict(set)
        effects = await self._session.execute(
            select(WorkflowEffectRow.run_id, WorkflowEffectRow.ord).where(
                WorkflowEffectRow.workflow_id == workflow_id,
                WorkflowEffectRow.run_id.in_(run_ids),
            )
        )
        for run_id, ord_ in effects.all():
            verified[run_id].add(ord_)

        return tuple(
            RunProof(
                run_id=run_id,
                wrote=frozenset(wrote[run_id]),
                verified=frozenset(verified[run_id]),
            )
            for run_id in run_ids
        )

    async def _steps_of(self, workflow_ids: list[str]) -> defaultdict[str, list[Step]]:
        query = (
            select(WorkflowStepRow)
            .where(WorkflowStepRow.workflow_id.in_(workflow_ids))
            .order_by(WorkflowStepRow.workflow_id, WorkflowStepRow.ord)
            .execution_options(populate_existing=True)
        )
        steps: defaultdict[str, list[Step]] = defaultdict(list)
        for row in (await self._session.execute(query)).scalars().all():
            steps[row.workflow_id].append(_row_to_step(row))
        return steps
