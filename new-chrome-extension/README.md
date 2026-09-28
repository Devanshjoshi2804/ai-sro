# SRO Chrome extension

Continuous observation, in the operator's own Chrome. It records and it
watches; it never starts or drives a run. The backend starts every run -- a yes
in the conversation, a mail it acts on, a press in the console -- and Steel runs
it.

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

## The side panel

Clicking the toolbar button opens a panel docked beside the tab. It is not a
second console: it renders natively only what needs `chrome.*` or the current
tab -- the REC state, pause, the run the backend is performing with a way to
stop it, purge, and what was learned narrowed to the tab's host --
and links out to the console for everything else, so no review screen exists
twice.

The console used to be framed inside the panel, behind a credential handshake:
the console announced itself with `sro.ready`, the panel answered with the
token addressed to that one origin, and the console confirmed. That frame is
gone -- a 360-pixel console behind a per-extension line of configuration, for
a screen that is a full-width application. "Open the console here" now trades
the tab beside the panel for the console's address; "Console ↗" opens it in a
new tab. Either way the token never leaves the worker for the panel: the
console is on its own now for authenticating itself.

Set the console's address in Settings; leave it empty and the panel still does
everything only it can do, and says so rather than opening nothing when asked
for a console with no address set.

## Deleting your own evidence

The options page has a "Delete the last hour" button, and it does both halves:
`DELETE /v1/observations?since=…` on the server, and the queue on this device,
which has not reached the server yet. Deleting one and not the other would
upload the hour the operator just asked to be rid of, on the next tick.

It asks twice before doing it, in the page rather than in a modal — a dialog
raised from an extension page blocks the very service worker being asked to do
the deleting — and forgets it was asked after five seconds.

## No command channel

This extension used to dial `WS /v1/agents/{device_id}/commands` and perform
runs in the operator's own tab -- `ui.perform`, `http.send`, `navigate` -- and
to start runs itself from offers it made off the operator's gestures, from
page rules, and from Retry, Undo and Run buttons. That was a second engine
beside the backend's, and on QA (2026-09-28) it turned one yes into three
runs, started a job because somebody opened their mail, and stopped most of
its own runs by losing the tab. All of it is gone. A run is asked for in the
conversation and started by the backend; the panel draws it and can stop it.

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
