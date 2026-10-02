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

The tests that drive a whole run do it through `RunWorkflow` on the real
Temporal server from `make up` (`localhost:7233`), on a task queue of their
own, and are skipped when it does not answer.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast
from urllib.parse import urlsplit

import docker
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from temporalio.api.enums.v1 import EventType
from temporalio.client import Client, WorkflowExecutionStatus, WorkflowFailureError
from temporalio.worker import Worker

from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.read_runs import CannotStop
from sro.application.execution.stops import Stops
from sro.application.execution.workflow_runs import AbortWorkflowRun, StartWorkflowRun
from sro.application.lookup.run_lookups import RunLookups
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.page import SessionRef
from sro.application.runtime.api_lane import ApiLane
from sro.application.runtime.broker import K_CLOSE_S, SessionBroker
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.fill_field import FillField
from sro.application.runtime.run_steps import RunSteps
from sro.application.runtime.step import Held
from sro.application.runtime.teach import Teach
from sro.application.runtime.ui_lane import UiLane
from sro.config import get_settings
from sro.domain.execution.account import K_LEASE_TTL, Account, LeaseState
from sro.domain.execution.lanes import Lane
from sro.domain.execution.progress import Progress
from sro.domain.execution.takeover import Took
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.lookup.plan import Lookup, Plan
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.gesture import (
    Action,
    Body,
    Call,
    Gesture,
    GestureBatch,
    Outline,
    OutlineField,
    Target,
)
from sro.domain.shared.hosts import REDACTED
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.tabs import MAIN
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.locks import PostgresAccountLocks
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.driver import SteelDriver
from sro.infrastructure.steel.pool import SteelPool
from sro.infrastructure.system import UuidFactory
from sro.infrastructure.temporal.activities import RunActivities, RunRef
from sro.infrastructure.temporal.durable import TemporalDurableExecution
from sro.infrastructure.temporal.workflows import RunWorkflow
from tests.browser.steel_rig import Rig, pages_in
from tests.browser.test_the_steel_pool_against_local_steel import (
    CDP_URL,
    STEEL_URL,
    release_every_live_session,
    status_of,
    tracking_contexts,
)
from tests.unit.fakes import (
    FakeAsker,
    FakeChannel,
    FakeClock,
    FakeCredentialVault,
    FakeDurableExecution,
    FakeIdFactory,
)
from tests.unit.runtime_support import RecordingLane, with_a_recorded_sign_in

if TYPE_CHECKING:
    from sro.container import Container

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
    sessions: async_sessionmaker[AsyncSession]

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
        session_factory,
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

    answers = await RunLookups(world.uow, broker, world.clock).execute(
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

    answers = await RunLookups(world.uow, broker, world.clock).execute(
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
    broker, driver = world.broker()
    tool, api, ui, sight = (RecordingLane(lane) for lane in Lane)
    steps = RunSteps(
        world.uow,
        broker,
        StepExecutor(tool, api, ui, sight, broker),
        Teach(world.uow, world.clock),
        api,
        world.clock,
        FakeIdFactory(),
        fill=FillField(driver, None),
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


TEMPORAL = "localhost:7233"


@pytest.fixture
async def temporal() -> Client:
    try:
        async with asyncio.timeout(5):
            return await Client.connect(TEMPORAL)
    except Exception as exc:
        pytest.skip(f"Temporal is not reachable at {TEMPORAL}: {exc}")


def _did(world: World, gesture_id: str, action: Action, *requests: Call) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant=TENANT,
        stream_id="stream-job",
        batch_id="batch-sign-in",
        at=action.at,
        url=world.rig.url("/app"),
        system=world.rig.url(""),
        tab_id=1,
        frame_url=None,
        action=action,
        requests=list(requests),
    )


def _steps(world: World) -> dict[str, tuple[Step, Gesture]]:
    """The rig's `/app` as it was recorded: a Refresh that reads the list, a
    typed customer type, and the Save that writes it."""
    refresh = _did(
        world,
        "ges_refresh",
        Action(kind="click", at=10.0, target=Target(role="button", name="Refresh")),
        Call("GET", world.rig.url("/api/customer-types?hold"), started_at=10.0, status=200),
    )
    typed = _did(
        world,
        "ges_type",
        Action(
            kind="type", at=11.0, value="GT1", target=Target(role="textbox", name="Customer Type")
        ),
    )
    save = _did(
        world,
        "ges_save",
        Action(kind="click", at=12.0, target=Target(role="button", name="Save")),
        Call(
            "POST",
            world.rig.url("/api/customer-types"),
            started_at=12.0,
            status=201,
            request_body=Body(text='{"name": "GT1"}', mime_type="application/json"),
        ),
    )
    return {
        "refresh": (
            Step(order=0, says="Refresh the list", system=None, cites=[refresh.id]),
            refresh,
        ),
        "type": (
            Step(
                order=0,
                says="Type the customer type",
                system=None,
                cites=[typed.id],
                parameters=["Customer Type"],
            ),
            typed,
        ),
        "save": (Step(order=0, says="Save it", system=None, cites=[save.id]), save),
    }


async def _a_run(world: World, *names: str) -> str:
    """A live Steel run of a job made of the named recorded steps, in order,
    shaped as mining leaves a job: a parameter only where a step fills it."""
    await _recorded(world)
    known = _steps(world)
    chosen = [known[name] for name in names]
    job = Workflow(
        id="wfl_whole_run",
        tenant=TENANT,
        title="Add a customer type",
        narrative="",
        steps=[replace(step, order=n) for n, (step, _) in enumerate(chosen)],
    )
    typed = any("Customer Type" in step.parameters for step in job.steps)
    job.parameters = [{"name": "Customer Type", "required": False}] if typed else []
    run_id = f"run_{uuid.uuid4().hex}"
    async with world.uow as uow:
        await uow.gestures.add_gestures(tuple(seen for _, seen in chosen))
        await uow.workflows.save(job)
        await uow.workflow_runs.save(
            WorkflowRun(
                id=run_id,
                tenant=TENANT,
                workflow_id=job.id,
                device_id="",
                values={"Customer Type": "GT2"} if typed else {},
                started_by="op",
                live=True,
                allow_focus=False,
                started_at=datetime.now(UTC).isoformat(),
                executor="steel",
            )
        )
        await uow.commit()
    return run_id


class _Process:
    """What `RunActivities` asks of the container, as one worker process has
    it: one driver of its own, and a fresh unit of work behind every
    `run_steps`, over the shared database and Steel."""

    def __init__(self, world: World) -> None:
        self._world = world
        self._driver = SteelDriver(get_settings().page_code_path)
        world.drivers.append(self._driver)

    def run_steps(self) -> RunSteps:
        world, driver = self._world, self._driver
        uow = SqlUnitOfWork(world.sessions)
        broker = SessionBroker(
            uow, world.pool, driver, world.locks, world.vault, world.clock, ui=UiLane(driver)
        )
        api = ApiLane(broker)
        executor = StepExecutor(
            RecordingLane(Lane.TOOL), api, UiLane(driver), RecordingLane(Lane.SIGHT), broker
        )
        return RunSteps(
            uow,
            broker,
            executor,
            Teach(uow, world.clock),
            api,
            world.clock,
            UuidFactory(),
            fill=FillField(driver, None),
        )


def _worker(world: World, temporal: Client, queue: str) -> Worker:
    runs = RunActivities(cast("Container", _Process(world)))
    return Worker(
        temporal,
        task_queue=queue,
        workflows=[RunWorkflow],
        activities=[
            runs.prepare,
            runs.acquire,
            runs.step,
            runs.answered,
            runs.stopped,
            runs.finish,
            runs.release,
        ],
        # A worker stopped mid-run leaves its workflow unfinished; uncached, the
        # next worker replays it from history rather than a sticky queue.
        max_cached_workflows=0,
    )


async def _saved(world: World, run_id: str) -> WorkflowRun:
    async with world.uow as uow:
        run = await uow.workflow_runs.get(CTX.tenant_id, run_id)
    assert run is not None
    return run


async def test_a_stop_mid_step_lets_the_step_finish_and_sends_nothing_after_it(
    world: World, temporal: Client
) -> None:
    run_id = await _a_run(world, "refresh", "save")
    queue = f"runs-test-{uuid.uuid4().hex}"
    stopping = AbortWorkflowRun(
        world.uow, Stops(), Approvals(), durable=TemporalDurableExecution(address=TEMPORAL)
    )
    async with _worker(world, temporal, queue):
        handle = await temporal.start_workflow(
            RunWorkflow.run,
            RunRef(tenant_id=TENANT, principal_id="op", run_id=run_id, budget_s=300.0),
            id=f"workflow-run-{run_id}",
            task_queue=queue,
        )
        assert await asyncio.to_thread(world.rig.asked.wait, 60)

        answered = await stopping.execute(CTX, run_id=run_id)
        world.rig.answer.set()

        with pytest.raises(WorkflowFailureError):
            await handle.result()

    assert answered.outcome == "running"
    assert (await handle.describe()).status is WorkflowExecutionStatus.CANCELED
    assert world.rig.saved == []
    run = await _saved(world, run_id)
    assert run.outcome == "aborted"
    assert [(one.of_step, one.verdict) for one in run.steps] == [(0, "held")]
    assert Progress.of(run.progress).tabs == {}
    assert run.finished_at is not None
    with pytest.raises(CannotStop, match="aborted"):
        await stopping.execute(CTX, run_id=run_id)


async def test_a_stop_while_the_run_waits_for_a_code_aborts_it_holding_nothing(
    world: World, temporal: Client
) -> None:
    run_id = await _a_run(world, "refresh")
    world.rig.asks_a_code = True
    queue = f"runs-test-{uuid.uuid4().hex}"
    stopping = AbortWorkflowRun(
        world.uow, Stops(), Approvals(), durable=TemporalDurableExecution(address=TEMPORAL)
    )
    async with _worker(world, temporal, queue):
        handle = await temporal.start_workflow(
            RunWorkflow.run,
            RunRef(tenant_id=TENANT, principal_id="op", run_id=run_id, budget_s=300.0),
            id=f"workflow-run-{run_id}",
            task_queue=queue,
        )
        async with asyncio.timeout(60):
            async for event in handle.fetch_history_events(wait_new_event=True):
                if event.event_type == EventType.EVENT_TYPE_TIMER_STARTED:
                    break
        parked = Progress.of((await _saved(world, run_id)).progress)
        async with world.uow as uow:
            lease = await uow.browser_sessions.get_lease(CTX.tenant_id, parked.lease)
        assert lease is not None
        assert lease.state is LeaseState.WAITING
        assert lease.holder == run_id

        await stopping.execute(CTX, run_id=run_id)
        with pytest.raises(WorkflowFailureError):
            await handle.result()

    assert (await handle.describe()).status is WorkflowExecutionStatus.CANCELED
    run = await _saved(world, run_id)
    assert run.outcome == "aborted"
    assert run.finished_at is not None
    assert Progress.of(run.progress).tabs == {}
    async with world.uow as uow:
        lease = await uow.browser_sessions.get_lease(CTX.tenant_id, parked.lease)
    assert lease is not None
    assert lease.state is not LeaseState.WAITING


async def test_a_worker_killed_mid_write_resumes_the_run_and_never_sends_it_again(
    world: World, temporal: Client
) -> None:
    run_id = await _a_run(world, "type", "save")
    world.rig.hold_saves = True
    queue = f"runs-test-{uuid.uuid4().hex}"
    first = asyncio.create_task(_worker(world, temporal, queue).run())
    handle = await temporal.start_workflow(
        RunWorkflow.run,
        RunRef(tenant_id=TENANT, principal_id="op", run_id=run_id, budget_s=300.0),
        id=f"workflow-run-{run_id}",
        task_queue=queue,
    )
    assert await asyncio.to_thread(world.rig.asked.wait, 60)
    tab = Progress.of((await _saved(world, run_id)).progress).tabs[MAIN]

    first.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await first
    world.rig.answer.set()
    async with _worker(world, temporal, queue):
        await handle.result()

    assert world.rig.saved == [{"name": "GT2"}]
    assert world.rig.logins == 1
    run = await _saved(world, run_id)
    assert [(one.of_step, one.verdict) for one in run.steps] == [(0, "held"), (1, "unclear")]
    progress = Progress.of(run.progress)
    assert progress.in_doubt(1)
    async with world.uow as uow:
        lease = await uow.browser_sessions.get_lease(CTX.tenant_id, progress.lease)
    assert lease is not None
    session = SessionRef(lease.context_id, await world.pool.cdp_url(lease.container_url))
    assert tab not in await pages_in(session)


async def test_a_takeover_after_the_operator_s_own_save_sends_only_the_rest(
    world: World, temporal: Client
) -> None:
    await _recorded(world)
    known = _steps(world)
    typed, save = known["type"][1], known["save"][1]

    def did(gid: str, like: Gesture, at: float, name: str | None = None) -> Gesture:
        body = Body(text=json.dumps({"name": name}), mime_type="application/json")
        return replace(
            like,
            id=gid,
            at=at,
            action=replace(like.action, at=at),
            requests=[replace(call, started_at=at, request_body=body) for call in like.requests]
            if name
            else [],
        )

    cited = [
        [did("t0", typed, 11.0)],
        [did("s1a", save, 12.0, "A1"), did("s1b", save, 112.0, "A2")],
        [did("t2", typed, 13.0)],
        [did("s3a", save, 14.0, "B1"), did("s3b", save, 114.0, "B2")],
    ]
    says = ["Type the first", "Save it", "Type the second", "Save it"]
    takes = [["First"], [], ["Second"], []]
    job = Workflow(
        id="wfl_two_saves",
        tenant=TENANT,
        title="Add two customer types",
        narrative="",
        steps=[
            Step(
                order=n,
                says=says[n],
                system=None,
                cites=[one.id for one in cited[n]],
                parameters=takes[n],
            )
            for n in range(4)
        ],
        parameters=[
            {"name": "First", "seen_values": ["A1", "A2"]},
            {"name": "Second", "seen_values": ["B1", "B2"]},
        ],
    )
    world.rig.saved.append({"name": "GT1"})
    proof = uuid.uuid4().hex
    theirs = replace(did("ges_operator_save", save, 100.0, "GT1"), stream_id="dev-1", tab_id=7)
    async with world.uow as uow:
        await uow.gestures.add_gestures((*(one for each in cited for one in each), theirs))
        await uow.workflows.save(job)
        await uow.devices.add(
            AgentDevice(
                id=DeviceId("dev-1"),
                tenant_id=CTX.tenant_id,
                principal_id=CTX.principal_id,
                label="the operator's browser",
                extension_version="1",
                registered_at=datetime.now(UTC),
                last_seen_at=datetime.now(UTC),
                secret=proof,
            )
        )
        await uow.commit()
    starter = StartWorkflowRun(
        world.uow,
        channel=FakeChannel(),
        asker=FakeAsker(),
        clock=world.clock,
        cap_usd=5.0,
        stops=Stops(),
        approvals=Approvals(),
        one_time_secrets=OneTimeSecrets(),
        durable=FakeDurableExecution(),
        steel_tenants=frozenset({TENANT}),
        servers={},
    )
    run = await starter.execute(
        CTX,
        workflow_id=job.id,
        device_id=DeviceId("dev-1"),
        device_secret=proof,
        values={"First": "GT1", "Second": "GT2"},
        live=True,
        allow_focus=False,
        matched=2,
        took_over=Took(tab_id=7, since=90.0, through=100.0, newest=100.0),
    )
    queue = f"runs-test-{uuid.uuid4().hex}"
    async with _worker(world, temporal, queue):
        await temporal.execute_workflow(
            RunWorkflow.run,
            RunRef(tenant_id=TENANT, principal_id="op", run_id=run.id, budget_s=300.0),
            id=f"workflow-run-{run.id}",
            task_queue=queue,
        )

    assert world.rig.saved == [{"name": "GT1"}, {"name": "GT2"}]
    finished = await _saved(world, run.id)
    assert finished.outcome == "held"
    assert [one.of_step for one in finished.steps] == [2, 3]


async def _run_to_its_end(
    world: World, temporal: Client, queue: str, values: dict[str, str]
) -> WorkflowRun:
    run_id = f"run_{uuid.uuid4().hex}"
    async with world.uow as uow:
        await uow.workflow_runs.save(
            WorkflowRun(
                id=run_id,
                tenant=TENANT,
                workflow_id="wfl_whole_run",
                device_id="",
                values=values,
                started_by="op",
                live=True,
                allow_focus=False,
                started_at=datetime.now(UTC).isoformat(),
                executor="steel",
            )
        )
        await uow.commit()
    handle = await temporal.start_workflow(
        RunWorkflow.run,
        RunRef(tenant_id=TENANT, principal_id="op", run_id=run_id, budget_s=300.0),
        id=f"workflow-run-{run_id}",
        task_queue=queue,
    )
    await handle.result()
    return await _saved(world, run_id)


async def test_a_field_nobody_demonstrated_is_filled_confirmed_by_the_save_and_learned(
    world: World, temporal: Client
) -> None:
    """The job was recorded typing a Customer Type and pressing Save; it never
    touched Department, so its recorded body is `{name}`. A run asked for a
    Department fills it by its label on the form the save's screen outlined,
    and only the save's own call carrying `department` confirms and teaches it."""
    unused = await _a_run(world, "type", "save")
    known = _steps(world)
    save = known["save"][1]
    outlined = replace(
        save,
        id="ges_save_outlined",
        action=replace(
            save.action,
            outlines=(
                Outline(
                    fields=(
                        OutlineField("textbox", "Customer Type"),
                        OutlineField("combobox", "Department", None, ("Finance", "Operations")),
                    )
                ),
            ),
        ),
    )
    async with world.uow as uow:
        await uow.gestures.add_gestures((outlined,))
        job = await uow.workflows.get(CTX.tenant_id, "wfl_whole_run")
        job.steps[1].cites = [outlined.id]
        await uow.workflows.save(job)
        never_run = await uow.workflow_runs.get(CTX.tenant_id, unused)
        assert never_run is not None
        await uow.workflow_runs.save(replace(never_run, outcome="aborted"))
        await uow.commit()
    queue = f"runs-test-{uuid.uuid4().hex}"

    async with _worker(world, temporal, queue):
        first = await _run_to_its_end(
            world, temporal, queue, {"Customer Type": "GT9", "department": "Operations"}
        )
        assert world.rig.saved[-1] == {"name": "GT9", "department": "Operations"}
        (field,) = Progress.of(first.progress).composed
        assert (field["lane"], field["verdict"], field["key"]) == ("ui", "done", "department")
        assert first.outcome == "held"
        async with world.uow as uow:
            grown = await uow.workflows.get(CTX.tenant_id, "wfl_whole_run")
        assert [one.says for one in grown.steps] == [
            "Type the customer type",
            "Fill Department",
            "Save it",
        ]
        assert grown.parameters[-1]["required"] is False

        second = await _run_to_its_end(
            world, temporal, queue, {"Customer Type": "GT10", "department": "Finance"}
        )
        assert Progress.of(second.progress).composed == []
        assert world.rig.saved[-1] == {"name": "GT10", "department": "Finance"}
        assert second.outcome == "held"

        third = await _run_to_its_end(world, temporal, queue, {"Customer Type": "GT11"})
        assert world.rig.saved[-1] == {"name": "GT11"}
        assert third.outcome == "held"
