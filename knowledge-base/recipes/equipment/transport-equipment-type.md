> **RETRACTED 2026-08-13 — `/wm/transportEquipmentTypes` DOES NOT EXIST.**
>
> Everything below that names this path is false and is kept only so the error is traceable.
> All six recorded cases in `../../http/exchanges/transportEquipmentTypes.jsonl` return
> **`404 ROUTE-MISSING`** — the framework's unrouted-URL shape,
> `{"message":"Not Found","url":"/ws/wm/transportEquipmentTypes"}` — including
> `GET /wm/transportEquipmentTypes/AIR` on a **real, existing code**.
>
> The original proof was *"confirmed via a separate GET returning 404 afterwards"*. That test is
> **circular**: a route that does not exist returns 404 forever, whether or not anything was
> deleted. It cannot distinguish a successful delete from an endpoint that was never there.
>
> **The real resource is `/wm/codes` with `columnName=trlr_typ`.**
> `GET /wm/codes/AIR*!trlr_typ` returns 200 with the record. Ledger entries for this path are
> `verified: false`. See `../../http/claims.json` → `transportEquipmentTypes-endpoint-exists`.

# Screen: Transport Equipment Type

nav_path: Configuration > Equipment > Equipment > Transport Equipment Type
route hash: `#wm.config/wm.config.equipment.equipment.transportequipmenttype////`

11 real pre-existing types: `AIR` (Air Express), `RT` (Controlled Temp Trailer/Reefer), `FF`
(Frozen Food Trailer), `IOFC` (Intermodal), `OCNT` (Ocean Container), `RAIL` (Railroad Car),
`FRIG` (Refrigerated Transport Equipment), `TANK` (Tank Truck), `TF` (Trailer, Dry Freight), `TW`
(Trailer, Refrigerated), `TRCK` (Truck/Transport Equipment). All codes are ≤5 characters — matches
a hard client-side truncation limit on the code field (see below). Each row has a Dock Access
Groups column, tying this screen to `dock_access_groups` (`../warehouse/locations.md`) —
transport equipment can be restricted to check in only at specific docks.

## Third confirmation of the generic code-list backend, with a twist

Same `/wm/codes` shared table found on Dock Access Groups and Location Access Groups
(`columnName=trlr_typ` here), **but** this screen's records are also exposed under their own
dedicated resource path: `/data/WM/wm/transportEquipmentTypes/{code}*!trlr_typ` (this is the
`self_uri` on the record) — the list call itself goes through
`/data/WM/wm/codes/transportEquipmentTypes?columnName=trlr_typ&offset=0&limit=100` (a hybrid URL
shape: `codes` as the base, `transportEquipmentTypes` as a path segment, not the bare
`/wm/codes?columnName=...` shape used by Dock/Location Access Groups).

Practical implication: `DELETE /data/WM/wm/transportEquipmentTypes/{code}*!{columnName}` works
directly (confirmed) — you don't have to go through the generic `/wm/codes/{code}*!{columnName}`
path for this specific screen.

## Buttons and actions

Flat `Add`/`Copy`/`Delete` toolbar buttons, no `Actions` dropdown — same family as Level Types,
Warehouse Equipment Type, Dock/Location Access Groups.

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| Add | full-page form (not a modal, unlike Dock/Location Access Groups) | `POST /data/WM/wm/transportEquipmentTypes` | Fields: Equipment (code, **max 5 chars, silently truncates** — typed `ZZAUDIT`, saved as `ZZAUD`), Description, Short Description, and a "Limit Equipment Access In Locations" picker explicitly labeled "Select the dock access codes where this equipment can check-in." |
| checkbox + Delete | remove | `DELETE /data/WM/wm/transportEquipmentTypes/{code}*!{columnName}` | In-app confirm modal, not native. Fires directly — no separate page-level Save step needed here (unlike Dock/Location Access Groups). |
| row click | edit | — | Loads the full-page form pre-filled. |
| Copy | duplicate | — | not tested |

## Bug found: stale render on detail view immediately after create

Clicking into the just-created record's detail page showed **`ZZAUD` in the Description and
Short Description fields** instead of the real typed values. Verified via direct API read that
the correct values (`longDescription: "Audit test transport equipment type"`,
`shortDescription: "Audit"`) were persisted the whole time — **this is a UI display bug, not data
loss**. Don't trust the detail-view immediately after a create/reload without cross-checking the
API; this matches the "aisle field went blank after save" rendering-lag pattern already logged for
`locations` in the Warehouse tier.

## Fields (`/data/WM/wm/transportEquipmentTypes/{code}*!trlr_typ`)

| Field | Notes |
|---|---|
| `codeValue` | the code, e.g. `TANK` |
| `columnName` | fixed `trlr_typ` |
| `longDescription` | Description field |
| `shortDescription` | Short Description field |
| `dockAccessCount` | rollup for the Dock Access Groups column, `0` if unrestricted |
| `sortSequence` | present, `0` on create (unlike Location Access Groups which auto-incremented) |
| `resourceId` | `{codeValue}*!{columnName}`, e.g. `TANK*!trlr_typ` |

## Verified write

Full cycle: `POST /data/WM/wm/transportEquipmentTypes` (code truncated to `ZZAUD`) → confirmed
correct via `GET /wm/codes/transportEquipmentTypes?columnName=trlr_typ` → checkbox + Delete
(confirm modal) → `DELETE /wm/transportEquipmentTypes/{code}*!trlr_typ` → separate `GET` 404.
Logged in `../../index/ui-actions.jsonl`.

## Open items

- "Limit Equipment Access In Locations" (dock access codes picker) not exercised.
- `Copy` action not tested.
- Whether the 5-char code limit is server-enforced or purely client-side UI truncation wasn't
  isolated — worth testing via direct API if a longer code is ever needed programmatically.
