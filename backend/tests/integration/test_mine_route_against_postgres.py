"""`POST /v1/mine` through the real container, against real Postgres.

The unit suite cannot settle this one. `FakeUnitOfWork` builds its repositories
in `__init__` and `SqlUnitOfWork` assigns them inside `__aenter__`, so a use
case that reads a repository off a session nobody opened is a green unit test
and an `AttributeError` against a customer's database -- which is exactly how
`/v1/shapes` and `/v1/spend` shipped dead in 4a (`50864cf`). This pass reads
five repositories and writes two, and its cap check and its mining share one
session on purpose.

The model is the only fake left: a stub `Asker` answering what a real one
answered, at the rig's own $0.01. Everything else -- the window, the checker,
the identity resolver, the parameter learner, the `mining_passes` mapper -- is
what production runs.

Two passes rather than one, so `learned_parameters` is EARNED. Migration 0041
added that column because every pass computed the figure and the persistence
layer dropped it; a single pass learns nothing by definition, so a test that
made one call could not tell a working column from a dropped one.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.ports.repositories import UnitOfWork
from sro.config import Settings
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import Answer
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

TENANT = TenantId("acme")
HOST = "http://127.0.0.1:63319"
NOW = datetime(2025, 2, 11, 23, 0, tzinfo=UTC)
"""Not today, for the reason every other fixture in this project is not: the
cap is summed from the midnight before this instant, and a pass that read a
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


def _proposal(cites: list[str]) -> dict[str, object]:
    return {
        "title": "create a work operation",
        "narrative": "the operator created a work operation",
        "systems": [HOST],
        "steps": [{"order": 0, "cites": cites, "says": "do it", "system": HOST, "parameters": []}],
        "parameters": [],
        "same_as": None,
        "unproven": [],
    }


def _redone(rows: list[Gesture]) -> list[Gesture]:
    """The same job done again, with something else typed into the same control.

    A second doing means NEW gestures -- that is why identity matches on shape
    rather than on cited ids, and why a diff has two values to compare.
    """
    return [
        replace(
            row,
            id=f"{row.id}_again",
            at=row.at + 10_000.0,
            action=(
                replace(row.action, value="SOMETHING-ELSE")
                if row.action.kind == "type" and row.action.value
                else row.action
            ),
        )
        for row in rows
    ]


@pytest.fixture
def container(session_factory: async_sessionmaker[AsyncSession]) -> _RealSessionContainer:
    # One instance for the whole test: the two passes below have to share a
    # queue of model answers, and a fresh container per request would hand the
    # second one the first one's.
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


async def test_a_day_is_mined_and_billed_through_one_real_session(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """Two doings of one job, through the door, against Postgres.

    The first keeps a workflow; the second recognises it and keeps nothing
    while learning what varies in it. Both leave a `mining_passes` row, and the
    second row carries `learned_parameters` -- the assertion the SQL mapper can
    fail on its own, and the one no fake can settle.
    """
    first = _gestures(TENANT.value)
    again = _redone(first)
    async with SqlUnitOfWork(container._session_factory) as uow:
        await uow.gestures.add_gestures(tuple(first))
        await uow.commit()

    container.asker = FakeAsker(
        Answer(data={"workflows": [_proposal([g.id for g in first])]}, cost_usd=0.01),
        Answer(data={"workflows": [_proposal([g.id for g in again])]}, cost_usd=0.01),
    )

    one = await client.post("/v1/mine")
    assert one.status_code == 200, one.text
    assert one.json()["kept"] == 1
    assert one.json()["learned_parameters"] == 0, "one doing cannot name a parameter"

    async with SqlUnitOfWork(container._session_factory) as uow:
        await uow.gestures.add_gestures(tuple(again))
        await uow.commit()

    two = await client.post("/v1/mine")
    assert two.status_code == 200, two.text
    assert two.json()["kept"] == 0, "it is the same job, not a new one"
    assert two.json()["learned_parameters"] >= 1, "and this time it knows what varies"

    async with SqlUnitOfWork(container._session_factory) as uow:
        rows = await uow.workflows.passes(TENANT)
    assert len(rows) == 2
    assert sorted(row.learned_parameters for row in rows) == [
        0,
        two.json()["learned_parameters"],
    ], "the figure reached the row and not only the wire"
    assert [row.cost_usd for row in rows] == [0.01, 0.01]
    # The receipt names the row it is a receipt for. A `pass_id` joined to
    # nothing is the one field that would make the whole body useless, and
    # `pas_`-shaped is not the same as `pas_`-correct.
    assert sorted(row.id for row in rows) == sorted([one.json()["pass_id"], two.json()["pass_id"]])


async def test_the_cap_is_read_off_the_same_session_the_pass_writes_through(
    container: _RealSessionContainer, client: httpx.AsyncClient
) -> None:
    """The 4a defect, aimed at this door. `over_cap` reads `uow.spend` and
    `mine` writes through the same unit of work, so a cap checked on a second
    unit of work nobody entered is an `AttributeError` here and invisible in
    the unit suite.

    Nothing is planted: an empty tenant reaches every repository this route
    touches, which is all it takes -- the defect fires on the first attribute
    and never reaches a query.
    """
    container.settings = Settings(daily_usd_cap=0.0, _env_file=None)
    container.asker = FakeAsker(Answer(data={"workflows": []}, cost_usd=0.01))

    answered = await client.post("/v1/mine")

    assert answered.status_code == 429, answered.text
    assert "$0.0000 of $0.00" in answered.json()["detail"]


async def test_a_deployment_with_no_model_is_refused_by_the_real_container(
    client: httpx.AsyncClient,
) -> None:
    """503 with the two settings to go and set. `_RealSessionContainer` has no
    asker, which is what a deployment with no key has.

    This asserts the status and nothing more. That the refusal happens BEFORE a
    session is opened is a different claim, and it is held by
    `test_the_missing_model_is_noticed_before_a_connection_is_taken` in the
    unit file, over a unit of work whose `__aenter__` raises -- which is a
    thing a real `SqlUnitOfWork` cannot be made to do from here.
    """
    answered = await client.post("/v1/mine")

    assert answered.status_code == 503, answered.text
    assert "gemini_api_key" in answered.json()["detail"]
