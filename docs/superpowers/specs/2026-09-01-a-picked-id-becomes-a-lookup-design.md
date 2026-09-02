# An id the operator picked becomes a lookup they can answer

## Context

An operator creating a carrier cross reference fills in a COD address. They do
not type it: they open a dialog, search, and click a row. What the form then
sends is `codAddressId: A000278094` -- an internal id nobody has memorised.

Induction turns that into a parameter and then refuses the whole skill:

> this skill would ask for something no step of it can actually type or choose
> on the screen. Demonstrate that value being entered directly, not just picked
> another way, so there is a step that can fill it in

(`induce_skill.py:564`, `_refuse_an_unfillable_input`.) The refusal is right --
a skill that asks a human to recite `A000278094` is a skill nobody can run --
but the value it is refusing over is one the demonstration can explain.

**Nothing in this design is new machinery.** All of it exists:

- `Options` (`domain/skill/lookup.py`) already models the listing call, the
  fields to show, the field the write needs, and the column the endpoint
  filters on. Its `url` already documents `${query}` "where the operator's own
  search terms went".
- `as_a_filter` (`induction/sites.py:112`) already keeps a demonstrated filter's
  own dialect and replaces its terms -- including this WMS's
  `query=[{"column":…,"operator":…,"value":…}]`.
- `ListChoices` (`execution/choices.py`) already serves the dropdown live,
  resolving headers and searching through `_searched` (`:115`).
- `Parameter.options` (`domain/skill/parameter.py:104`) already exists, and
  `ListChoices` resolves it by parameter name without caring whether the
  parameter varies.

So there is no domain change, no wire change, no migration, and no runtime
change. Every change in this document is in induction.

### Why it never fires, proven against the four real doings

The candidate is four doings of "create a carrier cross reference" recorded on
2026-08-31. Measured against them:

**A. Lookups are planned only for constants.** The call site passes
`parameterisation.choices` (`induce_skill.py:234`) -- values *both*
demonstrations chose. `Choice`'s own docstring says as much: "A value both
demonstrations chose". `cod_address_id` differs between doings, so it is a
`Parameter`, not a `Choice`, and is never offered to `lookups.plan`. The pair
that actually aligns (`e1c44a9004` + `d9cfc4ee31`) yields
`cod_address_id ('input', optional=True)` and `choices: none`.

**B. The identifying field must also be sent by the write.** `_plan_one`
requires `sent.get(key) == str(value)` (`lookups.py:106`). The write sends
`codAddressId` and nothing else off that record. Of the 21 non-empty fields on
the address the operator picked -- `addressName`, `addressLine1`, `city`,
`postalCode`, `phoneNumber` and the rest -- `sent-by-write` is false for every
one. For a picker-chosen id this condition can never be met.

**C. Only the two aligned runs are searched for the listing.** `_listing_of`
scans `run_a` then `run_b` (`lookups.py:161`). The aligned pair holds one call
each: the POST. The two doings that *do* contain the address listing are the
ones alignment rejects. The evidence is in the candidate and invisible to the
planner.

### What the evidence actually contains

Richer than the current rule assumes. One doing (`c9693604d4`) shows, in order:
click "COD Address"; type `test`; click "in Address Name"; and the application
issuing

```
GET /data/WM/wm/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]
```

then a click on "Select". That single read names the column a human searches
by, the value they typed, and the call that resolves one to the other -- which
is exactly `Options(url, search, value, label)`.

## Decisions taken before design

Both are the owner's, chosen against the alternatives:

- **Only an operator-caused filter proves a column identifies a record.** Not
  uniqueness: 11 of the 21 fields on that address are unique to it, so
  uniqueness alone would let `hostExternalId` become the thing an operator
  searches by. Not "seen on screen" either. A column counts only where the
  demonstration issued a read filtered on it. Where nobody searched, the id
  stays a question -- ADR 004: evidence, never inference.
- **Every doing is searched, and disagreement refuses.** Where two doings
  filtered the same field on different columns, no lookup is planned. Two
  answers about how a record is found is not evidence.

## Design

### 1. A lookup may be planned for a parameter, not only a choice

`lookups.plan` gains the varying values alongside the constants. A `Choice`
carries `step_index`, `value`, `field` and `seen_at`; a `Parameter` carries no
step index, so the planner cannot use it directly. So the call site passes, for
each input parameter, the value it took **in each run** together with the step
that sent it -- the same `(step_index, value, field)` triple a choice already
provides, built from `parameterisation.substitutions`, which already records
which site of which step carries the parameter.

`PlannedLookup.choice` becomes `PlannedLookup.field` plus the value used, so the
type stops being choice-shaped. `with_options` (`induce_skill.py:657`) already
keys on `found.choice.field`; it keys on `found.field` instead and already
writes to `Parameter.options`.

**Evidence is not downgraded.** `with_options` sets
`evidence=Evidence.PROPOSED` unconditionally today, which is right for a
constant being turned into a question: nothing yet says it varies. A parameter
the diff produced is `Evidence.PROVEN` -- the default -- because two
demonstrations disagreed about it, and that is a fact attaching a dropdown does
not disturb. Options say where a value comes from; evidence says how firmly we
know it is a parameter at all, and they are different questions. So a
parameter keeps the evidence it had, and only a choice becomes `PROPOSED`.

**Two runs, two values.** For a varying parameter each run picked a different
record. The listing is looked for using run A's value; run B's value is then
required to be findable in a read of the same endpoint. A parameter whose two
values came from two different collections is not one lookup and gets none.

### 2. A column the demonstration filtered on identifies the record

`_plan_one`'s `usable` rule gains a second, separate source, and the existing
write-sent rule stays exactly as it is for the case it already serves.

A **filtered read** is a non-mutating request whose URL carries a filter term
naming a column and a value, as `_filter_terms` (`sites.py:185`) already parses --
the same parser `as_a_filter` uses, so the two cannot drift about what a filter
is. It qualifies when:

- the read returned the record the operator picked, and
- the filter's column is a field of that record, non-empty, and
- across all doings that filtered for this field, every one named the same
  column.

The column then becomes `Options.search`, and `Options.url` is that filtered
read -- so `as_a_filter` re-aims the operator's own query at run time rather
than anything composed here.

**Uniqueness.** `_unique` currently guards against a label that matches several
records. A filtered read may return exactly one row, where uniqueness is
trivially true and means nothing. So uniqueness is checked against the widest
read of that collection the doings contain -- the unfiltered paged listing where
there is one -- and where there is no wider read, the check is skipped and the
narrow result is accepted: the operator picks from the dropdown, so an ambiguous
label costs a second look, not a wrong write.

**Label.** Identification is `search`; the label is what the dropdown shows. It
stays `MOST_FIELDS` fields as today, with the filtered column first, because a
dropdown whose first column is not the one being searched reads as a mistake.

### 3. Every doing is searched for the listing

`lookups.plan` gains the other doings' frames beside `run_a`/`run_b`. The call
site already holds them: `history` is passed to `parameterise(..., others=)`
(`induce_skill.py:227`, `diff.py:705`), built by `TeachCandidate` from up to
`MOST_DOINGS` (10) episodes (`teach.py:61`).

`_listing_of` searches run A, then run B, then the other doings in the order the
candidate holds them. In a doing that is not the aligned pair there is no
`choice.step_index` to bound the search, so the bound becomes the first
mutating request in that doing -- the same rule the pair uses ("before the
write"), expressed against a run alignment never touched.

## What this must refuse

- A picked id no doing ever filtered for. It stays a question, and
  `_refuse_an_unfillable_input` refuses the skill exactly as it does today.
- Two doings that filtered the same field on different columns.
- A parameter whose two runs' values came from different collections.
- A filtered read whose results do not contain the record the operator picked.
- A column whose value on the picked record is empty -- a dropdown labelled by
  a blank field is a list of blank rows, which `Options.__post_init__` already
  refuses and this must not reach.

## Verification

Every new test proved by reverting the rule it defends, per this repo's habit.

- **Unit, gap A**: a varying input parameter whose value each run picked from a
  listing gets `options`; the same parameter with no filtered read gets none and
  the induction still refuses.
- **Unit, gap B**: a record identified by a filtered column the write never
  sends is planned; uniqueness is judged against the widest read; a filter whose
  column is absent from the picked record is refused.
- **Unit, disagreement**: two doings filtering one field on different columns
  plan nothing.
- **Unit, gap C**: the listing is found in a doing outside the aligned pair, and
  the search stops at that doing's first mutation.
- **Regression**: the existing write-sent path still plans the lookups it
  planned before -- these tests exist and must not change.
- **Against the real evidence**: the carrier cross reference candidate induces a
  skill whose `cod_address_id` carries `Options(search="addressName")`, and
  `make test`, `make test-integration`, `make test-contract`.

## Out of scope

- **The refusal itself** (`_refuse_an_unfillable_input`) is unchanged. Where no
  lookup can be planned the skill is still refused whole. Whether that should
  instead ship a skill that asks a human is a separate decision about what an
  operator is handed, not about what the evidence proves.
- **`_seen_on_screen`** stays as the tie-breaker it already is for ordering
  usable fields. It is deliberately not promoted to evidence of identification.
- Re-inducing skills already built. The carrier skill was deleted on
  2026-09-01 and its candidate returned to `new`; it will induce through the
  normal offer once this ships.
