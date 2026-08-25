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
import queue
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.browser.ws import Channel, accept_key, decode

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
      // What `ui.perform`'s strongest locator asks. Two components, queried
      // the way this WMS's own code queries them: by xtype and itemId.
      ComponentQuery: {
        query: (q) => {
          const byQuery = {
            'panel#clients textfield#clientCode': 'client',
            'panel#clients button#saveButton': 'save',
          };
          const id = byQuery[q];
          const dom = id ? document.getElementById(id) : null;
          return dom ? [{isVisible: () => true, el: {dom}, inputEl: {dom}}] : [];
        },
      },
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
      // Awaited, not fired and forgotten. `__done` is what every test waits on
      // before flushing, and an XHR that had not finished by then made every
      // assertion about the XHR patch a race that usually won.
      const legacy = new Promise((resolve) => xhr.addEventListener('loadend', resolve));
      xhr.send('clientCode=' + document.getElementById('client').value + '&token=SEKRIT');
      await legacy;
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


CONSOLE = """<!doctype html>
<html><body><h1>Console</h1>
<script>
  // What the real console does: says it is listening, then takes a credential
  // from the origin that framed it and confirms.
  window.__handed = null;
  addEventListener("message", (event) => {
    if (event.data && event.data.kind === "sro.credential") {
      window.__handed = event.data.token;
      event.source.postMessage({kind: "sro.credential.ok"}, event.origin);
    }
  });
  parent.postMessage({kind: "sro.ready"}, "*");
</script>
</body></html>
"""

_CANDIDATES = [
    {
        "id": "cnd-here",
        "title": "Adjust an LPN quantity",
        "host": "127.0.0.1",
        "signature": "PUT wm/inventory/adjust",
        "status": "new",
        "times_seen": 4,
        "median_duration_ms": 32000,
        "minutes_so_far": 2.1,
        "first_seen": None,
        "last_seen": None,
        "skill_id": None,
        "dismissed_reason": None,
        "named_by_model": True,
        "joins": [
            {
                "other_id": "cnd-elsewhere",
                "kind": "variant",
                "because": "the second checks the count first",
                "by_model": True,
                "answered": None,
                "answered_by": None,
            }
        ],
        "episodes": [],
    },
    {
        "id": "cnd-elsewhere",
        "title": "Something on another system",
        "host": "erp.example",
        "signature": "POST erp/receipts",
        "status": "new",
        "times_seen": 9,
        "median_duration_ms": 12000,
        "minutes_so_far": 1.8,
        "first_seen": None,
        "last_seen": None,
        "skill_id": None,
        "dismissed_reason": None,
        "named_by_model": False,
        "joins": [],
        "episodes": [],
    },
]


class _Stub(BaseHTTPRequestHandler):
    """The frozen contract, answered with canned replies. See docs/14."""

    # 1.1 because a WebSocket upgrade is not a thing an HTTP/1.0 response can
    # carry, and Chrome refuses the handshake rather than explaining itself.
    protocol_version = "HTTP/1.1"

    batches: ClassVar[list[dict[str, Any]]] = []
    artifacts: ClassVar[list[dict[str, Any]]] = []
    fumble_artifacts: ClassVar[int] = 0
    channels: ClassVar[queue.Queue[Channel]] = queue.Queue()
    purges: ClassVar[list[str]] = []
    candidate_queries: ClassVar[list[str]] = []
    answered_joins: ClassVar[list[dict[str, Any]]] = []
    recordings: ClassVar[list[str]] = []
    sealed: ClassVar[list[str]] = []
    """Answer this many artifact uploads with a 503 before taking any. A lost
    reply from the blob store is the ordinary way one of these fails."""

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
        if "websocket" in self.headers.get("Upgrade", "").lower():
            return self._upgrade()
        if self.path.startswith("/v1/candidates"):
            _Stub.candidate_queries.append(self.path)
            # Filtered here the way the real endpoint filters: the panel's whole
            # question is "on this system", and a test that filtered client-side
            # would prove the wrong half.
            wanted = parse_qs(urlsplit(self.path).query).get("host", [""])[0]
            self._send(200, json.dumps([c for c in _CANDIDATES if c["host"] == wanted]).encode())
            return
        if self.path.startswith("/console"):
            # A console, as far as the panel is concerned: it announces itself
            # and writes down whatever it is handed.
            self._send(200, CONSOLE.encode(), "text/html; charset=utf-8")
            return
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

    def _upgrade(self) -> None:
        """The command channel, on the same port everything else is on.

        The credential rides in the subprotocol, and one has to be echoed or
        Chrome fails the connection -- which would look exactly like an
        extension that never dialled.
        """
        offered = [p.strip() for p in self.headers.get("Sec-WebSocket-Protocol", "").split(",")]
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept_key(self.headers["Sec-WebSocket-Key"]))
        if offered:
            self.send_header("Sec-WebSocket-Protocol", offered[0])
        self.end_headers()
        self.wfile.flush()

        channel = Channel(self.wfile)
        _Stub.channels.put(channel)
        while True:
            opcode, payload = decode(self.rfile)
            if opcode == 8:
                return
            if opcode != 1:
                continue
            try:
                channel.messages.put(json.loads(payload))
            except json.JSONDecodeError:
                continue

    def do_DELETE(self) -> None:
        _Stub.purges.append(self.path)
        self._send(200, json.dumps({"batches": 2, "events": 34, "artifacts": 5}).encode())

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
                            # On, so the screenshot half is exercised by every
                            # test here rather than by one that opts in. The
                            # cap is deliberately low: a test that clicks a
                            # handful of times must be able to reach it.
                            "capture_screenshots": True,
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
        if self.path.endswith("/heartbeat"):
            self._send(200, json.dumps({"pause": False, "policy": None}).encode())
            return
        if self.path == "/v1/recordings":
            recording_id = f"rec_browsertest{len(_Stub.recordings)}"
            _Stub.recordings.append(recording_id)
            self._send(
                201,
                json.dumps({"recording_id": recording_id, "live_view_url": ""}).encode(),
            )
            return
        if self.path.startswith("/v1/recordings/") and self.path.endswith("/finish"):
            _Stub.sealed.append(self.path.split("/")[3])
            self._send(
                200,
                json.dumps(
                    {
                        "id": self.path.split("/")[3],
                        "objective_key": None,
                        "label": None,
                        "status": "sealed",
                        "demonstrator": "browser-test",
                        "started_at": "2026-08-25T09:00:00+00:00",
                        "ended_at": "2026-08-25T09:05:00+00:00",
                        "frame_count": 2,
                        "has_narration": False,
                    }
                ).encode(),
            )
            return
        if self.path.endswith("/joins"):
            asked = json.loads(raw)
            _Stub.answered_joins.append({"path": self.path, **asked})
            # Kept, the way the real endpoint keeps it: the panel re-reads the
            # list after answering, and a suggestion that came back still asking
            # would be a screen that never stops asking.
            _CANDIDATES[0]["joins"][0].update(answered=asked["answer"], answered_by="you")
            self._send(200, json.dumps(_CANDIDATES[0]).encode())
            return
        if self.path == "/api/echo":
            # Says back what reached it, so the test can prove the call carried
            # the page's own cookies rather than the extension's origin.
            self._send(
                200,
                json.dumps(
                    {
                        "cookie": self.headers.get("Cookie", ""),
                        "body": raw.decode("utf-8", "replace"),
                    }
                ).encode(),
            )
            return
        if self.path == "/v1/observations/artifacts":
            if _Stub.fumble_artifacts > 0:
                _Stub.fumble_artifacts -= 1
                self._send(503, json.dumps({"detail": "the blob store is busy"}).encode())
                return
            _Stub.artifacts.append(_parts(self.headers.get("Content-Type", ""), raw))
            stored = {"uri": "s3://stub/shot.png", "size_bytes": len(raw)}
            self._send(201, json.dumps(stored).encode())
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


def _parts(content_type: str, raw: bytes) -> dict[str, Any]:
    """One multipart body, as the fields it carries.

    Hand-parsed rather than through `email` or `cgi`: the file part is PNG, and
    every stdlib parser here either decodes it as text or is gone in 3.13.
    """
    boundary = content_type.split("boundary=", 1)[1].strip('"').encode()
    fields: dict[str, Any] = {}
    for part in raw.split(b"--" + boundary)[1:-1]:
        head, _, value = part.lstrip(b"\r\n").partition(b"\r\n\r\n")
        disposition = head.split(b"\r\n")[0].decode("latin-1")
        name = disposition.split('name="', 1)[1].split('"', 1)[0]
        body = value[: -len(b"\r\n")] if value.endswith(b"\r\n") else value
        fields[name] = body if "filename=" in disposition else body.decode()
    return fields


@pytest.fixture
def stub() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    _Stub.batches = []
    _Stub.artifacts = []
    _Stub.fumble_artifacts = 0
    _Stub.channels = queue.Queue()
    _Stub.purges = []
    _Stub.candidate_queries = []
    _Stub.answered_joins = []
    _CANDIDATES[0]["joins"][0].update(answered=None, answered_by=None)
    _Stub.recordings = []
    _Stub.sealed = []
    # Threading, because the command channel holds its connection open for the
    # length of the test: on a single-threaded server that one socket is the
    # whole server, and every upload behind it waits forever.
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Stub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _Stub.batches
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def artifacts(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """What the extension uploaded to `/v1/observations/artifacts`, in order.

    Alongside `stub` rather than inside its tuple so the tests that predate
    screenshots keep unpacking two things.
    """
    return _Stub.artifacts


@pytest.fixture
def demonstrations(stub: tuple[str, list[dict[str, Any]]]) -> tuple[list[str], list[str]]:
    """The recordings this browser started, and the ones it sealed."""
    return _Stub.recordings, _Stub.sealed


@pytest.fixture
def candidate_queries(stub: tuple[str, list[dict[str, Any]]]) -> list[str]:
    """The `/v1/candidates` requests the panel made, as sent."""
    return _Stub.candidate_queries


@pytest.fixture
def answered_joins(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """What the panel said two candidates are to each other."""
    return _Stub.answered_joins


@pytest.fixture
def purges(stub: tuple[str, list[dict[str, Any]]]) -> list[str]:
    """The `DELETE /v1/observations` calls the extension made, as sent."""
    return _Stub.purges


@pytest.fixture
def fumble_artifacts(stub: tuple[str, list[dict[str, Any]]]) -> Callable[[int], None]:
    """Make the stub lose the next `times` screenshot uploads."""

    def fumble(times: int) -> None:
        _Stub.fumble_artifacts = times

    return fumble


@pytest.fixture
def channel(stub: tuple[str, list[dict[str, Any]]]) -> Callable[[], Channel]:
    """The socket the extension dialled, once it has. Waits for it rather than
    assuming: the extension opens it a moment after registration lands."""

    def dialled(timeout: float = 20.0) -> Channel:
        try:
            return _Stub.channels.get(timeout=timeout)
        except queue.Empty:
            raise AssertionError("the extension never opened a command channel") from None

    return dialled


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
