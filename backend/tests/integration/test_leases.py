from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from sro.domain.shared.identifiers import BrowserSessionId, PrincipalId, TenantId
from sro.infrastructure.db.repositories import SqlBrowserSessionRepository

T = TenantId("greyorange")
NOW = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)
LENA = Account.of("greyorange", "https://wms.example", "lena")


def _lease(lease_id: str, container: str = "http://steel:3000") -> Lease:
    return Lease(
        lease_id,
        LENA,
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


async def test_a_beaten_lease_outlives_its_ttl_and_a_silent_one_expires(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.READY)

    await repo.beat(T, "lse_a", now=NOW + timedelta(minutes=10))

    assert await repo.expired(now=NOW + timedelta(minutes=11)) == ()
    gone = await repo.expired(now=NOW + timedelta(minutes=13))
    assert [one.id for one in gone] == ["lse_a"]


async def test_a_settled_lease_frees_the_account_and_its_container(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.EXPIRED)

    fresh = await repo.lease(T, _lease("lse_b", "http://steel-2:3000"))

    assert fresh.id == "lse_b"
    assert await repo.busy_containers(now=NOW) == ("http://steel-2:3000",)


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
    await repo.settle(T, "lse_a", state=LeaseState.EXPIRED)

    assert await repo.current_lease(T, LENA) is None


async def test_a_stray_sweep_never_closes_a_leased_steel_session(
    session: AsyncSession,
) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.claim(T, BrowserSessionId("capture-1"), PrincipalId("op"), NOW)

    assert await repo.leased_sessions() == frozenset({"s-lse_a"})
