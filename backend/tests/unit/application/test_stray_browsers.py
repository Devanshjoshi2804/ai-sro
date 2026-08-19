"""Giving the browser back. This deployment has exactly one.

What was here before released nothing at all: it skipped every session the
provider could show a viewer for, and self-hosted Steel answers with one
deployment-wide debug URL for every live session. So the guard was true of all
of them, and an orphaned Chrome held the only browser for six hours while every
new session failed to launch against its profile lock.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.connection.release_strays import GRACE, ReleaseStrayBrowsers
from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.execution.pursuits import Pursuits
from tests import factories as f
from tests.unit.fakes import FakeBrowserProvider, FakeClock, FakeUnitOfWork


def _reaper(
    uow: FakeUnitOfWork,
    browser: FakeBrowserProvider,
    clock: FakeClock,
    pursuits: Pursuits,
    seen: dict[str, datetime],
) -> ReleaseStrayBrowsers:
    """Built per sweep, exactly as the container builds it: first-seen has to
    live outside the instance or nothing ever reaches the grace period."""
    return ReleaseStrayBrowsers(uow, browser, WatchBrowsers(browser), pursuits, clock, seen)


async def test_a_browser_nobody_claims_is_given_back_once_it_is_plainly_litter() -> None:
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    seen: dict[str, datetime] = {}
    session = await browser.open()

    early = await _reaper(uow, browser, clock, Pursuits(), seen).execute()
    clock.advance(int(GRACE.total_seconds()) + 60)
    late = await _reaper(uow, browser, clock, Pursuits(), seen).execute()

    assert early == (), "a browser opened a moment ago is somebody's, in another process"
    assert late == (str(session.id),)
    assert browser.closed == [session.id]


async def test_a_pursuit_keeps_its_browser_however_long_it_takes() -> None:
    """Working a task out on the screen claims the browser it is working on."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    seen: dict[str, datetime] = {}
    session = await browser.open()
    pursuits = Pursuits()
    progress = pursuits.start("pur_1", "adjust an LPN", tenant_id=f.TENANT.value)
    progress.session_id = str(session.id)

    clock.advance(int(GRACE.total_seconds()) * 4)
    released = await _reaper(uow, browser, clock, pursuits, seen).execute()

    assert released == ()
    assert browser.closed == []


async def test_a_demonstration_in_progress_keeps_its_browser() -> None:
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    seen: dict[str, datetime] = {}
    session = await browser.open()
    await uow.recordings.add(f.recording(browser_session_id=session.id))

    clock.advance(int(GRACE.total_seconds()) * 4)
    released = await _reaper(uow, browser, clock, pursuits=Pursuits(), seen=seen).execute()

    assert released == ()
