import asyncio
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from sro.domain.shared.identifiers import BrowserSessionId, PrincipalId, TenantId
from sro.infrastructure.db.repositories import SqlBrowserSessionRepository

T = TenantId("greyorange")
NOW = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)
LENA = Account.of("greyorange", "https://wms.example", "lena")

_LOCK_WAIT_DEADLINE_S = 5.0


async def _wait_until_a_racing_insert_blocks(observer: AsyncSession) -> None:
    """Poll `pg_locks` for a waiter, rather than guessing how long a
    competing INSERT takes to reach Postgres and block. A fixed sleep here
    would let the race tests pass whether or not the unique index they are
    named for still exists.

    The wait is a `transactionid` lock (the second inserter waiting to see
    whether the first transaction commits or aborts), not a `relation` one
    -- `ON CONFLICT`'s speculative-insertion check has no relation to name
    -- so this checks for any not-yet-granted lock from a different
    backend, which in this test's own throwaway database can only be the
    other acquirer."""
    deadline = time.monotonic() + _LOCK_WAIT_DEADLINE_S
    while time.monotonic() < deadline:
        waiting = await observer.scalar(
            text("SELECT count(*) FROM pg_locks WHERE NOT granted AND pid != pg_backend_pid()")
        )
        if waiting:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("the competing acquire never showed up blocked in pg_locks")


def _lease(
    lease_id: str, container: str = "http://steel:3000", *, account: Account = LENA
) -> Lease:
    return Lease(
        lease_id,
        account,
        container,
        f"s-{lease_id}",
        f"ctx-{lease_id}",
        "run_1",
        NOW,
        NOW + K_LEASE_TTL,
        LeaseState.SIGNING_IN,
    )


async def test_an_account_holds_one_live_lease(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)

    first = await repo.lease(T, _lease("lse_a"))
    second = await repo.lease(T, _lease("lse_b"))

    assert second.id == first.id == "lse_a"


async def test_casefold_variants_of_a_username_are_one_account(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    upper = Account.of("greyorange", "https://wms.example", "Lena@Example.com")
    lower = Account.of("greyorange", "https://wms.example", "lena@example.com")

    first = await repo.lease(T, _lease("lse_a", account=upper))
    second = await repo.lease(T, _lease("lse_b", account=lower))

    assert second.id == first.id == "lse_a"


async def test_two_sessions_racing_to_acquire_the_same_account_agree_on_one_winner(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with (
        session_factory() as session_a,
        session_factory() as session_b,
        session_factory() as observer,
    ):
        repo_a = SqlBrowserSessionRepository(session_a)
        repo_b = SqlBrowserSessionRepository(session_b)

        winner_a = await repo_a.lease(T, _lease("lse_a"))
        contender_b = asyncio.create_task(repo_b.lease(T, _lease("lse_b")))
        await _wait_until_a_racing_insert_blocks(observer)
        await session_a.commit()
        winner_b = await contender_b
        await session_b.commit()

        assert winner_b.id == winner_a.id == "lse_a"


async def test_a_rolled_back_acquire_lets_the_other_session_win(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with (
        session_factory() as session_a,
        session_factory() as session_b,
        session_factory() as observer,
    ):
        repo_a = SqlBrowserSessionRepository(session_a)
        repo_b = SqlBrowserSessionRepository(session_b)

        await repo_a.lease(T, _lease("lse_a"))
        contender_b = asyncio.create_task(repo_b.lease(T, _lease("lse_b")))
        await _wait_until_a_racing_insert_blocks(observer)
        await session_a.rollback()
        winner_b = await contender_b
        await session_b.commit()

        assert winner_b.id == "lse_b"


async def test_a_beaten_lease_outlives_its_ttl_and_a_silent_one_expires(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.READY)

    assert await repo.beat(T, "lse_a", now=NOW + timedelta(minutes=10))

    assert await repo.expired(now=NOW + timedelta(minutes=11)) == ()
    gone = await repo.expired(now=NOW + timedelta(minutes=13))
    assert [one.id for one in gone] == ["lse_a"]


async def test_an_expired_lease_frees_the_account_and_its_container(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))

    assert await repo.expire(T, "lse_a", now=NOW + K_LEASE_TTL)

    fresh = await repo.lease(T, _lease("lse_b", "http://steel-2:3000"))
    assert fresh.id == "lse_b"
    assert await repo.busy_containers(now=NOW) == ("http://steel-2:3000",)


async def test_a_shared_container_is_busy_with_every_tenants_leases(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.lease(
        TenantId("acme"), _lease("lse_b", account=Account.of("acme", "https://wms.example", "ann"))
    )

    assert sorted(await repo.busy_containers(now=NOW)) == ["http://steel:3000"] * 2


async def test_only_a_context_whose_lease_has_ended_is_retired(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    omar = Account.of("greyorange", "https://wms.example", "omar")
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.BROKEN)
    await repo.lease(T, _lease("lse_b", account=omar))
    await repo.lease(T, _lease("lse_c", "http://steel-2:3000"))
    await repo.settle(T, "lse_c", state=LeaseState.BROKEN)

    retired = await repo.retired_contexts(
        "http://steel:3000", ["ctx-lse_a", "ctx-lse_b", "ctx-lse_c", "ctx-unknown"]
    )

    assert retired == frozenset({"ctx-lse_a"})


async def test_the_sweeper_cannot_expire_a_lease_that_was_just_beaten(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.READY)

    assert await repo.beat(T, "lse_a", now=NOW + timedelta(minutes=1))

    assert not await repo.expire(T, "lse_a", now=NOW + K_LEASE_TTL)
    assert await repo.get_lease(T, "lse_a") is not None
    live = await repo.get_lease(T, "lse_a")
    assert live is not None
    assert live.state == LeaseState.READY


async def test_a_holder_learns_it_lost_its_lease(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.READY)

    assert await repo.expire(T, "lse_a", now=NOW + K_LEASE_TTL)

    assert not await repo.beat(T, "lse_a", now=NOW + K_LEASE_TTL + timedelta(seconds=1))


async def test_settle_cannot_revive_a_lease_expire_already_killed(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.READY)
    assert await repo.expire(T, "lse_a", now=NOW + K_LEASE_TTL)

    assert not await repo.settle(T, "lse_a", state=LeaseState.READY)

    still = await repo.get_lease(T, "lse_a")
    assert still is not None
    assert still.state == LeaseState.EXPIRED


async def test_settle_refuses_to_move_a_lease_to_expired(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))

    with pytest.raises(ValueError):
        await repo.settle(T, "lse_a", state=LeaseState.EXPIRED)


async def test_capture_sessions_never_see_a_lease(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.claim(T, BrowserSessionId("capture-1"), PrincipalId("op"), NOW)

    assert await repo.held_by(T) == (BrowserSessionId("capture-1"),)
    assert [held for held, _ in await repo.all_held()] == [BrowserSessionId("capture-1")]


async def test_a_lease_is_read_back_by_id(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))

    found = await repo.get_lease(T, "lse_a")

    assert found is not None
    assert found.account == LENA
    assert found.context_id == "ctx-lse_a"
    assert await repo.get_lease(T, "lse_never") is None


async def test_only_a_live_lease_answers_current_lease(session: AsyncSession) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.BROKEN)

    assert await repo.current_lease(T, LENA) is None


async def test_a_stray_sweep_never_closes_a_leased_steel_session(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.claim(T, BrowserSessionId("capture-1"), PrincipalId("op"), NOW)

    assert await repo.leased_sessions() == frozenset({"s-lse_a"})


async def test_an_account_is_pinned_to_the_container_of_its_latest_lease_live_or_not(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    assert await repo.pinned_container(T, LENA) is None

    await repo.lease(T, _lease("lse_a", "http://steel-2:3000"))
    assert await repo.expire(T, "lse_a", now=NOW + K_LEASE_TTL)
    assert await repo.pinned_container(T, LENA) == "http://steel-2:3000"

    later = replace(_lease("lse_b", "http://steel-3:3000"), heartbeat_at=NOW + K_LEASE_TTL)
    await repo.lease(T, later)
    assert await repo.pinned_container(T, LENA) == "http://steel-3:3000"
    omar = Account.of("greyorange", "https://wms.example", "omar")
    assert await repo.pinned_container(T, omar) is None
    assert await repo.pinned_container(TenantId("acme"), LENA) is None
