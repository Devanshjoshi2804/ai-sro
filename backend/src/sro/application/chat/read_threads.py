"""Reading threads. A router never touches a repository."""

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
        """This operator's most recently opened thread, or `None` if they have
        none yet.

        One continuous thread rather than one per host: a job that spans a
        mailbox and the warehouse system is one piece of work, and splitting the
        conversation by tab is the same mistake as splitting the work by tab.

        Asked of the repository as one scoped query rather than filtered out of
        a page of the tenant's newest. The console starts a thread on every
        first ask, so somebody else's threads are exactly what a window would
        fill with -- and an operator whose own thread fell out of it would be
        handed a fresh conversation, orphaning every offer already said in the
        old one, which `offered_at` will never let be said again.

        Returns `None` rather than starting one itself: making a thread is
        `StartThread`'s job, not a second way for one to come into being. A
        reader that quietly writes on a cache-miss is no longer a reader --
        the caller (the router) already knows how to start a thread, so the
        fallback belongs there.
        """
        async with self._uow as uow:
            mine = await uow.threads.list_for_tenant(
                ctx.tenant_id, opened_by=ctx.principal_id, limit=1
            )
        return mine[0] if mine else None
