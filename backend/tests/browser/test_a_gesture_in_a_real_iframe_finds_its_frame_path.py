"""The recorder's `framePathOf`, in a real Chrome rather than a mocked `window`.

`evidence.test.mjs` proves the arithmetic against a plain JS object standing in
for `window` -- it cannot prove that a real cross-origin `WindowProxy` actually
throws on `.location.href` the way the code assumes, that `parent.frames[i]
=== here` still holds across an origin boundary, or that `ancestorOrigins`
carries what the fallback reads. X4's `SteelDriver._frame` depends on all
three being true in a real browser, not merely in a JS object shaped like one.

Two origins sharing one server and port, the same trick
`test_a_sign_in_through_a_redirect_chain.py` uses: `127.0.0.1` and `localhost`
both reach this process's one listening socket, so no second server is needed
for a real cross-origin boundary. The default stub policy excludes
`localhost` (deliberately, for a different test's reason), so this file's
registration reply excludes nothing -- otherwise the cross-origin gesture
below would be captured by nobody and prove nothing.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from http.server import ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

import pytest

from tests.browser.conftest import DEVICE_SECRET, _Stub

pytestmark = pytest.mark.browser

TOP_PAGE = """<!doctype html><html><body><h1>Top</h1>
<iframe id="shell" src="/shell"></iframe>
</body></html>"""

SHELL_PAGE = """<!doctype html><html><body><h1>Shell</h1>
<iframe id="leafSame" src="/leaf-same"></iframe>
<iframe id="leafCross" src="{cross}/leaf-cross"></iframe>
</body></html>"""

LEAF_PAGE = """<!doctype html><html><body><button id="go">Go</button></body></html>"""


class _Frames(_Stub):
    """The stub, plus the nested-frame page this file needs and a policy that
    excludes neither origin -- the base registration reply excludes
    `localhost` for `test_the_extension_in_a_real_chrome.py`'s reason, which
    would silently drop the cross-origin gesture this test exists to check.
    """

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        if self.path == "/":
            return self._send(200, TOP_PAGE.encode(), "text/html; charset=utf-8")
        if self.path == "/shell":
            port = self.server.server_address[1]
            page = SHELL_PAGE.format(cross=f"http://localhost:{port}")
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        if self.path in ("/leaf-same", "/leaf-cross"):
            return self._send(200, LEAF_PAGE.encode(), "text/html; charset=utf-8")
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        if urlsplit(self.path).path == "/v1/agents/register":
            self._send(
                200,
                json.dumps(
                    {
                        "device_id": "dev_browsertest",
                        "device_secret": DEVICE_SECRET,
                        "policy_version": 1,
                        "policy": {
                            "version": 1,
                            "capture_enabled": True,
                            "exclude_hosts": [],
                            "include_hosts": [],
                            "capture_screenshots": False,
                            "screenshot_max_per_minute": 3,
                            "capture_response_bodies": True,
                            "max_body_bytes": 262144,
                            "daily_budget_bytes": 524288000,
                            "retention_days": 30,
                        },
                    }
                ).encode(),
            )
            return
        super().do_POST()


def _service_worker(context: Any) -> Any:
    return (
        context.service_workers[0]
        if context.service_workers
        else context.wait_for_event("serviceworker")
    )


def _options(context: Any, worker: Any) -> Any:
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    return page


def _sign_in(context: Any, worker: Any, api_url: str) -> dict[str, Any]:
    page = _options(context, worker)
    status: dict[str, Any] = page.evaluate(
        """async ([apiUrl]) => await chrome.runtime.sendMessage(
             {kind: "sign-in", apiUrl, token: "test.token.here", label: "browser-test"})""",
        [api_url],
    )
    page.close()
    return status


def _watch(context: Any, worker: Any, page: Any) -> None:
    page.bring_to_front()
    tab_id = worker.evaluate(
        "async () => (await chrome.tabs.query({active: true, lastFocusedWindow: true}))[0]?.id"
    )
    assert tab_id is not None, "no active tab to watch"
    asking = _options(context, worker)
    answer: dict[str, Any] = asking.evaluate(
        """async (tabId) => await chrome.runtime.sendMessage({kind: "watch-tab", tabId})""",
        tab_id,
    )
    asking.close()
    assert "error" not in answer, f"could not watch that tab: {answer}"


def _flush(context: Any, worker: Any) -> None:
    page = _options(context, worker)
    page.evaluate("""async () => await chrome.runtime.sendMessage({kind: "flush"})""")
    page.close()


def _flush_until_two_clicks_arrive(
    context: Any,
    worker: Any,
    batches: list[dict[str, Any]],
    deadline_seconds: float = 8.0,
) -> list[dict[str, Any]]:
    """Same shape as `capture_fixtures.py`'s fix: flush, check what actually
    arrived, and only sleep between attempts."""
    until = time.monotonic() + deadline_seconds
    while True:
        _flush(context, worker)
        events = [event for batch in batches for event in batch["events"]]
        clicks = [
            e for e in events if e.get("kind") == "gesture" and e["gesture"]["kind"] == "click"
        ]
        if len(clicks) >= 2:
            return events
        if time.monotonic() >= until:
            return events
        time.sleep(0.25)


@pytest.fixture
def frames() -> Any:
    _Stub.batches = []
    _Stub.channels = queue.Queue()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Frames)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def test_a_gesture_in_a_real_iframe_finds_its_frame_path(browser: Any, frames: Any) -> None:
    port = frames.server_address[1]
    system = f"http://127.0.0.1:{port}"
    cross = f"http://localhost:{port}"

    worker = _service_worker(browser)
    status = _sign_in(browser, worker, system)
    assert status["capturing"] is True, f"the extension did not start capturing: {status}"

    page = browser.new_page()
    page.goto(system)
    same_go = page.frame_locator("#shell").frame_locator("#leafSame").locator("#go")
    cross_go = page.frame_locator("#shell").frame_locator("#leafCross").locator("#go")
    same_go.wait_for(state="visible")
    cross_go.wait_for(state="visible")

    _watch(browser, worker, page)

    same_go.click()
    cross_go.click()

    events = _flush_until_two_clicks_arrive(browser, worker, _Stub.batches)
    page.close()

    clicks = [e for e in events if e.get("kind") == "gesture" and e["gesture"]["kind"] == "click"]
    assert len(clicks) == 2, f"expected one click from each frame, got {len(clicks)}: {clicks}"

    by_url = {c["gesture"]["url"]: c["gesture"] for c in clicks}
    same = by_url[f"{system}/leaf-same"]
    cross_ = by_url[f"{cross}/leaf-cross"]

    # The same-origin leaf: both hops are real, directly-read URLs -- a
    # `WindowProxy` for a same-origin ancestor never throws on `.location.href`.
    assert same["frame_path"] == [
        {"index": 0, "url": f"{system}/shell"},
        {"index": 0, "url": f"{system}/leaf-same"},
    ]

    # The cross-origin leaf: its own hop is a direct read (a frame can always
    # read its own location), but reading its cross-origin parent's `.href`
    # from its own realm throws a real `SecurityError` -- proving that
    # requires a real WindowProxy, which is exactly what a mocked `window`
    # cannot produce -- so that hop falls back to `ancestorOrigins`, an
    # origin rather than a full URL.
    assert cross_["frame_path"] == [
        {"index": 0, "url": system},
        {"index": 1, "url": f"{cross}/leaf-cross"},
    ]
