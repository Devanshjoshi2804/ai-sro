# Screen: Location Access Groups

nav_path: Configuration > Equipment > Equipment > Location Access Groups
route hash: `#wm.config/wm.config.equipment.equipment.locationaccessgroups////`

51 real pre-existing groups (`ALEQ`/All Equipment, `DROP`, `DEEP`, `BULK`, `FLOR`, `HIGH`, `CSPK`,
`CLW1`/`CLW2`, `PMAG`, `SPST`, `OTH`, `CRAN`, `HHT`, `LOW`, `OUT`, plus many `#8`-prefixed and
site-specific codes). These are the groups referenced by the `Location Access Groups` column on
Warehouse Equipment Type (`equipment-types.md`) — real config coupling between the two screens.

## MAJOR FINDING: same generic `/wm/codes` resource as Dock Access Groups

This screen is **not a dedicated resource**. It's the exact same shared code-list table found on
`Configuration > Warehouse > Locations > Dock Access Groups`
(`../warehouse/locations.md`), backed by `/data/WM/wm/codes`, keyed `{code}*!{columnName}` —
here `columnName=locacc`. Same UI shape too: `Add`/`Delete` flat toolbar buttons, no `Actions`
dropdown, a `Translation >` link for multi-locale descriptions, and drag-to-reorder rows (Display
Sequence column).

This is now confirmed on **two** screens (`dck_acc_cod`, `locacc`) — strong evidence the pattern
generalizes across the app for any "simple code + description + short description" screen. Worth
checking against further screens as the campaign continues, rather than assuming each is its own
resource.

## Buttons and actions

| Button | Action | API call(s) | Notes |
|---|---|---|---|
| Add | modal: code, description, short description | `POST /data/WM/wm/codes` | Modal's own Save commits immediately — confirmed the row was present in a fresh `GET` right after, no page-level Save needed for create. |
| checkbox + Delete | stages removal | (client-side only) | Row disappears from the grid immediately but is **not yet persisted**. |
| page-level Save | commits staged deletes | `DELETE /data/WM/wm/codes/{code}*!{columnName}` | This is the call that actually removes the record — confirmed via network capture and a separate `GET` before/after. |
| row drag | reorder (`sortSequence`) | not tested | |
| Translation | multi-locale descriptions | not tested | |

## Fields (`/data/WM/wm/codes/{code}*!locacc`)

| Field | Notes |
|---|---|
| `codeValue` | the code, e.g. `ALEQ` |
| `columnName` | fixed `locacc` for this screen — the discriminator for the shared table |
| `columnDescription` | `"Location Access"` — a label for the whole code list, not per-row |
| `longDescription` | Description field |
| `shortDescription` | Short Description field |
| `sortSequence` | Display Sequence column |
| `requiredFlag`, `inUseFlag` | present, not explored |
| `resourceId` | `{codeValue}*!{columnName}`, e.g. `ALEQ*!locacc` |

## Verified write

Full cycle: `POST /data/WM/wm/codes` (code `ZZAUDIT`, `columnName=locacc`) → confirmed via
separate `GET` → checkbox + Delete (staged) → page-level Save → `DELETE
/data/WM/wm/codes/ZZAUDIT*!locacc` → separate `GET` confirmed 0 rows, and confirmed the 51
pre-existing real rows (including `ALEQ`) were untouched. Logged in `../../index/ui-actions.jsonl`.

## Open items

- Row drag-to-reorder (`sortSequence` renumbering) not tested.
- Translation feature not tested.
- **Gotcha caught live**: after a page-level Save refreshes/re-sorts the grid, row *positions*
  shift. A checkbox click using coordinates from before that refresh can select the wrong row —
  this happened once here (accidentally selected real row `ALEQ` instead of `ZZAUDIT`), caught
  and cancelled before confirming. Always take a fresh screenshot after any grid refresh, right
  before checkbox-selecting a row for delete.
