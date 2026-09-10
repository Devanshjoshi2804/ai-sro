"""`/v1/workflow-runs` through the real container, against real Postgres.

The press first, then the two reads at the foot of the file: the list a person
picks from and the run itself. Ordering, the cap and the `awaiting` join are
exactly what a fake gets right by accident -- it sorts a dict in Python and
cannot be wrong about the direction of a `timestamptz` or about what the store
returns when two runs share an instant.

The unit suite cannot settle two of these. `FakeUnitOfWork` builds its
repositories in `__init__` and `SqlUnitOfWork` assigns them inside `__aenter__`,
so a use case that reads one off a session nobody opened is a green unit test
and an `AttributeError` against a customer's database -- which is how
`/v1/shapes` and `/v1/spend` shipped dead in 4a (`50864cf`). This door touches
four repositories in one session: the spend the cap is summed from, the runs the
busy check reads, the workflows the job comes from, and the runs the claim is
written to.

**And the busy check is not what makes one browser have one hand.** It is a
read, and between it and the row existing there are two more awaits; two
presses on one event loop both read free. That is not an argument here, it is
`test_two_presses_at_once_do_not_both_get_the_browser` below, which fails
without the UNIQUE partial index migration 0043 builds. No fake can host that
test: `FakeUnitOfWork` never yields, which is exactly why every sequential
suite is green.

And `in_flight` is the one refusal a fake gets right by accident. It is an index
read with three predicates -- tenant, device, and `outcome = 'running'` -- and
the third is the one that decides whether a browser whose last run FINISHED can
ever be used again. A fake filters a dict in Python and cannot be wrong about
it; the store can.

**And the Yes at the foot of the file**, where the first tap winning is the
store's own rule and not the caller's: `ON CONFLICT DO NOTHING` with
`RETURNING` is what makes the first authorisation the one in the audit, and a
fake that checks a dict for the key gets it right by accident.

The model is the only fake left, and nothing is spawned: `_Handed` records the
work and closes it, so no run drives a browser after the request that started it
has gone.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.context import RequestContext
from sro.application.execution.pursuits import Pursuits
from sro.application.ports.repositories import UnitOfWork
from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.execution.workflow_run import RunStep, WorkflowRun, already_running
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

TENANT = TenantId("acme")
LAPTOP = DeviceId("dev-1")

NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
"""Not today: the cap is summed from the midnight before this instant, and a
door that read a clock of its own would agree with a fixture dated now."""

CAP = 3.25


class _Attached:
    async def send_text(self, text: str) -> None:  # pragma: no cover - never called
        raise AssertionError("this route must not talk to a browser")


class _Handed(Pursuits):
    """What the route handed over, never run. The loop is `test_runner.py`'s;
    what matters here is that a claim reached the store before it."""

    def __init__(self) -> None:
        super().__init__()
        self.handed_over = 0

    def spawn(self, coroutine: Coroutine[object, object, None]) -> None:
        self.handed_over += 1
        coroutine.close()


class _RealSessionContainer(_FakeContainer):
    """The unit suite's container with the store swapped for the real one: the
    use case is built exactly as production builds it, and the unit of work it
    is handed has no repositories until its session opens."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        # Before `super().__init__`, which builds use cases and so calls
        # `unit_of_work` below.
        self._session_factory = session_factory
        super().__init__(FakeUnitOfWork())
        self.settings = Settings(daily_usd_cap=CAP, _env_file=None)
        self.clock = FakeClock(NOW)
        self.asker = FakeAsker()
        self.pursuits = _Handed()
        self.agent_sockets.attach(TENANT, LAPTOP, _Attached())

    def unit_of_work(self) -> UnitOfWork:
        return SqlUnitOfWork(self._session_factory)


@pytest.fixture
def container(session_factory: async_sessionmaker[AsyncSession]) -> _RealSessionContainer:
    return _RealSessionContainer(session_factory)


@pytest.fixture
async def client(container: _RealSessionContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


async def _hold(container: _RealSessionContainer) -> None:
    """One mined job in the real store, five steps and one declared value."""
    async with SqlUnitOfWork(container._session_factory) as uow:
        await uow.workflows.save(
            Workflow(
                id="wfl_1",
                tenant=TENANT.value,
                title="create a work area",
                narrative="the operator created a work area",
                steps=[Step(order=n, says=f"step {n}", system=None) for n in range(5)],
                parameters=[{"name": "clientCode", "seen_values": ["NEWTESTS"]}],
            )
        )
        await uow.commit()


def _body(**over: object) -> dict[str, object]:
    return {
        "workflow_id": "wfl_1",
        "device_id": LAPTOP.value,
        "values": {"clientCode": "  NEWTESTS  "},
        **over,
    }


async def test_a_press_claims_a_row_the_store_hands_back_whole(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """One session, four repositories, and the row committed before the answer.

    Read back through a second session on purpose: an uncommitted claim is
    invisible to the next request, which is the whole reason it is committed
    before anything is spawned.
    """
    await _hold(container)

    made = await client.post("/v1/workflow-runs", json=_body(live=True, allow_focus=False))

    assert made.status_code == 201, made.text
    async with SqlUnitOfWork(container._session_factory) as uow:
        stored = await uow.workflow_runs.get(TENANT, made.json()["id"])
    assert stored is not None
    assert stored.outcome == "running" and stored.finished_at is None
    # Every request field through the real mapper, at a value that is not its
    # default: a column dropped in the mapping is invisible to a fake that
    # holds the object it was handed.
    assert stored.values == {"clientCode": "NEWTESTS"}
    assert stored.live is True and stored.allow_focus is False
    assert stored.from_step == 0
    assert stored.device_id == LAPTOP.value
    assert stored.started_by == made.json()["started_by"]


async def test_a_press_mid_job_stores_the_step_the_operator_reached(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """`from_step` is task 4's column, and the guard in `run_workflow` compares
    a re-press against it. A claim whose step never reached the store refuses
    every mid-job re-press, and only a real round trip can say it did."""
    await _hold(container)

    made = await client.post("/v1/workflow-runs", json=_body(from_step=4))

    assert made.status_code == 201, made.text
    async with SqlUnitOfWork(container._session_factory) as uow:
        stored = await uow.workflow_runs.get(TENANT, made.json()["id"])
    assert stored is not None and stored.from_step == 4


async def test_a_second_press_on_a_busy_browser_is_refused_by_the_real_index(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The refusal a fake gets right by accident. Three predicates in a WHERE
    clause, and the run this browser is already driving is named in the answer."""
    await _hold(container)
    first = await client.post("/v1/workflow-runs", json=_body())

    landed = await client.post("/v1/workflow-runs", json=_body())

    assert landed.status_code == 409
    assert first.json()["id"] in landed.json()["detail"]
    async with SqlUnitOfWork(container._session_factory) as uow:
        assert len(await uow.workflow_runs.for_workflow(TENANT, "wfl_1")) == 1


async def test_a_browser_whose_last_run_finished_may_be_pressed_again(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """`outcome = 'running'` is the third predicate, and the one that decides
    whether a browser is usable tomorrow. Without it the first run of the day
    locks the browser for the life of the row."""
    await _hold(container)
    first = await client.post("/v1/workflow-runs", json=_body())
    async with SqlUnitOfWork(container._session_factory) as uow:
        finished = await uow.workflow_runs.get(TENANT, first.json()["id"])
        assert finished is not None
        finished.outcome = "held"
        finished.finished_at = NOW.isoformat()
        await uow.workflow_runs.save(finished)
        await uow.commit()

    again = await client.post("/v1/workflow-runs", json=_body())

    assert again.status_code == 201, again.text
    assert again.json()["id"] != first.json()["id"]


async def test_the_cap_is_summed_over_the_real_tables(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """429 out of a number no fake in this file plants: the day's spend is a
    sum across four tables in the store, and the door refuses before it claims
    anything."""
    await _hold(container)
    async with SqlUnitOfWork(container._session_factory) as uow:
        await uow.chats.record(
            ChatReading(
                id="cht_1",
                tenant=TENANT.value,
                at=NOW.replace(hour=10).isoformat(),
                cost_usd=3.30,
            )
        )
        await uow.commit()

    landed = await client.post("/v1/workflow-runs", json=_body())

    assert landed.status_code == 429
    assert container.pursuits.handed_over == 0
    async with SqlUnitOfWork(container._session_factory) as uow:
        assert await uow.workflow_runs.for_workflow(TENANT, "wfl_1") == ()


async def test_two_presses_at_once_do_not_both_get_the_browser(
    container: _RealSessionContainer,
) -> None:
    """The defect the ordering argument was supposed to buy against, and did not.

    `execute` reads `in_flight`, then awaits the workflow lookup and the save
    before the row exists. Every await is a scheduling point, so two overlapping
    presses both read no busy run and both claim. Run before migration 0043 this
    returns two `WorkflowRun`s and no refusal -- two runs driving one window,
    interleaving their clicks into a form neither of them can read back.

    Two separate `StartWorkflowRun`s, each with its own `SqlUnitOfWork` and so
    its own session, because that is what two requests are. Gathered rather than
    awaited in turn: awaited in turn this passes on the busy check alone and
    proves nothing.

    Both sentences are asserted identical to the one the busy check gives, on
    purpose: a caller able to tell "you were late" from "you lost a race" learns
    which of the two answered, and the rare path is the one nobody has seen
    rendered.
    """
    await _hold(container)
    ctx = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("operator"))

    async def press() -> object:
        return await container.start_workflow_run().execute(
            ctx,
            workflow_id="wfl_1",
            device_id=LAPTOP,
            values={"clientCode": "NEWTESTS"},
            live=False,
            allow_focus=True,
        )

    landed = await asyncio.gather(press(), press(), return_exceptions=True)

    claimed = [one for one in landed if not isinstance(one, BaseException)]
    refused = [one for one in landed if isinstance(one, Conflict)]
    assert len(claimed) == 1, f"both presses got the browser: {landed}"
    assert len(refused) == 1, f"the loser was not refused with a Conflict: {landed}"
    async with SqlUnitOfWork(container._session_factory) as uow:
        rows = await uow.workflow_runs.for_workflow(TENANT, "wfl_1")
    assert len(rows) == 1
    assert str(refused[0]) == already_running(LAPTOP.value, rows[0].id)


async def test_a_browser_freed_by_a_finished_run_is_not_held_by_the_index(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The index is partial, and this is the half that says so. A UNIQUE index
    without `WHERE outcome = 'running'` would let a browser run one job ever,
    and every test above it would still pass -- they all press once."""
    await _hold(container)
    for _ in range(3):
        made = await client.post("/v1/workflow-runs", json=_body())
        assert made.status_code == 201, made.text
        async with SqlUnitOfWork(container._session_factory) as uow:
            run = await uow.workflow_runs.get(TENANT, made.json()["id"])
            assert run is not None
            run.outcome, run.finished_at = "held", NOW.isoformat()
            await uow.workflow_runs.save(run)
            await uow.commit()


# --- and the two reads, against the same store -------------------------------


def _row(
    run_id: str,
    *,
    at: str,
    tenant: TenantId = TENANT,
    workflow_id: str = "wfl_1",
    device: DeviceId = LAPTOP,
    outcome: str = "held",
    steps: list[RunStep] | None = None,
) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant=tenant.value,
        workflow_id=workflow_id,
        device_id=device.value,
        values={"clientCode": "NEWTESTS"},
        started_by="night-shift",
        live=True,
        allow_focus=False,
        started_at=at,
        finished_at=None if outcome == "running" else at,
        outcome=outcome,
        steps=steps or [],
    )


async def _plant(container: _RealSessionContainer, *runs: WorkflowRun) -> None:
    async with SqlUnitOfWork(container._session_factory) as uow:
        for run in runs:
            await uow.workflow_runs.save(run)
        await uow.commit()


async def test_the_list_is_newest_first_out_of_the_real_store(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """Four rows including a tie, because ordering is what a fake gets right by
    accident: it sorts a dict in Python and cannot be wrong about the direction
    of a `timestamptz`, or about what Postgres returns for two runs that share
    an instant with nothing breaking the tie.

    `23:30+02:00` is half past nine -- later than everything as text, third as
    an instant. And newest first is the RIG's order, not `for_workflow`'s: the
    same store answers the two reads in opposite directions on purpose.
    """
    await _plant(
        container,
        # `run_a` first and answered second: a tie planted the way the heap
        # already returns it is a tie the tie-break never has to break.
        _row("run_a", at="2025-02-11T23:00:00+00:00"),
        _row("run_b", at="2025-02-11T23:00:00+00:00"),
        _row("run_text_first", at="2025-02-11T23:30:00+02:00"),
        _row("run_early", at="2025-02-11T10:00:00+00:00"),
    )

    listed = await client.get("/v1/workflow-runs")

    assert listed.status_code == 200, listed.text
    assert [one["id"] for one in listed.json()] == [
        "run_b",
        "run_a",
        "run_text_first",
        "run_early",
    ]


async def test_the_cap_is_the_querys_and_it_keeps_the_newest(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """`LIMIT` after the `ORDER BY`, in the store. A route slicing in Python
    would load every run of the tenant with all of its steps to answer with two
    of them -- the defect `tallies` exists to have removed once already."""
    await _plant(
        container,
        _row("run_newest", at="2025-02-11T23:00:00+00:00"),
        _row("run_middle", at="2025-02-11T22:00:00+00:00"),
        _row("run_oldest", at="2025-02-11T21:00:00+00:00"),
    )

    listed = await client.get("/v1/workflow-runs", params={"limit": 2})

    assert [one["id"] for one in listed.json()] == ["run_newest", "run_middle"]


async def test_the_queue_is_the_join_the_store_makes(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """`awaiting` is a join across two tables with three predicates -- the
    tenant, `outcome = 'running'` on the run and `verdict = 'awaiting'` on the
    step -- and the middle one decides whether a step left parked on a run that
    was aborted sits in a supervisor's queue forever, asking for a tap that can
    no longer let anything out.

    Two browsers, because one browser holds one running run since 0043, and
    because the queue is the parked steps across browsers: anyone may answer a
    parked run.
    """
    await _plant(
        container,
        _row(
            "run_parked",
            at="2025-02-11T23:00:00+00:00",
            outcome="running",
            steps=[
                RunStep(order=1, says="confirm the write", verdict="awaiting"),
                RunStep(order=2, says="a step nobody waits on", verdict="done"),
                RunStep(order=3, says="and let the second out", verdict="awaiting"),
            ],
        ),
        _row(
            "run_going",
            at="2025-02-11T23:00:00+00:00",
            outcome="running",
            device=DeviceId("dev-2"),
        ),
        _row(
            "run_aborted",
            at="2025-02-11T23:00:00+00:00",
            outcome="aborted",
            steps=[RunStep(order=0, says="left awaiting on a dead run", verdict="awaiting")],
        ),
    )

    listed = await client.get("/v1/workflow-runs", params={"awaiting": "true"})

    assert [one["id"] for one in listed.json()] == ["run_parked"]
    # Every parked step, `ord` ascending, and not only the deepest: plan 4b's
    # ruling, read back through the real steps join.
    (row,) = listed.json()
    waiting = [step for step in row["steps"] if step["verdict"] == "awaiting"]
    assert [(step["order"], step["says"]) for step in waiting] == [
        (1, "confirm the write"),
        (3, "and let the second out"),
    ]


async def test_a_run_is_read_back_whole_from_the_real_store(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """Through the real mapper, at values that are not defaults: a column
    dropped in the mapping is invisible to a fake holding the object it was
    handed."""
    await _plant(
        container,
        _row(
            "run_1",
            at="2025-02-11T23:00:00+00:00",
            steps=[RunStep(order=2, says="click Save", verdict="held")],
        ),
    )

    read = await client.get("/v1/workflow-runs/run_1")

    assert read.status_code == 200, read.text
    body = read.json()
    assert body["id"] == "run_1" and body["workflow_id"] == "wfl_1"
    assert body["values"] == {"clientCode": "NEWTESTS"}
    assert body["live"] is True and body["allow_focus"] is False
    assert body["outcome"] == "held" and body["finished_at"] is not None
    assert [(step["order"], step["says"]) for step in body["steps"]] == [(2, "click Save")]


async def test_a_run_of_another_tenant_is_a_404_from_the_real_store(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The tenant predicate is in the WHERE clause, not a Python filter over
    what came back. A 403 would confirm the id exists, and run ids are
    unguessable."""
    await _plant(
        container,
        _row("run_mine", at="2025-02-11T23:00:00+00:00"),
        _row(
            "run_theirs",
            at="2025-02-11T23:00:00+00:00",
            tenant=TenantId("rival"),
            device=DeviceId("dev-8"),
        ),
    )

    theirs = await client.get("/v1/workflow-runs/run_theirs")

    assert theirs.status_code == 404
    assert (await client.get("/v1/workflow-runs/run_mine")).status_code == 200
    assert [one["id"] for one in (await client.get("/v1/workflow-runs")).json()] == ["run_mine"]


# --- and the stop button, through the same store -----------------------------


async def test_a_stop_reaches_the_run_the_store_holds(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The lookup a stop refuses on is a real one.

    `FakeUnitOfWork` builds its repositories in `__init__` and `SqlUnitOfWork`
    assigns them inside `__aenter__`, so a use case reading `workflow_runs` off
    a session nobody opened is a green unit test and an `AttributeError`
    against a customer's database -- which is how `/v1/shapes` and `/v1/spend`
    shipped dead in 4a.

    Three answers in one test, because a refusal proved alone passes against a
    door that refuses everything and against one that was never registered: an
    id of the right shape that names nothing is a 404, a run of another tenant
    is the same 404, and the tenant's own running row is stopped.

    The row is read back afterwards and still says `running`: the task driving
    the browser closes it, and a route that wrote the outcome itself would be
    racing the step it just interrupted.
    """
    await _hold(container)
    pressed = await client.post("/v1/workflow-runs", json=_body())
    assert pressed.status_code == 201, pressed.text
    claimed = pressed.json()["id"]
    await _plant(
        container,
        _row(
            "run_theirs",
            at="2025-02-11T23:00:00+00:00",
            tenant=TenantId("rival"),
            device=DeviceId("dev-8"),
            outcome="running",
        ),
    )

    missing = await client.post("/v1/workflow-runs/run_nope/abort")
    theirs = await client.post("/v1/workflow-runs/run_theirs/abort")
    landed = await client.post(f"/v1/workflow-runs/{claimed}/abort")

    assert missing.status_code == 404 and theirs.status_code == 404
    assert theirs.json()["detail"] == missing.json()["detail"]
    assert landed.status_code == 202, landed.text
    assert container.stops.asked(claimed)
    assert not container.stops.asked("run_theirs")
    async with SqlUnitOfWork(container._session_factory) as uow:
        stored = await uow.workflow_runs.get(TENANT, claimed)
    assert stored is not None and stored.outcome == "running"


async def test_a_finished_run_in_the_store_cannot_be_stopped(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """`outcome` comes off the real column, not off an object the caller handed
    a fake. Answering "stopping" for a run that already ended is a console
    reporting something that did not happen."""
    await _plant(
        container,
        _row("run_done", at="2025-02-11T23:00:00+00:00", outcome="aborted"),
        _row(
            "run_going",
            at="2025-02-11T23:00:00+00:00",
            outcome="running",
            device=DeviceId("dev-2"),
        ),
    )

    landed = await client.post("/v1/workflow-runs/run_done/abort")

    assert landed.status_code == 409
    assert "aborted" in landed.json()["detail"]
    assert not container.stops.asked("run_done")
    assert (await client.post("/v1/workflow-runs/run_going/abort")).status_code == 202


# --- and the Yes, where the first tap winning is the store's own rule --------


APPROVER = "the-secret-the-laptop-was-minted"


def _parked_row(run_id: str, *ords: int, device: DeviceId = LAPTOP) -> WorkflowRun:
    return _row(
        run_id,
        at="2025-02-11T23:00:00+00:00",
        outcome="running",
        device=device,
        steps=[
            RunStep(order=order, says=f"click Save at step {order}", verdict="awaiting")
            for order in ords
        ],
    )


async def _register(container: _RealSessionContainer, device: DeviceId) -> None:
    async with SqlUnitOfWork(container._session_factory) as uow:
        await uow.devices.add(f.device(id=device, label=device.value, secret=APPROVER))
        await uow.commit()


async def _waiting_on(container: _RealSessionContainer, run_id: str) -> asyncio.Task[bool]:
    container.approvals.register(run_id)
    task = asyncio.ensure_future(container.approvals.wait_for(run_id, timeout=5.0))
    await asyncio.sleep(0)
    return task


async def test_a_tap_records_the_deepest_parked_step_in_the_store_and_releases_it(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """Both halves, through the real approvals table and a real parked task.

    `FakeUnitOfWork` builds its repositories in `__init__` and `SqlUnitOfWork`
    assigns them inside `__aenter__`, so a use case reading `workflow_runs` off
    a session nobody opened is a green unit test and an `AttributeError`
    against a customer's database.

    Which step, out of three parked, because `ORDER BY ord DESC LIMIT 1` is the
    rule a tap follows and it is NOT `awaiting`'s -- that one returns every
    parked step, ascending, and a route that reused it would authorise the
    shallowest.
    """
    await _plant(container, _parked_row("run_parked", 0, 2, 5))
    waiting = await _waiting_on(container, "run_parked")
    # Off the row's own `started_at`, which the fixture and this clock share:
    # a route recording the run's instant rather than the tap's would agree
    # with an assertion made at the default.
    container.clock.advance(1800)

    landed = await client.post("/v1/workflow-runs/run_parked/approve")

    assert landed.status_code == 200, landed.text
    assert landed.json() == {"order": 5, "first": True}
    assert await waiting is True
    async with SqlUnitOfWork(container._session_factory) as uow:
        recorded = await uow.workflow_runs.approvals("run_parked")
    assert [order for order, _, _ in recorded] == [5]
    # WHEN, through the real `timestamptz` and back out as text. The container
    # injects the clock for this one column and nothing else read it.
    assert recorded[0][1] == container.clock.now().isoformat()


async def test_the_second_tap_does_not_overwrite_the_first_authorisation(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The rule the fake gets right by accident. `ON CONFLICT DO NOTHING` with
    `RETURNING` is what makes the first tap the one in the audit -- and what
    makes the second one say so instead of claiming the row.

    A write rescued to the second rung parks at the same step and takes a
    second tap. It is not refused: the run really is parked again, and a 409
    would leave it sitting out its five minutes. But the browser and the
    instant on the row stay the first tapper's.
    """
    await _register(container, LAPTOP)
    await _plant(container, _parked_row("run_rescued", 2))
    container.clock.advance(1800)
    tapped_at = container.clock.now().isoformat()

    first = await client.post(
        "/v1/workflow-runs/run_rescued/approve",
        params={"device_id": LAPTOP.value},
        headers={"X-Device-Secret": APPROVER},
    )
    # A different instant, so "overwritten" and "stood" are two values here.
    container.clock.advance(1800)
    second = await client.post("/v1/workflow-runs/run_rescued/approve")

    assert first.status_code == 200 and first.json() == {"order": 2, "first": True}
    assert second.status_code == 200, second.text
    assert second.json() == {"order": 2, "first": False}
    async with SqlUnitOfWork(container._session_factory) as uow:
        recorded = await uow.workflow_runs.approvals("run_rescued")
    # One row, and it names the browser that got there first -- not the second
    # tap, which named none at all.
    assert len(recorded) == 1
    assert recorded[0][0] == 2 and recorded[0][2] == LAPTOP.value
    assert recorded[0][1] == tapped_at


async def test_a_browser_driving_another_run_cannot_release_this_ones_write(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The check `WorkflowRunRepository.approve`'s tenant-blindness is
    predicated on, through the real device registry that resolves the browser.

    Three answers in one test, because a refusal proved alone passes against a
    door that refuses everything and one that was never registered: another
    tenant's parked run is a 404, another browser's is a 403, and the browser
    that is driving this run releases it. Nothing is written by either refusal
    and the wait is still parked after both.
    """
    await _register(container, LAPTOP)
    await _register(container, DeviceId("dev-2"))
    await _plant(
        container,
        _parked_row("run_mine", 1),
        _row(
            "run_theirs",
            at="2025-02-11T23:00:00+00:00",
            tenant=TenantId("rival"),
            device=DeviceId("dev-8"),
            outcome="running",
            steps=[RunStep(order=1, says="click Save", verdict="awaiting")],
        ),
    )
    waiting = await _waiting_on(container, "run_mine")
    proving = {"headers": {"X-Device-Secret": APPROVER}}

    theirs = await client.post(
        "/v1/workflow-runs/run_theirs/approve", params={"device_id": LAPTOP.value}, **proving
    )
    stranger = await client.post(
        "/v1/workflow-runs/run_mine/approve", params={"device_id": "dev-2"}, **proving
    )
    driving = await client.post(
        "/v1/workflow-runs/run_mine/approve", params={"device_id": LAPTOP.value}, **proving
    )

    assert theirs.status_code == 404, theirs.text
    assert stranger.status_code == 403, stranger.text
    assert driving.status_code == 200, driving.text
    assert await waiting is True
    async with SqlUnitOfWork(container._session_factory) as uow:
        assert await uow.workflow_runs.approvals("run_theirs") == ()
        recorded = await uow.workflow_runs.approvals("run_mine")
    assert len(recorded) == 1 and recorded[0][2] == LAPTOP.value


async def test_a_run_with_nothing_parked_is_refused_out_of_the_real_rows(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """`verdict` and `outcome` off real columns, not off an object handed to a
    fake. Approving a step nobody parked records a person authorising a write
    that was never withheld."""
    await _plant(
        container,
        _row(
            "run_walking",
            at="2025-02-11T23:00:00+00:00",
            outcome="running",
            steps=[RunStep(order=0, says="open it", verdict="done", verdict_by="agent")],
        ),
        _parked_row("run_parked", 1, device=DeviceId("dev-3")),
    )

    landed = await client.post("/v1/workflow-runs/run_walking/approve")

    assert landed.status_code == 409, landed.text
    async with SqlUnitOfWork(container._session_factory) as uow:
        assert await uow.workflow_runs.approvals("run_walking") == ()
    assert (await client.post("/v1/workflow-runs/run_parked/approve")).status_code == 200


async def test_a_violation_that_is_not_the_index_is_not_reported_as_a_busy_browser(
    container: _RealSessionContainer,
) -> None:
    """The catch names one constraint, and this is the one that is not it.

    `except IntegrityError` was unqualified: ANY integrity violation was
    reported to the operator as "dev-1 is already running a run this press
    cannot see" -- a sentence about a different problem, and one that names no
    run at all, because `in_flight` finds nothing running and the detail
    renders `None`. Worse, the handler rolls the caller's transaction back on
    the way past, so the real cause is gone by the time the response is
    written. `started_by` is NOT NULL and no legal press can violate it, which
    is exactly why this needs a test rather than a reader.
    """
    async with SqlUnitOfWork(container._session_factory) as uow:
        run = WorkflowRun(
            id="run_broken",
            tenant=TENANT.value,
            workflow_id="wfl_1",
            device_id=LAPTOP.value,
            values={},
            started_by=None,
            live=False,
            allow_focus=False,
            started_at=NOW.isoformat(),
        )
        with pytest.raises(IntegrityError) as raised:
            await uow.workflow_runs.save(run)

    assert "started_by" in str(raised.value)
    assert "already running" not in str(raised.value)
