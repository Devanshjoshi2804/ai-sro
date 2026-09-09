"""`POST /v1/workflow-runs` through the real container, against real Postgres.

The unit suite cannot settle two of these. `FakeUnitOfWork` builds its
repositories in `__init__` and `SqlUnitOfWork` assigns them inside `__aenter__`,
so a use case that reads one off a session nobody opened is a green unit test
and an `AttributeError` against a customer's database -- which is how
`/v1/shapes` and `/v1/spend` shipped dead in 4a (`50864cf`). This door touches
four repositories in one session: the spend the cap is summed from, the runs the
busy check reads, the workflows the job comes from, and the runs the claim is
written to.

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

from collections.abc import AsyncIterator, Coroutine
from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.execution.pursuits import Pursuits
from sro.application.ports.repositories import UnitOfWork
from sro.config import Settings
from sro.domain.chat.reading import ChatReading
from sro.domain.shared.identifiers import DeviceId, TenantId
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
