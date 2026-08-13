# Screen: Areas

nav_path: Configuration > Warehouse > Areas
route hash: `#wm.config/wm.config.warehouse.areas/buildingId[__value__]=B1&buildingId[__type__]=string///`

76 real areas under building `B1` (auto-selected — this is the only building). Grid View /
Map View toggle, same pattern as Buildings. Real production data with heavy location counts
(some areas carry 800+ locations) — `version` on the record tested here was already at 106,
confirming this is an actively-used config, not a leftover.

## Buttons and actions

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| Add | new area form | not captured | Open item — not tested against 76 real production areas; deferred as too high a footprint for this pass. |
| Copy | duplicate area | not captured | Open item. |
| row click | opens edit form | store-driven | |
| Save (in edit) | `PUT /data/WM/wm/areas/{areaId}*!{warehouseId}` | full record | Verified: edit `longDescription` → `200` → separate `GET` confirmed persisted → reverted → separate `GET` confirmed reverted. Clean, no silent-drop. |
| checkbox + Delete | not tested | — | Deferred — deleting a real production area with hundreds of locations attached is out of scope for a config-field verification pass. |

## Fields (`/data/WM/wm/areas/{areaId}*!{warehouseId}`)

Resource id order: `{areaId}*!{warehouseId}` — same `*!` compound-key convention as
`buildings` and `businessUnits`.

| Field | UI label | Notes |
|---|---|---|
| `areaCode` | "Enter a name for the area" | resource id half, read-only after create |
| `longDescription` | "Enter a description for the area" | verified `PUT`-editable |
| `lostLocation` | "Enter the location designated for lost inventory" | search-combo field, not tested |
| `buildingId` | "Select the building where the area resides" | read-only in this env (only one building) |
| `businessUnit` | "Select the business unit where the area resides" | combo, not tested — this env has 0 business units so nothing to select |
| `aisleId`, `bayCount`, `productionFlag`, `shortDescription`, `storageFlag`, `workInProcessFlag` | — | present on the resource, null on the record tested, not exercised |
| `locationCount` | read-only | grid column, driven by linked locations |
| `version` | — | present; increment behavior on this resource not explicitly re-tested this pass (see `buildings.md` for the general finding that `version` behavior is resource-specific, not a platform rule — don't assume either way without testing) |

## Cross-screen pattern

Same map-canvas / Draw / View-layer-toggle UI as `buildings.md` describes — areas render as
their own layer on the same building floor-plan canvas (`View` dropdown lists Areas as a
toggleable layer). An existing area (`CO-STO-FL`) already had a saved shape rendered on the
canvas on open, confirming floor-plan geometry does persist per-area (unlike the Buildings
screen, where `B1` had no shape drawn) — worth using as a live example if the Draw workflow is
tested later.

## Open items

- Add / Copy / Delete — not tested (76 real production areas, high blast radius).
- `lostLocation` and `businessUnit` combo fields — not exercised (env has 0 business units).
- Draw/resize/Save floor-plan cycle — not live-tested, though `CO-STO-FL` proves persistence
  works for at least one existing shape.
