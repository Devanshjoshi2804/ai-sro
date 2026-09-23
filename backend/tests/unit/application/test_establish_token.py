from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.application.connection.establish_token import EstablishToken
from sro.application.context import RequestContext
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.shared.errors import NotFound
from tests import factories as f
from tests.unit.fakes import FakeTokenSource, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _connected(uow: FakeUnitOfWork) -> Connection:
    connection = Connection(
        id=ConnectionId("con_1"),
        tenant_id=f.TENANT,
        name="WMS",
        target_system="blue_yonder",
        base_url="https://wms.example.com",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    async with uow:
        await uow.connections.add(connection)
        await uow.commit()
    return connection


async def test_the_password_buys_a_token_named_for_the_connection_s_system() -> None:
    uow, tokens = FakeUnitOfWork(), FakeTokenSource()
    await _connected(uow)

    established = await EstablishToken(uow, tokens).execute(
        CTX,
        connection_id=ConnectionId("con_1"),
        username="operator",
        password="s3cret",  # noqa: S106 -- a fake token source's value
    )

    assert established.target_system == "blue_yonder"
    assert tokens.established == [("acme", "blue_yonder", "operator", "s3cret")]


async def test_a_deployment_with_no_identity_provider_refuses_before_touching_the_connection() -> (
    None
):
    uow = FakeUnitOfWork()
    await _connected(uow)

    with pytest.raises(NotFound):
        await EstablishToken(uow, None).execute(
            CTX,
            connection_id=ConnectionId("con_1"),
            username="operator",
            password="s3cret",  # noqa: S106 -- a fake token source's value
        )


async def test_an_unknown_connection_is_not_found() -> None:
    uow, tokens = FakeUnitOfWork(), FakeTokenSource()

    with pytest.raises(NotFound):
        await EstablishToken(uow, tokens).execute(
            CTX,
            connection_id=ConnectionId("con_missing"),
            username="operator",
            password="s3cret",  # noqa: S106 -- a fake token source's value
        )
