# Blue Yonder SCE knowledge base

A recorded description of a live Blue Yonder SCE warehouse-management instance: its screens, its
HTTP resources, the payload keys behind its forms, and the status contract of its writes — captured
by driving the real application, not read off a specification. No specification exists.

This is the thing CONTEXT.md §9 lists as *"waiting on someone else: Blue Yonder sandbox URL and
credentials, to build Phase 1 against reality"*. Reality is now in this folder.

Read [`../docs/13-blue-yonder-knowledge-base.md`](../docs/13-blue-yonder-knowledge-base.md) for what
it changes about the design. This file describes the contents and the rules they were recorded under.

## The one rule

**Evidence outranks prose.** Every operational claim here points at a stored request/response pair.
Where a written recipe and `http/exchanges/` disagree, the exchange is right and the recipe is a bug.

That rule exists because it was earned: an early pass documented `transportEquipmentTypes` as a
verified resource. The verification was "a GET afterwards returned 404, so the delete worked" — on a
route that had never existed, and returns 404 forever. Six documented behaviours were fiction. See
`blue-yonder-sce/http/claims.json`, which records what survived and what did not, by name.

## Evidence levels

Every claim carries one. They are not decoration; the lower two do not support automation.

| level | meaning |
|---|---|
| `asserted` | written down, no stored evidence |
| `observed` | seen once, recorded |
| `reproduced` | re-run deliberately and got the same result |
| `round-trip` | create → read back → update → delete → confirmed gone, all recorded |

## What is in the box

```
blue-yonder-sce/
  http/                 THE canonical evidence. Everything else is derived.
    exchanges/*.jsonl   1,074 full request/response records; every WM data endpoint called at least once
    status-matrix.json  every test case × resource cell, each backed by a stored exchange
    claims.json         23 claims with verdicts, including the falsified ones
    flows/*.json        35 multi-call flows with the value edges between them
    recipe-audit.json   the written recipes checked against the evidence
  index/
    app-map.json        316 screens: routes, 3,412 grid columns, toolbar actions
    form-models-all.json 84 captured Add-form field models: JSON key, label, required, type, maxLength
    field-dictionary.json 382 payload keys, 340 joined to their business meaning (96%)
    api-endpoints.json  551 endpoints with the screens each is seen on
    read-shapes.json    what 232 resources RETURN: 2,032 distinct fields, typed, with examples
    a11y-map.json       ARIA graph vs component model for all 316 screens
    a11y-trees.jsonl    the full ARIA snapshot of every screen
    write-endpoints.json the write catalogue, derived from the exchanges rather than hand-kept
    coverage.json       six completeness dimensions per screen — measured, not asserted
    wizards.json        multi-step Add dialogs, step by step
  md/                   the vendor help corpus converted to markdown, 587 pages, 1:1 with raw/
  raw/content/          the crawl verbatim: 585 help pages as fetched, unmodified
  recipes/              human-readable per-resource procedures — SECONDARY to http/
  images/               128 screen and help images
tools/                  the capture harness (Playwright over CDP, ExtJS-aware)
SCHEMA.md               the store contract: what a record must contain
PLAN.md                 definition of done, and why capture cannot be parallelised
STATUS.md               where each artifact lives and how it got there
```

## The vendor help corpus

The product's own documentation site was crawled in full and is here three times over, because each
form is useful for something different:

| form | what it is | size |
|---|---|---|
| `raw/content/` | 585 help pages exactly as fetched | 32 MB |
| `md/` | 587 markdown files, 1:1 with the crawl, front-matter carrying `url`, `toc_path` and a `source_sha1` back to the original | 7.6 MB |
| `index/*.json` | the corpus taken apart into queryable pieces | |

What the extraction produced:

| file | contents |
|---|---|
| `index/fields.json` | **7,741 field definitions** — the visible label and its business meaning |
| `index/procedures.json` | **1,029 procedures**, each with numbered steps, its TOC path, the nav entry it starts from, and the field tables it references |
| `index/pages.json` · `toc.json` | 586 pages with their table-of-contents position |
| `index/navigation.json` | the 20 top-level navigation entries |
| `index/graph.json` | 586 nodes and the links between help pages |
| `index/ui-vocabulary.json` · `icons.json` | the product's own words for its controls; 128 icons |
| `index/manifest.json` | product, version, Flare build, crawl timestamp, scope |

**Why this half matters.** The live capture knows `supplierNumber` is a required 32-character
textfield; it does not know what a supplier *is*. The help corpus explains suppliers thoroughly and
never once mentions `supplierNumber`, because user documentation speaks in labels. Joining the two on
the normalised visible label connects them: **340 of 382 captured payload keys (96 %) now carry a
business description, the help page that defines them, and the procedures that use them** —
`index/field-dictionary.json`, built by `tools/build-dictionary.mjs`.

That join is what makes the base usable for intent resolution rather than only for replay.

## What is deliberately not here

- **Credentials, cookies, CSRF tokens.** Stripped at write time by the recorder. Verified: the only
  request headers stored across all 682 exchanges are `accept` and `content-type`.

## Honest coverage

`index/coverage.json` measures six dimensions per screen. It is not flattering, on purpose:

| dimension | complete |
|---|---|
| structure (columns, actions) | 314 / 316 |
| read APIs identified | 273 / 316 (40 n/a — screens observed to issue no call at all) |
| read shapes recorded | 273 / 316 — **nothing outstanding** |
| form model captured (creatable screens) | 85 / 85 — **complete** |
| write APIs proven | 73 / 85 creatable |
| failure modes recorded | 72 / 85 creatable |
| **screens complete on all six** | **298 / 316** |

**API surface: 338 of 338 WM data endpoints have at least one stored call.** What is left out is
deliberate: 166 `/data/WM/rpux/*` and 45 `/refs/pageBuilder/*` endpoints, which serve grid columns
and page layout to the UI rather than warehouse data.

What remains open is stated in the same spirit. `pickMethods` and `releaseRules` are proven, but only
as composites — see the claims of the same name. `workOperations` remains unfixable: its DELETE answers 200 and does not delete, and one
throwaway row is stuck there.

Reads are done: every screen that issues a call has its resources and a recorded response body. The
remaining work is a short list: 11 creatable screens with no proven create, 2 screens that render
nothing at all (confirmed empty on a second look), and 3 operational screens whose reads were never
seen. Every Add form in the application has now been captured.

**Not every unproven write is a missing payload.** Handling Units is blocked by a missing
PREREQUISITE RECORD: its type combo lists only serialized handling unit types and this instance has
none. That is a different repair from a wrong body, and only walking the screen revealed it.

**A screen's write target is not always in its read set.** Billing saves to `billingFilters` and WCS
Integration to `warehouseControlSystems` — resources that appear in no read shape and no screen's
resource list. Only watching a Save found them.

**Five screens cannot create from their main form at all.** Pick Methods, Handling Units, Existing
Customers, Inbound Pallet Build and Item Class Levels block Save client-side until their sub-editors
are configured, and send no request. Their record is not a flat row, so no payload can be derived
from the form model — see the `composite-create-screens` claim.

**There are three create shapes in this app, not one:** a flat row; a row with a nested array
(`pickMethods` carries its `pickReleaseRules[]`); and an array posted to a `/batch` route (Hold Types
saves through `POST /wm/codes/batch`). A create strategy derived from form models alone produces the
first shape every time and is wrong on the other two. Where a screen refuses every generated body,
capture its Save — `tools/cdp/capture-ui-save.mjs` found both exceptions in one run each.

The failure-mode dimension is closed on every resource where exercising it is safe. Four are
refused on purpose and 5 screens stay incomplete because of it: `warehouses` (the site record this
capture runs inside), `locations` (61,912 live rows, wizard create), `buildings` (parent of every
location), `workOperations`, `packingConfigurations` — whose create answers 201 while producing a
record the API can neither list, fetch nor delete — and `holdDefinitions`, which accepts a create and
then refuses to delete it (422 on a permission check) or relabel it (PUT 200 that does not persist).
That is the honest floor — closing those numbers would mean damaging
the instance everything else depends on.

## How to filter a collection

`query=[{"column":"<jsonFieldName>","operator":"EQ","value":"<v>"}]`, ANDed across clauses. Operators
are upper-case and few: `EQ NE GT GE LT LE`. There is no `LIKE` — a `%` wildcard inside an `EQ`
value does prefix matching. The range operators genuinely compare (verified on four resources
against the real distribution of a numeric column), so date and quantity bounds work. Columns are the camelCase JSON names the resource returns, **not** the DB
column names its 422 errors quote. Full spec in `index/query-dsl.json`.

**Most columns are not filterable, and they fail silently.** Measured across **152 resources and
1,051 columns: 402 filterable, 649 not**. `addresses` filters on `addressId` and `addressName` but
not on `city` or `state` — with a value taken out of its own row. **43 resources have no filterable
column at all** and can only be paged. There is no pattern to infer it from (`*Code` 57%, `*Id` 42%,
everything else 31%), so `index/filterable-columns.json` holds the measured answer per resource.
Check it before trusting an empty result: on an unproven column, empty means unknown, not absent.

**Three operational writes are proven, and the convention is clear.** All of them PUT or POST an
**array of whole records** to a `/batch`-style route — never an id:

| action | endpoint |
|---|---|
| Adjustments ▸ Approve | `POST /wm/inventoryAdjustmentApprovals/async` |
| Work Queue ▸ Suspend Work | `PUT /wm/work/suspendDirectedWorks/batch` |
| Work Queue ▸ Resume Work | `PUT /wm/work/resumeDirectedWorks/batch` |
| Work Queue ▸ Assign User | `PUT /wm/work/async` with `assignedTo: "ABELOT"` |
| Work Queue ▸ Unassign | `PUT /wm/work/async` with `assignedTo: ""` |

**Two shapes, and the endpoint does not tell you the action.** Suspend and Resume have dedicated verb
routes; Assign and Unassign share one generic update route and differ only in the field they change.
A replayed call is only as safe as the body it carries.

Suspend/Resume is a reversible pair and was run as one: work 5490663 went PEND → SUSP → PEND, so the
warehouse ended where it started. An executor must therefore read the record before writing it.

**One operational write is now proven end to end.** `Inventory ▸ Adjustments ▸ Approve` posts an
**array of full adjustment records** — not an id — to `POST /wm/inventoryAdjustmentApprovals/async`,
and the 200 is an **async receipt**, not a result: `{asynchronousResourceGroupId, complete: false}`.
Poll `/async/{id}` until `complete: true` and read `/async/{id}/resources` for per-item
`asynchronousStatus` and `errorCode`. Effect verified on both sides — queue 9→8, on-hand 66→65 CS.
Contrast the adjustment CREATE, which answers 200 with `approvalRequired` and moves nothing. See
`http/flows/approveAdjustment.json`.

**Four vocabularies name one field, not three.** The a11y tree says `Description`, a Configuration
request body wants `businessUnitDescription`, the API's 422 quotes the DB column `lngdsc` — and
operational forms are addressed in DB columns too: Plan Wave's 22 fields are `dlvnum`, `totpcs`,
`from_late_shpdte`, `prtnum`, `l_ordnum`. A UI plan for the operational tier and a payload for the
Configuration tier cannot share a field dictionary.

**Approve is a two-stage action.** The button raises a form — `reasonCode` (required, 27 options,
two of which say *DO NOT USE* in their own labels), `comment`, and `generateCycleCount` (default
off, and a real side effect). The request only goes on OK. Other actions render as cards or inline
panels instead of windows, so "no dialog appeared" is not evidence an action ran — only observed
traffic is. See `index/operational-forms.json`.

**The operational verb inventory is enumerated.** 95 distinct actions across 24 screens —
`Receive Inventory`, `Auto Receive`, `Allocate`, `Cancel Picks`, `Suspend Work`, `Hand Over`,
`Change Carrier`, `Assign Lane` — in `index/operational-actions.json`. Menus were opened and read;
nothing was activated. **None has a recorded request yet**: each needs an approved capture, and the
only operational write ever observed here answered 200 with `approvalRequired` and moved no stock.

The other 83 operational screens are mostly **monitors**: 69 more domain verbs sit on 25 of them
(`Approve`/`Reject` on Adjustments, `Confirm Shipment`, `Start Audit`/`Repair All`, `Bundle`,
`Update Shipments`), and 16 carry nothing but export/print/refresh/filter. So the operational write
surface is ~65 screens, not 123 — see `index/toolbar-actions.json`.

**Records publish their own relationships.** A shipment carries `*_uri` links to its orders, picks,
waves, shipmentLines, handlingUnits, crossdocks and manifestDetails; a trailer to its inboundLoads,
stagingLocations and workflowResults. Two of those links are **operations, not collections** —
`trailers.closeWithWorkQueue` and `structuredInventory.editAsn`, identified by GET answering 405 —
and neither appears in the 551-endpoint catalogue. See `index/action-links.json`.

**State vocabularies** for 23 operational resources are in `index/status-vocabulary.json`, including
the shipment lifecycle: `R` Ready, `I` In-Process, `S` Staged, `L` Loading, `D` Loaded, `C` Load
Complete, `X` Transfer, `B` Cancelled.

## Two findings worth reading before writing any client

**The accessibility tree cannot drive this app.** Measured across all 316 screens: 3,699 visible
ExtJS buttons, **0 reachable by ARIA role and name**; 260 screens expose no `button` role at all, and
51,176 of ~80,000 nodes are grid cells. Payload keys never appear. See
`blue-yonder-sce/md/why-not-accessibility-tree.md`.

**`limit` is not universally honoured.** Eleven resources ignore it and return the whole table — the
same `limit=2` request that gives two rows elsewhere returned 7,808 rows from `appointments` and
13,883 from `userOperations`. They are marked `honours_limit: false` in `read-shapes.json`. Any
client needs a response-size guard rather than trust in the parameter.

## Reproducing any of it

The harness is in `tools/`. It attaches over CDP to a Chrome you have already logged into:

```bash
chrome --remote-debugging-port=9222 --user-data-dir=/tmp/by-profile
# log in by hand, then:
node tools/cdp/probe-resource.mjs read codes        # record a resource's read contract
node tools/cdp/map-forms.mjs configuration          # capture Add-form models
node tools/cdp/a11y-vs-ext.mjs "#wm.config/..."     # compare the two views of a screen
```

Session caveats that cost real time to learn are in `PLAN.md` and `blue-yonder-sce/recipes/README.md`.
The two worst: the session lives in a **session cookie**, so restarting Chrome means logging in again;
and the SPA **attaches one iframe per screen visited and never releases them** — 333 accumulated
frames crashed the renderer, so any long-lived session must reset periodically.
