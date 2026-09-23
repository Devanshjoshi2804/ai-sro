"""`POST /v1/chat` through the real container, against real Postgres.

The unit suite cannot settle this one. `FakeUnitOfWork` builds its repositories
in `__init__` and `SqlUnitOfWork` assigns them inside `__aenter__`, so a use
case that reads a repository off a session nobody opened is a green unit test
and an `AttributeError` against a customer's database -- which is exactly how
`/v1/shapes` and `/v1/spend` shipped dead in 4a (`50864cf`). This reading
touches three repositories -- the spend the cap is summed from, the workflows
it is read against, and the `chats` row it bills -- and all three share one
session on purpose.

The model is the only fake left: a stub `Asker` answering what a real one
answered. Everything else -- the workflow mapper, the spend sum across four
tables, the `chats` mapper -- is what production runs.

Two readings rather than one, so the bill is EARNED: the second is refused by a
cap the first one spent, which is a number no fake in this file plants and only
the real `SpendRepository` can produce.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.ports.repositories import UnitOfWork
from sro.config import Settings
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer, price
from sro.domain.skill.workflow import Step, Workflow
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.gemini.asker import GeminiAsker
from sro.infrastructure.gemini.metered import Meter, Metered
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

TENANT = TenantId("acme")
SAID = "create a work area for zone 4"

NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
"""Not today, for the reason every other fixture in this project is not: the
cap is summed from the midnight before this instant, and a reading that read a
clock of its own would agree with a fixture dated now by the calendar."""


class _RealSessionContainer(_FakeContainer):
    """The unit suite's container with the one fake this route turns on swapped
    for the real thing: the use case is built exactly as production builds it,
    and the unit of work it is handed has no repositories until its session
    opens."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        # Before `super().__init__`, which builds use cases and so calls
        # `unit_of_work` below.
        self._session_factory = session_factory
        super().__init__(FakeUnitOfWork())
        self.settings = Settings(daily_usd_cap=100.0, _env_file=None)
        self.clock = FakeClock(NOW)

    def unit_of_work(self) -> UnitOfWork:
        return SqlUnitOfWork(self._session_factory)


@pytest.fixture
def container(session_factory: async_sessionmaker[AsyncSession]) -> _RealSessionContainer:
    # One instance for the whole test: the two readings below share a queue of
    # model answers, and a fresh container per request would hand the second
    # one the first one's.
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


def _answer(workflow_id: str | None, values: list[dict[str, str]], **over: object) -> Answer:
    return Answer(
        data={"workflow_id": workflow_id, "values": values, "missing": []},
        **over,
    )


async def _hold(container: _RealSessionContainer) -> None:
    """One mined job in the real store, with two parameters -- so `values` and
    `missing` come back as two different answers rather than one twice."""
    async with SqlUnitOfWork(container._session_factory) as uow:
        await uow.workflows.save(
            Workflow(
                id="wfl_1",
                tenant=TENANT.value,
                title="create a work area",
                narrative="the operator created a work area",
                steps=[Step(order=0, says="s", system=None, cites=["ges_1"])],
                parameters=[
                    # Both marked as the form marks them. This test is about a
                    # sentence that supplied one field and not the other, and
                    # since 2026-09-22 only a field the page demands is missing.
                    {"name": "areaName", "seen_values": ["NEWTESTS"], "required": True},
                    {"name": "zone", "seen_values": ["3"], "required": True},
                ],
            )
        )
        await uow.commit()


async def test_a_sentence_is_read_and_billed_through_one_real_session(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The whole door, against Postgres: the workflow is read out of the real
    store, the offer is built from its real parameters, and the bill lands in a
    real `chats` row.

    The row is the assertion the SQL mapper can fail on its own and no fake can
    settle -- and the sentence NOT being in it is the promise the table has no
    column for.
    """
    await _hold(container)
    container.asker = FakeAsker(
        _answer(
            "wfl_1",
            [{"name": "areaName", "value": "ZONE4"}],
            in_tokens=900,
            out_tokens=140,
            thought_tokens=40,
            cost_usd=0.0007,
        )
    )

    answered = await client.post("/v1/chat", json={"utterance": SAID})

    assert answered.status_code == 200, answered.text
    body = answered.json()
    assert body["workflow_id"] == "wfl_1"
    assert body["values"] == {"areaName": "ZONE4"}
    assert body["missing"] == ["zone"]
    assert (body["in_tokens"], body["out_tokens"], body["thought_tokens"]) == (900, 140, 40)
    assert (body["cost_usd"], body["unpriced"], body["error"]) == (0.0007, False, None)

    async with SqlUnitOfWork(container._session_factory) as uow:
        rows = await uow.chats.since(TENANT, since=NOW.replace(hour=0).isoformat())
    (row,) = rows
    assert (row.workflow_id, row.cost_usd, row.in_tokens) == ("wfl_1", 0.0007, 900)
    assert SAID not in str(row), "the operator's sentence reached the store"


async def test_the_cap_is_read_off_the_same_store_the_meter_bills_into(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The cap earned rather than set, through the real metered client.

    The first reading is billed by the meter into `model_spend`; the cap is
    then dropped below what it cost and the second is refused by the sum the
    real `SpendRepository` computed. The tenant the bill lands on is the one
    the request was authenticated as -- nothing in the door passes it along.
    """
    await _hold(container)
    model = container.settings.gemini_plan_model
    reading = json.dumps({"workflow_id": "wfl_1", "values": [], "missing": []})

    class _Models:
        async def generate_content(self, **_: object) -> object:
            return SimpleNamespace(
                text=reading,
                candidates=[],
                usage_metadata=SimpleNamespace(
                    prompt_token_count=100_000,
                    candidates_token_count=100_000,
                    thoughts_token_count=0,
                    tool_use_prompt_token_count=None,
                ),
            )

    meter = Meter(
        lambda: SqlUnitOfWork(container._session_factory), clock=FakeClock(NOW), cap_usd=-1.0
    )
    container.asker = GeminiAsker(
        api_key="",
        client=Metered(SimpleNamespace(aio=SimpleNamespace(models=_Models())), meter),
    )
    cost = price(model, 100_000, 100_000)

    first = await client.post("/v1/chat", json={"utterance": SAID})
    assert first.status_code == 200, first.text

    container.settings = Settings(daily_usd_cap=round(cost - 0.01, 2), _env_file=None)

    refused = await client.post("/v1/chat", json={"utterance": SAID})

    assert refused.status_code == 429, refused.text
    assert f"${cost:.4f} of" in refused.json()["detail"]
    async with SqlUnitOfWork(container._session_factory) as uow:
        assert (await uow.spend.today(TENANT, now=NOW)).cost_usd == pytest.approx(cost)


async def test_a_deployment_with_no_model_is_refused_by_the_real_container(
    client: httpx.AsyncClient,
) -> None:
    """503 with the two settings to go and set. `_RealSessionContainer` has no
    asker, which is what a deployment with no key has.

    This asserts the status and nothing more. That the refusal happens BEFORE a
    session is opened is a different claim, held by
    `test_the_missing_model_is_noticed_before_a_connection_is_taken` in the
    unit file over a unit of work whose `__aenter__` raises -- which is a thing
    a real `SqlUnitOfWork` cannot be made to do from here.
    """
    answered = await client.post("/v1/chat", json={"utterance": SAID})

    assert answered.status_code == 503, answered.json()["detail"]
    assert "gemini_api_key" in answered.json()["detail"]
