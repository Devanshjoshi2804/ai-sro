import asyncio
from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from sro.application.ports.locks import AccountBusy
from sro.domain.execution.account import Account
from sro.infrastructure.db import locks as locks_module
from sro.infrastructure.db.locks import PostgresAccountLocks

LENA = Account.of("greyorange", "https://wms.example", "lena")
OMAR = Account.of("greyorange", "https://wms.example", "omar")


async def test_a_second_holder_of_one_account_waits_and_another_account_does_not(
    engine: AsyncEngine,
) -> None:
    locks = PostgresAccountLocks(engine)
    async with locks.hold(LENA):
        waiter = asyncio.create_task(_enter(locks, LENA))
        await _until(lambda: _waiting_advisory_locks(engine), at_least=1)
        assert not waiter.done()
        await asyncio.wait_for(_enter(locks, OMAR), timeout=5.0)
    await asyncio.wait_for(waiter, timeout=5.0)
    await asyncio.wait_for(_enter(locks, LENA), timeout=5.0)


async def test_two_case_variants_of_one_username_share_the_lock(engine: AsyncEngine) -> None:
    """§5.4 keys the lock on `Account.key`, which casefolds the username --
    so `Lena@wms.example` and `lena@wms.example` are one account's session,
    not two, and must contend for the same lock."""
    upper = Account.of("greyorange", "https://wms.example", "Lena@wms.example")
    lower = Account.of("greyorange", "https://wms.example", "lena@wms.example")
    assert upper.key == lower.key

    locks = PostgresAccountLocks(engine)
    async with locks.hold(upper):
        waiter = asyncio.create_task(_enter(locks, lower))
        await _until(lambda: _waiting_advisory_locks(engine), at_least=1)
        assert not waiter.done()
    await asyncio.wait_for(waiter, timeout=5.0)


async def test_two_tenants_of_the_same_account_do_not_share_the_lock(
    engine: AsyncEngine,
) -> None:
    """Scoped by tenant: `Account.key` leads with `tenant`, so one tenant's
    session change never waits on another's."""
    here = Account.of("greyorange", "https://wms.example", "lena")
    elsewhere = Account.of("other-corp", "https://wms.example", "lena")
    assert here.key != elsewhere.key

    locks = PostgresAccountLocks(engine)
    async with locks.hold(here):
        await asyncio.wait_for(_enter(locks, elsewhere), timeout=1.0)


async def test_the_lock_is_released_after_an_exception_in_the_body(engine: AsyncEngine) -> None:
    locks = PostgresAccountLocks(engine)

    with pytest.raises(RuntimeError):
        async with locks.hold(LENA):
            raise RuntimeError("the sign-in blew up")

    assert await _granted_advisory_locks(engine) == 0
    await asyncio.wait_for(_enter(locks, LENA), timeout=5.0)


async def test_the_lock_is_released_after_the_holder_is_cancelled(engine: AsyncEngine) -> None:
    locks = PostgresAccountLocks(engine)
    entered = asyncio.Event()

    async def _hold_until_cancelled() -> None:
        async with locks.hold(LENA):
            entered.set()
            await asyncio.sleep(30)

    holder = asyncio.create_task(_hold_until_cancelled())
    await asyncio.wait_for(entered.wait(), timeout=5.0)

    holder.cancel()
    with pytest.raises(asyncio.CancelledError):
        await holder

    assert await _granted_advisory_locks(engine) == 0
    await asyncio.wait_for(_enter(locks, LENA), timeout=5.0)


async def test_a_wait_past_the_deadline_raises_account_busy(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(locks_module, "K_LOCK_ATTEMPT_S", 1)
    monkeypatch.setattr(locks_module, "K_LOCK_WAIT_S", 2)
    locks = PostgresAccountLocks(engine)

    async with locks.hold(LENA):
        with pytest.raises(AccountBusy):
            await asyncio.wait_for(_enter(locks, LENA), timeout=10.0)


async def test_on_wait_is_called_between_attempts(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(locks_module, "K_LOCK_ATTEMPT_S", 1)
    locks = PostgresAccountLocks(engine)
    calls = 0

    async def _on_wait() -> None:
        nonlocal calls
        calls += 1

    async with locks.hold(LENA):
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_enter(locks, LENA, on_wait=_on_wait), timeout=5.0)

    assert calls >= 1


async def _no_op() -> None:
    return None


async def _enter(
    locks: PostgresAccountLocks,
    account: Account,
    *,
    on_wait: Callable[[], Awaitable[None]] = _no_op,
) -> None:
    async with locks.hold(account, on_wait=on_wait):
        return None


async def _granted_advisory_locks(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        return (
            await connection.execute(
                text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted")
            )
        ).scalar_one()


async def _waiting_advisory_locks(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        return (
            await connection.execute(
                text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted")
            )
        ).scalar_one()


async def _until(
    read: Callable[[], Awaitable[int]], *, at_least: int, within_s: float = 5.0
) -> None:
    deadline = asyncio.get_event_loop().time() + within_s
    while True:
        if await read() >= at_least:
            return
        if asyncio.get_event_loop().time() >= deadline:
            raise AssertionError(f"never reached {at_least} within {within_s}s")
        await asyncio.sleep(0.05)
