"""Give the browser back when nobody is using it.

This deployment has one browser. A session that outlives whatever opened it --
a sign-in that failed halfway, a demonstration nobody finished, a process that
restarted -- keeps holding it, and everything afterwards fails with "no browser
available" for a reason nobody can see. One was found holding the slot with no
Chrome behind it at all.

What makes a session stray is not its age: it is that nothing in this system
claims it. A demonstration that is still open claims one. A pursuit driving a
screen claims one. Every browser this system opens now claims one durably, in
``browser_sessions``, which is what makes the rest of this honest -- age used to
be measured from the first sweep that happened to notice a session, per process,
so a worker restart reset every clock and a browser could hold the slot forever.
"""

from __future__ import annotations

from datetime import timedelta

from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.execution.pursuits import Pursuits
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.shared.identifiers import BrowserSessionId

GRACE = timedelta(minutes=15)
"""How long a claimed browser nobody is using is left alone.

A claim says whose it is, not that anything is still doing something with it:
the pursuit that opened it registers in memory, in one process, and this sweep
runs in the other. So a claim young enough to belong to work in flight is left
alone, and one that has been idle for a quarter of an hour is the case that
actually holds the slot -- a sign-in window abandoned mid-login, a process that
restarted underneath its browser.

A session with no claim at all gets no grace. Nothing this system runs opened
it, and after the ownership record nothing ever will.
"""


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
        """Release what nothing claims. Returns what was given back."""
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
            # This used to skip anything with a viewer, on the reading that a
            # viewer means somebody is watching. It does not: self-hosted Steel
            # answers with one deployment-wide debug URL for every live session,
            # so the guard was true of all of them and nothing was ever
            # released -- which is how an orphaned Chrome came to hold the only
            # browser for six hours.
            claimed = opened_at.get(browser.session_id)
            if claimed is not None and now - claimed < GRACE:
                continue
            try:
                await self._browser.close(BrowserSessionId(browser.session_id))
            except BrowserUnavailable:
                continue
            released.append(browser.session_id)

        await self._forget(released)
        # Claims whose session the provider no longer has. Unreachable either
        # way -- every read intersects with what is live -- but a row kept
        # forever is a row a recycled id one day collides with.
        live = {browser.session_id for browser in open_now}
        await self._forget([held for held in opened_at if held not in live])
        return tuple(released)

    async def _in_use(self) -> set[str]:
        """Sessions something is doing something with: demonstrations, pursuits."""
        async with self._uow as uow:
            capturing = await uow.recordings.list_capturing()
        held = {
            str(recording.browser_session_id)
            for recording in capturing
            if recording.browser_session_id is not None
        }
        return held | {str(session) for session in self._pursuits.sessions()}

    async def _forget(self, session_ids: list[str]) -> None:
        if not session_ids:
            return
        async with self._uow as uow:
            for session_id in session_ids:
                await uow.browser_sessions.release(BrowserSessionId(session_id))
            await uow.commit()
