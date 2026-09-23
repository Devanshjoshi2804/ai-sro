"""The channel a browser holds open so work can be handed to it.

Commands go down, answers come back, and the socket is the only way in: there
is no endpoint that drives a device, because an endpoint that did would let one
tenant's credential reach another tenant's browser if the id ever leaked. The
registry is keyed by tenant as well as device for the same reason.
"""

from __future__ import annotations

import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from sro.application.context import RequestContext
from sro.application.ports.auth import CredentialRejected, Unconfigured
from sro.container import Container
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import DeviceId
from sro.whose import attribute

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

_BEARER = "bearer"
"""Same reason as the live view: a browser cannot set a header on a websocket,
and a token in the query string is a token in every access log.

Three parts, not two: `bearer`, the tenant credential, and the device's own
secret. The header the HTTP routes carry it in is not available here for the
same reason the credential is not, so it rides beside it. The subprotocol
answered with is still `bearer` -- a browser matches on the first part."""


@router.websocket("/{device_id}/commands")
async def commands(websocket: WebSocket, device_id: str) -> None:
    container: Container = websocket.app.state.container
    protocols = [
        part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")
    ]
    named = protocols[0] == _BEARER
    token = protocols[1] if named and len(protocols) > 1 else ""
    secret = protocols[2] if named and len(protocols) > 2 else ""

    try:
        caller = container.credentials.verify(f"Bearer {token}")
        ctx = RequestContext(tenant_id=caller.tenant_id, principal_id=caller.principal_id)
        device = await container.read_device().execute(
            ctx, device_id=DeviceId(device_id), secret=secret
        )
    except (CredentialRejected, Unconfigured, NotFound):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept(subprotocol=_BEARER)
    sockets = container.agent_sockets
    channel = _Channel(websocket)
    attribute(tenant=ctx.tenant_id.value, principal=ctx.principal_id.value, device=device.id.value)
    sockets.attach(ctx.tenant_id, device.id, channel)
    logger.info("device %s connected", device.id)

    try:
        while True:
            sockets.deliver(await websocket.receive_text(), ctx.tenant_id, device.id)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("the channel to device %s failed", device.id)
    finally:
        sockets.detach(ctx.tenant_id, device.id, channel)
        logger.info("device %s disconnected", device.id)
        with contextlib.suppress(Exception):
            await websocket.close()


class _Channel:
    """The registry's view of one socket. Narrow so nothing below the interface
    layer ever holds a ``WebSocket``."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def send_text(self, text: str) -> None:
        await self._websocket.send_text(text)
