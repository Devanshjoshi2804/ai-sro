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

An expired lease is not simply dropped: for a READY lease whose session still
answers, the state is saved through the same path a normal sign-in does
(`SessionBroker._save_state`) BEFORE the sweep's own `expire` compare-and-set
is attempted, under the same time bound `_close` uses -- a lost compare-and-set
still only saved a live lease's own current state, which nothing overwrites
after. Only a compare-and-set this sweep actually wins goes on to close the
context, and only after the session's been resolved: one this sweep cannot
even reach is left alone entirely, to be retried on the next one.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sro.application.connection.browsers import Browsers
from sro.application.connection.release_strays import ReleaseStrayBrowsers
from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.context import RequestContext
from sro.application.runtime.broker import SessionBroker
from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from sro.domain.shared.identifiers import BrowserSessionId, TenantId
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
        uow, pool, driver, FakeAccountLocks(), vault, clock, ui=SigningLane(driver), close_s=0.05
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

    assert lease.context_id in released
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

    assert lease.context_id in released
    assert lease.account.vault_key("state") not in vault.secrets
    assert pool.closed == [("http://steel:3000", lease.context_id)]


async def test_a_lease_whose_compare_and_set_loses_is_saved_but_never_closed() -> None:
    """A lost compare-and-set means somebody else's beat revived it: the
    save that already ran only wrote that live lease's own current state,
    which is harmless -- nothing can overwrite a newer state saved by
    another worker's `_ready` after this."""
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    driver.states[lease.context_id] = '{"cookies": ["lena"]}'
    uow.browser_sessions = _RevivingBrowserSessions(uow.browser_sessions, clock)  # type: ignore[assignment]
    broker = _broker(uow, pool, driver, vault, clock)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert released == ()
    assert pool.closed == []
    assert vault.secrets[lease.account.vault_key("state")] == '{"cookies": ["lena"]}'
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


async def test_a_wedged_save_times_out_and_the_context_still_closes() -> None:
    """I1: the save is bounded the same way `_close` already is. A renderer
    that stops answering CDP must not stop the sweep, which the worker loop
    also drives confirmations and every other lease's expiry through."""
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    driver.storage_state_hangs = True
    lease = await lease_for(uow, clock, holder="run_1")
    broker = _broker(uow, pool, driver, vault, clock)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert lease.context_id in released
    assert lease.account.vault_key("state") not in vault.secrets
    assert pool.closed == [("http://steel:3000", lease.context_id)]


async def test_a_waiting_lease_that_lapsed_is_closed_but_never_saved() -> None:
    """M1: only a READY lease's state means the signed-in state. A WAITING
    lease sits on the one-time-code prompt; saving it would overwrite the
    vault's `state` key with a page that never finished signing in."""
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    async with uow:
        await uow.browser_sessions.settle(
            TenantId(lease.account.tenant), lease.id, state=LeaseState.WAITING
        )
        await uow.commit()
    driver.states[lease.context_id] = '{"cookies": ["mid-code"]}'
    broker = _broker(uow, pool, driver, vault, clock)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert lease.context_id in released
    assert lease.account.vault_key("state") not in vault.secrets
    assert pool.closed == [("http://steel:3000", lease.context_id)]


async def test_an_unreachable_container_is_skipped_this_sweep_and_retried_next() -> None:
    """M3: the session is resolved before the compare-and-set. Committing
    EXPIRED and then failing to reach the container would strand the lease
    -- no longer `expired()`'s to find, never closed."""
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    pool.down.add("http://steel:3000")
    broker = _broker(uow, pool, driver, vault, clock)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert released == ()
    assert pool.closed == []
    still = await uow.browser_sessions.get_lease(TenantId(lease.account.tenant), lease.id)
    assert still is not None and still.state is LeaseState.READY

    pool.down.clear()
    retried = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert lease.context_id in retried
    assert pool.closed == [("http://steel:3000", lease.context_id)]


async def test_a_context_this_sweep_just_closed_is_not_also_closed_as_a_stray() -> None:
    """M6: self-hosted Steel still lists the one shared session as open even
    after a context inside it is closed. Without the skip, the sweep would
    try to release the whole session through the legacy capture-browser
    path for a session a lease still names."""
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    lease = await lease_for(uow, clock, holder="run_1")
    broker = _broker(uow, pool, driver, vault, clock)
    browser = FakeBrowserProvider()
    browser.opened.append(BrowserSessionId(lease.steel_session_id))
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _reaper(uow, browser, broker, clock).execute()

    assert released == (lease.context_id,)
    assert browser.closed == []


async def test_a_sibling_lease_on_the_same_steel_session_is_untouched() -> None:
    """M6: two accounts on the same container share one Steel session but
    never a context. Expiring one must never touch the other's."""
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 2}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    broker = _broker(uow, pool, driver, vault, clock)
    dying = await lease_for(uow, clock, holder="run_1")
    now = clock.now()
    living = Lease(
        "lse_sibling", Account.of(f.TENANT.value, "https://wms.example", "omar"),
        dying.container_url, dying.steel_session_id, "ctx-sibling", "run_2",
        now, now + K_LEASE_TTL, LeaseState.READY,
    )  # fmt: skip
    async with uow:
        await uow.browser_sessions.lease(f.TENANT, living)
        await uow.commit()
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    async with uow:
        await uow.browser_sessions.beat(f.TENANT, living.id, now=clock.now())

    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert dying.context_id in released
    assert pool.closed == [(dying.container_url, dying.context_id)]
    still = await uow.browser_sessions.get_lease(f.TENANT, living.id)
    assert still is not None and still.state is LeaseState.READY


async def test_the_sweeper_never_closes_a_lease_resume_just_revived() -> None:
    """I2: `resume` settles READY with a fresh deadline, guarded on the old
    one not yet having passed, before it does anything else. Once that
    commits, the sweep -- run right after, at a time that would have been
    past the OLD deadline -- must find nothing to expire."""
    uow, clock = FakeUnitOfWork(), FakeClock()
    pool, driver, vault = (
        FakeBrowserPool({"http://steel:3000": 1}),
        FakePageDriver(),
        FakeCredentialVault(),
    )
    broker = _broker(uow, pool, driver, vault, clock)
    now = clock.now()
    lease = Lease(
        "lse_wait", Account.of(f.TENANT.value, "https://wms.example", "lena"),
        "http://steel:3000", "sess-1", "ctx-1", "run_1",
        now, now + timedelta(seconds=5), LeaseState.WAITING,
    )  # fmt: skip
    async with uow:
        await uow.browser_sessions.lease(f.TENANT, lease)
        await uow.commit()
    driver.tabs["tab-1"] = "https://wms.example/app"
    driver.owners["tab-1"] = lease.context_id

    held = await broker.resume(CTX, lease.id, "tab-1", "https://wms.example/app", holder="run_1")
    assert held.lease.state is LeaseState.READY

    clock.advance(10)
    released = await _reaper(uow, FakeBrowserProvider(), broker, clock).execute()

    assert released == ()
    assert pool.closed == []
