# Damage record

Records of state this project changed on the live system and could not restore.

## Hold HLD0307485 left applied on LPN 00000776442003826960 — 2026-08-18

**State:** `onHold: true`, quantity 65, status AV (unchanged), holdsHistory 1 row.
**Hold:** `HLD0307485` prefix `SG` — "Greenlight Hold", type RH, severity 3.
Allows allocation, **blocks movement**.

**What happened.** Capturing the Apply/Release pair — chosen as the safest reversible operational
write — the apply succeeded and the release was refused:

```
errorCode 90011  Invalid Hold Transaction. (Hold with type (RH) not editable by (USER))
```

Three release payloads were tried; all failed identically. This is a permission rule on the hold
TYPE, not a malformed request.

**Why it was not foreseeable from the read side.** The hold definition exposes allowAllocationFlag,
allowMoveFlag and allowInventoryStatusChangeFlag, none of which describe who may release the hold.
The LPN was verified unheld with an empty hold history before the write, and the least restrictive
of the 60 hold definitions was chosen deliberately.

**To clear it:** an account with permission to release type RH holds must release hold
`HLD0307485` on LPN `00000776442003826960` (detail `D0000006VDYW`). Effect meanwhile: the LPN
can still be allocated but cannot be moved.


---

## 2. Two pending inventory adjustments queued for approval — 2026-08-19 — **RESOLVED**

**State:** rows `1578979` and `1578980` in `/wm/inventoryAdjustmentApprovals`, both
`adjustmentQuantity -55` against LPN `00000776442003821453` (detail `D00000056ORS`, item
`0113228000`, location `RB327A`), `deviceCode 000`, reason code `0003`.

**No stock has moved.** `approvalRequired: true` came back on both calls and neither was approved,
so the on-hand quantity is still 55. The rows are sitting in an approval queue, not in the ledger.

**What happened.** Proving `PUT /wm/inventory/adjust` was meant to be the reversible test of the
fifteen: +1 then -1. But the endpoint does not take a delta. It reads `scannedQuantity` as the
**counted** quantity and derives the adjustment from it, so `scannedQuantity: 0` against a 55-unit
detail queued a -55 write-off — twice, once per direction of the intended round trip. The
`inventoryAdjustmentQuantity` field that looked like the delta was ignored.

**Why it was not foreseeable from the contract.** The payload built by the client
(`getQuantityAdjustmentData`) carries `unitQuantity`, `inventoryAdjustmentQuantity` and
`scannedQuantity` side by side with no indication of which one the server treats as authoritative.
The name `inventoryAdjustmentQuantity` reads as the delta; it is not.

**Cleared 2026-08-19:** the user rejected both rows from the Adjustments screen. No stock ever moved.
The original instruction, kept for the record:

**To clear it:** reject rows `1578979` and `1578980` from the Adjustments screen
(`#wm.inventory/wm.inventory.adjustments`). `DELETE /wm/inventoryAdjustmentApprovals/{rowId}`
returns an empty-bodied 404 — there is no direct delete route, and the approve/reject routes live in
a lazily loaded QuickApp bundle that would not load for mining.

**Unrelated pre-existing row:** a `-1` adjustment on the same LPN dated 2026-08-13 (`deviceCode
NONE`) was already in the queue and was left untouched.

---

## 3. One report bookmark that cannot be deleted — 2026-08-19

**State:** bookmark `RPTBMRK-20260819084827_755006` on report `BP-PackingList`, owned by user
`RKUCHIYAGM`, with `bookmarkDetails` "ZZAUDIT bookmark v2".

**Impact: negligible.** A bookmark is a per-user pointer at a report. It changes no warehouse data
and is visible only to the account that created it.

**What happened.** Proving `POST /reporting/reports/reportBookmark` needed a bookmark to exist, and
creating one was the safe way to do that rather than editing somebody's real bookmark. Create (`201`)
and update (`PUT`, `200`) both worked. **`DELETE` on the same path returns `405 Method Not Allowed`** —
there is no API route to remove a bookmark, so the thing created to avoid touching real data cannot
be cleaned up over the API.

**Why it was not foreseeable.** The route triplet POST/PUT/DELETE is the norm on this API, and the
mined route list contains `reporting/reports/reportBookmark` for POST and `.../reportBookmark/` for
PUT — with no hint that DELETE is absent. Checking for the reverse path BEFORE creating is the
lesson, and it is the same lesson that worked well for the shipment/load assignment, where
`cancelWorkUnassignShipmentFromStop` was found first.

**To clear it:** remove the bookmark from the Reporting UI, which presumably has the delete the API
lacks. Or leave it — it is inert.

---

## 4. The only error-state pick was consumed — 2026-08-19

**State:** pick `W0000011IPJR` (workRequestId `5490618`, schedule batch `SBDTEST1`, order
`2094733108`, qty 26) moved `E` (Error) → `P` (Pending) → `R` (Released). It is now Released.

**Impact: low, and arguably a repair.** `SBDTEST1` is a test-prefixed batch, consistent with the
CSTEST / SPTEST data elsewhere on this instance, and Error → Released is a transition an operator
would make deliberately. No inventory moved; `appliedQuantity` is still 0.

**But it is not reversible, and it cost future coverage.** There is no verb that puts a pick back
into Error, and that pick was the ONLY row in status `E` across the 200 read from
`wm/picks/consolidatedPicks`. The distribution is now `R 184, C 16` with no `E` at all. So:

- `wm/workAssignments/removePicks/batch/async`, whose client gate is `pickStatus === 'E'`, can no
  longer be exercised here at all. It is recorded as `unresolved`, and now cannot progress.
- `resetPicks` cannot be re-demonstrated from Error without new error-state data.

**Why it happened.** Proving the two verbs required the state they consume — Reset consumes Error,
Release consumes Pending — and there was exactly one specimen. Both proofs were worth having, but
spending the last of a rare state on the first verb that wants it forecloses every later verb that
wants the same state.

**Lesson for the next sweep:** before acting on a row in a rare state, count how many rows share
that state and list the other routes gated on it. If the count is one, decide which verb the
specimen is worth spending on rather than discovering the trade after the fact.

**To restore the coverage:** an operator would need to drive a pick into Error (a failed pick
confirmation on the RF, typically), after which `removePicks` becomes testable again.
