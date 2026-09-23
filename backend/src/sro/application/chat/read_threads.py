from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.thread import Thread, ThreadId


class ReadThreads:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def get(self, ctx: RequestContext, *, thread_id: ThreadId) -> Thread:
        async with self._uow as uow:
            return await uow.threads.get(ctx.tenant_id, thread_id)

    async def list(self, ctx: RequestContext, *, limit: int = 50) -> tuple[Thread, ...]:
        async with self._uow as uow:
            return await uow.threads.list_for_tenant(ctx.tenant_id, limit=limit)

    async def current(self, ctx: RequestContext) -> Thread | None:
        async with self._uow as uow:
            mine = await uow.threads.list_for_tenant(
                ctx.tenant_id, opened_by=ctx.principal_id, limit=1
            )
        return mine[0] if mine else None
