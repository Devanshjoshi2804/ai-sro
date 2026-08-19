# Screen: Warehouse

nav_path: Configuration > Warehouse > Warehouse
route hash: `#wm.config/wm.config.warehouse.warehouse////`

Single-warehouse landing dashboard (this environment has exactly one warehouse, `SG`). Not a
list/grid screen like every other Configuration screen — it's a summary card with two action
links: "Edit Warehouse" and "Create a new warehouse".

## Buttons and actions

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| Edit Warehouse | opens "Edit Warehouse {id}" form | `GET /data/WM/wm/warehouses/{id}` (implicit, page context) | |
| Save (in edit) | `PUT /data/WM/wm/warehouses/{id}` | full record | Re-verified 2026-08-11: edit `longDescription` → `200` → separate `GET` confirmed persisted → reverted → separate `GET` confirmed reverted. Clean, no silent-drop behavior (unlike `suppliers`). |
| Create a new warehouse | opens create form | not captured this pass | Open item — this environment has only one warehouse and creating a second is a materially bigger blast radius (new site) than a field edit; deferred. |

## Fields (`/data/WM/wm/warehouses/{id}`, `?expand={address}`)

Full field list captured live (`GET /data/WM/wm/warehouses/SG?expand={address}`):

`active, address, addressId, address_uri, adjustmentThresholdCost, adjustmentThresholdUnit,
aisleMax, autoPlayCostThreshold, bayMax, concatenationOrder, consignmentCode, consignmentPeriod,
countingThresholdCost, countingThresholdUnit, currencyCode, defaultHoldPrefix,
defaultWarehouseFlag, lastRegenTime, lastRotationId, lensCustomerClientId, lensCustomerId,
lensEnabledFlag, lensSiteName, longDescription, originCode, permanentAdjustLoad,
permanentAdjustSubLoad, permanentCreateLoad, permanentCreateSubLoad, recalcDate,
recalcDistributionFlag, resourceId, rotationIdMaxValue, rotationIdMinValue, self_uri,
serializedGlobalLocationNumber, slotMax, translatedWarehouseId, warehouseId, warehouseMapLeftX,
warehouseMapLowerY, warehouseMapRightX, warehouseMapUpperY, warehouseTypeCode`

| Field | Notes |
|---|---|
| `warehouseId` | resource id, e.g. `SG`. Read-only after create (grayed out in Edit form). |
| `longDescription` | UI label "Description*". Verified `PUT`-editable, standard string, no observed truncation at the length tested (short marker only — long-field truncation not re-tested here, see `carriers.md`/general finding that some description-class fields truncate silently). |
| `address` / `addressId` | Edit form's Address block edits the linked address inline (not a join-view drop like `suppliers` — this form's "Edit" link next to Address Name opens the same address picker pattern seen elsewhere). Not independently re-tested this pass; assume the general `addresses/{id}` write path applies if editing address fields directly is ever needed. |
| `defaultHoldPrefix`, `currencyCode`, `lensEnabledFlag`, `lensSiteName`, `lensCustomerId` | visible in "Optional Settings" section of the edit form, not individually write-tested this pass — form-level `PUT` sends the full record so they ride along with any edit. |

## Cross-screen pattern

List-call envelope pattern does NOT apply here (single-record dashboard, no grid/pager). The
single-record `GET`/`PUT` envelope (`{@type, data:{...}}`) matches every other screen.

## Open items

- Create-a-new-warehouse flow — not captured (high blast radius: this is the only warehouse in
  the QA environment).
- Address-block edit via the Edit form's own "Edit" link — not independently exercised; only the
  top-level `longDescription` field was write-tested.
- Optional Settings fields (`defaultHoldPrefix`, lens integration fields, threshold costs) — not
  individually write-tested.
