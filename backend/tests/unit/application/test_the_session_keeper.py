"""Keeping systems open without taking them away from anybody.

The keeper exists so the first batch of the morning is not what discovers the
weekend expired the session. What it must never do is sign in while somebody is
demonstrating: this WMS permits one session, and taking it mid-task signs the
operator out of the screen they are teaching from.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from sro.application.connection.keep_open import KEEPER, KeepSessionsOpen
from sro.application.context import RequestContext
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.shared.identifiers import TenantId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork


@dataclass
class _Ensure:
    """Stands in for the whole sign-in path, which has its own tests."""

    reachable: bool = True
    asked: list[tuple[str, str]] | None = None

    async def execute(self, ctx: RequestContext, *, target_system: str) -> bool:
        (self.asked if self.asked is not None else []).append(
            (ctx.tenant_id.value, ctx.principal_id.value)
        )
        return self.reachable


def _connected(tenant: str = "acme", system: str = "blue_yonder") -> Connection:
    return Connection(
        id=ConnectionId(f"con-{tenant}"),
        tenant_id=TenantId(tenant),
        name=system,
        target_system=system,
        base_url="https://wms.test",
        created_at=f.T0,
        status=ConnectionStatus.CONNECTED,
    )


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


async def test_a_connected_system_is_kept_open(uow: FakeUnitOfWork) -> None:
    await uow.connections.add(_connected())
    ensure = _Ensure(asked=[])

    swept = await KeepSessionsOpen(uow, ensure).sweep()  # type: ignore[arg-type]

    assert swept.open_now == ("blue_yonder",)
    assert ensure.asked == [("acme", KEEPER.value)]


async def test_nothing_is_touched_while_somebody_is_demonstrating(
    uow: FakeUnitOfWork,
) -> None:
    """Their browser holds the session this would replace."""
    await uow.connections.add(_connected())
    await uow.recordings.add(f.recording())
    ensure = _Ensure(asked=[])

    swept = await KeepSessionsOpen(uow, ensure).sweep()  # type: ignore[arg-type]

    assert swept.left_alone == ("blue_yonder",)
    assert swept.open_now == ()
    assert ensure.asked == []


async def test_a_system_that_cannot_be_opened_is_reported_not_retried(
    uow: FakeUnitOfWork,
) -> None:
    await uow.connections.add(_connected())

    swept = await KeepSessionsOpen(uow, _Ensure(reachable=False)).sweep()  # type: ignore[arg-type]

    assert swept.unreachable == ("blue_yonder",)


async def test_every_tenant_is_swept_under_its_own_name(uow: FakeUnitOfWork) -> None:
    """No request is being served, so the keeper acts for each tenant in turn --
    and a refresh is recorded as the keeper's, not as whoever asked last."""
    await uow.connections.add(_connected(tenant="acme"))
    await uow.connections.add(_connected(tenant="rival"))
    ensure = _Ensure(asked=[])

    swept = await KeepSessionsOpen(uow, ensure).sweep()  # type: ignore[arg-type]

    assert len(swept.open_now) == 2
    assert {tenant for tenant, _ in (ensure.asked or [])} == {"acme", "rival"}
    assert {principal for _, principal in (ensure.asked or [])} == {KEEPER.value}


class _Strays:
    def __init__(self, released: tuple[str, ...] = ()) -> None:
        self.released = released
        self.asked = 0

    async def execute(self) -> tuple[str, ...]:
        self.asked += 1
        return self.released


async def test_forgotten_browsers_are_given_back(uow: FakeUnitOfWork) -> None:
    """This deployment has one browser. A session nothing claims holds it."""
    await uow.connections.add(_connected())
    strays = _Strays(released=("abandoned-session",))

    swept = await KeepSessionsOpen(uow, _Ensure(), strays).sweep()  # type: ignore[arg-type]

    assert swept.released == ("abandoned-session",)


async def test_nothing_is_reaped_while_somebody_is_demonstrating(
    uow: FakeUnitOfWork,
) -> None:
    """Their browser is the one that would be taken."""
    await uow.connections.add(_connected())
    await uow.recordings.add(f.recording())
    strays = _Strays(released=("would-have-taken-theirs",))

    swept = await KeepSessionsOpen(uow, _Ensure(), strays).sweep()  # type: ignore[arg-type]

    assert swept.released == ()
    assert strays.asked == 0
