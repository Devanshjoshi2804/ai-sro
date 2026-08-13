"""Connecting a system: open its login page, then keep the session it produced.

The credentials are typed by the operator into the system's own login form,
inside a browser we opened for them. They never reach this API — no endpoint
here accepts a password, and none ever should.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.shared.identifiers import BrowserSessionId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    ConnectionModel,
    ConnectSystemRequest,
    OpenedConnectionResponse,
    SessionHeadersRequest,
    SessionHeadersResponse,
)

router = APIRouter(prefix="/connections", tags=["connections"])


def _model(connection: Connection) -> ConnectionModel:
    return ConnectionModel(
        id=connection.id.value,
        name=connection.name,
        target_system=connection.target_system,
        base_url=connection.base_url,
        status=connection.status.value,
        authenticated_at=connection.authenticated_at,
        last_error=connection.last_error,
    )


@router.get("")
async def list_connections(container: ContainerDep, ctx: ContextDep) -> list[ConnectionModel]:
    uow = container.unit_of_work()
    async with uow as unit:
        connections = await unit.connections.list_for_tenant(ctx.tenant_id)
    return [_model(connection) for connection in connections]


@router.post("", status_code=status.HTTP_201_CREATED)
async def connect_system(
    body: ConnectSystemRequest, container: ContainerDep, ctx: ContextDep
) -> OpenedConnectionResponse:
    """Open a browser at the system. The operator signs in there, not here."""
    opened = await container.connect_system().execute(
        ctx,
        name=body.name,
        target_system=body.target_system,
        base_url=body.base_url,
    )
    return OpenedConnectionResponse(
        connection_id=opened.connection_id.value,
        live_view_url=opened.live_view_url,
        browser_session_id=opened.browser_session_id.value,
    )


@router.post("/{connection_id}/session")
async def store_session(
    connection_id: str,
    browser_session_id: str,
    container: ContainerDep,
    ctx: ContextDep,
) -> ConnectionModel:
    """Keep the session the operator just created.

    Called when they say they are signed in. The cookies are read out of the
    browser and encrypted into the vault; nothing about them is returned here.
    """
    connection = await container.store_session().execute(
        ctx,
        connection_id=ConnectionId(connection_id),
        browser_session_id=BrowserSessionId(browser_session_id),
    )
    return _model(connection)


@router.post("/{connection_id}/session-headers")
async def store_session_headers(
    connection_id: str,
    body: SessionHeadersRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> SessionHeadersResponse:
    """Headers the executor must send as this session and cannot derive.

    The response names the keys and never the values: an endpoint that echoed a
    credential back would put it in every proxy log between here and the caller.
    """
    written = await container.store_session_headers().execute(
        ctx,
        connection_id=ConnectionId(connection_id),
        facility=body.facility,
        headers=body.headers,
    )
    return SessionHeadersResponse(stored=list(written))
