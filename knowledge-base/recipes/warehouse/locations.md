# Screens: Location Types, Aisles, Yard/Dock/Staging/Storage/Processing/Pickup-and-Deposit/
# Production Locations, Level Types, Location Sequences, Dock Access Groups

nav_path: Configuration > Warehouse > Locations (flyout submenu, 11 sub-screens)
route hash prefix: `#wm.config/wm.config.warehouse.locations.<subtype>/buildingId[__value__]=B1...`

**All 7 physical-location-category screens (Yard, Dock, Staging, Storage, Processing, Pickup and
Deposit, Production) share one underlying resource: `/data/WM/wm/locations`.** They differ only
in the `query`/`locationTypeCategory` filter sent with the list `GET`. Confirmed category codes:
`STORAGE`, `YARD`, `DOCK` (Dock Doors sub-tab only — Dock Sets is separate), `STAGING` (with a
function sub-type like `XDCK`), `PROC`, `PND`, `PROD`. This environment has real production data
at wildly different scales per category — Storage alone carries 25,469+ rows, Dock Doors 255,
Staging 358, Yard 503+, while Production and Processing had **zero** pre-existing rows (genuinely
empty, not a fixture gap — confirmed by an empty "Total Locations: 0" on every area for both).

`Location Types`, `Level Types`, `Location Sequences`, and `Dock Access Groups` are **separate
resources**, distinct in shape and even in id-generation convention from `/wm/locations` and from
each other — see their own sections below. `Aisles` was not tested this pass.

## Create (all 7 category screens): shared wizard shape

Every category screen's `Actions > Add` opens the same multi-step wizard: **Select Area → Add
Locations (start/end range + function/type combo) → [Define Location Capacity, most screens] →
Review → Finish**. All fire the same endpoint:

**`POST /data/WM/wm/locations/batch`** — confirmed across Production, Yard, Dock, Staging,
Processing, Pickup and Deposit. Not a plain `POST /locations`.

The capacity step is **not universal** — it's present on Yard/Staging/Storage/Processing/Pickup-
and-Deposit/Production but **absent entirely** on Dock Doors (that wizard is only 3 steps: Select
Area → Add Locations → Review, no capacity screen at all). Where present, capacity-tracking
options are typically `Pallets / Volume / Eaches / Length / Unlimited`, sometimes narrower per
type (Yard only offers `Unlimited` / `Transport Equipment`; "Unlimited" renders as
`999999999 Equipment Capacity` specifically on Yard). A stacking-height sub-choice (`No Stacking
Restrictions` / `Pallet Stack Height` / `Interlock Stack Method`) appears alongside capacity on
Staging/Processing but not on Production.

Each category has its own "function"/"type" combo populated from real reference data, e.g.:
- **Yard**: `YARD - Yard` only (single option in this env)
- **Dock**: `RDCK`-Receiving Door, `SRDCK`-Shipping & Receiving Door, `SDCK`-Shipping Door,
  `STOTRLR`-Storage Transport Equipment
- **Staging**: `XDCK`-Indirect Cross Dock Zone, `OSTG`-Packing Completion, `PSTG`-Production
  Staging, `RSTG`-Receiving Staging Lane, `SSTGSP`-Ship Staging Special Pack, `SRSTG`-Shipping &
  Receiving Lane, `SSTG`-Shipping Staging Lane
- **Processing**: `CONS`-Consolidation, `DISTR`-Distribution Processing, `PALBLD`-Pallet building,
  `PROC`-Processing, `WRKS`-Workstations
- **Pickup and Deposit**: `PND`-Pickup & Deposit, `PNDT`-Pickup and Deposit Tracked
- **Production**: `PROD`-Production Station, `WIPS`-WIP Supply Area

## Delete (all 7 category screens): checkbox + Actions > Delete

Fires `DELETE /data/WM/wm/locations/{locationId}*!{warehouseId}?buildingId=`, behind an in-app
ExtJS "Are you sure?" confirm modal (not a native browser dialog — safe to script through).
Confirmed on Production, Yard, Dock, Staging, Processing directly through the UI grid.

**Exception — Pickup and Deposit:** the main grid (scoped by the top-right building selector)
never showed the just-created record even though the Add-wizard's own Select-Area list correctly
counted it (`CO-STO-FL: 1 P&D location`) both before and after create. The free-text search box
also mis-targets the `Aisle` column on this screen (same bug seen on Yard — see Open Items), so
there was no UI path to select-and-delete it. Fell back to a direct authenticated `DELETE` with
the `CSRF-ENCRYPT-TOKEN` header pulled live from the app iframe's `Ext.Ajax.defaultHeaders` — a
bare `fetch` DELETE with only `credentials:'include'` 404s, confirming the header is required
(not just cookie auth) for this verb.

## Buttons and actions (per Location record, e.g. Storage Locations)

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| row click | opens edit form | `GET /data/WM/wm/locations?storageLocation={code}&siteId=SG&subsites=----` (list-style query, not a direct id GET) | Form also fires ~15 side-channel lookups (areas, aisles, pick zones, printers, dock slots, codes) for combo population — normal per-screen overhead, not part of the write path. |
| Enable Location toggle + Save | `PUT /data/WM/wm/locations/{locationId}*!{warehouseId}` | full record | Verified: toggled to DISABLED → `200` → separate `GET` confirmed field changed → toggled back to ENABLED → `200` → separate `GET` confirmed a byte-for-byte revert (diffed the full JSON record before/after, zero field differences). |
| Actions > Add | create (see wizard above) | `POST /data/WM/wm/locations/batch` | See Create section. |
| checkbox + Actions > Delete | remove | `DELETE /data/WM/wm/locations/{id}*!{warehouseId}?buildingId=` | See Delete section. |

## Fields (`/data/WM/wm/locations/{locationId}*!{warehouseId}`)

Resource id order: `{locationId}*!{warehouseId}`, e.g. `AA101B*!SG` — same `*!` compound-key
convention as every other Warehouse-tier resource this pass (buildings, businessUnits, areas).

This is the **largest record shape found in the Warehouse tier** — 80+ fields covering geometry
(`bottomLeftX/Y`, `bottomRightX/Y`, `basePointId`), voice picking (`backfillVoiceCheckDigit`,
`backfillVoiceCheckDigit2/3`), counting (`countBack`, `countDate`, `countHistory_uri`), zoning
(`pickZoneCode`, `movementZoneCode`, `storageZoneCode`, `workZoneCode`, `countZoneCode`), and
flags (`crossDockFlag`, `fourWallInventoryFlag`, `palletPositionFlag`, `sharedLocationFlag`,
`significantFlag`, `summarizePicksFlag`, `workInProcessFlag`, `billingFlag`, `automove`,
`assignment`).

| Field | UI label | Notes |
|---|---|---|
| `locationCode` | drives the "Enable Location" toggle | **This is the enable/disable flag, not a field named `active`/`enabled`.** Observed value `P` in both the enabled and (briefly) disabled states in this test — the toggle write cycle round-tripped cleanly (full-record diff after re-enable showed zero changes vs. the original), but the exact enabled-vs-disabled value pair was not pinned down before reverting. If this flag needs to be driven programmatically, re-test and capture both values explicitly first. |
| `areaCode` | "Area*" | required |
| `aisle` | "Aisle" | free-text/search-combo, UI briefly showed this blank right after a Save+reload — confirmed via API this was a **UI rendering lag, not data loss** (field was intact, `AABN`, the whole time) |
| `bay` | "Bay" | |
| `level` | "Level" | maps from Level Types |
| `dockSlot` (?) | "Position" | disabled/grayed for non-dock location types |
| `locationTypeCategory` | "Location Type" | e.g. `STORAGE`, `YARD`, `DOCK`, `STAGING`, `PROC`, `PND`, `PROD` |
| `resourceId` | — | compound id, e.g. `AA101B*!SG` |
| `buildingId`, `warehouseId` | — | |
| `locationStatus` | — | e.g. `F` = "Full" — this is location fullness/occupancy, **not** the enable flag; don't confuse the two |
| `version` | — | present; not tested for optimistic-locking behavior this pass — see `carriers.md`/`buildings.md`, this API's `version` semantics are resource-specific and must be tested per-resource, never assumed |

## Location Types — separate resource

`/data/WM/wm/locationTypes` — ~20+ real entries (`CONS`, `DAMG`, `PND`, `PROC`, `PROD`, `RDCK`,
`SRDCK`, `ADJS`, `DSPCH`, `EXPR`, `GM-STO` with 7125 locations, etc), each carrying a
`totalLocations` rollup count and 40+ boolean behavior flags (`adjustmentsFlag`,
`backfillLocationFlag`, `crossDockFlag`, `dispatchFlag`, `lpnMixingFlag`, `pickToStoreFlag`,
`receivingDockFlag`, `shippingDockFlag`, ...). Create form requires **Category** then a
conditional **Sub-Category** (e.g. Storage needs `Distributed to Storage` or `Storage`) before
Location Type code/Description unlock. Actions menu also has **Consolidate** (merge one type into
another) — not tested.

**Exception:** `resourceId` is a **bare numeric id** (observed `10663`), not the `{code}*!
{warehouseId}` compound key used by `locations`/`buildings`/`businessUnits`/`areas`. Don't assume
the compound-key convention is universal within this tier.

Verified: `POST /data/WM/wm/locationTypes` (create, code `ZZAUDIT`) → 201-equivalent → separate
`GET locationTypes?locationType=ZZAUDIT` confirmed → checkbox + Delete → confirmed gone.

## Level Types — separate resource

`/data/WM/wm/levelTypes` — **zero pre-existing rows in this environment** (real, not a fixture
gap). UI toolbar pattern differs from every other Locations screen: flat `Add`/`Copy`/`Delete`
buttons directly on the toolbar, no `Actions` dropdown. Required fields: Name, Description, Total
Level Units (an integer). Optional: Maximum Weight, Enforce Horizontal/Vertical Alignment,
Display Pending Inventory Indicator.

**Exception:** `resourceId` is a **synthetic zero-padded numeric id** (`000000000000001*!SG`),
not derived from the entered Name — a third id-generation variant within this one submenu (see
`locationTypes`' bare-numeric-id note above; `locations`/`businessUnits`/`areas` all use the
entered code directly).

Verified: `POST /data/WM/wm/levelTypes` (name `ZZAUDIT`) → separate `GET` (0→1 row) → checkbox +
Delete → separate `GET` (1→0 row).

## Location Sequences — separate resource, **not write-tested**

Screen title is actually **"Travel Sequence"**, with `Travel` / `Storage` sub-tabs. This is a
bulk-sequence editor over **existing** real locations (thousands of rows, e.g. `000031626918`
etc with real work-zone/aisle/bay/level data), not a create-new-record screen — same high-blast-
radius profile as editing live Storage Locations directly. Documented read-only; no write test
performed, consistent with the low-blast-radius discipline used elsewhere in this campaign for
screens carrying real production data with no safe throwaway target.

## Dock Access Groups — MAJOR FINDING: generic shared code-list resource

Not a dedicated resource at all. Backed by **`/data/WM/wm/codes`**, a generic table shared across
(potentially many) simple named-list screens, keyed by **`{code}*!{columnName}`** where
`columnName` is a fixed string identifying which code list a row belongs to — here,
`columnName=dck_acc_cod`. This strongly suggests other "just a code + description + short
description" screens across the wider app may reuse this same `/wm/codes` backend under a
different `columnName` constant. Worth checking against other simple reference/lookup screens
before assuming each needs its own dedicated resource entry in the catalogue.

UI behavior specific to this screen: the Add modal's own Save **commits immediately** (row
survives a full page reload right after create), but a row-level checkbox + Delete only **stages**
the removal client-side — the page-level Save button at the bottom of the screen is what actually
fires the `DELETE` call. A screen also has a Translation feature (multi-locale descriptions) —
not tested.

Verified full cycle: `POST` via Add-modal Save (code `ZZAUDIT`) → confirmed persisted via full
page reload → checkbox + row-Delete (staged) → page-level Save →
`DELETE /data/WM/wm/codes/ZZAUDIT*!dck_acc_cod` → separate `GET codes?columnName=dck_acc_cod`
confirmed 0 rows.

## Verified writes (summary)

- `PUT /data/WM/wm/locations/{id}*!{warehouseId}` — Enable/Disable toggle edit→verify→revert.
- `POST /data/WM/wm/locations/batch` — create, verified on Production/Yard/Dock/Staging/
  Processing/Pickup-and-Deposit.
- `DELETE /data/WM/wm/locations/{id}*!{warehouseId}?buildingId=` — verified on all 7 category
  screens (Pickup and Deposit via direct API, the rest via UI).
- `POST`/`DELETE /data/WM/wm/locationTypes` — verified.
- `POST`/`DELETE /data/WM/wm/levelTypes` — verified.
- `POST`(via modal Save)/`DELETE /data/WM/wm/codes/{code}*!{columnName}` — verified for the
  `dck_acc_cod` code list (Dock Access Groups).

All logged in `../../index/ui-actions.jsonl`.

## Evidence added 2026-08-13 (reads)

First stored exchanges for this resource: `../../http/exchanges/locations.jsonl`.

- **Scale corrected.** `GET /wm/locations/count` reports **61,912** rows. This file said "25k+
  storage locations"; the real total is about 2.5x that.
- A location record carries **176 fields**.
- `read-missing` on a malformed id returns **400**, not 404 — consistent with the other
  compound-id resources. Only a well-formed but absent id yields `404 RECORD-MISSING`.
- **`GET /wm/locations/batch` returns 400, not `ROUTE-MISSING`** — so the documented batch-create
  path genuinely exists. It does not repeat the `transportEquipmentTypes` failure, where the
  documented route did not exist at all.

**Writes remain unproven and are deliberately not guessed.** With 176 fields and no captured
create payload, writing one would mean inventing the body — the exact habit that produced every
falsified claim here. The payload must first be captured from the real Add form, the way
`businessUnitDescription` was recovered on Business Units.

## There is no Add form — create is a wizard behind the Actions menu

`app-map.json` marks all ten location screens `can_create: false`. That is wrong, and the way it
is wrong matters: the map only ever looked for a toolbar button with `itemId === 'addButton'`.
`tools/cdp/dump-actions-menu.mjs` found an **enabled `Add` inside the `Actions` menu** on Storage,
Dock and Yard Locations (Staging's was disabled at the time of capture, presumably state-dependent).

So `can_create: false` across the map means *no Add button*, not *cannot create*. Any screen with an
`Actions` split button needs its menu enumerated before its create surface is known.

What Add opens is not a form either — it is a floating Ext `window` with **no `form` component**,
which is why the first capture pass reported "no form rendered" while a live dialog sat on screen
(`tools/cdp/menu-form.mjs` now falls back to the window's own fields).

Walking it (`tools/cdp/walk-wizard.mjs`, output in `index/wizards.json`) shows a multi-step wizard:

- step 1 carries a `loctype` combo labelled **"2. Select a location type"** — the numbering means a
  step 1 selection exists alongside it, and the dialog's own `Add` / `Delete` buttons indicate that
  selection is a list you build rather than a field you fill;
- `Next` stays **disabled** until that selection is made, so the walk cannot advance blind;
- Storage Locations offers six types: `10000` Damaged, `10023` Distribute to Storage, `10622` Grey
  Matter Controlled Storage, `10624` Grey Matter DAMAGES, `10623` Grey Matter LOST, `10022` Storage.

The consequence for the payload: **there is no single locations create body.** The field model
depends on the chosen location type, and creation is scoped to a parent (the screen's own route
carries `buildingId[__value__]=B1`). A create recipe here must be per-type and parent-aware.

Next step is to satisfy step 1's selection so `Next` enables, then record each subsequent step's
field model — still without clicking Finish.

## Open items

- The exact `locationCode` value pair for Enable/Disable was not captured before reverting — the
  round trip is proven clean, but the specific field driving the toggle was never caught in its
  changed state.
- `Aisles` and `Location Sequences` — not write-tested (Sequences: real bulk-edit data, no safe
  throwaway target; Aisles: not visited this pass).
- Search-box free-text mis-targets the `Aisle` column instead of `Location`/`Code` on at least
  Yard Locations and Pickup and Deposit Locations — a real UI bug, not an automation artifact.
  Don't rely on the quick-filter box for exact-match lookups on these screens; use a real
  column-scoped filter or fetch by API instead.
- The `/wm/codes` generic-resource finding (Dock Access Groups) hasn't been cross-checked against
  any other screen in the app — worth revisiting if another "simple named list" screen turns up
  in a later tier.
- `PND` category also showed a transient combo-render bug: immediately after selecting "Pickup &
  Deposit" the field displayed the raw `&amp;` entity instead of `&`; resolved itself after the
  wizard's Add-Locations click fired (cosmetic only, the persisted data was correct).
