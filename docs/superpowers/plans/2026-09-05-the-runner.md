# The runner — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A proven workflow performs, in the operator's own Chrome: a small model
plans one command per step, the extension performs it, the rig verifies against
state before it trusts a picture, and every step's record holds what was sent,
what came back, and what it cost.

**Architecture:** The third loop on the whiteboard. The rig grows a command
channel the extension dials (exactly as it already dials the backend's), a `Run`
record, and five pure modules — locators, planner, verifier, runner, doors —
around one loop: *look, plan, refuse-or-perform, verify, escalate once, stop and
ask.* The first execution of any workflow is dry: reads and navigations go out,
writes are shown in full and withheld.

**Tech Stack:** Python 3.12+, uv, SQLite, FastAPI WebSockets (already a
dependency via `uvicorn[standard]`), `google-genai`. Extension: plain ES modules,
node's own test runner. No new dependencies on either side.

**Spec:** [`docs/superpowers/specs/2026-09-03-model-first-workflow-mining-design.md`](../specs/2026-09-03-model-first-workflow-mining-design.md) — sections *The runner*, *Entering a run*, *What this must refuse*.
**Algorithms:** [`docs/new-agent-doc-arc/algorithms.md`](../../new-agent-doc-arc/algorithms.md) — this plan implements **A13–A15**.
**Wire:** [`docs/14-extension-protocol.md`](../../14-extension-protocol.md) §3, *The command channel*. Frozen. Nothing here changes it.
**Plans 1 and 2, which this builds on:** [`2026-09-03-evidence-in-intents-out.md`](2026-09-03-evidence-in-intents-out.md), [`2026-09-04-the-miner.md`](2026-09-04-the-miner.md).

---

## What this plan is for

Plans 1 and 2 built two of the whiteboard's three loops: every gesture is read,
and a window of a day is mined into workflows whose every step cites its
evidence. Eight real workflows exist in `rig.db`. Not one of them can be
performed. The spec's decision table says how they must be:

> **The model plans, the extension performs.** The frozen `docs/14` command
> channel, in the operator's own Chrome. Not server-side computer use, not
> parameter substitution into recorded calls.

An earlier bridge (`backend/src/sro/application/skill/from_rig.py` and its
siblings) turns a mined workflow into the *backend's* skill shape — recorded
calls with `$name` substituted into their bodies. That is exactly the execution
model the spec crossed out. It stays, recategorised: it is how a mined workflow
enters the backend's **governance** (the promotion ladder the spec says anything
unattended must pass through). It is not the runner. This plan is.

## Global Constraints

Every one of these from plans 1 and 2 is still binding:

- Python **>= 3.12**, `uv` only. Never `pip`, never a bare `python`.
- **Never import from `sro.*`** — `tests/test_standalone.py` walks every file under `src/` and fails if anything does.
- **No test may make a real network call.** `FakeAsker` is the seam for models; `FakeChannel` (Task 1) is the seam for the browser.
- **Credential values never reach storage or a prompt.** A header whose stored value is the redaction marker `«redacted»` is never sent.
- **Search grounding is never enabled** on a Gemini call. `build_config` carries no tools; every call routes through `Asker.ask`.
- **Money is recorded per model call**, on the step that made it, flagged `unpriced` when it cannot be established.
- **`ruff format` is the authority on layout.** Transcribe, then `uv run ruff format src tests`, then commit what it produces.
- Three gates clean before every commit: `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run mypy src`. The extension: `make test-extension` from the repo root.

And these are new, from the spec's *What this must refuse*:

- **A command to an origin outside the run's allowlist is refused by the rig before it reaches the extension.** The allowlist is the set of systems the workflow's own cited evidence names. Checked in the runner, not the channel.
- **The first execution of a workflow is dry.** Reads and navigations go out; a step that writes is shown in full and withheld. `live=True` is a person's explicit choice per run.
- **A run stops at its step budget:** the workflow's step count plus `K_STEP_SLACK`.
- **Screenshots go to the model inline** (`Part.from_bytes`, which `GeminiAsker.ask` already does) and are **never uploaded to the File API.** Nothing to delete because nothing is stored there.
- **Nothing runs unattended.** There is no scheduler in the rig. A run starts from a door a person opened, `allow_focus` is set by that door, and the rig has no way to start one on its own.
- **The extension answers every command exactly once.** That is `channel.js`'s existing contract and Task 2 preserves it verbatim.

## Decisions already taken, with their evidence

Do not relitigate these while implementing.

**Verify against state before a picture.** A state-grounded verifier scored 86.9% against 78.8% for one reading screenshots, and most completions leave their proof off-screen (artifact verification was 192 of 321 tasks). So A14's order is fixed: the response body the command returned, then a confirming read the cited evidence shows the page makes, then the screenshot last.

**Flash plans, Pro rescues.** Small models match frontier ones at per-step inference (Phi-4 14B at MRR 0.89). A clean step never touches the expensive model; only a step that surprises us does.

**`origin` is per step, from that step's own evidence.** A documented cross-application failure is losing window focus during a hand-off, so data meant for the second application is typed into the first. Per-step origin is what stops it.

**A weak locator match succeeds and flags stale.** `matched_by` in `{"css_path", None}` after `component` and `role_and_name` both missed is a step about to break. The run succeeds; the workflow is marked stale.

**Prefer `ui.perform` over `http.send` for a write.** Decided during this plan's design from a measurement: 544 of the real store's request headers are CSRF tokens, every one redacted at the rig's boundary to `«redacted»`. An `http.send` replaying the recorded call would send that marker as its CSRF header and be refused by the WMS. Clicking Save instead lets the page mint its own token. So the planner is told: drive the UI; send a call only when the cited gesture carries a call and has no usable UI target. This is not "parameter substitution into recorded calls" — the model decides per step, the evidence carries the values, and the UI does the sending.

**A rig "stream" is a device.** `correlate.py` sets `stream_id = batch.device_id`. So the device a run drives is the device its workflow's evidence came from, and `GET /v1/devices` lists what is connected; there is nothing else to choose between today.

## What plans 1 and 2 already give us

Do not rebuild any of this.

| From | Signature |
|---|---|
| `rig.store.Store` | `.connect()`, `.migrate()`, `.execute(sql, params)`, `.query(sql, params)`, `ADDED_COLUMNS` |
| `rig.records` | `Gesture(id, tenant, stream_id, batch_id, at, url, system, tab_id, frame_url, gesture: wire.Gesture, page_url, requests: list[wire.Request], page_events)`, `Intent` |
| `rig.wire` | `Gesture(kind, target, value, secret, modifiers, at, url)`, `Target(tag, role, name, text, testId, cssPath, xpath, component)`, `Component(framework, xtype, itemId, name, fieldLabel, text, query, chain)`, `Request(method, url, status, request_headers, request_body, response_body, ...)`, `REDACTED` |
| `rig.workflows` | `Workflow(id, tenant, title, narrative, systems, steps: list[Step], parameters, ...)`, `Step(order, says, system, cites, parameters)`, `known_workflows(store, tenant)`, `cited_ids(workflow)` |
| `rig.correlate` | `system_of(url) -> str \| None` — scheme and host |
| `rig.trim` | `trim(gesture) -> dict`, `thin(target) -> bool`, `is_secret(gesture) -> bool`, `body_keys(body)` |
| `rig.models` | `Asker` Protocol, `Answer(data, in_tokens, out_tokens, thought_tokens, cost_usd, unpriced, error)`, `Effort`, `FakeAsker(*answers)`, `one_at_a_time(name)` |
| `rig.api` | `build_app(*, store, asker, token, tenant, read_on_ingest)`, `_row_to_gesture(row)`, `authorised` dependency, `app.state.{store,asker,token,tenant}` |
| `rig.config` | `Settings` (`RIG_` env prefix): `intent_model`, `mine_model`, `tenant`, `ingest_token`, `daily_usd_cap` |
| tests | `tests/fixtures.py::BATCH` — 7 gestures on `http://127.0.0.1:63319`; the last is a `click` on `itemId=saveButton` carrying 5 requests, two of them `POST` |

## The wire, verbatim

From `docs/14` §3. The rig sends exactly these shapes and nothing else.

```jsonc
// rig → extension
{ "command_id": "cmd_…", "kind": "ui.perform", "run_id": "run_…",
  "deadline_ms": 20000, "payload": { … } }
// extension → rig
{ "command_id": "cmd_…", "ok": true,  "result": { … } }
{ "command_id": "cmd_…", "ok": false, "error": { "kind": "control_not_found", "detail": "…" } }
// unsolicited, extension → rig — dropped, except `busy`
{ "kind": "hello", "extension_version": "0.1.0", "tabs": 12 }
{ "kind": "busy",  "reason": "…", "for_ms": 5000 }
{ "kind": "ping" }
```

| kind | payload | result |
|---|---|---|
| `ui.perform` | `action` (click·type·select·press·upload·scroll·hover), `value`, `locators: [{strategy, query, within: null, visible_only: true}]`, `origin`, `allow_focus` (only when true), `starts_on` | `{performed, matched_by, candidates, detail}` |
| `http.send` | `method, url, headers, body` | `{status, headers, body, duration_ms}` |
| `ui.url` | `{origin}` | `{url}` |
| `screenshot` | `{inline: true, origin, allow_focus}` | `{image_base64, mime_type, width, height, text_digest}` |
| `navigate` | `{url, origin, allow_focus}` | `{navigated}` |
| `abort` | `{run_id}` | `{aborted}` |

Failure kinds the extension answers with: `control_not_found`, `not_visible`,
`not_actionable`, `no_tab_for_system`, `no_tab_for_origin`, `focus_not_permitted`,
`unreachable`, `timeout`, `aborted`.

Locator strategies, in the protocol's priority order: `component`,
`role_and_name` (query is `role|name`), `text`, `test_id`, `css_path`.

## File structure

```
new_agent_arch/src/rig/
  channel.py      NEW  the rig's end of the command channel: one socket per device,
                       send-and-await by command_id, busy, deadline. Mirrors the
                       backend's DeviceSockets, single-tenant.
  runs.py         NEW  Run and RunStep records, the runs/run_steps tables, save/load.
  locators.py     NEW  A13: locators_for(gesture), origin_of(gesture), allowlist(...).
  planner.py      NEW  the Flash call that plans exactly one command for a step.
  verify.py       NEW  A14: status, then a confirming read, then the screen.
  runner.py       NEW  A15: the loop. Dry-run withholding, budget, abort, rescue, stale.
  entry.py        NEW  the chat door: utterance → {workflow_id, values, missing}.
  store.py        MOD  runs + run_steps tables in SCHEMA.
  config.py       MOD  plan_model, rescue_model, command_deadline_s.
  api.py          MOD  WS /v1/agents/{device_id}/commands; POST /v1/runs; GET /v1/runs/{id};
                       POST /v1/runs/{id}/abort; GET /v1/devices; POST /v1/chat.
  web/index.html  MOD  a "run" button per job, the form, the live run.

new-chrome-extension/src/background/
  channel.js      MOD  extracted into createChannel({describe, dial}); the backend
                       instance keeps every export it has today.
  rig-channel.js  NEW  the second instance, dialled at state.rigUrl() with the rig token.
  service-worker.js MOD  rigChannel.settle() beside channel.settle(), same alarm.
  channel.test.mjs  NEW  exactly-once answering, keepalive, redial, both instances.

new_agent_arch/tests/
  test_channel.py  test_runs.py  test_locators.py  test_planner.py
  test_verify.py   test_runner.py  test_entry.py  test_api.py (MOD)
```

---

### Task 1: The rig's end of the command channel

**Files:**
- Create: `new_agent_arch/src/rig/channel.py`
- Modify: `new_agent_arch/src/rig/api.py` (the WebSocket route, after `/v1/health`)
- Modify: `new_agent_arch/src/rig/config.py` (`command_deadline_s`)
- Test: `new_agent_arch/tests/test_channel.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `channel.Answer(ok: bool, result: dict[str, Any], error_kind: str | None, error_detail: str | None)` with `.detail -> str`
  - `channel.Channel` Protocol: `async send(device_id: str, *, kind: str, payload: Mapping[str, object], run_id: str | None = None, deadline_s: float | None = None) -> Answer`; `online() -> list[str]`
  - `channel.DeviceChannel(deadline_s: float = 20.0)` implementing it, plus `attach(device_id, socket)`, `detach(device_id, socket)`, `deliver(raw: str, device_id: str) -> None`
  - `channel.FakeChannel(script: dict[str, list[Answer]] | None = None)` — answers by `kind` in order, records every `sent` envelope; `online()` returns `["dev_test"]`
  - `channel.DeviceUnreachable(Exception)`
  - `app.state.channel` on the FastAPI app, a `DeviceChannel`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_channel.py
import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from rig.api import build_app
from rig.channel import Answer, DeviceChannel, DeviceUnreachable, FakeChannel
from rig.models import FakeAsker
from rig.store import Store

TOKEN = "test-token"


class _Socket:
    """A list, which is all the channel needs a socket to be."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(json.loads(text))


async def test_a_command_is_answered_once_by_id() -> None:
    channel = DeviceChannel(deadline_s=1.0)
    socket = _Socket()
    channel.attach("dev_1", socket)

    task = asyncio.create_task(channel.send("dev_1", kind="ui.url", payload={"origin": "https://a"}))
    await asyncio.sleep(0)
    envelope = socket.sent[0]
    assert envelope["kind"] == "ui.url"
    assert envelope["payload"] == {"origin": "https://a"}
    assert envelope["deadline_ms"] == 1000
    channel.deliver(json.dumps({"command_id": envelope["command_id"], "ok": True, "result": {"url": "https://a/x"}}), "dev_1")

    answer = await task
    assert answer.ok and answer.result == {"url": "https://a/x"}


async def test_an_error_keeps_its_kind_and_detail() -> None:
    channel = DeviceChannel(deadline_s=1.0)
    socket = _Socket()
    channel.attach("dev_1", socket)
    task = asyncio.create_task(channel.send("dev_1", kind="ui.perform", payload={}))
    await asyncio.sleep(0)
    cid = socket.sent[0]["command_id"]
    channel.deliver(json.dumps({"command_id": cid, "ok": False,
                                "error": {"kind": "control_not_found", "detail": "no visible match"}}), "dev_1")

    answer = await task
    assert not answer.ok
    assert answer.error_kind == "control_not_found"
    assert answer.detail == "control_not_found: no visible match"


async def test_no_answer_by_the_deadline_is_a_timeout_not_a_hang() -> None:
    channel = DeviceChannel(deadline_s=0.05)
    channel.attach("dev_1", _Socket())

    answer = await channel.send("dev_1", kind="ui.url", payload={})

    assert not answer.ok and answer.error_kind == "timeout"


async def test_a_late_answer_is_dropped_not_applied() -> None:
    """A run that recorded the step as failed must not have it succeed underneath."""
    channel = DeviceChannel(deadline_s=0.05)
    socket = _Socket()
    channel.attach("dev_1", socket)
    await channel.send("dev_1", kind="ui.url", payload={})
    cid = socket.sent[0]["command_id"]

    channel.deliver(json.dumps({"command_id": cid, "ok": True, "result": {}}), "dev_1")  # must not raise


async def test_a_device_with_no_socket_is_unreachable() -> None:
    channel = DeviceChannel()
    with pytest.raises(DeviceUnreachable):
        await channel.send("dev_nobody", kind="ui.url", payload={})


async def test_busy_holds_a_command_but_cannot_veto_it() -> None:
    """A device asking for politeness must not be able to stop the work."""
    channel = DeviceChannel(deadline_s=0.2)
    socket = _Socket()
    channel.attach("dev_1", socket)
    channel.deliver(json.dumps({"kind": "busy", "for_ms": 60_000}), "dev_1")

    loop = asyncio.get_running_loop()
    started = loop.time()
    task = asyncio.create_task(channel.send("dev_1", kind="ui.url", payload={}))
    await asyncio.sleep(0.15)
    assert socket.sent, "sent within half the deadline, however long the device asked for"
    assert loop.time() - started < 0.2
    channel.deliver(json.dumps({"command_id": socket.sent[0]["command_id"], "ok": True, "result": {}}), "dev_1")
    await task


async def test_a_reconnect_replaces_the_socket_and_a_stale_detach_does_not() -> None:
    channel = DeviceChannel()
    old, new = _Socket(), _Socket()
    channel.attach("dev_1", old)
    channel.attach("dev_1", new)
    channel.detach("dev_1", old)

    assert channel.online() == ["dev_1"], "the live socket survived the stale close"


async def test_unsolicited_messages_are_dropped_on_the_floor() -> None:
    channel = DeviceChannel()
    channel.attach("dev_1", _Socket())
    for raw in ('{"kind":"hello","tabs":3}', '{"kind":"ping"}', "not json", "[]"):
        channel.deliver(raw, "dev_1")  # nothing to assert but that nothing raised


def test_the_route_accepts_the_bearer_subprotocol_and_refuses_the_rest(tmp_path) -> None:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    app = build_app(store=store, asker=FakeAsker(), token=TOKEN, tenant="acme", read_on_ingest=False)
    client = TestClient(app)

    with client.websocket_connect("/v1/agents/dev_1/commands", subprotocols=["bearer", TOKEN]) as ws:
        ws.send_text(json.dumps({"kind": "hello", "extension_version": "0.1.0", "tabs": 1}))
        assert app.state.channel.online() == ["dev_1"]
    assert app.state.channel.online() == []

    with pytest.raises(Exception):  # noqa: B017 -- starlette raises its own disconnect on a refused handshake
        with client.websocket_connect("/v1/agents/dev_1/commands", subprotocols=["bearer", "wrong"]):
            pass


async def test_the_fake_channel_answers_by_kind_and_remembers_what_was_sent() -> None:
    fake = FakeChannel({"ui.url": [Answer(ok=True, result={"url": "https://a/x"})]})

    answer = await fake.send("dev_test", kind="ui.url", payload={"origin": "https://a"})

    assert answer.result == {"url": "https://a/x"}
    assert fake.sent[0]["kind"] == "ui.url"
    unscripted = await fake.send("dev_test", kind="screenshot", payload={})
    assert not unscripted.ok and unscripted.error_kind == "not_actionable"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd new_agent_arch && uv run pytest tests/test_channel.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'rig.channel'`

- [ ] **Step 3: Write `channel.py`**

```python
"""The rig's end of the command channel.

The extension dials out and the rig sends commands down; there is no endpoint
that drives a browser, because one would let a leaked device id reach a browser
that is not the caller's. One command, one answer, correlated by an id this side
mints. The extension answers every command exactly once, including with an
error, and a late answer is discarded rather than applied -- a run that has
already recorded the step as failed must not have it succeed underneath it.

This is the backend's `infrastructure/agent/sockets.py`, single-tenant. It is
written again rather than imported because the rig may not import `sro.*`; the
two must agree on the wire and nothing else.

Held in memory on purpose. A socket does not survive a restart either.
"""

import asyncio
import json
import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

log = logging.getLogger(__name__)

K_COMMAND_DEADLINE_S = 20.0
"""How long a browser has to answer one command. The extension's own timeout
is `deadline_ms` off the envelope, so both ends give up together."""

K_MAX_BUSY_WAIT = 0.5
"""How much of a command's own deadline may be spent waiting for the operator
to stop typing, as a fraction. A device that says it is busy is asking for
politeness, not for a veto."""

_DEFAULT_BUSY_S = 5.0


class DeviceUnreachable(Exception):
    """No socket for that device, or it stopped listening mid-send."""


class Socket(Protocol):
    async def send_text(self, text: str) -> None: ...


@dataclass(frozen=True, slots=True)
class Answer:
    ok: bool
    result: dict[str, Any] = field(default_factory=dict)
    error_kind: str | None = None
    error_detail: str | None = None

    @property
    def detail(self) -> str:
        """What went wrong, keeping the kind the extension named. The kind is
        the machine-readable half; dropping it made `focus_not_permitted`
        indistinguishable from a control that was not there."""
        if self.error_kind and self.error_detail:
            return f"{self.error_kind}: {self.error_detail}"
        return self.error_detail or self.error_kind or ""


class Channel(Protocol):
    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Answer: ...

    def online(self) -> list[str]: ...


class DeviceChannel:
    """Which browsers are connected here, and what they owe an answer to."""

    def __init__(self, deadline_s: float = K_COMMAND_DEADLINE_S) -> None:
        self._deadline = deadline_s
        self._sockets: dict[str, Socket] = {}
        self._pending: dict[str, asyncio.Future[Answer]] = {}
        self._busy_until: dict[str, float] = {}

    # -- the route's side ---------------------------------------------------

    def attach(self, device_id: str, socket: Socket) -> None:
        """A second connection for the same device replaces the first: a
        browser that reconnected after a network drop is the same browser."""
        self._sockets[device_id] = socket

    def detach(self, device_id: str, socket: Socket) -> None:
        """Only if it is still the socket we hold. A slow close arriving after
        a reconnect must not unregister the live one."""
        if self._sockets.get(device_id) is socket:
            del self._sockets[device_id]
            self._busy_until.pop(device_id, None)

    def deliver(self, raw: str, device_id: str) -> None:
        """An answer arrived. Unknown ids are dropped, not raised: a reply to a
        command that already timed out is late, not wrong."""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("device %s sent something that is not JSON", device_id)
            return
        if not isinstance(message, dict):
            return
        if message.get("kind") == "busy":
            seconds = _busy_seconds(message.get("for_ms"))
            self._busy_until[device_id] = asyncio.get_running_loop().time() + seconds
            return
        waiting = self._pending.pop(str(message.get("command_id", "")), None)
        if waiting is None or waiting.done():
            return
        error = message.get("error")
        error = error if isinstance(error, dict) else {}
        result = message.get("result")
        waiting.set_result(
            Answer(
                ok=bool(message.get("ok")),
                result=result if isinstance(result, dict) else {},
                error_kind=str(error["kind"]) if error.get("kind") else None,
                error_detail=str(error["detail"]) if error.get("detail") else None,
            )
        )

    # -- the runner's side --------------------------------------------------

    def online(self) -> list[str]:
        return sorted(self._sockets)

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Answer:
        if device_id not in self._sockets:
            raise DeviceUnreachable(f"{device_id} has no channel open")
        deadline = deadline_s or self._deadline
        await self._wait_out_the_operator(device_id, deadline)
        # Read AFTER the wait: a laptop lid in the middle of it has the
        # extension re-dial, and `attach` replaces the entry.
        socket = self._sockets.get(device_id)
        if socket is None:
            raise DeviceUnreachable(f"{device_id} has no channel open")

        command_id = f"cmd_{uuid.uuid4().hex}"
        waiting: asyncio.Future[Answer] = asyncio.get_running_loop().create_future()
        self._pending[command_id] = waiting
        try:
            await socket.send_text(
                json.dumps(
                    {
                        "command_id": command_id,
                        "kind": kind,
                        "run_id": run_id,
                        "deadline_ms": int(deadline * 1000),
                        "payload": dict(payload),
                    }
                )
            )
        except Exception as broken:
            self._pending.pop(command_id, None)
            raise DeviceUnreachable(f"{device_id} stopped listening") from broken
        try:
            return await asyncio.wait_for(waiting, timeout=deadline)
        except TimeoutError:
            return Answer(
                ok=False,
                error_kind="timeout",
                error_detail=f"the browser did not answer within {deadline:.0f}s",
            )
        finally:
            self._pending.pop(command_id, None)

    async def _wait_out_the_operator(self, device_id: str, deadline: float) -> None:
        until = self._busy_until.get(device_id)
        if until is None:
            return
        loop = asyncio.get_running_loop()
        remaining = until - loop.time()
        if remaining <= 0:
            self._busy_until.pop(device_id, None)
            return
        await asyncio.sleep(min(remaining, deadline * K_MAX_BUSY_WAIT))


def _busy_seconds(for_ms: object) -> float:
    if isinstance(for_ms, int | float) and not isinstance(for_ms, bool) and for_ms > 0:
        return min(float(for_ms) / 1000.0, 60.0)
    return _DEFAULT_BUSY_S


class FakeChannel:
    """Scripted answers by command kind, and a record of every envelope sent.

    The seam every runner test goes through. An unscripted kind answers
    `not_actionable`, which is what a real extension says to a command it does
    not have -- so a test that forgot to script a kind fails the way a real run
    would rather than hanging.
    """

    def __init__(self, script: dict[str, list[Answer]] | None = None) -> None:
        self.script = {kind: list(answers) for kind, answers in (script or {}).items()}
        self.sent: list[dict[str, Any]] = []

    def online(self) -> list[str]:
        return ["dev_test"]

    async def send(
        self,
        device_id: str,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Answer:
        self.sent.append({"device_id": device_id, "kind": kind, "payload": dict(payload), "run_id": run_id})
        queued = self.script.get(kind)
        if queued:
            return queued.pop(0)
        return Answer(ok=False, error_kind="not_actionable", error_detail=f"this extension has no {kind}")
```

- [ ] **Step 4: Add the setting and the route**

In `config.py`, after `daily_usd_cap`:

```python
    plan_model: str = "gemini-3.8-flash"
    """Plans one command per step. Small models match frontier ones at this
    class of inference; a clean step never touches the expensive one."""

    rescue_model: str = "gemini-3.1-pro-preview"
    """Retries a step once, with both screenshots and the failure. Only a step
    that surprised the planner costs what surprises cost."""

    command_deadline_s: float = 20.0
```

In `api.py`, `build_app`: add `from rig.channel import DeviceChannel` at the top of the module; after `app.state.tenant = tenant` add `app.state.channel = DeviceChannel(deadline_s=settings().command_deadline_s)`. Then after the `/v1/health` route:

```python
    @app.websocket("/v1/agents/{device_id}/commands")
    async def commands(websocket: WebSocket, device_id: str) -> None:
        """The extension dials this the way it dials the backend's.

        The credential rides in the subprotocol, not the query string: a
        browser cannot set a header on a WebSocket, and a token in the URL is
        a token in every access log. The rig has one token and no device
        secret -- this is a development second reader, and the boundary is
        that whoever holds the ingest token may drive a browser that has
        chosen to dial here. Refused sockets close with 1008 exactly like a
        wrong token would, so the handshake enumerates nothing.
        """
        protocols = [
            part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")
        ]
        offered = protocols[1] if len(protocols) > 1 and protocols[0] == "bearer" else ""
        if offered != token:
            await websocket.close(code=1008)
            return
        await websocket.accept(subprotocol="bearer")
        channel: DeviceChannel = app.state.channel
        channel.attach(device_id, websocket)
        log.info("device %s connected to the rig", device_id)
        try:
            while True:
                # Named by the route, not by the message: a browser that told
                # the registry which device it was could say it was another.
                channel.deliver(await websocket.receive_text(), device_id)
        except WebSocketDisconnect:
            pass
        finally:
            channel.detach(device_id, websocket)
            log.info("device %s disconnected from the rig", device_id)
```

Add `WebSocket, WebSocketDisconnect` to the `from fastapi import ...` line. `websocket.send_text` already satisfies the `Socket` protocol, so a `WebSocket` is attached directly.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_channel.py -q`
Expected: 10 passed

- [ ] **Step 6: Gates and commit**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run pytest -q
git add src/rig/channel.py src/rig/api.py src/rig/config.py tests/test_channel.py
git commit -m "feat(rig): the rig's end of the command channel"
```

---

### Task 2: The extension dials the rig too

**Files:**
- Modify: `new-chrome-extension/src/background/channel.js` — extract `createChannel`
- Create: `new-chrome-extension/src/background/rig-channel.js`
- Modify: `new-chrome-extension/src/background/service-worker.js` — `rigChannel.settle()` beside every `channel.settle()` / `channel.close()`
- Modify: `Makefile` — `node new-chrome-extension/src/background/channel.test.mjs` in `test-extension`
- Test: `new-chrome-extension/src/background/channel.test.mjs`

**Interfaces:**
- Consumes: `commands.perform(command)`, `state.rigUrl()`, `state.rigToken()`, `state.deviceId()`.
- Produces: `channel.js` keeps every export it has today (`status`, `settle`, `close`, `operatorIsWorking`) for the backend socket, and additionally exports `createChannel({ describe, dial })`. `rig-channel.js` exports `status`, `settle`, `close`.
- **Every command carries its source.** `createChannel` calls `commands.perform(command, describe)`, and `perform(command, source = "backend")` records `source` on `latest` and on `state.setActiveRun({ runId, at, source })`. Task 11 reads it: a run's finish is asked of the process that started it, and a rig run asked of the backend answers 404 and shows "performing" until the quiet timer wipes it.

The socket the rig gets is the backend's socket, verbatim: same keepalive, same
exactly-once answering, same redial. The only differences are where it dials
and what it offers in the subprotocol — the rig has no device secret, so the
subprotocol is `["bearer", rigToken]`. `describe` is the word used in
`state.setLastError` so a failure says which channel failed.

- [ ] **Step 1: Write the failing test**

```javascript
// channel.test.mjs
// Run with `node src/background/channel.test.mjs`.
import assert from "node:assert/strict";
import test from "node:test";

// The minimum of `chrome` these modules touch at import and in the paths under test.
const stored = new Map([
  ["sro.token", "backend-token"],
  ["sro.deviceId", "dev_1"],
  ["sro.deviceSecret", "shh"],
  ["sro.apiUrl", "http://backend:8000"],
  ["sro.rigUrl", "http://rig:8100"],
  ["sro.rigToken", "rig-token"],
]);
globalThis.chrome = {
  runtime: { getManifest: () => ({ version: "0.1.0" }) },
  storage: {
    local: {
      get: async (key) => (stored.has(key) ? { [key]: stored.get(key) } : {}),
      set: async (pairs) => Object.entries(pairs).forEach(([k, v]) => stored.set(k, v)),
      remove: async () => {},
    },
  },
  tabs: { query: async () => [{}, {}] },
};

// A WebSocket that records what was dialled and what was sent, and lets the
// test deliver a message. `readyState` is OPEN from construction so keepalive
// and answers flow without an event loop tick.
const opened = [];
class FakeSocket {
  constructor(url, protocols) {
    this.url = url;
    this.protocols = protocols;
    this.readyState = 1;
    this.sent = [];
    opened.push(this);
    queueMicrotask(() => this.onopen?.());
  }
  send(text) { this.sent.push(JSON.parse(text)); }
  close() { this.readyState = 3; this.onclose?.(); }
  deliver(message) { this.onmessage?.({ data: JSON.stringify(message) }); }
}
FakeSocket.OPEN = 1;
globalThis.WebSocket = FakeSocket;

const commands = await import("./commands.js");
commands.perform = async (command) => ({ ok: true, result: { echoed: command.kind } });
const channel = await import("./channel.js");
const rig = await import("./rig-channel.js");

const settle = () => new Promise((r) => setTimeout(r, 0));

test("the backend channel dials the backend with token and secret", async () => {
  await channel.settle();
  await settle();
  const socket = opened.find((s) => s.url.startsWith("ws://backend:8000"));
  assert.ok(socket, "dialled the backend");
  assert.equal(socket.url, "ws://backend:8000/v1/agents/dev_1/commands");
  assert.deepEqual(socket.protocols, ["bearer", "backend-token", "shh"]);
  assert.equal(socket.sent[0].kind, "hello");
});

test("the rig channel dials the rig with the rig token and no secret", async () => {
  await rig.settle();
  await settle();
  const socket = opened.find((s) => s.url.startsWith("ws://rig:8100"));
  assert.ok(socket, "dialled the rig");
  assert.equal(socket.url, "ws://rig:8100/v1/agents/dev_1/commands");
  assert.deepEqual(socket.protocols, ["bearer", "rig-token"]);
});

test("a command is answered exactly once, on the socket it came in on", async () => {
  await rig.settle();
  await settle();
  const socket = opened.find((s) => s.url.startsWith("ws://rig:8100"));
  socket.deliver({ command_id: "cmd_1", kind: "ui.url", deadline_ms: 1000, payload: {} });
  socket.deliver({ command_id: "cmd_1", kind: "ui.url", deadline_ms: 1000, payload: {} });
  await settle();
  const answers = socket.sent.filter((m) => m.command_id === "cmd_1");
  assert.equal(answers.length, 1, "a duplicate id is not answered twice");
  assert.deepEqual(answers[0], { command_id: "cmd_1", ok: true, result: { echoed: "ui.url" } });
});

test("no rig url means no rig socket, and no error", async () => {
  stored.set("sro.rigUrl", "");
  rig.close();
  const before = opened.length;
  await rig.settle();
  await settle();
  assert.equal(opened.length, before, "nothing dialled");
  assert.equal(rig.status(), "closed");
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node new-chrome-extension/src/background/channel.test.mjs`
Expected: FAIL — `Cannot find module './rig-channel.js'`

- [ ] **Step 3: Extract `createChannel` in `channel.js`**

Turn the module-level state (`socket`, `keepalive`, `retryIn`, `retryTimer`,
`answered`, `lastBusy`) and the functions (`status`, `settle`, `close`, `open`,
`retryLater`, `announce`, `startKeepalive`, `stopKeepalive`, `send`,
`operatorIsWorking`, `handle`) into a factory. The bodies do not change; only
where they read their configuration from.

```javascript
/**
 * One command channel: a socket that dials out, announces itself, keeps
 * itself alive, answers every command exactly once, and redials after a drop.
 *
 * `dial()` answers `{ url, protocols }` or `null` for "do not open one now".
 * `describe` names the channel in error messages. Everything else -- the
 * keepalive, the exactly-once answering, the backoff -- is the same for every
 * channel, which is the point of the factory: the rig gets the backend's
 * socket verbatim, not a second implementation of it.
 */
export function createChannel({ describe, dial }) {
  // `describe` doubles as the run's source: the panel asks the process that
  // started a run how it ended, and only the channel knows which one did.
  let socket = null;
  let keepalive = null;
  let retryIn = FIRST_RETRY_MS;
  let retryTimer = null;
  let answered = new Set();
  let lastBusy = 0;

  function status() { /* unchanged body */ }

  async function settle() {
    const target = await dial();
    if (!target) { close(); return; }
    if (socket) return;
    open(target.url, target.protocols);
  }

  function close() { /* unchanged body */ }

  function open(url, protocols) {
    let opening;
    try {
      opening = new WebSocket(url, protocols);
    } catch (error) {
      void state.setLastError(`the ${describe} command channel could not be opened: ${error}`);
      retryLater();
      return;
    }
    /* the rest unchanged */
  }

  /* retryLater, announce, startKeepalive, stopKeepalive, send, operatorIsWorking,
     handle: unchanged bodies, closing over the variables above, with two edits:
     every `state.setLastError(...)` string gains `${describe}`, and `handle`'s
     `commands.perform(command)` becomes `commands.perform(command, describe)`. */

  return { status, settle, close, operatorIsWorking };
}

// The backend's channel, exactly as before: every export this module had.
const backend = createChannel({
  describe: "backend",
  async dial() {
    const [token, deviceId, secret, serverPaused, apiUrl] = await Promise.all([
      state.token(), state.deviceId(), state.deviceSecret(), state.serverPaused(), state.apiUrl(),
    ]);
    if (!token || !deviceId || !secret || serverPaused) return null;
    return {
      url: `${apiUrl.replace(/^http/, "ws")}/v1/agents/${encodeURIComponent(deviceId)}/commands`,
      protocols: ["bearer", token, secret],
    };
  },
});

export const status = backend.status;
export const settle = backend.settle;
export const close = backend.close;
export const operatorIsWorking = backend.operatorIsWorking;
```

- [ ] **Step 4: Write `rig-channel.js`**

```javascript
/**
 * The same socket, dialled at the rig.
 *
 * The rig is the model-first architecture's own process: it mirrors this
 * browser's uploads already (mirror.js), and a run it starts has to reach a
 * browser too. It gets the backend's channel verbatim -- keepalive,
 * exactly-once answering, backoff -- pointed at `state.rigUrl()`.
 *
 * No device secret: the rig has one token and no device registry, and offers
 * `["bearer", rigToken]`. Empty rig url means what it means for the mirror --
 * nothing is dialled, silently. The rig is optional; its absence is not the
 * extension's problem.
 */
import { createChannel } from "./channel.js";
import { isMirrorable } from "./mirror.js";
import { state } from "./state.js";

const rig = createChannel({
  describe: "rig",
  async dial() {
    const [rigUrl, rigToken, deviceId] = await Promise.all([
      state.rigUrl(), state.rigToken(), state.deviceId(),
    ]);
    if (!isMirrorable(rigUrl) || !rigToken || !deviceId) return null;
    return {
      url: `${rigUrl.replace(/^http/, "ws")}/v1/agents/${encodeURIComponent(deviceId)}/commands`,
      protocols: ["bearer", rigToken],
    };
  },
});

export const status = rig.status;
export const settle = rig.settle;
export const close = rig.close;
```

- [ ] **Step 4b: `commands.perform` records the source**

In `commands.js`, `export async function perform(command, source = "backend")`.
Where `latest` is built for a new run, add `source` to the object; where
`state.setActiveRun({ runId: command.run_id, at: now })` is written, it becomes
`state.setActiveRun({ runId: command.run_id, at: now, source })`. Nothing else
in `perform` changes. Add one test to `channel.test.mjs`: stub
`commands.perform` to record its second argument, deliver a command with
`run_id: "run_r1"` on the rig socket, and assert the recorded source is `"rig"`;
deliver one on the backend socket and assert `"backend"`.

- [ ] **Step 5: Wire it into `service-worker.js`**

`import * as rigChannel from "./rig-channel.js";` beside the `channel` import. Every `void channel.settle();` gains `void rigChannel.settle();` on the next line (the alarm handler and the two `settle()` calls). Every `channel.close();` gains `rigChannel.close();`. The `"rig"` message case that saves `rigUrl`/`rigToken` ends with `void rigChannel.settle();` so a newly configured rig is dialled without waiting for the alarm.

- [ ] **Step 6: Add the test to the Makefile and run everything**

In `Makefile`'s `test-extension` target, add `node new-chrome-extension/src/background/channel.test.mjs` after the `rig-settings.test.mjs` line.

Run: `make test-extension`
Expected: every existing check still passes, plus the four new tests.

- [ ] **Step 7: Commit**

```bash
git add new-chrome-extension/src/background/channel.js new-chrome-extension/src/background/rig-channel.js new-chrome-extension/src/background/service-worker.js new-chrome-extension/src/background/channel.test.mjs Makefile
git commit -m "feat(extension): dial the rig's command channel beside the backend's"
```

---

### Task 3: The Run record

**Files:**
- Create: `new_agent_arch/src/rig/runs.py`
- Modify: `new_agent_arch/src/rig/store.py` — `runs` and `run_steps` in `SCHEMA`
- Test: `new_agent_arch/tests/test_runs.py`

**Interfaces:**
- Produces:
  - `runs.new_run_id() -> str` (`run_` + 32 hex)
  - `runs.RunStep(order, says, planned_by, sent, result, verdict, verdict_by, reason, matched_by, stale, before_url, after_url, in_tokens, out_tokens, thought_tokens, cost_usd, unpriced)`
  - `runs.Run(id, tenant, workflow_id, device_id, values, started_by, live, allow_focus, started_at, finished_at, outcome, steps, withheld, in_tokens, out_tokens, thought_tokens, cost_usd, unpriced)`
  - `runs.save_run(store, run)`, `runs.load_run(store, tenant, run_id) -> Run | None`, `runs.runs_for(store, tenant, workflow_id) -> list[Run]`
  - `runs.OUTCOMES = ("running", "held", "stopped", "refused", "aborted", "failed")`
  - `runs.VERDICTS = ("held", "failed", "unclear", "withheld", "refused", "skipped")`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runs.py
from pathlib import Path

from rig.runs import OUTCOMES, VERDICTS, Run, RunStep, load_run, new_run_id, runs_for, save_run
from rig.store import Store


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def _run(**over) -> Run:
    base = dict(
        id=new_run_id(), tenant="acme", workflow_id="wfl_1", device_id="dev_1",
        values={"workArea": "THIRD"}, started_by="form", live=False, allow_focus=True,
        started_at="2026-09-05T10:00:00+00:00", finished_at=None, outcome="running",
        steps=[], withheld=[],
    )
    return Run(**{**base, **over})


def test_a_run_id_has_the_shape_the_other_ids_have() -> None:
    assert new_run_id().startswith("run_") and len(new_run_id()) == 36


def test_a_run_round_trips_with_every_step_and_every_withheld_write(tmp_path: Path) -> None:
    store = _store(tmp_path)
    run = _run(
        steps=[
            RunStep(order=0, says="type the code", planned_by="gemini-3.8-flash",
                    sent={"kind": "ui.perform", "payload": {"action": "type", "value": "THIRD"}},
                    result={"performed": True, "matched_by": "component", "candidates": 1},
                    verdict="held", verdict_by="screen", reason="the field shows THIRD",
                    matched_by="component", stale=False,
                    before_url="https://wms/x", after_url="https://wms/x",
                    in_tokens=300, out_tokens=40, thought_tokens=10, cost_usd=0.0004, unpriced=False),
            RunStep(order=1, says="save", planned_by="gemini-3.8-flash",
                    sent={"kind": "ui.perform", "payload": {"action": "click"}},
                    result={"withheld": True},
                    verdict="withheld", verdict_by="dry", reason="a dry run does not send writes",
                    matched_by=None, stale=False, before_url=None, after_url=None),
        ],
        withheld=[{"step": 1, "method": "POST", "url": "https://wms/data/WM/wm/workAreas",
                   "body": '{"workArea":"THIRD"}'}],
        outcome="held", finished_at="2026-09-05T10:01:00+00:00",
        in_tokens=300, out_tokens=40, thought_tokens=10, cost_usd=0.0004,
    )

    save_run(store, run)
    back = load_run(store, "acme", run.id)

    assert back == run
    assert runs_for(store, "acme", "wfl_1") == [run]
    assert load_run(store, "acme", "run_nobody") is None


def test_saving_again_replaces_the_steps_rather_than_appending(tmp_path: Path) -> None:
    """A run is saved after every step so the page can poll it; the second
    save must not double the first step."""
    store = _store(tmp_path)
    run = _run(steps=[RunStep(order=0, says="a", verdict="held", verdict_by="status", reason="")])
    save_run(store, run)
    run.steps.append(RunStep(order=1, says="b", verdict="held", verdict_by="status", reason=""))
    save_run(store, run)

    assert [s.order for s in load_run(store, "acme", run.id).steps] == [0, 1]


def test_the_vocabularies_are_closed() -> None:
    assert "running" in OUTCOMES and "withheld" in VERDICTS
```

- [ ] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/test_runs.py -q`
Expected: FAIL — `No module named 'rig.runs'`

- [ ] **Step 3: Add the tables to `store.py`**

Append to `SCHEMA`, after `workflow_steps`:

```sql
CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    tenant      TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    values_json TEXT NOT NULL DEFAULT '{}',
    started_by  TEXT NOT NULL DEFAULT '',
    live        INTEGER NOT NULL DEFAULT 0,
    allow_focus INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    outcome     TEXT NOT NULL DEFAULT 'running',
    -- The writes a dry run produced and did not send, in full. This is what a
    -- person reads before pressing through to live.
    withheld    TEXT NOT NULL DEFAULT '[]',
    in_tokens   INTEGER NOT NULL DEFAULT 0,
    out_tokens  INTEGER NOT NULL DEFAULT 0,
    thought_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd    REAL NOT NULL DEFAULT 0.0,
    unpriced    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS runs_tenant ON runs (tenant, workflow_id, started_at);

CREATE TABLE IF NOT EXISTS run_steps (
    run_id      TEXT NOT NULL,
    ord         INTEGER NOT NULL,
    says        TEXT NOT NULL DEFAULT '',
    planned_by  TEXT,
    sent        TEXT,             -- the command envelope's kind and payload, JSON
    result      TEXT,             -- what the extension answered, JSON
    verdict     TEXT NOT NULL,
    verdict_by  TEXT NOT NULL DEFAULT '',
    reason      TEXT NOT NULL DEFAULT '',
    matched_by  TEXT,
    stale       INTEGER NOT NULL DEFAULT 0,
    before_url  TEXT,
    after_url   TEXT,
    in_tokens   INTEGER NOT NULL DEFAULT 0,
    out_tokens  INTEGER NOT NULL DEFAULT 0,
    thought_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd    REAL NOT NULL DEFAULT 0.0,
    unpriced    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, ord)
);
```

- [ ] **Step 4: Write `runs.py`**

```python
"""What a run leaves behind. *Why did it do that* has a file."""

import json
import secrets
from dataclasses import asdict, dataclass, field
from typing import Any

from rig.store import Store

OUTCOMES = ("running", "held", "stopped", "refused", "aborted", "failed")
"""running: in flight. held: every step held. stopped: a step failed twice and
the run stopped to ask. refused: a planned command named an origin outside the
allowlist, or the step budget ran out. aborted: the stop button. failed: the
browser went away."""

VERDICTS = ("held", "failed", "unclear", "withheld", "refused", "skipped")


def new_run_id() -> str:
    return "run_" + secrets.token_hex(16)


@dataclass
class RunStep:
    order: int
    says: str
    verdict: str
    verdict_by: str = ""
    reason: str = ""
    planned_by: str | None = None
    sent: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    matched_by: str | None = None
    stale: bool = False
    before_url: str | None = None
    after_url: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False


@dataclass
class Run:
    id: str
    tenant: str
    workflow_id: str
    device_id: str
    values: dict[str, str]
    started_by: str
    live: bool
    allow_focus: bool
    started_at: str
    finished_at: str | None = None
    outcome: str = "running"
    steps: list[RunStep] = field(default_factory=list)
    withheld: list[dict[str, Any]] = field(default_factory=list)
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False


def save_run(store: Store, run: Run) -> None:
    """Whole run, every time. Called after every step so the page can poll;
    steps are replaced rather than appended so the second save does not double
    the first step."""
    with store.connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO runs (id, tenant, workflow_id, device_id, values_json,"
            " started_by, live, allow_focus, started_at, finished_at, outcome, withheld,"
            " in_tokens, out_tokens, thought_tokens, cost_usd, unpriced)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run.id, run.tenant, run.workflow_id, run.device_id,
                json.dumps(run.values, ensure_ascii=False), run.started_by,
                int(run.live), int(run.allow_focus), run.started_at, run.finished_at,
                run.outcome, json.dumps(run.withheld, ensure_ascii=False),
                run.in_tokens, run.out_tokens, run.thought_tokens, run.cost_usd, int(run.unpriced),
            ),
        )
        connection.execute("DELETE FROM run_steps WHERE run_id = ?", (run.id,))
        for step in run.steps:
            connection.execute(
                "INSERT INTO run_steps (run_id, ord, says, planned_by, sent, result, verdict,"
                " verdict_by, reason, matched_by, stale, before_url, after_url,"
                " in_tokens, out_tokens, thought_tokens, cost_usd, unpriced)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run.id, step.order, step.says, step.planned_by,
                    json.dumps(step.sent, ensure_ascii=False) if step.sent is not None else None,
                    json.dumps(step.result, ensure_ascii=False) if step.result is not None else None,
                    step.verdict, step.verdict_by, step.reason, step.matched_by, int(step.stale),
                    step.before_url, step.after_url,
                    step.in_tokens, step.out_tokens, step.thought_tokens, step.cost_usd, int(step.unpriced),
                ),
            )


def _step(row: Any) -> RunStep:
    return RunStep(
        order=row["ord"], says=row["says"], verdict=row["verdict"], verdict_by=row["verdict_by"],
        reason=row["reason"], planned_by=row["planned_by"],
        sent=json.loads(row["sent"]) if row["sent"] else None,
        result=json.loads(row["result"]) if row["result"] else None,
        matched_by=row["matched_by"], stale=bool(row["stale"]),
        before_url=row["before_url"], after_url=row["after_url"],
        in_tokens=row["in_tokens"], out_tokens=row["out_tokens"], thought_tokens=row["thought_tokens"],
        cost_usd=row["cost_usd"], unpriced=bool(row["unpriced"]),
    )


def _run(store: Store, row: Any) -> Run:
    steps = [_step(s) for s in store.query(
        "SELECT * FROM run_steps WHERE run_id = ? ORDER BY ord", (row["id"],))]
    return Run(
        id=row["id"], tenant=row["tenant"], workflow_id=row["workflow_id"], device_id=row["device_id"],
        values=json.loads(row["values_json"]), started_by=row["started_by"],
        live=bool(row["live"]), allow_focus=bool(row["allow_focus"]),
        started_at=row["started_at"], finished_at=row["finished_at"], outcome=row["outcome"],
        steps=steps, withheld=json.loads(row["withheld"]),
        in_tokens=row["in_tokens"], out_tokens=row["out_tokens"], thought_tokens=row["thought_tokens"],
        cost_usd=row["cost_usd"], unpriced=bool(row["unpriced"]),
    )


def load_run(store: Store, tenant: str, run_id: str) -> Run | None:
    rows = store.query("SELECT * FROM runs WHERE tenant = ? AND id = ?", (tenant, run_id))
    return _run(store, rows[0]) if rows else None


def runs_for(store: Store, tenant: str, workflow_id: str) -> list[Run]:
    return [_run(store, r) for r in store.query(
        "SELECT * FROM runs WHERE tenant = ? AND workflow_id = ? ORDER BY started_at", (tenant, workflow_id))]


def as_json(run: Run) -> dict[str, Any]:
    """The route's view. `asdict` is exact here because nothing in a Run is a
    type json cannot carry."""
    return asdict(run)
```

- [ ] **Step 5: Run the tests, gates, commit**

Run: `uv run pytest tests/test_runs.py tests/test_store.py -q` — Expected: all pass (the store test's migration check must still hold with the new tables).

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run pytest -q
git add src/rig/runs.py src/rig/store.py tests/test_runs.py
git commit -m "feat(rig): the Run record -- what a run leaves behind"
```

---

### Task 4: Locators, origin, allowlist (A13)

**Files:**
- Create: `new_agent_arch/src/rig/locators.py`
- Test: `new_agent_arch/tests/test_locators.py`

**Interfaces:**
- Consumes: `rig.records.Gesture`, `rig.wire.Target`, `rig.correlate.system_of`, `rig.workflows.Workflow`, `rig.wire.REDACTED`.
- Produces:
  - `locators.locators_for(gesture: Gesture) -> list[dict[str, Any]]` — protocol shape, priority order
  - `locators.origin_of(gesture: Gesture) -> str | None` — **the page first** (`gesture.system`, else `system_of(gesture.url)`), then the first request that *completed* and names a system, then any request naming one. Ruled during execution: every consumer of `origin` is about the tab the operator was on, and request-first steered a run at a dead host when a failed call was earliest.
  - `locators.allowlist(workflow: Workflow, by_id: Mapping[str, Gesture]) -> set[str]`
  - `locators.primary_gesture(step: Step, by_id) -> Gesture | None` — first cited gesture that exists and is not a scroll
  - `locators.writes(step: Step, by_id) -> bool` — any cited gesture carries a non-GET request
  - `locators.recorded_call(step: Step, by_id) -> Request | None` — the first non-GET request a cited gesture carries, else the first request at all

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_locators.py
import copy

from rig.correlate import correlate
from rig.locators import allowlist, locators_for, origin_of, primary_gesture, recorded_call, writes
from rig.wire import Batch
from rig.workflows import Step, Workflow
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def test_the_ladder_is_the_protocols_and_in_its_order() -> None:
    save = next(g for g in _gestures() if g.gesture.target and g.gesture.target.component
                and g.gesture.target.component.itemId == "saveButton")
    t = save.gesture.target
    t.role, t.name, t.text, t.testId, t.cssPath = "button", "Save", "Save", "save-btn", "div > button"
    t.component.query = "button#saveButton"

    ladder = locators_for(save)

    assert [l["strategy"] for l in ladder] == ["component", "role_and_name", "text", "test_id", "css_path"]
    assert ladder[0]["query"] == "button#saveButton"
    assert ladder[1]["query"] == "button|Save"
    assert all(l["within"] is None and l["visible_only"] is True for l in ladder)


def test_an_item_id_alone_is_still_a_component_query() -> None:
    g = copy.deepcopy(_gestures()[0])
    g.gesture.target.component.query = None
    assert locators_for(g)[0] == {"strategy": "component", "query": "#clientCode", "within": None, "visible_only": True}


def test_a_scroll_has_no_ladder_and_a_step_citing_only_scrolls_has_no_primary() -> None:
    g = copy.deepcopy(_gestures()[0])
    g.gesture.kind, g.gesture.target = "scroll", None
    assert locators_for(g) == []
    assert primary_gesture(Step(order=0, says="scroll", system=None, cites=[g.id]), {g.id: g}) is None


def test_origin_prefers_the_call_and_falls_back_to_the_page() -> None:
    gestures = _gestures()
    with_calls = next(g for g in gestures if g.requests)
    without = next(g for g in gestures if not g.requests)
    with_calls.requests[0].url = "https://wms.example/data/x"
    assert origin_of(with_calls) == "https://wms.example"
    assert origin_of(without) == "http://127.0.0.1:63319"


def test_the_allowlist_is_every_system_the_evidence_names_and_nothing_else() -> None:
    gestures = _gestures()
    by_id = {g.id: g}
    by_id = {g.id: g for g in gestures}
    saver = next(g for g in gestures if g.requests)
    saver.requests[0].url = "https://wms.example/data/x"
    wf = Workflow(id="wfl_1", tenant="acme", title="t", narrative="n",
                  steps=[Step(order=0, says="s", system=None, cites=[g.id for g in gestures])])

    assert allowlist(wf, by_id) == {"http://127.0.0.1:63319", "https://wms.example"}


def test_a_step_writes_when_any_cited_gesture_caused_a_mutation() -> None:
    gestures = _gestures()
    by_id = {g.id: g for g in gestures}
    saver = next(g for g in gestures if g.requests)
    typer = next(g for g in gestures if not g.requests)
    assert writes(Step(order=0, says="save", system=None, cites=[saver.id]), by_id)
    assert not writes(Step(order=0, says="type", system=None, cites=[typer.id]), by_id)
    assert recorded_call(Step(order=0, says="save", system=None, cites=[saver.id]), by_id).method == "POST"
```

- [ ] **Step 2: Run to verify they fail** — `uv run pytest tests/test_locators.py -q` → `No module named 'rig.locators'`

- [ ] **Step 3: Write `locators.py`**

```python
"""A13: what a step knows before any model is asked.

A step cites gestures; those gestures carry recorder.js fingerprints; so the
locator list the protocol wants is built from the cited evidence with no model
involved, in the protocol's own priority order. `origin` is per step, from that
step's own evidence -- in a job spanning two systems the Blue Yonder steps carry
Blue Yonder's origin and the SAP step carries SAP's. A documented
cross-application agent failure is losing window focus during a hand-off, so
data meant for the second application is typed into the first; this is what
stops it.
"""

from collections.abc import Mapping
from typing import Any

from rig.correlate import system_of
from rig.records import Gesture
from rig.wire import Request
from rig.workflows import Step, Workflow

_UNTARGETED = frozenset({"scroll"})


def _locator(strategy: str, query: str) -> dict[str, Any]:
    return {"strategy": strategy, "query": query, "within": None, "visible_only": True}


def locators_for(gesture: Gesture) -> list[dict[str, Any]]:
    """The ladder, strongest first: the framework's own handle, then role and
    name, then visible text, then the test id, then the css path the protocol
    calls a last resort. A gesture with no target -- a scroll -- has no ladder."""
    target = gesture.gesture.target
    if target is None:
        return []
    ladder: list[dict[str, Any]] = []
    component = target.component
    if component is not None:
        query = component.query or (f"#{component.itemId}" if component.itemId else None)
        if query:
            ladder.append(_locator("component", query))
    if target.role and target.name:
        ladder.append(_locator("role_and_name", f"{target.role}|{target.name}"))
    if target.text:
        ladder.append(_locator("text", target.text))
    if target.testId:
        ladder.append(_locator("test_id", target.testId))
    if target.cssPath:
        ladder.append(_locator("css_path", target.cssPath))
    return ladder


def origin_of(gesture: Gesture) -> str | None:
    """Scheme and host of the first call that names a system, else of the page."""
    for request in gesture.requests:
        system = system_of(request.url)
        if system:
            return system
    return gesture.system or system_of(gesture.url)


def primary_gesture(step: Step, by_id: Mapping[str, Gesture]) -> Gesture | None:
    """The first cited gesture that exists and can be acted on."""
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is not None and gesture.gesture.kind not in _UNTARGETED:
            return gesture
    return None


def recorded_call(step: Step, by_id: Mapping[str, Gesture]) -> Request | None:
    """The call this step's evidence made: the first mutation, else the first
    call at all. What `http.send` would replay, and what `verify` reads an
    expected status from."""
    reads: list[Request] = []
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() not in ("GET", "HEAD", "OPTIONS"):
                return request
            reads.append(request)
    return reads[0] if reads else None


def writes(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    """Whether performing this step changes something. A dry run withholds it."""
    call = recorded_call(step, by_id)
    return call is not None and call.method.upper() not in ("GET", "HEAD", "OPTIONS")


def allowlist(workflow: Workflow, by_id: Mapping[str, Gesture]) -> set[str]:
    """Every system the workflow's own cited evidence names. A planned command
    to any other origin is refused before it leaves the process."""
    named: set[str] = set()
    for step in workflow.steps:
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None:
                continue
            for candidate in (gesture.system, system_of(gesture.url)):
                if candidate:
                    named.add(candidate)
            for request in gesture.requests:
                system = system_of(request.url)
                if system:
                    named.add(system)
    return named
```

- [ ] **Step 4: Run, gates, commit**

```bash
uv run pytest tests/test_locators.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run mypy src
git add src/rig/locators.py tests/test_locators.py
git commit -m "feat(rig): A13 -- locators, origin and the allowlist, from evidence alone"
```

---

### Task 5: The planner — Flash plans exactly one command

**Files:**
- Create: `new_agent_arch/src/rig/planner.py`
- Test: `new_agent_arch/tests/test_planner.py`

**Interfaces:**
- Consumes: `Asker`, `Answer`, `trim(gesture)`, `locators_for`, `origin_of`, `recorded_call`, `REDACTED`.
- Produces:
  - `planner.Look(url: str | None, screenshot: bytes | None, digest: str)`
  - `planner.Planned(kind: str, payload: dict[str, Any], why: str, answer: Answer)` — `kind in {"ui.perform", "http.send", "navigate", "none"}`; `"none"` when the model could not plan (answer has an error)
  - `planner.PLAN_SCHEMA`, `planner.INSTRUCTIONS`
  - `async planner.plan_step(*, step, cited: list[Gesture], values: Mapping[str, str], look: Look, origin: str | None, starts_on: str | None, allow_focus: bool, asker, model, effort=None, failure: str | None = None) -> Planned`

The model answers a **small** shape — which kind, which action, which value,
which url — and the rig assembles the payload. The locators never come from the
model: they are A13's, from evidence. The model may only choose between them by
not choosing at all; the extension tries them in order.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_planner.py
from rig.correlate import correlate
from rig.models import Answer, FakeAsker
from rig.planner import PLAN_SCHEMA, Look, plan_step
from rig.wire import Batch
from rig.workflows import Step
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def _typed():
    return next(g for g in _gestures() if g.gesture.kind == "type" and not g.gesture.secret)


async def test_a_ui_plan_carries_the_evidence_locators_not_the_models() -> None:
    gesture = _typed()
    asker = FakeAsker(Answer(data={"kind": "ui.perform", "action": "type", "value": "THIRD",
                                    "url": None, "why": "the step types the code"}, cost_usd=0.0003))

    planned = await plan_step(
        step=Step(order=0, says="type the code", system=None, cites=[gesture.id]),
        cited=[gesture], values={"clientCode": "THIRD"}, look=Look(url="http://127.0.0.1:63319/", screenshot=None, digest=""),
        origin="http://127.0.0.1:63319", starts_on=None, allow_focus=True, asker=asker, model="gemini-3.8-flash",
    )

    assert planned.kind == "ui.perform"
    assert planned.payload["action"] == "type" and planned.payload["value"] == "THIRD"
    assert planned.payload["locators"][0] == {"strategy": "component", "query": "panel#clients textfield#clientCode", "within": None, "visible_only": True}
    assert planned.payload["origin"] == "http://127.0.0.1:63319"
    assert planned.payload["allow_focus"] is True
    assert planned.answer.cost_usd == 0.0003


async def test_the_values_the_run_was_given_are_what_the_model_sees_not_the_recorded_ones() -> None:
    gesture = _typed()
    asker = FakeAsker(Answer(data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""}))
    await plan_step(step=Step(order=0, says="type", system=None, cites=[gesture.id]), cited=[gesture],
                    values={"clientCode": "THIRD"}, look=Look(None, None, ""), origin=None, starts_on=None,
                    allow_focus=False, asker=asker, model="m")
    assert "THIRD" in asker.asked[0]["evidence"]
    assert "allow_focus" not in asker.asked[0]["evidence"], "nothing about focus reaches the model"
    assert "http://127.0.0.1:63319/" in asker.asked[0]["evidence"], "the step's real page, for a deep job"


async def test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped() -> None:
    saver = next(g for g in _gestures() if g.requests)
    post = next(r for r in saver.requests if r.method == "POST")
    post.request_headers = {"Content-Type": "application/json", "CSRF-ENCRYPT-TOKEN": "«redacted»"}
    asker = FakeAsker(Answer(data={"kind": "http.send", "action": None, "value": None, "url": None, "why": "no ui target"}))

    planned = await plan_step(step=Step(order=0, says="save", system=None, cites=[saver.id]), cited=[saver],
                              values={}, look=Look(None, None, ""), origin=None, starts_on=None,
                              allow_focus=False, asker=asker, model="m")

    assert planned.kind == "http.send"
    assert planned.payload["method"] == "POST" and planned.payload["url"] == post.url
    assert "CSRF-ENCRYPT-TOKEN" not in planned.payload["headers"], "a marker is never sent as a header"
    assert planned.payload["headers"]["Content-Type"] == "application/json"


async def test_a_model_that_could_not_answer_plans_nothing_and_says_why() -> None:
    gesture = _typed()
    planned = await plan_step(step=Step(order=0, says="type", system=None, cites=[gesture.id]), cited=[gesture],
                              values={}, look=Look(None, None, ""), origin=None, starts_on=None, allow_focus=False,
                              asker=FakeAsker(Answer(error="boom", unpriced=True)), model="m")
    assert planned.kind == "none" and "boom" in planned.why


async def test_a_kind_the_protocol_does_not_have_is_planned_as_nothing() -> None:
    gesture = _typed()
    planned = await plan_step(step=Step(order=0, says="type", system=None, cites=[gesture.id]), cited=[gesture],
                              values={}, look=Look(None, None, ""), origin=None, starts_on=None, allow_focus=False,
                              asker=FakeAsker(Answer(data={"kind": "rm -rf", "action": None, "value": None, "url": None, "why": ""})), model="m")
    assert planned.kind == "none"


async def test_a_retry_carries_the_failure_and_the_second_screenshot() -> None:
    gesture = _typed()
    asker = FakeAsker(Answer(data={"kind": "navigate", "action": None, "value": None, "url": "http://127.0.0.1:63319/form", "why": "wrong page"}))
    planned = await plan_step(step=Step(order=0, says="type", system=None, cites=[gesture.id]), cited=[gesture],
                              values={}, look=Look("http://127.0.0.1:63319/", b"\x89PNG", "Save"), origin="http://127.0.0.1:63319",
                              starts_on=None, allow_focus=True, asker=asker, model="m", failure="control_not_found: no visible match")
    assert "control_not_found" in asker.asked[0]["evidence"]
    assert asker.asked[0]["image"] == b"\x89PNG"
    assert planned.kind == "navigate" and planned.payload == {"url": "http://127.0.0.1:63319/form", "origin": "http://127.0.0.1:63319", "allow_focus": True}


def test_the_schema_puts_why_last_and_kind_first() -> None:
    """Decide before explaining: identifying the command before composing the
    reason measurably beats composing first."""
    assert list(PLAN_SCHEMA["properties"]) == ["kind", "action", "value", "url", "why"]
```

- [ ] **Step 2: Run to verify they fail** — `uv run pytest tests/test_planner.py -q`

- [ ] **Step 3: Write `planner.py`**

```python
"""Flash plans exactly one command for one step.

The model answers a small shape -- which kind of command, which action, which
value, which url -- and the rig assembles the payload. The locators never come
from the model: they are A13's, built from the cited evidence, and the
extension tries them in order. What the model decides is only what to do with
them, and it is told to prefer driving the interface over replaying a call.

That preference was measured, not assumed. 544 of the real store's request
headers are CSRF tokens, every one redacted at the rig's boundary. An
`http.send` replaying the recorded call would send the marker as its token and
be refused; clicking Save lets the page mint its own. So `http.send` is for a
step whose evidence carries a call and no usable target -- and a header whose
stored value is the redaction marker is never sent under any plan.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rig.locators import locators_for, recorded_call
from rig.models import Answer, Asker, Effort
from rig.records import Gesture
from rig.trim import trim
from rig.wire import REDACTED
from rig.workflows import Step

KINDS = frozenset({"ui.perform", "http.send", "navigate"})
ACTIONS = frozenset({"click", "type", "select", "press", "upload", "scroll", "hover"})

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    # kind first, why last: decide, then explain.
    "properties": {
        "kind": {"type": "string", "enum": ["ui.perform", "http.send", "navigate"]},
        "action": {"type": "string", "nullable": True,
                   "enum": ["click", "type", "select", "press", "upload", "scroll", "hover"]},
        "value": {"type": "string", "nullable": True},
        "url": {"type": "string", "nullable": True},
        "why": {"type": "string"},
    },
    "required": ["kind", "why"],
    "propertyOrdering": ["kind", "action", "value", "url", "why"],
}

INSTRUCTIONS = """You are performing one step of a job an operator demonstrated in a warehouse
system, in their own browser. You are given the step's sentence, the evidence
it was read from (the gesture the operator made and any calls the page sent),
the values this run was given, and where the browser is now.

Plan exactly ONE command:
- ui.perform: act on the control the evidence points at. Give the action and,
  for type/select/upload, the value from this run's values. Prefer this.
- http.send: only when the evidence carries a call and there is no usable
  control to drive. The call itself is taken from the evidence.
- navigate: only when the browser is on the wrong page for this step -- compare
  `browser.url` with `step_page`, the screen this step was demonstrated on.
  Give the url. After a navigate the same step is planned again.

Never invent a control, a url or a value that is not in the evidence or the
run's values. If the step cannot be done from what you are shown, say so in
`why` and choose the kind that gets closest."""


@dataclass(frozen=True, slots=True)
class Look:
    url: str | None
    screenshot: bytes | None
    digest: str


@dataclass(frozen=True, slots=True)
class Planned:
    kind: str
    payload: dict[str, Any]
    why: str
    answer: Answer


def _value_for(step: Step, gesture: Gesture, values: Mapping[str, str], said: str | None) -> str | None:
    """The run's value for this control, else what the model said, else what
    was recorded. The run's values win: they are what the person asked for."""
    target = gesture.gesture.target
    component = target.component if target else None
    for name in (
        component.itemId if component else None,
        component.fieldLabel if component else None,
        target.name if target else None,
        *step.parameters,
    ):
        if name and name in values:
            return values[name]
    if said:
        return said
    return gesture.gesture.value


def _headers_without_markers(headers: Mapping[str, str]) -> dict[str, str]:
    return {name: value for name, value in headers.items() if REDACTED not in value}


async def plan_step(
    *,
    step: Step,
    cited: list[Gesture],
    values: Mapping[str, str],
    look: Look,
    origin: str | None,
    starts_on: str | None,
    allow_focus: bool,
    asker: Asker,
    model: str,
    effort: Effort | None = None,
    failure: str | None = None,
) -> Planned:
    primary = next((g for g in cited if g.gesture.kind != "scroll"), cited[0] if cited else None)
    evidence = json.dumps(
        {
            "step": {"order": step.order, "says": step.says, "parameters": step.parameters},
            "evidence": [trim(g) for g in cited],
            "values": dict(values),
            "browser": {"url": look.url, "screen_text": look.digest},
            # The real page, not `trim()`'s starred path shape: a step deep in a
            # job was demonstrated on a specific screen, and the planner can only
            # say "navigate there first" if it is told where there is.
            "step_page": primary.page_url or primary.url,
            "previous_attempt_failed": failure,
        },
        indent=2,
        ensure_ascii=False,
    )
    answer = await asker.ask(
        model=model, instructions=INSTRUCTIONS, evidence=evidence, schema=PLAN_SCHEMA,
        image=look.screenshot, effort=effort,
    )
    if answer.data is None or primary is None:
        return Planned("none", {}, answer.error or "no evidence to act on", answer)

    data = answer.data
    kind = data.get("kind")
    why = str(data.get("why") or "")
    if kind not in KINDS:
        return Planned("none", {}, f"the model planned a command the protocol does not have: {kind!r}", answer)

    if kind == "navigate":
        url = data.get("url")
        if not isinstance(url, str) or not url:
            return Planned("none", {}, "navigate with no url", answer)
        return Planned("navigate", {"url": url, "origin": origin, "allow_focus": allow_focus}, why, answer)

    if kind == "http.send":
        call = recorded_call(step, {g.id: g for g in cited})
        if call is None:
            return Planned("none", {}, "http.send planned for a step whose evidence carries no call", answer)
        body = call.request_body.text if call.request_body and call.request_body.text else None
        return Planned(
            "http.send",
            {"method": call.method.upper(), "url": call.url,
             "headers": _headers_without_markers(call.request_headers), "body": body},
            why, answer,
        )

    action = data.get("action") if data.get("action") in ACTIONS else primary.gesture.kind
    payload: dict[str, Any] = {
        "action": action,
        "value": _value_for(step, primary, values, data.get("value")) if action in ("type", "select", "upload", "press") else None,
        "locators": locators_for(primary),
        "origin": origin,
    }
    if allow_focus:
        payload["allow_focus"] = True
    if starts_on:
        payload["starts_on"] = starts_on
    return Planned("ui.perform", payload, why, answer)
```

- [ ] **Step 4: Run, gates, commit**

```bash
uv run pytest tests/test_planner.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run mypy src
git add src/rig/planner.py tests/test_planner.py
git commit -m "feat(rig): the planner -- Flash plans one command, the evidence supplies the locators"
```

---

### Task 6: Verify against state before a picture (A14)

**Files:**
- Create: `new_agent_arch/src/rig/verify.py`
- Test: `new_agent_arch/tests/test_verify.py`

**Interfaces:**
- Consumes: `channel.Channel`, `channel.Answer`, `Asker`, `recorded_call`, `Look`.
- Produces:
  - `verify.Verdict(state: str, by: str, reason: str, answer: Answer | None)` — `state in {"held","failed","unclear"}`, `by in {"status","read","screen","none"}`
  - `verify.VERDICT_SCHEMA`
  - `verify.expected_statuses(step, by_id) -> set[int]`
  - `verify.confirming_read(step, by_id) -> Request | None` — a GET a cited gesture made after its write
  - `async verify.verify(*, step, sent_kind, answer: channel.Answer, cited, values, look_before, look_after, channel, device_id, run_id, origin, asker, model) -> Verdict`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_verify.py
from rig.channel import Answer as Reply
from rig.channel import FakeChannel
from rig.correlate import correlate
from rig.models import Answer, FakeAsker
from rig.planner import Look
from rig.verify import confirming_read, expected_statuses, verify
from rig.wire import Batch
from rig.workflows import Step
from tests.fixtures import BATCH


def _saver():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return next(g for g in gestures if g.requests)


def _step(g):
    return Step(order=0, says="save", system=None, cites=[g.id])


async def test_a_call_that_returned_the_status_the_evidence_expects_is_held_by_status() -> None:
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    post.status = 201
    asker = FakeAsker()

    verdict = await verify(step=_step(saver), sent_kind="http.send", answer=Reply(ok=True, result={"status": 201, "body": "{}"}),
                           cited=[saver], values={}, look_before=Look(None, None, ""), look_after=Look(None, None, ""),
                           channel=FakeChannel(), device_id="dev_test", run_id="run_1", origin=None, asker=asker, model="m")

    assert (verdict.state, verdict.by) == ("held", "status")
    assert asker.asked == [], "no model was asked when the state already said"


async def test_a_call_the_warehouse_rejected_is_failed_by_status() -> None:
    saver = _saver()
    verdict = await verify(step=_step(saver), sent_kind="http.send", answer=Reply(ok=True, result={"status": 422, "body": "no"}),
                           cited=[saver], values={}, look_before=Look(None, None, ""), look_after=Look(None, None, ""),
                           channel=FakeChannel(), device_id="dev_test", run_id="run_1", origin=None, asker=FakeAsker(), model="m")
    assert (verdict.state, verdict.by) == ("failed", "status") and "422" in verdict.reason


async def test_a_ui_step_is_confirmed_by_the_read_the_evidence_shows_the_page_makes() -> None:
    """Hidden state before visible state: the read comes back with the value
    the run supplied, and no screenshot is looked at."""
    saver = _saver()
    post = next(r for r in saver.requests if r.method == "POST")
    later_get = next(r for r in saver.requests if r.method == "GET" and r.started_at > post.started_at)
    channel = FakeChannel({"http.send": [Reply(ok=True, result={"status": 200, "body": '{"workArea":"THIRD"}'})]})

    verdict = await verify(step=_step(saver), sent_kind="ui.perform", answer=Reply(ok=True, result={"performed": True}),
                           cited=[saver], values={"workArea": "THIRD"}, look_before=Look(None, None, ""), look_after=Look(None, None, ""),
                           channel=channel, device_id="dev_test", run_id="run_1", origin="http://127.0.0.1:63319", asker=FakeAsker(), model="m")

    assert (verdict.state, verdict.by) == ("held", "read")
    assert channel.sent[0]["payload"]["url"] == later_get.url


async def test_the_screenshot_is_last_and_least() -> None:
    saver = _saver()
    saver.requests = []  # nothing to read, nothing to confirm by
    asker = FakeAsker(Answer(data={"held": True, "why": "the form shows the saved record"}, cost_usd=0.0002))

    verdict = await verify(step=_step(saver), sent_kind="ui.perform", answer=Reply(ok=True, result={"performed": True}),
                           cited=[saver], values={}, look_before=Look("u", b"before", "Save"), look_after=Look("u", b"after", "Saved"),
                           channel=FakeChannel(), device_id="dev_test", run_id="run_1", origin=None, asker=asker, model="m")

    assert (verdict.state, verdict.by) == ("held", "screen")
    assert asker.asked[0]["image"] == b"after"
    assert verdict.answer is not None and verdict.answer.cost_usd == 0.0002


async def test_no_screenshot_and_no_state_is_unclear_not_held() -> None:
    saver = _saver()
    saver.requests = []
    verdict = await verify(step=_step(saver), sent_kind="ui.perform", answer=Reply(ok=True, result={"performed": True}),
                           cited=[saver], values={}, look_before=Look(None, None, ""), look_after=Look(None, None, ""),
                           channel=FakeChannel(), device_id="dev_test", run_id="run_1", origin=None, asker=FakeAsker(), model="m")
    assert verdict.state == "unclear" and verdict.by == "none"


async def test_a_command_the_browser_refused_is_failed_before_anything_is_verified() -> None:
    saver = _saver()
    verdict = await verify(step=_step(saver), sent_kind="ui.perform", answer=Reply(ok=False, error_kind="control_not_found", error_detail="no visible match"),
                           cited=[saver], values={}, look_before=Look(None, None, ""), look_after=Look(None, None, ""),
                           channel=FakeChannel(), device_id="dev_test", run_id="run_1", origin=None, asker=FakeAsker(), model="m")
    assert verdict.state == "failed" and verdict.reason == "control_not_found: no visible match"


def test_expected_statuses_and_the_confirming_read_come_from_the_evidence() -> None:
    saver = _saver()
    by_id = {saver.id: saver}
    assert expected_statuses(_step(saver), by_id) == {r.status for r in saver.requests if r.method == "POST" and r.status}
    read = confirming_read(_step(saver), by_id)
    assert read is not None and read.method == "GET"
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Write `verify.py`**

```python
"""A14: verify against state, and only then against a picture.

A state-grounded verifier scored 86.9% against 78.8% for one reading
screenshots, with human agreement at 94%. Most completions leave their proof
off-screen -- artifact verification was 192 of 321 tasks. So: the response the
command itself returned first, a confirming read the cited evidence shows the
page performs second, and the screenshot last and least. A green toast is the
weakest of the three and the easiest to be wrong about.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rig.channel import Answer as Reply
from rig.channel import Channel
from rig.locators import recorded_call
from rig.models import Answer, Asker
from rig.planner import Look
from rig.records import Gesture
from rig.wire import REDACTED, Request
from rig.workflows import Step

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"held": {"type": "boolean"}, "why": {"type": "string"}},
    "required": ["held", "why"],
    "propertyOrdering": ["held", "why"],
}

INSTRUCTIONS = """You are checking whether one step of a warehouse job was actually done.
You are shown the step, what was sent, what the browser answered, the screen
text before and after, and the screen after. Answer whether the step HELD --
whether the thing it was meant to do is now true on the screen -- and say why
in one sentence. Do not assume success from the absence of an error."""


@dataclass(frozen=True, slots=True)
class Verdict:
    state: str  # held | failed | unclear
    by: str  # status | read | screen | none
    reason: str
    answer: Answer | None = None


def expected_statuses(step: Step, by_id: Mapping[str, Gesture]) -> set[int]:
    """Every status the cited evidence's mutation came back with."""
    found: set[int] = set()
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() not in ("GET", "HEAD", "OPTIONS") and request.status:
                found.add(request.status)
    return found


def confirming_read(step: Step, by_id: Mapping[str, Gesture]) -> Request | None:
    """A GET a cited gesture made after its write: the read the page performs
    to show the result, which is the hidden state a run can ask for again."""
    call = recorded_call(step, by_id)
    if call is None or call.method.upper() in ("GET", "HEAD", "OPTIONS"):
        return None
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for request in gesture.requests:
            if request.method.upper() == "GET" and request.started_at > call.started_at:
                return request
    return None


def _mentions(body: str, values: Mapping[str, str]) -> bool:
    return any(value and value in body for value in values.values())


async def verify(
    *,
    step: Step,
    sent_kind: str,
    answer: Reply,
    cited: list[Gesture],
    values: Mapping[str, str],
    look_before: Look,
    look_after: Look,
    channel: Channel,
    device_id: str,
    run_id: str,
    origin: str | None,
    asker: Asker,
    model: str,
) -> Verdict:
    if not answer.ok:
        return Verdict("failed", "none", answer.detail)
    by_id = {g.id: g for g in cited}

    # 1. Artifact: what the command itself returned.
    if sent_kind == "http.send":
        status = answer.result.get("status")
        if isinstance(status, int):
            wanted = expected_statuses(step, by_id)
            if status in wanted or (not wanted and 200 <= status < 300):
                return Verdict("held", "status", f"the call returned {status}")
            if status >= 400:
                return Verdict("failed", "status", f"the call returned {status}")

    # 2. Hidden state: a read the cited evidence shows this page performs.
    probe = confirming_read(step, by_id)
    if probe is not None and values:
        got = await channel.send(
            device_id, kind="http.send", run_id=run_id,
            payload={"method": "GET", "url": probe.url,
                     "headers": {k: v for k, v in probe.request_headers.items() if REDACTED not in v},
                     "body": None},
        )
        body = str(got.result.get("body") or "") if got.ok else ""
        if got.ok and _mentions(body, values):
            return Verdict("held", "read", f"a read of {probe.url} shows the value this run supplied")
        if got.ok:
            return Verdict("failed", "read", f"a read of {probe.url} does not show the value this run supplied")

    # 3. Visible state: last, and least.
    if look_after.screenshot is None:
        return Verdict("unclear", "none", "nothing returned a status, nothing to read, and no screen to look at")
    evidence = json.dumps(
        {"step": {"says": step.says}, "sent": sent_kind, "browser_answered": answer.result,
         "screen_before": look_before.digest, "screen_after": look_after.digest, "values": dict(values)},
        indent=2, ensure_ascii=False,
    )
    judged = await asker.ask(model=model, instructions=INSTRUCTIONS, evidence=evidence,
                             schema=VERDICT_SCHEMA, image=look_after.screenshot)
    if judged.data is None:
        return Verdict("unclear", "screen", judged.error or "the model returned nothing", judged)
    held = bool(judged.data.get("held"))
    return Verdict("held" if held else "failed", "screen", str(judged.data.get("why") or ""), judged)
```

- [ ] **Step 4: Run, gates, commit**

```bash
uv run pytest tests/test_verify.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run mypy src
git add src/rig/verify.py tests/test_verify.py
git commit -m "feat(rig): A14 -- verify against state, and only then against a picture"
```

---

### Task 7: The loop (A15)

**Files:**
- Create: `new_agent_arch/src/rig/runner.py`
- Test: `new_agent_arch/tests/test_runner.py`

**Interfaces:**
- Consumes: everything above; `rig.api._row_to_gesture`; `known_workflows`; `save_run`.
- Produces:
  - `runner.K_STEP_SLACK = 3`, `runner.K_WEAK_LOCATORS = frozenset({"css_path", None})`
  - `async runner.run_workflow(store, workflow, *, values, channel, device_id, asker, plan_model, rescue_model, live: bool, allow_focus: bool, started_by: str, run_id: str | None = None) -> Run`
  - `runner.Aborts` — `abort(run_id)`, `is_aborted(run_id)`, in-process set the abort route flips
  - `runner.mark_stale(store, workflow_id, step_order, matched_by)` — appends to a `stale` list on the workflow's `unproven`? No: writes a `workflow_stale` row. See below.

Per step: **look** (`ui.url`, then `screenshot` inline — a `focus_not_permitted` answer means no picture, not a failure); **plan** with Flash; **refuse** if the origin is off the allowlist or the plan is `none`; **withhold** if this is a dry run and the step writes; **perform**; **verify**; on `failed`/`unclear`, **look again and re-plan with Pro once**, carrying the failure and both screenshots; still not held → **stop and ask**. Between steps: the abort flag, the budget. After every step: `save_run`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runner.py
import json
from pathlib import Path
from typing import Any

from rig.api import save_batch
from rig.channel import Answer as Reply
from rig.channel import FakeChannel
from rig.models import Answer, FakeAsker
from rig.runner import Aborts, K_STEP_SLACK, run_workflow
from rig.runs import load_run
from rig.store import Store
from rig.wire import Batch
from rig.workflows import Step, Workflow, save_workflow
from tests.fixtures import BATCH


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    save_batch(store, Batch.model_validate(BATCH), "acme")
    return store


def _ids(store: Store) -> list[str]:
    return [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]


def _workflow(store: Store) -> Workflow:
    ids = _ids(store)
    typed, saver = ids[0], ids[-1]
    wf = Workflow(id="wfl_1", tenant="acme", title="create a client", narrative="n",
                  systems=["http://127.0.0.1:63319"],
                  steps=[Step(order=0, says="type the code", system=None, cites=[typed], parameters=["clientCode"]),
                         Step(order=1, says="save", system=None, cites=[saver])],
                  parameters=[{"name": "clientCode", "seen_values": ["A", "B"]}])
    save_workflow(store, wf)
    return wf


def _plan(action: str, value: str | None = None) -> Answer:
    return Answer(data={"kind": "ui.perform", "action": action, "value": value, "url": None, "why": "w"}, cost_usd=0.001)


def _looks(n: int) -> dict[str, list[Reply]]:
    return {"ui.url": [Reply(ok=True, result={"url": "http://127.0.0.1:63319/form"})] * n,
            "screenshot": [Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "Save"})] * n}


async def test_a_dry_run_sends_the_reads_and_withholds_the_write_in_full(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component", "candidates": 1})]})
    asker = FakeAsker(_plan("type", "THIRD"), Answer(data={"held": True, "why": "typed"}), _plan("click"))

    run = await run_workflow(store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
                             asker=asker, plan_model="flash", rescue_model="pro", live=False, allow_focus=True, started_by="form")

    assert run.outcome == "held"
    assert [s.verdict for s in run.steps] == ["held", "withheld"]
    performed = [s for s in channel.sent if s["kind"] == "ui.perform"]
    assert len(performed) == 1 and performed[0]["payload"]["value"] == "THIRD", "the typing went out"
    assert run.withheld and run.withheld[0]["method"] == "POST", "the write is shown, in full"
    assert load_run(store, "acme", run.id) == run, "saved"


async def test_a_live_run_sends_the_write(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [
        Reply(ok=True, result={"performed": True, "matched_by": "component", "candidates": 1}),
        Reply(ok=True, result={"performed": True, "matched_by": "component", "candidates": 1})]})
    asker = FakeAsker(_plan("type", "THIRD"), Answer(data={"held": True, "why": ""}), _plan("click"), Answer(data={"held": True, "why": ""}))

    run = await run_workflow(store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
                             asker=asker, plan_model="flash", rescue_model="pro", live=True, allow_focus=True, started_by="form")

    assert [s.verdict for s in run.steps] == ["held", "held"] and not run.withheld


async def test_an_origin_outside_the_evidence_is_refused_before_it_is_sent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel(_looks(2))
    asker = FakeAsker(Answer(data={"kind": "navigate", "action": None, "value": None, "url": "https://evil.example/x", "why": ""}))

    run = await run_workflow(store, wf, values={}, channel=channel, device_id="dev_test", asker=asker,
                             plan_model="flash", rescue_model="pro", live=True, allow_focus=True, started_by="form")

    assert run.outcome == "refused" and run.steps[0].verdict == "refused"
    assert not [s for s in channel.sent if s["kind"] == "navigate"], "nothing left the process"


async def test_a_failed_step_is_retried_once_with_pro_then_the_run_stops_and_asks(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(6), "ui.perform": [
        Reply(ok=False, error_kind="control_not_found", error_detail="gone"),
        Reply(ok=False, error_kind="control_not_found", error_detail="still gone")]})
    asker = FakeAsker(_plan("type", "x"), _plan("type", "x"))

    run = await run_workflow(store, wf, values={"clientCode": "x"}, channel=channel, device_id="dev_test", asker=asker,
                             plan_model="flash", rescue_model="pro", live=True, allow_focus=True, started_by="form")

    assert run.outcome == "stopped"
    assert run.steps[0].verdict == "failed" and run.steps[0].planned_by == "pro", "the second attempt was Pro's"
    assert [a["model"] for a in asker.asked] == ["flash", "pro"]
    assert len(run.steps) == 1, "it stopped rather than carrying on to save"


async def test_a_navigate_gets_to_the_page_and_does_not_spend_the_rescue(tmp_path: Path) -> None:
    """A deep job was demonstrated across several screens. Moving to the next
    one is not doing the step: after the navigate the same step is planned
    again on the same rung, so a step that needed a page change and then went
    wrong still has its one Pro rescue."""
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(6), "navigate": [Reply(ok=True, result={"navigated": True})],
                           "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component", "candidates": 1})]})
    asker = FakeAsker(
        Answer(data={"kind": "navigate", "action": None, "value": None, "url": "http://127.0.0.1:63319/form", "why": "wrong page"}),
        _plan("type", "x"),
        Answer(data={"held": True, "why": ""}),
        _plan("click"),
    )

    run = await run_workflow(store, wf, values={"clientCode": "x"}, channel=channel, device_id="dev_test", asker=asker,
                             plan_model="flash", rescue_model="pro", live=False, allow_focus=True, started_by="form")

    assert [s["kind"] for s in channel.sent if s["kind"] in ("navigate", "ui.perform")] == ["navigate", "ui.perform"]
    assert run.steps[0].verdict == "held" and run.steps[0].planned_by == "flash", "the rescue was never needed"


async def test_a_weak_locator_match_succeeds_and_flags_the_step_stale(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "css_path", "candidates": 1})]})
    asker = FakeAsker(_plan("type", "x"), Answer(data={"held": True, "why": ""}), _plan("click"))

    run = await run_workflow(store, wf, values={"clientCode": "x"}, channel=channel, device_id="dev_test", asker=asker,
                             plan_model="flash", rescue_model="pro", live=False, allow_focus=True, started_by="form")

    assert run.steps[0].verdict == "held" and run.steps[0].stale is True and run.steps[0].matched_by == "css_path"


async def test_the_stop_button_is_honoured_between_steps(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component", "candidates": 1})],
                           "abort": [Reply(ok=True, result={"aborted": True})]})
    asker = FakeAsker(_plan("type", "x"), Answer(data={"held": True, "why": ""}))
    Aborts.abort("run_stop")

    run = await run_workflow(store, wf, values={"clientCode": "x"}, channel=channel, device_id="dev_test", asker=asker,
                             plan_model="flash", rescue_model="pro", live=True, allow_focus=True, started_by="form", run_id="run_stop")

    assert run.outcome == "aborted" and run.steps == []


async def test_the_step_budget_is_the_workflows_steps_plus_slack(tmp_path: Path) -> None:
    """Every attempt counts against it, so a model looping on a form runs out."""
    store = _store(tmp_path)
    wf = _workflow(store)
    assert K_STEP_SLACK == 3
    attempts = len(wf.steps) + K_STEP_SLACK + 2
    channel = FakeChannel({**_looks(attempts * 2), "ui.perform": [Reply(ok=False, error_kind="not_visible", error_detail="")] * attempts})
    asker = FakeAsker(*[_plan("type", "x")] * attempts)

    run = await run_workflow(store, wf, values={"clientCode": "x"}, channel=channel, device_id="dev_test", asker=asker,
                             plan_model="flash", rescue_model="pro", live=True, allow_focus=True, started_by="form")

    assert run.outcome in ("stopped", "refused")
    assert len([s for s in channel.sent if s["kind"] == "ui.perform"]) <= len(wf.steps) + K_STEP_SLACK


async def test_every_model_call_on_a_run_is_billed_to_its_step(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component", "candidates": 1})]})
    asker = FakeAsker(Answer(data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""}, cost_usd=0.002, in_tokens=100, out_tokens=10),
                      Answer(data={"held": True, "why": ""}, cost_usd=0.001, in_tokens=50, out_tokens=5),
                      _plan("click"))

    run = await run_workflow(store, wf, values={"clientCode": "x"}, channel=channel, device_id="dev_test", asker=asker,
                             plan_model="flash", rescue_model="pro", live=False, allow_focus=True, started_by="form")

    assert run.steps[0].cost_usd == 0.003 and run.steps[0].in_tokens == 150
    assert run.cost_usd == sum(s.cost_usd for s in run.steps)


async def test_a_browser_that_went_away_fails_the_run_and_says_so(tmp_path: Path) -> None:
    from rig.channel import DeviceChannel
    store = _store(tmp_path)
    wf = _workflow(store)
    run = await run_workflow(store, wf, values={}, channel=DeviceChannel(), device_id="dev_gone", asker=FakeAsker(),
                             plan_model="flash", rescue_model="pro", live=False, allow_focus=True, started_by="form")
    assert run.outcome == "failed" and "dev_gone" in run.steps[0].reason
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Write `runner.py`**

```python
"""A15: the loop. Look, plan, refuse-or-perform, verify, escalate once, stop.

Flash plans; Pro rescues. A clean step never touches the expensive model, and
only the steps that surprise us cost what surprises cost. Between steps the
stop button and the budget are checked; after every step the run is saved, so
the page can watch it and so a crash mid-run leaves a record rather than a
mystery.

The first execution of any workflow is dry. Reads and navigations go out; a
step whose evidence carries a mutation is shown in full and withheld. A person
presses through to live.
"""

import base64
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from rig.channel import Answer as Reply
from rig.channel import Channel, DeviceUnreachable
from rig.locators import allowlist, origin_of, primary_gesture, recorded_call, writes
from rig.models import Answer, Asker
from rig.planner import Look, Planned, plan_step
from rig.records import Gesture
from rig.runs import Run, RunStep, new_run_id, save_run
from rig.store import Store
from rig.verify import Verdict, verify
from rig.workflows import Step, Workflow

log = logging.getLogger(__name__)

K_STEP_SLACK = 3
"""Attempts a run may make beyond its step count before it stops. A model
looping on a form is money spent and a warehouse confused."""

K_WEAK_LOCATORS = frozenset({"css_path", None})
"""A step that only ever matches on the last fallback is a step about to break.
The run succeeds and the step is flagged stale."""


class Aborts:
    """The stop button. In-process, like the channel it belongs beside: a run
    does not survive a restart either."""

    _stopped: set[str] = set()

    @classmethod
    def abort(cls, run_id: str) -> None:
        cls._stopped.add(run_id)

    @classmethod
    def is_aborted(cls, run_id: str) -> bool:
        return run_id in cls._stopped

    @classmethod
    def forget(cls, run_id: str) -> None:
        cls._stopped.discard(run_id)


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _bill(step: RunStep, *answers: Answer | None) -> None:
    for answer in answers:
        if answer is None:
            continue
        step.in_tokens += answer.in_tokens
        step.out_tokens += answer.out_tokens
        step.thought_tokens += answer.thought_tokens
        step.cost_usd += answer.cost_usd
        step.unpriced = step.unpriced or answer.unpriced


def _total(run: Run) -> None:
    run.in_tokens = sum(s.in_tokens for s in run.steps)
    run.out_tokens = sum(s.out_tokens for s in run.steps)
    run.thought_tokens = sum(s.thought_tokens for s in run.steps)
    run.cost_usd = sum(s.cost_usd for s in run.steps)
    run.unpriced = any(s.unpriced for s in run.steps)


def _gestures_for(store: Store, workflow: Workflow) -> dict[str, Gesture]:
    from rig.api import _row_to_gesture  # deferred: api imports runner for the route

    wanted = sorted({c for s in workflow.steps for c in s.cites})
    if not wanted:
        return {}
    marks = ",".join("?" * len(wanted))
    rows = store.query(f"SELECT * FROM gestures WHERE tenant = ? AND id IN ({marks})", (workflow.tenant, *wanted))
    return {row["id"]: _row_to_gesture(row) for row in rows}


async def _look(channel: Channel, device_id: str, run_id: str, origin: str | None, allow_focus: bool) -> Look:
    """Where the browser is and what is on the screen. A refused screenshot --
    `focus_not_permitted` -- is no picture, not a failure: the planner works
    from the url and the digest."""
    where = await channel.send(device_id, kind="ui.url", run_id=run_id, payload={"origin": origin})
    url = str(where.result.get("url")) if where.ok and where.result.get("url") else None
    payload: dict[str, Any] = {"inline": True, "origin": origin}
    if allow_focus:
        payload["allow_focus"] = True
    shot = await channel.send(device_id, kind="screenshot", run_id=run_id, payload=payload)
    image = None
    digest = ""
    if shot.ok:
        raw = shot.result.get("image_base64")
        if isinstance(raw, str) and raw:
            try:
                image = base64.b64decode(raw)
            except ValueError:
                image = None
        digest = str(shot.result.get("text_digest") or "")
    return Look(url=url, screenshot=image, digest=digest)


def _withheld(step: Step, planned: Planned, by_id: Mapping[str, Gesture]) -> dict[str, Any]:
    """The write a dry run did not send, in full: what a person reads before
    pressing through to live."""
    call = recorded_call(step, by_id)
    shown: dict[str, Any] = {"step": step.order, "planned": {"kind": planned.kind, "payload": planned.payload}}
    if call is not None:
        shown.update(method=call.method.upper(), url=call.url,
                     body=call.request_body.text if call.request_body else None)
    return shown


async def run_workflow(
    store: Store,
    workflow: Workflow,
    *,
    values: Mapping[str, str],
    channel: Channel,
    device_id: str,
    asker: Asker,
    plan_model: str,
    rescue_model: str,
    live: bool,
    allow_focus: bool,
    started_by: str,
    run_id: str | None = None,
) -> Run:
    run = Run(id=run_id or new_run_id(), tenant=workflow.tenant, workflow_id=workflow.id, device_id=device_id,
              values=dict(values), started_by=started_by, live=live, allow_focus=allow_focus, started_at=_now())
    save_run(store, run)
    by_id = _gestures_for(store, workflow)
    allowed = allowlist(workflow, by_id)
    budget = len(workflow.steps) + K_STEP_SLACK
    attempts = 0
    starts_on = None
    first = primary_gesture(workflow.steps[0], by_id) if workflow.steps else None
    if first is not None:
        starts_on = first.page_url or first.url

    try:
        for step in sorted(workflow.steps, key=lambda s: s.order):
            if Aborts.is_aborted(run.id):
                await channel.send(device_id, kind="abort", run_id=run.id, payload={"run_id": run.id})
                run.outcome = "aborted"
                break
            cited = [by_id[c] for c in step.cites if c in by_id]
            primary = primary_gesture(step, by_id)
            record = RunStep(order=step.order, says=step.says, verdict="skipped")
            if primary is None:
                record.verdict, record.reason = "skipped", "no cited gesture can be acted on"
                run.steps.append(record)
                continue
            origin = origin_of(primary)

            verdict: Verdict | None = None
            for attempt, model in ((1, plan_model), (2, rescue_model)):
                if attempts >= budget:
                    record.verdict, record.reason = "refused", f"the step budget of {budget} attempts is spent"
                    run.outcome = "refused"
                    break
                attempts += 1
                before = await _look(channel, device_id, run.id, origin, allow_focus)
                planned = await plan_step(
                    step=step, cited=cited, values=values, look=before, origin=origin, starts_on=starts_on,
                    allow_focus=allow_focus, asker=asker, model=model,
                    failure=verdict.reason if verdict else None,
                )
                record.planned_by = model
                record.before_url = before.url
                _bill(record, planned.answer)
                record.sent = {"kind": planned.kind, "payload": planned.payload}

                if planned.kind == "none":
                    verdict = Verdict("failed", "none", planned.why)
                    continue
                target_origin = planned.payload.get("origin") if planned.kind != "http.send" else None
                if planned.kind == "http.send":
                    from rig.correlate import system_of
                    target_origin = system_of(str(planned.payload.get("url")))
                if planned.kind == "navigate":
                    from rig.correlate import system_of
                    target_origin = system_of(str(planned.payload.get("url")))
                if target_origin and target_origin not in allowed:
                    record.verdict, record.reason = "refused", f"{target_origin} is not a system this job's evidence names"
                    run.outcome = "refused"
                    break

                if planned.kind == "navigate":
                    # Getting to the right page is not doing the step. Send it,
                    # then plan this step again on the same rung: a deep job
                    # was demonstrated across several screens, and moving to
                    # the next one must not spend the one rescue the step has.
                    # It does spend budget, so a planner that only ever
                    # navigates still runs out.
                    moved = await channel.send(device_id, kind="navigate", run_id=run.id, payload=planned.payload)
                    if not moved.ok:
                        verdict = Verdict("failed", "none", f"could not navigate: {moved.detail}")
                        continue
                    if attempts >= budget:
                        record.verdict, record.reason = "refused", f"the step budget of {budget} attempts is spent"
                        run.outcome = "refused"
                        break
                    attempts += 1
                    before = await _look(channel, device_id, run.id, origin, allow_focus)
                    planned = await plan_step(
                        step=step, cited=cited, values=values, look=before, origin=origin,
                        starts_on=starts_on, allow_focus=allow_focus, asker=asker, model=model,
                        failure=None,
                    )
                    record.before_url = before.url
                    _bill(record, planned.answer)
                    record.sent = {"kind": planned.kind, "payload": planned.payload}
                    if planned.kind in ("none", "navigate"):
                        verdict = Verdict("failed", "none", planned.why or "still on the wrong page after navigating")
                        continue
                    target_origin = system_of(str(planned.payload.get("url"))) if planned.kind == "http.send" else planned.payload.get("origin")
                    if target_origin and target_origin not in allowed:
                        record.verdict, record.reason = "refused", f"{target_origin} is not a system this job's evidence names"
                        run.outcome = "refused"
                        break

                if not live and writes(step, by_id):
                    run.withheld.append(_withheld(step, planned, by_id))
                    record.verdict, record.verdict_by, record.reason = "withheld", "dry", "a dry run does not send writes"
                    record.result = {"withheld": True}
                    break

                reply = await channel.send(device_id, kind=planned.kind, run_id=run.id, payload=planned.payload)
                record.result = dict(reply.result) if reply.ok else {"error": reply.detail}
                record.matched_by = reply.result.get("matched_by") if reply.ok else None
                after = await _look(channel, device_id, run.id, origin, allow_focus)
                record.after_url = after.url
                verdict = await verify(
                    step=step, sent_kind=planned.kind, answer=reply, cited=cited, values=values,
                    look_before=before, look_after=after, channel=channel, device_id=device_id,
                    run_id=run.id, origin=origin, asker=asker, model=plan_model,
                )
                _bill(record, verdict.answer)
                record.verdict, record.verdict_by, record.reason = verdict.state, verdict.by, verdict.reason
                if verdict.state == "held":
                    if planned.kind == "ui.perform" and record.matched_by in K_WEAK_LOCATORS:
                        record.stale = True
                    break

            run.steps.append(record)
            _total(run)
            save_run(store, run)
            if run.outcome != "running":
                break
            if record.verdict in ("failed", "unclear"):
                run.outcome = "stopped"
                break
        else:
            run.outcome = "held"
    except DeviceUnreachable as gone:
        run.steps.append(RunStep(order=len(run.steps), says="", verdict="failed", verdict_by="none", reason=str(gone)))
        run.outcome = "failed"

    run.finished_at = _now()
    _total(run)
    save_run(store, run)
    Aborts.forget(run.id)
    return run
```

Note the two deferred `system_of` imports inside the loop: collapse them into one module-level `from rig.correlate import system_of` when transcribing — the block above is authoritative for behaviour, not layout, and `ruff` will flag the repetition.

- [ ] **Step 4: Run, gates, commit**

```bash
uv run pytest tests/test_runner.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run pytest -q
git add src/rig/runner.py tests/test_runner.py
git commit -m "feat(rig): A15 -- the loop: look, plan, refuse or perform, verify, rescue once, stop"
```

---

### Task 8: The doors — form, chat, and the routes

**Files:**
- Create: `new_agent_arch/src/rig/entry.py`
- Modify: `new_agent_arch/src/rig/api.py` — `GET /v1/devices`, `POST /v1/runs`, `GET /v1/runs/{run_id}`, `POST /v1/runs/{run_id}/abort`, `POST /v1/chat`
- Test: `new_agent_arch/tests/test_entry.py`, `new_agent_arch/tests/test_api.py` (append)

**Interfaces:**
- Produces:
  - `entry.UNDERSTAND_SCHEMA`, `async entry.understand(utterance: str, workflows: list[Workflow], asker, model) -> Understood(workflow_id: str | None, values: dict[str, str], missing: list[str], answer: Answer)`
  - Routes as below. `POST /v1/runs` body: `{workflow_id, values, live, device_id, allow_focus, started_by}`; answers `202 {run_id}` and performs in a background task. `GET /v1/runs/{id}` answers `runs.as_json(run)`. `POST /v1/runs/{id}/abort` flips `Aborts` and answers `{aborted: true}`. `GET /v1/devices` answers `{devices: channel.online()}`. `POST /v1/chat` body `{utterance}`, answers the `Understood` — it **offers** and never starts.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_entry.py
from rig.entry import UNDERSTAND_SCHEMA, understand
from rig.models import Answer, FakeAsker
from rig.workflows import Step, Workflow

WFS = [Workflow(id="wfl_1", tenant="acme", title="create a client", narrative="n",
                steps=[Step(order=0, says="s", system=None, cites=["g"])],
                parameters=[{"name": "clientCode", "seen_values": ["A"]}])]


async def test_an_utterance_is_read_against_the_workflows_held_and_asks_for_what_is_missing() -> None:
    asker = FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": {"clientCode": "NEW9"}, "missing": []}))
    got = await understand("create client NEW9", WFS, asker, "m")
    assert got.workflow_id == "wfl_1" and got.values == {"clientCode": "NEW9"} and got.missing == []
    assert "create a client" in asker.asked[0]["evidence"], "the workflows are what it reads against"


async def test_a_workflow_the_rig_does_not_hold_is_not_offered() -> None:
    got = await understand("x", WFS, FakeAsker(Answer(data={"workflow_id": "wfl_nope", "values": {}, "missing": []})), "m")
    assert got.workflow_id is None


async def test_a_value_for_a_parameter_the_workflow_does_not_declare_is_dropped() -> None:
    got = await understand("x", WFS, FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": {"clientCode": "A", "evil": "b"}, "missing": []})), "m")
    assert got.values == {"clientCode": "A"}


def test_the_schema_is_the_specs() -> None:
    assert set(UNDERSTAND_SCHEMA["properties"]) == {"workflow_id", "values", "missing"}
```

Append to `tests/test_api.py`:

```python
def test_a_run_is_started_from_the_form_door_and_can_be_read_back(
    client: TestClient, store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rig.channel import Answer as Reply
    from rig.channel import FakeChannel
    from rig.workflows import Step, Workflow, save_workflow

    save_batch(store, Batch.model_validate(BATCH), "new")
    ids = [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]
    save_workflow(store, Workflow(id="wfl_1", tenant="new", title="t", narrative="n",
                                  steps=[Step(order=0, says="type", system=None, cites=[ids[0]])]))
    fake = FakeChannel({"ui.url": [Reply(ok=True, result={"url": "u"})] * 4,
                        "screenshot": [Reply(ok=True, result={"image_base64": "aVBORw0=", "text_digest": "Save"})] * 4,
                        "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component", "candidates": 1})]})
    client.app.state.channel = fake
    client.app.state.asker = FakeAsker(
        Answer(data={"kind": "ui.perform", "action": "type", "value": "x", "url": None, "why": ""}),
        Answer(data={"held": True, "why": ""}))

    started = client.post("/v1/runs", json={"workflow_id": "wfl_1", "values": {}, "live": False,
                                             "device_id": "dev_test", "allow_focus": True, "started_by": "form"},
                          headers=_auth())
    assert started.status_code == 202
    run_id = started.json()["run_id"]

    import time
    for _ in range(50):
        body = client.get(f"/v1/runs/{run_id}", headers=_auth()).json()
        if body["outcome"] != "running":
            break
        time.sleep(0.05)
    assert body["outcome"] == "held"
    assert body["steps"][0]["verdict"] == "held" and body["steps"][0]["verdict_by"] == "screen"


def test_a_run_against_a_device_that_is_not_connected_is_refused_at_the_door(client: TestClient) -> None:
    refused = client.post("/v1/runs", json={"workflow_id": "wfl_1", "values": {}, "live": False,
                                             "device_id": "dev_nobody", "allow_focus": True, "started_by": "form"},
                          headers=_auth())
    assert refused.status_code == 409


def test_chat_offers_and_never_starts(client: TestClient, store: Store) -> None:
    from rig.workflows import Step, Workflow, save_workflow
    save_workflow(store, Workflow(id="wfl_1", tenant="new", title="create a client", narrative="n",
                                  steps=[Step(order=0, says="s", system=None, cites=["g"])],
                                  parameters=[{"name": "clientCode", "seen_values": ["A"]}]))
    client.app.state.asker = FakeAsker(Answer(data={"workflow_id": "wfl_1", "values": {"clientCode": "NEW9"}, "missing": []}))

    offered = client.post("/v1/chat", json={"utterance": "create client NEW9"}, headers=_auth()).json()

    assert offered == {"workflow_id": "wfl_1", "values": {"clientCode": "NEW9"}, "missing": []}
    assert store.query("SELECT count(*) AS n FROM runs")[0]["n"] == 0, "saying it offers the work; pressing start authorises it"


def test_the_stop_button_flips_the_flag_and_tells_the_browser(client: TestClient) -> None:
    from rig.channel import Answer as Reply
    from rig.channel import FakeChannel
    from rig.runner import Aborts
    client.app.state.channel = FakeChannel({"abort": [Reply(ok=True, result={"aborted": True})]})
    assert client.post("/v1/runs/run_x/abort", json={"device_id": "dev_test"}, headers=_auth()).json() == {"aborted": True}
    assert Aborts.is_aborted("run_x")
    Aborts.forget("run_x")


def test_devices_lists_what_is_connected(client: TestClient) -> None:
    assert client.get("/v1/devices", headers=_auth()).json() == {"devices": []}
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Write `entry.py`**

```python
"""The chat door. Saying it offers the work; pressing start authorises it.

Flash reads the utterance against the workflows the rig holds and answers
which one, with which values, and what is still missing. Nothing performs from
here: the answer is an offer the form renders, and `POST /v1/runs` is the press.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from rig.models import Answer, Asker
from rig.workflows import Workflow

UNDERSTAND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "workflow_id": {"type": "string", "nullable": True},
        "values": {"type": "object", "additionalProperties": {"type": "string"}},
        "missing": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["workflow_id", "values", "missing"],
    "propertyOrdering": ["workflow_id", "values", "missing"],
}

INSTRUCTIONS = """An operator has said what they want done. You are given the jobs this system
can do, each with the parameters it takes and the values it has seen. Answer
which job they mean (its id, or null if none fits), the values they gave for
its parameters, and which parameters are still missing. Never invent a value."""


@dataclass(frozen=True, slots=True)
class Understood:
    workflow_id: str | None
    values: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    answer: Answer | None = None


async def understand(utterance: str, workflows: list[Workflow], asker: Asker, model: str) -> Understood:
    held = [
        {"id": w.id, "title": w.title, "narrative": w.narrative,
         "parameters": [{"name": p.get("name"), "seen": p.get("seen_values", [])} for p in w.parameters if isinstance(p, dict)]}
        for w in workflows
    ]
    answer = await asker.ask(
        model=model, instructions=INSTRUCTIONS,
        evidence=json.dumps({"said": utterance, "jobs": held}, indent=2, ensure_ascii=False),
        schema=UNDERSTAND_SCHEMA,
    )
    if answer.data is None:
        return Understood(None, answer=answer)
    by_id = {w.id: w for w in workflows}
    chosen = by_id.get(str(answer.data.get("workflow_id") or ""))
    if chosen is None:
        return Understood(None, answer=answer)
    declared = {p.get("name") for p in chosen.parameters if isinstance(p, dict)}
    raw = answer.data.get("values")
    values = {k: str(v) for k, v in (raw.items() if isinstance(raw, dict) else ()) if k in declared and isinstance(v, str)}
    missing = [m for m in (answer.data.get("missing") or []) if isinstance(m, str) and m in declared]
    return Understood(chosen.id, values, missing, answer)
```

- [ ] **Step 4: Add the routes to `api.py`**

Before `@app.get("/", response_class=HTMLResponse)`:

```python
    @app.get("/v1/devices", dependencies=[Depends(authorised)])
    def devices() -> dict[str, Any]:
        return {"devices": app.state.channel.online()}

    @app.post("/v1/runs", status_code=202, dependencies=[Depends(authorised)])
    async def start_run(body: dict[str, Any]) -> dict[str, Any]:
        """The press. A person opened a door and chose live or dry; the rig
        has no way to start a run on its own."""
        from rig.runner import run_workflow
        from rig.runs import new_run_id
        from rig.workflows import known_workflows

        # The browser first, then the workflow: "your browser is not connected"
        # is the answer a person can act on, and it holds whatever they asked for.
        device_id = str(body.get("device_id") or "")
        if device_id not in app.state.channel.online():
            raise HTTPException(status_code=409, detail=f"{device_id or 'no device'} is not connected to the rig")
        workflow = next((w for w in known_workflows(store, tenant) if w.id == body.get("workflow_id")), None)
        if workflow is None:
            raise HTTPException(status_code=404, detail="no such workflow")
        values = body.get("values") if isinstance(body.get("values"), dict) else {}
        run_id = new_run_id()
        asyncio.create_task(
            run_workflow(
                store, workflow, values={str(k): str(v) for k, v in values.items()},
                channel=app.state.channel, device_id=device_id, asker=app.state.asker,
                plan_model=settings().plan_model, rescue_model=settings().rescue_model,
                live=bool(body.get("live")), allow_focus=bool(body.get("allow_focus", True)),
                started_by=str(body.get("started_by") or "form"), run_id=run_id,
            )
        )
        return {"run_id": run_id}

    @app.get("/v1/runs/{run_id}", dependencies=[Depends(authorised)])
    def read_run(run_id: str) -> dict[str, Any]:
        from rig.runs import as_json, load_run

        run = load_run(store, tenant, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="no such run")
        return as_json(run)

    @app.post("/v1/runs/{run_id}/abort", dependencies=[Depends(authorised)])
    async def abort_run(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
        from rig.runner import Aborts

        Aborts.abort(run_id)
        device_id = str(body.get("device_id") or "")
        if device_id in app.state.channel.online():
            await app.state.channel.send(device_id, kind="abort", run_id=run_id, payload={"run_id": run_id})
        return {"aborted": True}

    @app.post("/v1/chat", dependencies=[Depends(authorised)])
    async def chat(body: dict[str, Any]) -> dict[str, Any]:
        """Offers. Never starts."""
        from rig.entry import understand
        from rig.workflows import known_workflows

        got = await understand(str(body.get("utterance") or ""), known_workflows(store, tenant),
                               app.state.asker, settings().plan_model)
        return {"workflow_id": got.workflow_id, "values": got.values, "missing": got.missing}
```

The route reads `app.state.channel` and `app.state.asker` at call time rather
than closing over `asker`, so a test can swap them.

- [ ] **Step 5: Run, gates, commit**

```bash
uv run pytest tests/test_entry.py tests/test_api.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run pytest -q
git add src/rig/entry.py src/rig/api.py tests/test_entry.py tests/test_api.py
git commit -m "feat(rig): the doors -- a form that starts, a chat that offers, a button that stops"
```

---

### Task 9: The page — run a job, watch it

**Files:**
- Modify: `new_agent_arch/src/rig/web/index.html`
- Test: `new_agent_arch/tests/test_api.py` (append: the page names the new routes and escapes a run's text)

Every job card gets a **run** button. Pressing it opens a form under the card:
one field per declared parameter, prefilled with the last `seen_values` entry;
a device picker from `GET /v1/devices`; a `live` checkbox defaulting **off**;
a **start** button posting `POST /v1/runs`. Below it, the live run: polled from
`GET /v1/runs/{id}` every second while `outcome == "running"`, one line per step
— `order · says · verdict · by · matched_by · cost` — a **stop** button posting
`/abort`, and when finished, the `withheld` writes rendered in full under the
heading *what a live run would have sent*.

- [ ] **Step 1: Write the failing test**

```python
def test_the_page_can_start_watch_and_stop_a_run() -> None:
    page = (Path(__file__).resolve().parents[1] / "src/rig/web/index.html").read_text()
    for needed in ("/v1/devices", "/v1/runs", "/abort", "what a live run would have sent",
                   'type="checkbox"', "stop"):
        assert needed in page, needed
```

- [ ] **Step 2: Run to verify it fails**

- [ ] **Step 3: Add to `index.html`**

Inside `job(w)`, after the steps: `<button class="run" data-id="${esc(w.id)}">run</button><div class="runner" id="runner-${esc(w.id)}"></div>`. Then, in the script, alongside `drawJobs`:

```javascript
  async function openRunner(w) {
    const { devices } = await get("/v1/devices");
    const fields = (w.parameters ?? []).map((p) => {
      const seen = (p.seen_values ?? []).slice(-1)[0] ?? "";
      return `<label>${esc(p.name)} <input name="${esc(p.name)}" value="${esc(seen)}"></label>`;
    }).join("");
    const picker = devices.length
      ? `<select name="device">${devices.map((d) => `<option>${esc(d)}</option>`).join("")}</select>`
      : `<span class="none">no browser is connected to the rig</span>`;
    const box = document.getElementById(`runner-${w.id}`);
    box.innerHTML = `<form class="start">${fields}${picker}
      <label><input type="checkbox" name="live"> live — send the writes</label>
      <button ${devices.length ? "" : "disabled"}>start</button></form><div class="live"></div>`;
    box.querySelector("form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.target);
      const values = {};
      for (const p of w.parameters ?? []) values[p.name] = form.get(p.name) ?? "";
      const { run_id } = await post("/v1/runs", {
        workflow_id: w.id, values, live: form.get("live") === "on",
        device_id: form.get("device"), allow_focus: true, started_by: "form",
      });
      watch(run_id, form.get("device"), box.querySelector(".live"));
    });
  }

  async function watch(runId, device, into) {
    const run = await get(`/v1/runs/${encodeURIComponent(runId)}`);
    const steps = run.steps.map((s) =>
      `<div class="step ${esc(s.verdict)}">${s.order} · ${esc(s.says)} · <b>${esc(s.verdict)}</b>
       ${s.verdict_by ? "by " + esc(s.verdict_by) : ""} ${s.matched_by ? "· matched " + esc(s.matched_by) : ""}
       ${s.stale ? "· <i>stale</i>" : ""} · $${(s.cost_usd ?? 0).toFixed(4)}<div class="why">${esc(s.reason)}</div></div>`).join("");
    const withheld = run.withheld.length
      ? `<h4>what a live run would have sent</h4>` + run.withheld.map((w) =>
          `<pre>${esc(w.method ?? "")} ${esc(w.url ?? "")}\n${esc(w.body ?? "")}</pre>`).join("")
      : "";
    into.innerHTML = `<div class="outcome">${esc(run.outcome)} · $${(run.cost_usd ?? 0).toFixed(4)}
      ${run.outcome === "running" ? `<button class="stop">stop</button>` : ""}</div>${steps}${withheld}`;
    into.querySelector(".stop")?.addEventListener("click", () =>
      post(`/v1/runs/${encodeURIComponent(runId)}/abort`, { device_id: device }));
    if (run.outcome === "running") setTimeout(() => watch(runId, device, into), 1000);
  }

  async function post(path, body) {
    const r = await fetch(path, { method: "POST", headers: { ...auth(), "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return r.json();
  }
```

Wire the buttons in `drawJobs`, after setting `innerHTML`:
`for (const b of document.querySelectorAll("button.run")) b.addEventListener("click", () => openRunner(workflows.find((w) => w.id === b.dataset.id)));`

`auth()` and `esc()` already exist in the page; `get()` already sends the token.
Every string a run carries — `says`, `reason`, `url`, `body` — goes through
`esc()`, because it came from a model or a warehouse page.

- [ ] **Step 4: Run, commit**

```bash
uv run pytest tests/test_api.py -q
git add src/rig/web/index.html tests/test_api.py
git commit -m "feat(rig): the page runs a job and watches it, dry by default"
```

---

### Task 11: The extension's panel shows a rig run

**Files:**
- Modify: `new-chrome-extension/src/background/service-worker.js` — `noteFinished` asks the rig for a rig run
- Modify: `new-chrome-extension/src/background/api.js` — `api.rigRun(runId)`, `api.rigAbort(runId, deviceId)`
- Modify: `new-chrome-extension/src/panel/panel.js` — a rig run's card: steps from the run's own record, **Stop** to the rig, no "It's wrong"
- Test: `new-chrome-extension/src/background/finishing.test.mjs` (extend), `new-chrome-extension/src/panel/run-card.test.mjs` (extend)

**Interfaces:**
- Consumes: `activeRun.source` (Task 2), `GET /v1/runs/{id}` and `POST /v1/runs/{id}/abort` on the rig (Task 8), `state.rigUrl()`, `state.rigToken()`, `state.deviceId()`.
- Produces: `api.rigRun(runId) -> { id, source: "rig", status, steps: [{ index, outcome, says, reason }], withheld }` — the rig's `outcome` mapped onto the panel's `status` vocabulary (`running` stays `running`; everything else is finished), each rig step mapped to `{ index: order, outcome: verdict, says, reason }`.

Every UX state the extension already has stays exactly as it is for a rig run
-- the driving band on the page, the "performing" card, `busy` when the
operator types, `allow_focus` refusing to steal the screen. What changes is
only who is asked how it ended and where Stop goes. The rig has no reversal
and no "It's wrong": those affordances are not shown for a run whose
`source` is `rig`, rather than shown and broken.

- [ ] **Step 1: Write the failing tests**

In `finishing.test.mjs`, beside the existing backend case: an `activeRun` with
`source: "rig"` and a stubbed `api.rigRun` answering `{ id, status: "held", steps: [...] }`
results in `state.finishedRun()` carrying `source: "rig"` and `status: "held"`,
and the backend's `api.run` is **not** called. In `run-card.test.mjs`: a run
with `source: "rig"` and no `skill` renders one row per `run.steps` entry from
the run's own `says`, shows **Stop** while `status === "running"`, and renders
no "It's wrong" / undo control when finished.

- [ ] **Step 2: Run them to verify they fail**

Run: `node new-chrome-extension/src/background/finishing.test.mjs && node new-chrome-extension/src/panel/run-card.test.mjs`

- [ ] **Step 3: `api.rigRun` and `api.rigAbort`**

In `api.js`, beside `run`:

```javascript
  /** A run the rig is performing. The rig's `outcome` is the panel's `status`;
   * its steps are `{order, says, verdict}` and the card wants `{index, outcome}`. */
  async rigRun(runId) {
    const [base, token] = await Promise.all([state.rigUrl(), state.rigToken()]);
    const r = await fetch(`${base}/v1/runs/${encodeURIComponent(runId)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) throw new ApiError(r.status, `the rig has no run ${runId}`);
    const run = await r.json();
    return {
      id: run.id,
      source: "rig",
      status: run.outcome,
      steps: (run.steps || []).map((s) => ({ index: s.order, outcome: s.verdict, says: s.says, reason: s.reason })),
      withheld: run.withheld || [],
    };
  },
  async rigAbort(runId, deviceId) {
    const [base, token] = await Promise.all([state.rigUrl(), state.rigToken()]);
    await fetch(`${base}/v1/runs/${encodeURIComponent(runId)}/abort`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ device_id: deviceId }),
    });
  },
```

- [ ] **Step 4: `noteFinished` asks the right process**

```javascript
async function noteFinished(active) {
  try {
    const run = active.source === "rig" ? await api.rigRun(active.runId) : await api.run(active.runId);
    if (run.status === "running") return;
    await state.setFinishedRun({
      id: run.id,
      source: active.source || "backend",
      status: run.status,
      steps: run.steps || [],
      withheld: run.withheld || [],
      derived: run.derived || {},
      reversal: run.reversal || null,
      failure: run.failure || null,
      wrongBecause: run.wrong_because || null,
      at: Date.now(),
    });
  } catch {
    /* unchanged */
  }
}
```

and `checkFinishing` passes `active` rather than `active.runId`.

- [ ] **Step 5: The card**

In `panel.js`, where a finished or active run is rendered: when `run.source === "rig"`,
build the step rows from `run.steps` (`says` as the intent text, `outcome` for
the glyph) rather than from `skill.latest.steps`; wire **Stop** to
`api.rigAbort(run.id, await state.deviceId())`; and do not render the
"It's wrong" / undo controls. When finished with `withheld.length`, render a
short line under the card: *"dry run -- N write(s) shown on the rig, not sent"*.
Reuse `runCard`'s structure; do not fork it -- add a `source` branch where the
step list and the buttons are chosen.

- [ ] **Step 6: Run everything, commit**

```bash
make test-extension
git add new-chrome-extension/src/background/service-worker.js new-chrome-extension/src/background/api.js new-chrome-extension/src/panel/panel.js new-chrome-extension/src/background/finishing.test.mjs new-chrome-extension/src/panel/run-card.test.mjs
git commit -m "feat(extension): the panel shows a rig run, and asks the rig how it ended"
```

---

### Task 10: The runner meets a real browser

**Files:**
- Modify: `docs/new-agent-doc-arc/findings.md` — a new section, *A run performs*
- Modify: `docs/superpowers/specs/2026-09-03-model-first-workflow-mining-design.md` — the decision table's *How it executes* row gains one line naming the backend bridge as the governance path, not the execution path

This is verification 6 and 7 from the spec, and it needs two things this plan
cannot supply: the operator's Chrome with the extension pointed at the rig, and
a WMS session. What **can** be done unattended is done first and reported as
such; what needs a person is stated as the measurement it is, with the exact
commands, and left for them.

- [ ] **Step 1: The whole loop against a fake browser, end to end over HTTP**

A script, not a test: `new_agent_arch/scripts/dry_run.py`. It starts the app
with a `FakeChannel` scripted to answer every look and every perform as a
success, starts a dry run of each of the eight real workflows from `rig.db`
over `POST /v1/runs`, and prints per workflow: steps, verdicts, what was
withheld, cost. This proves the chain from door to record with no model call
either — use a `FakeAsker` that plans `ui.perform` with the primary gesture's
own kind and answers every verification `held`. Print the eight withheld writes
in full: they are what a person will read before the first live run.

- [ ] **Step 2: Then the real one — written down for the operator**

In `findings.md`, under *A run performs*, the exact recipe:

1. In the extension's options page, set the rig URL and token. The extension dials `ws://…/v1/agents/<device>/commands`; `GET /v1/devices` on the rig lists it.
2. Sign in to the WMS in that Chrome.
3. On the rig's page, open `Create Work Area NEWTESTS`, press **run**, leave **live** off, start.
4. Record what happened: each step's verdict and `matched_by`; the withheld POST; the run's cost; the extension's own `sro.lastError`.
5. Then a **different** job's write — `Create Work Area TWOTEST`'s — is what verification 7 refuses: the run's allowlist is that workflow's own systems, so a planned `navigate` to any other origin is refused before it is sent. Record the `refused` step.

State plainly in the same section: the dry run against a fake browser proves
the chain; only the real one proves the claim, and it has not been done until
this section says it has, with the numbers.

- [ ] **Step 3: The one-line correction to the decision table**

Under *How it executes* in the spec, append: *"`backend/src/sro/application/skill/from_rig.py` and its siblings turn a mined workflow into the backend's skill shape — recorded calls with values substituted — for the backend's promotion ladder. That is the governance path anything unattended must pass through; it is not how a run performs. `new_agent_arch/src/rig/runner.py` is."*

- [ ] **Step 4: Commit**

```bash
git add new_agent_arch/scripts/dry_run.py docs/new-agent-doc-arc/findings.md docs/superpowers/specs/2026-09-03-model-first-workflow-mining-design.md
git commit -m "docs: a run performs -- the chain proven against a fake browser, the claim left for a real one"
```

---

## Self-review

**Spec coverage.** *The runner* — locators from evidence (T4), origin per step (T4), Flash plans one command (T5), extension performs (T1/T2), verify against state (T6), Pro retries once then stop and ask (T7), `matched_by` as health signal / stale (T7), `allow_focus` from the door (T8). *Entering a run* — chat offers (T8), form fallback prefilled (T9). *What this must refuse* — origin allowlist (T7), dry first execution (T7), step budget (T7), no fabricated citations (already enforced at mining; the runner reads only stored workflows), no grounding (inherited), no File API screenshots (inline via `Part.from_bytes`, T5/T6), nothing unattended (no scheduler; T8's door is the only start). *Verification 6 and 7* — T10. **Gap named, not hidden:** "Still failed: stop and ask" — the run stops and records; nothing yet notifies a person beyond the page showing `stopped`. That is the page, which is a door a person has open.

**Added after the owner's note that everything will be done by the rig** — so every browser state a real job passes through is the runner's, not an edge case: the planner is told the page each step was demonstrated on (T5) and a `navigate` is a pre-step that does not spend the rescue (T7), which is what a deep, many-screen job needs; and the extension's panel treats a rig run as a first-class run, asked of the rig and stoppable at the rig (T11). Task 10 runs after Task 11.

**Placeholder scan.** None. Every code step is complete.

**Type consistency.** `channel.Answer` is imported as `Reply` wherever `models.Answer` is also in scope. `Look(url, screenshot, digest)` is positional in tests and keyword in the runner — same three fields. `Planned.kind` values match `KINDS ∪ {"none"}`. `Verdict.by` values match `runs.py`'s `verdict_by` free text. `run_workflow`'s signature is identical in T7's tests, T8's route and T10's script.
