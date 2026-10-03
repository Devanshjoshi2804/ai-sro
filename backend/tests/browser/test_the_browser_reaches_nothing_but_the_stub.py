"""No browser test may reach a real deployment.

The extension's default API URL is the QA box. Every extension test used to
send it two requests there before the stub's URL was set -- real 401s from a
real backend, one of which signed an operator out. Two rules hold that shut:
a browser with no credential calls nobody, and Chrome is launched with a proxy
that refuses everything not on loopback.
"""

from __future__ import annotations

import contextlib
import re
import socket
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from tests.browser.conftest import EXTENSION, chrome_args

pytestmark = pytest.mark.browser

# Where the extension goes when nobody has told it otherwise, read from the
# build rather than written down: `make gen-deployment` changes it.
_DEFAULT = re.search(
    r'DEFAULT_API_URL = "([^"]+)"',
    (EXTENSION / "src" / "background" / "deployment.generated.js").read_text(),
)
assert _DEFAULT
QA_BOX = _DEFAULT[1]
QA_HOST = urlsplit(QA_BOX).netloc


@pytest.fixture
def seen() -> Iterator[tuple[str, list[str]]]:
    """A proxy that logs the first line of each request it is asked for."""
    lines: list[str] = []
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()

    def serve() -> None:
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(2)
                with contextlib.suppress(OSError):
                    lines.append(conn.recv(4096).split(b"\r\n")[0].decode(errors="replace"))

    threading.Thread(target=serve, daemon=True).start()
    yield f"http://127.0.0.1:{server.getsockname()[1]}", lines
    server.close()


def test_a_sign_in_flow_makes_no_request_off_loopback(
    stub: tuple[str, list[dict[str, Any]]], tmp_path: Path, seen: tuple[str, list[str]]
) -> None:
    proxy, lines = seen
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(tmp_path / "profile"),
            headless=True,
            channel="chromium",
            args=chrome_args(proxy),
        )
        try:
            worker = (
                context.service_workers[0]
                if context.service_workers
                else context.wait_for_event("serviceworker")
            )
            page = context.new_page()
            page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
            page.evaluate(
                """async (apiUrl) => await chrome.runtime.sendMessage(
                     {kind: "sign-in", apiUrl, consoleUrl: "", token: "t.t.t", label: "guard"})""",
                stub[0],
            )
            page.wait_for_timeout(1500)
            # Chrome's own background traffic (time, sign-in checks) also lands
            # on this proxy; what is asserted is that the extension's default
            # deployment is not among it.
            assert [line for line in lines if QA_HOST in line] == [], lines

            # The control: this proxy does see an off-loopback request, so the
            # empty list above means something.
            page.evaluate(f"fetch('{QA_BOX}/x', {{mode: 'no-cors'}}).catch(() => null)")
            page.wait_for_timeout(1000)
            assert any(QA_HOST in line for line in lines), "the logging proxy sees nothing"
        finally:
            context.close()


def test_the_default_launch_fails_closed(
    stub: tuple[str, list[dict[str, Any]]], browser: Any
) -> None:
    page = browser.new_page()
    refused = page.evaluate(
        f"fetch('{QA_BOX}/x', {{signal: AbortSignal.timeout(3000)}}).then(() => false, () => true)"
    )
    assert refused, "a browser test reached a non-loopback host"
