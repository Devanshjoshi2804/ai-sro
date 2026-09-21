# What the warehouse actually does

The shape this system mines is real, and it lives in the wrong place.

We have proved one job end to end: a mail asks for a customer type, the rig
fills the form on the page and presses Save, and the warehouse returns 201.
Twice in a row, for about two cents a run, every control found by its recorded
identity. That is the product working.

This document is the answer to a question that had not been asked: **is that
job representative?** The answer is no, and the way it is not representative
decides what to build next.

Measured **2026-09-18** against
[`knowledge-base/`](../knowledge-base/KNOWLEDGE-BASE.md) — 78MB captured from a
real Blue Yonder SCE QA sandbox (`bf56-kms-wms-web-np2.jdadelivers.com`, site
SG), not from vendor documentation. Claims below are marked where they are
inferred rather than counted.

---

## 1. The count that decides it

`index/form-models-all.json` holds every form model mined from the app:

| tier | count |
|---|---|
| `configuration` | 88 |
| `operational` | 1 |

Eighty-nine forms; one of them is operational. Counted, not estimated.

And all fifteen written recipes in [`recipes/`](../knowledge-base/recipes) are
master data — `partners/customer-types.md`, `partners/suppliers.md`,
`partners/carriers.md`, `warehouse/areas.md`, `equipment/equipment-types.md`
and the rest. There is not one recipe for an inbound or outbound operational
screen.

So the "Add button, fill a form, Save" shape that the miner finds cleanly, and
that we have now proved end to end, is **almost exclusively a configuration
shape**. Customer Types is representative of master data. It is not
representative of a warehouse's day.

## 2. What the browser is actually for

The high-volume physical work never touches this application at all.
`md/warehouse-management/picking.md` says it plainly:

> picks are confirmed by an **RF device, a voice recognition device, or a
> paper-based process**

Receiving, packing and shipping are framed the same way. The web screen gives
*visibility and the ability to manage* that work; it does not perform it. A
shift's thousands of picks and receipts are not browser events and never will
be.

Of 55 screens in `index/toolbar-actions.json`, a large share carry no domain
verb at all — export, print, refresh, filter. They are monitors. Automating a
monitor is automating reading.

What *is* clerical browser work, done by a person, repeatedly:

- **inventory** — cycle count scheduling, adjustments approval, holds, location audit
- **master data upkeep** — the configuration screens we already do
- **exception handling** — picking issues, receiving issues, shipping issues

The first two are mechanisable. The third is judgement across screens and is
not a demonstration-replay problem.

## 3. Where the repeated clerical work is

`index/operational-forms.json` holds **nine** operational forms. The one worth
naming first:

**Adjustments → Approve.** Fields: `Reason` (a required combo with a fixed
option list — `0003 Carrier Damage (Inbound)`, `0005 Product Put on Hold`, …),
`Comment`, `Generate Cycle Count`. Every RF-driven adjustment above a
threshold lands in this queue. Clearing it is the same small form, repeated
per row, varying a reason code and a comment.

Then cycle count scheduling (schedule / release / reset / reopen), holds
apply/release, and the mass-update actions on locations, order lines and
shipments.

**These are a different interaction shape from anything we have mined.** They
are not Add forms. They are *Actions-menu verbs applied to existing, filtered
records*. The record is selected, not created; the form is a modal over a
selection; and what the verb changes may not be on the screen that fired it.

**Volumes here are inferred from the shape of the task, not measured.** The
sandbox is QA data with test-prefixed records (`ZZTEST01`, `SPTEST1`,
`CSTEST`). Nothing in the knowledge base is production telemetry, and the
industry figures available publicly are consultancy and vendor material rather
than measurement. Treat "Adjustments Approve is high volume" as a hypothesis
worth checking with a real customer, not as a finding.

## 4. The catalogue of silent success

§5 of [`KNOWLEDGE-BASE.md`](../knowledge-base/KNOWLEDGE-BASE.md) is the most
valuable thing in the repository for this system's safety, and it is all
`[live]` — observed, not inferred. A sample, verbatim in substance:

- **`PUT /data/WM/wm/suppliers/{id}` returns 200 and ignores the write
  entirely.** The response body echoes the record back with the field still
  `null`. "No error, no field-level rejection, indistinguishable from success
  unless you check the actual value."
- **`null` in a PUT body does not clear a field.** It returns 200 and no-ops.
  To clear, send `""`. A revert that replays the original GET body — which
  naturally contains `null` — silently fails to revert.
- **`POST /wm/locations/massupdate` with an invalid field name** returns 200,
  async `COMPLETE`, `errorCode: null`, and changes nothing. The same signature
  as a business-rule refusal, two unrelated causes. That route's async takes
  **30–90 seconds** to settle, so polling briefly reads a slow success as a
  failure.
- **Remote search comboboxes silently ignore typed text.** Typing fills the box
  visually and leaves the model value `null`. "Clicking Save on this invalid
  state produces zero symptoms: no dialog, no mask, no network request at all."

The knowledge base's own rule, written before we hit any of this:

> **Never trust a `200` alone as proof a write worked — always diff the
> specific field in the response (or a separate read) against what you sent,
> not just the HTTP status.**

`unreturned()` (`f162ec28`) now does exactly that, and it was written without
having read this line. That is agreement, not derivation, which is worth
something.

### The one that defeats it

One quirk in that table is worse than the rest and defeats today's fix:

> **Description field: silent client-side truncation** — `Warehouse.Description`
> truncates at ~28 characters with **no error, no warning** — the truncated
> value is what's already in the outgoing request body.

The truncation happens **in the browser, before the request**. So what we
"supplied" *is* the truncated value, the record comes back matching it exactly,
and `unreturned()` reports nothing missing. Every belt agrees, and the record
is not what the mail asked for.

Catching this needs a comparison the system does not currently make: **what the
request asked for, against what went into the field** — before the write, not
after it. Nothing in the chain holds the original request text at that point.
This is the sharpest open safety gap we know of.

## 5. What is captured and unused

- `index/bundle-routes.json` — **70+ write routes mined out of the app's own
  minified JS**, tagged to their handler, "nearly all absent from
  `write-endpoints.json`". A ready-made discovery queue, not proof.
- `index/field-dictionary.json` and `index/filter-catalogue.json` — 253
  label → payload → query-column triples. This is precisely the
  three-vocabularies problem that a naive form-to-payload mapper gets wrong
  silently, already solved and unread.
- `index/declared-filter-columns.json` — 879 server-declared columns.
- `http/` — 296 exchange files with full request/response pairs.

For the **fields gap** in particular (§6 below), `field-dictionary.json` is a
better source for a job's field vocabulary than anything I proposed: it is the
app's own mapping, not an inference from one recorded body.

## 6. What this changes about the plan

I proposed, before this research: make dropped values loud, then make
truncation visible, then bind fields beyond the two parameters, then
composition. The first two are done (`f162ec28`) and stand — they are "stop a
wrong result looking like a right one", which is the failure mode that has cost
us most.

What I would change:

**Field-binding drops below the Actions-verb shape.** Binding a `Department`
value into a Customer Type create is worth doing, but it makes a low-volume
configuration job better. Handling "select records, apply a verb, verify
somewhere else" opens the screens where the repeated work actually is. It is
also a harder problem, and the §5 quirks say why: the verified state often
lives on a different record or a different endpoint than the one that fired.

**Before either, the client-side truncation gap.** It is the only known case
where every belt agrees and the record is still wrong, and it is cheap to close
relative to what it prevents.

**Composition stays last.** Unchanged, and the research supports it: RPA
products solve chained tasks by hand-wiring arguments between workflows and
none of them compensate a committed step automatically. There is no free answer
to import.

## 7. What is honest about this document

- The counts in §1 and the quotes in §2 and §4 I verified directly against the
  files. The `88 / 1` split, the nine operational forms, the fifteen recipes
  and the picking quote are counted or read, not reported.
- The volume claims in §3 are **inferred from task shape**. No production
  telemetry exists here.
- Blue Yonder's own field-level documentation is behind a customer portal.
  Anything about screens we have not captured is generalisation from ExtJS
  behaviour, and is marked as such where it appears.
- This was researched by a subagent and then checked. One of its claims — that
  nothing in the verification chain compares against the original request —
  was wrong in its reasoning (`mentions` does compare against supplied values)
  and right in its conclusion (it uses `any`, so a truncated field passes).
  The version in §4 is the corrected one.
