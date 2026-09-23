from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.learned_step import Taught


class ReadWhatAJobTaught:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, workflow_id: str) -> tuple[Taught, ...]:
        async with self._uow as uow:
            await uow.workflows.get(ctx.tenant_id, workflow_id)
            return await uow.workflows.taught_itself(workflow_id)


__all__ = ["ReadWhatAJobTaught"]
