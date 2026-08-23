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
