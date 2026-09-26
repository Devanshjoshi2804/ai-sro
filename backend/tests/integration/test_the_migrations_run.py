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
from datetime import UTC, datetime

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, insert, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from sro.infrastructure.db.models import Base, WorkflowRow, WorkflowRunRow, WorkflowStepRow
from sro.infrastructure.db.workflows import workflow_from_json


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
        # `compare_metadata` does not read `postgresql_where`, and `create_all`
        # is not what a deployment runs -- so nothing else here would notice a
        # 0073 that forgot to narrow the index to `executor = 'extension'`, or
        # that skipped `ck_workflow_runs_executor` entirely.
        one_running_def = (
            await connection.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE indexname = 'uq_workflow_runs_one_running_per_device'"
                )
            )
        ).scalar_one()
        executor_check = (
            await connection.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'ck_workflow_runs_executor'"
                )
            )
        ).scalar_one()
    await engine.dispose()

    assert upgrade.returncode == 0, upgrade.stderr
    assert "browser_sessions" in tables, "the ownership record a browser is claimed in"
    assert {"skills", "runs", "recordings", "connections"} <= tables
    assert "uq_workflow_runs_one_running_per_device" in indexes
    assert "outcome" in one_running_def and "'running'" in one_running_def, one_running_def
    assert "executor" in one_running_def and "'extension'" in one_running_def, one_running_def
    assert "'extension'" in executor_check and "'steel'" in executor_check, executor_check


async def test_downgrading_0073_refuses_when_two_steel_runs_share_a_device(
    postgres_url: str,
) -> None:
    """0073's `downgrade` recreates the wider index --
    `UNIQUE (tenant_id, device_id) WHERE outcome = 'running'` -- which two
    running Steel runs with `device_id = ""` cannot both satisfy. It has to
    refuse before Postgres's own duplicate-key error does, with a message
    that names the tenant and device rather than a bare constraint name."""
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

    now = datetime.now(tz=UTC)
    async with engine.begin() as connection:
        await connection.execute(
            insert(WorkflowRunRow.__table__),
            [
                {
                    "id": "run_steel_clash_1",
                    "tenant_id": "acme",
                    "workflow_id": "wfl_1",
                    "device_id": "",
                    "started_at": now,
                    "outcome": "running",
                    "executor": "steel",
                },
                {
                    "id": "run_steel_clash_2",
                    "tenant_id": "acme",
                    "workflow_id": "wfl_1",
                    "device_id": "",
                    "started_at": now,
                    "outcome": "running",
                    "executor": "steel",
                },
            ],
        )

    downgrade = await asyncio.to_thread(
        subprocess.run,
        # Not "-1": 0073 no longer heads the chain (S2's 0074 does), so one
        # relative step would only undo 0074 and never reach 0073's own
        # downgrade -- naming the target revision runs every step down to
        # it, including the one this test means to exercise.
        [sys.executable, "-m", "alembic", "downgrade", "0072"],
        env={**os.environ, "SRO_DATABASE_URL": postgres_url},
        capture_output=True,
        text=True,
    )
    await engine.dispose()

    assert downgrade.returncode != 0
    assert "cannot downgrade 0073" in downgrade.stderr, downgrade.stderr
    assert "'acme'" in downgrade.stderr, downgrade.stderr


async def _alembic(postgres_url: str, *args: str) -> None:
    ran = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", *args],
        env={**os.environ, "SRO_DATABASE_URL": postgres_url},
        capture_output=True,
        text=True,
    )
    assert ran.returncode == 0, ran.stderr


async def test_0078_makes_every_stored_job_undecided_and_back(postgres_url: str) -> None:
    """0069 stored `false` on every job it found, which reads as "decided: does
    not sign in" and so no sweep ever looked again. 0078 turns every stored
    `false` into NULL -- undecided -- for the sweep to decide from evidence,
    and keeps `true`, which only ever came from evidence. Its downgrade maps
    NULL back to the `false` the older code expects."""
    engine = create_async_engine(postgres_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await _alembic(postgres_url, "upgrade", "0077")
        async with engine.begin() as connection:
            await connection.execute(
                insert(WorkflowRow.__table__),
                [
                    {
                        "id": "wfl_old",
                        "tenant_id": "acme",
                        "created_at": datetime.now(tz=UTC),
                        "signs_in": False,
                    },
                    {
                        "id": "wfl_marked",
                        "tenant_id": "acme",
                        "created_at": datetime.now(tz=UTC),
                        "signs_in": True,
                    },
                ],
            )
        read = text("SELECT id, signs_in FROM workflows ORDER BY id")

        await _alembic(postgres_url, "upgrade", "0078")
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO workflows (id, tenant_id, pass_id, title, narrative, systems,"
                    " parameters, shape_key, created_at) VALUES ('wfl_new', 'acme', '', '', '',"
                    " '[]', '[]', '[]', now())"
                )
            )
            upgraded = (await connection.execute(read)).all()
        await _alembic(postgres_url, "downgrade", "0077")
        async with engine.begin() as connection:
            downgraded = (await connection.execute(read)).all()
        await _alembic(postgres_url, "upgrade", "head")
    finally:
        await engine.dispose()

    assert [tuple(row) for row in upgraded] == [
        ("wfl_marked", True),
        ("wfl_new", None),
        ("wfl_old", None),
    ]
    assert [tuple(row) for row in downgraded] == [
        ("wfl_marked", True),
        ("wfl_new", False),
        ("wfl_old", False),
    ]


async def test_0081_pins_every_steel_run_still_going_and_back(postgres_url: str) -> None:
    """A Steel run going when 0081 lands has been reading its job as it
    stands, so that is the version it is pinned to; an ended run and an
    extension run are left unpinned. The downgrade drops the pin."""
    engine = create_async_engine(postgres_url)
    now = datetime.now(tz=UTC)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await _alembic(postgres_url, "upgrade", "0080")
        async with engine.begin() as connection:
            await connection.execute(
                insert(WorkflowRow.__table__),
                [
                    {
                        "id": "wfl_1",
                        "tenant_id": "acme",
                        "created_at": now,
                        "parameters": [{"name": "who"}],
                    }
                ],
            )
            await connection.execute(
                insert(WorkflowStepRow.__table__),
                [
                    {
                        "workflow_id": "wfl_1",
                        "ord": 1,
                        "says": "save",
                        "cites": ["g2"],
                        "parameters": [],
                        "system": None,
                    },
                    {
                        "workflow_id": "wfl_1",
                        "ord": 0,
                        "says": "type",
                        "cites": ["g1"],
                        "parameters": ["who"],
                        "system": "https://wms.example",
                    },
                ],
            )
            await connection.execute(
                insert(WorkflowRunRow.__table__),
                [
                    {
                        "id": run_id,
                        "tenant_id": "acme",
                        "workflow_id": "wfl_1",
                        "device_id": "",
                        "started_at": now,
                        "outcome": outcome,
                        "executor": executor,
                    }
                    for run_id, outcome, executor in (
                        ("run_going", "running", "steel"),
                        ("run_ended", "held", "steel"),
                        ("run_extension", "running", "extension"),
                    )
                ],
            )
        read = text("SELECT id, pinned FROM workflow_runs ORDER BY id")

        await _alembic(postgres_url, "upgrade", "0081")
        async with engine.begin() as connection:
            upgraded = dict(tuple(row) for row in (await connection.execute(read)).all())
        await _alembic(postgres_url, "downgrade", "0080")
        async with engine.connect() as connection:
            columns = await connection.run_sync(
                lambda sync: {one["name"] for one in inspect(sync).get_columns("workflow_runs")}
            )
        await _alembic(postgres_url, "upgrade", "head")
    finally:
        await engine.dispose()

    assert (upgraded["run_ended"], upgraded["run_extension"]) == (None, None)
    going = workflow_from_json(upgraded["run_going"])
    assert (going.id, going.parameters, going.repeat) == ("wfl_1", [{"name": "who"}], None)
    assert [
        (one.order, one.says, one.system, one.cites, one.parameters) for one in going.steps
    ] == [
        (0, "type", "https://wms.example", ["g1"], ["who"]),
        (1, "save", None, ["g2"], []),
    ]
    assert "pinned" not in columns


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
