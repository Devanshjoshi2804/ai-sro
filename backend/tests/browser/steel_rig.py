from __future__ import annotations

import asyncio
import contextlib
import json
import os
import secrets
import socket
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import pytest
from playwright.async_api import CDPSession, async_playwright
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.page import SessionRef
from sro.config import get_settings
from sro.infrastructure.steel.client import websocket_debugger_url
from sro.infrastructure.steel.driver import SteelDriver

_PUBLIC_PAGE = "<!doctype html><html><body><h1>public</h1></body></html>"

_FRAMED_PAGE = """<!doctype html><html><body>
  <iframe src="/public"></iframe><iframe src="/app"></iframe>
</body></html>"""

_FRAMED_TWICE_PAGE = """<!doctype html><html><body>
  <iframe src="/app"></iframe><iframe src="/app"></iframe>
</body></html>"""

_APP_PAGE = """<!doctype html><html><head><meta name="csrf-token" content="{token}"></head><body>
  <form aria-label="Customer Type">
    <label for="ct">Customer Type</label><input id="ct" name="customerType">
    <label for="dept">Department</label><select id="dept" name="department">
      <option value=""></option><option>Finance</option><option>Operations</option>
    </select>
    <button id="save" type="button">Save</button>
    <button id="refresh" type="button">Refresh</button>
  </form>
  <script>
    document.getElementById("refresh").addEventListener("click", () => {{
      fetch("/api/customer-types?hold");
    }});
    document.getElementById("save").addEventListener("click", async () => {{
      const token = document.querySelector("meta[name=csrf-token]").content;
      const name = document.getElementById("ct").value;
      const department = document.getElementById("dept").value;
      await fetch("/api/customer-types", {{
        method: "POST",
        headers: {{"X-CSRF-Token": token, "content-type": "application/json"}},
        body: JSON.stringify(department ? {{name, department}} : {{name}}),
      }});
    }});
  </script>
</body></html>"""

_LOGIN_PAGE = """<!doctype html><html><body>
  <form method="post" action="/idp/login?state={state}&response_mode={mode}">
    <input id="username" name="username">
    <input id="password" name="password" type="password">
    <button id="go" type="submit">Sign in</button>
  </form>
</body></html>"""

_IDENTIFIER_PAGE = """<!doctype html><html><body>
  <form method="post" action="/idp/next">
    <input id="username" name="username" autocomplete="username webauthn">
    <button id="next" type="submit">Next</button>
  </form>
</body></html>"""

_FORM_POST_PAGE = """<!doctype html><html><body onload="document.forms[0].submit()">
  <form method="post" action="{to}">
    <input type="hidden" name="code" value="{code}">
    <input type="hidden" name="state" value="{state}">
  </form>
</body></html>"""

_LANDING_PAGE = """<!doctype html><html><body><script>
  fetch("/api/ping", {method: "POST", headers: {"X-CSRF-Token": "landing-token"}});
</script></body></html>"""

_SIGN_IN_TIMEOUT_S = 10.0
_HELD_S = 30.0


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Rig:
    """A local app behind an identity-provider chain: `/` sends an
    unauthenticated visitor to `/idp/authorize`, which serves a login form
    posted to `/idp/login`; that redeems the credentials for a code redirected
    to `/cb`, which trades the code for a session cookie and lands on `/app`.
    `/app` also serves the CSRF-protected `/api/customer-types` write this
    task's live rig exercises. `/`'s own query is forwarded into the authorize
    request: `response_mode=fragment|form_post` picks how the code comes back,
    `prompt=none` returns an error at once, and `acr_values=identifier` sends
    on to an identifier-first page with no password field. `/held-login` answers
    only once the test sets `answer`, so a navigation can be caught in flight.
    `POST /api/ping` answers 201 from any page and sets `pinged`; with `?hold`
    it answers only once `release` is set, so a test can hold a request open
    across a mark. `/app`'s Refresh reads `/api/customer-types?hold`, which
    sets `asked` and answers only once `answer` is set; with `hold_saves` a
    save is kept and sets `asked`, and its answer waits the same way, so a
    test can act while a read or a write is in flight. With `idp_elsewhere`
    the identity provider answers on a
    second port -- a second origin, as a real one is -- and `logins` counts
    the credentials posted to it."""

    def __init__(self, *, for_steel: bool = False, idp_elsewhere: bool = False) -> None:
        self._for_steel = for_steel
        self._sessions: dict[str, str] = {}
        self._codes: dict[str, tuple[str, str]] = {}
        self._csrf: dict[str, str] = {}
        self.saved: list[dict[str, object]] = []
        self.asked = threading.Event()
        self.answer = threading.Event()
        self.pinged = threading.Event()
        self.release = threading.Event()
        self.hold_saves = False
        self.logins = 0
        host = "0.0.0.0" if for_steel else "127.0.0.1"  # noqa: S104
        self._servers = [ThreadingHTTPServer((host, 0), _handler_for(self))]
        if idp_elsewhere:
            self._servers.append(ThreadingHTTPServer((host, 0), _handler_for(self)))
        for server in self._servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()

    def _at(self, server: ThreadingHTTPServer, path: str) -> str:
        host = (
            os.environ.get("SRO_STEEL_SEES_HOST", "host.docker.internal")
            if self._for_steel
            else "127.0.0.1"
        )
        return f"http://{host}:{server.server_address[1]}{path}"

    def url(self, path: str) -> str:
        return self._at(self._servers[0], path)

    def idp_url(self, path: str) -> str:
        return self._at(self._servers[-1], path)

    def expire(self) -> None:
        self._sessions.clear()
        self._csrf.clear()

    def close(self) -> None:
        self.answer.set()
        for server in self._servers:
            server.shutdown()

    async def sign_in_in(
        self, driver: SteelDriver, session: SessionRef, target_id: str, *, lands: str = "/app"
    ) -> None:
        await driver.evaluate(
            session, target_id, "document.getElementById('username').value = 'operator'"
        )
        await driver.evaluate(
            session, target_id, "document.getElementById('password').value = 'a-password'"
        )
        with contextlib.suppress(PlaywrightError):
            await driver.evaluate(session, target_id, "document.getElementById('go').click()")

        loop = asyncio.get_running_loop()
        deadline = loop.time() + _SIGN_IN_TIMEOUT_S
        while True:
            if urlsplit(await driver.url_of(session, target_id)).path == lands:
                return
            if loop.time() > deadline:
                raise AssertionError("sign-in did not reach /app")
            await asyncio.sleep(0.1)


def _handler_for(rig: Rig) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return

        def _cookie(self) -> str | None:
            raw = self.headers.get("cookie", "")
            for part in raw.split(";"):
                name, _, value = part.strip().partition("=")
                if name == "sid" and value:
                    return value
            return None

        def _html(self, body: str, *, status: int = 200) -> None:
            raw = body.encode()
            self.send_response(status)
            self.send_header("content-type", "text/html")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _json(self, obj: object, *, status: int = 200) -> None:
            raw = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _redirect(self, location: str, *, cookie: str | None = None) -> None:
            self.send_response(302)
            self.send_header("location", location)
            if cookie is not None:
                self.send_header("set-cookie", cookie)
            self.end_headers()

        def do_GET(self) -> None:
            split = urlsplit(self.path)
            path, query = split.path, parse_qs(split.query, keep_blank_values=True)
            sid = self._cookie()

            if path == "/public":
                self._html(_PUBLIC_PAGE)
            elif path == "/framed":
                self._html(_FRAMED_PAGE)
            elif path == "/landing":
                self._html(_LANDING_PAGE)
            elif path == "/api/basic":
                if not self.headers.get("authorization"):
                    self.send_response(401)
                    self.send_header("www-authenticate", 'Basic realm="rig"')
                    self.send_header("content-length", "0")
                    self.end_headers()
                    return
                self._json({"ok": True})
            elif path == "/framed-twice":
                self._html(_FRAMED_TWICE_PAGE)
            elif path == "/":
                if sid and sid in rig._sessions:
                    self._redirect(rig.url("/app"))
                    return
                state = secrets.token_hex(8)
                params = urlencode(
                    {
                        "response_type": "code",
                        "client_id": "app",
                        "redirect_uri": rig.url("/cb"),
                        "state": state,
                        **{name: values[0] for name, values in query.items()},
                    }
                )
                self._redirect(rig.idp_url(f"/idp/authorize?{params}"))
            elif path == "/idp/authorize":
                state = query.get("state", [""])[0]
                if query.get("prompt") == ["none"]:
                    back = urlencode({"error": "login_required", "state": state})
                    self._redirect(f"{query['redirect_uri'][0]}?{back}")
                elif query.get("acr_values") == ["identifier"]:
                    self._redirect(rig.idp_url("/idp/identifier"))
                else:
                    mode = query.get("response_mode", ["query"])[0]
                    self._html(_LOGIN_PAGE.format(state=state, mode=mode))
            elif path == "/idp/identifier":
                self._html(_IDENTIFIER_PAGE)
            elif path == "/held-login":
                rig.asked.set()
                rig.answer.wait(_HELD_S)
                self._html(_LOGIN_PAGE.format(state="", mode="query"))
            elif path == "/cb":
                if "code" not in query:
                    self._html(_PUBLIC_PAGE)
                    return
                self._signed_in(query)
            elif path == "/app":
                if not sid or sid not in rig._sessions:
                    self._redirect(rig.url("/"))
                    return
                self._html(_APP_PAGE.format(token=rig._csrf[sid]))
            elif path == "/api/customer-types":
                if not sid or sid not in rig._sessions:
                    self.send_response(401)
                    self.end_headers()
                    return
                if "hold" in query:
                    rig.asked.set()
                    rig.answer.wait(_HELD_S)
                self._json(rig.saved)
            else:
                self.send_response(404)
                self.end_headers()

        def _signed_in(self, answer: dict[str, list[str]]) -> None:
            code, state = answer.get("code", [""])[0], answer.get("state", [""])[0]
            found = rig._codes.pop(code, None)
            if found is None or found[0] != state:
                self.send_response(401)
                self.end_headers()
                return
            new_sid = secrets.token_hex(16)
            rig._sessions[new_sid] = found[1]
            rig._csrf[new_sid] = secrets.token_hex(16)
            self._redirect(rig.url("/app"), cookie=f"sid={new_sid}; Path=/")

        def do_POST(self) -> None:
            split = urlsplit(self.path)
            path, query = split.path, parse_qs(split.query, keep_blank_values=True)
            body = self.rfile.read(int(self.headers.get("content-length") or 0))

            if path == "/api/ping":
                rig.pinged.set()
                if "hold" in query:
                    rig.release.wait(10)
                self._json({"id": "ping-1"}, status=201)
            elif path == "/idp/login":
                rig.logins += 1
                form = parse_qs(body.decode())
                username = form.get("username", [""])[0]
                state = query.get("state", [""])[0]
                code = secrets.token_hex(8)
                rig._codes[code] = (state, username)
                params = urlencode({"code": code, "state": state})
                mode = query.get("response_mode", ["query"])[0]
                if mode == "form_post":
                    self._html(_FORM_POST_PAGE.format(to=rig.url("/cb"), code=code, state=state))
                elif mode == "fragment":
                    self._redirect(rig.url(f"/cb#{params}"))
                else:
                    self._redirect(rig.url(f"/cb?{params}"))
            elif path == "/cb":
                self._signed_in(parse_qs(body.decode()))
            elif path == "/api/customer-types":
                sid = self._cookie()
                if not sid or sid not in rig._sessions:
                    self.send_response(401)
                    self.end_headers()
                    return
                if self.headers.get("x-csrf-token") != rig._csrf.get(sid):
                    self.send_response(401)
                    self.end_headers()
                    return
                rig.saved.append(json.loads(body or b"{}"))
                if rig.hold_saves:
                    rig.asked.set()
                    rig.answer.wait(_HELD_S)
                self._json({"ok": True}, status=201)
            else:
                self.send_response(404)
                self.end_headers()

    return Handler


@pytest.fixture
def rig() -> Iterator[Rig]:
    instance = Rig()
    try:
        yield instance
    finally:
        instance.close()


async def _chromium() -> AsyncIterator[str]:
    playwright_mod = pytest.importorskip("playwright.async_api")
    port = _free_port()
    async with playwright_mod.async_playwright() as p:
        try:
            browser = await p.chromium.launch(args=[f"--remote-debugging-port={port}"])
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium here: {why}")
        try:
            yield f"http://localhost:{port}"
        finally:
            await browser.close()


@pytest.fixture
async def cdp_url() -> AsyncIterator[str]:
    async for url in _chromium():
        yield url


@pytest.fixture
async def cdp_url_2() -> AsyncIterator[str]:
    async for url in _chromium():
        yield url


@asynccontextmanager
async def _browser_session(cdp_url: str) -> AsyncIterator[CDPSession]:
    async with httpx.AsyncClient() as client:
        endpoint = await websocket_debugger_url(cdp_url, client)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(endpoint)
        try:
            yield await browser.new_browser_cdp_session()
        finally:
            await browser.close()


async def open_account(cdp_url: str) -> SessionRef:
    """A real browser context, made the way S4's `SteelClient._new_context`
    makes one, so every test drives the production path."""
    async with _browser_session(cdp_url) as raw:
        made = await raw.send("Target.createBrowserContext", {"disposeOnDetach": False})
    return SessionRef(str(made["browserContextId"]), cdp_url)


async def close_account(session: SessionRef) -> None:
    async with _browser_session(session.cdp_url) as raw:
        known = (await raw.send("Target.getBrowserContexts"))["browserContextIds"]
        if session.context_id in known:
            await raw.send("Target.disposeBrowserContext", {"browserContextId": session.context_id})


async def pages_in(session: SessionRef) -> list[str]:
    async with _browser_session(session.cdp_url) as raw:
        found = (await raw.send("Target.getTargets"))["targetInfos"]
    return [
        str(one["targetId"])
        for one in found
        if one.get("type") == "page" and one.get("browserContextId") == session.context_id
    ]


async def _account(cdp_url: str) -> AsyncIterator[SessionRef]:
    session = await open_account(cdp_url)
    try:
        yield session
    finally:
        await close_account(session)


@pytest.fixture
async def one(cdp_url: str) -> AsyncIterator[SessionRef]:
    async for session in _account(cdp_url):
        yield session


@pytest.fixture
async def two(cdp_url: str) -> AsyncIterator[SessionRef]:
    async for session in _account(cdp_url):
        yield session


@pytest.fixture
async def elsewhere(cdp_url_2: str) -> AsyncIterator[SessionRef]:
    async for session in _account(cdp_url_2):
        yield session


@pytest.fixture
async def driver() -> AsyncIterator[SteelDriver]:
    made = SteelDriver(get_settings().page_code_path)
    try:
        yield made
    finally:
        await made.aclose()
