from __future__ import annotations

from datetime import timedelta

from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.execution.pursuits import Pursuits
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.shared.identifiers import BrowserSessionId

GRACE = timedelta(minutes=15)


class ReleaseStrayBrowsers:
    def __init__(
        self,
        uow: UnitOfWork,
        browser: BrowserProvider,
        watch: WatchBrowsers,
        pursuits: Pursuits,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._browser = browser
        self._watch = watch
        self._pursuits = pursuits
        self._clock = clock

    async def execute(self) -> tuple[str, ...]:
        open_now = await self._watch.all_in_deployment()
        in_use = await self._in_use()
        async with self._uow as uow:
            opened_at = {
                str(session_id): when for session_id, when in await uow.browser_sessions.all_held()
            }
        now = self._clock.now()

        released: list[str] = []
        for browser in open_now:
            if browser.session_id in in_use:
                continue
            claimed = opened_at.get(browser.session_id)
            if claimed is not None and now - claimed < GRACE:
                continue
            try:
                await self._browser.close(BrowserSessionId(browser.session_id))
            except BrowserUnavailable:
                continue
            released.append(browser.session_id)

        await self._forget(released)
        live = {browser.session_id for browser in open_now}
        await self._forget([held for held in opened_at if held not in live])
        return tuple(released)

    async def _in_use(self) -> set[str]:
        async with self._uow as uow:
            capturing = await uow.recordings.list_capturing()
            leased = await uow.browser_sessions.leased_sessions()
        held = {
            str(recording.browser_session_id)
            for recording in capturing
            if recording.browser_session_id is not None
        }
        return held | leased | {str(session) for session in self._pursuits.sessions()}

    async def _forget(self, session_ids: list[str]) -> None:
        if not session_ids:
            return
        async with self._uow as uow:
            for session_id in session_ids:
                await uow.browser_sessions.release(BrowserSessionId(session_id))
            await uow.commit()
