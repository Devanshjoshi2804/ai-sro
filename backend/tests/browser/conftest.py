"""A real Chrome with the real extension loaded, talking to a stub backend.

Everything else that tests this extension tests a piece of it: a vm sandbox
standing in for the isolated world, fixtures hand-shaped to match what the code
is believed to emit, a contract test that parses those fixtures. None of it had
ever run the extension in a browser, so nothing had checked the parts only a
browser has -- that a content script registered for `world: "MAIN"` really can
see the page's globals, that the patched `fetch` is the one the page calls,
that IndexedDB survives, that a password typed into a real input really is
absent from the bytes that leave the machine.

The backend here is a stub rather than the real service on purpose: this is a
test of the browser half, it must not need Postgres or MinIO to run, and the
bytes the extension uploads are exactly the bytes the real ingest would store
verbatim. `tests/contract/` already proves those bytes parse into the domain.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

EXTENSION = Path(__file__).resolve().parents[3] / "new-chrome-extension"

PAGE = """<!doctype html>
<html><body>
  <h1>Depot</h1>
  <form id="f">
    <label for="client">Client Code</label>
    <input id="client" name="clientCode" type="text">
    <label for="pw">Password</label>
    <input id="pw" name="password" type="password">
    <button id="save" type="button">Save</button>
  </form>
  <script>
    // A stand-in for the component registry this WMS is built out of. It only
    // has to be a *page-realm* global with the two entry points the recorder
    // reaches for: from an isolated world `window.Ext` is a different window's
    // property and none of this is visible, which is precisely the bug.
    window.Ext = {
      getCmp: (id) => ({
        'client': {xtype: 'textfield', itemId: 'clientCode', name: 'clientCode',
                   fieldLabel: 'Client Code',
                   ownerCt: {xtype: 'panel', itemId: 'clients'}},
        'save': {xtype: 'button', itemId: 'saveButton', text: 'Save',
                 ownerCt: {xtype: 'panel', itemId: 'clients'}},
      })[id] || null,
    };
    document.getElementById('save').addEventListener('click', async () => {
      // One of each transport, because they are patched separately.
      await fetch('/api/orders', {
        method: 'POST',
        headers: {'content-type': 'application/json', 'Authorization': 'Bearer LIVE-SESSION-TOKEN'},
        body: JSON.stringify({
          clientCode: document.getElementById('client').value,
          password: document.getElementById('pw').value,
        }),
      });
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/legacy');
      xhr.responseType = 'json';   // the shape whose responseText getter throws
      xhr.setRequestHeader('content-type', 'application/x-www-form-urlencoded');
      xhr.send('clientCode=' + document.getElementById('client').value + '&token=SEKRIT');
      // The body on a Request rather than in init -- the shape that used to
      // be reported as having no body at all.
      await fetch(new Request('/api/wrapped', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({clientCode: document.getElementById('client').value,
                              secret: document.getElementById('pw').value}),
      }));
      // A stream: reading this to the end would never finish, and used to mean
      // the page's own fetch never resolved.
      await fetch('/api/stream');
      window.__done = true;
    });
  </script>
</body></html>
"""


class _Stub(BaseHTTPRequestHandler):
    """The frozen contract, answered with canned replies. See docs/14."""

    batches: ClassVar[list[dict[str, Any]]] = []

    def log_message(self, *args: Any) -> None:
        pass

    def _send(self, code: int, body: bytes, kind: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, b"")

    def do_GET(self) -> None:
        if self.path == "/api/stream":
            # Deliberately never finished: an endless body is the case that
            # hung the page, and it must not hang this test either.
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b"data: tick\n\n")
            self.wfile.flush()
            return
        self._send(200, PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        if self.path == "/v1/agents/register":
            self._send(
                200,
                json.dumps(
                    {
                        "device_id": "dev_browsertest",
                        "policy_version": 1,
                        "policy": {
                            "version": 1,
                            "capture_enabled": True,
                            # `localhost` and `127.0.0.1` reach this same stub
                            # without any DNS, so one hostname can be excluded
                            # and the other not, and the difference is a real
                            # policy decision rather than a mocked one.
                            "exclude_hosts": ["localhost"],
                            "include_hosts": [],
                            "capture_screenshots": False,
                            "screenshot_max_per_minute": 20,
                            "capture_response_bodies": True,
                            "max_body_bytes": 262144,
                            "daily_budget_bytes": 524288000,
                            "retention_days": 30,
                        },
                    }
                ).encode(),
            )
            return
        if self.path.endswith("/heartbeat"):
            self._send(200, json.dumps({"pause": False, "policy": None}).encode())
            return
        if self.path == "/v1/observations":
            batch = json.loads(raw)
            _Stub.batches.append(batch)
            self._send(
                201,
                json.dumps(
                    {
                        "batch_id": batch["batch_id"],
                        "accepted": len(batch["events"]),
                        "rejected": 0,
                        "problems": [],
                        "stored_at": "s3://stub/x.ndjson",
                        "already_had_it": False,
                    }
                ).encode(),
            )
            return
        self._send(200, json.dumps({"ok": True}).encode())


@pytest.fixture
def stub() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    _Stub.batches = []
    server = HTTPServer(("127.0.0.1", 0), _Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _Stub.batches
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def browser(tmp_path: Path) -> Iterator[Any]:
    """A persistent context with the unpacked extension loaded.

    Persistent because an extension needs a profile, and headed because MV3
    service workers do not start under old headless. Skips rather than fails
    where no browser is installed, the way the contract test skips with no
    fixtures.
    """
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                str(tmp_path / "profile"),
                headless=True,
                channel="chromium",
                args=[
                    f"--disable-extensions-except={EXTENSION}",
                    f"--load-extension={EXTENSION}",
                ],
            )
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium able to load an extension here: {why}")
        try:
            yield context
        finally:
            context.close()
