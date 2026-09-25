import asyncio
from datetime import timedelta

import pytest

from sro.application.connection.refusals import CodeAsked
from sro.application.context import RequestContext
from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone, SessionRef
from sro.application.ports.pool import PoolFull
from sro.application.runtime.broker import K_CODE_WAIT, SessionBroker
from sro.application.runtime.step import Held, NeedsAPerson, WaitingForAPerson
from sro.domain.execution.account import (
    K_LEASE_TTL,
    K_VAULT_VALUE_BYTES,
    Account,
    Lease,
    LeaseState,
)
from sro.domain.execution.lanes import SeenCall
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.signing_in import PageSignals
from sro.interface.http.schemas import NewSecretRequest
from sro.interface.http.v1.routers.secrets import _key_for
from tests.unit.fakes import (
    FakeAccountLocks,
    FakeBrowserPool,
    FakeClock,
    FakeCredentialVault,
    FakePageDriver,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import IDP, SigningLane, with_a_recorded_sign_in

CTX = RequestContext(TenantId("greyorange"), PrincipalId("op"))
ACME = RequestContext(TenantId("acme"), PrincipalId("op"))
APP = "https://wms.example/app"
LENA = Account.of("greyorange", IDP, "lena")
OMAR = Account.of("greyorange", IDP, "omar")
STEEL = "http://steel:3000"
PASSWORD = "not-a-real-secret"  # noqa: S105 -- a test value, never a credential
WRONG = "wrong"


def _broker(
    uow: FakeUnitOfWork,
    driver: FakePageDriver,
    vault: FakeCredentialVault,
    lane: SigningLane | None = None,
    *,
    pool: FakeBrowserPool | None = None,
    clock: FakeClock | None = None,
) -> SessionBroker:
    return SessionBroker(
        uow,
        pool or FakeBrowserPool({STEEL: 1}),
        driver,
        FakeAccountLocks(),
        vault,
        clock or FakeClock(),
        ui=lane or SigningLane(driver),
        close_s=0.05,
    )


async def _signing_world(
    password: str = PASSWORD,
) -> tuple[FakeUnitOfWork, FakePageDriver, FakeCredentialVault]:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await with_a_recorded_sign_in(uow, lands_on=APP, username="lena")
    await vault.store(LENA.vault_key("password"), password)
    driver.shows_sign_in_until_signed = True
    return uow, driver, vault


async def test_a_restored_state_that_holds_signs_nobody_in() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await vault.store(LENA.vault_key("state"), '{"cookies": []}')
    lane = SigningLane(driver)

    held = await _broker(uow, driver, vault, lane).acquire(CTX, LENA, APP, holder="run_1")

    assert held.lease.state is LeaseState.READY
    assert lane.stepped == []
    assert ("restore_state", held.session.context_id, '{"cookies": []}') in driver.calls
    assert driver.tabs[held.target_id] == APP


async def test_a_sign_in_page_is_signed_through_with_the_vault_password() -> None:
    uow, driver, vault = await _signing_world()
    lane = SigningLane(driver)

    held = await _broker(uow, driver, vault, lane).acquire(CTX, LENA, APP, holder="run_1")

    assert lane.stepped == [0, 1, 2]
    assert lane.secret_seen == PASSWORD
    assert await vault.get(LENA.vault_key("state")) is not None
    assert held.lease.state is LeaseState.READY
    assert driver.tabs[held.target_id] == APP


async def test_two_runs_on_one_account_share_one_lease_as_two_tabs() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    broker = _broker(uow, driver, vault)

    one = await broker.acquire(CTX, LENA, APP, holder="run_1")
    two = await broker.acquire(CTX, LENA, APP, holder="run_2")

    assert one.lease.id == two.lease.id
    assert one.target_id != two.target_id
    assert one.session == two.session


async def test_a_form_that_comes_back_latches_the_password_and_asks() -> None:
    uow, driver, vault = await _signing_world(password=WRONG)
    driver.refuses = True
    pool = FakeBrowserPool({STEEL: 1})

    with pytest.raises(NeedsAPerson) as asked:
        await _broker(uow, driver, vault, pool=pool).acquire(CTX, LENA, APP, holder="run_1")

    assert asked.value.kind == "password"
    assert await vault.get(LENA.vault_key("password") + "#refused") is not None
    assert await vault.get(LENA.vault_key("state")) is None
    (lease,) = uow.browser_sessions.leases.values()
    assert lease.state is LeaseState.READY, "a person is needed; the context is not broken"
    assert pool.closed == []


async def test_a_refused_password_is_never_typed_again() -> None:
    uow, driver, vault = await _signing_world(password=WRONG)
    driver.refuses = True
    with pytest.raises(NeedsAPerson):
        await _broker(uow, driver, vault).acquire(CTX, LENA, APP, holder="run_1")
    lane = SigningLane(driver)
    broker = _broker(uow, driver, vault, lane)
    held = await broker.acquire(CTX, LENA, APP, holder="run_2")

    with pytest.raises(NeedsAPerson) as asked:
        await broker.reauth(CTX, held, APP)

    assert asked.value.kind == "password"
    assert lane.stepped == []


async def _asked_for_a_code(
    uow: FakeUnitOfWork, driver: FakePageDriver, broker: SessionBroker
) -> Held:
    driver.shows_sign_in_until_signed = False
    driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))
    with pytest.raises(WaitingForAPerson) as asked:
        await broker.acquire(CTX, LENA, APP, holder="run_1")
    assert asked.value.kind == "code"
    return asked.value.held


async def test_a_one_time_code_keeps_its_page_open_and_its_account_while_a_person_answers() -> None:
    uow, driver, vault = await _signing_world()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    asked_at = clock.now()
    waiting = await _asked_for_a_code(uow, driver, broker)
    lease = uow.browser_sessions.leases[waiting.lease.id]
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    assert await broker.beat(CTX, lease.id, holder="run_2")
    with pytest.raises(AccountBusy):
        await broker.acquire(CTX, LENA, APP, holder="run_2")
    with pytest.raises(WaitingForAPerson):
        await broker.resume(CTX, lease.id, waiting.target_id, APP, holder="run_1")

    assert lease.state is LeaseState.WAITING
    assert lease.expires_at == waiting.lease.expires_at == asked_at + K_CODE_WAIT
    assert uow.browser_sessions.leases[lease.id].state is LeaseState.WAITING
    assert uow.browser_sessions.leases[lease.id].expires_at == lease.expires_at
    assert waiting.target_id in driver.tabs
    assert pool.closed == []

    driver.signals_for_every_tab = PageSignals(APP)
    held = await broker.resume(CTX, lease.id, waiting.target_id, APP, holder="run_1")

    assert held.lease.state is LeaseState.READY
    assert held.target_id == waiting.target_id
    assert await vault.get(LENA.vault_key("state")) is not None
    assert (await broker.acquire(CTX, LENA, APP, holder="run_2")).lease.id == lease.id


async def test_a_code_nobody_answers_in_time_is_taken_over() -> None:
    uow, driver, vault = await _signing_world()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    waiting = await _asked_for_a_code(uow, driver, broker)
    clock.advance(int(K_CODE_WAIT.total_seconds()) + 1)
    driver.signals_for_every_tab = PageSignals(APP)

    held = await broker.acquire(CTX, LENA, APP, holder="run_2")

    assert uow.browser_sessions.leases[waiting.lease.id].state is LeaseState.EXPIRED
    assert held.lease.id != waiting.lease.id
    assert (STEEL, waiting.session.context_id) in pool.closed


class _JumpsTheClockOnSignals:
    """Wraps a `FakePageDriver`. `signals` advances the clock before
    answering, the way real time passing during a page probe would -- a
    deterministic way to land the clock past a deadline strictly between
    `resume`'s own `lease.live(now)` check and its later `settle`, a gap no
    synchronous test can otherwise open."""

    def __init__(self, inner: FakePageDriver, clock: FakeClock, by: timedelta) -> None:
        self._inner = inner
        self._clock = clock
        self._by = by

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    async def signals(self, session: SessionRef, target_id: str) -> PageSignals:
        self._clock.advance(int(self._by.total_seconds()))
        return await self._inner.signals(session, target_id)


class _ForcedAnswers:
    """Wraps a `BrowserSessionRepository`, forcing `settle` and/or `beat` to
    a fixed answer regardless of the store's own -- to test what a caller
    does with a `False` it did not itself cause."""

    def __init__(
        self, inner: object, *, settle: bool | None = None, beat: bool | None = None
    ) -> None:
        self._inner = inner
        self._settle = settle
        self._beat = beat

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    async def settle(self, *args: object, **kwargs: object) -> bool:
        if self._settle is not None:
            return self._settle
        return await self._inner.settle(*args, **kwargs)

    async def beat(self, *args: object, **kwargs: object) -> bool:
        if self._beat is not None:
            return self._beat
        return await self._inner.beat(*args, **kwargs)


async def test_the_deadline_passing_before_resumes_settle_is_pagegone_and_never_gotos() -> None:
    """I2 (re-review): the deadline passes strictly between the live check
    and the settle, not before either -- otherwise `resume` would already
    have taken the fresh-acquire branch. Only the guarded `settle` catches
    this, and `goto` (which comes after it) must never run."""
    uow, driver, vault = await _signing_world()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    waiting = await _asked_for_a_code(uow, driver, broker)
    driver.signals_for_every_tab = PageSignals(APP)
    jumpy = _JumpsTheClockOnSignals(
        driver, clock, timedelta(seconds=int(K_CODE_WAIT.total_seconds()) + 1)
    )
    resuming = _broker(uow, jumpy, vault, SigningLane(driver), pool=pool, clock=clock)

    with pytest.raises(PageGone):
        await resuming.resume(CTX, waiting.lease.id, waiting.target_id, APP, holder="run_1")

    assert not any(call[0] == "goto" for call in driver.calls)
    assert uow.browser_sessions.leases[waiting.lease.id].state is LeaseState.WAITING


async def test_resume_raises_pagegone_when_its_settle_is_refused() -> None:
    """Whatever the store's reason -- lost the race, wrong tenant, gone --
    a `False` settle is `PageGone`, and `goto` (which comes after it) never
    runs on a lease `resume` no longer holds."""
    uow, driver, vault = await _signing_world()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    waiting = await _asked_for_a_code(uow, driver, broker)
    driver.signals_for_every_tab = PageSignals(APP)
    uow.browser_sessions = _ForcedAnswers(uow.browser_sessions, settle=False)  # type: ignore[assignment]

    with pytest.raises(PageGone):
        await broker.resume(CTX, waiting.lease.id, waiting.target_id, APP, holder="run_1")

    assert not any(call[0] == "goto" for call in driver.calls)


async def test_resume_raises_pagegone_when_its_beat_is_refused() -> None:
    """The settle already committed READY by the time `beat` is asked, so a
    `False` beat here means the lease was lost between them -- `PageGone`,
    even though `goto` already ran against a context this call no longer
    holds."""
    uow, driver, vault = await _signing_world()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    waiting = await _asked_for_a_code(uow, driver, broker)
    driver.signals_for_every_tab = PageSignals(APP)
    uow.browser_sessions = _ForcedAnswers(uow.browser_sessions, beat=False)  # type: ignore[assignment]

    with pytest.raises(PageGone):
        await broker.resume(CTX, waiting.lease.id, waiting.target_id, APP, holder="run_1")

    assert any(call[0] == "goto" for call in driver.calls)
    assert uow.browser_sessions.leases[waiting.lease.id].state is LeaseState.READY


async def test_resume_past_its_deadline_goes_through_a_fresh_acquire_never_back_to_ready() -> None:
    uow, driver, vault = await _signing_world()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    waiting = await _asked_for_a_code(uow, driver, broker)
    clock.advance(int(K_CODE_WAIT.total_seconds()) + 1)
    driver.signals_for_every_tab = PageSignals(APP)

    held = await broker.resume(CTX, waiting.lease.id, waiting.target_id, APP, holder="run_1")

    assert uow.browser_sessions.leases[waiting.lease.id].state is LeaseState.EXPIRED
    assert held.lease.id != waiting.lease.id
    assert held.lease.state is LeaseState.READY


async def test_resume_when_the_code_page_now_shows_a_password_asks_for_a_password_not_a_code() -> (
    None
):
    uow, driver, vault = await _signing_world()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    waiting = await _asked_for_a_code(uow, driver, broker)
    driver.signals_for_every_tab = PageSignals(APP, password=True)

    with pytest.raises(NeedsAPerson) as asked:
        await broker.resume(CTX, waiting.lease.id, waiting.target_id, APP, holder="run_1")

    assert asked.value.kind == "password"
    assert uow.browser_sessions.leases[waiting.lease.id].state is LeaseState.WAITING


async def test_no_stored_password_asks_for_one_and_types_nothing() -> None:
    uow, driver, vault = await _signing_world()
    await vault.delete(LENA.vault_key("password"))
    lane = SigningLane(driver)

    with pytest.raises(NeedsAPerson) as asked:
        await _broker(uow, driver, vault, lane).acquire(CTX, LENA, APP, holder="run_1")

    assert asked.value.kind == "password"
    assert lane.stepped == []


async def test_a_sign_in_recorded_as_someone_else_is_never_replayed_for_this_account() -> None:
    uow, driver, vault = await _signing_world()
    omar = Account.of("greyorange", IDP, "omar")
    await vault.store(omar.vault_key("password"), "omars-secret")
    lane = SigningLane(driver)

    with pytest.raises(NeedsAPerson):
        await _broker(uow, driver, vault, lane).acquire(CTX, omar, APP, holder="run_1")

    assert lane.stepped == []


async def test_the_account_is_keyed_where_the_password_is_typed_as_the_panel_stores_it() -> None:
    uow, driver, vault = await _signing_world()

    account = await _broker(uow, driver, vault).account_for(CTX, APP)

    stored = _key_for(
        "greyorange",
        NewSecretRequest(system=IDP, field="password", value="x", username="lena"),
    )
    assert account == LENA
    assert account.vault_key("password") == stored


async def test_no_recorded_sign_in_or_no_username_asks_rather_than_guesses() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    with pytest.raises(NeedsAPerson):
        await _broker(uow, driver, vault).account_for(CTX, APP)

    await with_a_recorded_sign_in(uow, lands_on=APP, username=None)
    with pytest.raises(NeedsAPerson):
        await _broker(uow, driver, vault).account_for(CTX, APP)


async def test_an_expired_lease_is_taken_over_on_its_own_container_and_its_context_closed() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool, clock = FakeBrowserPool({STEEL: 5, "http://steel-2:3000": 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    await broker.acquire(CTX, Account.of("greyorange", IDP, "omar"), APP, holder="run_1")
    first = await broker.acquire(CTX, LENA, APP, holder="run_2")
    assert first.lease.container_url == "http://steel-2:3000"
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    opened = len(driver.calls)

    second = await broker.acquire(CTX, LENA, APP, holder="run_3")

    assert second.lease.id != first.lease.id
    assert second.lease.container_url == first.lease.container_url
    assert uow.browser_sessions.leases[first.lease.id].state is LeaseState.EXPIRED
    assert (first.lease.container_url, first.lease.context_id) in pool.closed
    assert ("open_tab", first.session.context_id) not in {
        call[:2] for call in driver.calls[opened:]
    }


async def test_a_hung_close_never_holds_up_the_account() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    await broker.acquire(CTX, LENA, APP, holder="run_1")
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    pool.closes_hang = True

    held = await asyncio.wait_for(broker.acquire(CTX, LENA, APP, holder="run_2"), timeout=2)

    assert held.lease.state is LeaseState.READY


async def test_a_state_over_the_vault_limit_is_not_saved() -> None:
    uow, driver, vault = await _signing_world()
    broker = _broker(uow, driver, vault)
    driver.states["ctx_1"] = "x" * (K_VAULT_VALUE_BYTES + 1)

    held = await broker.acquire(CTX, LENA, APP, holder="run_1")

    assert held.session.context_id == "ctx_1"
    assert await vault.get(LENA.vault_key("state")) is None


async def test_reattach_finds_the_tab_and_a_dead_lease_or_tab_is_page_gone() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    clock = FakeClock()
    broker = _broker(uow, driver, vault, clock=clock)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")

    assert await broker.reattach(CTX, held.lease.id, held.target_id) == held
    with pytest.raises(PageGone):
        await broker.reattach(CTX, held.lease.id, "tab-99")
    await broker.release(CTX, held)
    with pytest.raises(PageGone):
        await broker.reattach(CTX, held.lease.id, held.target_id)
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    with pytest.raises(PageGone):
        await broker.reattach(CTX, held.lease.id, held.target_id)


async def test_a_beat_says_whether_the_holder_still_has_the_lease() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    clock = FakeClock()
    broker = _broker(uow, driver, vault, clock=clock)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")

    assert await broker.beat(CTX, held.lease.id, holder="run_1") is True
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    await uow.browser_sessions.expire(CTX.tenant_id, held.lease.id, now=clock.now())
    assert await broker.beat(CTX, held.lease.id, holder="run_1") is False


async def test_the_api_lane_is_handed_the_session_s_cookie_and_token() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    driver.cookie = "sid=abc"
    driver.headers = {"x-csrf-token": "t1"}
    broker = _broker(uow, driver, vault)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")

    said = await broker.headers(CTX, held, "https://wms.example")

    assert said == {"cookie": "sid=abc", "x-csrf-token": "t1"}


async def test_a_fresh_token_is_one_the_page_sent_after_the_reload() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    driver.headers = {"x-csrf-token": "t2"}
    broker = _broker(uow, driver, vault)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    mark = driver.mark

    async def marking(session: SessionRef, target_id: str) -> int:
        at = await mark(session, target_id)
        driver.calls.append(("mark", at))
        return at

    driver.mark = marking  # type: ignore[method-assign]
    driver.calls.clear()

    await broker.headers(CTX, held, "https://wms.example/app", fresh=True)

    names = [call[0] for call in driver.calls]
    assert names.index("mark") < names.index("goto") < names.index("headers_for")
    at = driver.calls[names.index("mark")][1]
    assert driver.calls[names.index("headers_for")][-1] == at


async def test_the_lease_names_the_steel_session_and_the_context_apart() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool = FakeBrowserPool({STEEL: 5})

    held = await _broker(uow, driver, vault, pool=pool).acquire(CTX, LENA, APP, holder="run_1")

    assert held.lease.steel_session_id == pool.session_id
    assert held.lease.context_id == held.session.context_id != pool.session_id
    assert await uow.browser_sessions.leased_sessions() == frozenset({pool.session_id})


async def test_a_crashed_context_is_settled_broken_and_the_account_moves_to_a_fresh_one() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    first = await broker.acquire(CTX, LENA, APP, holder="run_1")
    driver.dead.add(first.session.context_id)
    pool.dead.add(first.session.context_id)
    clock.advance(10)

    second = await broker.acquire(CTX, LENA, APP, holder="run_2")

    old = uow.browser_sessions.leases[first.lease.id]
    assert old.state is LeaseState.BROKEN
    assert old.expires_at == first.lease.expires_at
    assert second.lease.state is LeaseState.READY
    assert second.session.context_id not in {first.session.context_id}
    assert driver.tabs[second.target_id] == APP


async def test_a_lease_whose_container_left_the_pool_config_is_settled_broken_not_crashed() -> None:
    """Minor (S9 re-review round 3): a container the pool config no longer
    names can never be closed -- its context left with it, and `cdp_url`
    raises `KeyError` for it, not `BrowserUnavailable`. `_close` must treat
    that as the context already being gone: settle BROKEN, log, and never
    let the `KeyError` reach the caller trying to replace the lease."""
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    now = clock.now()
    stale = Lease(
        "lse_stale", LENA, "gone-container", "sess-gone", "ctx-gone", "run_0",
        now - timedelta(minutes=20), now - timedelta(minutes=10), LeaseState.WAITING,
    )  # fmt: skip
    async with uow:
        await uow.browser_sessions.lease(TenantId("greyorange"), stale)
        await uow.commit()
    pool.unknown.add("gone-container")
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)

    held = await broker.acquire(CTX, LENA, APP, holder="run_1")

    assert held.lease.id != stale.id
    assert held.lease.state is LeaseState.READY
    assert uow.browser_sessions.leases[stale.id].state is LeaseState.EXPIRED


class _FlakyTab:
    """Delegates to `driver`, except that `open_tab` for `context_id` raises
    `PageGone` `fails` times before it succeeds -- a busy Chrome that fails
    to attach a tab in time, or a crashed renderer, while the context itself
    survives (S7 rereview, N1)."""

    def __init__(self, driver: FakePageDriver, context_id: str, *, fails: int) -> None:
        self._driver = driver
        self._context_id = context_id
        self._left = fails

    def __getattr__(self, name: str) -> object:
        return getattr(self._driver, name)

    async def open_tab(self, session: SessionRef, url: str) -> str:
        if self._left > 0 and session.context_id == self._context_id:
            self._left -= 1
            raise PageGone(f"context {self._context_id} did not attach a tab in time")
        return await self._driver.open_tab(session, url)


async def test_a_page_gone_context_the_pool_still_lists_survives_with_a_new_tab() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    first = await broker.acquire(CTX, LENA, APP, holder="run_1")
    sibling = await broker.acquire(CTX, LENA, APP, holder="run_1b")
    clock.advance(10)
    # Two failures: one for `acquire`'s own attach outside the lock, one for
    # `_ready`'s retry under it -- the third call, from the fix, succeeds.
    flaky = _FlakyTab(driver, first.session.context_id, fails=2)
    flaky_broker = _broker(uow, flaky, vault, pool=pool, clock=clock)

    third = await flaky_broker.acquire(CTX, LENA, APP, holder="run_2")

    lease = uow.browser_sessions.leases[first.lease.id]
    assert lease.state is LeaseState.READY
    assert third.lease.id == first.lease.id
    assert third.session.context_id == first.session.context_id
    assert third.target_id not in {first.target_id, sibling.target_id}
    assert (STEEL, first.session.context_id) not in pool.closed
    still_there = await broker.reattach(CTX, sibling.lease.id, sibling.target_id)
    assert still_there.target_id == sibling.target_id
    assert still_there.session == sibling.session


async def test_a_signing_in_lease_found_under_the_lock_is_an_orphan_and_is_replaced_now() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    now = clock.now()
    orphan = Lease(
        "lse_orphan", LENA, STEEL, pool.session_id, "ctx_orphan", "run_0",
        now, now + K_LEASE_TTL, LeaseState.SIGNING_IN,
    )  # fmt: skip
    await uow.browser_sessions.lease(CTX.tenant_id, orphan)

    held = await _broker(uow, driver, vault, pool=pool, clock=clock).acquire(
        CTX, LENA, APP, holder="run_1"
    )

    assert uow.browser_sessions.leases["lse_orphan"].state is LeaseState.BROKEN
    assert held.lease.id != "lse_orphan"
    assert held.lease.state is LeaseState.READY
    assert (STEEL, "ctx_orphan") in pool.closed


async def test_a_context_a_dead_lease_left_behind_is_reclaimed_and_no_other_is() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool, clock = FakeBrowserPool({STEEL: 5}), FakeClock()
    broker = _broker(uow, driver, vault, pool=pool, clock=clock)
    omar = await broker.acquire(CTX, OMAR, APP, holder="run_1")
    now = clock.now()
    left = Lease(
        "lse_left", LENA, STEEL, pool.session_id, "ctx_left", "run_0",
        now, now + K_LEASE_TTL, LeaseState.SIGNING_IN,
    )  # fmt: skip
    await uow.browser_sessions.lease(CTX.tenant_id, left)
    await uow.browser_sessions.settle(CTX.tenant_id, "lse_left", state=LeaseState.BROKEN)
    pool.opened += [(STEEL, "ctx_left"), (STEEL, "ctx_another_process")]

    await broker.acquire(CTX, LENA, APP, holder="run_2")

    assert (STEEL, "ctx_left") in pool.closed
    assert (STEEL, "ctx_another_process") not in pool.closed
    assert (STEEL, omar.session.context_id) not in pool.closed


async def test_a_container_is_full_by_every_tenants_live_leases() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    broker = _broker(uow, driver, vault, pool=FakeBrowserPool({STEEL: 1}))
    await broker.acquire(ACME, Account.of("acme", IDP, "ann"), APP, holder="run_1")

    with pytest.raises(PoolFull):
        await broker.acquire(CTX, LENA, APP, holder="run_2")


async def test_the_tab_handed_to_the_first_run_keeps_no_call_from_the_sign_in() -> None:
    uow, driver, vault = await _signing_world()
    driver._log = [(0, SeenCall("POST", f"{IDP}/login", 200, request_body="password=x"))]

    held = await _broker(uow, driver, vault).acquire(CTX, LENA, APP, holder="run_1")

    assert await driver.calls_since(held.session, held.target_id, -1) == ()


async def test_a_settle_that_fails_still_closes_the_context() -> None:
    uow, driver, vault = await _signing_world(password=WRONG)
    driver.refuses = True
    pool = FakeBrowserPool({STEEL: 1})

    async def down(*_: object, **__: object) -> bool:
        raise ConnectionError("the database is down")

    uow.browser_sessions.settle = down  # type: ignore[method-assign]

    with pytest.raises(ConnectionError):
        await _broker(uow, driver, vault, pool=pool).acquire(CTX, LENA, APP, holder="run_1")

    (lease,) = uow.browser_sessions.leases.values()
    assert pool.closed == [(STEEL, lease.context_id)]


async def test_runs_waiting_on_the_lock_find_the_session_already_signed_back_in() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await with_a_recorded_sign_in(uow, lands_on=APP, username="lena")
    await vault.store(LENA.vault_key("password"), PASSWORD)
    lane = SigningLane(driver)
    broker = _broker(uow, driver, vault, lane)
    one = await broker.acquire(CTX, LENA, APP, holder="run_1")
    two = await broker.acquire(CTX, LENA, APP, holder="run_2")
    driver.expire_session()

    await asyncio.gather(broker.reauth(CTX, one, APP), broker.reauth(CTX, two, APP))

    assert lane.sign_ins == 1
    assert driver.tabs[one.target_id] == driver.tabs[two.target_id] == APP
    assert await vault.get(LENA.vault_key("state")) is not None


async def test_reauth_forgets_the_password_call_once_it_signs_back_in() -> None:
    uow, driver, vault = await _signing_world()
    lane = SigningLane(driver)
    broker = _broker(uow, driver, vault, lane)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    driver.expire_session()
    driver._log = [(0, SeenCall("POST", f"{IDP}/login", 200, request_body="password=x"))]

    await broker.reauth(CTX, held, APP)

    assert await driver.calls_since(held.session, held.target_id, -1) == ()


async def test_a_password_refused_on_re_sign_in_parks_the_lease_for_the_queued_caller() -> None:
    uow, driver, vault = await _signing_world()
    lane = SigningLane(driver)
    broker = _broker(uow, driver, vault, lane)
    one = await broker.acquire(CTX, LENA, APP, holder="run_1")
    two = await broker.acquire(CTX, LENA, APP, holder="run_2")
    driver.expire_session()
    driver.refuses = True
    before = lane.sign_ins

    first, second = await asyncio.gather(
        broker.reauth(CTX, one, APP), broker.reauth(CTX, two, APP), return_exceptions=True
    )

    assert isinstance(first, NeedsAPerson) and first.kind == "password"
    assert isinstance(second, AccountBusy)
    assert lane.sign_ins == before + 1
    assert await vault.get(LENA.vault_key("password") + "#refused") is not None
    assert uow.browser_sessions.leases[one.lease.id].state is LeaseState.WAITING


async def test_a_code_asked_on_re_sign_in_holds_the_account_for_the_person() -> None:
    uow, driver, vault = await _signing_world()
    lane = SigningLane(driver)
    broker = _broker(uow, driver, vault, lane)
    one = await broker.acquire(CTX, LENA, APP, holder="run_1")
    two = await broker.acquire(CTX, LENA, APP, holder="run_2")
    driver.expire_session()
    driver.shows_sign_in_until_signed = False
    driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))

    with pytest.raises(WaitingForAPerson) as asked:
        await broker.reauth(CTX, one, APP)
    with pytest.raises(AccountBusy):
        await broker.reauth(CTX, two, APP)

    assert asked.value.held.target_id == one.target_id
    assert uow.browser_sessions.leases[one.lease.id].state is LeaseState.WAITING
    assert lane.sign_ins == 1


async def test_a_crashed_container_is_replaced_and_its_state_restored() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await vault.store(LENA.vault_key("state"), '{"cookies": []}')
    pool = FakeBrowserPool({STEEL: 5})
    broker = _broker(uow, driver, vault, pool=pool)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    driver.dead.add(held.session.context_id)
    pool.dead.add(held.session.context_id)

    again = await broker.recover(CTX, held.lease.id, APP, holder="run_1")

    assert again.lease.id != held.lease.id
    restored = [call[2] for call in driver.calls if call[0] == "restore_state"]
    assert restored == ['{"cookies": []}', '{"cookies": []}']
    assert uow.browser_sessions.leases[held.lease.id].state is LeaseState.BROKEN
    assert (STEEL, held.session.context_id) in pool.closed


async def test_recover_keeps_a_lease_whose_context_the_pool_still_lists() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    pool = FakeBrowserPool({STEEL: 5})
    broker = _broker(uow, driver, vault, pool=pool)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    await driver.close_tab(held.session, held.target_id)

    again = await broker.recover(CTX, held.lease.id, APP, holder="run_1")

    assert again.lease.id == held.lease.id
    assert again.target_id != held.target_id
    assert pool.closed == []


async def test_after_a_re_sign_in_no_token_the_page_sent_before_it_is_handed_out() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await with_a_recorded_sign_in(uow, lands_on=APP, username="lena")
    await vault.store(LENA.vault_key("password"), PASSWORD)
    driver.headers = {"x-csrf-token": "before-the-sign-in"}
    driver.headers_after_mark = {"x-csrf-token": "after-the-sign-in"}
    broker = _broker(uow, driver, vault)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    assert (await broker.headers(CTX, held, APP))["x-csrf-token"] == "before-the-sign-in"
    driver.expire_session()

    await broker.reauth(CTX, held, APP)
    later = _broker(uow, driver, vault)

    assert (await later.headers(CTX, held, APP))["x-csrf-token"] == "after-the-sign-in"


async def test_a_re_sign_in_asked_to_go_back_ends_on_that_page() -> None:
    uow, driver, vault = await _signing_world()
    broker = _broker(uow, driver, vault)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    driver.expire_session()

    await broker.reauth(CTX, held, APP, back_to="https://wms.example/app/orders/7")

    assert driver.tabs[held.target_id] == "https://wms.example/app/orders/7"


async def test_a_sign_in_that_lands_clears_the_code_asked_latch() -> None:
    uow, driver, vault = await _signing_world()
    asked = CodeAsked(vault)
    await asked.ask(LENA.vault_key("password"), at=FakeClock().now())

    await _broker(uow, driver, vault).acquire(CTX, LENA, APP, holder="run_1")

    assert await asked.since(LENA.vault_key("password")) is None


async def test_a_code_asked_again_after_the_window_restarts_the_latch() -> None:
    # A code asked once and never answered must not leave the latch stale for
    # good: the next prompt, one window later, starts a new window, so a
    # lookup types the password at most once per K_CODE_WAIT (L1 re-review N3).
    _, _, vault = await _signing_world()
    asked = CodeAsked(vault)
    key = LENA.vault_key("password")
    first = FakeClock().now()
    later = first + K_CODE_WAIT + timedelta(minutes=1)

    await asked.ask(key, at=first)
    await asked.ask(key, at=later)

    assert await asked.since(key) == later
