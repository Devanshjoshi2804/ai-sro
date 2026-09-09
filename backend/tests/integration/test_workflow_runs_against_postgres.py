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
    assert container.pursuits.handed_over == 0  # type: ignore[attr-defined]
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
