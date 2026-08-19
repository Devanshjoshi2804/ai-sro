"""Give the browser back when nobody is using it.

This deployment has one browser. A session that outlives whatever opened it --
a sign-in that failed halfway, a demonstration nobody finished, a process that
restarted -- keeps holding it, and everything afterwards fails with "no browser
available" for a reason nobody can see. One was found holding the slot with no
Chrome behind it at all.

What makes a session strays is not its age: it is that nothing in this system
claims it. A demonstration that is still open claims one. A pursuit driving a
screen claims one. Everything else is litter, and the provider itself says so --
a session it can no longer offer a viewer for has no browser attached.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.execution.pursuits import Pursuits
from sro.application.ports.browser import BrowserProvider, BrowserUnavailable
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.shared.identifiers import BrowserSessionId

GRACE = timedelta(minutes=15)
"""How long an unclaimed session is left alone before it is litter.

Not politeness: a claim is only visible to the process holding it. A pursuit
registers in memory in the API, and this sweep runs in the worker, so "nothing
claims it" is a statement this side cannot make about a browser that was opened
a second ago. It can make it about one that has been unclaimed for a quarter of
an hour, which is the case that actually holds the slot -- an operator's sign-in
window abandoned mid-login, a session whose process restarted underneath it.
"""


class ReleaseStrayBrowsers:
    def __init__(
        self,
        uow: UnitOfWork,
        browser: BrowserProvider,
        watch: WatchBrowsers,
        pursuits: Pursuits,
        clock: Clock,
        seen: dict[str, datetime] | None = None,
    ) -> None:
        self._uow = uow
        self._browser = browser
        self._watch = watch
        self._pursuits = pursuits
        self._clock = clock
        # Given from outside because a new instance of this is built for every
        # sweep; first-seen kept per instance would reset each time and no
        # session would ever reach the grace period.
        self._seen = {} if seen is None else seen

    async def execute(self) -> tuple[str, ...]:
        """Release what nothing claims. Returns what was given back."""
        open_now = await self._watch.execute()
        if not open_now:
            return ()

        claimed = await self._claimed()
        now = self._clock.now()
        # Sessions that are gone stop being remembered, or one that is opened
        # with a recycled id inherits somebody else's clock. Pruned in place:
        # this dict belongs to the caller, and rebinding it here would leave
        # every sweep starting from an empty one -- which is the state where
        # nothing is ever old enough to release.
        still_open = {browser.session_id for browser in open_now}
        for session in tuple(self._seen):
            if session not in still_open:
                del self._seen[session]

        released: list[str] = []
        for browser in open_now:
            if browser.session_id in claimed:
                # Claimed now is claimed afresh: a demonstration that ends and
                # is reopened must not inherit the age of the first one.
                self._seen.pop(browser.session_id, None)
                continue
            # This used to skip anything with a viewer, on the reading that a
            # viewer means somebody is watching. It does not: self-hosted Steel
            # answers with one deployment-wide debug URL for every live session,
            # so the guard was true of all of them and nothing was ever
            # released -- which is how an orphaned Chrome came to hold the only
            # browser for six hours.
            first_seen = self._seen.setdefault(browser.session_id, now)
            if now - first_seen < GRACE:
                continue
            try:
                await self._browser.close(BrowserSessionId(browser.session_id))
            except BrowserUnavailable:
                continue
            released.append(browser.session_id)
        return tuple(released)

    async def _claimed(self) -> set[str]:
        """Sessions this system is using: demonstrations, and pursuits."""
        async with self._uow as uow:
            capturing = await uow.recordings.list_capturing()
        held = {
            str(recording.browser_session_id)
            for recording in capturing
            if recording.browser_session_id is not None
        }
        return held | {str(session) for session in self._pursuits.sessions()}
