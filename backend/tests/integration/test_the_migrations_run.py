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
import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, insert, inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from sro.infrastructure.db.models import Base, WorkflowRunRow


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
        # The absolute target, not `-1`: 0073 was the head when this was
        # written, and later migrations stacked on top (0074, then 0075 --
        # sign-in pages are watched) would otherwise make `-1` undo one of
        # those instead and never reach 0073's own refusal.
        [sys.executable, "-m", "alembic", "downgrade", "0072"],
        env={**os.environ, "SRO_DATABASE_URL": postgres_url},
        capture_output=True,
        text=True,
    )
    await engine.dispose()

    assert downgrade.returncode != 0
    assert "cannot downgrade 0073" in downgrade.stderr, downgrade.stderr
    assert "'acme'" in downgrade.stderr, downgrade.stderr


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


_SIGN_IN_MIGRATION = next(
    Path(__file__).resolve().parents[2].glob("migrations/versions/*_sign_in_pages_are_watched.py")
)

# Every default exclusion list a tenant's stored policy can hold: the 8-host
# list 0022 left (the first five plus the three mailboxes it appended), the
# 9-host one 47672b14 wrote for new tenants, and the 3-host one b94e2830 did.
# Order is whatever wrote it, so each is stored here in an order nobody chose.
_OLD_DEFAULTS = {
    "eight": [
        "mail.google.com",
        "outlook.live.com",
        "mail.yahoo.com",
        "accounts.google.com",
        "login.microsoftonline.com",
        "outlook.office.com",
        "outlook.office365.com",
        "outlook.cloud.microsoft",
    ],
    "nine": [
        "mail.google.com",
        "outlook.live.com",
        "outlook.office.com",
        "outlook.office365.com",
        "outlook.cloud.microsoft",
        "mail.yahoo.com",
        "accounts.google.com",
        "login.microsoftonline.com",
        "b2clogin.com",
    ],
    "three": ["b2clogin.com", "accounts.google.com", "login.microsoftonline.com"],
}


def _revision_before_sign_in() -> str:
    spec = importlib.util.spec_from_file_location("sign_in_migration", _SIGN_IN_MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return str(module.down_revision)


async def _alembic(postgres_url: str, *args: str) -> None:
    done = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-m", "alembic", *args],
        env={**os.environ, "SRO_DATABASE_URL": postgres_url},
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr


async def test_every_old_default_exclusion_list_is_healed_and_the_policy_moves_on(
    postgres_url: str,
) -> None:
    """Spec §5.6: identity providers are watched, structure-only.

    A stored list equal (as a set) to any default the code ever wrote is that
    default, not a choice, so it becomes empty -- and the version moves, both
    the row's and the policy's own, or a signed-in extension would go on
    holding the old list until somebody signed it out (the heartbeat sends a
    policy only when the version differs; 0022 is the precedent). A list an
    owner wrote stays exactly as it was.
    """
    await _alembic(postgres_url, "downgrade", _revision_before_sign_in())
    engine = create_async_engine(postgres_url)
    chosen = ["accounts.google.com", "login.microsoftonline.com", "hr.acme.example"]
    async with engine.begin() as connection:
        await connection.execute(text("DELETE FROM observation_policies"))
        for tenant, hosts in (*_OLD_DEFAULTS.items(), ("chosen", chosen)):
            await connection.execute(
                text(
                    "INSERT INTO observation_policies (tenant_id, version, policy) "
                    "VALUES (:tenant, 4, CAST(:policy AS jsonb))"
                ),
                {"tenant": tenant, "policy": json.dumps({"version": 4, "exclude_hosts": hosts})},
            )

    await _alembic(postgres_url, "upgrade", "head")

    async with engine.connect() as connection:
        rows = {
            tenant: (version, policy)
            for tenant, version, policy in (
                await connection.execute(
                    text("SELECT tenant_id, version, policy FROM observation_policies")
                )
            ).all()
        }
    await engine.dispose()

    for tenant in _OLD_DEFAULTS:
        version, policy = rows[tenant]
        assert policy["exclude_hosts"] == [], tenant
        assert version == 5, tenant
        assert policy["version"] == 5, tenant
    assert rows["chosen"] == (4, {"version": 4, "exclude_hosts": chosen})
