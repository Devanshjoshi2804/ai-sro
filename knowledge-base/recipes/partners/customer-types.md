# Screen: Customer Types

nav_path: Configuration > Partners > Customers > Customer Types
route hash: `#wm.config/wm.config.partners.customers.types////`

**Genuine coverage gap, closed 2026-08-12.** This sub-screen sits alongside "Existing Customers"
under the Customers flyout but was never visited in the original Partners pass — confirmed
missing by re-checking a fresh screenshot of the nav menu. 20+ real customer types pre-exist
(`ABSC`, `AFP9`, `AFPS`, `AFS0`, `AHOL`, `BCW`, `BOZZ`, `BPCO`, `BSS`, `CBP`, `CHEE`, `CON`, `COO`,
`COST`, `DELH`, `DOM`, `DSTR`, `DUM`, `DUNK`, `GIAN`, plus a large `WLKE`-prefixed family of
per-retailer packing-list variants like `WN01`-`WN04`, `WELA`-`WELZ`). These are exactly the
values the `Customer Type` field on **Existing Customers** references (`../existing-customers.md`
mentions `DUM` as a valid code) — this screen is the master list backing that field.

## Buttons and actions

Flat `Add`/`Copy`/`Delete` toolbar, no `Actions` dropdown.

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| Add | full-page form | `POST /data/WM/wm/customerTypes` | Required: Customer Type (code, **max 4 chars, silently truncates** — typed `ZZAUDIT`, saved as `ZZAU`), Customer Type Description. Large form below the fold: Department, Manufacturer, Create Shipment By, Pallet Building, then INVENTORY section (Allocation Search Path Group, Inventory Rotation Method, Allocation Profile, Reservation Priority, Bulk Picking...). |
| checkbox + Delete | remove | `DELETE /data/WM/wm/customerTypes/{code}` | In-app confirm modal. |
| row click | edit | `GET /data/WM/wm/customerTypes/{code}` | not tested |
| Copy | duplicate | — | not tested |

## Fields (`/data/WM/wm/customerTypes/{code}`)

Bare entered code as resourceId (`customerTypes/ZZAU`) — **no compound key**, same convention as
Warehouse Equipment Type (`../equipment/equipment-types.md`). Large record (~40 fields), notable:

| Field | Notes |
|---|---|
| `customerType` | the code |
| `longDescription` | Description field |
| `crossDockFlag` | `-1` on create by default — same "inherit" sentinel seen on the Customer record itself (`existing-customers.md`) |
| `createShipmentBy`, `palletBuildingConsolidateBy` | nullable, drive the Create Shipment By / Pallet Building dropdowns |
| `earlyDeliveryThreshold`, `lateDeliveryThreshold`, `enforceEarlyDeliveryRuleFlag`, `enforceLateDeliveryRuleFlag` | delivery-window business rules, default `0`/`false` |
| `bulkPickingFlag` | boolean, default `false` |
| `outboundDateWindow`, `outboundDateWindowUnit` | default `0` / `"MIN"` |
| `quantityOvershipLimit`, `quantityUndershipLimit`, `maxQuantityOvershipPercentage`, `maxQuantityUndershipPercentage` | over/under-ship business rules, default `0` |

## Failure cases (this is what a future executor needs to detect, not just the happy path)

1. **Client-side required-field gate.** Both `Customer Type*` and `Customer Type Description*`
   show a red exclamation icon while empty, and the `Save` button stays disabled — confirmed via
   network capture that **no request fires at all** when Save is clicked in this state (there is
   nothing to click, functionally — the button ignores clicks while disabled). Standard ExtJS
   `formBind` behavior, but worth confirming per-screen since not every screen in this app gates
   this cleanly (see the Existing Customers invisible-mask trap, which looks identical from a
   screenshot but behaves completely differently).
2. **Duplicate-code rejection is entirely client-side.** Typing a code that collides with a real
   existing record (e.g. any of the 20+ above) shows an inline red tooltip directly under the
   field: *"This customer type has already existed"*. Confirmed via `read_network_requests` that
   **zero network calls** accompany this check — it's validated against a store already loaded
   into the page (likely the grid's own cached store), not a live server round-trip. Implication
   for an executor: this check can go stale if the grid was loaded a long time ago and a
   duplicate was created by someone else in the meantime — don't treat "no red tooltip" as proof
   a code is free without also checking the API directly for high-stakes creates.
3. **Stuck-disabled-Save bug, environment-specific.** After several Add-form re-entries within one
   browser session (this happened here because of repeated harmless "Processing completed without
   exception" nav-glitch dialogs — see `KNOWLEDGE-BASE.md` — being dismissed and the Add button
   re-clicked each time), the visible Save button got stuck permanently disabled **despite a fully
   valid form** — confirmed by walking every field's `isValid()` via
   `Ext.ComponentQuery.query('form')` and finding zero invalid fields, then finding **two separate
   `saveButton` component instances** via `Ext.ComponentQuery.query('button')`, one of them
   stale-disabled. Did not reproduce on a single clean Add-form load. If an executor's Save click
   silently does nothing on a form that reads as fully valid, check for duplicate `saveButton`
   instances before assuming a data problem.
4. **Do not "reset" a stuck page with a raw browser reload.** A plain page reload (not a SPA route
   change within the app) invalidates this app's OIDC session and drops straight to a full
   re-login screen — lost the working session doing exactly this while chasing the stuck-Save bug
   above. Always navigate to a known-good in-app hash route to recover, never `location.reload()`
   or an F5-equivalent.

## Verified write

Full cycle: `POST /data/WM/wm/customerTypes` (code truncated to `ZZAU`) → separate `GET`
confirmed → checkbox + Delete (confirm modal) → separate `GET` 404. Logged in
`../../index/ui-actions.jsonl`.

## Open items

- Row-click edit (`PUT`) not tested.
- `Copy` button not tested.
- The large INVENTORY/second-half-of-form fields (Allocation Search Path Group, Inventory
  Rotation Method, Allocation Profile, Reservation Priority, Bulk Picking and beyond) not
  individually exercised — only confirmed they exist and don't block Save at their defaults.
