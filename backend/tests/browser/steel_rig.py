from __future__ import annotations

import asyncio
import contextlib
import json
import os
import secrets
import socket
import threading
from collections.abc import AsyncIterator, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.page import SessionRef
from sro.infrastructure.steel.driver import SteelDriver

_PUBLIC_PAGE = "<!doctype html><html><body><h1>public</h1></body></html>"

_APP_PAGE = """<!doctype html><html><head><meta name="csrf-token" content="{token}"></head><body>
  <form aria-label="Customer Type">
    <label for="ct">Customer Type</label><input id="ct" name="customerType">
    <button id="save" type="button">Save</button>
  </form>
  <script>
    document.getElementById("save").addEventListener("click", async () => {{
      const token = document.querySelector("meta[name=csrf-token]").content;
      const name = document.getElementById("ct").value;
      await fetch("/api/customer-types", {{
        method: "POST",
        headers: {{"X-CSRF-Token": token, "content-type": "application/json"}},
        body: JSON.stringify({{name}}),
      }});
    }});
  </script>
</body></html>"""

_LOGIN_PAGE = """<!doctype html><html><body>
  <form method="post" action="/idp/login?state={state}">
    <input id="username" name="username">
    <input id="password" name="password" type="password">
    <button id="go" type="submit">Sign in</button>
  </form>
</body></html>"""

_SIGN_IN_TIMEOUT_S = 10.0


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
    task's live rig exercises."""

    def __init__(self, *, for_steel: bool = False) -> None:
        self._for_steel = for_steel
        self._sessions: dict[str, str] = {}
        self._codes: dict[str, tuple[str, str]] = {}
        self._csrf: dict[str, str] = {}
        self.saved: list[dict[str, object]] = []
        host = "0.0.0.0" if for_steel else "127.0.0.1"  # noqa: S104
        self._port = _free_port()
        self._server = ThreadingHTTPServer((host, self._port), _handler_for(self))
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def url(self, path: str) -> str:
        host = (
            os.environ.get("SRO_STEEL_SEES_HOST", "host.docker.internal")
            if self._for_steel
            else "127.0.0.1"
        )
        return f"http://{host}:{self._port}{path}"

    def expire(self) -> None:
        self._sessions.clear()
        self._csrf.clear()

    def close(self) -> None:
        self._server.shutdown()

    async def sign_in_in(self, driver: SteelDriver, session: SessionRef, target_id: str) -> None:
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
            if (await driver.url_of(session, target_id)).endswith("/app"):
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
            path, query = split.path, parse_qs(split.query)
            sid = self._cookie()

            if path == "/public":
                self._html(_PUBLIC_PAGE)
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
                    }
                )
                self._redirect(rig.url(f"/idp/authorize?{params}"))
            elif path == "/idp/authorize":
                self._html(_LOGIN_PAGE.format(state=query.get("state", [""])[0]))
            elif path == "/cb":
                code, state = query.get("code", [""])[0], query.get("state", [""])[0]
                found = rig._codes.pop(code, None)
                if found is None or found[0] != state:
                    self.send_response(401)
                    self.end_headers()
                    return
                new_sid = secrets.token_hex(16)
                rig._sessions[new_sid] = found[1]
                rig._csrf[new_sid] = secrets.token_hex(16)
                self._redirect(rig.url("/app"), cookie=f"sid={new_sid}; Path=/")
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
                self._json(rig.saved)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:
            split = urlsplit(self.path)
            path, query = split.path, parse_qs(split.query)
            body = self.rfile.read(int(self.headers.get("content-length") or 0))

            if path == "/idp/login":
                form = parse_qs(body.decode())
                username = form.get("username", [""])[0]
                state = query.get("state", [""])[0]
                code = secrets.token_hex(8)
                rig._codes[code] = (state, username)
                params = urlencode({"code": code, "state": state})
                self._redirect(rig.url(f"/cb?{params}"))
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
