"""Every migration, applied to an empty database, in order.

`conftest.postgres_url` already runs `alembic upgrade head` once per session,
against a fresh database, so every other test in this directory runs against
a real migration and never against `Base.metadata.create_all`. This file
drops the schema and migrates again, on that same database, so it can assert
what the session setup does not: specific tables and indexes exist, and the
migrated shape agrees with what `models.py` declares.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from sro.infrastructure.db.models import Base


async def test_upgrading_from_nothing_builds_the_schema(postgres_url: str) -> None:
    engine = create_async_engine(postgres_url)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # In its own process, which is how a deployment runs it: `migrations/env.py`
    # reads the address from the settings and drives its own event loop, and
    # borrowing this test's would leave that loop's sockets for the garbage
    # collector to complain about long after the test had passed.
    upgrade = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "SRO_DATABASE_URL": postgres_url},
        capture_output=True,
        text=True,
    )

    async with engine.connect() as connection:
        tables = set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))
        # Not a table, and the one thing here that is a RULE rather than a
        # shape: `uq_workflow_runs_one_running_per_device` is what stops two
        # concurrent presses both claiming one browser, and the rest of the
        # suite builds its schema from `Base.metadata` -- where the index is
        # also declared, and would keep every test green while the migration
        # that a deployment actually runs built nothing.
        indexes = set(
            (
                await connection.execute(
                    text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
                )
            )
            .scalars()
            .all()
        )
    await engine.dispose()

    assert upgrade.returncode == 0, upgrade.stderr
    assert "browser_sessions" in tables, "the ownership record a browser is claimed in"
    assert {"skills", "runs", "recordings", "connections"} <= tables
    assert "uq_workflow_runs_one_running_per_device" in indexes


# Every test in this directory already runs against the migrated schema --
# `conftest.postgres_url` builds it with `alembic upgrade head` before the
# session's first test. Before that fixture ran migrations itself, this test
# was the only thing standing between `models.py` and a deploy that never
# noticed the two had drifted: deleting `uq_workflow_runs_one_running_per_device`
# from `models.py` left `make check` green, because the rest of the suite
# still built its tables with `Base.metadata.create_all` and the index came
# from migration 0043 either way.
#
# So the two are compared, once, here: what a deployment runs against what the
# code declares.

KNOWN_DRIFT = {
    # Same index, same column: migration 0018 named it
    # `ix_observation_batches_recording` and the model lets SQLAlchemy name it
    # `ix_observation_batches_recording_id`. Harmless in itself -- and left
    # rather than renamed because renaming it is a migration that takes a lock
    # on a live table to change a string nothing reads.
    ("remove_index", "ix_observation_batches_recording"),
    ("add_index", "ix_observation_batches_recording_id"),
}


async def test_the_migrated_schema_is_the_schema_the_code_declares(postgres_url: str) -> None:
    """Drift, in both directions, with one known exception.

    A column or index that exists in `models.py` and in no migration is a
    deployment that breaks on the first query. One that exists in a migration
    and not in the models is a column nothing writes, and -- worse -- a future
    `alembic revision --autogenerate` that proposes dropping it.
    """
    engine = create_async_engine(postgres_url)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    upgrade = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "SRO_DATABASE_URL": postgres_url},
        capture_output=True,
        text=True,
    )
    assert upgrade.returncode == 0, upgrade.stderr

    async with engine.connect() as connection:
        found = await connection.run_sync(_drift)
    await engine.dispose()

    assert found <= KNOWN_DRIFT, f"the migrations and the models disagree: {sorted(found)}"


def _drift(connection: Connection) -> set[tuple[str, str]]:
    """Every difference alembic can see, as (what, which).

    Reduced to a comparable pair rather than kept whole: `compare_metadata`
    answers with tuples whose middle is a live SQLAlchemy object, and an
    assertion against those reads as an address.
    """
    context = MigrationContext.configure(connection)
    differences: set[tuple[str, str]] = set()
    for one in compare_metadata(context, Base.metadata):
        # A modified column arrives as a LIST of diffs for that one column.
        for diff in one if isinstance(one, list) else [one]:
            kind = str(diff[0])
            named = next(
                (
                    getattr(part, "name", part)
                    for part in diff[1:]
                    if isinstance(part, str) or hasattr(part, "name")
                ),
                "",
            )
            differences.add((kind, str(named)))
    return differences
