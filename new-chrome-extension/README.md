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

Regenerate a fixture by capturing the real thing, not by hand-editing the JSON —
a hand-written fixture proves the fixture, not the extension.
