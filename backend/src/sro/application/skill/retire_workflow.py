from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock


class RetireWorkflow:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, workflow_id: str) -> None:
        async with self._uow as uow:
            await uow.workflows.retire(ctx.tenant_id, workflow_id, at=self._clock.now())
            await uow.commit()
