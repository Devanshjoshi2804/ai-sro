"""The stored-credential sign-in, driven through a login that hops before it asks.

A real identity provider rarely serves its form at the address a system sends
you to. It passes the browser along: a portal that bounces to a chooser, a
chooser that posts itself on to the provider, a provider that posts the result
back. Each hop is a document that exists for a moment and is replaced. Measured
on 2026-09-23 against a real chain of that shape, the driver crashed with
"Execution context was destroyed" because it probed a page that was mid-flight,
and it treated a page with nothing to fill as the end of the login.

The chain here is local and deliberately generic: two hosts (the system on
127.0.0.1, the "provider" on localhost), two self-submitting hops, then an
ordinary form. Nothing about any vendor's markup.
"""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import AsyncIterator, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from sro.application.ports.sign_in import SignInFailed
from sro.infrastructure.steel.sign_in import PlaywrightSignIn

pytestmark = pytest.mark.browser

STORM_S = 10.0
"""How long the first hop keeps handing the browser to itself.

The measured chain took about 50 s and its pages never went network-idle, so
the driver's eight-second wait for quiet always ran out and it probed a page in
flight. A hop that re-posts itself for longer than that wait reproduces the
same condition locally, and a driver that stops at the first page with nothing
to fill fails here the way it failed there.
"""

LINKS = "".join(f'<a href="#x{i}">option {i}</a> ' for i in range(300))


def _hop(to: str, after_ms: int) -> str:
    """A document that hands the browser on, the way identity providers do.

    A hidden form posting itself, a moment after load, with a page full of
    links so a probe of it takes long enough to be caught by the hand-over.
    """
    return f"""<!doctype html><html><body>
      <p>One moment...</p>{LINKS}
      <form id="on" method="post" action="{to}"><input type="hidden" name="s" value="1"></form>
      <script>setTimeout(() => document.getElementById("on").submit(), {after_ms});</script>
    </body></html>"""


FORM = """<!doctype html><html><body>
  <form method="get" action="{app}">
    <input id="username" name="username" type="text">
    <input id="password" name="password" type="password">
    <button type="submit">Sign in</button>
  </form>
</body></html>"""


def _server(arrived: list[dict[str, str]]) -> tuple[ThreadingHTTPServer, int]:
    started: dict[str, float] = {}

    class Chain(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return

        def _page(self, body: str) -> None:
            raw = body.encode()
            self.send_response(200)
            self.send_header("content-type", "text/html")
            self.send_header("content-length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _serve(self) -> None:
            port = self.server.server_address[1]
            system, provider = f"http://127.0.0.1:{port}", f"http://localhost:{port}"
            path = urlsplit(self.path).path
            if path == "/":
                self.send_response(302)
                self.send_header("location", f"{provider}/hop-1")
                self.end_headers()
            elif path == "/hop-1":
                started.setdefault("at", time.monotonic())
                time.sleep(0.05)
                storming = time.monotonic() - started["at"] < STORM_S
                self._page(_hop(f"{provider}/hop-1" if storming else f"{provider}/hop-2", 50))
            elif path == "/hop-2":
                self._page(_hop(f"{provider}/login", 150))
            elif path == "/login":
                self._page(FORM.format(app=f"{system}/app"))
            elif path == "/lost":
                self.send_response(302)
                self.send_header("location", f"{provider}/nowhere")
                self.end_headers()
            elif path == "/nowhere":
                self._page(
                    "<!doctype html><html><body><p>Access denied for this account.</p>"
                    f"{LINKS}</body></html>"
                )
            elif path == "/refuses":
                self.send_response(302)
                self.send_header("location", f"{provider}/refusing-form")
                self.end_headers()
            elif path == "/refusing-form":
                query = parse_qs(urlsplit(self.path).query)
                if query:
                    arrived.append({k: v[0] for k, v in query.items()})
                said = "<p>Invalid username or password.</p>" if query else ""
                self._page(said + FORM.format(app=f"{provider}/refusing-form"))
            elif path == "/app":
                query = parse_qs(urlsplit(self.path).query)
                arrived.append({k: v[0] for k, v in query.items()})
                self._page("<!doctype html><html><body><h1>Depot</h1></body></html>")
            else:
                self.send_response(404)
                self.end_headers()

        def do_GET(self) -> None:
            self._serve()

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("content-length") or 0))
            self._serve()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Chain)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def chain() -> Iterator[tuple[int, list[dict[str, str]]]]:
    arrived: list[dict[str, str]] = []
    server, port = _server(arrived)
    try:
        yield port, arrived
    finally:
        server.shutdown()


@pytest.fixture
async def debugger_url() -> AsyncIterator[str]:
    """A Chromium the driver can attach to over CDP, as it does to Steel."""
    playwright = pytest.importorskip("playwright.async_api")
    port = _free_port()
    async with playwright.async_playwright() as p:
        try:
            browser = await p.chromium.launch(args=[f"--remote-debugging-port={port}"])
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium here: {why}")
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            await browser.close()


async def test_a_login_that_hops_twice_before_its_form_still_signs_in(
    chain: tuple[int, list[dict[str, str]]], debugger_url: str
) -> None:
    port, arrived = chain

    result = await PlaywrightSignIn().sign_in(
        debugger_url=debugger_url,
        url=f"http://127.0.0.1:{port}/",
        username="operator",
        password="not-a-real-secret",  # noqa: S106 -- a local test page's field
        timeout_s=45.0,
    )

    assert urlsplit(result.landed_at).path == "/app"
    assert arrived == [{"username": "operator", "password": "not-a-real-secret"}]


async def test_a_page_that_goes_nowhere_fails_soon_and_says_what_it_showed(
    chain: tuple[int, list[dict[str, str]]], debugger_url: str
) -> None:
    """A hand-over moves; a dead end does not.

    A page off the system's host with nothing to fill and nothing to press is
    waited on, because it is usually a hop in flight. One that stays the same
    document probe after probe is an answer -- a locked account, an access
    denied -- and the operator needs to read it, well before the timeout.
    """
    port, arrived = chain
    started = time.monotonic()

    with pytest.raises(SignInFailed, match="Access denied for this account"):
        await PlaywrightSignIn().sign_in(
            debugger_url=debugger_url,
            url=f"http://127.0.0.1:{port}/lost",
            username="operator",
            password="not-a-real-secret",  # noqa: S106 -- a local test page's field
            timeout_s=60.0,
        )

    assert time.monotonic() - started < 25.0
    assert arrived == []


async def test_refused_credentials_are_submitted_once_and_never_again(
    chain: tuple[int, list[dict[str, str]]], debugger_url: str
) -> None:
    """Retyping a password the system just refused is how an account gets locked."""
    port, arrived = chain

    with pytest.raises(SignInFailed, match="refused") as failed:
        await PlaywrightSignIn().sign_in(
            debugger_url=debugger_url,
            url=f"http://127.0.0.1:{port}/refuses",
            username="operator",
            password="not-a-real-secret",  # noqa: S106 -- a local test page's field
            timeout_s=60.0,
        )

    assert len(arrived) == 1
    assert "Invalid username or password" in str(failed.value)
    assert "not-a-real-secret" not in str(failed.value)
