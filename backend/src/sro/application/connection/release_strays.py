from __future__ import annotations

from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.runtime.broker import SessionBroker
from sro.domain.shared.identifiers import BrowserSessionId, TenantId


class ReleaseStrayBrowsers:
    def __init__(
        self,
        uow: UnitOfWork,
        browser: BrowserProvider,
        watch: WatchBrowsers,
        broker: SessionBroker,
        clock: Clock,
    ) -> None:
        self._uow = uow
        self._browser = browser
        self._watch = watch
        self._broker = broker
        self._clock = clock

    async def execute(self) -> tuple[str, ...]:
        expired = await self._expired_leases()
        open_now = await self._watch.all_in_deployment()
        async with self._uow as uow:
            capturing = await uow.recordings.list_capturing()
            leased = await uow.browser_sessions.leased_sessions()
        in_use = {
            str(one.browser_session_id) for one in capturing if one.browser_session_id is not None
        }
        strays: list[str] = []
        for browser in open_now:
            if browser.session_id in in_use or browser.session_id in leased:
                continue
            if browser.session_id in expired:
                continue
            try:
                await self._browser.close(BrowserSessionId(browser.session_id))
            except BrowserUnavailable:
                continue
            strays.append(browser.session_id)
        async with self._uow as uow:
            claimed = [str(held) for held, _ in await uow.browser_sessions.all_held()]
        live = {browser.session_id for browser in open_now}
        await self._forget([*strays, *(one for one in claimed if one not in live)])
        return (*expired, *strays)

    async def _expired_leases(self) -> tuple[str, ...]:
        async with self._uow as uow:
            gone = await uow.browser_sessions.expired(now=self._clock.now())
        closed: list[str] = []
        for lease in gone:
            async with self._uow as uow:
                won = await uow.browser_sessions.expire(
                    TenantId(lease.account.tenant), lease.id, now=self._clock.now()
                )
                await uow.commit()
            if not won:
                continue
            await self._broker.end_expired(lease)
            closed.append(lease.steel_session_id)
        return tuple(closed)

    async def _forget(self, session_ids: list[str]) -> None:
        if not session_ids:
            return
        async with self._uow as uow:
            for session_id in session_ids:
                await uow.browser_sessions.release(BrowserSessionId(session_id))
            await uow.commit()
