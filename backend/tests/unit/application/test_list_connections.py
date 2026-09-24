from __future__ import annotations

from datetime import UTC, datetime

from sro.application.connection.list_connections import ListConnections
from sro.application.context import RequestContext
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.shared.identifiers import PrincipalId, TenantId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

OTHER = TenantId("other-corp")
CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
OTHER_CTX = RequestContext(tenant_id=OTHER, principal_id=PrincipalId("clerk@other.test"))


def _connection(connection_id: str, tenant_id: TenantId = f.TENANT) -> Connection:
    return Connection(
        id=ConnectionId(connection_id),
        tenant_id=tenant_id,
        name="WMS",
        target_system="blue_yonder",
        base_url="https://wms.example.com",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


async def test_only_the_caller_s_tenant_comes_back() -> None:
    uow = FakeUnitOfWork()
    async with uow:
        await uow.connections.add(_connection("con_ours"))
        await uow.connections.add(_connection("con_theirs", tenant_id=OTHER))
        await uow.commit()

    ours = await ListConnections(uow).execute(CTX)
    theirs = await ListConnections(uow).execute(OTHER_CTX)

    assert {c.id.value for c in ours} == {"con_ours"}
    assert {c.id.value for c in theirs} == {"con_theirs"}
