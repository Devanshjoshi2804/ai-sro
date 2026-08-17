# knowlegde_graph — canonical store

Everything learned about a target system lives here. Nothing authoritative lives outside it.

## Why this exists in this shape

The previous state of this repo failed an audit on 2026-08-12 for one structural reason: its
claims were not re-checkable. `write-endpoints.json` marked 54 endpoints "verified" while storing
create bodies as English prose, so no agent could execute one. `write-audit.jsonl` looked like a
251-line proof log but 212 of its lines were hand-written narrative rather than tool output. One
endpoint (`/wm/transportEquipmentTypes`) was marked verified against a route that does not exist,
because its proof — "a later GET returned 404" — is satisfied forever by a nonexistent route.

The rule that follows: **a claim is only as good as the recorded exchange that backs it.** Every
assertion here must point at a stored request/response pair produced by a re-runnable tool.

## Layout

```
knowlegde_graph/
  SCHEMA.md                        this file
  blue-yonder-sce/
    http/                          canonical HTTP evidence — the source of truth
      exchanges/<resource>.jsonl   every observed exchange, full request + full response
      status-matrix.json           per endpoint: which status codes were actually observed
      flows/<flow>.json            ordered call sequence for a driven UI flow
      edges.json                   dataflow edges: response value of call A used in request of B
      claims.json                  every prior claim, and whether Playwright reproduced it
    index/                         derived catalogues (endpoints, form models, write ledger)
    recipes/                       human-facing per-screen prose, derived from http/
```

`http/` is primary. `index/` and `recipes/` are derived views and must never contradict it; when
they do, `http/` wins and the others are corrected.

## Exchange record

One JSON object per line in `http/exchanges/<resource>.jsonl`:

```jsonc
{
  "ts": "2026-08-12T…",
  "tool": "tools/cdp/http-record.mjs",   // what produced this; never hand-written
  "case": "create-valid",                 // which probe in the battery
  "request": {
    "method": "POST",
    "url": "/data/WM/wm/clients",
    "query": { "siteId": "SG" },
    "headers": { "content-type": "application/json" },   // auth headers stripped, see below
    "body": { }                                           // parsed when JSON, else raw string
  },
  "response": {
    "status": 201,
    "statusText": "Created",
    "headers": { },
    "body": { },
    "kind": "OK"        // OK | ROUTE-MISSING | RECORD-MISSING | HTTP-<code>
  },
  "notes": "…"
}
```

### `kind` — why status codes alone are not enough

This deployment returns two structurally different 404s and conflating them is what let a dead
endpoint pass as verified:

| kind | shape | means |
|---|---|---|
| `ROUTE-MISSING` | `{"message":"Not Found","url":"/ws/wm/…","status":"404"}` | the endpoint does not exist |
| `RECORD-MISSING` | `{"timestamp","responseId","errors":[{"userMessage":…}]}` | the endpoint exists, the record does not |

Only `RECORD-MISSING` proves a delete worked. `ROUTE-MISSING` proves the opposite: there was never
anything there.

## Security

Auth material is **never** stored. `cookie`, `set-cookie`, `authorization`, `csrf-encrypt-token`
and `x-csrf*` are stripped from both request and response headers before any write to disk. The
recorder executes inside the authenticated page so it never handles a credential value at all.

## Evidence levels

Every claim carries one. Nothing may be reported as done at a level it has not reached.

| level | meaning |
|---|---|
| `asserted` | written down by a human or model, no stored exchange. **Not evidence.** |
| `observed` | one stored exchange exists |
| `reproduced` | re-run by a tool and matched a prior stored exchange |
| `round-trip` | create → read → update → read → delete → confirmed `RECORD-MISSING` |

`asserted` claims are carried as open work, never as coverage.

## What the instrument cannot see

Every one of the 266 stored exchanges was issued **from inside the authenticated page**, by
`fetch` running in the app's own frame. That is what makes the recorder safe — it never handles a
credential — and it is also a blind spot with a precise boundary:

**Any header the browser attaches on its own is untested here.** `Cookie`, `Referer`, `Origin`,
`User-Agent` and the `Sec-*` family were supplied by Chrome, never by the recorder, and were
stripped or ignored on the way to disk. So this base can say what the server does with a *body*
and a *route*. It cannot, from its own evidence, say which of those ambient headers the server
actually requires.

That is not hypothetical, and it is now reproduced here rather than taken on report
(`http/exchanges/businessUnits.jsonl`, cases `referer-*` and `out-of-page-*`):

| call | result |
|---|---|
| in-page, browser's own Referer | **200** |
| in-page, `referrerPolicy: no-referrer` | **opaqueredirect** — the browser blocked a 3xx |
| out-of-page, no Referer, `maxRedirects: 0` | **302 → `/portal`** |
| out-of-page, Referer set to the portal origin | **200** |
| in-page, Referer derived from the target URL | **200** — the value is not checked against the page actually open |

Two things follow. **The failure is silent by default**: an executor that follows redirects gets 200
and an HTML login page, which passes any check reading only the status code. And **`Referer` must be
synthesised from the target, not replayed and not dropped** — it is neither a semantic parameter nor
a safely-omitted client header, which is a category a two-run diff cannot discover.

**Standing rule: an exchange recorded in-page proves the route and the payload, not the header
set.** A claim that a call is replayable out-of-browser needs a probe that varies the ambient
header deliberately (`tools/cdp/probe-referer.mjs`), and until such a probe runs, the claim is
`asserted`.

## Verification provenance

Claims originally produced by hand-driven browser sessions (Claude-in-Chrome) are treated as
`asserted` until a scripted Playwright run reproduces them. Where the two disagree, the
disagreement itself is recorded in `http/claims.json` with both observations, rather than one
silently overwriting the other — a hand-driven session can succeed through timing or manual
recovery that a script cannot, and that difference is a finding about the app, not noise.


## The flow graph

`http/graph.json`, built by `tools/build-graph.mjs`, queried by `tools/graph-query.mjs`.

It is **derived, never authored**. An edge exists only because a recorded exchange shows it, and
each edge carries the evidence file it came from. Nothing is inferred from naming or convention —
that inference is precisely what produced the four false claims this knowledge base was rebuilt to
correct.

### Node annotations

Resource nodes carry three derived blocks beside their raw operation table. All three are computed
from the stored cases, never from a claim's prose:

| field | what it answers |
|---|---|
| `behaviour_warnings` | is this safe to retry, does a 200 on DELETE mean anything here, will a sampling read pull the whole table |
| `write_contract` | per method: the real path, the proof level, and the payload keys that worked — plus `creates_through` where a view's create goes somewhere else |
| `read_shape` | field count, rows in the recorded sample, and the status of that read |

The warning set is small and each member was earned by something that went wrong in capture:
`duplicate-create-succeeds` (3 resources), `ignores-limit` (11), `delete-unconfirmed` (2),
`create-refused` (4), `create-modelled-on-existing-record` (7), `creates-through-another-resource`.

A warning is only raised from a case that SUCCEEDED where success is the claim. Keying on the case
name alone once tagged three resources as composite-create when they had in fact refused the attempt
outright — the opposite conclusion from the same record.

### Node types

| type | meaning |
|---|---|
| `screen` | a UI screen: route, field model, required fields |
| `resource` | a REST resource: operations, observed status codes, payload template, id shape, gotchas |

### Edge types

| type | meaning |
|---|---|
| `reads` / `writes` | a screen issued this call, with the phase and status observed |
| `dataflow` | a value from one response appeared in a later request |
| `requires` | ordering constraint implied by a strong dataflow edge |

### Why dataflow edges carry a confidence

Matching a request value against earlier responses over-matches on **ambient** values. The client
id `----` appears in almost every response here, which produced edges like
`packingConfigurations -> addresses` describing no real dependency.

So each edge records how many responses carried the value. Seen in at most two (produced once,
plus its own echo) is a genuine server-assigned handoff and marked `strong`; anything wider is
`ambient` and does **not** imply ordering. Only `strong` edges generate `requires`.

Result: 3 strong handoffs (`addresses.addressId` into `clients` and `suppliers`,
`addresses.addressName` into `suppliers`) and 2 ordering constraints, rather than 13 edges of
which most were noise.

### Foreign keys in payload templates

Payloads were captured from real requests, so a foreign key still holds the id from capture time —
`suppliers` carried `addressId: "A000365885"`. Replayed verbatim, an executor would attach its new
record to an unrelated existing row.

Those fields are templatised, and identified from the dataflow edges rather than by name: a field
is a foreign key exactly when a strong dataflow edge lands on it. A name-based rule over-matched,
rewriting `warehouseId: "SG"` — a constant — as if it were a handoff.

### Queries

```
node tools/graph-query.mjs plan suppliers    # what must exist first, payloads, handoffs, hazards
node tools/graph-query.mjs resource clients  # operations, status codes per case, gotchas
node tools/graph-query.mjs screen printers   # required fields, what it reads and writes
node tools/graph-query.mjs hazards           # everything known to be unsafe or previously wrong
```

`plan` walks `requires` transitively, then prints the create order, the field handoffs between
steps with their evidence, each payload template, what a duplicate create returns, and any hazard
recorded on that path.
