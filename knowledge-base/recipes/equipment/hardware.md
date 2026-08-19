# Screens: Printers, RF Devices, Voice Devices, Workstations, Hardware Settings

nav_path: Configuration > Equipment > Hardware
route hash prefix: `#wm.config/wm.config.equipment.hardware.<subtype>////`

## Shared `/wm/devices` table (RF Devices, Voice Devices, Workstations)

Three of the five Hardware screens share one resource, `/data/WM/wm/devices`, differentiated by
`deviceClass`: `R` (RF Devices), `V` (Voice Devices), `W` (Workstations). Confirmed by creating a
throwaway record on each and reading back `deviceClass` on the persisted row. Standard
`{deviceCode}*!{warehouseId}` compound resourceId on all three.

**Printers is NOT part of this table** — it has its own dedicated resource, `/data/WM/wm/printers`
(also `{code}*!{warehouseId}`), confirmed via network capture — this is the exception, not part of
the shared-devices pattern.

## Printers

8 real printers (`SG_DOC01`..`SG_DOC08`, all Postscript, `Status: Connected` — a **live device
state field**, not just config). Add form: Printer Name, Printer Network Address (optional),
Printer Type (dropdown: Intermec EasyCoder 4400, Postscript, Zebra 140Xi/XIII, Zebra RFID),
Printer Description, Printer Language, Printer Status (radio: Disconnected/Connected/Rerouted).

**Deliberately created the test record with Status = Disconnected**, not Connected, to avoid
implying a live device registration on a real network.

Verified: `POST /data/WM/wm/printers` → 201 → checkbox + Delete (in-app confirm modal) →
`DELETE /data/WM/wm/printers/{code}*!{warehouseId}` → separate GET 404.

## RF Devices

293 real pre-existing devices. **High-risk screen** — many rows show a live `Current User`
(e.g. `EXT-SAEED1`, `SLEWIS`), meaning real operators are actively logged into those handheld or
vehicle-mount terminals right now. Only did a throwaway create+delete; never touched any existing
row.

Add form: Device Code, Device Name, Locale (long list, no type-to-filter — use arrow keys to
scroll to an option like `USA English`), Vendor Name (`ANY`/`DEFAULT`/`INT`/`LXE`/`MAC`/`MAC6`/
`OLDNQR`/...), Terminal (free text), Terminal Type (`Handheld` or `Vehicle`, each driving
default Width/Height — `Vehicle` defaults to `40 x 8`, matching most real rows), Work Areas, Home
Work Area.

Verified: `POST /data/WM/wm/devices` (`deviceClass=R`) → 201 → checkbox + Delete → separate GET
404. The 293-device count and Vendors sub-tab (14 real vendors, not tested) confirm this is a
substantial real fleet, not test data.

**Gotcha**: the quick-filter search box mis-targets the `Current User` column instead of `Device`
(same bug pattern as Yard/Pickup-and-Deposit Locations in the Warehouse tier) — sort by clicking
the `Device` column header instead of relying on search.

## Voice Devices

Only 2 real pre-existing devices (`001A`, `DREDD123`). Add form: Device, Description, Voice
Locale (defaults to `USA English`), Voice Terminal (optional, falls back to Device if blank),
Work Areas, Home Work Area, Report/Label Printer.

> **RETRACTED 2026-08-13 — DO NOT AUTOMATE THIS SCREEN.**
>
> This section previously said `POST /data/WM/wm/devices` (`deviceClass=V`) was verified at 201.
> That is false on the wire. Every recorded attempt returns **`404`, `errorCode -1403`,
> `"no rows affected"`** — six cases in `../../http/exchanges/devices.jsonl`
> (`voice-create-len4`..`len7`, and with `voiceTerminalId` both set and blank), plus
> `../../http/flows/lifecycle-voiceDevices.json`.
>
> The identical body succeeded once earlier in the same session, and a field-by-field diff shows
> no meaningful difference — so the behaviour is stateful and is not understood. `deviceClass=W`
> (Workstations) returns 201 throughout on the same endpoint.
>
> Worse for automation: **a failed save wedges the screen permanently.** The exception modal can
> be dismissed but its masks survive, leaving the form unusable and poisoning every later step in
> the same session. Recovery needs the `.x-mask` nodes removed from the DOM and a route change
> (`tools/cdp/recover.mjs`). Treat voice-device creation as manual-only until the backend
> behaviour is explained. See `../../http/claims.json` → `voicedevices-create-404`.

## Workstations

Many real pre-existing workstations (`000`, `012`, `0219`, `WCOUTBOUND`, `WCINBOUND`, `WC01`,
`WC TASKING`, plus many personal-machine-named entries like `TWALLACE`, `TSMITH`). Add form:
Workstation ID, Description, Touchscreen (Yes/No, for packing-station carton-content
confirmation), Movement Zone, Report/Label Printer, Scale Type + Scale Network Address.

Verified: `POST /data/WM/wm/devices` (`deviceClass=W`) → 201 → checkbox + Delete → separate GET
404.

## Hardware Settings — global site-wide config, deliberately NOT write-tested

Not a CRUD list — a single settings page with toggles that affect **every** RF/voice operator
site-wide. **Skipped, not undocumented**: a dry-run entry is logged in `../../index/ui-actions.jsonl`
with the observed click coordinates and layout for both toggles, per the standing policy in
`NOTES.md` §0 — if this write is ever explicitly requested, start from that entry rather than
re-discovering the form from scratch. Its exact save endpoint/payload was never captured (no
network log was taken for this page's own load), so that part is still unknown and would need a
live capture before any real automated write here.
- **Enable Session Recovery** (Yes/No) + **Recovery Timeout** (e.g. `20s`) — whether an
  interrupted RF connection restores the operator's session without re-login.
- **Single RF Login** (Yes/No) — whether the system limits an operator to one logged-in RF
  device at a time.
- **Language Code** grid (Voice Settings) — read-only-looking Locale → Language Code mapping
  (`Dutch (Holland)` → `nl_NL`, `French (France)` → `fr_FR`, `German (Germany)` → `de_DE`, etc),
  editable per the page description but not tested.

Deliberately left untested — flipping Session Recovery or Single RF Login live would affect every
currently-logged-in RF/voice operator in this shared QA environment, a different blast-radius
class than a config-only record. Consistent with the "no live-multi-user-impact writes" exception
carried from the campaign's standing rules.

## Verified writes (summary)

- `POST`/`DELETE /data/WM/wm/printers/{code}*!{warehouseId}`
- `POST`/`DELETE /data/WM/wm/devices/{code}*!{warehouseId}` (deviceClass `R`, `V`, `W` each
  verified independently)

All logged in `../../index/ui-actions.jsonl`.

## Open items

- Vendors sub-tab on RF Devices (14 real vendors) — not tested.
- Hardware Settings toggles — deliberately not tested (live multi-user impact).
- Printer/Workstation Report/Label Printer associations, Scale Type/Network Address, Movement
  Zone — not exercised on any screen.
- Edit (`PUT`) not tested on any Hardware screen — only create/delete.
