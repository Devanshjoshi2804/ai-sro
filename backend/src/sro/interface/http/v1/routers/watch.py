"""Watching a browser session, frame by frame, over a websocket.

The provider's own viewer was the thing an operator pressed "Watch it" for, and
self-hosted Steel answers that with one page for the whole deployment: no
session in the URL, "Session connecting..." forever once the browser it means
has been released. This serves the session's screen instead -- the same picture,
from Chrome's screencast, addressed by the session the operator asked about.

View-only on purpose. Teaching happens in a browser the operator drives
themselves; what this is for is watching work that is being done for them.
"""

from __future__ import annotations

import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from sro.application.ports.auth import CredentialRejected, Unconfigured
from sro.application.ports.browser import BrowserUnavailable
from sro.container import Container
from sro.domain.shared.identifiers import BrowserSessionId

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browser", tags=["browser"])

_BEARER = "bearer"
"""A browser cannot set headers on a websocket, and a token in the query string
is a token in every access log and referrer. The subprotocol list can carry it,
which is what it is used for everywhere else this problem comes up."""


@router.websocket("/{session_id}/live")
async def watch_session(websocket: WebSocket, session_id: str) -> None:
    """JPEG frames as binary messages, until the socket closes or the browser does."""
    container: Container = websocket.app.state.container
    protocols = [
        part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")
    ]
    token = protocols[1] if len(protocols) > 1 and protocols[0] == _BEARER else ""

    try:
        container.credentials.verify(f"Bearer {token}")
    except (CredentialRejected, Unconfigured):
        # Closed rather than refused with a status: the handshake has not been
        # accepted, so there is no response body a browser would ever show.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept(subprotocol=_BEARER)
    try:
        async for frame in container.browser.frames(BrowserSessionId(session_id)):
            await websocket.send_bytes(frame)
    except WebSocketDisconnect:
        return
    except BrowserUnavailable as exc:
        logger.info("live view for %s ended: %s", session_id, exc)
    except Exception:
        logger.exception("live view for %s failed", session_id)
    with contextlib.suppress(RuntimeError):
        # The socket is already closed when the viewer left first, and closing a
        # closed socket raises rather than being the no-op it reads as.
        await websocket.close()
