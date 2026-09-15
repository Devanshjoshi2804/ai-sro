"""Steel sessions API. Implements ``BrowserProvider``. See docs/07-adr/003-steel.md."""

from __future__ import annotations

import asyncio
import logging
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
"""Not a credential, and not replayable from the demonstration either.

Blue Yonder's auth filter reads a per-session ``libraryContext`` out of the
Referer and redirects to the login page without it. The executor sent a live
cookie and a live token and still got a 302 -- which looks exactly like being
signed out. The page the application itself calls from is part of the session,
so it is kept with the session."""

_WANTED = frozenset({Sensitivity.AUTH, Sensitivity.CSRF})
"""What authenticates a call, and nothing else. The cookie is kept separately
and refreshed on its own schedule; the transport headers belong to the request
being made, not to the one being replayed."""

logger = logging.getLogger(__name__)

_LIVE_ATTEMPTS = 4
_LIVE_POLL_SECONDS = 0.5
"""Chrome takes a moment to attach, so `idle` is only a failure once it has had
a few seconds to stop being one."""


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
        dimensions: tuple[int, int] = (1600, 1000),
        client: httpx.AsyncClient | None = None,
        public_base_url: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cdp_url = cdp_url.rstrip("/")
        # Everything this client does itself goes to `_base_url`. The one
        # string it builds for somebody else's browser uses this.
        self._viewer_base = (public_base_url or base_url).rstrip("/")
        self._timeout_seconds = session_timeout_seconds
        self._dimensions = dimensions
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def open(self, *, start_url: str | None = None) -> BrowserSession:
        # Measured against this deployment: creating a session while another is
        # `live` does not add a browser, it *takes* the one there is -- the
        # previous session vanishes from the list mid-task. So a sign-in, a
        # session check or a second pursuit silently killed whatever was already
        # on screen, and the thing that lost its browser reported, truthfully,
        # that the screen stopped responding to it.
        #
        # Refusing says which session holds it, which is something an operator
        # can act on. An `idle` session has no browser behind it and is not
        # holding anything, so it does not count.
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
            # Sized deliberately. The operator has to be able to read the screen
            # they are demonstrating on, and the accessibility tree that gets
            # captured is the one this viewport produced -- a cramped layout
            # teaches a skill about a layout nobody uses.
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
            # Steel reports its own URLs as seen from inside its container
            # (0.0.0.0:3000). Only the path is usable from out here; the host
            # comes from configuration, which knows the published ports.
            live_view_url=self._viewer(body),
            debugger_url=await self._websocket_debugger_url(),
        )

    async def _require_browser(self, session_id: BrowserSessionId, status: str) -> None:
        """Refuse a session that has no browser behind it.

        Steel answers 201 whether or not Chrome came up: a session with nothing
        attached is reported as `idle`, and a self-hosted Steel has exactly one
        browser to give. Handing that back produced a teaching session that
        looked like it was recording and showed "the browser session has ended"
        -- half an hour of a demonstration going nowhere.

        A brief `idle` is normal while Chrome starts, so this waits before
        deciding, and then says which session is holding the browser.
        """
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
        """Sessions Steel currently believes are using the browser."""
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
        sessions the provider already reaped.

        The release is checked rather than assumed. Steel answers 200 to
        releasing a session whose Chrome has already died and leaves it marked
        live, which reads as success and holds the only browser forever.
        """
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
        """A short-lived CDP attachment.

        Deliberately not held open: these run against a browser a human is
        using, and an idle connection to it is a way to lose their session
        rather than keep it.
        """
        debugger_url = await self._websocket_debugger_url()
        async with async_playwright() as driver:
            browser = await driver.chromium.connect_over_cdp(debugger_url)
            try:
                yield browser
            finally:
                await browser.close()

    async def session_cookies(self, session_id: BrowserSessionId) -> tuple[dict[str, object], ...]:
        """Read the cookies through a short-lived CDP attachment.

        Deliberately not held open: this runs once, when a human has just
        finished logging in, and an idle connection to the browser they are
        using is a way to lose their session rather than keep it.
        """
        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else None
            cookies = await context.cookies() if context else []
        return tuple(dict(cookie) for cookie in cookies)

    async def forget_everything(self, session_id: BrowserSessionId) -> None:
        """Clear the cookie jar this deployment's one browser carries between
        sessions, so what a session is signed into is only what it restored."""
        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            cdp = await context.new_cdp_session(page)
            await cdp.send("Network.clearBrowserCookies")
            await cdp.detach()

    async def restore(self, session_id: BrowserSessionId, cookies: list[dict[str, object]]) -> None:
        """Set stored cookies, addressed so the browser will accept them.

        ``Network.setCookies`` derives the source scheme from the URL, and drops
        a cookie marked secure without one -- silently, in a batch it still
        reports as successful. The identity provider's cookies are exactly the
        secure ones.
        """
        if not cookies:
            return
        async with self._attached() as browser:
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            cdp = await context.new_cdp_session(page)
            await cdp.send("Network.setCookies", {"cookies": [_addressed(c) for c in cookies]})
            await cdp.detach()

    async def session_headers(self, session_id: BrowserSessionId, url: str) -> dict[str, str]:
        """Watch the application make one request, and keep what authenticates it.

        The page is reloaded rather than merely observed: the tokens wanted are
        sent on the application's own data calls, and a browser sitting idle on
        a screen makes none. Reloading the address the connection names is the
        cheapest way to provoke exactly the traffic the executor will imitate.

        Only same-origin requests are read. A third party's bearer token is
        theirs, is useless against this system, and has no business in a vault
        keyed by it.
        """
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
                # Data calls only: the document request carries no token, and
                # its Referer is whatever the operator came from.
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
                # The data calls follow the document, not the other way round.
                await page.wait_for_timeout(6000)
            except Exception:
                logger.warning("could not provoke traffic at %s", url, exc_info=True)
            finally:
                await cdp.detach()

        return found

    async def live_sessions(self) -> tuple[BrowserSessionId, ...]:
        """Every session Steel currently has a browser for."""
        return tuple(BrowserSessionId(str(held["id"])) for held in await self._live_sessions())

    async def debugger_url(self, session_id: BrowserSessionId) -> str:
        """A self-hosted Steel has one browser, so this is the same endpoint for
        every session it reports. Asked per session anyway, because that is what
        the port promises and what a pool would have to honour."""
        return await self._websocket_debugger_url()

    async def frames(self, session_id: BrowserSessionId) -> AsyncIterator[bytes]:
        """The session's screen off CDP, rather than Steel's own viewer page."""
        async for frame in stream_frames(await self.debugger_url(session_id)):
            yield frame

    async def live_view_url(self, session_id: BrowserSessionId) -> str | None:
        """Ask Steel where the session can be driven.

        A released session still answers, but with a status that says it is over;
        there is nothing to point an operator at, so that is ``None``.
        """
        try:
            response = await self._client.get(f"{self._base_url}/v1/sessions/{session_id}")
            if response.status_code == httpx.codes.NOT_FOUND:
                return None
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrowserUnavailable(f"could not read Steel session {session_id}: {exc}") from exc

        body = response.json()
        # `idle` too: a viewer pointed at a session with no browser behind it
        # renders an empty frame that reads as "the operator's work vanished".
        if str(body.get("status", "")).lower() in {"released", "failed", "idle"}:
            return None
        return self._viewer(body)

    def _viewer(self, body: dict[str, object]) -> str:
        """Steel's bare session player rather than its own console.

        `sessionViewerUrl` is Steel's product UI — its header, its Docs and
        Discord links, a details panel and a Release Session button sitting
        inside our teaching screen, offering an operator a way to end the
        recording that we would never hear about. `debugUrl` is the same
        screencast with none of it.
        """
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
    """Which sessions are holding the only browser, and since when.

    One sentence, two callers: refusing to take the browser from somebody, and
    reporting that nothing attached to the session we were given. An operator
    needs the same three facts either way -- who has it, how long they have had
    it, and that a stuck one outlives its own Chrome.
    """
    return (
        ", ".join(
            f"{held.get('id')} has been {held.get('status')} since {held.get('createdAt')}"
            for held in holders[:3]
        )
        + " — a self-hosted Steel has one browser, and a session it still calls live "
        "after its Chrome has gone will hold it forever. Restart the Steel container."
    )


def _path_of(url: object) -> str:
    """Path and query of a URL, or "/" when there is nothing useful."""
    if not url:
        return "/"
    parts = urlsplit(str(url))
    path = parts.path or "/"
    return f"{path}?{parts.query}" if parts.query else path
