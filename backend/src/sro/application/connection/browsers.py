"""Every browser this system opens, finds or hands back, and whose it is.

The provider has no tenants and must not learn about any -- Steel hands out an
id and knows nothing else about it. Ownership is a fact *this* system records
about that id, so it lives on this side of the port, in a table both processes
read: the API and the Temporal worker each build their own container, and both
open and close browsers.

Before this existed, a session id was a bare string. Six paths took one from a
URL, from the provider's list of live sessions, or from a query parameter, and
drove it or emptied its cookies into the caller's vault -- none of them able to
tell one customer's browser from another's.

Borrowing survives, because it was always the right behaviour on a provider with
one browser: asking for a second does not produce one. What changed is the set
it borrows from -- this tenant's browsers rather than the deployment's.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserProvider, BrowserSession, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import BrowserSessionId


class Browsers:
    def __init__(
        self,
        browser: BrowserProvider,
        uow: UnitOfWork,
        clock: Clock,
        ids: IdFactory,
    ) -> None:
        self._browser = browser
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def open(self, ctx: RequestContext, *, start_url: str | None = None) -> BrowserSession:
        """A new browser, claimed for this tenant before it is handed over.

        When the provider has none to give, one this tenant already holds and
        nobody is demonstrating in. Raises ``BrowserUnavailable`` if neither.
        """
        try:
            session = await self._browser.open(start_url=start_url)
        except BrowserUnavailable:
            borrowed = await self._spare(ctx)
            if borrowed is None:
                raise
            return borrowed

        await self._claim(ctx, session.id)
        return session

    async def attach(self, ctx: RequestContext, debugger_url: str) -> BrowserSession:
        """A browser the operator already has open, owned like any other.

        The id is ours rather than the provider's -- it never issued one. It was
        a single shared constant before, so every attached recording of every
        tenant collided on it. Releasing it is a no-op at the provider, which is
        correct: closing somebody's own Chrome was never ours to do.
        """
        session_id = BrowserSessionId(f"attached_{self._ids.new_recording_id().value}")
        await self._claim(ctx, session_id)
        return BrowserSession(id=session_id, live_view_url="", debugger_url=debugger_url)

    async def mine(self, ctx: RequestContext) -> tuple[BrowserSession, ...]:
        """This tenant's browsers that are still live.

        The intersection is the point. A claim on a session the provider has
        forgotten is not a browser, and a live session this tenant never claimed
        is not theirs to look at.
        """
        async with self._uow as uow:
            claimed = {str(held) for held in await uow.browser_sessions.held_by(ctx.tenant_id)}
        if not claimed:
            return ()

        found: list[BrowserSession] = []
        for session_id in await self._live():
            if str(session_id) not in claimed:
                continue
            found.append(await self._describe(session_id))
        return tuple(found)

    async def session(self, ctx: RequestContext, session_id: BrowserSessionId) -> BrowserSession:
        """This tenant's browser, by id.

        ``NotFound`` when it is not theirs, deliberately the same answer as an id
        that never existed: every other resource here 404s across tenants, and
        this must not become the one that says which ids are real.
        """
        for session in await self.mine(ctx):
            if session.id == session_id:
                return session
        raise NotFound(f"no browser session {session_id} belongs to you")

    async def release(self, session_id: BrowserSessionId) -> None:
        """Close it and drop the claim. Both idempotent, and not tenant-scoped:
        the stray sweep and crash recovery are nobody's request."""
        try:
            await self._browser.close(session_id)
        finally:
            async with self._uow as uow:
                await uow.browser_sessions.release(session_id)
                await uow.commit()

    async def _claim(self, ctx: RequestContext, session_id: BrowserSessionId) -> None:
        async with self._uow as uow:
            await uow.browser_sessions.claim(
                ctx.tenant_id, session_id, ctx.principal_id, self._clock.now()
            )
            await uow.commit()

    async def _spare(self, ctx: RequestContext) -> BrowserSession | None:
        """One of this tenant's browsers that nobody is demonstrating in.

        Never one a recording is capturing: two things driving one screen record
        each other's gestures, and the demonstration is the evidence everything
        else is built from.
        """
        async with self._uow as uow:
            capturing = await uow.recordings.list_capturing()
        busy = {str(recording.browser_session_id) for recording in capturing}
        return next(
            (session for session in await self.mine(ctx) if str(session.id) not in busy),
            None,
        )

    async def _live(self) -> tuple[BrowserSessionId, ...]:
        try:
            return await self._browser.live_sessions()
        except BrowserUnavailable:
            # A provider that cannot be asked is not a provider holding a browser
            # of yours. Nothing is released and nothing is offered.
            return ()

    async def _describe(self, session_id: BrowserSessionId) -> BrowserSession:
        return BrowserSession(
            id=session_id,
            live_view_url=await self._browser.live_view_url(session_id) or "",
            debugger_url=await self._browser.debugger_url(session_id),
        )
