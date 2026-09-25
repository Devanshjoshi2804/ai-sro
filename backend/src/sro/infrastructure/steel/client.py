from __future__ import annotations

import asyncio
import json
import logging
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from types import TracebackType
from typing import Any
from urllib.parse import urlsplit

import httpx
import websockets
from playwright.async_api import Browser, BrowserContext, CDPSession, Page, async_playwright
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.browser import BrowserSession, BrowserUnavailable
from sro.domain.recording.sensitivity import K_TOKENS, classify_header
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel.capture import addressed
from sro.infrastructure.steel.screencast import stream_frames

_CONTEXT = frozenset({"referer"})

K_TOKEN_WAIT_S = 6

logger = logging.getLogger(__name__)

_LIVE_ATTEMPTS = 4
_LIVE_POLL_SECONDS = 0.5

K_MAX_CONTEXTS_PER_CONTAINER = 20

K_CONTEXT_PAGE_TIMEOUT_S = 10

K_BROWSER_REPLY_S = 10.0


class SteelClient:
    def __init__(
        self,
        base_url: str,
        cdp_url: str,
        *,
        capacity: int = 1,
        session_timeout_seconds: int = 3600,
        dimensions: tuple[int, int] = (1600, 1000),
        client: httpx.AsyncClient | None = None,
        public_base_url: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cdp_url = cdp_url.rstrip("/")
        self._viewer_base = (public_base_url or base_url).rstrip("/")
        self._capacity = capacity
        self._timeout_seconds = session_timeout_seconds
        self._dimensions = dimensions
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def open(self, *, start_url: str | None = None) -> BrowserSession:
        holding = await self._holding()
        if holding:
            raise BrowserUnavailable(
                f"this container holds {self._capacity} context(s) and all are in "
                "use; " + _held_by(holding)
            )
        body = await self._start(start_url)
        return BrowserSession(
            id=BrowserSessionId(str(body["id"])),
            live_view_url=self._viewer(body),
            debugger_url=await self._websocket_debugger_url(),
        )

    async def open_context(self) -> tuple[BrowserSessionId, str]:
        holding = await self._holding()
        session_id = str(holding[0]["id"] if holding else (await self._start(None))["id"])
        return BrowserSessionId(session_id), await self._new_context()

    async def contexts(self) -> frozenset[str]:
        listed = await self._browser_call("Target.getBrowserContexts", {})
        return frozenset(str(one) for one in listed["browserContextIds"])

    async def dispose(self, context_id: str) -> None:
        try:
            await self._browser_call(
                "Target.disposeBrowserContext", {"browserContextId": context_id}
            )
        except BrowserUnavailable:
            if context_id in await self.contexts():
                raise

    async def _holding(self) -> list[dict[str, object]]:
        return [
            held
            for held in await self._live_sessions()
            if str(held.get("status", "")).lower() == "live"
        ]

    async def _start(self, start_url: str | None) -> dict[str, Any]:
        payload: dict[str, object] = {
            "timeout": self._timeout_seconds * 1000,
            "blockAds": True,
            "solveCaptcha": False,
            "skipFingerprintInjection": True,
            "dimensions": {"width": self._dimensions[0], "height": self._dimensions[1]},
        }
        if start_url:
            payload["startUrl"] = start_url

        try:
            response = await self._client.post(f"{self._base_url}/v1/sessions", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not start a Steel session: {exc}") from exc

        body: dict[str, Any] = response.json()
        await self._require_browser(BrowserSessionId(str(body["id"])), str(body.get("status", "")))
        return body

    async def _new_context(self) -> str:
        made = await self._browser_call("Target.createBrowserContext", {"disposeOnDetach": False})
        return str(made["browserContextId"])

    async def _browser_call(self, method: str, params: dict[str, object]) -> dict[str, Any]:
        try:
            async with (
                asyncio.timeout(K_BROWSER_REPLY_S),
                websockets.connect(await self._websocket_debugger_url(), max_size=None) as link,
            ):
                await link.send(json.dumps({"id": 1, "method": method, "params": params}))
                async for raw in link:
                    said = json.loads(raw)
                    if said.get("id") != 1:
                        continue
                    if "error" in said:
                        raise BrowserUnavailable(f"{method} failed: {said['error']}")
                    return dict(said["result"])
        except TimeoutError as why:
            raise BrowserUnavailable(
                f"{method}: the browser did not answer within {K_BROWSER_REPLY_S} s"
            ) from why
        except (websockets.WebSocketException, OSError) as why:
            raise BrowserUnavailable(f"{method} failed: {why}") from why
        raise BrowserUnavailable(f"{method}: the browser closed the connection")

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
        matched = await self._named(session_id)
        return str(matched.get("status", "unknown")) if matched else "unknown"

    async def _named(self, session_id: BrowserSessionId) -> dict[str, object] | None:
        return next(
            (
                session
                for session in await self._sessions()
                if str(session.get("id")) == str(session_id)
            ),
            None,
        )

    async def _sessions(self) -> list[dict[str, object]]:
        try:
            response = await self._client.get(f"{self._base_url}/v1/sessions")
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        return list(response.json().get("sessions", []))

    async def _live_sessions(self) -> list[dict[str, object]]:
        return [
            session
            for session in await self._sessions()
            if str(session.get("status", "")).lower() in {"live", "idle"}
        ]

    async def _websocket_debugger_url(self) -> str:
        try:
            return await websocket_debugger_url(self._cdp_url, self._client)
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not reach the CDP endpoint: {exc}") from exc

    async def close(self, session_id: BrowserSessionId) -> None:
        if await self.contexts():
            logger.warning(
                "refusing to release Steel session %s while its container still lists a "
                "browser context; a self-hosted Steel releases its one browser for any "
                "id it is asked to release",
                session_id,
            )
            return
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
            if self._capacity == 1:
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(url, wait_until="domcontentloaded")
                return

            sid = str(session_id)
            raw = await browser.new_browser_cdp_session()
            await self._require_context(raw, sid)
            page = await self._own_page(browser, raw, sid, url)
            await page.wait_for_load_state("domcontentloaded")
            await raw.detach()

    async def _require_context(self, raw: CDPSession, sid: str) -> None:
        try:
            ids = (await raw.send("Target.getBrowserContexts"))["browserContextIds"]
        except PlaywrightError as why:
            raise BrowserUnavailable(f"could not verify context {sid}: {why}") from why
        if sid not in ids:
            raise BrowserUnavailable(f"context {sid} no longer exists in this container")

    async def _own_page(self, browser: Browser, raw: CDPSession, sid: str, url: str) -> Page:
        for target in (await raw.send("Target.getTargets"))["targetInfos"]:
            if target.get("browserContextId") == sid and target.get("type") == "page":
                await raw.send("Target.closeTarget", {"targetId": target["targetId"]})

        default_context: BrowserContext = (
            browser.contexts[0] if browser.contexts else await browser.new_context()
        )
        try:
            made = await raw.send("Target.createTarget", {"url": url, "browserContextId": sid})
        except PlaywrightError as why:
            raise BrowserUnavailable(f"could not open a page in context {sid}: {why}") from why
        target_id = str(made["targetId"])

        loop = asyncio.get_running_loop()
        deadline = loop.time() + K_CONTEXT_PAGE_TIMEOUT_S
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise BrowserUnavailable(f"context {sid} did not surface its page in time")
            try:
                page = await default_context.wait_for_event("page", timeout=remaining * 1000)
            except PlaywrightError as why:
                raise BrowserUnavailable(
                    f"context {sid} did not surface its page in time: {why}"
                ) from why
            info_session = await default_context.new_cdp_session(page)
            info = await info_session.send("Target.getTargetInfo")
            await info_session.detach()
            if str(info["targetInfo"]["targetId"]) == target_id:
                return page

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
            if self._capacity == 1:
                context = browser.contexts[0] if browser.contexts else None
                cookies = list(await context.cookies()) if context else []
                return tuple(dict(cookie) for cookie in cookies)

            sid = str(session_id)
            raw = await browser.new_browser_cdp_session()
            await self._require_context(raw, sid)
            found = (await raw.send("Storage.getCookies", {"browserContextId": sid}))["cookies"]
            await raw.detach()
            return tuple(dict(cookie) for cookie in found)

    async def forget_everything(self, session_id: BrowserSessionId) -> None:
        async with self._attached() as browser:
            if self._capacity == 1:
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = context.pages[0] if context.pages else await context.new_page()
                cdp = await context.new_cdp_session(page)
                await cdp.send("Network.clearBrowserCookies")
                await cdp.detach()
                return

            sid = str(session_id)
            raw = await browser.new_browser_cdp_session()
            await self._require_context(raw, sid)
            await raw.send("Storage.clearCookies", {"browserContextId": sid})
            await raw.detach()

    async def restore(self, session_id: BrowserSessionId, cookies: list[dict[str, object]]) -> None:
        if not cookies:
            return
        async with self._attached() as browser:
            if self._capacity == 1:
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = context.pages[0] if context.pages else await context.new_page()
                cdp = await context.new_cdp_session(page)
                await cdp.send("Network.setCookies", {"cookies": [addressed(c) for c in cookies]})
                await cdp.detach()
                return

            sid = str(session_id)
            raw = await browser.new_browser_cdp_session()
            await self._require_context(raw, sid)
            await raw.send(
                "Storage.setCookies",
                {"cookies": [addressed(c) for c in cookies], "browserContextId": sid},
            )
            await raw.detach()

    async def session_headers(self, session_id: BrowserSessionId, url: str) -> dict[str, str]:
        host = urlsplit(url).hostname or ""
        found: dict[str, str] = {}
        tokened = asyncio.Event()

        async with self._attached() as browser:
            if self._capacity == 1:
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                sid = str(session_id)
                raw = await browser.new_browser_cdp_session()
                await self._require_context(raw, sid)
                page = await self._own_page(browser, raw, sid, "about:blank")
                await raw.detach()

            cdp = await page.context.new_cdp_session(page)

            def observe(event: dict[str, Any]) -> None:
                request = event.get("request") or {}
                if (urlsplit(str(request.get("url", ""))).hostname or "") != host:
                    return
                for name, value in (request.get("headers") or {}).items():
                    if not isinstance(value, str):
                        continue
                    token = classify_header(name) in K_TOKENS
                    if token or name.lower() in _CONTEXT:
                        found.setdefault(name.lower(), value)
                    if token:
                        tokened.set()

            cdp.on("Network.requestWillBeSent", observe)
            await cdp.send("Network.enable")
            try:
                await page.goto(url, wait_until="domcontentloaded")
                with suppress(TimeoutError):
                    async with asyncio.timeout(K_TOKEN_WAIT_S):
                        await tokened.wait()
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
        matched = await self._named(session_id)
        if matched is None:
            return None
        if str(matched.get("status", "")).lower() in {"released", "failed", "idle"}:
            return None
        return self._viewer(matched)

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
        + " — a self-hosted Steel container has one browser, and a session it still calls "
        "live after its Chrome has gone will hold that capacity forever. Restart the "
        "Steel container."
    )


async def cdp_origin(cdp_url: str) -> str:
    parts = urlsplit(cdp_url)
    host, port = parts.hostname or "localhost", parts.port or 9223
    try:
        found = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
    except OSError:
        return parts.netloc
    return f"{found[0][4][0]!s}:{port}"


async def websocket_debugger_url(cdp_url: str, client: httpx.AsyncClient) -> str:
    authority = await cdp_origin(cdp_url)
    if urlsplit(cdp_url).scheme in {"ws", "wss"}:
        return f"ws://{authority}{_path_of(cdp_url)}"
    response = await client.get(f"http://{authority}/json/version")
    response.raise_for_status()
    return f"ws://{authority}{_path_of(response.json().get('webSocketDebuggerUrl'))}"


def _path_of(url: object) -> str:
    if not url:
        return "/"
    parts = urlsplit(str(url))
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path
