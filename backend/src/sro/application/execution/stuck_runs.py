from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from sro.application.chat.announce import SayWhatHappened
from sro.application.context import RequestContext
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.execution.progress import K_BUDGET_FLOOR_S, run_budget
from sro.domain.execution.waiting import STUCK, Durably, stuck
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.workflow import cited_ids

logger = logging.getLogger(__name__)

Release = Callable[[RequestContext, str], Awaitable[None]]


class CloseStuckRuns:
    def __init__(
        self,
        uow: UnitOfWork,
        *,
        durable: DurableExecution | None,
        release: Release,
        clock: Clock,
        ids: IdFactory,
    ) -> None:
        self._uow = uow
        self._durable = durable
        self._release = release
        self._clock = clock
        self._ids = ids

    async def execute(self) -> tuple[str, ...]:
        async with self._uow as uow:
            running = await uow.workflow_runs.running()
        closed: list[str] = []
        for run in running:
            try:
                if await self._close(run):
                    closed.append(run.id)
            except Exception:
                logger.exception("%s: a stuck run could not be closed", run.id)
        return tuple(closed)

    async def _close(self, run: WorkflowRun) -> bool:
        tenant = TenantId(run.tenant)
        budget, title = await self._budget(tenant, run)
        now = self._clock.now()
        if not stuck(run, budget_s=budget, now=now, durable=await self._durably(run)):
            return False
        async with self._uow as uow:
            won = await uow.workflow_runs.close_stuck(
                tenant, run.id, reason=STUCK, at=now.isoformat(), was=run.progress
            )
            await uow.commit()
        if not won:
            return False
        operator = PrincipalId(run.started_by or "run-sweeper")
        ctx = RequestContext(tenant, operator)
        if run.executor == "steel":
            await self._release(ctx, run.id)
        if run.started_by:
            await SayWhatHappened(self._uow, self._clock, self._ids).execute(
                ctx,
                for_operator=operator,
                text=f"{title} did not finish: {STUCK}.",
                decision={"kind": "note", "run_id": run.id},
            )
        return True

    async def _budget(self, tenant: TenantId, run: WorkflowRun) -> tuple[float, str]:
        async with self._uow as uow:
            try:
                workflow = run.pinned or await uow.workflows.get(tenant, run.workflow_id)
            except NotFound:
                return float(K_BUDGET_FLOOR_S), "A run"
            cited = await uow.gestures.gestures_for(tenant, ids=tuple(sorted(cited_ids(workflow))))
        return run_budget(workflow, {one.id: one for one in cited}), workflow.title

    async def _durably(self, run: WorkflowRun) -> Durably:
        if run.executor != "steel" or self._durable is None:
            return "unknown"
        return await self._durable.run_state(run.id)
