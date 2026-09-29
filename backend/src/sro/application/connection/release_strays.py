from __future__ import annotations

import logging
from dataclasses import dataclass

from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.runtime.broker import SessionBroker
from sro.domain.shared.identifiers import BrowserSessionId, TenantId

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Expired:
    contexts: tuple[str, ...] = ()
    steel_sessions: tuple[str, ...] = ()


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
        expired = await self.expire_leases()
        strays = await self.close_strays(expired=expired.steel_sessions)
        return (*expired.contexts, *strays)

    async def expire_leases(self) -> Expired:
        async with self._uow as uow:
            gone = await uow.browser_sessions.expired(now=self._clock.now())
        contexts: list[str] = []
        steel_sessions: list[str] = []
        for lease in gone:
            if not await self._broker.prepare_to_expire(lease):
                continue
            async with self._uow as uow:
                won = await uow.browser_sessions.expire(
                    TenantId(lease.account.tenant), lease.id, now=self._clock.now()
                )
                await uow.commit()
            if not won:
                continue
            await self._broker.end_expired(lease)
            logger.info("closed context %s of lease %s", lease.context_id, lease.id)
            contexts.append(lease.context_id)
            steel_sessions.append(lease.steel_session_id)
        return Expired(tuple(contexts), tuple(steel_sessions))

    async def close_strays(self, *, expired: tuple[str, ...] = ()) -> tuple[str, ...]:
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
        return tuple(strays)

    async def _forget(self, session_ids: list[str]) -> None:
        if not session_ids:
            return
        async with self._uow as uow:
            for session_id in session_ids:
                await uow.browser_sessions.release(BrowserSessionId(session_id))
            await uow.commit()
