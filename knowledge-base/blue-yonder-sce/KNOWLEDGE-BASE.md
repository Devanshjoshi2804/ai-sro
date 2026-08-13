---
title: "Blue Yonder SCE — Knowledge Base (§4.3 shape)"
system: "Blue Yonder Supply Chain Execution Web Applications"
deployment: "bf56-kms-wms-web-np2.jdadelivers.com (QA sandbox, site SG)"
last_validated: "2026-08-10"
---

# Blue Yonder — Knowledge Base

Populates `ai-first-sro-solution-design.md` §4.3 for this system: *"auth profile refs, endpoint
catalogue with discovered throttling limits, MOCA command signatures, element fingerprints with
last-validated timestamps, known modals and quirks, business rules."* Everything below was
observed empirically against a real QA sandbox session, not inferred from docs alone. Doc-derived
claims are marked **[doc]**; live-observed claims are marked **[live]**.

This also answers the design doc's **Open Decision #2** (Blue Yonder deployment shape) for this
specific deployment — see §6.

---

## 1. Auth profile (refs only, no secrets)

**[live]** Two entirely separate auth surfaces exist, and they are not interchangeable:

| Surface | Mechanism | Used for | Lifetime |
|---|---|---|---|
| Portal session | Cookies (`REFSSessionID`, app-specific session cookie, `__cf_bm`), issued via Azure AD B2C OIDC | Reads (`GET`) | ~30 min observed idle timeout |
| Write authorization | Opaque `csrf-encrypt-token` header, ~88 chars, base64-like, distinct from any readable cookie | Writes (`PUT`/`POST`) | Unknown — not derived from a stable cookie, likely session-bound and possibly rotated |

**[live] RESOLVED — was a wrong-token problem, not a blocked-endpoint problem.** The readable
`JDA-CSRF` cookie (36 chars, UUID-shaped) is **not** the value the app sends as the
`CSRF-ENCRYPT-TOKEN` header (88 chars, different alphabet). Mirroring the cookie as the header
gets a bare `404` with an empty body — every earlier attempt (top frame, correct iframe with
matching Referer, with/without `x-requested-with`) failed this way, and it was reasonable at the
time to read that as a gateway/WAF block. It wasn't. **The real value lives at
`Ext.Ajax.defaultHeaders['CSRF-ENCRYPT-TOKEN']`** — set once by the ExtJS app at load, retrievable
with one `browser_evaluate` call scoped to the app iframe's JS realm. Using that exact value, a
plain `fetch()` PUT succeeds normally (`200`), from any frame, any origin within the page. Proven
with a real (non-no-op) value change that persisted, was confirmed on a **separate** `GET` (§3.2
cross-path verification), then reverted — same clean result.

**Implication for the SRO design — corrected:** a script client that has (a) a session cookie and
(b) this token **can write** to this deployment via a clean, direct L3 API call. It does not need
L4 network-interception replay or L5 UI automation to perform a write — those remain valuable as
fallbacks (e.g. session refresh via automated login, see below), but they are not the *only* path
for writes as earlier concluded. The remaining constraint is narrower than "writes don't work":
only **specific, individually verified (method, path) pairs** are known-safe — see
`../blue-yonder-mcp/server.mjs`'s `write_api` tool and
`index/write-endpoints.json`, which is deliberately small and grows only by repeating the same
edit→verify→revert proof for each new endpoint, never by assuming a documented-looking path
behaves like a tested one.

**Auth profile ref, cloud path (documented but unverified — README has full detail):**
Azure AD B2C tenant `blueyonderalphaus`, policy `b2c_1a_signin_group_17`, `client_id` on file in
`../blue-yonder-mcp/README.md`. A Blue-Yonder-issued app registration (client credentials or ROPC
against this tenant) is the only path that plausibly gets a real OAuth2 bearer token instead of a
scraped session — and a bearer-token call may or may not need to satisfy the same
`csrf-encrypt-token` gate. **Untested — this is the first thing to try once credentials exist.**

**[live] Full interactive login chain is deeper than one B2C hop — corrects the README:**

```
Portal (bf56-kms-wms-web-np2.jdadelivers.com)
  -> Azure B2C authorize, tenant "blueyonderalphaus", policy "b2c_1a_signin_group_17"
  -> IdP chooser: "Kenco Management Services, LLC (SSO)" | "Local WMS users (bf56-001-eus2) (SSO)"
     | "Blue Yonder Support Sign In"
  -> [Local WMS users branch] Keycloak realm "bf56-001-eus2", client "bf56-001-eus2-liam",
     host keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai
     -> username/password form, standard Keycloak login
  -> back through B2C authresp, second B2C tenant "blueyonderus" in the redirect_uri
  -> Portal, authenticated
```

Interactive username+password login against the Keycloak "Local WMS users" IdP **works and is
automatable** (confirmed by driving it end-to-end with Playwright) — this is a real, reproducible
fallback for session refresh that doesn't depend on scraping a live cookie out of DevTools.

**[live] Concurrency hazard, directly relevant to §6 of the design doc:** running a second
interactive login in a *second browser tab of the same profile* (shared cookie store) while an
existing authenticated tab was open **broke both sessions simultaneously** — the second flow's
B2C hop returned `400 Bad Request` at `.../oauth2/authresp`, and the first tab's already-working
session was invalidated in the same moment. Root cause is almost certainly B2C/Keycloak storing
flow state (nonce, state) in cookies that a second concurrent flow overwrote. This is direct,
empirical confirmation of the design doc's own rule — *"one browser per worker... isolate them"*
(§6) — for a reason more concrete than resource isolation: **shared cookies across concurrent
auth flows corrupt each other's session state entirely**, not just contend for browser resources.
Any executor implementation must give every concurrent Blue Yonder session (even just for one
tenant) its own isolated cookie store / browser context, never two tabs in one profile.

---

## 2. Endpoint catalogue

Full catalogue: `index/api-endpoints.json` (551 endpoints, 207 app routes, 176 joined to nav
paths, 185 joined to help topics). Built by `tools/build-api-catalogue.mjs`.

**[live] Throttling limits discovered:** none observed. No `429`, no `Retry-After`, no rate-limit
headers on any of ~600 requests captured across the harvest and write-testing sessions. Matches
the design doc's own warning: *"Blue Yonder MOCA has no meaningful protection against you
hammering it — you are responsible for not taking down a customer's WMS"* (§6). Treat the absence
of a rate limit as a constraint on **us**, not a green light.

**[live] Read/write path shapes differ:**
- Reads: synchronous `GET /data/WM/wm/<collection>` → `200` + `ResponseBodyWrapper{data:[...]}`.
- Simple writes (edit): synchronous `PUT /data/WM/wm/<collection>/<id>` → `200` + updated record.
- Complex writes (create): **async job pattern** — `POST /data/WM/wm/<collection>/async` returns
  `202`-equivalent with an `asynchronousResourceGroupId`; poll
  `GET /data/WM/wm/<collection>/async/{groupId}/resources` until
  `asynchronousStatus` leaves `IN_PROGRESS`. Terminal states seen: `SUCCESS`, `FAILURE`.

**[live] The standard list-fetch shape, confirmed identical across every screen tested:**

```
GET /data/WM/wm/<collection>?query=[]&offset=0&limit=<pageSize>&siteId=SG&subsites=----
GET /data/WM/wm/<collection>/count?limit=1&offset=0&countMapping=&siteId=SG&subsites=----
GET /refs/filtering/api/v1/filterDefs?name=WM<Entity>       (once per screen load)
GET /refs/filtering/api/v1/filters?filterDef=WM<Entity>&default=   (once per screen load)
```

- `query=[]` is "no filter"; a real filter is a JSON array of `{column, operator, value}`
  objects (many concrete examples already in `index/api-endpoints.json`).
- `offset`/`limit` map directly to the grid's page-size selector and page position — this is
  the pagination contract for every collection endpoint, not just one screen's.
- The `/count` call is separate from the row-fetch call and drives the pager's total, not the
  row data.
- `filterDefs`/`filters` are UI metadata only (available filter columns, saved presets) — no
  row data, safe to skip entirely for a data-only client.
- Exception already found: `transportModes` rejects `siteId`/`subsites` outright (`500`) — don't
  assume every collection accepts the same query params without checking a real capture first.

---

## 3. MOCA command signatures

**[live] The read layer is plain REST; the write layer is MOCA wrapped in the async job
envelope.** This corrects an earlier note in `NOTES.md` that claimed no MOCA on the wire at all.
Confirmed by a failed `create warehouse` job whose `FAILURE` response body contained the literal
MOCA command text:

```
create warehouse WHERE adj_thr_unit = 0 AND wmp_left_x = 0 AND ... AND wh_id = 'ZZTEST01'
  ... | publish data where res_id = 'ZZTEST01'
```

This is exactly the artifact §2.2 of the design doc wants captured from a demo — *"the network
calls are MOCA commands... a documented, schema-discoverable, replayable artifact."* One failed
write, fully logged, handed us a verbatim command signature for free.

**[live] Atomicity:** a `FAILURE` async job leaves **zero partial state**. Verified by re-checking
the warehouse list after the failed `ZZTEST01` create — nothing persisted. This validates §5
TIMEOUTS' rule *"never auto-retry a validation failure — retrying just repeats the error"* with a
real example: the `ZZTEST01` failure (errorCode 2966, pick-method/work-type/zone conflict) is
deterministic and input-independent — see §5 for why.

---

## 3b. One logical "create" is often several physical resources

**[live]** Creating a single `client` through the real UI form fires **four separate `POST`
requests**, in order, each depending on the previous one's generated id:

```
POST /data/WM/wm/addresses            -> 201, returns a generated addressId (e.g. A000365873)
POST /data/WM/wm/clients              -> 201, body includes that addressId
POST /data/WM/wm/clientWarehouse      -> 201, enables the client for one warehouse
POST /data/WM/wm/packingConfigurations -> 201, per-warehouse packing settings
```

This was only visible by watching the **full** network sequence after clicking Save once in
the real UI — guessing a single-resource POST body from the "Clients" screen's visible fields
would have produced an incomplete, non-functional client (no address, not enabled for any
warehouse, no packing config). **Never hand-construct a create payload from a docs page or a
GET response shape — capture the actual cascade from one real Save click first.**

Deleting reverses the dependency order exactly: `packingConfigurations` → `clientWarehouse` →
`clients` → `addresses`. Deleting out of order risks a foreign-key-style rejection (untested —
we deleted in the correct order and it worked cleanly every time, so the failure mode itself
is still hypothetical, but the dependency direction is directly observed from the create order).

Full verified schemas for all four create/delete pairs are in
`index/write-endpoints.json`. This is now the template for testing any other "Add" button on
the platform: click it once for real, watch every request it fires, don't assume it's one POST.

---

## 4. Element fingerprints — a real quirk for the L5 recipe layer

**[live] ExtJS component IDs are not stable identifiers.** The Save button was `#button-1360` on
one form load and `#button-1464` on the next (same screen, same user, minutes apart). Any L5
recipe or healer that fingerprints by DOM id will break on the very next page load. **Fingerprint
by accessible role + name instead** (`role=button, name="Save"`) — that stayed constant across
every reload in this session. This is a concrete instance of exactly the failure mode §3.3's
"Case 2a — Heal" step exists to catch (locator miss on ExtJS-generated ids), and it will trigger
on nearly every screen in this app, not just Warehouse config — ExtJS auto-generates ids this way
by default.

**[live] Iframe naming is per-session, not stable either.** The app's iframe `name` attribute
embeds a session context hash (`Ctx:f4d6755a...-1786341311975`) — do not hardcode it; always
resolve the active iframe at runtime.

**[live] CRITICAL: error dialogs can be completely invisible to accessibility-tree snapshots
while still blocking the entire page.** A validation failure on the "Add Customer" form popped
an ExtJS `messagebox` with real text ("Customer Type field is mandatory when..."), rendered at
real, correct on-screen coordinates (`getBoundingClientRect()` confirmed it), and holding a
page-covering `.x-mask.modal-mask` — yet it **never appeared in any accessibility snapshot**,
across several consecutive snapshot calls. Every subsequent click on the real Save button landed
on the invisible mask instead and produced **zero symptoms**: no error returned, no network
request fired, no visible change, nothing to react to. Two full Save attempts were silently
swallowed this way before the cause was found by directly querying
`Ext.ComponentQuery.query('[floating]')` for modal components and reading their DOM text
manually — a method that does not depend on the accessibility tree at all.

**This is the single most important operational finding for any L5 automation against this
app.** A recipe or healer that only checks "did an error appear in the snapshot" will hang or
silently no-op indefinitely on this class of failure. **Any automation step that clicks Save (or
any submit action) must, immediately after, check for `document.querySelector('.x-mask.modal-mask')`
and `Ext.ComponentQuery.query('[floating]').some(c => c.modal && c.isVisible())` as a fallback —
never rely on the accessibility snapshot alone to detect a blocking modal.**

---

## 5. Known modals and quirks

| Quirk | Detail | Source |
|---|---|---|
| Unauthenticated request → HTTP 200 | Expired/missing session returns the login page HTML with status `200`, not `401`. Any client checking only `res.ok` reads a dead session as a healthy empty result. | live, documented in `../blue-yonder-mcp/README.md` |
| Session idle timeout ~30 min | Matches the design doc's own example quirk almost verbatim ("Blue Yonder session drops after 20 min idle", §2.6) — independently confirmed here at ~30 min. | live |
| "Unsaved Changes" confirm dialog | Clicking Cancel on a dirty form triggers a **second** confirm modal ("Unsaved Changes — Yes/No") before actually navigating away. A recipe that only handles the primary Cancel click will hang here. | live |
| Description field: silent client-side truncation | `Warehouse.Description` truncates at ~28 characters with **no error, no warning** — the truncated value is what's already in the outgoing request body, so this is not a server rejection. | live |
| Description field: separate hard validation | Certain characters (square brackets `[ ]`) trigger an explicit `"Invalid Warehouse Description"` error banner — a distinct code path from the silent truncation above. | live |
| Create-warehouse default pick methods | Every new warehouse auto-seeds release rules under fixed names `Pallet Replen` / `Case Replen` (**[doc]**, confirmed in the Pick Methods help topic: *"there are typically only two pick methods used for replenishments"*). If those names already have default release rules registered (true for any site with an existing warehouse, e.g. SG), every subsequent create collides on `(Pick Method, Work Type, Threshold Flag, Default Flag, Destination Move Zone)` — **deterministically, regardless of the new warehouse's own field values.** | live + doc cross-reference |
| GET on a bad resource ID → structured `400` | `GET .../warehouses/ZZNOTREAL` returns `{"errorCode":"910","userMessage":"Invalid input value for input argument: warehouseId"}` — a real, parseable error contract. Contrast with the bare, empty-body `404` on blocked writes (§1, now resolved) — that asymmetry is itself the signal reads and writes hit different enforcement layers. | live |
| **`null` in a PUT body does not clear a field** | Sending `{"bolaPrefix": null}` to revert a client field that started `null` returned `200` but left the field **unchanged** (still the test value) — the write silently no-oped rather than clearing it. Sending `{"bolaPrefix": ""}` (empty string) worked, verified `null` on a separate read. **General write-client rule for this API: to clear a field, send `""`, never `null`.** A revert routine that blindly replays the original GET body (which naturally contains `null` for empty fields) will silently fail to revert — caught here only because verification used a separate read, not the write's own response. | live — `clients` resource, likely applies across `/data/WM/wm/*` |
| **Some PUT-shaped endpoints silently ignore the whole write** | `PUT /data/WM/wm/suppliers/{id}` with `receivingPhone` changed to a real value returned `200` — and the response body itself echoed the record back with `receivingPhone` still `null`, not even partially applied. No error, no field-level rejection, indistinguishable from success unless you check the actual value. Suppliers here are EDI/receiving-synced master data, most likely read-only at the field level regardless of the route accepting a PUT. **Never trust a `200` alone as proof a write worked — always diff the specific field in the response (or a separate read) against what you sent, not just the HTTP status.** | live |
| **Remote search comboboxes silently ignore typed text** | Fields with a magnifying-glass icon (e.g. `Carrier*` on Add Carrier PRO Number) are remote/forceSelection comboboxes: typing a value visually fills the box but leaves the underlying model value `null` — confirmed via `field.getValue()` after typing. Unlike a local-store combobox (typed text matching a cached option binds fine, e.g. `Client*` elsewhere) or the Customer Type case (fixed cleanly with `setValue()`), calling `setValue()` here still left the field `isValid() === false` — it needs an actual selected record from a remote query, not a string. **Clicking Save on this invalid state produces zero symptoms: no dialog, no mask, no network request at all.** Cleaner to detect than the invisible-dialog case (`Ext.ComponentQuery.query('form')[...].getForm().getFields()` reveals the invalid field directly) but requires the same discipline: after any Save click, confirm a request actually fired before assuming success *or* failure. Workaround: bypass the picker, `POST`/`PUT` directly with a real existing id value. | live |
| **Conditional required fields, not marked with `*`** | On "Add Customer", `Customer Type` has no asterisk but becomes mandatory the moment `Cross Dock Order Lines` or `Pallet Building` is left at its default "Inherit from customer type" — a cross-field business rule invisible from the form's static markup. Error only surfaced via the invisible-modal-mask mechanism above. **Assume any screen may have unmarked conditional-required fields; a clean `isValid()` check on individual fields does not catch cross-field rules.** | live |
| **Only GET/POST/PUT/DELETE exist here — full stop** | Probed `OPTIONS` (on a resource and its collection), `HEAD`, and `PATCH` against known-good paths. All five returned Cloudflare **error 520** ("Web server is returning an unknown error") — rejected at the CDN/WAF layer, never reached the app. No `Allow` header, no capability discovery available. **`PATCH` is not a thing here** — there is no partial-update alternative to PUT's full-record-replace; every edit must GET the full record, mutate the field(s), and PUT the whole thing back, which is exactly why the null-vs-empty-string gotcha above matters — the full record being replayed is the attack surface for silent revert failures. Session confirmed healthy after the probes (follow-up `GET` came back `200`, record unaffected). | live |

---

## 6. Business rules / answer to Open Decision #2

Design doc §0.1 lists Blue Yonder access as *"MOCA... queryable, schema-discoverable... Luminate
REST where the Connect/API entitlement is present."* Open Decision #2 asks: *"Cloud with Luminate
REST entitlement, or on-prem MOCA?"*

**For this deployment specifically: neither, cleanly — a third shape.** It's cloud-hosted (Azure
AD B2C federated to a Keycloak realm, Cloudflare in front), reads are plain REST, writes are MOCA
wrapped in an async REST envelope, gated by a non-cookie CSRF proof (`CSRF-ENCRYPT-TOKEN`,
sourced from the ExtJS app's own `Ext.Ajax.defaultHeaders`, not from any cookie). Call this
**"legacy web-portal REST, session+token authenticated."** Once corrected for the wrong-token bug
in §1, this shape *does* support L3 direct-API writes — with a session cookie and the app-level
token, both obtainable from one authenticated browser session. It is not a published/entitled
Luminate API, so there's no formal contract or SLA, but it is functionally an L3 write path today,
narrower and less durable than a real OAuth2 credential would give, but real.

This sharpens Open Decision #3 ("who owns credentials") differently than first thought: a scraped
session cookie **plus** the app-level CSRF token together are sufficient for both reads and
writes, so "customer-held delegated session" is a viable, already-working integration shape here
— not a fallback of last resort. A real OAuth2 client-credentials token (§1, case 14 in §7) would
still be the more durable production answer since cookies expire in ~30 min and the CSRF token's
own lifetime is unconfirmed, but the system does not *require* it to accept writes.

---

## 7. Edge-case matrix

Executed **[live]**, planned **[todo]**. All live cases ran against the single QA warehouse `SG`
or a nonexistent id, fully reversed, logged to `index/write-audit.jsonl`.

| # | Case | Status | Result |
|---|---|---|---|
| 1 | Create with valid-looking new data | live | `FAILURE`, atomic, no orphan (§3, §5) |
| 2 | Edit existing record, valid change | live | `200`, persisted, reverted, verified |
| 3 | Edit with over-length input (client path) | live | Silently truncated client-side (§5) |
| 4 | Edit with disallowed characters (client path) | live | Explicit `"Invalid Warehouse Description"` error (§5) |
| 5 | No-op write (identical value) via direct API | live, **superseded** | Originally read as blocked at a `404` gate — that was the wrong-token bug (§1). Retested with the correct `CSRF-ENCRYPT-TOKEN`: `200`, safe to retry, no distinct behavior for identical vs. changed values. |
| 6 | Over-length input via direct API (bypass client truncation) | todo | Not yet retested with the correct token. Now genuinely reachable — worth doing to learn if the server enforces length independently of the UI's silent truncation. |
| 7 | Disallowed characters via direct API (bypass client validation) | todo | Not yet retested with the correct token. Now genuinely reachable — worth doing to learn if `"Invalid Description"` is server-enforced or UI-only. |
| 8 | Write to nonexistent resource, direct API | todo | Not yet retested with the correct token. Row 9 shows reads return a structured `400` for this — worth confirming writes do too now that the real gate is understood. |
| 9 | Read on nonexistent resource | live | Structured `400`, real error contract (§5) |
| 10 | Correct frame/Referer, matched headers, direct API write | live, **superseded** | Frame/Referer were never the cause — root cause was the wrong CSRF token value (§1). Retracting the "gateway/WAF block" hypothesis entirely. |
| 11 | Session expiry mid-write | todo | Inferred (not re-tested) to behave like expired-session reads: `200` + login-page HTML. Needs a real ~30-min-aged session to confirm for `PUT`/`POST` specifically. Also unknown: does the CSRF token expire independently of the session? |
| 12 | Concurrent writes to the same record (race) | todo | No optimistic-locking field (`version`/`etag`) observed in any response body — two sequential edits both succeeded with no conflict signal. Needs two genuinely concurrent writers to confirm last-write-wins vs. lock. |
| 13 | Find where `CSRF-ENCRYPT-TOKEN` is minted / whether it rotates | todo | **Resolved enough to use** (it's a static value on `Ext.Ajax.defaultHeaders`, readable once per session) — still open: does it rotate on re-login, expire independently of the cookie, or differ per user/role? Matters for how often an automated client needs to refresh it. |
| 14 | Real OAuth2 bearer token (once B2C app registration exists) against the same write endpoints | todo | Still valuable for durability (session cookies expire ~30 min) but no longer the *only* way to write — cookie+CSRF-token already works. |
| 15 | Interactive username+password login via Keycloak "Local WMS users" IdP, driven by browser automation | live | Works, reproducible, no vision model needed — pure a11y-role clicks + form fill. Real fallback for session refresh. |
| 16 | Two concurrent login/session flows in one shared-cookie browser context | live | **Both sessions broke.** Second flow's B2C hop `400`'d, first tab's working session was invalidated too. Confirms §6 "one browser per worker" is load-bearing for correctness, not just resource isolation. |
| 17 | Real (non-no-op) direct-API write with correct `CSRF-ENCRYPT-TOKEN`: change, verify on separate read, revert | live | **The breakthrough.** `200` / `200` / `200`, value round-tripped exactly. See §1. |
| 18 | Revert a field to `null` by replaying the original (null-containing) GET body | live | **Silently fails** — `200` but field stays at the test value. Sending `""` instead works. See §5. Caught only because verification used a separate read; a same-response-trusting revert routine would have shipped a false "reverted" state. |
| 19 | PUT-shaped endpoint accepts a real changed value but ignores it entirely | live | `suppliers` — `200`, response body echoes the record back completely unchanged. Worse than an error: indistinguishable from success without diffing the actual field. See §5. |
| 20 | Full CRUD lifecycle: create → verify → delete → verify, across a multi-resource cascade | live | `clients` — 4 `POST`s to create (`addresses`→`clients`→`clientWarehouse`→`packingConfigurations`), all `201`; 4 `DELETE`s in reverse order to clean up, all `200`; both endpoints confirm `404` after. Fully clean, no orphan data. See §3b. |
| 21 | Probe for HTTP verbs beyond GET/POST/PUT/DELETE (`OPTIONS`, `HEAD`, `PATCH`) | live | All three return Cloudflare `520` — rejected at the CDN/WAF layer, never reach the app. No `Allow` header, no capability discovery. Only the four verbs already in use exist on this deployment. See §5. |
| 22 | Trigger a real client-side validation failure and observe how the error surfaces | live | **Invisible modal dialog** — real DOM, correct on-screen position, but absent from every accessibility snapshot, leaving a page-wide mask that silently swallows all further clicks. See §4. Single most important finding for L5 automation reliability. |
| 23 | Full CRUD lifecycle on a second, differently-shaped multi-resource entity (`customers`, 2-resource cascade vs. `clients`' 4) | live | Clean: `POST addresses`→`POST customers` (both `201`) to create, `DELETE customers`→`DELETE addresses` (both `200`) to remove, both confirmed `404` after. Also confirmed `customers` (unlike `suppliers`) genuinely accepts field edits. |
| 24 | Retest `suppliers` with `POST`/`DELETE`, not just `PUT` | live | **Corrects an earlier over-generalization.** `POST` (create, 2-resource cascade) and `DELETE` both work cleanly, `200`/`201`/`404` as expected. Only `PUT` on an *existing* EDI-synced record is silently rejected. "Suppliers PUT is rejected" ≠ "suppliers is read-only" — a real, specific asymmetry, not a blanket block. |
| 25 | Retest `carrierProNumbers` with `POST`/`DELETE` via a remote search combobox (`Carrier*`) | live | UI Save silently no-ops (zero symptoms, see quirks table) because the combobox never bound a real value. Bypassed the picker, `POST` directly with a real `addressId` + `carrier` + new `poolPointAddressId` → `201`. Full CRUD (`PUT` from earlier, now `POST`/`DELETE`) confirmed clean. |

---

## 8. What this means for the executor design (§3 of the SRO doc)

- **Reads for this system can go through L2/L3 today** — the 551-endpoint catalogue plus our MCP
  server (`../../blue-yonder-mcp/`) already implements exactly the pattern §0.1 recommends
  ("community MOCA MCP servers already exist, read-only default") — except purpose-built for this
  deployment's actual REST surface rather than raw MOCA.
- **Writes for this system CAN go through L3 today**, corrected from an earlier conclusion in this
  same document. A session cookie plus the app-level `CSRF-ENCRYPT-TOKEN` (§1) is sufficient for a
  clean direct-API `PUT`, no browser required once both values are in hand. `write_api` in
  `../../blue-yonder-mcp/server.mjs` implements this today for one verified endpoint. L4 replay and
  L5 UI automation remain valuable — L4 for *discovering* new safe write endpoints (recording a
  real demo, per §2.2), L5 for session refresh via automated login (row 15) — but neither is the
  only way to perform a write anymore.
- Per §3.2 (cross-path verification): every write test in this pass was already verified through
  a **different** path than the write itself — writes went through the UI form or direct fetch,
  verification went through a separate `GET`/network-capture read. That's the pattern to keep, and
  it's exactly what caught the wrong-token bug in the first place: the failing writes were never
  silently trusted.
- Per §3.4 (promotion ladder): still **Recorded**, not higher, for Blue Yonder writes — one
  verified endpoint is not a track record. Before promoting to Shadow: verify a few more endpoints
  with the same edit→verify→revert discipline, confirm the CSRF token's actual lifetime (row 13),
  and separately, the create-warehouse pick-method collision (§5) still needs a
  Customer-Support-registered pick method before that specific operation is usable at all.
