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
        session, _borrowed = await self.take(ctx, start_url=start_url)
        return session

    async def take(
        self, ctx: RequestContext, *, start_url: str | None = None
    ) -> tuple[BrowserSession, bool]:
        try:
            session = await self._browser.open(start_url=start_url)
        except BrowserUnavailable:
            borrowed = await self._spare(ctx)
            if borrowed is None:
                raise
            return borrowed, True

        await self._claim(ctx, session.id)
        return session, False

    async def attach(self, ctx: RequestContext, debugger_url: str) -> BrowserSession:
        session_id = BrowserSessionId(f"attached_{self._ids.new_recording_id().value}")
        await self._claim(ctx, session_id)
        return BrowserSession(id=session_id, live_view_url="", debugger_url=debugger_url)

    async def mine(self, ctx: RequestContext) -> tuple[BrowserSession, ...]:
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
        for session in await self.mine(ctx):
            if session.id == session_id:
                return session
        raise NotFound(f"no browser session {session_id} belongs to you")

    async def release(self, session_id: BrowserSessionId) -> None:
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
            return ()

    async def _describe(self, session_id: BrowserSessionId) -> BrowserSession:
        return BrowserSession(
            id=session_id,
            live_view_url=await self._browser.live_view_url(session_id) or "",
            debugger_url=await self._browser.debugger_url(session_id),
        )
