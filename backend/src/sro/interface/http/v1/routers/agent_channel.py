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
from sro.infrastructure.telemetry.whose import attribute

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
        # A valid credential is not ownership. The device has to be this
        # tenant's and has to prove it is itself, and one that is neither is
        # closed exactly like one that does not exist -- a socket that closed
        # differently for a wrong secret would be a way to enumerate devices
        # without ever holding one.
        device = await container.read_device().execute(
            ctx, device_id=DeviceId(device_id), secret=secret
        )
    except (CredentialRejected, Unconfigured, NotFound):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept(subprotocol=_BEARER)
    sockets = container.agent_sockets
    channel = _Channel(websocket)
    # The socket authenticates for itself -- no `ContextDep`, no
    # `asking_device` -- so the attribution those two install never reached
    # here, and the one door that stays open for a whole session was the one
    # door whose lines said nothing about whose session it was. Set after the
    # credential and the secret have both been checked, for `asking_device`'s
    # reason: an id in a query string is a claim until something proves it.
    attribute(tenant=ctx.tenant_id.value, principal=ctx.principal_id.value, device=device.id.value)
    sockets.attach(ctx.tenant_id, device.id, channel)
    logger.info("device %s connected", device.id)

    try:
        while True:
            # Named here, not by the message: a browser that told the registry
            # which device it was could tell it that it was another one.
            sockets.deliver(await websocket.receive_text(), ctx.tenant_id, device.id)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("the channel to device %s failed", device.id)
    finally:
        sockets.detach(ctx.tenant_id, device.id, channel)
        logger.info("device %s disconnected", device.id)
        # Closing a socket that has already gone is not a failure, and there
        # is nothing left to do about it either way.
        #
        # `RuntimeError` alone was not enough. A browser that goes -- an
        # extension reloaded, a laptop shut, a tunnel dropped -- leaves this
        # `close()` writing a close frame to nobody, and uvicorn answers that
        # with `ClientDisconnected`, which is neither a `RuntimeError` nor
        # importable from here without reaching into a server's internals. It
        # went uncaught, out of the endpoint, and printed thirty lines of
        # `Exception in ASGI application` for the ordinary event this
        # `finally` exists to handle. Measured on the deployment 2026-09-21:
        # two of them against three reconnections.
        #
        # Broad on purpose and only here. The detach above has already
        # happened, the disconnection is already said, and the one thing this
        # line can still do is not shout about a socket nobody is holding.
        with contextlib.suppress(Exception):
            await websocket.close()


class _Channel:
    """The registry's view of one socket. Narrow so nothing below the interface
    layer ever holds a ``WebSocket``."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def send_text(self, text: str) -> None:
        await self._websocket.send_text(text)
