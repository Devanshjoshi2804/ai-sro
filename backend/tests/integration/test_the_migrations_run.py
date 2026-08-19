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

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from sro.config import get_settings


async def test_upgrading_from_nothing_builds_the_schema(postgres_url: str) -> None:
    engine = create_async_engine(postgres_url)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # `migrations/env.py` reads the address from the settings, exactly as it
    # does in a deployment, so this is the same path `make migrate` takes.
    was = os.environ.get("SRO_DATABASE_URL")
    os.environ["SRO_DATABASE_URL"] = postgres_url
    get_settings.cache_clear()
    try:
        # In a thread: `migrations/env.py` calls `asyncio.run`, which cannot
        # happen inside the loop this test is already running on.
        await asyncio.to_thread(command.upgrade, Config("alembic.ini"), "head")
    finally:
        if was is None:
            del os.environ["SRO_DATABASE_URL"]
        else:
            os.environ["SRO_DATABASE_URL"] = was
        get_settings.cache_clear()

    async with engine.connect() as connection:
        tables = set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))
    await engine.dispose()

    assert "browser_sessions" in tables, "the ownership record a browser is claimed in"
    assert {"skills", "runs", "recordings", "connections"} <= tables
