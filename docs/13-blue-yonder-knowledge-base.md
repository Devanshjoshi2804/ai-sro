# The Blue Yonder SCE knowledge base

What we now know about the target system, how it was established, and the four places it contradicts
something this repository currently assumes.

The artifact is [`../knowledge-base/`](../knowledge-base/); its README describes the contents and the
rules they were recorded under. This document is about consequences.

## What it unblocks

CONTEXT.md §9 lists *"Blue Yonder sandbox URL and credentials, to build Phase 1 against reality"* as
waiting on someone else. That is no longer waiting. A live SCE instance has been driven, recorded and
audited: 316 screens mapped, 551 endpoints catalogued, 266 full request/response exchanges stored,
and nine resources taken through a complete `create → read back → update → delete → confirm gone`
cycle with every status recorded.

The decision table also carries *"Knowledge base | Live sandbox + recorded traffic only | **No spec to
validate a generated call against**"*. The consequence column can now be softened for this system:
there is still no vendor specification, but there is a recorded one, and a generated call can be
checked against `knowledge-base/blue-yonder-sce/http/status-matrix.json` before it is ever sent.

## Four corrections

### 1. SCE's browser traffic is REST, not MOCA commands

ADR 005 states: *"For Blue Yonder the 'network calls' are MOCA commands, so a recording of a wave
release yields a documented, schema-discoverable command sequence."*

Measured: of 551 endpoints the portal calls, **499 belong to the `WM` service and all of them are
REST** with a `{@type, data}` envelope — 315 on `/data/WM/wm/<resource>`, 161 on `/data/WM/rpux/`
(grid columns and filters), 22 named commands under `/data/WM/`. No MOCA command traffic was observed
leaving the browser.

(Re-counted from `index/api-endpoints.json`. An earlier draft of this document attributed all 499 to
the `/data/WM/wm/` prefix; that prefix holds 315. The conclusion is unaffected — every one of them is
REST — but the figure named the wrong set, and this base's own rule is that evidence outranks prose.)

MOCA is underneath — the REST responses carry a `moca-status` header (`2966` on a duplicate-key 409,
`-1` on a validation 422). That is better than the ADR's premise rather than worse: the transport is
an ordinary REST call that replays cleanly, and the MOCA error code still comes back for precise
failure classification. But a `network_plan` built expecting MOCA command syntax will not match what
a demonstration on the SCE web portal actually records.

The ADR's conclusion survives intact; its reasoning about the mechanism needs a correction.

### 2. L2 cannot rely on the accessibility tree for this app

Phase 2 is *"UI replay by accessibility ancestry"*, and capture stores `Accessibility.getFullAXTree`
at every gesture, with the stated example `dialog "Adjust" > form > button "Confirm"`.

Measured on four SCE screens (`knowledge-base/blue-yonder-sce/index/a11y-vs-ext.json`):

| screen | a11y nodes | `button` | `textbox` | Ext fields | payload keys in a11y |
|---|---|---|---|---|---|
| Location Preference Rules | 459 | 0 | 0 | 14 | 0 of 14 |
| Customer Types | 73 | 2 | 8 | 18 | 0 of 18 |
| Business Units | 18 | 0 | 2 | 2 | 0 of 2 |
| Carriers (1,581-row grid) | 9 | 0 | 0 | — | — |

Two things follow.

**Role coverage is erratic, not absent.** ExtJS 4.2.2 renders controls as nested `<div>`; some screens
surface roles and some do not. Absence would be easy — you detect it and fall back. Inconsistency is
the harder failure: a driver that finds a control by role on one screen and silently finds nothing on
the next looks like it works.

**Payload keys are never in the tree: 0 of 34 fields, every screen.** Three vocabularies name one
field and none derives from another — the label `Description`, the JSON key
`businessUnitDescription`, and the DB column `lngdsc` that the API's own 422 error returns. Only the
ExtJS component model holds all three ends together.

What to do about it is not "abandon the AX tree". Keep capturing it — ancestry is genuinely useful
where roles exist, and it is a good change-fingerprint. Add an **ExtJS adapter** for this WMS that
reads `Ext.ComponentQuery` and button `itemId`s, which is stable, is what the application calls its
own controls, and is already working code in `knowledge-base/tools/cdp/ext.mjs`. Treat "the UI plan's
control-finding strategy" as per-WMS, chosen at capture time, rather than one strategy for all.

The relevant nuance for capture: **the SPA updates the URL and `document.title` while leaving the DOM
frozen on the previous screen.** Both of those are unreliable load signals. A content fingerprint
must change before a frame is attributed to a new screen.

### 3. Retry safety is per-resource, and one resource has no uniqueness at all

`docs/12-execution-and-agents.md` states every mutating step carries an idempotency key so a retried
`POST /adjust` is not a double adjustment. Correct — and the recorded contract shows why the key
cannot be the only protection.

From `http/status-matrix.json`, all cells backed by stored exchanges:

| case | what was actually observed |
|---|---|
| `create-duplicate` | **409** on 14 resources, **422** on 3 — and **201 on `addresses`**, which has no uniqueness constraint: the duplicate is simply created |
| `delete-again` | **200** on 13 resources, **404 RECORD-MISSING** on `clients`, **422** on `clientWarehouse` |
| `read-missing` | **404** on 7 resources, **400** on 11 — a malformed id and an absent record are not the same answer |
| `update-missing` | **404** on 4, **400** on 4 |

So: a retried create against `addresses` silently produces a second record; "delete is idempotent"
holds for most resources and fails on two; and code that treats 404 as "gone" and 400 as "broken
request" will misjudge eleven resources.

This belongs in the executor as **data, not branches** — the status matrix is already a table.

### 4. The verifier must distinguish two different 404s

Read-back verification asks the WMS what it now believes. On this system a 404 has two meanings, and
they are distinguishable only by body shape:

```jsonc
// ROUTE-MISSING — the endpoint does not exist, and never did
{"message": "Not Found", "url": "/ws/wm/transportEquipmentTypes/X"}

// RECORD-MISSING — the endpoint exists; the record is gone
{"timestamp": "...", "responseId": "...", "errors": [ ... ]}
```

**Only the second proves a delete.** This is not hypothetical: an early pass here documented six
behaviours of a resource whose route had never existed, because "GET returned 404 afterwards" was
taken as proof. A verifier that accepts a bare 404 as a satisfied post-condition will confirm
deletions that never happened, on endpoints that never existed — and will do it consistently, because
a dead route returns 404 forever.

Every mutating verification needs the positive form: read back and assert the *record's* absence
signature, not the status code alone.

## Where it fits the phases

| Phase | What the knowledge base gives it |
|---|---|
| **0** Secret hardening | Confirms the exposure is real and immediate: the SCE session lives in a **session cookie** that does not survive a browser restart, so any long capture campaign re-authenticates repeatedly. Nothing may be recorded against this login until password capture is fixed. |
| **1** L1 network execution | The resource catalogue, the write contract, and per-resource retry semantics. `field-dictionary.json` (204 keys, 185 with business meaning) is a ready parameter dictionary; `status-matrix.json` is ready verifier policy data. |
| **2** L2 UI replay | The ExtJS control model and a working harness — plus the measured warning above about ancestry-by-role, and the wedge/iframe hazards that break any long browser session. |
| **3** L3 vision | Screen inventory and captures for grounding; the redaction target is narrower than feared, since the evidence store already demonstrates capture with auth headers stripped by construction. |
| **4** Chat and intent | 316 screens, 551 endpoints, and the vendor's entire help corpus — 7,741 defined fields and 1,029 named procedures — give the objective vocabulary a real domain to resolve against, in the product's own words rather than ours. |
| **5** Autonomy | The failure taxonomy that a circuit breaker needs, and an honest statement of which resources have proven post-conditions — the criterion for what may ever go autonomous. |

## On the provenance limit

CONTEXT.md §7 says a skill generated from a knowledge base *"cites nothing — there is no evidence it
was ever performed successfully"*, and that such skills must be a distinct kind.

That rule should stand. But the citation is no longer empty: a skill generated from this base can
cite the exchange that proves the call works — `http/exchanges/<resource>.jsonl`, a specific
`create-valid` record with its status and body, part of a completed round-trip.

That is evidence about **the system's behaviour**, not evidence that **a human performed this task
for this purpose**. It does not make a generated skill equivalent to a demonstrated one, and it must
not open the promotion ladder's front door. It does mean a generated skill enters review with a
verifiable claim attached instead of a plausible guess, which is the difference between a reviewer
checking work and a reviewer inventing confidence.

## What this does not give

Stated plainly, because the coverage table in the README is unflattering and should stay that way:

- **Read shapes are recorded for 4 of 316 screens.** Most GET response bodies are unknown.
- **Writes are proven for 9 of 85 creatable screens**, all in the Configuration tier. Operational
  screens — the ones that release waves and move inventory — are mapped read-only and deliberately
  not written to.
- **The `locations` create path is a multi-step wizard**, not a form, and its payload depends on the
  chosen location type. 61,912 rows, no proven create body. It has not been guessed.
- **This is one instance, one site (`SG`), one version.** Everything here is a recorded observation of
  that instance, not a vendor contract, and an upgrade can invalidate any of it. That is the same
  exposure the L1 rung already carries by design.
