# Screens: Existing Carriers, Carrier PRO Number, Transport Modes, Carrier Cross Reference

All four live under Configuration > Partners > Carriers.

## Existing Carriers

route hash: `#wm.config/wm.config.partners.carriers.main////`

| Button | API call(s) | Payload | Notes |
|---|---|---|---|
| Add | `POST /data/WM/wm/carriers` | `{carrierCode, carrierName, ...}` | Single-resource — **no address cascade** fires if Carrier Address is left blank (address is optional here, unlike clients/customers). Required: Carrier* (code), Carrier Name*. |
| Copy | not captured | — | Open item. |
| row click | `GET /data/WM/wm/carriers/{id}` | — | |
| Save (edit) | `PUT /data/WM/wm/carriers/{id}` | full record minus `address`/`carrierDetails`/`carrierMatrices` | verified on `accountNumber` |
| Delete | not captured via UI; direct-API equivalent tested | `DELETE /data/WM/wm/carriers/{id}` | |

1581 real carriers in this environment.

## Carrier PRO Number

route hash: `#wm.config/wm.config.partners.carriers.carrierpronumber////`
Resource: `/data/WM/wm/carrierProNumbers/{id}`, id = `{addressId}*!{carrierCode}*!{poolPointAddressId}`.

- Verified `PUT` on `prefix`.
- **Carries a `version` field that increments on every successful write** (1→2→3 across
  edit+revert). It looks like optimistic locking. **It is not** — settled 2026-08-11: a `PUT`
  carrying `version: 1` against a record already stored at version 2 was accepted, applied, and
  bumped to 3. No `409`, no error, no rejection. `version` is a write counter and nothing more.
  **Consequence for the executor: this API has no lost-update protection at all.** Two workers
  editing the same record silently overwrite each other with no detectable signal. Serialise
  per-record on our side, or accept last-write-wins.
- Strip nested `carrierInfo` before PUT.

### Create/Delete — the Add form's picker doesn't work as expected

The `Carrier*` field on "Add Carrier PRO Number" has a magnifying-glass search icon. Typing a
real carrier code (e.g. `EXLA`) into it **visually fills the box but never binds the underlying
model value** — `form.getForm().findField('carrier').getValue()` reads back `null`. Calling
`field.setValue('EXLA')` directly still leaves `isValid() === false`. **Clicking Save on this
state produces zero symptoms**: no error dialog, no modal mask, no network request at all —
strictly quieter than the Existing Customers conditional-field case. Detected only by querying
`Ext.ComponentQuery.query('form')` and checking each field's `isValid()` directly.

Same applies to `Carrier Facility Address*`, also a search combobox.

**Working create, bypassing the picker entirely:**

```
POST /data/WM/wm/carrierProNumbers
{
  "addressId": "<a real existing address id>",
  "carrier": "<a real existing carrier code>",
  "poolPointAddressId": "<any new distinguishing string>",
  "checkDigitMethod": "", "format": "", "numberLength": "10",
  "nextValue": "", "prefix": "", "separator": ""
}
```
→ `201`, `resourceId` = `{addressId}*!{carrier}*!{poolPointAddressId}`. `DELETE` on that id
returns `200`, confirmed `404` on a following read. Full CRUD (`PUT`/`POST`/`DELETE`) now
verified clean.

## Transport Modes

route hash: `#wm.config/wm.config.partners.carriers.transportmodes////`
Resource: `/data/WM/wm/transportModes/{id}` (id = the 1-3 char mode code, e.g. `AF`, `GND`).

**Critical: this collection is NOT site-scoped.** Calling it with `?siteId=SG&subsites=----`
returns a `500`, not an empty result — the real app calls it with **no query params at all**.
This was the actual cause of an earlier false "empty collection" finding; the collection has 21
real global reference records (`warehouseId` is `null` on every row).

| Action | API | Payload |
|---|---|---|
| edit | `PUT /transportModes/{id}` | full record |
| create | `POST /transportModes` | `{transportMode, transportModeDescription, directFlag:0, smallPackageFlag:0, palletBuildConsolidationBy:'', warehouseId:''}` |
| delete | `DELETE /transportModes/{id}` | — |

All verified edit→verify→revert and create→verify→delete→verify, no siteId param on any call.

## Carrier Cross Reference

route hash: `#wm.config/wm.config.partners.carriers.crossreferences////`
Resource: `/data/WM/wm/carrierCrossReferences/{id}`, id = `{carrier}*!{destinationName}*!{serviceLevel}`.

Maps this WMS's carrier/service-level codes to an external TMS (all current rows point to
`destinationName: "ENVEYO"`). Verified edit (`taxID`) and full create→delete→verify cycle.
Create body: `{carrier, destinationCarrier, destinationLevel, destinationName, serviceLevel, groundFlag:false, serverPrintsLabelFlag:false}`.

## Cross-screen pattern confirmed

Every one of these four screens: `PUT`/`POST`/`DELETE` all work cleanly, no silent-ignore
behavior like `suppliers` showed. The only real gotchas found across all four Partners carrier
screens were (a) the site-scoping trap on `transportModes`, and (b) the general null-vs-empty-
string revert rule from `clients` (applies here too, not re-verified per field but assume it
holds).

## Failure cases (retrofitted 2026-08-12, Existing Carriers only so far)

Save gates proactively for required fields (`Carrier*` red icon on page load, matches the
Clients/Customer Types style).

**CORRECTED 2026-08-12 — the duplicate check is NOT server-side.** This file previously claimed
the form accepts the click and the server rejects it. Re-tested under Playwright with request
capture (`tools/cdp/modal-probe.mjs carriersDuplicate`): filling a real existing carrier code
(`001`) + Carrier Name and clicking Save produces the modal `Error / Record already exists` while
sending **zero requests** — 0 before the click, 0 after. The modal is generated client-side. The
original reading mistook a server-styled error message for evidence of a server round-trip.

At the API layer a duplicate carrier *does* return `409` (`../../http/exchanges/carriers.jsonl`),
but the UI never gets that far. Those are two separate facts and only the first one matters to an
executor calling the API directly. See `../../http/claims.json`.

## Failure cases — Transport Modes (retrofitted 2026-08-12)

Blank Save: red required-field icons on `Transport Mode*`/`Description*` appear only after
clicking Save (Suppliers-style timing, not proactive-on-load), but confirmed **zero network
requests** fire — purely client-side. Duplicate code test (typed a real existing mode code):
same result — Save click produces no request, form just shows the field invalid. Client-side
gate, matching the Customer Types/Existing Customers architecture (pattern #1/#4), not the
server-side-409 style of Suppliers/Existing Carriers.

Also note: this screen's internal Add-form scroll is a real ExtJS `div.x-panel-body` region,
distinct from the outer page scroll — the Save/Cancel footer stays pinned at a fixed page
position outside it. Synthetic wheel-scroll actions did not reliably move this container;
setting `element.scrollTop` directly via JS did. See `KNOWLEDGE-BASE.md` for the general
technique (query `div.x-panel-body` filtered by `scrollHeight > clientHeight`, then set
`scrollTop`).

## Failure cases — Carrier Cross Reference (retrofitted 2026-08-12)

Blank Save: no proactive gate on load; clicking Save on an empty form reveals red icons on
`Carrier*`/`Service Level*`/`External System Name*`, **zero network requests** fired — client-side.

Duplicate-key test: filled a real existing composite key (`Carrier=FDE2`, `Service Level=FDE2`,
`External System Name=Enveyo`, matching an existing row). All three fields immediately show a red
icon **and** a real, queryable validation message: `"The External System Cross References already
exists."` (confirmed via `Ext.ComponentQuery` — `field.isValid() === false`, `field.getErrors()`
returns that string; the bound `value`s are correct, so this is a genuine live uniqueness check,
**not** the broken-combobox-binding bug seen on Carrier PRO Number). Save produces **zero network
requests** — the composite-key duplicate check runs entirely client-side, live on field
change/blur, before Save is ever clicked. No orphan-record risk since nothing ever POSTs.

This is a distinct sub-variant of the client-side-gate pattern: unlike Customer Types/Existing
Customers/Transport Modes (icon-only, no readable inline message), this screen's client-side
validator carries an explicit, human-readable duplicate-key error string. Six Partners screens now
directly tested for failure-case behavior (Customer Types, Suppliers, Clients, Existing Customers,
Existing Carriers, Transport Modes, Carrier Cross Reference — seven, all with materially different
validation UX), confirming the standing rule: never assume one screen's validation architecture
(client vs server, proactive vs on-click, silent icon vs message) carries over to a sibling screen.

## Open items

- Copy button on Existing Carriers — not captured.
- Service Levels sub-editor (visible on both Add Carrier and the main carrier record) — not
  explored, likely its own nested CRUD (`carrierServiceLevels`, seen in the read catalogue).
- Carrier Cross Reference's COD Address sub-form (Edit link, nested address fields) — not
  exercised, unknown whether it cascades a separate `addresses` POST like Clients/Existing
  Customers or stays embedded in the parent record.
