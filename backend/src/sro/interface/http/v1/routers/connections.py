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
    CredentialsRequest,
    OpenedConnectionResponse,
    SessionCheckModel,
    SessionHeadersRequest,
    SessionHeadersResponse,
    SignedInResponse,
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


@router.get("/health")
async def check_sessions(container: ContainerDep, ctx: ContextDep) -> list[SessionCheckModel]:
    """Whether each stored session still works, asked of the systems themselves.

    Live rather than remembered: a session that expired an hour ago still looks
    connected in the database, and the operator finds out inside a
    demonstration. This is what lets the app say it first.
    """
    checks = await container.check_session().execute(ctx)
    return [
        SessionCheckModel(
            connection_id=check.connection_id,
            target_system=check.target_system,
            health=check.health.value,
            detail=check.detail,
        )
        for check in checks
    ]


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


@router.put("/{connection_id}/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def store_credentials(
    connection_id: str,
    body: CredentialsRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> None:
    """What the connection signs itself back in with, entered once.

    This is the difference between a saved session and a connector: a session
    dies on the system's schedule, and something has to be able to make a new
    one at 3am without waking anybody.

    Encrypted into the vault on arrival. No endpoint returns it, nothing logs
    it, no recording contains it, and it is typed into no page but the login
    page of the host this connection names.
    """
    await container.store_credentials().execute(
        ctx,
        connection_id=ConnectionId(connection_id),
        username=body.username,
        password=body.password,
    )


@router.post("/{connection_id}/sign-in")
async def sign_in(
    connection_id: str, target_system: str, container: ContainerDep, ctx: ContextDep
) -> SignedInResponse:
    """Sign in now with what is stored, and keep the session it produces."""
    signed_in = await container.sign_in().execute(ctx, target_system=target_system)
    return SignedInResponse(
        target_system=signed_in.target_system,
        landed_at=signed_in.landed_at,
        steps=list(signed_in.steps),
    )


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
