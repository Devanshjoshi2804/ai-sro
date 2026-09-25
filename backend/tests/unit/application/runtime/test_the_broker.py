import asyncio

import pytest

from sro.application.context import RequestContext
from sro.application.ports.page import PageGone
from sro.application.ports.pool import PoolFull
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import NeedsAPerson
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
    assert lease.state is LeaseState.BROKEN
    assert pool.closed == [(STEEL, lease.context_id)]


async def test_a_refused_password_is_never_typed_again() -> None:
    uow, driver, vault = await _signing_world(password=WRONG)
    driver.refuses = True
    with pytest.raises(NeedsAPerson):
        await _broker(uow, driver, vault).acquire(CTX, LENA, APP, holder="run_1")
    lane = SigningLane(driver)

    with pytest.raises(NeedsAPerson) as asked:
        await _broker(uow, driver, vault, lane).acquire(CTX, LENA, APP, holder="run_2")

    assert asked.value.kind == "password"
    assert lane.stepped == []


async def test_a_one_time_code_asks_a_person() -> None:
    uow, driver, vault = await _signing_world()
    driver.shows_sign_in_until_signed = False
    driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))

    with pytest.raises(NeedsAPerson):
        await _broker(uow, driver, vault).acquire(CTX, LENA, APP, holder="run_1")


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
