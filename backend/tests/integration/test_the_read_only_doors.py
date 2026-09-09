"""`/v1/shapes` and `/v1/spend`, answered by a real session.

Both shipped reading a repository off a `SqlUnitOfWork` nobody had entered.
That is an `AttributeError` and a 500 against a real database, because the
real class assigns its repositories inside `__aenter__` -- and every route
test in the plan passed, because `FakeUnitOfWork` builds its repositories in
`__init__` and answers entered or not.

So the assertion is the unglamorous one: 200, with a real unit of work behind
it. Nothing is planted. An empty tenant reaches every repository these two
routes touch -- `workflow_runs.tallies`, `workflows.known`, `spend.today` --
which is all it takes, because the defect fires on the first attribute and
never reaches a query. A fixture would only test the queries, which
`test_spend_and_audit_reads.py` already does against the same Postgres.

The unit suite cannot hold this test: its fake IS the thing that is too
permissive. `tests/unit/fakes.py` was tightened in the same commit so that a
future use case forgetting `async with` fails there too, but the class of
defect is one only a real session can settle.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.ports.repositories import UnitOfWork
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for


class _RealSessionContainer(_FakeContainer):
    """The unit suite's container with the one fake these routes turn on
    swapped for the real thing: every use case is built exactly as production
    builds it, and the unit of work it is handed has no repositories until
    its session opens."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        # Before `super().__init__`, which builds use cases and so calls
        # `unit_of_work` below.
        self._session_factory = session_factory
        super().__init__(FakeUnitOfWork())

    def unit_of_work(self) -> UnitOfWork:
        return SqlUnitOfWork(self._session_factory)


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: _RealSessionContainer(session_factory)
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


async def test_shapes_is_answered_by_a_real_session(client: httpx.AsyncClient) -> None:
    """`ServeShapes` handed `shapes_for` the container's unit of work
    directly, and the first line of it reads `uow.workflow_runs`."""
    response = await client.get("/v1/shapes")
    assert response.status_code == 200, response.text
    assert response.json() == {"shapes": []}


async def test_spend_is_answered_by_a_real_session(client: httpx.AsyncClient) -> None:
    """`Container.read_spend` handed `spent_today` a fresh unit of work, and
    the whole of `spent_today` is `uow.spend.today(...)`."""
    response = await client.get("/v1/spend")
    assert response.status_code == 200, response.text
    assert response.json()["cost_usd"] == 0
