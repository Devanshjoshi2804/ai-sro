"""Real Postgres via testcontainers.

These prove what fakes cannot: that the SQL is valid, that the tenant filter is
in the WHERE clause, and that a deep aggregate survives a round trip through
JSONB.

The ``postgres_url`` fixture that borrows the throwaway, migrated database
lives in ``tests.postgres`` -- the contract suite needs the same thing, to
give the app's own startup sweep somewhere real to query, and importing one
definition of "a disposable database" beats two going out of sync.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sro.infrastructure.db.models import Base
from sro.infrastructure.db.session import create_session_factory
from tests.postgres import postgres_url  # noqa: F401  (fixture, used by name)


@pytest.fixture
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:  # noqa: F811
    """Per test, and unpooled.

    pytest-asyncio gives each test its own event loop, and an asyncpg connection
    belongs to the loop that opened it. A shared pool across tests therefore
    hands the second test a connection tied to a loop that is already closed.

    The schema itself is `postgres_url`'s job, once per session -- this only
    truncates between tests.
    """
    engine = create_async_engine(postgres_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                await connection.execute(table.delete())
        await engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)
