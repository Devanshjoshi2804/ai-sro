"""`page-code.js`'s strategy ladder, proved to choose the same element in two
different engines: real Chrome, through the extension's own
`chrome.scripting.executeScript({files})` injection, and plain Playwright,
through `add_init_script(path=...)` -- spec §8.2's parity suite.

Two engines because they are the two ways this file is ever run: the
extension in an operator's own browser, Steel through Playwright for a
durable run. Nothing else in this repository loads `page-code.js` both ways
at once, so a change that reads correctly against one and silently differs
against the other is invisible to every other test here.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, ClassVar

import pytest

from sro.config import get_settings

pytestmark = pytest.mark.browser

GRID_PAGE = """<!doctype html><html><body>
<input id="client" name="clientCode">
<script>
  window.Ext = {
    ComponentQuery: {
      query: (q) => (q === 'panel#clients textfield#clientCode'
        ? [{isVisible: () => true, inputEl: {dom: document.getElementById('client')}}]
        : []),
    },
    getCmp: (id) => (id === 'client'
      ? {xtype: 'textfield', itemId: 'clientCode', ownerCt: {xtype: 'panel', itemId: 'clients'}}
      : null),
  };
</script>
</body></html>"""

IFRAME_TOP_PAGE = """<!doctype html><html><body>
<iframe id="inner" src="/iframe-inner"></iframe>
</body></html>"""

IFRAME_INNER_PAGE = """<!doctype html><html><body>
<button aria-label="Save">go</button>
</body></html>"""

STALE_PAGE = """<!doctype html><html><body>
<input id="ext-gen4821" name="clientCode">
</body></html>"""

DUPLICATE_PAGE = """<!doctype html><html><body>
<button style="position:absolute;left:10px;top:10px;width:60px;height:20px">Save</button>
<button style="position:absolute;left:400px;top:10px;width:60px;height:20px">Save</button>
</body></html>"""


class _Pages(BaseHTTPRequestHandler):
    """No backend, no registration, no extension protocol -- these pages
    exist only to be resolved against, in a real tab. Not `conftest.py`'s
    `_Stub`: everything that class answers is unused here, and inheriting it
    would make a passing test prove less than it looks like it does."""

    protocol_version = "HTTP/1.1"

    ROUTES: ClassVar[dict[str, str]] = {
        "/grid": GRID_PAGE,
        "/iframe-top": IFRAME_TOP_PAGE,
        "/iframe-inner": IFRAME_INNER_PAGE,
        "/stale": STALE_PAGE,
        "/duplicate": DUPLICATE_PAGE,
    }

    def do_GET(self) -> None:
        body = self.ROUTES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        encoded = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def pages() -> Any:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Pages)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _service_worker(context: Any) -> Any:
    return (
        context.service_workers[0]
        if context.service_workers
        else context.wait_for_event("serviceworker")
    )


def _tab_id(worker: Any, url: str) -> int:
    tabs = worker.evaluate("async (url) => await chrome.tabs.query({url})", url)
    assert tabs, f"no tab open on {url}"
    return tabs[0]["id"]


def _frame_id(worker: Any, tab_id: int, url_suffix: str) -> int:
    frames = worker.evaluate(
        "async (tabId) => await chrome.webNavigation.getAllFrames({tabId})", tab_id
    )
    found = next((f for f in frames if url_suffix in f["url"]), None)
    assert found is not None, f"no frame ending in {url_suffix}: {frames}"
    return found["frameId"]


def _resolve_in_extension(
    worker: Any, tab_id: int, frame_id: int, payload: dict[str, Any]
) -> dict[str, Any]:
    """The extension's own path: inject the file, then dispatch by name --
    the same two calls `sroCall` in `commands.js` makes."""
    worker.evaluate(
        """async ([tabId, frameId]) => {
            await chrome.scripting.executeScript({
                target: {tabId, frameIds: [frameId]},
                world: "MAIN",
                files: ["src/page/page-code.js"],
            });
        }""",
        [tab_id, frame_id],
    )
    answer: dict[str, Any] = worker.evaluate(
        """async ([tabId, frameId, payload]) => {
            const [{result}] = await chrome.scripting.executeScript({
                target: {tabId, frameIds: [frameId]},
                world: "MAIN",
                func: (p) => globalThis.sroPage.resolve(p),
                args: [payload],
            });
            return result;
        }""",
        [tab_id, frame_id, payload],
    )
    return answer


def _resolve_in_plain_chromium(
    url: str, payload: dict[str, Any], frame_url_suffix: str | None = None
) -> dict[str, Any]:
    """The other loader `page-code.js` has to agree with: `add_init_script`
    is how Steel's own `PlaywrightUiDriver` reads a page, with no extension
    anywhere in the picture.

    Run on its own thread, not the main one: `browser` (conftest.py) already
    holds a `sync_playwright()` connection open on the main thread for the
    life of the test, and the sync API refuses a second one on the same
    thread -- it drives its own event loop and `asyncio_mode = "auto"`'s
    already-running one is one too many, whether or not this call happens
    from an `async def` test. A second OS thread has its own asyncio state
    to refuse a second loop on, which is exactly the isolation this needs
    and nothing more elaborate does.
    """
    from playwright.sync_api import sync_playwright

    answer: dict[str, Any] = {}
    failure: list[BaseException] = []

    def run() -> None:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                try:
                    context = browser.new_context()
                    context.add_init_script(path=get_settings().page_code_path)
                    page = context.new_page()
                    page.goto(url)
                    frame = (
                        next(f for f in page.frames if f.url.endswith(frame_url_suffix))
                        if frame_url_suffix
                        else page.main_frame
                    )
                    answer.update(frame.evaluate("p => globalThis.sroPage.resolve(p)", payload))
                finally:
                    browser.close()
        except BaseException as exc:
            failure.append(exc)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    if failure:
        raise failure[0]
    return answer


def _same_answer(extension: dict[str, Any], playwright: dict[str, Any]) -> None:
    got = (extension["strategy"], extension["candidates"], extension["xpath"])
    wanted = (playwright["strategy"], playwright["candidates"], playwright["xpath"])
    assert got == wanted, f"extension answered {extension}, playwright answered {playwright}"


def test_an_extjs_component_chain_resolves_the_same_control_in_both_engines(
    browser: Any, pages: Any
) -> None:
    port = pages.server_address[1]
    url = f"http://127.0.0.1:{port}/grid"
    payload = {"target": {"component": {"chain": ["panel#clients", "textfield#clientCode"]}}}

    worker = _service_worker(browser)
    page = browser.new_page()
    page.goto(url)
    extension_found = _resolve_in_extension(worker, _tab_id(worker, url), 0, payload)
    page.close()

    playwright_found = _resolve_in_plain_chromium(url, payload)

    assert extension_found["found"] is True, extension_found
    assert extension_found["strategy"] == "component_chain"
    _same_answer(extension_found, playwright_found)


def test_a_control_inside_an_iframe_resolves_the_same_control_in_both_engines(
    browser: Any, pages: Any
) -> None:
    port = pages.server_address[1]
    url = f"http://127.0.0.1:{port}/iframe-top"
    payload = {"target": {"role": "button", "name": "Save"}}

    worker = _service_worker(browser)
    page = browser.new_page()
    page.goto(url)
    page.wait_for_selector("iframe")
    tab_id = _tab_id(worker, url)
    frame_id = _frame_id(worker, tab_id, "/iframe-inner")
    extension_found = _resolve_in_extension(worker, tab_id, frame_id, payload)
    page.close()

    playwright_found = _resolve_in_plain_chromium(url, payload, frame_url_suffix="/iframe-inner")

    assert extension_found["found"] is True, extension_found
    assert extension_found["strategy"] == "within_role_name"
    _same_answer(extension_found, playwright_found)


def test_stale_ids_since_the_recording_still_resolve_by_a_surviving_attribute_in_both_engines(
    browser: Any, pages: Any
) -> None:
    port = pages.server_address[1]
    url = f"http://127.0.0.1:{port}/stale"
    payload = {
        "target": {
            "tag": "input",
            "attributes": {"name": "clientCode"},
            "css_path": "#stale-recorded-id-999",
        },
    }

    worker = _service_worker(browser)
    page = browser.new_page()
    page.goto(url)
    extension_found = _resolve_in_extension(worker, _tab_id(worker, url), 0, payload)
    page.close()

    playwright_found = _resolve_in_plain_chromium(url, payload)

    assert extension_found["found"] is True, extension_found
    assert extension_found["strategy"] == "attributes"
    _same_answer(extension_found, playwright_found)


def test_two_matching_controls_are_told_apart_by_bounds_in_both_engines(
    browser: Any, pages: Any
) -> None:
    port = pages.server_address[1]
    url = f"http://127.0.0.1:{port}/duplicate"
    payload = {
        "target": {
            "role": "button",
            "name": "Save",
            "bounds": {"x": 395, "y": 12, "width": 60, "height": 20},
        },
    }

    worker = _service_worker(browser)
    page = browser.new_page()
    page.goto(url)
    extension_found = _resolve_in_extension(worker, _tab_id(worker, url), 0, payload)
    page.close()

    playwright_found = _resolve_in_plain_chromium(url, payload)

    assert extension_found["found"] is True, extension_found
    assert extension_found["strategy"] == "within_role_name"
    assert extension_found["candidates"] == 2
    _same_answer(extension_found, playwright_found)
