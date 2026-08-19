"""Every migration, applied to an empty database, in order.

The integration suite builds its schema with `Base.metadata.create_all`, which
proves the models agree with themselves and says nothing about the migrations
that actually run in a deployment. A migration with a typo in it therefore
passed the whole suite and failed at deploy, on the one path where failing is
expensive.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


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
    await engine.dispose()

    assert upgrade.returncode == 0, upgrade.stderr
    assert "browser_sessions" in tables, "the ownership record a browser is claimed in"
    assert {"skills", "runs", "recordings", "connections"} <= tables
