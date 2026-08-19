# Screen: Buildings

nav_path: Configuration > Warehouse > Buildings
route hash: `#wm.config/wm.config.warehouse.buildings////`

Single building (`B1`) in this environment. Screen has Map View / Grid View toggle (both render
the same building list; Grid View is the reliable one for automation — Map View needs a canvas
click). Single-item environments auto-navigate straight to the detail page.

## Buttons and actions

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| Add | new building form | not captured | Open item — same blast-radius reasoning as Warehouse's "Create a new warehouse": only 1 building exists, deferred. |
| Copy | duplicate building | not captured | Open item. |
| Delete | remove building | not captured via UI | Help doc: blocked if any entity (area, etc.) is assigned to the building — cascade-protected, not silently destructive. |
| row click (Grid) / auto-nav | opens `{buildingId}` detail | store-driven, no fresh network call on 2nd visit (ExtJS grid store cache) | |
| Save (in edit) | `PUT /data/WM/wm/buildings/{buildingId}*!{warehouseId}` | full record | UI form only exposes **Building Name** (read-only, "Edit" link required to change it — not exercised) and **Building Address** (shared address record — see below) + the floor-plan canvas. No UI field for the business-logic columns below; those were write-tested directly against the API. |
| Draw (floor-plan canvas) | drops a resizable box on the warehouse map image, drag/resize, then Save | help doc `buildings.md` — box becomes the building boundary | Not live-tested (gesture-heavy, low priority). Building's own resource has no geometry fields; strong signal the box coords land on the **warehouse** record's `warehouseMapLeftX/LowerY/RightX/UpperY` (present on `/wm/warehouses/{id}`, see `warehouse.md`) rather than on the building — single-warehouse env, so this held. Confirm live before relying on it in a multi-building environment. |
| Upload Image | swap the map background image | not captured | Open item — file upload flow. |
| View dropdown (canvas) | layer toggle checkboxes: All / Areas / Buildings / Count Zones / Movement Zones / Pick Zones / Storage Zones / Work Zones | UI-only, no API | Confirms Areas and Locations render on this same map canvas — expect the same Draw/View pattern on those screens. |

## Fields (`/data/WM/wm/buildings/{buildingId}*!{warehouseId}`)

Resource id order: `{buildingId}*!{warehouseId}`, e.g. `B1*!SG` — confirmed live (reversed order
not tested, follow the suppliers-id lesson and assume it's strict).

**Bare collection call works** (`GET /data/WM/wm/buildings?siteId=SG&subsites=----`); the naive
single-record path guess (`/buildings/B1`, `/buildings/B1?siteId=...`) 400s — same 400 the real
app itself hits if you replay that exact URL, i.e. this is a genuine app quirk, not a client bug.
Get the correct compound id from a collection row's `resourceId` first, then GET the single record.

| Field | Type | Notes |
|---|---|---|
| `buildingId`, `warehouseId` | string | compound key halves |
| `addressId` | string | points at a **shared** address — this building's address (`A000000024`) is the *same* address record as warehouse `SG`'s own address. Editing it here also changes what the Warehouse screen shows. Not edited this pass to avoid a cross-screen side effect. |
| `fluidLoadFlag` | 0/1 | Verified `PUT`-editable. Edit→verify→revert cycle done via direct API (no UI field exists for it). |
| `sortDefaultFlag` | 0/1 | not write-tested, same shape as `fluidLoadFlag` |
| `sortAttributeLocationStatus` | string (e.g. `"P"`) | not write-tested |
| `businessFacility` | nullable | not write-tested |
| `version` | int | **Does NOT increment on write** (stayed 97 before/after a confirmed-persisted `PUT`) — unlike `carrierProNumbers.version`, which does. Confirms `version` semantics are per-resource, not a platform-wide rule; don't assume either behavior without testing the specific resource. |
| `areaCount`, `locationCount` | int, read-only | **Mismatch found:** API reported `areaCount: 94`, `locationCount: 61912`; the Grid View row for the same building showed `76` areas / `19816` locations. Not yet root-caused — possibly the grid counts are scoped narrower (e.g. active-only, or a specific location type) while the API field is a raw total. Flagged, not resolved. |

## Verified write

`PUT /data/WM/wm/buildings/{buildingId}*!{warehouseId}` — `fluidLoadFlag` edit→verify→revert,
confirmed via separate `GET`, both directions. Logged in `../../index/ui-actions.jsonl`.

## Open items

- Add / Copy / Delete — not captured (single-building environment, deliberately deferred).
- Draw/resize/Save floor-plan cycle — not live-tested.
- Upload Image — not captured.
- `areaCount`/`locationCount` API-vs-grid mismatch — not root-caused.
- Building Name edit (behind the "Edit" link, field is read-only otherwise) — not tested.
