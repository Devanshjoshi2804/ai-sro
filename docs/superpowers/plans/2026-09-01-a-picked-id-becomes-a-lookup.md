# A picked id becomes a lookup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An id the operator picked off a screen becomes a dropdown they can answer, instead of a parameter that refuses the whole skill.

**Architecture:** Three rule changes inside induction. `lookups.plan` learns to plan for varying parameters as well as constants, to accept a column the demonstration's own filtered read named, and to look for that read in every doing rather than only the aligned pair. Nothing outside `application/induction/` changes: `Options`, `as_a_filter`, `ListChoices` and `Parameter.options` already carry this end to end.

**Tech Stack:** Python 3.14, pytest, ruff, mypy. No new dependency, no migration, no wire change.

**Spec:** `docs/superpowers/specs/2026-09-01-a-picked-id-becomes-a-lookup-design.md`

## Global Constraints

- **Evidence, never inference (ADR 004).** A column identifies a record only where the demonstration issued a read filtered on it. Uniqueness alone, and `_seen_on_screen` alone, are explicitly not enough.
- **Disagreement refuses.** Where two doings filtered the same field on different columns, plan no lookup.
- **Hexagonal boundaries.** Every change is in `backend/src/sro/application/induction/`. Do not touch `domain/`, `infrastructure/`, `interface/`, or any migration. import-linter enforces this and `make lint` runs it.
- **Existing behaviour is regression-protected.** The write-sent path in `_plan_one` keeps working exactly as it does today; its tests must pass unchanged.
- **Prove each new test by reverting the rule it defends** — this repo's habit. A test that passes with the rule removed is not a test.
- Run `cd backend && uv run pytest <path> -q` for a single file; `make lint` and `make types` before the final commit of each task.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `backend/src/sro/application/induction/lookups.py` | Turning a remembered id into a lookup | All three rules. `Wanted` added, `PlannedLookup.choice` → `.field`, `_plan_one` gains the filtered-column source, `_listing_of` gains the other doings |
| `backend/src/sro/application/induction/induce_skill.py` | Orchestrates induction | Call site builds `Wanted` from choices *and* parameters; `with_options` keys on `.field` and stops overriding evidence |
| `backend/tests/unit/application/test_a_picked_id_becomes_a_lookup.py` | New | Every rule in this plan |
| `backend/tests/unit/application/` (existing lookup tests) | Regression | Updated only where `PlannedLookup.choice` is named |

`sites.filter_terms_of` (`sites.py:178`) already returns every filter term a URL carries, each a dict with `column` and `value`. Reuse it — do not write a second filter parser.

---

## Task 1: A read the operator filtered

**Files:**
- Modify: `backend/src/sro/application/induction/lookups.py`
- Test: `backend/tests/unit/application/test_a_picked_id_becomes_a_lookup.py` (create)

**Interfaces:**
- Consumes: `sro.application.induction.sites.filter_terms_of(url) -> list[dict[str, str]]`
- Produces: `filtered_on(request: CapturedRequest) -> str | None` — the single column this read was filtered on, or `None`.

- [ ] **Step 1: Write the failing test**

```python
from sro.application.induction.lookups import filtered_on
from tests.unit.application.lookup_fixtures import a_read


def test_a_read_the_operator_filtered_names_its_column() -> None:
    read = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]'
    )

    assert filtered_on(read) == "addressName"


def test_an_unfiltered_page_names_nothing() -> None:
    assert filtered_on(a_read("https://wms.example/addresses?offset=0&limit=50")) is None


def test_a_read_filtered_on_two_columns_names_nothing() -> None:
    """Two columns is two answers about how the record was found, and the rule
    is that disagreement refuses."""
    read = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"},'
        '{"column":"city","operator":"EQ","value":"BURLINGTON"}]'
    )

    assert filtered_on(read) is None


def test_an_empty_filter_slot_names_nothing() -> None:
    """`_filter_terms` calls an empty list a filter -- it says the endpoint
    takes one. It does not say which column anybody searched."""
    assert filtered_on(a_read("https://wms.example/addresses?query=[]")) is None
```

- [ ] **Step 2: Write the fixture helper**

Create `backend/tests/unit/application/lookup_fixtures.py`:

```python
"""Frames and calls shaped like the carrier cross reference evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.recording.network import CapturedRequest


def a_read(url: str, records: list[dict[str, object]] | None = None) -> CapturedRequest:
    return CapturedRequest(
        request_id=url,
        method="GET",
        url=url,
        status=200,
        response_body_text=json.dumps({"data": records or []}),
    )


def a_write(url: str, body: dict[str, object]) -> CapturedRequest:
    return CapturedRequest(
        request_id=url,
        method="POST",
        url=url,
        status=201,
        request_body_text=json.dumps(body),
    )


def a_frame(*requests: CapturedRequest, kind: ActionKind = ActionKind.CLICK, value: str = "") -> ActionFrame:
    return ActionFrame(
        index=0,
        occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        action=InputAction(kind=kind, value=value),
        requests=tuple(requests),
    )
```

**Before writing this file, read `backend/src/sro/domain/recording/network.py` and `backend/src/sro/domain/recording/events.py` and match the real constructor signatures** — `CapturedRequest`, `ActionFrame` and `InputAction` have required fields this sketch may not name, and existing tests already build them. Grep for an existing builder first (`rg "CapturedRequest\(" backend/tests | head`) and reuse it if one exists rather than adding a second.

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd backend && uv run pytest tests/unit/application/test_a_picked_id_becomes_a_lookup.py -q`
Expected: FAIL with `ImportError: cannot import name 'filtered_on'`

- [ ] **Step 4: Implement**

In `lookups.py`, import `filter_terms_of` beside the existing `sites` imports and add:

```python
def filtered_on(request: CapturedRequest) -> str | None:
    """The column this read was filtered on, where exactly one was.

    The operator typed a name into a dialog and the application turned it into
    `query=[{"column":"addressName","operator":"EQ","value":"test"}]`. That URL
    is the only place in the evidence that says how a human finds this record
    in this system -- better than any field that merely happens to be unique,
    because a person was seen using it.

    ``None`` for two columns as well as none: two answers about how a record is
    found is not evidence, and the rule is that disagreement refuses.
    """
    columns = {term["column"] for term in filter_terms_of(request.url) if term.get("column")}
    return columns.pop() if len(columns) == 1 else None
```

- [ ] **Step 5: Run the tests**

Run: `cd backend && uv run pytest tests/unit/application/test_a_picked_id_becomes_a_lookup.py -q`
Expected: 4 passed

- [ ] **Step 6: Prove the rule**

Change `len(columns) == 1` to `len(columns) >= 1` and confirm `test_a_read_filtered_on_two_columns_names_nothing` fails. Revert.

- [ ] **Step 7: Commit**

```bash
git add backend/src/sro/application/induction/lookups.py backend/tests/unit/application/
git commit -m "feat(induction): the column an operator searched by, read off their own query"
```

---

## Task 2: The listing is looked for in every doing

**Files:**
- Modify: `backend/src/sro/application/induction/lookups.py`
- Test: `backend/tests/unit/application/test_a_picked_id_becomes_a_lookup.py`

**Interfaces:**
- Consumes: `filtered_on` from Task 1
- Produces: `_listing_of(runs: tuple[tuple[ActionFrame, ...], ...], value: str, step_index: int | None) -> tuple[CapturedRequest, list[dict]] | None`

The current signature is `_listing_of(run, choice)` and bounds the scan with `run[: choice.step_index]`. A doing outside the aligned pair has no such index, so the bound becomes that doing's own first mutating request — the same rule ("before the write") expressed without alignment.

- [ ] **Step 1: Write the failing test**

```python
def test_the_listing_is_found_in_a_doing_outside_the_pair() -> None:
    """The two doings that align hold one call each: the write. The doing that
    holds the address listing is the one alignment rejected."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    pair = (a_frame(write),)
    other = (a_frame(listing), a_frame(write))

    found = _listing_of((pair, other), value="A1", step_index=0)

    assert found is not None
    assert found[0].url == listing.url


def test_a_read_after_that_doing_s_own_write_is_not_the_listing() -> None:
    """The grid refreshing after a save shows the record that was just created.
    Reading the id back out of it proves nothing about how it was chosen."""
    after = a_read("https://wms.example/addresses", [{"addressId": "A1", "addressName": "test"}])
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    assert _listing_of(((a_frame(write), a_frame(after)),), value="A1", step_index=None) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/application/test_a_picked_id_becomes_a_lookup.py -q`
Expected: FAIL — `_listing_of` takes `(run, choice)`

- [ ] **Step 3: Implement**

Replace `_listing_of` with:

```python
def _listing_of(
    runs: tuple[tuple[ActionFrame, ...], ...], value: str, step_index: int | None
) -> tuple[CapturedRequest, list[dict[str, object]]] | None:
    """The read that showed this value, and the records it returned.

    Searched across every doing the candidate holds, not only the two that
    aligned. The pair that aligns is chosen for being the same task twice, and
    that is a different question from which doing happened to have the dialog
    open -- in the evidence this was written against, the two aligned doings
    hold one call each and the address listing is in neither.

    ``step_index`` bounds the search in the aligned runs, where a step index
    means something. In the other doings it does not, so the bound is that
    doing's own first mutating request: the same rule -- before the write --
    said without reference to an alignment those frames were never part of.
    """
    for at, run in enumerate(runs):
        upto = step_index if at < 2 and step_index is not None else _first_mutation(run)
        for frame in run[:upto]:
            for request in frame.requests:
                if request.is_mutation or is_background_traffic(request.url):
                    continue
                records = _records(request)
                if any(value in [str(v) for v in record.values()] for record in records):
                    return request, records
    return None


def _first_mutation(run: tuple[ActionFrame, ...]) -> int:
    for index, frame in enumerate(run):
        if any(request.is_mutation for request in frame.requests):
            return index
    return len(run)
```

`plan` gains the other doings and builds the tuple it searches:

```python
def plan(
    choices: tuple[Choice, ...],
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    taken: set[str],
    *,
    screens: tuple[ActionFrame, ...] = (),
    others: tuple[tuple[ActionFrame, ...], ...] = (),
    system: str = "",
    facility: str = "",
) -> tuple[PlannedLookup, ...]:
    runs = (run_a, run_b, *others)
```

`runs` is passed down to `_plan_one`, which replaces its
`_listing_of(run_a, choice) or _listing_of(run_b, choice)` with a single
`_listing_of(runs, choice.value, choice.step_index)`. The first two entries of
`runs` are the aligned pair, which is what `_listing_of`'s `at < 2` test means;
keep them first.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit/application/ -q -k "lookup or picked"`
Expected: PASS, including the existing lookup tests

- [ ] **Step 5: Prove the rule**

Delete the `_first_mutation` bound (scan the whole doing) and confirm `test_a_read_after_that_doing_s_own_write_is_not_the_listing` fails. Revert.

- [ ] **Step 6: Commit**

```bash
git add backend/src/sro/application/induction/lookups.py backend/tests/unit/application/
git commit -m "feat(induction): the doing that had the dialog open is not always the doing that aligned"
```

---

## Task 3: A filtered column identifies the record

**Files:**
- Modify: `backend/src/sro/application/induction/lookups.py`
- Test: `backend/tests/unit/application/test_a_picked_id_becomes_a_lookup.py`

**Interfaces:**
- Consumes: `filtered_on`, `_listing_of` from Tasks 1-2
- Produces: `_plan_one` accepting a record identified by a column the write never sends

- [ ] **Step 1: Write the failing test**

```python
def test_a_column_the_write_never_sends_can_still_identify_the_record() -> None:
    """The create sends `codAddressId` and nothing else off that record. Of the
    address's own fields the write sends none, so the write-sent rule can never
    be satisfied for a value that was picked rather than typed."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    planned = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=(a_frame(listing), a_frame(write)),
        run_b=(a_frame(listing), a_frame(write)),
        taken=set(),
    )

    assert len(planned) == 1
    assert planned[0].options.search == "addressName"
    assert planned[0].options.value == "addressId"


def test_a_picked_id_no_doing_ever_searched_for_stays_a_question() -> None:
    listing = a_read(
        "https://wms.example/addresses?offset=0&limit=50",
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    assert plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=(a_frame(listing), a_frame(write)),
        run_b=(a_frame(listing), a_frame(write)),
        taken=set(),
    ) == ()


def test_two_doings_that_searched_different_columns_plan_nothing() -> None:
    by_name = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "test", "city": "BURLINGTON"}],
    )
    by_city = a_read(
        'https://wms.example/addresses?query=[{"column":"city","operator":"EQ","value":"BUR"}]',
        [{"addressId": "A2", "addressName": "other", "city": "BURLINGTON"}],
    )
    write_a = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})
    write_b = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A2"})

    assert plan(
        (Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),),
        run_a=(a_frame(by_name), a_frame(write_a)),
        run_b=(a_frame(by_city), a_frame(write_b)),
        taken=set(),
    ) == ()


def test_a_filtered_column_absent_from_the_picked_record_plans_nothing() -> None:
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"nickname","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "test"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A1"})

    assert plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=(a_frame(listing), a_frame(write)),
        run_b=(a_frame(listing), a_frame(write)),
        taken=set(),
    ) == ()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/application/test_a_picked_id_becomes_a_lookup.py -q`
Expected: FAIL with `ImportError: cannot import name 'Wanted'`

- [ ] **Step 3: Introduce `Wanted`, and make `PlannedLookup` name a field**

`_plan_one` is about to be asked for values that are not choices, so it stops
taking one. Add to `lookups.py`:

```python
@dataclass(frozen=True, slots=True)
class Wanted:
    """A value the skill will ask for, and the step that sent it.

    A constant the operator chose twice and a value that differed between
    doings arrive here as the same thing, because they are the same thing: an
    id nobody memorised, picked off a screen the recording still holds. Whether
    the skill will vary it is a question about the parameter, not about where
    its value comes from.
    """

    field: str
    values: tuple[str, ...]
    """What was picked. One value for a constant; one per run for a value that
    varied, every one of which must be explainable or this is not one list."""

    step_index: int
```

`PlannedLookup.choice: Choice` becomes `field: str`, and `plan`'s first
argument becomes `wanted: tuple[Wanted, ...]`. In this task `_plan_one` still
uses only `wanted.values[0]`; Task 4 makes it read them all.

Update the two callers so the suite stays green: `with_options`
(`induce_skill.py:657`) keys on `found.field`, and the call site at `:234` maps
its choices across rather than passing them raw:

```python
            planned = lookups.plan(
                tuple(
                    lookups.Wanted(
                        field=choice.field, values=(choice.value,), step_index=choice.step_index
                    )
                    for choice in parameterisation.choices
                ),
                tuple(pair[0] for pair in pairs),
                tuple(pair[1] for pair in pairs),
                {parameter.name for parameter in parameterisation.parameters},
                screens=frames_a,
                others=tuple(history),
                system=objective.target_system,
                facility=objective.facility,
            )
```

`resolvable` becomes `{found.field for found in planned}`.

- [ ] **Step 4: Implement the filtered-column rule**

In `_plan_one`, keep the existing `usable` list exactly as it is and add the filtered source before the `if not usable` guard:

```python
    column = _searched_column(runs, value)
    if column is not None and str(picked.get(column, "")).strip() and column != take:
        # An operator's own search names the column. It goes first and it goes
        # in whether or not the write sends it: the write sends the id and
        # nothing else off this record, so requiring the write to send the
        # identifying field is requiring the impossible for every value that
        # was picked rather than typed.
        usable = [(column, str(picked[column]))] + [p for p in usable if p[0] != column]
```

and add:

```python
def _searched_column(
    runs: tuple[tuple[ActionFrame, ...], ...], value: str
) -> str | None:
    """The column the doings searched this record by, where they agree.

    Every doing that filtered at all is asked. A doing that scrolled instead is
    silent rather than dissenting -- it has no opinion about how the record is
    found, and silence is not disagreement. Two doings naming different columns
    is disagreement, and plans nothing.
    """
    named = {
        column
        for run in runs
        for frame in run
        for request in frame.requests
        if not request.is_mutation
        and any(value in [str(v) for v in record.values()] for record in _records(request))
        and (column := filtered_on(request)) is not None
    }
    return named.pop() if len(named) == 1 else None
```

`Options.search` then comes from `label[0]`, which the reordering above has made the searched column. `Options.url` is already the request `_listing_of` returned — the filtered read — so `as_a_filter` re-aims the operator's own query at run time.

- [ ] **Step 5: Uniqueness against the widest read**

A filtered read may return one row, where `_unique` is trivially true. Before the `usable` filter, pick the widest read of that collection across all doings:

```python
    widest = max(
        (
            _records(request)
            for run in runs
            for frame in run
            for request in frame.requests
            if not request.is_mutation and _same_collection(request.url, request_url)
        ),
        key=len,
        default=records,
    )
```

and judge `_unique` against `widest` rather than `records`. `_same_collection` compares `urlsplit(url).path`. Where no wider read exists the narrow result stands: the operator picks from the dropdown, so an ambiguous label costs a second look, not a wrong write.

- [ ] **Step 6: Run the tests**

Run: `cd backend && uv run pytest tests/unit/application/ -q`
Expected: all pass, including every existing lookup test unchanged

- [ ] **Step 7: Prove the rules**

Three reverts, one at a time, each confirming exactly one test fails:
1. Drop `column != take` → a lookup labelled by its own id.
2. Change `_searched_column`'s `len(named) == 1` to `>= 1` → the disagreement test fails.
3. Remove the `picked.get(column)` non-empty guard → `Options.__post_init__` refuses a blank label.

- [ ] **Step 8: Commit**

```bash
git add backend/src/sro/application/induction/ backend/tests/unit/application/
git commit -m "feat(induction): a column the operator searched by identifies the record the write only sends an id for"
```

---

## Task 4: A lookup for a value that varies

**Files:**
- Modify: `backend/src/sro/application/induction/lookups.py`, `backend/src/sro/application/induction/induce_skill.py`
- Test: `backend/tests/unit/application/test_a_picked_id_becomes_a_lookup.py`

**Interfaces:**
- Produces: `Wanted(field: str, values: tuple[str, ...], step_index: int)`; `PlannedLookup.field: str` replacing `PlannedLookup.choice: Choice`
- Consumes: `Parameterisation.parameters`, `Parameterisation.substitutions`, `Parameter.observed_values`

- [ ] **Step 1: Write the failing test**

```python
def test_a_value_that_varies_gets_the_dropdown_a_constant_would_have() -> None:
    """A picked id that differs between doings needs the list more than one that
    does not: the operator must supply a different address each time, and they
    cannot type an id."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "first"}, {"addressId": "A2", "addressName": "second"}],
    )
    planned = plan(
        (Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),),
        run_a=(a_frame(listing), a_frame(a_write("https://wms.example/x", {"codAddressId": "A1"}))),
        run_b=(a_frame(listing), a_frame(a_write("https://wms.example/x", {"codAddressId": "A2"}))),
        taken=set(),
    )

    assert [p.field for p in planned] == ["cod_address_id"]


def test_two_values_from_two_different_collections_are_not_one_lookup() -> None:
    addresses = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "first"}],
    )
    clients = a_read(
        'https://wms.example/clients?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A2", "addressName": "second"}],
    )

    assert plan(
        (Wanted(field="cod_address_id", values=("A1", "A2"), step_index=1),),
        run_a=(a_frame(addresses), a_frame(a_write("https://wms.example/x", {"codAddressId": "A1"}))),
        run_b=(a_frame(clients), a_frame(a_write("https://wms.example/x", {"codAddressId": "A2"}))),
        taken=set(),
    ) == ()


def test_attaching_a_dropdown_does_not_downgrade_what_two_runs_proved() -> None:
    """`Evidence` says how firmly we know this is a parameter; `options` says
    where its value comes from. They are different questions."""
    listing = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"t"}]',
        [{"addressId": "A1", "addressName": "first"}],
    )
    write = a_write("https://wms.example/x", {"codAddressId": "A1"})
    (found,) = plan(
        (Wanted(field="cod_address_id", values=("A1",), step_index=1),),
        run_a=(a_frame(listing), a_frame(write)),
        run_b=(a_frame(listing), a_frame(write)),
        taken=set(),
    )
    parameter = Parameter(name="cod_address_id", kind=ParameterKind.INPUT)  # Evidence.PROVEN

    assert with_options((parameter,), (found,))[0].evidence is Evidence.PROVEN
    assert with_options((parameter,), (found,))[0].options is not None
```

- [ ] **Step 2: Run to verify it fails**

Expected: FAIL — `PlannedLookup` has no `field`; `with_options` forces `PROPOSED`

- [ ] **Step 3: Every value must be explainable, from one collection**

`_plan_one` reads `wanted.values` in full instead of only the first. Each value
must resolve through `_listing_of` to a record in a read of the **same
collection** — `urlsplit(url).path` equal — and the first value's read supplies
`Options`. A parameter whose two runs' values came from two different
collections is not one list and gets no lookup:

```python
    reads = [_listing_of(runs, value, wanted.step_index) for value in wanted.values]
    if not all(reads) or len({urlsplit(read[0].url).path for read in reads if read}) != 1:
        return None
    request, records = reads[0]
```

- [ ] **Step 4: Implement the call site**

In `induce_skill.py`, replace the `lookups.plan(parameterisation.choices, ...)` call at `:234` with one that passes both. Build the parameter side from `substitutions`, which already records which step carries each name:

```python
            steps_of = {
                substitution.parameter: index
                for index, subs in parameterisation.substitutions.items()
                for substitution in subs
            }
            wanted = tuple(
                lookups.Wanted(field=choice.field, values=(choice.value,), step_index=choice.step_index)
                for choice in parameterisation.choices
            ) + tuple(
                lookups.Wanted(
                    field=parameter.name,
                    values=parameter.observed_values,
                    step_index=steps_of[parameter.name],
                )
                for parameter in parameterisation.parameters
                if parameter.kind is ParameterKind.INPUT
                and parameter.options is None
                and parameter.observed_values
                and parameter.name in steps_of
            )
```

Pass `others=tuple(history)` through to `plan` so Task 2's multi-doing search has them. `resolvable` becomes `{found.field for found in planned}` — it is used to keep a resolved choice out of `_settle_choices`, and a parameter was never in that set, so nothing else changes.

- [ ] **Step 5: Implement the evidence fix**

In `with_options`, key on `found.field` and **delete the `evidence=Evidence.PROPOSED,` line**. A choice that becomes a parameter is already created `PROPOSED` at `diff.py:876`; a parameter the diff produced is `PROVEN` because two demonstrations disagreed, and attaching a dropdown does not unprove that. Remove the now-unused `Evidence` import if nothing else in the module uses it.

- [ ] **Step 6: Run everything**

Run: `cd backend && uv run pytest tests/unit -q && make lint && make types`
Expected: all pass

- [ ] **Step 7: Prove the rules**

1. Restore `evidence=Evidence.PROPOSED` → the evidence test fails.
2. Drop the same-collection check → `test_two_values_from_two_different_collections_are_not_one_lookup` fails.

- [ ] **Step 8: Commit**

```bash
git add backend/src/sro/application/induction/
git commit -m "feat(induction): a picked id that varies gets the list a constant one already got"
```

---

## Task 5: The carrier cross reference candidate induces

**Files:**
- Test: `backend/tests/unit/application/test_a_picked_id_becomes_a_lookup.py`

This is the end-to-end assertion that the three rules compose, written against the shape of the real evidence: four doings, two of which align and hold only the write, one of which holds the filtered address read.

- [ ] **Step 1: Write the test**

```python
def test_the_shape_that_refused_a_whole_skill_now_induces_one() -> None:
    """Four doings of a carrier cross reference. The two that align hold one
    call each; the address listing is in a third. Before these rules the skill
    was refused whole -- `_refuse_an_unfillable_input` -- because the operator
    would have been asked to recite `A000278094`."""
    searched = a_read(
        'https://wms.example/addresses?query=[{"column":"addressName","operator":"EQ","value":"test"}]',
        [{"addressId": "A000278094", "addressName": "0 C TANNER", "city": "BURLINGTON"}],
    )
    write = a_write("https://wms.example/carrierCrossReferences", {"codAddressId": "A000278094"})

    planned = plan(
        (Wanted(field="cod_address_id", values=("A000278094",), step_index=0),),
        run_a=(a_frame(write),),
        run_b=(a_frame(write),),
        taken=set(),
        others=((a_frame(searched), a_frame(write)),),
    )

    assert len(planned) == 1
    assert planned[0].options.search == "addressName"
    assert planned[0].options.value == "addressId"
    assert "addresses" in planned[0].options.url
```

- [ ] **Step 2: Run**

Run: `cd backend && uv run pytest tests/unit/application/test_a_picked_id_becomes_a_lookup.py -q`
Expected: PASS

- [ ] **Step 3: Full gate**

Run: `make lint && make types && make test && make test-integration && make test-contract`
Expected: all green. `make test-contract` proves no wire change leaked out.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/application/
git commit -m "test(induction): the carrier cross reference shape induces instead of refusing"
```

---

## Verification against the real evidence

Not a task — a check to run by hand after Task 5, because it is the only thing that proves this works on the data it was designed against, and it needs the live database.

The carrier candidate (`cnd_…1d167d172798a8`) is `new` with four doings recorded on 2026-08-31. Re-run the teach it currently refuses:

```bash
cd backend && uv run python - <<'PY'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sro.config import get_settings
from sro.container import build_container
from sro.application.context import RequestContext
from sro.domain.shared.identifiers import CandidateId, TenantId, PrincipalId

async def main():
    settings = get_settings()
    e = create_async_engine(settings.database_url)
    async with e.connect() as c:
        cand, tenant, principal = (await c.execute(text(
            "select id, tenant_id, principal_id from task_candidates "
            "where id like '%1d167d172798a8'"))).one()
    ctx = RequestContext(tenant_id=TenantId(tenant), principal_id=PrincipalId(principal))
    taught = await build_container(settings).teach_candidate().execute(ctx, candidate_id=CandidateId(cand))
    print("skill:", taught.skill_id, "needs demo:", taught.needs_demonstration, taught.because)
asyncio.run(main())
PY
```

Expected: a skill id, `needs_demonstration: False`, and its `cod_address_id` parameter carrying `Options(search="addressName", value="addressId")`. Do not run this against the live database until the whole plan is green — it writes a skill and marks the candidate taught. The candidate must be `new` when it runs; it is now.

If it refuses, read `because` before changing any rule: "no doing ever searched" means the strict evidence rule is doing its job on evidence that does not support a lookup, which is a finding about the recordings, not a defect in this plan.
