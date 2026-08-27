# A Field Nobody Filled — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two doings of one task that filled different subsets of a form induce
into one skill, whose optional fields are skipped on both the network and the
gesture path when nobody supplies them.

**Architecture:** A form's write is the contract. Where two runs' writes carry
the same keys and one leaves a key empty, that key is an optional parameter and
its absent form is what the emptier run sent. A keystroke is bound to the key it
filled by comparing the typed text with the values in that run's own body, after
normalisation. A step that fills an optional key becomes conditional: performed
when a value is supplied, skipped when not, with the network path sending the
absent form instead.

**Tech Stack:** Python 3.14, pytest (async, no fixtures beyond the repo's fakes),
`uv` for everything, hexagonal layering enforced by import-linter.

**Spec:** `docs/superpowers/specs/2026-08-27-fields-nobody-filled-design.md`

## Global Constraints

- Parts 1 and 2 of the spec only. Parts 3–6 (questions, pre-flight, the offer,
  per-trigger permission) are separate plans and nothing here may depend on them.
- **No model decides identity.** Every rule added here reads stored evidence.
  ADR 004.
- **No migration.** `SkillStep` and `Parameter` are document fields on the
  version, stored as JSONB through a pydantic `TypeAdapter`
  (`src/sro/infrastructure/db/codec.py`). New fields need defaults, because rows
  written before this have no such key.
- **Layering:** domain imports nothing from the codebase; application imports
  domain and ports only; infrastructure is reachable only through
  `src/sro/container.py`. `uv run lint-imports` enforces it.
- **Every new test is proved by reverting the rule it defends** before the task
  is done: break the rule, watch that test fail, restore, watch it pass.
- Commands run from `backend/`. Lint gate for every commit:
  `uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports`
- Comments explain *why*, in the voice of the surrounding code. No comment
  restates what the line does.

---

### Task 1: A null is an absence, not a different shape

`jsonutil.structure` maps a scalar to `("scalar", type(value).__name__)`, so
`{"deltaPriority": 1}` and `{"deltaPriority": null}` are different shapes and
`_diff_request` raises "the two runs sent differently-shaped request bodies;
the flows diverged" before anything else in this plan can run.

**Files:**
- Modify: `src/sro/application/induction/jsonutil.py` (add `same_shape`)
- Modify: `src/sro/application/induction/diff.py:973-978` (use it)
- Test: `tests/unit/application/test_a_field_nobody_filled.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `jsonutil.same_shape(a: JsonValue, b: JsonValue) -> bool` and
  `jsonutil.is_empty(value: object) -> bool`. Later tasks use `is_empty`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/application/test_a_field_nobody_filled.py`:

```python
"""A form has thirty fields and no two people fill the same subset.

Two work areas created in Blue Yonder on 2026-08-27, watched passively, are the
evidence behind every rule in this file: same endpoint, same keys, and one of
them leaves Delta Priority empty. Before this, that was "the flows diverged".
"""

from __future__ import annotations

from sro.application.induction import jsonutil


def test_an_empty_value_is_not_a_different_shape() -> None:
    filled = {"workArea": "TWOTEST", "deltaPriority": 1, "distanceThreshold": ""}
    skipped = {"workArea": "THREE TE", "deltaPriority": None, "distanceThreshold": ""}

    assert jsonutil.same_shape(filled, skipped) is True


def test_a_key_one_run_does_not_send_is_still_a_different_shape() -> None:
    """The rule this relaxes exists for a reason. A key present in one body and
    absent from the other is two different requests, not one optional field."""
    with_key = {"workArea": "TWOTEST", "deltaPriority": 1}
    without_key = {"workArea": "THREE TE"}

    assert jsonutil.same_shape(with_key, without_key) is False


def test_two_kinds_of_filled_value_still_disagree() -> None:
    """Relaxing null against anything is the whole change. A number against a
    string is a flow that diverged, and stays one."""
    assert jsonutil.same_shape({"qty": 5}, {"qty": "five"}) is False
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/unit/application/test_a_field_nobody_filled.py -q`
Expected: FAIL, `AttributeError: module 'sro.application.induction.jsonutil' has no attribute 'same_shape'`

- [ ] **Step 3: Implement**

Append to `src/sro/application/induction/jsonutil.py`:

```python
def is_empty(value: object) -> bool:
    """Whether this leaf is a field somebody left alone.

    A form sends its whole record: what the operator skipped arrives as `null`,
    or as `""` from a text control that was never focused. Both are absence
    wearing the type the application chose for it.
    """
    return value is None or value == ""


def same_shape(a: JsonValue, b: JsonValue) -> bool:
    """Whether two bodies are the same request with different values in it.

    Stricter than it looks. Every key must be in both -- a key one run did not
    send is a different request, which is what `structure` was written to
    catch. What is allowed is a leaf that is empty on one side: the same field,
    filled once and skipped once, which is the ordinary way two people fill one
    form.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_shape(a[key], b[key]) for key in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_shape(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict | list) or isinstance(b, dict | list):
        return False
    return is_empty(a) or is_empty(b) or type(a) is type(b)
```

- [ ] **Step 4: Use it where the shape is judged**

In `src/sro/application/induction/diff.py`, replace:

```python
    if jsonutil.structure(document_a) != jsonutil.structure(document_b):
```

with:

```python
    if not jsonutil.same_shape(document_a, document_b):
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/application/test_a_field_nobody_filled.py tests/unit -q`
Expected: PASS, and the whole unit suite still passes.

- [ ] **Step 6: Prove the new tests**

Temporarily change `same_shape`'s last line to `return type(a) is type(b)`, run
the file, watch `test_an_empty_value_is_not_a_different_shape` fail, then
restore. Then change it to `return True`, watch
`test_two_kinds_of_filled_value_still_disagree` fail, and restore.

- [ ] **Step 7: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add src/sro/application/induction/jsonutil.py src/sro/application/induction/diff.py tests/unit/application/test_a_field_nobody_filled.py
git commit -m "fix(induction): a null is a field left alone, not a different request"
```

---

### Task 2: The emptier run says what absent looks like

With Task 1 the two bodies diff, and `deltaPriority` becomes a `Difference` with
`value_a="1"` and `value_b="None"` — a parameter whose second observed value is
the string `None`, which is nonsense to show an operator and worse to send. The
difference has to carry that one side was empty, and what empty looked like.

**Files:**
- Modify: `src/sro/application/induction/diff.py:42-48` (`Difference`)
- Modify: `src/sro/application/induction/diff.py:980-989` (`_diff_request` leaves)
- Modify: `src/sro/domain/skill/parameter.py:43` (`Parameter`)
- Modify: `src/sro/application/induction/diff.py:761-790` (`_build_parameter`)
- Test: `tests/unit/application/test_a_field_nobody_filled.py`

**Interfaces:**
- Consumes: `jsonutil.is_empty` from Task 1.
- Produces: `Difference.absent_as: str | None = None`;
  `Parameter.optional: bool = False`; `Parameter.absent_as: str | None = None`.
  Task 5 reads both `Parameter` fields; Task 4 reads `Difference.absent_as`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/application/test_a_field_nobody_filled.py`:

```python
from sro.application.induction.diff import Difference, parameters_for
from sro.application.induction.sites import JsonBodySite
```

(Import at the top of the file with the others; shown here for locality.)

```python
def test_a_field_filled_once_is_optional_and_remembers_what_empty_looked_like() -> None:
    """`null` and `""` are both absence, and which one this field uses is the
    application's business -- so it is read from the run that skipped it rather
    than chosen here."""
    difference = Difference(
        step_index=0,
        site=JsonBodySite("/deltaPriority"),
        value_a="1",
        value_b="",
        absent_as="null",
    )

    parameter = parameters_for([difference])[0]

    assert parameter.optional is True
    assert parameter.absent_as == "null"
    assert parameter.observed_values == ("1",), "an absence is not a value somebody observed"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/unit/application/test_a_field_nobody_filled.py -q -k optional`
Expected: FAIL — `Difference` has no `absent_as`, and `parameters_for` does not exist.

- [ ] **Step 3: Add the fields**

In `src/sro/application/induction/diff.py`, `Difference` gains:

```python
    absent_as: str | None = None
    """What this field looked like in the run that left it alone -- `"null"`,
    or `""` from a text control nobody focused. Present only when exactly one
    of the two runs filled it, which is what makes the field optional."""
```

In `src/sro/domain/skill/parameter.py`, `Parameter` gains:

```python
    optional: bool = False
    """Whether a run may leave this out.

    Proved, not assumed: one demonstration filled this field and the other left
    it alone, and both created the record. A field filled in every
    demonstration there is stays required, because nothing has shown the task
    works without it."""

    absent_as: str | None = None
    """What to send when nobody supplies it, exactly as the demonstration that
    skipped it sent -- `"null"` for a number the form nulls, `""` for a text
    control it empties. Never chosen here: a form that wants one and gets the
    other rejects the write."""
```

- [ ] **Step 4: Extract the parameter builder and make it read the new field**

In `diff.py`, `_build_parameter` currently builds an INPUT parameter from a
difference group. Add a module-level entry point beside it, used by the test and
by the existing caller:

```python
def parameters_for(sites: list[Difference]) -> list[Parameter]:
    """One parameter per group of sites carrying the same value.

    Public because the optional rule is worth testing on its own: a field
    filled once and skipped once is the ordinary shape of a real form, and it
    reaches here as a group of one.
    """
    absent = next((site.absent_as for site in sites if site.absent_as is not None), None)
    filled = next(site.value_a if site.value_b == "" else site.value_b for site in sites)
    if absent is None:
        raise ValueError("parameters_for is for optional sites; use _build_parameter otherwise")
    return [
        Parameter(
            name=suggest_name(sites[0].site, url=sites[0].url, field_label=sites[0].field_label),
            kind=ParameterKind.INPUT,
            description=(
                f"filled in one demonstration and left alone in the other, so it may be "
                f"left out; sent as {absent} when nobody supplies it"
            ),
            observed_values=(filled,),
            optional=True,
            absent_as=absent,
        )
    ]
```

- [ ] **Step 5: Emit `absent_as` where bodies are compared**

In `diff.py`'s `_diff_request`, the leaf comparison becomes:

```python
    leaves_b = dict(jsonutil.leaves(document_b))
    differences: list[Difference] = []
    for pointer, leaf_a in jsonutil.leaves(document_a):
        leaf_b = leaves_b[pointer]
        if str(leaf_a) == str(leaf_b):
            continue
        empty_a, empty_b = jsonutil.is_empty(leaf_a), jsonutil.is_empty(leaf_b)
        differences.append(
            Difference(
                step_index=index,
                site=JsonBodySite(pointer),
                # An absence is not a value, so it is not offered as one: the
                # side that filled the field is what an operator is shown.
                value_a="" if empty_a else str(leaf_a),
                value_b="" if empty_b else str(leaf_b),
                absent_as=_absent_form(leaf_a if empty_a else leaf_b)
                if empty_a != empty_b
                else None,
            )
        )
    return differences


def _absent_form(leaf: object) -> str:
    """The empty exactly as it was sent. `json.dumps` rather than `str`,
    because a form that nulls a number wants `null` and not `None`."""
    return json.dumps(leaf)
```

`json` is already imported in `diff.py`; check before adding.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/unit -q`
Expected: PASS. If an existing test asserts `observed_values` containing
`"None"`, that test encoded the old behaviour — read it, and if it is about
optional fields, rewrite it around the case that actually differs.

- [ ] **Step 7: Prove the new test**

Remove `optional=True` from `parameters_for`, watch the test fail, restore.

- [ ] **Step 8: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add -A src tests
git commit -m "feat(induction): a field filled once and skipped once is optional"
```

---

### Task 3: Bind a keystroke to the field it filled

For a step to be conditional, the system has to know which key that step fills.
The evidence says so directly: `type 'twoTEST'` appears in that run's own write
as `workArea: "TWOTEST"`.

**Files:**
- Create: `src/sro/application/induction/binding.py`
- Test: `tests/unit/application/test_a_field_nobody_filled.py`

**Interfaces:**
- Consumes: `jsonutil.leaves`.
- Produces: `binding.key_filled_by(frame: ActionFrame, within: ActionFrame) -> str | None`
  — the JSON pointer in `within`'s write that `frame`'s typed value filled, or
  `None`. Task 4 calls it.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/application/test_a_field_nobody_filled.py`:

```python
def test_a_typed_value_is_bound_to_the_field_it_filled() -> None:
    typing = f.action_frame(index=0, action=f.input_action(kind=ActionKind.TYPE, value="twoTEST"))
    saving = f.action_frame(
        index=1,
        requests=(f.captured_request(method="POST", body='{"workArea": "TWOTEST"}'),),
    )

    assert binding.key_filled_by(typing, saving) == "/workArea"


def test_a_form_is_allowed_to_tidy_what_it_was_given() -> None:
    """The work area name field uppercases as you type. Exact comparison would
    fail to bind the one field the whole task is named for."""
    typing = f.action_frame(index=0, action=f.input_action(kind=ActionKind.TYPE, value=" 1 "))
    saving = f.action_frame(
        index=1, requests=(f.captured_request(method="POST", body='{"voiceCode": 1}'),)
    )

    assert binding.key_filled_by(typing, saving) == "/voiceCode"


def test_a_value_that_could_be_two_fields_is_bound_to_neither() -> None:
    """Two keys holding "1" cannot say which one the keystroke filled, and a
    step made conditional on the wrong field is a step that silently stops
    happening."""
    typing = f.action_frame(index=0, action=f.input_action(kind=ActionKind.TYPE, value="1"))
    saving = f.action_frame(
        index=1,
        requests=(f.captured_request(method="POST", body='{"voiceCode": 1, "priority": 1}'),),
    )

    assert binding.key_filled_by(typing, saving) is None


def test_a_click_fills_nothing() -> None:
    clicking = f.action_frame(index=0, action=f.input_action(kind=ActionKind.CLICK, value=None))
    saving = f.action_frame(
        index=1, requests=(f.captured_request(method="POST", body='{"workArea": "X"}'),)
    )

    assert binding.key_filled_by(clicking, saving) is None
```

Add to the imports at the top of the file:

```python
from sro.application.induction import binding
from sro.domain.recording.events import ActionKind
from tests import factories as f
```

Check `tests/factories.py` for the exact names of the frame, action and request
factories before writing these; use whatever it already provides rather than
adding new ones. If a factory for `CapturedRequest` with a body does not exist,
add one there in the repo's existing style.

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/unit/application/test_a_field_nobody_filled.py -q -k bound or tidy or neither or click`
Expected: FAIL, `ModuleNotFoundError: sro.application.induction.binding`

- [ ] **Step 3: Implement**

Create `src/sro/application/induction/binding.py`:

```python
"""Which field a keystroke filled.

A step can only be made conditional on a parameter if something proves the step
produces that parameter. The proof is already stored: what the operator typed
turns up in the write their next few gestures sent, under one key.

Normalised, because a form is allowed to tidy what it was given -- the work
area name uppercases as you type, a code field trims, a number field sends 1
for what was typed as "1". Nothing looser than that: a value that merely
contains another is not a match, and a value that fits two keys fits neither.
"""

from __future__ import annotations

import json

from sro.application.induction import jsonutil
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame


def key_filled_by(frame: ActionFrame, within: ActionFrame) -> str | None:
    """The pointer in `within`'s write that `frame`'s typed value filled."""
    typed = frame.action.value
    if not typed or frame.action.secret:
        return None

    write = next(
        (
            request
            for request in within.requests
            if request.is_mutation and not is_background_traffic(request.url)
        ),
        None,
    )
    body = write.request_body.text if write and write.request_body else None
    if not body:
        return None

    document = jsonutil.parse(body) if hasattr(jsonutil, "parse") else json.loads(body)
    if not isinstance(document, dict):
        return None

    wanted = _tidied(typed)
    found = [
        pointer for pointer, leaf in jsonutil.leaves(document) if _tidied(str(leaf)) == wanted
    ]
    return found[0] if len(found) == 1 else None


def _tidied(value: str) -> str:
    return value.strip().casefold()
```

Use whatever JSON-parsing helper `diff.py` already uses (`parse_json`) rather
than the `hasattr` line above — read `diff.py`'s imports and follow them.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/application/test_a_field_nobody_filled.py -q`
Expected: PASS.

- [ ] **Step 5: Prove them**

Change `_tidied` to `return value`, watch the tidying test fail, restore. Change
`len(found) == 1` to `len(found) >= 1`, watch the two-fields test fail, restore.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add src/sro/application/induction/binding.py tests
git commit -m "feat(induction): what a keystroke filled, proved by the write it produced"
```

---

### Task 4: An unmatched step whose field the other run left empty

`align` refuses when one run has an evidential step the other does not
(`diff.py:262-271`), and a `type` carrying a value is evidential
(`_evidential`, `:225`). That is what refused the two work areas.

**Files:**
- Modify: `src/sro/application/induction/diff.py:243-274` (`align`)
- Test: `tests/unit/application/test_a_field_nobody_filled.py`

**Interfaces:**
- Consumes: `binding.key_filled_by` (Task 3), `jsonutil.is_empty` (Task 1).
- Produces: `align` returns pairs as before; unmatched-but-optional frames are
  dropped rather than refused. Task 5 needs to know which parameter the dropped
  step filled — `align` gains a second return value:
  `align(run_a, run_b) -> tuple[Aligned, ...]` where
  `Aligned = tuple[ActionFrame, ActionFrame]` unchanged, plus a module-level
  `optional_keys(run_a, run_b) -> dict[str, str]` mapping pointer to absent
  form, computed by the same walk. Keep `align`'s signature; add the second
  function so nothing existing changes shape.

- [ ] **Step 1: Write the failing test**

Append to the test file:

```python
def test_a_step_the_other_run_skipped_does_not_refuse_the_pair() -> None:
    """The two work areas. One run typed a Delta Priority and the other did
    not, and both created a work area."""
    filled = (
        f.action_frame(index=0, action=f.input_action(kind=ActionKind.TYPE, value="ONE")),
        f.action_frame(index=1, action=f.input_action(kind=ActionKind.TYPE, value="1")),
        f.action_frame(
            index=2,
            requests=(
                f.captured_request(
                    method="POST", body='{"workArea": "ONE", "deltaPriority": 1}'
                ),
            ),
        ),
    )
    skipped = (
        f.action_frame(index=0, action=f.input_action(kind=ActionKind.TYPE, value="TWO")),
        f.action_frame(
            index=1,
            requests=(
                f.captured_request(
                    method="POST", body='{"workArea": "TWO", "deltaPriority": null}'
                ),
            ),
        ),
    )

    paired = align(filled, skipped)

    assert len(paired) == 2, "the pair was refused, or the skipped step was kept"


def test_a_step_that_filled_something_the_other_run_did_not_send_still_refuses() -> None:
    """A key in one body and not the other is two different requests. The
    relaxation is for a field both runs carry and one leaves alone."""
    filled = (
        f.action_frame(index=0, action=f.input_action(kind=ActionKind.TYPE, value="ONE")),
        f.action_frame(index=1, action=f.input_action(kind=ActionKind.TYPE, value="9")),
        f.action_frame(
            index=2,
            requests=(f.captured_request(method="POST", body='{"workArea": "ONE", "zone": 9}'),),
        ),
    )
    without = (
        f.action_frame(index=0, action=f.input_action(kind=ActionKind.TYPE, value="TWO")),
        f.action_frame(
            index=1, requests=(f.captured_request(method="POST", body='{"workArea": "TWO"}'),)
        ),
    )

    with pytest.raises(InductionFailed, match="not two runs of one task"):
        align(filled, without)
```

Add `import pytest`, `from sro.application.induction.diff import align` and
`from sro.application.induction.errors import InductionFailed` to the imports.

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/unit/application/test_a_field_nobody_filled.py -q -k refuse`
Expected: the first test FAILS with "the second run did something the other did
not"; the second already passes.

- [ ] **Step 3: Implement**

In `align`, the orphan check becomes:

```python
    paired = _longest_common(run_a, run_b)
    matched = {id(frame) for pair in paired for frame in pair}
    for run, other, label in ((run_a, run_b, "the first run"), (run_b, run_a, "the second run")):
        orphan = next(
            (
                frame
                for frame in run
                if id(frame) not in matched
                and _evidential(frame)
                and not _fills_something_optional(frame, run, other)
            ),
            None,
        )
        if orphan is not None:
            raise InductionFailed(
                f"{label} did something the other did not: "
                f"{describe_step(orphan)}. The runs are not two runs of one task",
                step_index=orphan.index,
            )
```

and beside it:

```python
def _fills_something_optional(
    frame: ActionFrame, run: tuple[ActionFrame, ...], other: tuple[ActionFrame, ...]
) -> bool:
    """Whether this unmatched step only filled a field the other run left alone.

    Two people filling one form fill different subsets of it, and both create
    the record. Dropping such a step loses nothing the skill needs, because the
    field it filled is about to become an optional parameter -- and keeping the
    refusal means a form of any size never induces at all.

    Everything here is read from the writes. The field must be one *both* runs
    sent, or the two are different requests and the refusal stands.
    """
    for write in run:
        pointer = key_filled_by(frame, write)
        if pointer is None:
            continue
        for theirs in other:
            document = _write_document(theirs)
            if document is None:
                continue
            leaves = dict(jsonutil.leaves(document))
            if pointer in leaves:
                return jsonutil.is_empty(leaves[pointer])
    return False
```

`_write_document` is the body-parsing half of `key_filled_by`; extract it into
`binding.py` as `write_document(frame) -> JsonValue | None` and use it from both
places rather than writing it twice.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit -q`
Expected: PASS, the whole suite.

- [ ] **Step 5: Prove the new test**

Delete the `and not _fills_something_optional(...)` clause, watch
`test_a_step_the_other_run_skipped_does_not_refuse_the_pair` fail, restore.
Then make `_fills_something_optional` `return True`, watch
`test_a_step_that_filled_something_the_other_run_did_not_send_still_refuses`
fail, and restore.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add -A src tests
git commit -m "feat(induction): a form filled two ways is one task done twice"
```

---

### Task 5: The step says which value it needs

The pair now induces, and `deltaPriority` is an optional parameter. The step
that fills it must say so, or execution has no way to know what to skip.

**Files:**
- Modify: `src/sro/domain/skill/skill.py:21-50` (`SkillStep`)
- Modify: `src/sro/application/induction/emit.py:26-47` (`emit_step`)
- Modify: `src/sro/application/induction/induce_skill.py:453-488` (`_build_steps`)
- Test: `tests/unit/application/test_a_field_nobody_filled.py`

**Interfaces:**
- Consumes: `Parameter.optional` (Task 2), `binding.key_filled_by` (Task 3).
- Produces: `SkillStep.when: str | None = None` — the parameter whose presence
  decides whether this step runs. Tasks 6 and 7 read it.

- [ ] **Step 1: Write the failing test**

```python
async def test_the_step_that_fills_an_optional_field_says_which_one() -> None:
    """Without this, execution has a parameter it may leave out and no idea
    which gesture to leave out with it."""
    skill = await _induce_the_two_work_areas()
    version = skill.versions[-1]

    optional = [p for p in version.parameters if p.optional]
    assert [p.name for p in optional] == ["delta_priority"]
    conditional = [step for step in version.steps if step.when]
    assert [step.when for step in conditional] == ["delta_priority"]
```

`_induce_the_two_work_areas` is a helper in this file that builds two recordings
from the shapes above and runs `InduceSkill` with the repo's fakes — copy the
construction from `tests/unit/application/test_teaching_what_was_watched.py`,
which already does exactly this.

- [ ] **Step 2: Run it and watch it fail**

Run: `uv run pytest tests/unit/application/test_a_field_nobody_filled.py -q -k says_which`
Expected: FAIL — `SkillStep` has no `when`.

- [ ] **Step 3: Add the field**

In `src/sro/domain/skill/skill.py`, `SkillStep` gains:

```python
    when: str | None = None
    """The parameter whose presence decides whether this step happens.

    A form's optional field: the demonstration that filled it typed here, and
    the one that skipped it did not. Supplied, the step runs; absent, it is
    skipped and the field takes the form the skipping demonstration sent."""
```

No invariant is added: a `when` naming a parameter that does not exist is
caught by `SkillVersion.__post_init__`'s existing placeholder check only if it
appears in a template, so add to that check — read `skill.py:270-285` and extend
the same loop that raises "references undeclared parameters" to cover `when`.

- [ ] **Step 4: Set it where steps are emitted**

`emit_step` gains a `when: str | None = None` keyword and passes it into
`SkillStep`. `_build_steps` computes it: for each pair, if the frame typed a
value that binds (Task 3) to a pointer whose parameter is optional, pass that
parameter's name.

```python
    optional_by_pointer = {
        parameter.source_pointer or _pointer_of(parameter, parameterisation): parameter.name
        for parameter in parameterisation.parameters
        if parameter.optional
    }
```

Read `Parameterisation.substitutions` to map a step's `JsonBodySite` pointer to
the parameter name rather than inventing `_pointer_of`; the mapping is already
there as `Substitution(site=JsonBodySite(pointer), parameter=name)`.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit -q`
Expected: PASS.

- [ ] **Step 6: Prove the new test**

Stop passing `when` in `emit_step`, watch the test fail, restore.

- [ ] **Step 7: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add -A src tests
git commit -m "feat(skill): a step can say which value it needs to happen at all"
```

---

### Task 6: The network path sends the absent form

**Files:**
- Modify: `src/sro/application/execution/execute_skill.py:719-780` (`_perform`)
- Modify: `src/sro/application/execution/execute_skill.py:1178-1196` (`_check_runnable`)
- Test: `tests/unit/application/test_a_field_nobody_filled.py`

**Interfaces:**
- Consumes: `Parameter.optional`, `Parameter.absent_as` (Task 2).
- Produces: nothing new; behaviour only.

- [ ] **Step 1: Write the failing test**

```python
async def test_a_run_without_an_optional_value_sends_what_the_demonstration_sent() -> None:
    """`null`, because that is what the form sent when nobody filled it. A
    field that wants null and gets an empty string is a rejected write."""
    ...  # build a version with an optional parameter whose absent_as is "null",
    ...  # run it through ExecuteSkill with a FakeHttpCaller, and read what went
    assert sent.body == '{"workArea": "PACK-3", "deltaPriority": null}'


async def test_an_optional_value_that_is_supplied_is_sent() -> None:
    assert sent.body == '{"workArea": "PACK-3", "deltaPriority": 4}'


async def test_a_required_value_nobody_supplied_still_refuses_to_run() -> None:
    with pytest.raises(NotRunnable, match="no value supplied for work_area"):
        ...
```

Build these on `tests/unit/application/test_running_a_skill.py` (or whichever
file already drives `ExecuteSkill` with `FakeHttpCaller`) — copy its harness
rather than inventing one.

- [ ] **Step 2: Run and watch fail**

Expected: the first FAILS with `no value for parameter 'delta_priority'` — the
template renders with `KeyError` today.

- [ ] **Step 3: Implement**

In `_perform`, before rendering, fill absent optionals:

```python
        # An optional field nobody supplied is sent the way the demonstration
        # that skipped it sent it. Filled in here rather than left to the
        # template, because `absent_as` is JSON -- `null`, not the string
        # "null" -- and the template only knows about text.
        rendered = dict(values)
        for parameter in parameters:
            if parameter.optional and parameter.name not in rendered:
                rendered[parameter.name] = parameter.absent_as or ""
```

and render from `rendered`. Where `absent_as` is `"null"` the body template's
`"${delta_priority}"` must lose its quotes at emission — handle that in
`emit.py` by substituting the placeholder *without* surrounding quotes for a
parameter whose `absent_as` is not a JSON string. Read `_network_plan` and
`substitute_url`/body substitution before writing this; the quoting rule lives
there.

In `_check_runnable`, the required set skips optionals:

```python
    required = {
        p.name for p in version.parameters if p.kind is ParameterKind.INPUT and not p.optional
    }
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit -q`

- [ ] **Step 5: Prove them**

Drop the `not p.optional` clause, watch the "without an optional value" test
fail with `NotRunnable`, restore.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add -A src tests
git commit -m "feat(execution): an optional field is sent the way the demonstration skipped it"
```

---

### Task 7: The gesture path skips the step

The point of the whole plan for a WMS with no writable API.

**Files:**
- Modify: `src/sro/application/execution/execute_skill.py:463-520` (`_perform_in_ui`)
- Test: `tests/unit/application/test_a_field_nobody_filled.py`

**Interfaces:**
- Consumes: `SkillStep.when` (Task 5).
- Produces: a `StepOutcome` with `StepDisposition.SKIPPED` and a detail naming
  the parameter.

- [ ] **Step 1: Write the failing test**

```python
async def test_a_conditional_step_with_no_value_is_not_typed() -> None:
    """On a system with no writable API, the form is the only way in -- so the
    skip has to work here, not only on the call."""
    driver = FakeUiDriver()
    await _run_by_clicking(version_with_optional_delta, values={"work_area": "PACK-3"}, ui=driver)

    typed = [action for action in driver.performed if action.kind is ActionKind.TYPE]
    assert [a.value for a in typed] == ["PACK-3"], "the skipped field was typed anyway"


async def test_a_conditional_step_with_a_value_is_typed() -> None:
    driver = FakeUiDriver()
    await _run_by_clicking(
        version_with_optional_delta, values={"work_area": "PACK-3", "delta_priority": "4"}, ui=driver
    )

    typed = [action for action in driver.performed if action.kind is ActionKind.TYPE]
    assert [a.value for a in typed] == ["PACK-3", "4"]
```

- [ ] **Step 2: Run and watch fail**

Expected: the first FAILS — the step is performed with an empty or missing
value.

- [ ] **Step 3: Implement**

At the top of `_perform_in_ui`:

```python
        if step.when and not values.get(step.when):
            # The demonstration that skipped this field did not touch this
            # control, so neither does this. Skipped rather than typed empty:
            # an empty keystroke into a required-looking field is how a form
            # ends up with a validation error nobody asked for.
            return StepOutcome(
                index=step.index,
                medium=Medium.UI,
                disposition=StepDisposition.SKIPPED,
                intent=step.intent,
                detail=f"nothing was supplied for {step.when}, which this step fills",
            )
```

Check the exact `StepOutcome` construction used elsewhere in that method and
match it, including how `medium` is chosen when the run escalates.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit -q`

- [ ] **Step 5: Prove them**

Remove the guard, watch the first test fail, restore.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add -A src tests
git commit -m "feat(execution): a field nobody supplied is a control nobody touches"
```

---

### Task 8: The two work areas, end to end

Everything above is unit-scale. This proves the thing the plan exists for,
against the evidence that motivated it.

**Files:**
- Create: `backend/tests/fixtures/work_areas/` (two batch payloads, trimmed from
  the real capture)
- Test: `tests/unit/application/test_a_field_nobody_filled.py`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing.

- [ ] **Step 1: Take the evidence out of the object store**

The two doings are stored under `acme/devansh/2026-08-27/`. Read them with the
snippet in `backend/scripts/` style, keep only the events between the first
gesture of each doing and its write, and save them as two `.ndjson` fixtures.
Redact nothing further — the capture already redacted credentials — but check
the fixture for the tenant's own hostname and replace it with `wms.acme.test`.

- [ ] **Step 2: Write the failing test**

```python
async def test_the_two_work_areas_become_one_skill() -> None:
    """The evidence this whole plan came from: two work areas created by hand
    on 2026-08-27, one with a Delta Priority and one without."""
    uow, blobs = FakeUnitOfWork(), FakeBlobStore()
    candidate = await _stored_from_fixtures(uow, blobs)

    taught = await _teach(uow, blobs, _NoUnderstanding(), _Induces()).execute(
        CTX, candidate_id=candidate.id
    )

    assert taught.skill_id is not None
    version = (await uow.skills.get(f.TENANT, taught.skill_id)).versions[-1]
    names = {p.name for p in version.parameters}
    assert {"work_area", "work_area_description"} <= names
    assert [p.name for p in version.parameters if p.optional] == ["delta_priority"]
```

- [ ] **Step 3: Run it, fix what it finds**

This is the test most likely to surface something the unit tests missed —
a normalisation the form does that Task 3 does not cover, an assertion the
extractor derives from an empty field, a name the suggester picks that reads
badly. Fix those in the task they belong to rather than here.

- [ ] **Step 4: Run everything**

```bash
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/browser -q
```

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src tests/unit/fakes.py && uv run lint-imports
git add -A
git commit -m "test(induction): the two work areas that would not induce"
```

---

### Task 9: Say it in the docs

**Files:**
- Create: `docs/adr/00N-a-skipped-field-is-a-value.md` (next free number)
- Modify: `docs/04-induction.md` (or whichever doc describes the two-run diff —
  check `docs/` and follow its numbering)

- [ ] **Step 1: Write the ADR**

Context: the two work areas and why they refused. Decision: an unmatched step
may be dropped when the writes prove the field it filled is optional; the absent
form is read from the run that skipped it; binding is exact after normalisation.
Consequences: a form of any size can induce from passive observation; a key one
run does not send still refuses; a value binding to two keys binds to neither.

- [ ] **Step 2: Commit**

```bash
git add docs
git commit -m "docs: why a skipped field is a value and not a missing step"
```

---

## Self-Review

**Spec coverage.** Part 1 → Tasks 1–5 (shape, optionality, binding, alignment,
the conditional step). Part 2 → Tasks 6–7 (network absent form, UI skip) with
the vision path inheriting the skip because it goes through the same
`_perform_in_ui` guard. Parts 3–6 are out of scope by the Global Constraints and
have their own plans. The spec's normalisation rule is Task 3. The spec's "no
migration" claim is checked in Task 5 (document fields with defaults).

**Placeholders.** Task 6's test bodies and Task 8's fixture loading are written
as prose because they must be built on harnesses already in the repo, which the
implementer has to read; every rule they assert is stated exactly. Everything
else carries real code.

**Type consistency.** `Parameter.optional` / `Parameter.absent_as` (Task 2) are
read in Tasks 5, 6. `SkillStep.when` (Task 5) is read in Tasks 6, 7.
`binding.key_filled_by` (Task 3) is called in Tasks 4, 5. `jsonutil.is_empty`
and `jsonutil.same_shape` (Task 1) are called in Tasks 2, 4.
