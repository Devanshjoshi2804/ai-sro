# Screen: Suppliers

nav_path: Configuration > Partners > Suppliers
route hash: `#wm.config/wm.config.partners.suppliers////`

234 real suppliers in this environment, mostly EDI/receiving-synced (supplier numbers look like
GS1-style codes, e.g. `0040381130715`). "Add" creates a genuinely new, manually-entered supplier.

## Fetching the list (the "R" in CRUD, not just single-record GET)

```
GET /data/WM/wm/suppliers?query=[]&offset=0&limit=50&siteId=SG&subsites=----
```

- `query=[]` — empty JSON array means no filter. A real filter is a JSON array of condition
  objects (see other screens' `query=[{"column":...,"operator":"EQ","value":...}]` patterns
  already in `../../index/api-endpoints.json`).
- `offset`/`limit` — standard pagination. The UI's page-size selector (default 50 here) sets
  `limit` directly; `offset` advances by `limit` per page. Matches the "Page 1 of 5, Displaying
  1-50 of 234" control shown in the grid footer.
- **`start` is NOT a synonym for `offset`** — it is accepted and silently ignored. Verified
  2026-08-11: `limit=3&offset=3` returns rows 4-6, while `limit=3&start=3` returns rows 1-3,
  identical to no paging param at all. Anything sending `start` reads page 1 forever and looks
  like it is working.
- The response is an envelope, not a bare array: `{@type, data:[…], first, last, next, limit}`.
  A single record comes back as `{@type, data:{…}}` — unwrap `.data` before using it as a `PUT`
  body, or the write goes out shaped `{@type, data}` and still returns `200` while doing nothing.
- Filters: `query=[{"column":…,"operator":"LK","value":…}]` on this collection returned `422`
  in testing — the exact filter grammar is not yet pinned down. Page through with
  `offset`/`limit` until it is.
- A separate `GET /data/WM/wm/suppliers/count?...` call gets the total for the pager, decoupled
  from the row-fetching call.
- Column definitions and default filter come from two side-channel calls fired once per screen
  load: `GET /refs/filtering/api/v1/filterDefs?name=WM<Entity>` and
  `GET /refs/filtering/api/v1/filters?filterDef=WM<Entity>&default=`. These don't carry row
  data, just UI metadata (available filter columns, saved filter presets) — safe to ignore for
  a data-only client, but explains two of the "extra" requests seen on every screen load.

This list-call shape (`query=[]`, `offset`/`limit`, a separate `/count`, and the
`filterDefs`/`filters` metadata pair) is the **standard pattern across every list screen tested
so far** — document it once here rather than repeating it per screen.

## Buttons and actions

| Button | Action | API call(s) | Payload | Notes |
|---|---|---|---|---|
| Add | opens "Add New Supplier" form | `POST /data/WM/wm/addresses` (addressType `SUP`) → `POST /data/WM/wm/suppliers`, both `201` | see `write-endpoints.json` | Required: Supplier* (number), Client*, Supplier Address*. Client combobox accepts typed text matching a real client code (e.g. `----`) — this one binds fine, unlike the search-style combos on Carrier PRO Number. |
| Copy | duplicate as new | not captured | — | Open item. |
| row click | opens view/edit form | `GET /data/WM/wm/suppliers/{id}?expand={address}` | — | |
| Save (in edit) | **works for supplier-owned fields only** | `PUT /data/WM/wm/suppliers/{id}` | full record, envelope unwrapped | `200` always. Supplier-owned columns persist; address-projected columns are silently dropped. See the section below — this is a join view, not a protected record. |
| Delete | removes supplier(s) | not captured via UI click; direct-API equivalent tested: `DELETE suppliers/{id}` then `DELETE addresses/{id}` | — | Both `200`, confirmed `404` after. |

## The PUT "rejection" was a misdiagnosis — this is a join view (settled 2026-08-11)

Two earlier readings were both wrong: first "suppliers are read-only", then the narrower
"existing EDI-synced records are protected from edits". Neither survives a controlled test.

Method: created supplier `ZZAUDIT01` through the API, then immediately `PUT` a batch of fields
on it and re-read via a separate `GET`. A record seconds old, never touched by EDI — and the
same fields still dropped. So it was never about record provenance.

**What is actually going on:** `/data/WM/wm/suppliers/{id}` is a **join view over the supplier
row and its address row**. `PUT` writes only the columns the supplier row owns and silently
discards the rest — `200`, no error, no partial-write warning.

| Persists on `PUT suppliers/{id}` | Silently dropped (address-owned) |
|---|---|
| `trustedFlag`, `autoReceiveFlag` | `receivingPhone`, `receivingFax` |
| `trackConsignment`, `consignmentDays`, `consignmentType` | `addressName`, `addressLine1..3` |
| `receiveStatus`, `addressId` | `city`, `state`, `postalCode`, `countryName` |
| | `firstName`, `lastName` |

**The trap inside the trap — two fields are aliases.** `supplier.receivingPhone` *is*
`address.phoneNumber`, and `supplier.receivingFax` *is* `address.faxNumber`. There is no field
called `receivingPhone` on the address resource. So writing `receivingPhone` fails through the
supplier resource (wrong table) *and* through the address resource (wrong field name) — which
is exactly why it looked like a permanent rejection.

Correct way to set a supplier's receiving phone:

```
PUT /data/WM/wm/addresses/{supplier.addressId}
{ ...address record..., "phoneNumber": "555-0129", "faxNumber": "5552220000" }
```

Then re-read the supplier: `receivingPhone` / `receivingFax` now show those values.

**Also corrected:** the address is *not* required to create a supplier. `POST /suppliers` with
only `{supplierNumber, clientId, trustedFlag, trackConsignment}` returns `201`. "Supplier
Address\*" is a form-level requirement, not an API one — the 2-resource cascade in the Add
button's capture is what the *UI* does, not the minimum the API accepts. `addressId` can be
attached later with an ordinary `PUT`.

## Fields (Supplier record, `/data/WM/wm/suppliers/{id}`)

| Field | Type | Required (create) | Notes |
|---|---|---|---|
| `supplierNumber` | string | yes (from "Supplier*") | resource id is `{clientId}*!{supplierNumber}` — that order, confirmed 2026-08-11 (the reverse returns 404, the bare number returns 400) |
| `clientId` | string | yes | |
| `addressId` | string | **no** — optional at the API | UI requires it; API accepts a supplier without one. Attach later via `PUT`. |
| `trustedFlag` | boolean | no | default `false` |
| `autoReceiveFlag` | boolean | no | disabled in UI unless `trustedFlag` is true |
| `trackConsignment` | string | no | default `'TRKNONE'` |
| `receivingPhone`, `receivingFax`, `manufacturerId`, `barCodeTemplateId`, `lotFormatId`, `serialNumberTypeId`, `receiveStatus` | string | no | all nullable business config; **PUT-editable only if supplier was created in-app, not on EDI-synced records** (see above) |

## Verified write operations

`../../index/write-endpoints.json`: `POST addresses` + `POST suppliers` (create cascade),
`DELETE suppliers/{id}` + `DELETE addresses/{id}` (reverse-order delete). `PUT suppliers/{id}`
documented as a **negative result** — silently ignored on existing records.

## Failure cases (retrofitted 2026-08-12)

1. **Save is NOT gated client-side upfront** — contrast with Customer Types
   (`customer-types.md`), which shows red required-field icons on page load and disables Save.
   Here Save stays enabled/clickable the whole time; clicking it on a blank form is what reveals
   the red icons on `Supplier*`, `Supplier Address*`, `Client*`. Confirmed via network capture
   that this blank-form Save click fires **zero requests** — purely client-side, but the UX is
   opposite in timing from Customer Types. An automation script must click Save once to discover
   which fields are required on this screen, rather than trusting the initial page state.
2. **Duplicate supplier number is a real server-side 409.** Filling the form with a real existing
   supplier number (tested `0040381130715`) + a valid existing client + a fresh address, then
   Save, returns `POST /data/WM/wm/suppliers` → **409 Conflict**, surfaced to the user as an
   in-app modal "Record already exists." — a genuine REST status code, not a client-side check
   (contrast with Customer Types' duplicate check, which never touches the network at all).
3. **CORRECTED 2026-08-12 — this screen DOES orphan an address.** An earlier version of this file
   claimed `POST /wm/addresses` never fires when the supplier check fails, and presented Suppliers
   as the safe contrast against the Clients cascade. **That was wrong.** Re-run under Playwright
   with full request/response capture (`tools/cdp/trace.mjs suppliersDuplicate`, evidence in
   `../../http/flows/suppliersDuplicate.json`):

   ```
   POST /data/WM/wm/addresses  -> 201   (addressId A000365889 assigned)
   POST /data/WM/wm/suppliers  -> 409
   ```

   The address POST fires first and succeeds, exactly as on Clients. The original reading came
   from eyeballing the browser network panel during a hand-driven session and missing the call.
   **Consequence: a retry loop on this screen leaks one address record per failed attempt.** Treat
   Suppliers and Clients identically — both need explicit orphan cleanup before retrying. See
   `../../http/claims.json` for the full before/after.

## Open items

- Copy button — not captured.
- Bulk multi-select Delete via the UI button — not tested (direct-API delete confirmed instead).
- Barcode Template / Lot Format / Serial Number Type dropdowns — not exercised.
