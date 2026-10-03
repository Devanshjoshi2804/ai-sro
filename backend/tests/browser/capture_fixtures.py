"""Regenerate the golden payloads in `new-chrome-extension/fixtures/`.

    make fixtures

Captured, never written by hand. A hand-written fixture proves the fixture; the
whole point of these is that `tests/contract/test_observation_payloads.py` reads
bytes the extension actually produced and asserts they parse into the domain, so
a change on either side of the frozen contract fails both people's `make check`.

Not a test. It writes files, it needs a browser, and it is run deliberately when
the shapes change -- the contract test is what runs every time.
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from tests.browser.conftest import EXTENSION, _Stub

FIXTURES = EXTENSION / "fixtures"

CLIENT_CODE = "ACME-4471"
PASSWORD = "hunter2-do-not-store"  # noqa: S105

PAGE = """<!doctype html>
<html><body>
  <h1>Depot</h1>
  <form id="f">
    <label for="client">Client Code</label>
    <input id="client" name="clientCode" type="text">
    <label for="pw">Password</label>
    <input id="pw" name="password" type="password">
    <label for="dock">Dock</label>
    <select id="dock" name="dock">
      <option value="">choose</option>
      <option value="D3">Dock 3</option>
    </select>
    <label for="manifest">Manifest</label>
    <input id="manifest" name="manifest" type="file">
    <button id="save" type="button">Save</button>
  </form>
  <script>
    window.Ext = {
      ComponentQuery: {
        query: (q) => {
          const dom = document.getElementById(({
            'panel#clients textfield#clientCode': 'client',
            'panel#clients button#saveButton': 'save',
          })[q] || '');
          return dom ? [{isVisible: () => true, el: {dom}, inputEl: {dom}}] : [];
        },
      },
      getCmp: (id) => ({
        'client': {xtype: 'textfield', itemId: 'clientCode', name: 'clientCode',
                   fieldLabel: 'Client Code', ownerCt: {xtype: 'panel', itemId: 'clients'}},
        'save': {xtype: 'button', itemId: 'saveButton', text: 'Save',
                 ownerCt: {xtype: 'panel', itemId: 'clients'}},
      })[id] || null,
    };
    window.__calls = (async () => {
      // One of each, because each is a fixture: a read, a write with bodies on
      // both sides, and one that never completes.
      await fetch('/api/orders?facility=DC1');
      await fetch('/api/orders', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({clientCode: 'ACME-4471', dock: 'D3'}),
      });
      try { await fetch('http://127.0.0.1:1/never'); } catch (e) { /* the point */ }
      // The other transport, with a body each way.
      await new Promise((done) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/legacy');
        xhr.setRequestHeader('content-type', 'application/x-www-form-urlencoded');
        xhr.addEventListener('loadend', done);
        xhr.send('clientCode=ACME-4471&dock=D3');
      });
      // A body that is a conversation rather than a document: reading it to the
      // end is a wait that never returns, so it is deliberately not read.
      await fetch('/api/stream');
      window.__done = true;
    });
    document.getElementById('save').addEventListener('click', () => window.__calls());
  </script>
</body></html>
"""


class _Fixtures(_Stub):
    """The browser-test stub, serving a page with one of everything on it."""

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        if self.path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b"data: tick\n\n")
            self.wfile.flush()
            return None
        if self.path.startswith("/api/"):
            return self._send(200, json.dumps({"orders": [{"id": "ORD-1"}]}).encode())
        return self._send(200, PAGE.encode(), "text/html; charset=utf-8")


def _worker(context: Any) -> Any:
    return (
        context.service_workers[0]
        if context.service_workers
        else context.wait_for_event("serviceworker")
    )


def _options(context: Any, worker: Any) -> Any:
    page = context.new_page()
    page.goto(f"{worker.url.rsplit('/src/', 1)[0]}/src/options/options.html")
    return page


def _write(name: str, payload: object, into: Path = FIXTURES) -> None:
    path = into / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        print(f"  {path.relative_to(EXTENSION.parent)}")  # noqa: T201
    except ValueError:
        print(f"  {path}")  # noqa: T201


def _one(
    events: list[dict[str, Any]], of_kind: str, matching: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """The first event of a kind whose inner payload matches. `matching` is a
    dict rather than keyword arguments because `kind` is a field name inside a
    gesture as well as the name of the envelope's own field."""
    for event in events:
        if event.get("kind") != of_kind:
            continue
        inner = event.get(of_kind, event)
        if all(inner.get(key) == value for key, value in (matching or {}).items()):
            return event
    return None


def _wanted(events: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    """Every fixture `main` writes, named, or `None` for the ones not seen yet.

    The one place both `_capture`'s own completion check and `main`'s write
    step name what a full capture looks like -- so the two cannot drift into
    disagreeing about what "everything arrived" means.
    """
    found: dict[str, dict[str, Any] | None] = {
        "gesture-click": _one(events, "gesture", {"kind": "click"}),
        "gesture-type": _one(events, "gesture", {"kind": "type", "secret": False}),
        "gesture-select": _one(events, "gesture", {"kind": "select"}),
        "gesture-press": _one(events, "gesture", {"kind": "press"}),
        "gesture-upload": _one(events, "gesture", {"kind": "upload"}),
        "gesture-secret": _one(events, "gesture", {"secret": True}),
        "page-navigated": _one(events, "page", {"page_kind": "navigated"}),
    }
    requests = [event for event in events if event["kind"] == "request"]
    found["request-get"] = next(
        (r for r in requests if r["request"]["method"] == "GET" and r["request"].get("status")),
        None,
    )
    found["request-post"] = next(
        (
            r
            for r in requests
            if r["request"]["method"] == "POST" and r["request"].get("request_body")
        ),
        None,
    )
    found["request-failed"] = next(
        (r for r in requests if r["request"].get("failure_reason")), None
    )
    found["request-with-body"] = next(
        (
            r
            for r in requests
            if r["request"]["resource_type"] == "xhr" and r["request"].get("request_body")
        ),
        None,
    )
    # A response nothing read: an event stream stays open for the life of the
    # page, so there is no "the body" to wait for.
    found["request-uninspectable-body"] = next(
        (
            r
            for r in requests
            if (r["request"].get("response_body") or {}).get("text") is None
            and r["request"].get("status")
        ),
        None,
    )
    return found


def _capture(context: Any, api_url: str, batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Do a task the way an operator would, and hand back what was uploaded."""
    worker = _worker(context)
    signing_in = _options(context, worker)
    status = signing_in.evaluate(
        """async ([apiUrl]) => await chrome.runtime.sendMessage(
             {kind: "sign-in", apiUrl, token: "fixture-token", label: "fixtures"})""",
        [api_url],
    )
    signing_in.close()
    if not status["capturing"]:
        raise SystemExit(f"the extension did not start capturing: {status}")

    page = context.new_page()
    page.goto(api_url)
    # The operator's own answer to "which tab is the work in". Nothing is
    # captured from a tab nobody pointed at, so a fixture run has to say it too.
    watching = _options(context, worker)
    watching.evaluate(
        """async (wanted) => {
             const tabs = await chrome.tabs.query({});
             const tab = tabs.find((each) => (each.url || "").startsWith(wanted));
             return await chrome.runtime.sendMessage(
               {kind: "watch-tab", tabId: tab.id, url: tab.url},
             );
           }""",
        api_url,
    )
    watching.close()
    page.reload()
    page.fill("#client", CLIENT_CODE)
    page.fill("#pw", PASSWORD)
    page.select_option("#dock", "D3")
    page.set_input_files(
        "#manifest",
        files=[{"name": "manifest.csv", "mimeType": "text/csv", "buffer": b"lpn,qty\nLPN1,4\n"}],
    )
    page.click("#client")
    page.press("#client", "Enter")
    page.click("#save")
    page.wait_for_function("() => window.__done === true", timeout=20_000)

    flushing = _options(context, worker)
    events = _flush_until_everything_wanted_has_arrived(flushing, batches)
    flushing.close()
    page.close()

    return events


def _flush_until_everything_wanted_has_arrived(
    flushing: Any, batches: list[dict[str, Any]], deadline_seconds: float = 8.0
) -> list[dict[str, Any]]:
    """Flush until every fixture `main` writes has arrived, or the deadline.

    One flush right after the page's own `__done` is not enough: a
    content-script message can still be in flight -- on its way from the page
    to the service worker -- when `drain()` sees an empty queue and returns.
    The XHR body, the failed request and the open event stream are the ones
    most often still travelling, because they are what the page's fetches
    finish last. Retrying against what has actually arrived, rather than
    guessing how long that takes, gives a late one the further flushes it
    needs without slowing down the ordinary case where nothing is missing on
    the first one.
    """
    deadline = time.monotonic() + deadline_seconds
    while True:
        flushing.evaluate("""async () => await chrome.runtime.sendMessage({kind: "flush"})""")
        events = [event for batch in batches for event in batch["events"]]
        if not any(found is None for found in _wanted(events).values()):
            return events
        if time.monotonic() >= deadline:
            return events
        flushing.wait_for_timeout(250)


def main(into: Path = FIXTURES) -> int:
    """Capture into `into`, which the drift test points at a temporary directory
    so it can compare what the extension emits now against what is committed."""
    from playwright.sync_api import sync_playwright

    _Stub.batches = []
    _Stub.artifacts = []
    _Stub.purges = []
    _Stub.fumble_artifacts = 0

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Fixtures)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    api_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(Path(tempfile.mkdtemp(prefix="sro-fixtures-")) / "profile"),
                headless=True,
                channel="chromium",
                args=[
                    f"--disable-extensions-except={EXTENSION}",
                    f"--load-extension={EXTENSION}",
                ],
            )
            try:
                events = _capture(context, api_url, _Stub.batches)
            finally:
                context.close()
    finally:
        server.shutdown()
        server.server_close()

    print(f"captured {len(events)} events; writing:")  # noqa: T201

    wanted = _wanted(events)
    missing = [name for name, payload in wanted.items() if payload is None]
    for name, payload in wanted.items():
        if payload is not None:
            _write(name, payload, into)

    if _Stub.batches:
        _write("batch", _Stub.batches[0], into)

    if missing:
        # Loudly, and with a failing exit: a fixture silently not regenerated is
        # a stale file that keeps passing the contract test against a shape the
        # extension no longer produces.
        print(f"\nNOT captured: {', '.join(missing)}", file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
