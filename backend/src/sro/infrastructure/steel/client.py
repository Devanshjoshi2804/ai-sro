from __future__ import annotations

import asyncio
import logging
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Any
from urllib.parse import urlsplit

import httpx
from playwright.async_api import Browser, async_playwright

from sro.application.ports.browser import BrowserSession, BrowserUnavailable
from sro.domain.recording.sensitivity import Sensitivity, classify_header
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel.capture import _addressed
from sro.infrastructure.steel.screencast import stream_frames

_CONTEXT = frozenset({"referer"})

_WANTED = frozenset({Sensitivity.AUTH, Sensitivity.CSRF})

logger = logging.getLogger(__name__)

_LIVE_ATTEMPTS = 4
_LIVE_POLL_SECONDS = 0.5


class SteelClient:
    def __init__(
        self,
        base_url: str,
        cdp_url: str,
        *,
        session_timeout_seconds: int = 3600,
        dimensions: tuple[int, int] = (1600, 1000),
        client: httpx.AsyncClient | None = None,
        public_base_url: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cdp_url = cdp_url.rstrip("/")
        self._viewer_base = (public_base_url or base_url).rstrip("/")
        self._timeout_seconds = session_timeout_seconds
        self._dimensions = dimensions
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def open(self, *, start_url: str | None = None) -> BrowserSession:
        holding = [
            held
            for held in await self._live_sessions()
            if str(held.get("status", "")).lower() == "live"
        ]
        if holding:
            raise BrowserUnavailable(
                "this deployment has one browser and it is already in use; " + _held_by(holding)
            )

        payload: dict[str, object] = {
            "timeout": self._timeout_seconds * 1000,
            "blockAds": True,
            "solveCaptcha": False,
            "dimensions": {"width": self._dimensions[0], "height": self._dimensions[1]},
        }
        if start_url:
            payload["startUrl"] = start_url

        try:
            response = await self._client.post(f"{self._base_url}/v1/sessions", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not start a Steel session: {exc}") from exc

        body = response.json()
        session_id = BrowserSessionId(str(body["id"]))
        await self._require_browser(session_id, str(body.get("status", "")))

        return BrowserSession(
            id=session_id,
            live_view_url=self._viewer(body),
            debugger_url=await self._websocket_debugger_url(),
        )

    async def _require_browser(self, session_id: BrowserSessionId, status: str) -> None:
        for attempt in range(_LIVE_ATTEMPTS):
            if status.lower() == "live":
                return
            if status.lower() in {"released", "failed"}:
                break
            await asyncio.sleep(_LIVE_POLL_SECONDS * (attempt + 1))
            status = await self._status(session_id)

        holders = [
            held for held in await self._live_sessions() if str(held.get("id")) != str(session_id)
        ]
        await self.close(session_id)
        raise BrowserUnavailable(
            f"Steel accepted the session but no browser attached to it (status {status!r})"
            + (
                "; " + _held_by(holders)
                if holders
                else " — check that Chrome can start inside the Steel container."
            )
        )

    async def _status(self, session_id: BrowserSessionId) -> str:
        try:
            response = await self._client.get(f"{self._base_url}/v1/sessions/{session_id}")
            response.raise_for_status()
        except httpx.HTTPError:
            return "unknown"
        return str(response.json().get("status", "unknown"))

    async def _live_sessions(self) -> list[dict[str, object]]:
        try:
            response = await self._client.get(f"{self._base_url}/v1/sessions")
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        sessions = response.json().get("sessions", [])
        return [
            session
            for session in sessions
            if str(session.get("status", "")).lower() in {"live", "idle"}
        ]

    async def _cdp_origin(self) -> str:
        parts = urlsplit(self._cdp_url)
        host, port = parts.hostname or "localhost", parts.port or 9223
        try:
            found = await asyncio.get_running_loop().getaddrinfo(
                host, port, family=socket.AF_INET, type=socket.SOCK_STREAM
            )
        except OSError:
            return parts.netloc
        return f"{found[0][4][0]!s}:{port}"

    async def _websocket_debugger_url(self) -> str:
        authority = await self._cdp_origin()
        try:
            response = await self._client.get(f"http://{authority}/json/version")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not reach the CDP endpoint: {exc}") from exc

        path = _path_of(response.json().get("webSocketDebuggerUrl"))
        return f"ws://{authority}{path}"

    async def close(self, session_id: BrowserSessionId) -> None:
        try:
            response = await self._client.post(f"{self._base_url}/v1/sessions/{session_id}/release")
            if response.status_code == httpx.codes.NOT_FOUND:
                return
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(
                f"could not release Steel session {session_id}: {exc}"
            ) from exc

        if (status := await self._status(session_id)).lower() in {"live", "idle"}:
            logger.warning(
                "Steel accepted the release of %s and still reports it as %s; "
                "its browser is gone and the session will hold Steel's only one "
                "until the container is restarted",
                session_id,
                status,
            )

    async def navigate(self, session_id: BrowserSessionId, url: str) -> None:
        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")

    @asynccontextmanager
    async def _attached(self) -> AsyncIterator[Browser]:
        debugger_url = await self._websocket_debugger_url()
        async with async_playwright() as driver:
            browser = await driver.chromium.connect_over_cdp(debugger_url)
            try:
                yield browser
            finally:
                await browser.close()

    async def session_cookies(self, session_id: BrowserSessionId) -> tuple[dict[str, object], ...]:
        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else None
            cookies = await context.cookies() if context else []
        return tuple(dict(cookie) for cookie in cookies)

    async def forget_everything(self, session_id: BrowserSessionId) -> None:
        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            cdp = await context.new_cdp_session(page)
            await cdp.send("Network.clearBrowserCookies")
            await cdp.detach()

    async def restore(self, session_id: BrowserSessionId, cookies: list[dict[str, object]]) -> None:
        if not cookies:
            return
        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            cdp = await context.new_cdp_session(page)
            await cdp.send("Network.setCookies", {"cookies": [_addressed(c) for c in cookies]})
            await cdp.detach()

    async def session_headers(self, session_id: BrowserSessionId, url: str) -> dict[str, str]:
        host = urlsplit(url).hostname or ""
        found: dict[str, str] = {}

        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            cdp = await context.new_cdp_session(page)

            def observe(event: dict[str, Any]) -> None:
                request = event.get("request") or {}
                if (urlsplit(str(request.get("url", ""))).hostname or "") != host:
                    return
                if "/data/" not in str(request.get("url", "")):
                    return
                for name, value in (request.get("headers") or {}).items():
                    if not isinstance(value, str):
                        continue
                    if classify_header(name) in _WANTED or name.lower() in _CONTEXT:
                        found.setdefault(name.lower(), value)

            cdp.on("Network.requestWillBeSent", observe)
            await cdp.send("Network.enable")
            try:
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(6000)
            except Exception:
                logger.warning("could not provoke traffic at %s", url, exc_info=True)
            finally:
                await cdp.detach()

        return found

    async def live_sessions(self) -> tuple[BrowserSessionId, ...]:
        return tuple(BrowserSessionId(str(held["id"])) for held in await self._live_sessions())

    async def debugger_url(self, session_id: BrowserSessionId) -> str:
        return await self._websocket_debugger_url()

    async def frames(self, session_id: BrowserSessionId) -> AsyncIterator[bytes]:
        async for frame in stream_frames(await self.debugger_url(session_id)):
            yield frame

    async def live_view_url(self, session_id: BrowserSessionId) -> str | None:
        try:
            response = await self._client.get(f"{self._base_url}/v1/sessions/{session_id}")
            if response.status_code == httpx.codes.NOT_FOUND:
                return None
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not read Steel session {session_id}: {exc}") from exc

        body = response.json()
        if str(body.get("status", "")).lower() in {"released", "failed", "idle"}:
            return None
        return self._viewer(body)

    def _viewer(self, body: dict[str, object]) -> str:
        return self._viewer_base + _path_of(body.get("debugUrl") or body.get("sessionViewerUrl"))

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


def _held_by(holders: list[dict[str, object]]) -> str:
    return (
        ", ".join(
            f"{held.get('id')} has been {held.get('status')} since {held.get('createdAt')}"
            for held in holders[:3]
        )
        + " — a self-hosted Steel has one browser, and a session it still calls live "
        "after its Chrome has gone will hold it forever. Restart the Steel container."
    )


def _path_of(url: object) -> str:
    if not url:
        return "/"
    parts = urlsplit(str(url))
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path
