from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.chat.thread import Thread, ThreadId, asking_about
from sro.domain.shared.errors import NotFound


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
                ctx.tenant_id, opened_by=ctx.principal_id, asking=False, limit=1
            )
        return mine[0] if mine else None

    async def asked(self, ctx: RequestContext, *, limit: int = 10) -> tuple[Thread, ...]:
        async with self._uow as uow:
            return await uow.threads.list_for_tenant(
                ctx.tenant_id, opened_by=ctx.principal_id, asking=True, limit=limit
            )

    async def asking(self, ctx: RequestContext, about: str) -> Thread | None:
        if not about.strip():
            return None
        try:
            async with self._uow as uow:
                return await uow.threads.get(
                    ctx.tenant_id, asking_about(ctx.tenant_id, ctx.principal_id, about)
                )
        except NotFound:
            return None
