"""Keeping systems open without taking them away from anybody.

The keeper exists so the first batch of the morning is not what discovers the
weekend expired the session. It used to stand aside whenever somebody was
demonstrating, on the belief that the WMS permits one session per account and a
server login would sign the operator out. Measured on QA on 2026-09-23, two
logins for the same account in separate browser contexts both stayed valid, so
a demonstration no longer stops a sign-in. What still stops one is having no
browser to sign in with, and what still waits for a demonstration is reaping
browsers.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from sro.application.connection.keep_open import KEEPER, KeepSessionsOpen
from sro.application.connection.release_strays import Expired
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserUnavailable
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

    swept = await KeepSessionsOpen(uow, ensure).sweep()

    assert swept.open_now == ("blue_yonder",)
    assert ensure.asked == [("acme", KEEPER.value)]


async def test_a_demonstration_does_not_stop_a_sign_in(uow: FakeUnitOfWork) -> None:
    """A second session for the same account leaves the operator's working."""
    await uow.connections.add(_connected())
    await uow.recordings.add(f.recording())
    ensure = _Ensure(asked=[])

    swept = await KeepSessionsOpen(uow, ensure).sweep()

    assert swept.open_now == ("blue_yonder",)
    assert swept.left_alone == ()
    assert ensure.asked == [("acme", KEEPER.value)]


async def test_a_system_with_no_browser_free_is_left_alone_and_the_rest_still_swept(
    uow: FakeUnitOfWork,
) -> None:
    """The pool is finite. Having no browser to sign in with is not an outage,
    and one tenant waiting for a browser must not stop the next one's refresh."""
    await uow.connections.add(_connected(tenant="acme"))
    await uow.connections.add(_connected(tenant="rival", system="other_wms"))

    @dataclass
    class _Busy(_Ensure):
        async def execute(self, ctx: RequestContext, *, target_system: str) -> bool:
            if ctx.tenant_id.value == "acme":
                raise BrowserUnavailable("every browser is in use")
            return await super().execute(ctx, target_system=target_system)

    swept = await KeepSessionsOpen(uow, _Busy()).sweep()

    assert swept.left_alone == ("blue_yonder",)
    assert swept.open_now == ("other_wms",)
    assert swept.unreachable == ()


async def test_a_system_that_cannot_be_opened_is_reported_not_retried(
    uow: FakeUnitOfWork,
) -> None:
    await uow.connections.add(_connected())

    swept = await KeepSessionsOpen(uow, _Ensure(reachable=False)).sweep()

    assert swept.unreachable == ("blue_yonder",)


async def test_every_tenant_is_swept_under_its_own_name(uow: FakeUnitOfWork) -> None:
    """No request is being served, so the keeper acts for each tenant in turn --
    and a refresh is recorded as the keeper's, not as whoever asked last."""
    await uow.connections.add(_connected(tenant="acme"))
    await uow.connections.add(_connected(tenant="rival"))
    ensure = _Ensure(asked=[])

    swept = await KeepSessionsOpen(uow, ensure).sweep()

    assert len(swept.open_now) == 2
    assert {tenant for tenant, _ in (ensure.asked or [])} == {"acme", "rival"}
    assert {principal for _, principal in (ensure.asked or [])} == {KEEPER.value}


class _Strays:
    def __init__(self, released: tuple[str, ...] = (), expired: tuple[str, ...] = ()) -> None:
        self.released = released
        self.expired = expired
        self.asked = 0

    async def expire_leases(self) -> Expired:
        return Expired(contexts=self.expired, steel_sessions=self.expired)

    async def close_strays(self, *, expired: tuple[str, ...] = ()) -> tuple[str, ...]:
        self.asked += 1
        return self.released


async def test_forgotten_browsers_are_given_back(uow: FakeUnitOfWork) -> None:
    """This deployment has one browser. A session nothing claims holds it."""
    await uow.connections.add(_connected())
    strays = _Strays(released=("abandoned-session",))

    swept = await KeepSessionsOpen(uow, _Ensure(), strays).sweep()

    assert swept.released == ("abandoned-session",)


async def test_nothing_is_reaped_while_somebody_is_demonstrating(
    uow: FakeUnitOfWork,
) -> None:
    """Their browser is the one that would be taken."""
    await uow.connections.add(_connected())
    await uow.recordings.add(f.recording())
    strays = _Strays(released=("would-have-taken-theirs",))

    swept = await KeepSessionsOpen(uow, _Ensure(), strays).sweep()

    assert swept.released == ()
    assert strays.asked == 0


async def test_lease_expiry_is_never_held_up_by_somebody_elses_demonstration(
    uow: FakeUnitOfWork,
) -> None:
    """A demonstration protects the capture browser it is using, not the
    rest of the deployment. A dead lease's context must not pile up in the
    one Chrome just because somebody, anywhere, is recording."""
    await uow.connections.add(_connected())
    await uow.recordings.add(f.recording())
    strays = _Strays(expired=("dead-lease-session",))

    swept = await KeepSessionsOpen(uow, _Ensure(), strays).sweep()

    assert swept.released == ("dead-lease-session",)
    assert strays.asked == 0
