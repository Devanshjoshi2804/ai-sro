"""Real Postgres via testcontainers.

These prove what fakes cannot: that the SQL is valid, that the tenant filter is
in the WHERE clause, and that a deep aggregate survives a round trip through
JSONB.

The database comes from ``SRO_INTEGRATION_DATABASE_URL`` when it is set, and
from testcontainers otherwise. Skipped rather than failed when neither is
available, so the suite stays useful on a machine without Docker.

Either way the schema comes from ``alembic upgrade head`` -- the same command
``make migrate`` runs -- never from ``Base.metadata.create_all``. That
function only adds tables that are missing; it never alters one that already
exists, so a shared database that several branches touch goes stale the
moment a migration adds a column, and the suite stays green against a shape
no deployment has.

When ``SRO_INTEGRATION_DATABASE_URL`` names a shared server, that address is
never itself migrated or dropped -- only used, once per session, to create a
throwaway ``sro_test_<suffix>`` database and drop it again at the end.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from urllib.parse import SplitResult, urlsplit, urlunsplit

import pytest
from docker.errors import DockerException
from sqlalchemy import NullPool, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sro.infrastructure.db.models import Base
from sro.infrastructure.db.session import create_session_factory

_DB_PREFIX = "sro_test_"
_STALE_AFTER_SECONDS = 24 * 60 * 60


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


def _with_database(url: str, name: str) -> str:
    parts: SplitResult = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


def _made_at(database_name: str) -> float | None:
    """The epoch second folded into ``sro_test_<epoch>_<random>`` -- a
    ``datname`` carries no created-at column of its own to read age back
    from, so the name is the only place a sweep can find it."""
    stamp = database_name.removeprefix(_DB_PREFIX).split("_", 1)[0]
    try:
        return float(stamp)
    except ValueError:
        return None


@asynccontextmanager
async def _maintenance_connection(server_url: str) -> AsyncIterator[AsyncConnection]:
    """CREATE DATABASE and DROP DATABASE both refuse to run inside a
    transaction, and both refuse to run against the database they name -- so
    every statement here goes through the server's own always-there
    database, autocommitted."""
    engine = create_async_engine(
        _with_database(server_url, "postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        async with engine.connect() as connection:
            yield connection
    finally:
        await engine.dispose()


async def _sweep_stale_databases(server_url: str) -> None:
    """Best-effort: a session that never reached its own teardown (a crash, a
    killed CI job) leaves ``sro_test_<suffix>`` behind on the shared server.
    Never touches ``sro_test`` itself -- the prefix match requires the
    trailing underscore this sweep always writes and that name never has."""
    async with _maintenance_connection(server_url) as connection:
        names = (
            (
                await connection.execute(
                    text("SELECT datname FROM pg_database WHERE datname LIKE :pattern"),
                    {"pattern": f"{_DB_PREFIX}%"},
                )
            )
            .scalars()
            .all()
        )
        now = time.time()
        for name in names:
            made = _made_at(name)
            if made is not None and now - made > _STALE_AFTER_SECONDS:
                await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))


async def _create_database(server_url: str, name: str) -> None:
    async with _maintenance_connection(server_url) as connection:
        await connection.execute(text(f'CREATE DATABASE "{name}"'))


async def _drop_database(server_url: str, name: str) -> None:
    async with _maintenance_connection(server_url) as connection:
        await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))


async def _migrate(database_url: str) -> None:
    """The extension first -- a migration can declare a ``vector`` column --
    then ``alembic upgrade head`` in its own process, exactly as
    ``migrations/env.py`` and ``make migrate`` already run it: it reads the
    address from ``SRO_DATABASE_URL`` through ``Settings`` and drives its own
    event loop, which this fixture's loop would leave sockets open for the
    garbage collector to complain about."""
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            try:
                await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            except ProgrammingError as exc:  # pragma: no cover - depends on the server
                pytest.skip(
                    "this database has no pgvector and this role cannot install it: "
                    f"{exc.orig or exc}. Point SRO_INTEGRATION_DATABASE_URL at a server "
                    "with `CREATE EXTENSION vector` already run, or unset it to use "
                    "testcontainers."
                )
    finally:
        await engine.dispose()

    upgrade = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "SRO_DATABASE_URL": database_url},
        capture_output=True,
        text=True,
    )
    if upgrade.returncode != 0:
        pytest.fail(f"alembic upgrade head failed:\n{upgrade.stderr}", pytrace=False)


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    # CI runs Postgres as a service container and has no Docker socket to start
    # one of its own, so an address given in the environment wins.
    provided = os.environ.get("SRO_INTEGRATION_DATABASE_URL")
    if provided:
        _refuse_unless_disposable(provided)
        name = f"{_DB_PREFIX}{int(time.time())}_{uuid.uuid4().hex[:8]}"
        asyncio.run(_sweep_stale_databases(provided))
        asyncio.run(_create_database(provided, name))
        session_url = _with_database(provided, name)
        try:
            asyncio.run(_migrate(session_url))
            yield session_url
        finally:
            asyncio.run(_drop_database(provided, name))
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
        url = container.get_connection_url()
        asyncio.run(_migrate(url))
        yield url
    finally:
        container.stop()


@pytest.fixture
async def engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
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


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as opened:
        yield opened
        await opened.commit()
