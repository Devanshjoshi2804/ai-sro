from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from sro.application.ports.locks import AccountBusy
from sro.domain.execution.account import Account, lock_id_of

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

    def hold(
        self, account: Account, *, on_wait: Callable[[], Awaitable[None]] = _no_heartbeat
    ) -> AbstractAsyncContextManager[None]:
        return self.hold_named(account.key, on_wait=on_wait)

    @asynccontextmanager
    async def hold_named(
        self, name: str, *, on_wait: Callable[[], Awaitable[None]] = _no_heartbeat
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
                            text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id_of(name)}
                        )
                    except DBAPIError as error:
                        if not _is_lock_timeout(error):
                            raise
                        raise _Retry from error
                    yield
                return
            except _Retry:
                if time.monotonic() >= deadline:
                    raise AccountBusy(f"{name} is held by another session") from None
                await on_wait()

    @asynccontextmanager
    async def try_hold_named(self, name: str) -> AsyncIterator[bool]:
        async with self._engine.begin() as connection:
            got = await connection.execute(
                text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_id_of(name)}
            )
            yield bool(got.scalar_one())


def _is_lock_timeout(error: DBAPIError) -> bool:
    return getattr(error.orig, "sqlstate", None) == _LOCK_NOT_AVAILABLE
