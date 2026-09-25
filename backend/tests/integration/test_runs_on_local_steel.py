"""The session broker against real local Steel and real Postgres: leases in
`browser_sessions`, the account lock in Postgres, one Steel container holding
each account in its own browser context, and a rig whose identity provider
answers on a second origin, as a real one does.

Skipped unless local Steel answers and `SRO_INTEGRATION_DATABASE_URL` (or
Docker) gives a database. Run each test alone: they share the container's one
browser, and each releases the Steel session when it ends.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from sro.application.context import RequestContext
from sro.application.runtime.broker import K_CLOSE_S, SessionBroker
from sro.application.runtime.ui_lane import UiLane
from sro.config import get_settings
from sro.domain.execution.account import K_LEASE_TTL, Account
from sro.domain.observation.gesture import GestureBatch
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.db.locks import PostgresAccountLocks
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.driver import SteelDriver
from sro.infrastructure.steel.pool import SteelPool
from tests.browser.steel_rig import Rig
from tests.browser.test_the_steel_pool_against_local_steel import CDP_URL, STEEL_URL
from tests.unit.fakes import FakeClock, FakeCredentialVault
from tests.unit.runtime_support import with_a_recorded_sign_in

pytestmark = pytest.mark.browser

TENANT = "greyorange"
CTX = RequestContext(TenantId(TENANT), PrincipalId("op"))
K_CONTEXTS = 3


@pytest.fixture
async def client() -> AsyncIterator[SteelClient]:
    made = SteelClient(STEEL_URL, CDP_URL, capacity=K_CONTEXTS)
    try:
        if not await made.health():
            pytest.skip("Steel is not running; `make up` first")
    except Exception as exc:
        pytest.skip(f"Steel is not reachable: {exc}")
    async with made:
        try:
            yield made
        finally:
            if made._session_id is not None:
                await made.close(made._session_id)


@pytest.fixture
def steel_rig() -> Iterator[Rig]:
    made = Rig(for_steel=True, idp_elsewhere=True)
    try:
        yield made
    finally:
        made.close()


@dataclass
class World:
    rig: Rig
    pool: SteelPool
    uow: SqlUnitOfWork
    locks: PostgresAccountLocks
    vault: FakeCredentialVault
    clock: FakeClock
    drivers: list[SteelDriver]

    def broker(self) -> tuple[SessionBroker, SteelDriver]:
        driver = SteelDriver(get_settings().page_code_path)
        self.drivers.append(driver)
        made = SessionBroker(
            self.uow, self.pool, driver, self.locks, self.vault, self.clock, ui=UiLane(driver)
        )
        return made, driver

    def account(self, username: str) -> Account:
        return Account.of(TENANT, self.rig.idp_url(""), username)


@pytest.fixture
async def world(
    client: SteelClient,
    steel_rig: Rig,
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[World]:
    made = World(
        steel_rig,
        SteelPool({STEEL_URL: client}, per_container=K_CONTEXTS),
        SqlUnitOfWork(session_factory),
        PostgresAccountLocks(engine),
        FakeCredentialVault(),
        FakeClock(datetime.now(UTC)),
        [],
    )
    try:
        yield made
    finally:
        for driver in made.drivers:
            await driver.aclose()


async def _recorded(world: World) -> Account:
    async with world.uow as uow:
        await uow.gestures.add_batch(
            GestureBatch(
                batch_id="batch-sign-in",
                device_id="dev-1",
                tenant=TENANT,
                mode="passive",
                received_at="2026-09-25T09:00:00+00:00",
            )
        )
        await with_a_recorded_sign_in(
            uow, lands_on=world.rig.url("/app"), username="operator", at=world.rig.idp_url("")
        )
        await uow.commit()
    broker, _ = world.broker()
    account = await broker.account_for(CTX, world.rig.url("/app"))
    assert account == world.account("operator")
    await world.vault.store(account.vault_key("password"), "a-password")
    return account


async def test_a_sign_in_page_is_signed_through_the_recorded_chain(world: World) -> None:
    account = await _recorded(world)
    broker, driver = world.broker()

    held = await broker.acquire(CTX, account, world.rig.url("/app"), holder="run_1")

    assert world.rig.logins == 1
    assert urlsplit(await driver.url_of(held.session, held.target_id)).path == "/app"
    assert await world.vault.get(account.vault_key("state"))


async def test_an_expired_session_is_restored_with_no_fresh_sign_in(world: World) -> None:
    account = await _recorded(world)
    broker, driver = world.broker()
    first = await broker.acquire(CTX, account, world.rig.url("/app"), holder="run_1")
    assert world.rig.logins == 1
    await driver.forget(first.session)
    world.clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    again, fresh = world.broker()

    second = await again.acquire(CTX, account, world.rig.url("/app"), holder="run_2")

    assert world.rig.logins == 1
    assert second.lease.id != first.lease.id
    assert second.lease.container_url == first.lease.container_url
    assert urlsplit(await fresh.url_of(second.session, second.target_id)).path == "/app"
    assert not await world.pool.alive(first.lease.container_url, first.lease.context_id)


async def test_two_accounts_share_one_container_and_a_hung_sibling_never_blocks_a_close(
    world: World,
) -> None:
    broker, driver = world.broker()
    lena, omar = world.account("lena"), world.account("omar")
    page = world.rig.url("/public")

    one = await broker.acquire(CTX, lena, page, holder="run_1")
    two = await broker.acquire(CTX, lena, page, holder="run_2")
    other = await broker.acquire(CTX, omar, page, holder="run_3")

    assert one.lease.id == two.lease.id
    assert one.target_id != two.target_id
    assert other.lease.container_url == one.lease.container_url
    assert other.session.context_id != one.session.context_id

    world.clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    assert await broker.beat(CTX, other.lease.id, holder="run_3")
    hung = asyncio.create_task(
        driver.goto(other.session, other.target_id, world.rig.url("/held-login"))
    )
    try:
        assert await asyncio.to_thread(world.rig.asked.wait, 10)
        started = time.monotonic()

        taken = await broker.acquire(CTX, lena, page, holder="run_4")

        assert time.monotonic() - started < K_CLOSE_S + 5
        assert taken.lease.id != one.lease.id
        assert await world.pool.alive(other.lease.container_url, other.session.context_id)
    finally:
        world.rig.answer.set()
        with contextlib.suppress(Exception):
            await hung
    assert urlsplit(await driver.url_of(other.session, other.target_id)).path == "/held-login"
