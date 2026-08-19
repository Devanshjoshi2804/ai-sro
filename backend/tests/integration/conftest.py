"""Real Postgres via testcontainers.

These prove what fakes cannot: that the SQL is valid, that the tenant filter is
in the WHERE clause, and that a deep aggregate survives a round trip through
JSONB.

The database comes from ``SRO_INTEGRATION_DATABASE_URL`` when it is set, and
from testcontainers otherwise. Skipped rather than failed when neither is
available, so the suite stays useful on a machine without Docker.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from urllib.parse import urlsplit

import pytest
from docker.errors import DockerException
from sqlalchemy import NullPool, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sro.infrastructure.db.models import Base
from sro.infrastructure.db.session import create_session_factory


def _refuse_unless_disposable(url: str) -> None:
    """Every test here truncates every table when it finishes.

    Pointed at a database someone is using, that is silent data loss with a
    green suite to show for it. The database name has to say it is disposable.
    """
    name = urlsplit(url).path.lstrip("/")
    if not (name.startswith("test") or name.endswith(("test", "_test"))):
        pytest.fail(
            f"refusing to run destructive integration tests against database {name!r}: "
            "they truncate every table after each test. Point "
            "SRO_INTEGRATION_DATABASE_URL at a disposable database (say 'sro_test'), "
            "or unset it to use testcontainers.",
            pytrace=False,
        )


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    # CI runs Postgres as a service container and has no Docker socket to start
    # one of its own, so an address given in the environment wins.
    provided = os.environ.get("SRO_INTEGRATION_DATABASE_URL")
    if provided:
        _refuse_unless_disposable(provided)
        yield provided
        return

    # Imported inside the fixture: importing testcontainers builds a Docker
    # client, and on a machine without Docker that leaves a socket for the
    # garbage collector to complain about at exit.
    from testcontainers.community.postgres import PostgresContainer

    container = PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg")
    try:
        container.start()
    except DockerException as exc:
        pytest.skip(f"Docker unavailable: {exc}")

    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    """Per test, and unpooled.

    pytest-asyncio gives each test its own event loop, and an asyncpg connection
    belongs to the loop that opened it. A shared pool across tests therefore
    hands the second test a connection tied to a loop that is already closed.
    """
    engine = create_async_engine(postgres_url, poolclass=NullPool)
    async with engine.begin() as connection:
        # Before the schema, because `knowledge_entries.embedding` is a
        # `vector` and the image ships the extension without installing it.
        # Without this every integration test errored with `type "vector" does
        # not exist` -- twelve tests that had never run on a developer machine,
        # while the suite reported green from the unit tests alone.
        try:
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except ProgrammingError as exc:  # pragma: no cover - depends on the server
            pytest.skip(
                "this database has no pgvector and this role cannot install it: "
                f"{exc.orig or exc}. Point SRO_INTEGRATION_DATABASE_URL at a database "
                "with `CREATE EXTENSION vector` already run, or unset it to use "
                "testcontainers."
            )
        await connection.run_sync(Base.metadata.create_all)
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
