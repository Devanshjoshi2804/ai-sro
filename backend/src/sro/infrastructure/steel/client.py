"""Steel sessions API. Implements ``BrowserProvider``. See docs/07-adr/003-steel.md."""

from __future__ import annotations

from types import TracebackType
from urllib.parse import urlsplit

import httpx

from sro.application.ports.browser import BrowserSession, BrowserUnavailable
from sro.domain.shared.identifiers import BrowserSessionId


class SteelClient:
    """Talks to a self-hosted Steel instance.

    Steel's REST shape is confined to this module. The application only knows
    ``BrowserProvider``, so replacing Steel is an adapter change.
    """

    def __init__(
        self,
        base_url: str,
        cdp_url: str,
        *,
        session_timeout_seconds: int = 3600,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cdp_url = cdp_url.rstrip("/")
        self._timeout_seconds = session_timeout_seconds
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def open(self, *, start_url: str | None = None) -> BrowserSession:
        payload: dict[str, object] = {
            "timeout": self._timeout_seconds * 1000,
            "blockAds": True,
            "solveCaptcha": False,
        }
        if start_url:
            payload["startUrl"] = start_url

        try:
            response = await self._client.post(f"{self._base_url}/v1/sessions", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not start a Steel session: {exc}") from exc

        body = response.json()
        session_id = str(body["id"])
        return BrowserSession(
            id=BrowserSessionId(session_id),
            # Steel reports its own URLs as seen from inside its container
            # (0.0.0.0:3000). Only the path is usable from out here; the host
            # comes from configuration, which knows the published ports.
            live_view_url=self._base_url + _path_of(body.get("sessionViewerUrl")),
            debugger_url=await self._websocket_debugger_url(),
        )

    async def _websocket_debugger_url(self) -> str:
        """Chrome's own websocket endpoint, with the host put back.

        Chrome derives ``webSocketDebuggerUrl`` from the request Host header and
        drops the port, so what it returns is ``ws://localhost/devtools/...``.
        Following that verbatim dials port 80. The path is right; the authority
        has to come from configuration.
        """
        try:
            response = await self._client.get(f"{self._cdp_url}/json/version")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not reach the CDP endpoint: {exc}") from exc

        authority = urlsplit(self._cdp_url).netloc
        path = _path_of(response.json().get("webSocketDebuggerUrl"))
        return f"ws://{authority}{path}"

    async def close(self, session_id: BrowserSessionId) -> None:
        """Release the session. A 404 is success -- crash recovery calls this on
        sessions the provider already reaped."""
        try:
            response = await self._client.post(f"{self._base_url}/v1/sessions/{session_id}/release")
            if response.status_code == httpx.codes.NOT_FOUND:
                return
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(
                f"could not release Steel session {session_id}: {exc}"
            ) from exc

    async def health(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/v1/health")
        except httpx.HTTPError:
            return False
        return response.is_success

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> SteelClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()


def _path_of(url: object) -> str:
    """Path and query of a URL, or "/" when there is nothing useful."""
    if not url:
        return "/"
    parts = urlsplit(str(url))
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path
