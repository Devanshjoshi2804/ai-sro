"""Giving the browser back. This deployment has exactly one.

What was here before released nothing at all: it skipped every session the
provider could show a viewer for, and self-hosted Steel answers with one
deployment-wide debug URL for every live session. So the guard was true of all
of them, and an orphaned Chrome held the only browser for six hours while every
new session failed to launch against its profile lock.

Age is now read from the ownership claim rather than from whenever a sweep first
noticed the session. Two processes sweep and each kept its own first-seen map, so
a worker restart reset every clock -- a browser could outlive any grace period by
being noticed afresh forever.
"""

from __future__ import annotations

from sro.application.connection.browsers import Browsers
from sro.application.connection.release_strays import GRACE, ReleaseStrayBrowsers
from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.context import RequestContext
from sro.application.execution.pursuits import Pursuits
from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _reaper(
    uow: FakeUnitOfWork,
    browser: FakeBrowserProvider,
    clock: FakeClock,
    pursuits: Pursuits,
) -> ReleaseStrayBrowsers:
    return ReleaseStrayBrowsers(uow, browser, WatchBrowsers(browser), pursuits, clock)


async def test_a_browser_nobody_ever_claimed_is_litter_immediately() -> None:
    """Nothing this system runs opened it -- everything that opens a browser
    claims it now -- so it is left over from a crash or from before the record."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    session = await browser.open()

    released = await _reaper(uow, browser, clock, Pursuits()).execute()

    assert released == (str(session.id),)
    assert browser.closed == [session.id]


async def test_a_freshly_claimed_browser_gets_its_grace() -> None:
    """The work holding it registers in memory, in the other process. Young
    enough to belong to something in flight means leave it alone."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    browsers = Browsers(browser, uow, clock, FakeIdFactory())
    session = await browsers.open(CTX)

    early = await _reaper(uow, browser, clock, Pursuits()).execute()
    clock.advance(int(GRACE.total_seconds()) + 60)
    late = await _reaper(uow, browser, clock, Pursuits()).execute()

    assert early == ()
    assert late == (str(session.id),)


async def test_releasing_it_forgets_whose_it_was() -> None:
    """A claim outliving its session is a row a recycled id collides with, and
    the primary key would then refuse the caller who did nothing wrong."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    browsers = Browsers(browser, uow, clock, FakeIdFactory())
    await browsers.open(CTX)

    clock.advance(int(GRACE.total_seconds()) + 60)
    await _reaper(uow, browser, clock, Pursuits()).execute()

    assert uow.browser_sessions.rows == {}


async def test_a_pursuit_keeps_its_browser_however_long_it_takes() -> None:
    """Working a task out on the screen claims the browser it is working on."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    session = await Browsers(browser, uow, clock, FakeIdFactory()).open(CTX)
    pursuits = Pursuits()
    progress = pursuits.start("pur_1", "adjust an LPN", tenant_id=f.TENANT.value)
    progress.session_id = str(session.id)

    clock.advance(int(GRACE.total_seconds()) * 4)
    released = await _reaper(uow, browser, clock, pursuits).execute()

    assert released == ()
    assert browser.closed == []


async def test_a_demonstration_in_progress_keeps_its_browser() -> None:
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    session = await Browsers(browser, uow, clock, FakeIdFactory()).open(CTX)
    await uow.recordings.add(f.recording(browser_session_id=session.id))

    clock.advance(int(GRACE.total_seconds()) * 4)
    released = await _reaper(uow, browser, clock, pursuits=Pursuits()).execute()

    assert released == ()


async def test_the_steel_session_a_live_lease_runs_in_is_never_litter() -> None:
    """Every account on the container has its context inside that one
    session; releasing it would end all of them mid-run."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    session = await browser.open()
    now = clock.now()
    await uow.browser_sessions.lease(
        f.TENANT,
        Lease(
            "lse_1", Account.of(f.TENANT.value, "https://wms.example", "lena"),
            "http://steel:3000", str(session.id), "ctx_1", "run_1",
            now, now + K_LEASE_TTL, LeaseState.READY,
        ),
    )  # fmt: skip

    clock.advance(int(GRACE.total_seconds()) + 60)
    released = await _reaper(uow, browser, clock, Pursuits()).execute()

    assert released == ()
