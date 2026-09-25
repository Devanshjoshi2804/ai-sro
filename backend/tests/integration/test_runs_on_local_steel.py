"""The session broker against real local Steel and real Postgres: leases in
`browser_sessions`, the account lock in Postgres, one Steel container holding
each account in its own browser context, and a rig whose identity provider
answers on a second origin, as a real one does.

Skipped unless local Steel answers and `SRO_INTEGRATION_DATABASE_URL` (or
Docker) gives a database. Run each test alone: they share the container's one
browser, and each releases the Steel session when it ends.

`test_a_crashed_container_is_replaced_and_its_saved_state_restored` restarts
the shared Steel container itself, which kills every other live test running
against it -- any `-m browser` run on the machine, CI included. It is opt-in:
set `SRO_STEEL_CRASH_TESTS=1` to run it, and only after checking no other live
session is in use.

`test_a_lookup_reads_through_the_account_s_steel_session` sends its GET from
this process as well as loading pages in Steel, so the rig's host must resolve
on both sides: set `SRO_STEEL_SEES_HOST` to this machine's LAN address
(`host.docker.internal` resolves only inside the container).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

import docker
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from sro.application.context import RequestContext
from sro.application.lookup.run_lookups import RunLookups
from sro.application.ports.browser import BrowserUnavailable
from sro.application.runtime.broker import K_CLOSE_S, SessionBroker
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.run_steps import RunSteps
from sro.application.runtime.step import Held
from sro.application.runtime.teach import Teach
from sro.application.runtime.ui_lane import UiLane
from sro.config import get_settings
from sro.domain.execution.account import K_LEASE_TTL, Account, LeaseState
from sro.domain.execution.lanes import Lane
from sro.domain.execution.progress import MAIN, Progress
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.observation.gesture import Action, Call, Gesture, GestureBatch, Target
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.locks import PostgresAccountLocks
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.http.httpx_caller import HttpxCaller
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.driver import SteelDriver
from sro.infrastructure.steel.pool import SteelPool
from tests.browser.steel_rig import Rig, pages_in
from tests.browser.test_the_steel_pool_against_local_steel import (
    CDP_URL,
    STEEL_URL,
    release_every_live_session,
    status_of,
    tracking_contexts,
)
from tests.unit.fakes import FakeClock, FakeCredentialVault
from tests.unit.runtime_support import RecordingLane, with_a_recorded_sign_in

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
    async with made, tracking_contexts() as created:
        try:
            yield made
        finally:
            await release_every_live_session(made, created)


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

    def broker(self, pool: SteelPool | None = None) -> tuple[SessionBroker, SteelDriver]:
        driver = SteelDriver(get_settings().page_code_path)
        self.drivers.append(driver)
        made = SessionBroker(
            self.uow,
            pool or self.pool,
            driver,
            self.locks,
            self.vault,
            self.clock,
            ui=UiLane(driver),
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
    assert await driver.calls_since(held.session, held.target_id, 0) == ()


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
    assert first.lease.context_id not in await world.pool.contexts(first.lease.container_url)


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
        assert other.session.context_id in await world.pool.contexts(other.lease.container_url)
    finally:
        world.rig.answer.set()
        with contextlib.suppress(Exception):
            await hung
    assert urlsplit(await driver.url_of(other.session, other.target_id)).path == "/held-login"


async def test_a_restarted_process_leases_beside_a_live_account_and_never_ends_it(
    world: World,
) -> None:
    lena, omar = world.account("lena"), world.account("omar")
    page = world.rig.url("/public")
    before, _ = world.broker()
    kept = await before.acquire(CTX, lena, page, holder="run_1")

    async with SteelClient(STEEL_URL, CDP_URL, capacity=K_CONTEXTS) as restarted:
        after, driver = world.broker(SteelPool({STEEL_URL: restarted}, per_container=K_CONTEXTS))
        other = await after.acquire(CTX, omar, page, holder="run_2")
        world.clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
        assert await after.beat(CTX, kept.lease.id, holder="run_1")

        taken = await after.acquire(CTX, omar, page, holder="run_3")

        listed = await world.pool.contexts(STEEL_URL)
        assert other.lease.steel_session_id == kept.lease.steel_session_id
        assert other.lease.context_id != other.lease.steel_session_id
        assert taken.lease.id != other.lease.id
        assert other.lease.context_id not in listed
        assert {kept.lease.context_id, taken.lease.context_id} <= listed
        assert await status_of(kept.lease.steel_session_id) == "live"
        assert urlsplit(await driver.url_of(taken.session, taken.target_id)).path == "/public"


async def test_a_container_whose_browser_went_away_recovers_onto_a_fresh_context(
    world: World,
    client: SteelClient,
) -> None:
    lena = world.account("lena")
    page = world.rig.url("/public")
    broker, _ = world.broker()
    first = await broker.acquire(CTX, lena, page, holder="run_1")

    # A real crash releases the container's shared browser directly, at
    # Steel, not through `SteelClient.close`'s guard (S7 rereview, R2-1),
    # which now refuses that release for as long as any context is live.
    async with httpx.AsyncClient() as http:
        await http.post(f"{STEEL_URL}/v1/sessions/{first.lease.steel_session_id}/release")

    again, driver = world.broker()
    second = await again.acquire(CTX, lena, page, holder="run_2")

    async with world.uow as uow:
        old = await uow.browser_sessions.get_lease(CTX.tenant_id, first.lease.id)
    assert old is not None
    assert old.state is LeaseState.BROKEN
    assert second.lease.id != first.lease.id
    assert second.lease.context_id in await world.pool.contexts(STEEL_URL)
    assert urlsplit(await driver.url_of(second.session, second.target_id)).path == "/public"


async def test_an_expiry_mid_step_signs_in_once_for_every_run_on_the_account(world: World) -> None:
    account = await _recorded(world)
    broker, driver = world.broker()
    one = await broker.acquire(CTX, account, world.rig.url("/app"), holder="run_1")
    two = await broker.acquire(CTX, account, world.rig.url("/app"), holder="run_2")
    assert world.rig.logins == 1
    world.rig.expire()

    await asyncio.gather(
        broker.reauth(CTX, one, world.rig.url("/app")),
        broker.reauth(CTX, two, world.rig.url("/app")),
    )

    assert world.rig.logins == 2
    for held in (one, two):
        assert urlsplit(await driver.url_of(held.session, held.target_id)).path == "/app"


async def _a_lookup(world: World, headers: dict[str, str]) -> tuple[SessionBroker, Held]:
    account = await _recorded(world)
    world.rig.saved.append({"name": "GT0"})
    read = Call(
        method="GET",
        url=world.rig.url("/api/customer-types"),
        request_id="req-read",
        started_at=10.0,
        request_headers=headers,
        status=200,
    )
    seen = Gesture(
        id="ges_read",
        tenant=TENANT,
        stream_id="stream-read",
        batch_id="batch-sign-in",
        at=10.0,
        url=world.rig.url("/app"),
        system=world.rig.url(""),
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=10.0),
        requests=[read],
    )
    async with world.uow as uow:
        await uow.gestures.add_gestures((seen,))
        await uow.commit()
    broker, _ = world.broker()
    held = await broker.acquire(CTX, account, world.rig.url("/app"), holder="run_1")
    return broker, held


LOOKUP = Lookup(system="rig", how="call", target="/api/customer-types")


async def test_a_lookup_reads_through_the_account_s_steel_session(world: World) -> None:
    broker, held = await _a_lookup(world, {"accept": "application/json"})
    before = await pages_in(held.session)

    answers = await RunLookups(world.uow, broker, HttpxCaller()).execute(
        CTX, plan=Plan(question="q", lookups=(LOOKUP,))
    )

    (looked,) = answers.looked
    assert looked.ok, looked.detail
    assert looked.answer["status"] == 200
    assert json.loads(str(looked.answer["body"])) == [{"name": "GT0"}]
    assert world.rig.logins == 1
    assert await pages_in(held.session) == before


async def test_a_token_the_page_never_sends_is_named_inside_the_lookup_s_budget(
    world: World,
) -> None:
    broker, _ = await _a_lookup(world, {"X-CSRF-Token": REDACTED})

    answers = await RunLookups(world.uow, broker, HttpxCaller()).execute(
        CTX, plan=Plan(question="q", lookups=(LOOKUP,)), within=3.0
    )

    assert answers.looked[0].detail == "the session has no x-csrf-token for this read"


async def test_two_runs_of_one_job_share_the_account_s_lease_as_two_tabs(world: World) -> None:
    await _recorded(world)
    app = world.rig.url("/app")
    opened = Gesture(
        id="ges_open_app",
        tenant=TENANT,
        stream_id="stream-job",
        batch_id="batch-sign-in",
        at=10.0,
        url=app,
        system=world.rig.url(""),
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=10.0, target=Target(role="link", name="Orders")),
    )
    job = Workflow(
        id="wfl_two_tabs",
        tenant=TENANT,
        title="Open the orders",
        narrative="",
        steps=[Step(order=0, says="Open the orders", system=None, cites=[opened.id])],
    )
    async with world.uow as uow:
        await uow.gestures.add_gestures((opened,))
        await uow.workflows.save(job)
        for run_id in ("run_tab_1", "run_tab_2"):
            await uow.workflow_runs.save(
                WorkflowRun(
                    id=run_id,
                    tenant=TENANT,
                    workflow_id=job.id,
                    device_id="",
                    values={},
                    started_by="op",
                    live=False,
                    allow_focus=False,
                    started_at=datetime.now(UTC).isoformat(),
                    executor="steel",
                )
            )
        await uow.commit()
    broker, _ = world.broker()
    tool, api, ui, sight = (RecordingLane(lane) for lane in Lane)
    steps = RunSteps(
        world.uow,
        broker,
        StepExecutor(tool, api, ui, sight, broker),
        Teach(world.uow, world.clock),
        api,
        world.clock,
    )

    for run_id in ("run_tab_1", "run_tab_2"):
        assert (await steps.prepare(CTX, run_id)).browser
        await steps.acquire(CTX, run_id)

    async with world.uow as uow:
        one, two = (
            Progress.of(found.progress)
            for found in [
                await uow.workflow_runs.get(CTX.tenant_id, run_id)
                for run_id in ("run_tab_1", "run_tab_2")
            ]
            if found is not None
        )
    assert world.rig.logins == 1
    assert one.lease == two.lease
    assert one.tabs[MAIN] != two.tabs[MAIN]
    for run_id in ("run_tab_1", "run_tab_2"):
        await steps.release(CTX, run_id)


K_STEEL_BACK_S = 60.0


async def _restart_steel(client: SteelClient) -> None:
    port = urlsplit(STEEL_URL).port
    (container,) = docker.from_env().containers.list(filters={"publish": str(port)})
    await asyncio.to_thread(container.restart)
    async with asyncio.timeout(K_STEEL_BACK_S):
        while True:
            with contextlib.suppress(BrowserUnavailable):
                await client.contexts()
                return
            await asyncio.sleep(0.5)


@pytest.mark.skipif(
    os.environ.get("SRO_STEEL_CRASH_TESTS") != "1",
    reason="restarts the shared Steel container, killing every other live test "
    "running against it; set SRO_STEEL_CRASH_TESTS=1 to opt in",
)
async def test_a_crashed_container_is_replaced_and_its_saved_state_restored(
    world: World, client: SteelClient
) -> None:
    account = await _recorded(world)
    broker, _ = world.broker()
    first = await broker.acquire(CTX, account, world.rig.url("/app"), holder="run_1")
    assert world.rig.logins == 1

    await _restart_steel(client)
    again, driver = world.broker()
    second = await again.recover(CTX, first.lease.id, world.rig.url("/app"), holder="run_1")

    assert world.rig.logins == 1
    async with world.uow as uow:
        old = await uow.browser_sessions.get_lease(CTX.tenant_id, first.lease.id)
    assert old is not None
    assert old.state is LeaseState.BROKEN
    assert second.lease.id != first.lease.id
    assert urlsplit(await driver.url_of(second.session, second.target_id)).path == "/app"
