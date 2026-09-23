from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.execution.stops import Stops
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.run import Run, RunId, RunStatus
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import SkillId


class GetRun:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, run_id: RunId) -> Run:
        async with self._uow as uow:
            return await uow.runs.get(ctx.tenant_id, run_id)


class ListRuns:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Run, ...]:
        async with self._uow as uow:
            return await uow.runs.list_for_tenant(
                ctx.tenant_id, skill_id=skill_id, limit=limit, offset=offset
            )


class CannotStop(Conflict):
    code = "cannot_stop"


NOT_IN_A_BROWSER_HERE = "that run is not being performed in a browser this process is driving"


class StopRun:
    def __init__(self, uow: UnitOfWork, stops: Stops) -> None:
        self._uow = uow
        self._stops = stops

    async def execute(self, ctx: RequestContext, *, run_id: RunId) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
        if run.status is not RunStatus.RUNNING:
            raise CannotStop(f"that run already {run.status.value}")
        if run.device_id is None:
            raise CannotStop(NOT_IN_A_BROWSER_HERE)
        self._stops.ask(run.id.value)
        return run
