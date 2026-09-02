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

        Filtered here rather than in the repository, because `list_for_tenant`
        is what the repository offers and a tenant's threads are few. When they
        are not, this wants its own query -- and the shape of that query is
        exactly this filter, so nothing is lost by waiting for the pressure.

        Returns `None` rather than starting one itself: making a thread is
        `StartThread`'s job, not a second way for one to come into being. A
        reader that quietly writes on a cache-miss is no longer a reader --
        the caller (the router) already knows how to start a thread, so the
        fallback belongs there.
        """
        async with self._uow as uow:
            threads = await uow.threads.list_for_tenant(ctx.tenant_id, limit=50)
        mine = [thread for thread in threads if thread.opened_by == ctx.principal_id]
        return max(mine, key=lambda thread: thread.opened_at) if mine else None
