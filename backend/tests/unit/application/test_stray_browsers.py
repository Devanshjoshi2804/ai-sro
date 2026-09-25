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

An expired lease is not simply dropped: whoever was signed in there may never
come back, so the sweep saves the signed-in state through the same path a
normal sign-in does (`SessionBroker._save_state`) before it lets the context
go -- and only for a lease its own `expire` compare-and-set actually won,
never one a beat has since revived.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.connection.browsers import Browsers
from sro.application.connection.release_strays import ReleaseStrayBrowsers
from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.context import RequestContext
from sro.application.runtime.broker import SessionBroker
from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from sro.domain.shared.identifiers import TenantId
from tests import factories as f
from tests.unit.fakes import (
    FakeAccountLocks,
    FakeBrowserPool,
    FakeBrowserProvider,
    FakeBrowserSessionRepository,
    FakeClock,
    FakeCredentialVault,
    FakeIdFactory,
    FakePageDriver,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import SigningLane, lease_for

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


class _RevivingBrowserSessions:
    """Wraps a `FakeBrowserSessionRepository`. The instant its `expired()` is
    read, the lease it found is beaten again, as a waiter racing the same
    sweep would -- so the sweep's own `expire` compare-and-set, made right
    after, loses."""

    def __init__(self, inner: FakeBrowserSessionRepository, clock: FakeClock) -> None:
        self._inner = inner
        self._clock = clock

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    async def expired(self, *, now: datetime) -> tuple[Lease, ...]:
        gone = await self._inner.expired(now=now)
        for lease in gone:
            await self._inner.beat(TenantId(lease.account.tenant), lease.id, now=self._clock.now())
        return gone


def _broker(
    uow: FakeUnitOfWork,
    pool: FakeBrowserPool,
    driver: FakePageDriver,
    vault: FakeCredentialVault,
    clock: FakeClock,
) -> SessionBroker:
    return SessionBroker(
        uow, pool, driver, FakeAccountLocks(), vault, clock, ui=SigningLane(driver)
    )


def _reaper(
    uow: FakeUnitOfWork,
    browser: FakeBrowserProvider,
    broker: SessionBroker,
    clock: FakeClock,
) -> ReleaseStrayBrowsers:
    return ReleaseStrayBrowsers(uow, browser, WatchBrowsers(browser), broker, clock)


async def test_a_browser_nobody_ever_claimed_is_litter_immediately() -> None:
    """Nothing this system runs opened it -- everything that opens a browser
    claims it now -- so it is left over from a crash or from before the record."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    broker = _broker(uow, FakeBrowserPool({}), FakePageDriver(), FakeCredentialVault(), clock)
    session = await browser.open()

    released = await _reaper(uow, browser, broker, clock).execute()

    assert released == (str(session.id),)
    assert browser.closed == [session.id]


async def test_releasing_it_forgets_whose_it_was() -> None:
    """A claim outliving its session is a row a recycled id collides with, and
    the primary key would then refuse the caller who did nothing wrong."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    broker = _broker(uow, FakeBrowserPool({}), FakePageDriver(), FakeCredentialVault(), clock)
    browsers = Browsers(browser, uow, clock, FakeIdFactory())
    await browsers.open(CTX)

    await _reaper(uow, browser, broker, clock).execute()

    assert uow.browser_sessions.rows == {}


async def test_a_demonstration_in_progress_keeps_its_browser() -> None:
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    broker = _broker(uow, FakeBrowserPool({}), FakePageDriver(), FakeCredentialVault(), clock)
    session = await Browsers(browser, uow, clock, FakeIdFactory()).open(CTX)
    await uow.recordings.add(f.recording(browser_session_id=session.id))

    released = await _reaper(uow, browser, broker, clock).execute()

    assert released == ()


async def test_the_steel_session_a_live_lease_runs_in_is_never_litter() -> None:
    """Every account on the container has its context inside that one
    session; releasing it would end all of them mid-run."""
    uow, browser, clock = FakeUnitOfWork(), FakeBrowserProvider(), FakeClock()
    broker = _broker(uow, FakeBrowserPool({}), FakePageDriver(), FakeCredentialVault(), clock)
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

    released = await _reaper(uow, browser, broker, clock).execute()

    assert released == ()


async def test_an_expired_lease_whose_session_answers_is_saved_then_closed() -> None:
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    driver.states[lease.context_id] = '{"cookies": ["lena"]}'
    broker = _broker(uow, pool, driver, vault, clock)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert lease.steel_session_id in released
    assert vault.secrets[lease.account.vault_key("state")] == '{"cookies": ["lena"]}'
    assert pool.closed == [("http://steel:3000", lease.context_id)]


async def test_an_expired_lease_whose_session_is_gone_is_closed_without_a_save() -> None:
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    driver.dead.add(lease.context_id)
    broker = _broker(uow, pool, driver, vault, clock)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert lease.steel_session_id in released
    assert lease.account.vault_key("state") not in vault.secrets
    assert pool.closed == [("http://steel:3000", lease.context_id)]


async def test_a_lease_whose_compare_and_set_loses_is_neither_saved_nor_closed() -> None:
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    uow.browser_sessions = _RevivingBrowserSessions(uow.browser_sessions, clock)  # type: ignore[assignment]
    broker = _broker(uow, pool, driver, vault, clock)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert released == ()
    assert pool.closed == []
    assert vault.secrets == {}
    still = await uow.browser_sessions.get_lease(TenantId(lease.account.tenant), lease.id)
    assert still is not None and still.state is LeaseState.READY


async def test_a_lease_that_keeps_beating_survives_any_number_of_sweeps() -> None:
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    broker = _broker(uow, pool, driver, vault, clock)
    lease = await lease_for(uow, clock, holder="run_1")
    for _ in range(20):
        clock.advance(60)
        async with uow:
            await uow.browser_sessions.beat(
                TenantId(lease.account.tenant), lease.id, now=clock.now()
            )
        assert await _reaper(uow, FakeBrowserProvider(), broker, clock).execute() == ()
