from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from sro.domain.execution.account import Account

K_LOCK_WAIT_S = 120


class PostgresAccountLocks:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def hold(self, account: Account) -> AsyncIterator[None]:
        async with self._engine.connect() as connection:
            await connection.execute(text(f"SET lock_timeout = '{K_LOCK_WAIT_S}s'"))
            await connection.execute(
                text("SELECT pg_advisory_lock(:key)"), {"key": account.lock_id}
            )
            try:
                yield
            finally:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": account.lock_id}
                )
