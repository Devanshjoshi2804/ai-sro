# Screen: Warehouse Equipment Type

nav_path: Configuration > Equipment > Equipment > Warehouse Equipment Type
route hash: `#wm.config/wm.config.equipment.equipment.warehouseequipmenttype////`

20+ real equipment types in this environment (forklifts, reach trucks, hand-helds, clamp trucks,
etc), each tied to a voice code (used at RF/voice terminal login) and one or more Location Access
Groups. This is operator-facing config with real business impact — misconfiguring a voice code or
access group changes what an RF operator can log into and where they can work.

## Buttons and actions

Toolbar is flat `Add` / `Copy` / `Delete` buttons — **no `Actions` dropdown**, same pattern as
Level Types (`../warehouse/locations.md`).

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| Add | new equipment type form | `POST /data/WM/wm/equipmentTypes` | Required: Warehouse Equipment Type (code), Description, Voice Code, LPN Warehouse Equipment Type Limit (0 = unlimited). Optional: Capture Warehouse Equipment (safety-check/lock toggle), Work Area Associations, Limit Access In Locations (Location Access Groups picker), per-work-zone/work-area limits. |
| checkbox + Delete | remove | `DELETE /data/WM/wm/equipmentTypes/{code}` | In-app ExtJS confirm modal, not a native dialog. |
| row click | edit | — | not tested |
| Copy | duplicate | — | not tested |

## Fields (`/data/WM/wm/equipmentTypes/{code}`)

**resourceId is the bare entered code** (e.g. `ZZAUDIT`, `self_uri` is
`/wm/equipmentTypes/ZZAUDIT`) — no compound key, no synthetic numeric id. Different from
`locationTypes`/`levelTypes` in the Warehouse tier, which each use their own id scheme.

| Field | Notes |
|---|---|
| `vehicleTypeId` | same value as the code/resourceId |
| `longDescription` | maps to the Description field |
| `shortDescription` | not set by the create form in this test (came back `null`) |
| `voiceCode` | integer, drives voice-terminal login |
| `vehicleLimit` | LPN limit, 0 = unlimited |
| `captureEquipment` | boolean, safety-check/lock-unlock capture toggle |
| `useWorkAreaMove` | boolean, Work Area Associations toggle |
| `location` | int, seen as `0` on create — purpose not explored |
| `equipmentsCount` | read-only rollup, `# of Associated Warehouse Equipments` column |
| `dateLastModified`, `lastModifiedBy` | audit fields |

## Verified write

Full cycle: `POST /data/WM/wm/equipmentTypes` (code `ZZAUDIT`) → 201 → separate `GET` confirmed →
checkbox + Delete (confirm modal) → separate `GET /equipmentTypes/{code}` → 404. Logged in
`../../index/ui-actions.jsonl`.

## Open items

- Edit (`PUT`) not tested — only create/delete.
- `Limit Warehouse Equipment Type Access In Locations` (Location Access Groups picker) and the
  per-work-zone/work-area limit sub-forms not exercised.
- `Copy` action not tested.
- The real `#8...` prefixed equipment codes (e.g. `8HAND`, `8REPLEN`) suggest a site-specific
  naming convention — don't read too much into the `8` prefix without asking the customer.
