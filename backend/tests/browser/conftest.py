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
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlsplit

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
<html><body><h1>Console</h1></body></html>
"""
"""What the real console is, as far as the panel is concerned now: a page at
an address, nothing more. It used to announce itself with `sro.ready` and take
a credential posted into its frame -- that whole handshake was this stub
proving itself rather than the extension, because the frame it answered was
already gone from the panel (`service-worker.js`'s `panel-console`: "the token
no longer leaves this worker for the panel at all"). AGENTS.md's rule is that a
double must not implement the thing under test."""

MAIL = """<!doctype html>
<html><body>
  <div class="mail">
    <span class="from-address">dispatch@supplier.test</span>
    <h1 class="subject">Short shipment on PO 4471</h1>
    <div class="mail-body">
      Two cartons short. Reference <span class="shipment-ref">SH-4471</span>, please advise.
    </div>
  </div>
</body></html>
"""
"""One mail, in the shape an operator marked one: a sender, a subject and the
value they pointed at. Deliberately not any real client's markup -- what the
extension resolves is the marks the watch carries, and a page shaped like
Gmail would suggest it knows something about Gmail, which it must not."""


MAIL_WITH_NO_REFERENCE = MAIL.replace(
    'Reference <span class="shipment-ref">SH-4471</span>, please advise.',
    "Two cartons short, details to follow.",
)
"""The same mail from the same supplier, with the number nobody typed in.

Every mailbox produces these -- an autoreply, a thread with the reference only
in an attachment. The rule matches, the mark finds nothing, and the offer is a
run that would start and be skipped a moment later.
"""


_SHAPES: list[dict[str, object]] = [
    {
        "id": "wfl_lpn",
        "title": "Adjust an LPN quantity",
        # The page the job begins on, as a path -- the stub puts its own
        # address in front. `/elsewhere` is a different page, so an offer that
        # fired on the HOST rather than the page would be obvious.
        "starts_on": "/",
        "hosts": ["127.0.0.1"],
        # Four rungs, because `recognise.match` scans k down from
        # `shape.length - 1` and `offer_after` floors at 2: a shape of three or
        # fewer can be served and never matched.
        "shape": [
            ["127.0.0.1", "input#client", "type"],
            ["127.0.0.1", "input#qty", "type"],
            ["127.0.0.1", "select#depot", "select"],
            ["127.0.0.1", "button#save", "click"],
        ],
        # None, so a press is a press: a job with a parameter nobody has typed
        # sends the card to the conversation to ask for it, which is a
        # different test and one `panel.test.mjs` already holds. Two of this
        # deployment's own jobs declare no parameters either.
        "parameters": [],
        "held_runs": 1,
        "offer_after": 2,
        "quiet_until": None,
        "writes": [{"does": "create", "record": "orders", "on": "http://127.0.0.1", "step": "3"}],
    }
]
"""One job the rig has proved, as `/v1/shapes` answers it.

What the extension offers on arrival: a pill on the page the job starts on,
one card in the panel, nothing on another page."""


_SKILL_LPN_ADJUST = {
    "id": "skl-lpn-adjust",
    "name": "Adjust an LPN quantity",
    "versions": [
        {
            "version": 1,
            # Not "autonomous" and not a version with a clean streak, so
            # `previewOf` in the panel shows every step rather than
            # collapsing to one line -- the shape task 9 needs to see a
            # preview actually list.
            "stage": "practice",
            "track_record": {"clean_streak": 0},
            # The tab the run opens before step one. On the wire because the
            # preview names it -- ADR 014's closed list of what an operator
            # reads before pressing is the step intents, the resolved value of
            # each parameter, and this. Never navigated to by anything in this
            # suite -- the backend's driver is what opens it, and this stub is
            # not one -- so any recognisable address does; what is under test
            # is that the panel says which screen before the press.
            "starts_on": "http://wms.test/inventory/lpn",
            "steps": [
                {"index": 0, "intent": "Type the LPN barcode"},
                {"index": 1, "intent": "Press Save"},
            ],
            "parameters": [
                {
                    "name": "lpn",
                    "kind": "input",
                    "source_step_index": 0,
                    "description": "LPN barcode",
                }
            ],
        }
    ],
}
"""What `GET /v1/skills/skl-lpn-adjust` answers with -- just enough of a
version for the panel's preview to have real steps and a real parameter to
read a sentence's value into, which the mail flow's canned skill (empty
`versions`, used only to read a name off) never needed."""


DEVICE_SECRET = "the-secret-this-browser-was-minted-at-registration"  # noqa: S105
"""What the stub mints for `dev_browsertest`, and refuses every device-scoped
call without. The real backend mints a random one per device; a fixed one here
is what lets a test say which browser is asking."""


class _Stub(BaseHTTPRequestHandler):
    """The frozen contract, answered with canned replies. See docs/14."""

    # 1.1 because a WebSocket upgrade is not a thing an HTTP/1.0 response can
    # carry, and Chrome refuses the handshake rather than explaining itself.
    protocol_version = "HTTP/1.1"

    batches: ClassVar[list[dict[str, Any]]] = []
    artifacts: ClassVar[list[dict[str, Any]]] = []
    fumble_artifacts: ClassVar[int] = 0
    stops: ClassVar[list[str]] = []
    purges: ClassVar[list[str]] = []
    shape_queries: ClassVar[list[str]] = []
    rig_presses: ClassVar[list[dict[str, Any]]] = []
    rig_runs: ClassVar[dict[str, dict[str, Any]]] = {}
    watches: ClassVar[list[dict[str, Any]]] = []
    """The mail rules this browser is handed. Empty by default, so every other
    test here is a browser with no watch on it and nothing of ours in a
    mailbox."""

    granted: ClassVar[list[str]] = []
    matched: ClassVar[list[dict[str, Any]]] = []
    """What the browser posted when it recognised a mail, as bytes and as
    parsed. The bytes are the point: a subject that reached the wire would be
    in them."""

    fired: ClassVar[list[dict[str, Any]]] = []
    """The presses. One per offer an operator acted on, carrying the values it
    was offered with -- nothing was stored at the match, so these are the only
    copy there is."""
    """Answer this many artifact uploads with a 503 before taking any. A lost
    reply from the blob store is the ordinary way one of these fails."""

    """Every sentence handed to intent resolution, in the operator's own
    words -- what the box in `beginOffer` actually sent, not what it was
    prefilled with."""

    run_previews: ClassVar[list[dict[str, Any]]] = []
    """Every press that started a run from a preview, as sent: which skill,
    what a sentence resolved its parameters to, and the sentence itself. This
    is the write task 9's chain promises -- the operator's own words, landing
    as a real request rather than being kept anywhere in between."""

    run_wrongs: ClassVar[list[dict[str, Any]]] = []
    """What was recorded each time a finished run was called wrong -- pressing
    "Undo that" is one of these before it is anything else."""

    runs: ClassVar[dict[str, dict[str, Any]]] = {}
    """Every run this stub has started, keyed by id and mutable: there is no
    real orchestrator behind this stub to carry a run from "running" to a
    terminal status on its own, so a test moves one there itself, the way the
    real backend's own background worker would once its steps actually
    finished."""

    def log_message(self, *args: Any) -> None:
        pass

    def _proved_it_is_itself(self) -> bool:
        """The real backend's rule, because this stub has to be the real other
        half of it: a device-scoped path is refused, indistinguishably from a
        device that never existed, unless the browser presents what
        registration minted for it. Checked here rather than merely recorded --
        an extension that stopped sending it would otherwise go on passing
        every test in this suite while being locked out of a real deployment.
        """
        device_scoped = self.path.startswith("/v1/agents/") or any(
            # The evidence paths take their device id from a request body
            # rather than the URL, so the shape does not say they are
            # device-scoped -- but they are, and the same secret is what says
            # which browser is filing under whose name.
            self.path.split("?")[0] == each
            for each in ("/v1/observations", "/v1/observations/artifacts")
        )
        if not device_scoped or self.path == "/v1/agents/register":
            return True
        if self.headers.get("X-Device-Secret") == DEVICE_SECRET:
            return True
        self._send(404, json.dumps({"detail": "device dev_browsertest was not found"}).encode())
        return False

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
        if not self._proved_it_is_itself():
            return None
        if self.path.startswith("/v1/agents/") and self.path.endswith("/watches"):
            self._send(200, json.dumps(_Stub.watches).encode())
            return
        if self.path.startswith("/mail-vague"):
            self._send(200, MAIL_WITH_NO_REFERENCE.encode(), "text/html; charset=utf-8")
            return
        if self.path.startswith("/mail"):
            self._send(200, MAIL.encode(), "text/html; charset=utf-8")
            return
        if self.path.startswith("/v1/skills/"):
            skill_id = self.path.split("/")[3]
            if skill_id == _SKILL_LPN_ADJUST["id"]:
                self._send(200, json.dumps(_SKILL_LPN_ADJUST).encode())
                return
            # Enough of a skill for the panel to name the task on the card. A
            # card that named an id would be asking somebody to decide about
            # `skl-short-ship`.
            self._send(
                200,
                json.dumps(
                    {"id": skill_id, "name": "Resolve a short ship", "versions": []}
                ).encode(),
            )
            return
        if self.path.startswith("/v1/runs/"):
            # No real orchestrator sits behind this stub, so a run's status
            # here is exactly what a test has put in `_Stub.runs` -- "running"
            # from the moment `/runs/from-preview` answered until a test moves
            # it on, the same thing the real backend's own worker would do in
            # its own time.
            run = _Stub.runs.get(self.path.split("/")[3])
            if run is None:
                self._send(404, json.dumps({"detail": "no such run"}).encode())
                return
            self._send(200, json.dumps(run).encode())
            return
        if self.path.startswith("/v1/shapes"):
            _Stub.shape_queries.append(self.path)
            # The rig's jobs, as the extension asks for them on every page.
            #
            # This route did not exist here until 2026-09-19, and six browser
            # tests had been failing since the worker stopped offering mining
            # CANDIDATES and started offering the rig's own shapes
            # (`candidatesFor`: "Dropped where it is read"). Nothing served
            # shapes, so no offer could ever arrive in a real Chrome and the
            # suite that exists to prove the pill and the card was red.
            #
            # `starts_on` gets this stub's address in front of it because
            # the port is minted per run and the
            # extension compares host AND port -- and with the SCHEME, because
            # the rig records the tab's whole url and `shapesFor` normalises it
            # through `new URL(...)`. Served without one, every shape is
            # dropped silently and nothing is ever offered.
            here = self.headers.get("Host", "")
            self._send(
                200,
                json.dumps(
                    {
                        "shapes": [
                            {**shape, "starts_on": f"http://{here}{shape['starts_on']}"}
                            for shape in _SHAPES
                        ],
                        "can_find": False,
                    }
                ).encode(),
            )
            return
        if self.path.startswith("/v1/workflow-runs/"):
            run = _Stub.rig_runs.get(self.path.rsplit("/", 1)[-1].split("?")[0])
            if run is None:
                self._send(404, json.dumps({"detail": "no such run"}).encode())
                return
            self._send(200, json.dumps(run).encode())
            return
        if self.path.startswith("/elsewhere"):
            # A different page, with a control the first one does not have, so a
            # tree taken from the wrong side of a navigation is obvious.
            self._send(
                200,
                b"<!doctype html><html><body><h1>Elsewhere</h1>"
                b"<button id='only-here'>Only here</button></body></html>",
                "text/html; charset=utf-8",
            )
            return
        if self.path.startswith("/console"):
            # Where "Open the console here" and "Console ↗" are supposed to
            # land -- and nothing else, now that neither frames it.
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

    def do_DELETE(self) -> None:
        _Stub.purges.append(self.path)
        self._send(200, json.dumps({"batches": 2, "events": 34, "artifacts": 5}).encode())

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        if not self._proved_it_is_itself():
            return
        # The address without its query. FastAPI routes on the path and reads
        # the query separately; a stub that matched on both together answered
        # 404 to every call that carried one, which is a difference between the
        # double and the thing that has nothing to do with what is under test.
        route = urlsplit(self.path).path
        if route == "/v1/workflow-runs":
            # The press. `POST /v1/workflow-runs` answers 201 with the whole
            # run row -- the extension reads `started.id` off it, and a stub
            # answering `{"run_id": ...}` would leave the panel with a run it
            # can never poll.
            asked = json.loads(raw or b"{}")
            _Stub.rig_presses.append(asked)
            run = {
                "id": "run_pressed",
                "tenant": "acme",
                "workflow_id": asked.get("workflow_id", ""),
                "device_id": asked.get("device_id", ""),
                "values": asked.get("values", {}),
                "items": asked.get("items", []),
                "started_by": "browser-test",
                "live": bool(asked.get("live")),
                "allow_focus": bool(asked.get("allow_focus")),
                "started_at": "2026-09-19T10:00:00+00:00",
                "finished_at": None,
                "outcome": "running",
                "from_step": 0,
                "steps": [],
                "withheld": [],
                "in_tokens": 0,
                "out_tokens": 0,
                "thought_tokens": 0,
                "cost_usd": 0.0,
                "unpriced": False,
                "watched": bool(asked.get("watched")),
            }
            _Stub.rig_runs["run_pressed"] = run
            self._send(201, json.dumps(run).encode())
            return
        if route.startswith("/v1/runs/") and route.endswith("/stop"):
            _Stub.stops.append(route)
            self._send(200, b"{}")
            return
        if self.path == "/v1/agents/register":
            self._send(
                200,
                json.dumps(
                    {
                        "device_id": "dev_browsertest",
                        # What this browser proves it is itself with from here
                        # on. The tenant credential says which tenant and can
                        # never say which browser, and `.../fire` starts a run.
                        "device_secret": DEVICE_SECRET,
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
        if self.path.endswith("/grants"):
            # The operator pressing "watch this host anyway" on a host the
            # tenant excludes. The real backend records the grant and answers
            # with every grant this device now holds; the extension mirrors
            # that answer and admits evidence from those hosts until they
            # expire. Answered here so the grant path is exercised end to end
            # rather than simulated by writing the extension's own storage.
            host = json.loads(raw or b"{}").get("host", "")
            expires = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
            _Stub.granted.append(host)
            self._send(
                200,
                json.dumps({"grants": [{"host": host, "expires_at": expires}]}).encode(),
            )
            return
        if route.endswith("/matched"):
            # The whole path, query included: which offer this match is for is
            # on the wire, and a test asserting a mail is reported once has to
            # be able to see it.
            _Stub.matched.append(
                {"path": self.path, "raw": raw.decode(), "values": json.loads(raw)}
            )
            self._send(
                200,
                json.dumps(
                    {
                        "trigger_id": route.split("/")[5],
                        "skill_id": "skl-short-ship",
                        "values": json.loads(raw),
                        # The real endpoint asks the skill; this asks the rule,
                        # which for one watch is the same question: a name the
                        # watch reads and the mail did not give up.
                        "missing": _missing(json.loads(raw)),
                    }
                ).encode(),
            )
            return
        if route.endswith("/fire"):
            _Stub.fired.append({"path": self.path, "raw": raw.decode(), "values": json.loads(raw)})
            self._send(
                202,
                json.dumps(
                    {
                        "trigger_id": self.path.split("/")[5],
                        "run_id": "run-from-a-mail",
                        "skipped": None,
                    }
                ).encode(),
            )
            return
        if self.path.endswith("/heartbeat"):
            self._send(200, json.dumps({"pause": False, "policy": None}).encode())
            return
        if self.path.endswith("/runs/from-preview"):
            body = json.loads(raw)
            skill_id = self.path.split("/")[3]
            run_id = f"run-preview-{len(_Stub.run_previews) + 1}"
            _Stub.run_previews.append(
                {"path": self.path, "skill_id": skill_id, "run_id": run_id, **body}
            )
            _Stub.runs[run_id] = {
                "id": run_id,
                "skill_id": skill_id,
                "skill_version": 1,
                "stage": "practice",
                "medium": "extension",
                "device_id": body.get("device_id"),
                "status": "running",
                "parameters": body.get("parameters", {}),
                "derived": {},
                "requested_by": "browser-test",
                "authorized_by": None,
                "started_at": datetime.now(UTC).isoformat(),
                "ended_at": None,
                "failure": None,
                "wrong_because": None,
                "intent": body.get("intent", ""),
                "reversal": None,
                "steps": [],
            }
            self._send(201, json.dumps(_Stub.runs[run_id]).encode())
            return
        if self.path.endswith("/wrong"):
            run_id = self.path.split("/")[3]
            body = json.loads(raw)
            _Stub.run_wrongs.append({"run_id": run_id, **body})
            run = _Stub.runs.setdefault(run_id, {})
            run["wrong_because"] = body.get("because")
            self._send(202, json.dumps(run).encode())
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


def _missing(values: dict[str, str]) -> list[str]:
    """What the watches this browser holds read that the mail did not give up."""
    reads = {name for rule in _Stub.watches for name in rule.get("from_message", [])}
    return sorted(name for name in reads if not values.get(name, "").strip())


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
    _Stub.stops = []
    _Stub.purges = []
    _Stub.shape_queries = []
    _Stub.rig_presses = []
    _Stub.rig_runs = {}
    _Stub.watches = []
    _Stub.matched = []
    _Stub.fired = []
    _Stub.run_previews = []
    _Stub.run_wrongs = []
    _Stub.runs = {}
    # Threading, because the panel's event stream holds its connection open for
    # the length of the test: on a single-threaded server that one socket is the
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
def rig_presses(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Every `POST /v1/workflow-runs` the extension made, as sent.

    The one press this product is for: a person reads a card and a warehouse is
    written to. Nothing in this suite watched it happen until 2026-09-19."""
    return _Stub.rig_presses


@pytest.fixture
def shape_queries(stub: tuple[str, list[dict[str, Any]]]) -> list[str]:
    """The `/v1/shapes` requests the extension made, as sent.

    The offer a browser makes on arrival comes from the rig's proven jobs."""
    return _Stub.shape_queries


@pytest.fixture
def watching(
    stub: tuple[str, list[dict[str, Any]]],
) -> Callable[[list[dict[str, Any]]], None]:
    """Give this browser its operator's mail rules, before it registers.

    Empty unless a test says otherwise: a watch registers a content script on
    a mailbox, and every other test in this file is entitled to a browser with
    nothing of ours anywhere near one.
    """

    def hand_over(rules: list[dict[str, Any]]) -> None:
        _Stub.watches = rules

    return hand_over


@pytest.fixture
def matched(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """What this browser posted when it recognised a mail, as sent."""
    return _Stub.matched


@pytest.fixture
def fired(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """The presses this browser made, as sent."""
    return _Stub.fired


@pytest.fixture
def purges(stub: tuple[str, list[dict[str, Any]]]) -> list[str]:
    """The `DELETE /v1/observations` calls the extension made, as sent."""
    return _Stub.purges


@pytest.fixture
def run_previews(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Every press that started a run from a preview, as sent."""
    return _Stub.run_previews


@pytest.fixture
def run_wrongs(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """What was recorded each time a finished run was called wrong."""
    return _Stub.run_wrongs


@pytest.fixture
def finish_run(
    stub: tuple[str, list[dict[str, Any]]],
) -> Callable[[str, dict[str, str], dict[str, Any] | None], None]:
    """Move a run this stub started to a terminal status.

    Nothing here is a real orchestrator: `/runs/from-preview` answers
    "running" and stays there until a test says otherwise, exactly as far as
    this stub can honestly go on its own. This is the moment a real
    deployment's own background worker would reach on its own time, once the
    run's steps had actually finished -- called explicitly here because
    nothing in this process is going to reach it by itself.
    """

    def move(run_id: str, derived: dict[str, str], reversal: dict[str, Any] | None) -> None:
        run = _Stub.runs[run_id]
        run["status"] = "succeeded"
        run["derived"] = derived
        run["reversal"] = reversal
        run["ended_at"] = datetime.now(UTC).isoformat()

    return move


@pytest.fixture
def fumble_artifacts(stub: tuple[str, list[dict[str, Any]]]) -> Callable[[int], None]:
    """Make the stub lose the next `times` screenshot uploads."""

    def fumble(times: int) -> None:
        _Stub.fumble_artifacts = times

    return fumble


@pytest.fixture
def stops(stub: tuple[str, list[dict[str, Any]]]) -> list[str]:
    """The `POST /v1/runs/{id}/stop` calls the extension made, as sent."""
    return _Stub.stops


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
