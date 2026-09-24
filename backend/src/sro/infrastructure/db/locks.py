from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from sro.application.ports.locks import AccountBusy
from sro.domain.execution.account import Account

K_LOCK_ATTEMPT_S = 10
K_LOCK_WAIT_S = 120
K_LOCK_CONNECT_TIMEOUT_S = 10

_LOCK_NOT_AVAILABLE = "55P03"


async def _no_heartbeat() -> None:
    return None


class _Retry(Exception):
    pass


class PostgresAccountLocks:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def hold(
        self, account: Account, *, on_wait: Callable[[], Awaitable[None]] = _no_heartbeat
    ) -> AsyncIterator[None]:
        deadline = time.monotonic() + K_LOCK_WAIT_S
        while True:
            try:
                async with self._engine.begin() as connection:
                    await connection.execute(
                        text(f"SET LOCAL lock_timeout = '{K_LOCK_ATTEMPT_S}s'")
                    )
                    try:
                        await connection.execute(
                            text("SELECT pg_advisory_xact_lock(:key)"), {"key": account.lock_id}
                        )
                    except DBAPIError as error:
                        if not _is_lock_timeout(error):
                            raise
                        raise _Retry from error
                    yield
                return
            except _Retry:
                if time.monotonic() >= deadline:
                    raise AccountBusy(f"{account.key} is held by another session") from None
                await on_wait()


def _is_lock_timeout(error: DBAPIError) -> bool:
    return getattr(error.orig, "sqlstate", None) == _LOCK_NOT_AVAILABLE
