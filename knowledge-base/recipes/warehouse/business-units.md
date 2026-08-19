# Screen: Business Unit

nav_path: Configuration > Warehouse > Business Units
route hash: `#wm.config/wm.config.warehouse.businessunits////`

**Zero business units exist in this environment** (both grid and `GET /data/WM/wm/businessUnits`
confirm 0 rows). Every action below was verified via a create → edit → delete cycle since there
was no existing record to test against.

## Buttons and actions

| Button | Action | API call(s) | Payload | Notes |
|---|---|---|---|---|
| Add | opens "Add Business Unit" form | `POST /data/WM/wm/businessUnits` | `{businessUnit, description}` | Two fields only, both required. `201` on success. |
| row click | opens edit form | store-driven (no fresh GET on same-session revisit) | — | `businessUnit` field read-only in edit form (same pattern as `buildingId`). |
| Save (in edit) | `PUT /data/WM/wm/businessUnits/{businessUnit}*!{warehouseId}` | full record | Verified: edit `description` → `200` → grid re-render confirmed. |
| checkbox + Delete | `DELETE /data/WM/wm/businessUnits/{businessUnit}*!{warehouseId}` | — | Fires an in-app ExtJS "Are you sure?" confirm modal (not a native browser dialog — safe to script through). `200` on confirm, grid empties. |

## Fields

Resource id order: `{businessUnit}*!{warehouseId}`, e.g. `ZZAUDIT*!SG` — same compound-key
pattern as `buildings` (`{buildingId}*!{warehouseId}`). Consistent convention across Warehouse
tier screens.

| Field | Notes |
|---|---|
| `businessUnit` | resource id half, e.g. `ZZAUDIT`. Read-only after create. |
| `description` | free text, UI-editable. |
| `areaCount`, `itemCount` | read-only grid columns, not present as editable fields. |

## Verified write

Full CRUD cycle done end-to-end through the UI (not direct API): create → verify (grid) → edit
description → verify (grid) → delete via checkbox+Delete confirm modal → verify (grid empty).
Logged in `../../index/ui-actions.jsonl`.

## Open items

- None — full lifecycle already covered by the only record ever created (and removed) in this
  environment.
