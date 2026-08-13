"""Read runs. The audit trail is only useful if it can be looked at."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.run import Run, RunId
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
