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
from datetime import UTC, datetime, timedelta
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


_CANDIDATES: list[dict[str, object]] = [
    {
        "id": "cnd-here",
        "title": "Adjust an LPN quantity",
        "host": "127.0.0.1",
        # The page this task begins on, as a path. The stub puts its own
        # address in front when it serves this, because the port is minted per
        # run and the extension compares host *and* port -- the miner records
        # the netloc, so two applications on one machine are two applications.
        #
        # The root, where the stub serves its ordinary page. `/elsewhere` is a
        # different one, so a nudge that fired on the host rather than the page
        # would be obvious.
        "starts_on": "/",
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
            },
            {
                # Already answered, and by a person: the one state anything is
                # allowed to act on.
                "other_id": "cnd-elsewhere",
                "kind": "workflow",
                "because": "the receipt is always written straight after",
                "by_model": True,
                "answered": "same",
                "answered_by": "you",
            },
        ],
        "episodes": [],
    },
    {
        "id": "cnd-dismissed",
        "title": "Something already said no to",
        "host": "127.0.0.1",
        "signature": "GET wm/labels/*",
        "status": "dismissed",
        "times_seen": 7,
        "median_duration_ms": 9000,
        "minutes_so_far": 1.0,
        "first_seen": None,
        "last_seen": None,
        "skill_id": None,
        "dismissed_reason": "not worth automating",
        "named_by_model": False,
        "joins": [],
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
    {
        "id": "cnd-lpn-here",
        # No model title: this candidate is offered on the noun `plainly()`
        # reads off its own signature, the other of the two sentences that
        # function says, so the end-to-end test exercises both halves of the
        # panel between them rather than only the one `cnd-here` already
        # covers.
        "title": None,
        # `localhost`, not `127.0.0.1` -- a second host aliasing the same
        # stub (see `MAIL_WITH_NO_REFERENCE`'s sibling tests for the same
        # trick), so a "new" candidate here is never counted by
        # `test_the_panel_shows_only_the_tasks_of_the_system_in_front_of_it`,
        # which asserts there is exactly one on `127.0.0.1`.
        "host": "localhost",
        "signature": "PUT wm/inventory/adjust",
        "status": "new",
        "times_seen": 3,
        "median_duration_ms": 20000,
        "minutes_so_far": 1.0,
        "first_seen": None,
        "last_seen": None,
        "skill_id": None,
        "dismissed_reason": None,
        "named_by_model": False,
        "joins": [],
        "episodes": [],
    },
]

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
    channels: ClassVar[queue.Queue[Channel]] = queue.Queue()
    purges: ClassVar[list[str]] = []
    candidate_queries: ClassVar[list[str]] = []
    answered_joins: ClassVar[list[dict[str, Any]]] = []
    merged: ClassVar[list[dict[str, Any]]] = []
    recordings: ClassVar[list[str]] = []
    sealed: ClassVar[list[str]] = []
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

    resolutions_asked: ClassVar[list[str]] = []
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
            for each in ("/v1/observations", "/v1/observations/artifacts", "/v1/recordings")
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
        if "websocket" in self.headers.get("Upgrade", "").lower():
            return self._upgrade()
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
        if self.path.startswith("/v1/candidates"):
            _Stub.candidate_queries.append(self.path)
            # Filtered here the way the real endpoint filters: the panel's whole
            # question is "on this system", and a test that filtered client-side
            # would prove the wrong half.
            wanted = parse_qs(urlsplit(self.path).query).get("host", [""])[0]
            # `starts_on` is stored as a path and answered as an address: this
            # stub's port is minted per run, and what the panel compares against
            # is host-with-port. Everything else is served as written.
            here = self.headers.get("Host", "")
            mine = [
                {**c, "starts_on": f"{here}{c['starts_on']}".rstrip("/")}
                if c.get("starts_on")
                else c
                for c in _CANDIDATES
                if c["host"] == wanted
            ]
            self._send(200, json.dumps(mine).encode())
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
        if self.path.startswith("/wide"):
            # A page whose accessibility tree is the size a real WMS screen
            # produces. One teaching batch holds 2MB, and a demonstration on a
            # page like this needs several -- which is the case that used to
            # lose everything after the first.
            crowd = "".join(
                f'<button id="b{index}">Control {index}</button>' for index in range(1200)
            )
            self._send(
                200, PAGE.replace("</form>", f"</form>{crowd}").encode(), "text/html; charset=utf-8"
            )
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
        # `bearer`, the tenant credential, and the device's own secret. A
        # browser cannot set a header on a WebSocket, so the secret rides here
        # beside the credential -- and a socket that opened without it would be
        # the one device-scoped path this suite left unproved.
        if len(offered) < 3 or offered[2] != DEVICE_SECRET:
            self.send_response(403)
            self.end_headers()
            return
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
        if not self._proved_it_is_itself():
            return
        # The address without its query. FastAPI routes on the path and reads
        # the query separately; a stub that matched on both together answered
        # 404 to every call that carried one, which is a difference between the
        # double and the thing that has nothing to do with what is under test.
        route = urlsplit(self.path).path
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
        if self.path.endswith("/teach-together"):
            asked = json.loads(raw)
            _Stub.merged.append({"path": self.path, **asked})
            self._send(
                202,
                json.dumps(
                    {
                        "first_id": self.path.split("/")[3],
                        "second_id": asked["other_id"],
                        "recording_ids": ["rec-1", "rec-2"],
                        "skill_id": "skl-merged",
                        "needs_demonstration": False,
                        "because": None,
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
        if self.path.endswith("/teach"):
            # Silent, the way `beginOffer` asks for it: nothing here needs
            # evidence to disagree about, so the induction the real endpoint
            # would attempt always succeeds on the first ask.
            self._send(
                202,
                json.dumps(
                    {
                        "candidate_id": self.path.split("/")[3],
                        "recording_id": None,
                        "skill_id": _SKILL_LPN_ADJUST["id"],
                        "needs_demonstration": False,
                        "because": None,
                    }
                ).encode(),
            )
            return
        if self.path == "/v1/intent/resolve":
            asked = json.loads(raw)
            _Stub.resolutions_asked.append(asked.get("utterance", ""))
            # A fixed match regardless of what was typed: reading a sentence
            # is `resolve_intent`'s job and is proven at the unit and contract
            # level already (`tests/unit/application/test_resolve_intent.py`).
            # What a browser has to prove is that the sentence really leaves
            # the panel and a real preview comes back for it -- not that the
            # parser is any good, which no stub could prove anyway.
            self._send(
                200,
                json.dumps(
                    {
                        "utterance": asked.get("utterance", ""),
                        "matched": {
                            "skill_id": _SKILL_LPN_ADJUST["id"],
                            "name": _SKILL_LPN_ADJUST["name"],
                            "version": 1,
                            "stage": "practice",
                            "summary": "Types the LPN and saves the new quantity.",
                            "score": 100,
                            "why": [],
                            "unexplained": [],
                        },
                        "choices": [],
                        "missing_parameters": [],
                        "runnable": True,
                        "confident": True,
                        "question": None,
                        "why": [],
                        "proposal": None,
                        "items": [{"lpn": "LPN-4471"}],
                    }
                ).encode(),
            )
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
    _Stub.channels = queue.Queue()
    _Stub.purges = []
    _Stub.candidate_queries = []
    _Stub.answered_joins = []
    _Stub.merged = []
    _CANDIDATES[0]["joins"][0].update(answered=None, answered_by=None)
    _Stub.recordings = []
    _Stub.sealed = []
    _Stub.watches = []
    _Stub.matched = []
    _Stub.fired = []
    _Stub.resolutions_asked = []
    _Stub.run_previews = []
    _Stub.run_wrongs = []
    _Stub.runs = {}
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
def merged(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """The pairs the panel asked to have taught as one skill."""
    return _Stub.merged


@pytest.fixture
def answered_joins(stub: tuple[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """What the panel said two candidates are to each other."""
    return _Stub.answered_joins


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
def resolutions_asked(stub: tuple[str, list[dict[str, Any]]]) -> list[str]:
    """Every sentence the panel asked `/v1/intent/resolve` about, in order."""
    return _Stub.resolutions_asked


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
