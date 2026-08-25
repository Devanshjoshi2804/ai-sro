# SRO Chrome extension

Continuous observation and in-browser execution, in the operator's own Chrome.

Read first:

- [`docs/14-extension-protocol.md`](../docs/14-extension-protocol.md) — the
  frozen contract between this directory and the backend. Everything this
  extension sends or receives is specified there.
- [`docs/07-adr/008-passive-observation.md`](../docs/07-adr/008-passive-observation.md)
  — why observation is passive, and the controls that are not optional.
- [`docs/07-adr/009-the-extension-is-an-adapter.md`](../docs/07-adr/009-the-extension-is-an-adapter.md)
  — why this extension implements existing ports rather than inventing a runtime.

## Ownership

This directory belongs to whoever owns the extension track. Nothing in
`backend/src/sro/` is edited from here, with one exception:
`backend/src/sro/infrastructure/steel/recorder.js` is the shared page recorder
and is owned by this track — the server-side capture adapter consumes it as it
is. It is listed under "do not change casually" in `AGENTS.md`; read the capture
invariants there before touching it.

The backend track does not edit anything in this directory.

## Running it

```bash
# 1. the mock, or the real backend on :8000
python3 mock-server/server.py

# 2. chrome://extensions -> Developer mode -> Load unpacked -> this directory
# 3. the extension's Details -> Extension options
#    backend  http://127.0.0.1:8000
#    token    make token tenant=acme principal=you   (from the repo root)
```

Against the real backend, observation is off until somebody switches it on for
the tenant -- that is the consent gate, not a bug:

```bash
make observe tenant=acme args="--on --exclude payroll.acme.com"
```

The badge reads `REC` only when a credential, a device, an enabled policy and
neither pause all agree. When it does not, the options page says which one is
missing, and it is never guessing: everything on that screen comes from the
service worker's own state.

## Screenshots

A gesture on an allowed page is illustrated by a PNG of what the operator was
looking at, uploaded to `/v1/observations/artifacts` and keyed to the gesture it
follows by `frame_index`. Four things bound it, and all four are enforced here
rather than by the backend:

- the tenant's `capture_screenshots`, which is off unless the policy says on;
- the tenant's `screenshot_max_per_minute`, spent only on a picture that was
  actually taken;
- the host of the whole document the gesture's frame sits in, so an allowed
  widget inside an excluded page is never photographed;
- the device's `daily_budget_bytes` — pictures are the first thing the queue
  gives up when it is over, before response bodies and long before a gesture.

Chrome adds a fifth of its own: it refuses more than two captures a second.

Once the batch carrying a gesture is accepted, its picture moves to a store of
its own keyed `batch_id:frame_index`, and uploads from there on the same alarm.
So an upload that fails is retried without re-sending the batch, and staging the
same batch twice replaces the row rather than queueing a second copy. Three
failed attempts and the picture is dropped, loudly — the options page says so.

## Teaching a task

Passive capture is cheap and invisible on purpose. The teaching tier is the
opposite: the operator opens the system, presses **Start teaching** on the
options page, does the task once, and presses stop. While it runs, the extension
attaches `chrome.debugger` to that tab and takes an accessibility tree at every
gesture — the one view that says what a control *is* rather than where it sits
today, and what induction needs to build a locator that survives a re-render.

Chrome banners the tab for as long as it is attached, which is right: this is
deliberate, it is short, and the operator should be able to see it stop.

The tab taught in is the last ordinary page they were on, not the options page
they pressed the button in. Start flushes everything captured so far as passive
work, stop uploads the demonstration's own evidence and only then seals the
recording — a batch never straddles the moment teaching began or ended, because
the backend refuses teaching evidence that names no demonstration and passive
evidence that names one.

## Deleting your own evidence

The options page has a "Delete the last hour" button, and it does both halves:
`DELETE /v1/observations?since=…` on the server, and the queue on this device,
which has not reached the server yet. Deleting one and not the other would
upload the hour the operator just asked to be rid of, on the next tick.

It asks twice before doing it, in the page rather than in a modal — a dialog
raised from an extension page blocks the very service worker being asked to do
the deleting — and forgets it was asked after five seconds.

## The command channel

The extension dials `WS /v1/agents/{device_id}/commands` and answers what comes
down it: `ui.perform` and `ui.perform_at`, `ui.url`, `screenshot`, `navigate`,
`http.send`, `abort`. Every command is answered exactly once, including with an
error — a command left unanswered reads to the backend as a device that went
away, which fails the run by blaming the browser rather than the page.

A run that may take the screen says so. `allow_focus` on the payload is the
trigger's decision, never this browser's: with it, a tab on the run's origin is
brought forward so it can be photographed and driven; without it, a command that
would move the operator's screen is refused as `focus_not_permitted`.

The run names the page. Every command that acts on one carries `origin`, and the
extension drives a tab on that origin rather than whatever is frontmost — a
browser has a dozen tabs and only one of them is the system a skill was taught
on. No tab on it is `no_tab_for_system`, which the backend counts as a device
problem rather than a skill that has drifted.

Three things are worth knowing before changing any of it:

- **`ui.perform` runs in the page's realm**, because the component locator is a
  question only the application's own framework can answer. `http.send` runs in
  the isolated world instead: same origin and the same cookies, but not the
  page's patched `fetch`, so a replayed request is never captured as the
  operator's own.
- **A tab being driven is not captured.** Gestures and requests from it are
  dropped for the length of the command plus a settle window. Without that, the
  miner learns a task from this extension replaying that task.
- **The socket is the worker's lifetime.** Chrome evicts an idle service worker
  after 30 seconds and takes the socket with it, so a keepalive goes up every
  20 seconds and every alarm tick re-dials.

While the operator is making gestures the extension sends `busy`, and the
backend holds new commands for the shorter of that window and half the
command's deadline — enough that a replay does not land in the middle of
somebody typing, not enough for a browser to veto the work.

The operator's own pause does not close the channel. That switch means "stop
watching me"; running a skill they asked for is not watching, and a device that
goes unreachable whenever somebody pauses observation is a device nobody can
schedule work on. An administrator's pause does close it.

## Working without the backend

`mock-server/` implements the frozen contract with canned responses. Build the
whole extension against it and point at the real API when the endpoints land.

Request and response types are generated from the committed
`frontend/openapi.json` with the `openapi-typescript` the repo already depends
on. That file is refreshed by the backend track with `make types`; read it, do
not edit it, and do not copy it here.

## How the two halves are proved to fit

`fixtures/` holds golden payloads produced by this extension against a real WMS.
`backend/tests/contract/test_observation_payloads.py` loads those exact files and
asserts they parse into domain objects and satisfy every invariant. Neither side
edits the other's code; a break in either half fails both people's `make check`.

The credential lives in `chrome.storage.local`, not `session`: `session` is
cleared when Chrome restarts, and an operator who has to paste a token every
morning is an operator who turns the extension off.

Regenerate them with `make fixtures`, which drives a real Chrome with this
extension loaded and writes what it actually emitted. Never by hand-editing the
JSON — a hand-written fixture proves the fixture, not the extension.
