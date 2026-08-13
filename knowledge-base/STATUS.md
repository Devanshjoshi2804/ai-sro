# Status — Blue Yonder SCE knowledge base

Last updated 2026-08-12. Everything below points at stored evidence; nothing here is asserted.

## Where this started, and what was actually wrong

The repo held a 54-entry write ledger marked "verified", a 251-line audit log, and 15 prose
recipes. An audit on 2026-08-12 found the whole thing was **not re-checkable**:

- `write-endpoints.json` stored create bodies as English prose inside `notes`, so no agent could
  execute a single create.
- `write-audit.jsonl` looked like a proof log; 212 of its 261 lines were hand-written narrative,
  not tool output.
- Claims came from hand-driven browser sessions that read the UI and inferred what the wire did.

## Where it is now

| | then | now |
|---|---|---|
| Full HTTP exchanges stored | 0 | **241** |
| POST endpoints with an executable payload | 0 of 21 | **18 of 21** |
| Claims backed by a stored exchange | 0 | **13** |
| Claims re-tested under Playwright | 0 | 13 → **9 reproduced, 4 falsified** |
| Screens with a captured form model | 0 | **18 of 21** |
| UI lifecycle (create/edit/delete) captured | 0 screens | **9 of 10 grid screens** |
| Re-runnable verification tooling | none | `tools/cdp/*` |

## Where each thing lives

```
knowlegde_graph/
  SCHEMA.md                     the contract: record shape, 404 taxonomy, evidence levels
  STATUS.md                     this file
  blue-yonder-sce/
    http/                       PRIMARY EVIDENCE - everything else is derived from it
      exchanges/<resource>.jsonl  full request+response per probe, auth stripped
      status-matrix.json          per endpoint: which status codes were actually observed
      flows/lifecycle-<screen>.json  UI create/edit/copy/delete call sequences
      flows/<name>Duplicate.json     failure-path traces with dataflow edges
      claims.json                 every claim + whether Playwright reproduced it
    index/
      write-endpoints.json        the ledger, now carrying real `payload` bodies
      form-models.json            per-screen field model: label -> JSON field -> required
      captures/                   raw UI create captures
    recipes/                      human-facing prose, corrected where falsified
```

`http/` is the source of truth. When a recipe and `http/` disagree, `http/` wins.

## What the evidence established

**Server contract, measured across 19 resources** (`http/status-matrix.json`):

| case | result |
|---|---|
| create-duplicate | 409 on 14 resources; 422 on clients, customerTypes, carrierProNumbers; 201 on addresses (server-assigned id, no conflict possible) |
| create-empty | 400 everywhere (not 422, as previously assumed) |
| delete-again | 200 on 16; **422 on clientWarehouse; 404 on clients** — idempotency is per-resource, not a platform guarantee |
| read-missing | **400 = malformed id for that resource; 404 RECORD-MISSING = well-formed but absent** |

**Two structurally different 404s**, and conflating them is what let a dead endpoint pass as
verified for a day:

- `ROUTE-MISSING` → `{"message":"Not Found","url":"/ws/wm/…"}` — the endpoint does not exist
- `RECORD-MISSING` → `{"timestamp","responseId","errors":[…]}` — it exists, the record does not

Only `RECORD-MISSING` proves a delete. A "later GET returned 404" proof is circular on a dead route.

**Payloads cannot be derived from the API.** A failed create returns 422 naming the missing DB
COLUMN, but the API rejects that name in the body and wants a camelCase key that is not
mechanically derivable: column `lngdsc`, recipe said `description`, real key is
`businessUnitDescription`. Only capturing the request the app itself sends is reliable.

**Four falsified claims**, all from the same root cause — reading the UI instead of the wire:

1. *Suppliers duplicate leaves no orphan* → it orphans an address exactly like clients. The recipe
   had told automation authors this screen was safe to retry.
2. *Carriers duplicate is server-side* → the modal appears with **zero requests sent**.
3. *transportEquipmentTypes endpoint exists* → dead route.
4. *DELETE is idempotent* (my own claim, from a 9-resource sample) → false on 2 of 19.

## What cannot be automated, and why

**voiceDevices** — `POST /wm/devices` with `deviceClass: "V"` returns `404 errorCode -1403
"no rows affected"`. The identical body returned 201 earlier in the same session; a field-by-field
diff shows no meaningful difference. Reproduced at code lengths 4–7, with `voiceTerminalId` set and
blank. `deviceClass: "W"` succeeds throughout on the same endpoint.

Worse for automation: after the failed save the screen **wedges permanently** — the exception modal
can be dismissed but its masks survive, leaving the form unusable. Recovery needs the masks removed
from the DOM and a route change; dismissing the dialog is not enough (`tools/cdp/recover.mjs`).

**Rule: do not drive voice-device creation through this screen or this endpoint.** Treat it as
manual until the backend behaviour is understood.

**locations** — untested by policy: 25k+ real rows and a batch-create path, no provably isolated
throwaway target.

**packingConfigurations** — POST returns 201 with a completely empty body and the row is not
retrievable from the collection, so there is no id to address it by. Update/delete unverifiable.

## Automation notes that cost real time to learn

- **Collection listings lie about creates.** A newly created client returns fine by id but does not
  appear in `GET /wm/clients?query=[]&limit=400`. Never confirm a create from a listing.
- **Server-side paging.** The carriers grid holds 25 of 1581 rows across 64 pages. A new record is
  never on page 1; sorting and filtering the loaded page cannot surface it. Load the last page.
- **Two link mechanisms** for opening a record: `rpLinkColumn` renders
  `<span class="rpux-link-grid-column-link">` with a grid cellclick handler; `templatecolumn`
  renders `wm-grid-navigate-link-column` with no grid listener. Rows contain no anchors at all.
- **Toolbar buttons have no handler** — their listeners are scoped to a `WM.plugins.grid.GridActions`
  plugin. `doDelete` is `store.remove()` + `store.sync()`; `doCopy` is a client-side `record.copy()`
  and **cannot** emit a request, so Copy firing nothing is correct behaviour, not missing coverage.
- **A blocking modal poisons every subsequent step.** Always clear before acting.
- **The cleanup sweep has produced four distinct false negatives**: a stale marker list, a missing
  collection, unpaged reads on a 1581-row table, and a mid-scan navigation race. Treat any "clean"
  from a single unpaged read as unproven.

## What is next

1. **The flow graph** — the deliverable that was deferred. Inputs now exist: `form-models.json`,
   plus real dataflow edges (`addresses.data.addressId => clients.body.addressId`) and create/edit/
   delete sequences for 10 screens.
2. **The remaining screens** — 3 form models failed (`clientGroups` behind a tab, `locationTypes`
   wrong route, `locationAccessGroups` modal timeout).
3. **Nested sub-editors** — Service Levels, Handling Unit Types, COD Address. Zero coverage, and
   the newly observed sub-resources (`carrierServiceLevels`,
   `devices/{id}/consolidateAtPackStationZone`) suggest more.
4. **Tier 2/3** — Receiving, Shipping, Picking, Outbound Planner, Inventory ops. Zero coverage,
   and the bulk of the 189 undescribed routes out of 207.
