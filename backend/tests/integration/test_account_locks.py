import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from sro.domain.execution.account import Account
from sro.infrastructure.db.locks import PostgresAccountLocks

LENA = Account.of("greyorange", "https://wms.example", "lena")
OMAR = Account.of("greyorange", "https://wms.example", "omar")


async def test_a_second_holder_of_one_account_waits_and_another_account_does_not(
    engine: AsyncEngine,
) -> None:
    locks = PostgresAccountLocks(engine)
    async with locks.hold(LENA):
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_enter(locks, LENA), timeout=1.0)
        await asyncio.wait_for(_enter(locks, OMAR), timeout=5.0)
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
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_enter(locks, lower), timeout=1.0)
    await asyncio.wait_for(_enter(locks, lower), timeout=5.0)


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


async def _enter(locks: PostgresAccountLocks, account: Account) -> None:
    async with locks.hold(account):
        return None
