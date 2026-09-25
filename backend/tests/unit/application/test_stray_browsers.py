"""Giving the browser back. This deployment has exactly one.

What was here before released nothing at all: it skipped every session the
provider could show a viewer for, and self-hosted Steel answers with one
deployment-wide debug URL for every live session. So the guard was true of all
of them, and an orphaned Chrome held the only browser for six hours while every
new session failed to launch against its profile lock.

A browser is now held exactly while its lease is live: no in-memory list of
who is working (that was one process's memory, and a worker restart forgot
it), no flat grace window either -- a lease that keeps beating survives any
number of sweeps, and one that stops is swept the moment it expires, not
fifteen minutes later.
"""

from __future__ import annotations

from sro.application.connection.browsers import Browsers
from sro.application.connection.release_strays import ReleaseStrayBrowsers
from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.context import RequestContext
from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from sro.domain.shared.identifiers import TenantId
from tests import factories as f
from tests.unit.fakes import (
    FakeBrowserPool,
    FakeBrowserProvider,
    FakeClock,
    FakeIdFactory,
    FakePageDriver,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import lease_for

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _reaper(
    uow: FakeUnitOfWork,
    browser: FakeBrowserProvider,
    pool: FakeBrowserPool,
    driver: FakePageDriver,
    clock: FakeClock,
) -> ReleaseStrayBrowsers:
    return ReleaseStrayBrowsers(uow, browser, WatchBrowsers(browser), pool, driver, clock)


async def test_a_browser_nobody_ever_claimed_is_litter_immediately() -> None:
    """Nothing this system runs opened it -- everything that opens a browser
    claims it now -- so it is left over from a crash or from before the record."""
    uow, browser, pool, driver, clock = (
        FakeUnitOfWork(),
        FakeBrowserProvider(),
        FakeBrowserPool({}),
        FakePageDriver(),
        FakeClock(),
    )
    session = await browser.open()

    released = await _reaper(uow, browser, pool, driver, clock).execute()

    assert released == (str(session.id),)
    assert browser.closed == [session.id]


async def test_releasing_it_forgets_whose_it_was() -> None:
    """A claim outliving its session is a row a recycled id collides with, and
    the primary key would then refuse the caller who did nothing wrong."""
    uow, browser, pool, driver, clock = (
        FakeUnitOfWork(),
        FakeBrowserProvider(),
        FakeBrowserPool({}),
        FakePageDriver(),
        FakeClock(),
    )
    browsers = Browsers(browser, uow, clock, FakeIdFactory())
    await browsers.open(CTX)

    await _reaper(uow, browser, pool, driver, clock).execute()

    assert uow.browser_sessions.rows == {}


async def test_a_demonstration_in_progress_keeps_its_browser() -> None:
    uow, browser, pool, driver, clock = (
        FakeUnitOfWork(),
        FakeBrowserProvider(),
        FakeBrowserPool({}),
        FakePageDriver(),
        FakeClock(),
    )
    session = await Browsers(browser, uow, clock, FakeIdFactory()).open(CTX)
    await uow.recordings.add(f.recording(browser_session_id=session.id))

    released = await _reaper(uow, browser, pool, driver, clock).execute()

    assert released == ()


async def test_the_steel_session_a_live_lease_runs_in_is_never_litter() -> None:
    """Every account on the container has its context inside that one
    session; releasing it would end all of them mid-run."""
    uow, browser, pool, driver, clock = (
        FakeUnitOfWork(),
        FakeBrowserProvider(),
        FakeBrowserPool({}),
        FakePageDriver(),
        FakeClock(),
    )
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

    released = await _reaper(uow, browser, pool, driver, clock).execute()

    assert released == ()


async def test_a_lease_that_stopped_beating_is_released_and_its_browser_closed() -> None:
    uow, pool, driver, clock = (
        FakeUnitOfWork(),
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeClock(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), pool, driver, clock).execute()

    assert lease.steel_session_id in released
    assert pool.closed == [("http://steel:3000", lease.context_id)]


async def test_a_lease_that_keeps_beating_survives_any_number_of_sweeps() -> None:
    uow, pool, driver, clock = (
        FakeUnitOfWork(),
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeClock(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    for _ in range(20):
        clock.advance(60)
        async with uow:
            await uow.browser_sessions.beat(
                TenantId(lease.account.tenant), lease.id, now=clock.now()
            )
        assert await _reaper(uow, FakeBrowserProvider(), pool, driver, clock).execute() == ()
