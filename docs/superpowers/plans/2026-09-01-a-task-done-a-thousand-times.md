# A Task Done A Thousand Times — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Induction decides each step by how often it appears across every occurrence of a task, instead of by what two of them happen to share.

**Architecture:** `align(run_a, run_b)` pairs two recordings on their longest common subsequence, and every other occurrence is passed separately to `parameterise(..., others=history)`. So the other doings shape parameters and never steps — which is how a real skill ended up with a `cod_address_id` parameter and no step to fill it. This plan makes the steps read the same evidence the parameters already do: align every occurrence against one reference, count how often each step appears, and keep a rare step when a value explains it.

**Tech Stack:** Python 3.14, hexagonal layering enforced by import-linter, mypy --strict, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-a-task-done-a-thousand-times-design.md`

## Global Constraints

- **No model decides whether a step belongs.** ADR 004. A step's status is arithmetic over observed frames, and a reviewer must be able to recompute it by hand from the evidence.
- A rare step **that correlates with a supplied value is a branch** and is kept as `SkillStep.when`, however rare. A rare step with nothing explaining it is dropped.
- **Never truncate one demonstration to another's length.** A short doing is evidence a step can be skipped, never that it does not exist. The existing `frames[:keep]` truncation is loop detection and must keep working exactly as it does.
- **Never name a parameter with no step to fill it.** That is today's defect and the plan must close it, not move it.
- `domain/` imports nothing from `application/`; `application/` imports no `infrastructure/`. import-linter enforces this and `make lint` fails the build.
- Every new test is proved by reverting the rule it defends before the task is committed.
- Gate from `backend/`: `uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run lint-imports && uv run pytest tests/unit tests/contract -q`.

---

### Task 1: Every occurrence reaches the steps, not just the parameters

**Files:**
- Modify: `backend/src/sro/application/induction/diff.py` (add `align_all` beside `align`)
- Test: `backend/tests/unit/application/test_a_task_done_many_ways.py` (create)

**Interfaces:**
- Consumes: `align(run_a, run_b)`, `_longest_common`, `_same`, `_evidential`, `describe_step` — all in `diff.py`.
- Produces: `align_all(runs: Sequence[tuple[ActionFrame, ...]]) -> Alignment`, where `Alignment` is a frozen dataclass carrying `reference: tuple[ActionFrame, ...]` and `seen: dict[int, int]` mapping reference-frame index to how many runs contained that step.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/application/test_a_task_done_many_ways.py`:

```python
"""One task, done four different ways, is still one task.

An operator added four carrier cross references in a real WMS. Sometimes they
filled every field, sometimes a few; one doing included a whole address lookup
the others skipped. Induction aligned two of the four and produced a skill with
two steps -- both the same button -- while correctly deriving four parameters
from all four. It named `cod_address_id` and had no step that could fill it.

The variation is the work, not noise in it. What separates a step of the task
from a fumble is how often it appears, not whether two particular doings
happened to share it.
"""

from __future__ import annotations

from sro.application.induction.diff import align_all
from tests import factories as f


def _run(*controls: str):
    """A doing, as the sequence of controls it touched."""
    return tuple(
        f.frame(index, action=f.click_on(control)) for index, control in enumerate(controls)
    )


def test_a_step_every_doing_made_is_seen_by_all_of_them() -> None:
    found = align_all([
        _run("Add", "Carrier", "Save"),
        _run("Add", "Carrier", "Save"),
        _run("Add", "Carrier", "Save"),
    ])

    assert [f.control_of(frame) for frame in found.reference] == ["Add", "Carrier", "Save"]
    assert set(found.seen.values()) == {3}


def test_a_step_only_one_doing_made_is_counted_once_not_dropped() -> None:
    """The whole defect in one assertion. Today the address lookup vanishes
    because two of four doings did not contain it; here it survives with its
    count, and a later task decides what that count means."""
    found = align_all([
        _run("Add", "Carrier", "Save"),
        _run("Add", "Carrier", "Save"),
        _run("Add", "Carrier", "COD Address", "Save"),
    ])

    controls = [f.control_of(frame) for frame in found.reference]
    assert "COD Address" in controls, controls
    assert found.seen[controls.index("COD Address")] == 1
    assert found.seen[controls.index("Add")] == 3


def test_the_reference_is_the_doing_others_agree_with_most() -> None:
    """Not the longest, and not the most recent. The longest may be the one
    where somebody wandered; the most recent is an accident of ordering."""
    found = align_all([
        _run("Add", "Carrier", "Save"),
        _run("Add", "Carrier", "Save"),
        _run("Add", "Carrier", "Save"),
        _run("OK", "Add", "Wander", "Carrier", "Save"),
    ])

    assert [f.control_of(frame) for frame in found.reference][:3] == ["Add", "Carrier", "Save"]


def test_one_doing_alone_is_still_an_alignment() -> None:
    """A task demonstrated once has nothing to disagree with it. Every step is
    seen by everything there is."""
    found = align_all([_run("Add", "Save")])

    assert len(found.reference) == 2
    assert set(found.seen.values()) == {1}


def test_nothing_at_all_refuses_rather_than_returning_an_empty_task() -> None:
    from pytest import raises

    from sro.application.induction.errors import InductionFailed

    with raises(InductionFailed):
        align_all([])
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/application/test_a_task_done_many_ways.py -v`
Expected: FAIL — `align_all` does not exist.

`f.click_on` and `f.control_of` may not exist. READ `backend/tests/factories.py` and `backend/src/sro/application/induction/diff.py:216` (`_control`) first, and use what is there. Do not add shared factory helpers to make the literal text work — build local helpers in the test file, following `backend/tests/unit/domain/test_autonomy.py`.

- [ ] **Step 3: Write `align_all`**

In `diff.py`, beside `align`. It must:

1. Choose the **reference**: the run whose steps are most often present in the others, measured with the existing `_longest_common` against each. Not the longest, not the most recent — say why in the docstring.
2. Align every run against the reference with `_longest_common`.
3. Count, per reference-frame index, how many runs contained a matching step.
4. Where a run has an evidential step the reference does not, **extend the reference** with it at the aligned position rather than dropping it. This is the defect being fixed; the docstring must say so.
5. Refuse on empty input with `InductionFailed`.

Do NOT change `align`. It stays as the two-run function, and Task 2 decides who calls what.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit/application/test_a_task_done_many_ways.py -v` — expected PASS, 5 tests.
Then: `cd backend && uv run pytest tests/unit tests/contract -q` — expected PASS, nothing else moved.

- [ ] **Step 5: Prove each test by reverting its rule**

For the extend-the-reference rule, drop the extension and confirm only `test_a_step_only_one_doing_made_is_counted_once_not_dropped` fails. For the reference choice, pick the longest run instead and confirm only `test_the_reference_is_the_doing_others_agree_with_most` fails. Restore both. Report which revert went with which test.

- [ ] **Step 6: Commit**

```bash
cd backend && uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run lint-imports
git add backend/src/sro/application/induction/diff.py backend/tests/unit/application/test_a_task_done_many_ways.py
git commit -m "feat(induction): align every occurrence, and count what each one did

align() pairs two runs on their longest common subsequence, and every other
occurrence goes separately to parameterise() as history. So the other doings
shaped the parameters and never the steps: a real skill came out with a
cod_address_id parameter derived from a demonstration whose steps were then
discarded, and no step that could fill it.

align_all reads them all against one reference -- the doing the others agree
with most, which is neither the longest nor the newest -- and keeps how many
contained each step. It decides nothing yet; it stops throwing the evidence
away."
```

---

### Task 2: A step's place is decided by how often it appears

**Files:**
- Create: `backend/src/sro/application/induction/frequency.py`
- Test: `backend/tests/unit/application/test_what_makes_a_step_part_of_a_task.py` (create)
- Create: `docs/07-adr/015-a-step-is-decided-by-how-often-it-happens.md`

**Interfaces:**
- Consumes: `Alignment` from Task 1; `Parameterisation`, `Choice` from `diff.py`; `SkillStep.when`.
- Produces: `Standing` (an enum: `ALWAYS`, `CONDITIONAL`, `NOISE`) and `standing_of(alignment, parameterisation) -> dict[int, Standing]`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/application/test_what_makes_a_step_part_of_a_task.py`:

```python
"""What separates a step of a task from a fumble.

Neither intersection nor union survives a thousand doings. Intersection is what
induction does today and loses every optional field. Union would learn the task
plus a thousand accidents -- every mis-click, every field somebody typed and
corrected, every interruption.

Frequency is the signal neither has. And frequency alone is not enough: a step
in three per cent of doings that appears whenever one particular value was
supplied is a branch, and dropping it is how a skill silently stops handling the
case somebody needed it for. A step in three per cent with nothing explaining it
is a fumble.
"""
```

Cover, each as its own test, using local helpers rather than new shared factories:

- a step in every doing is `ALWAYS`
- a step in most doings, above the threshold, is `ALWAYS`
- a step below the threshold **whose presence tracks a supplied parameter** is `CONDITIONAL`, even at one occurrence in a hundred
- a step below the threshold with **no parameter explaining it** is `NOISE`
- a task demonstrated once has every step `ALWAYS` — there is nothing to disagree with it
- the threshold is read from a named module constant, not a literal at the call site

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/application/test_what_makes_a_step_part_of_a_task.py -v`
Expected: FAIL — no module `sro.application.induction.frequency`.

- [ ] **Step 3: Write it**

Create `frequency.py` with a named constant carrying its reasoning in the style of `WORTH_OFFERING` in `backend/src/sro/domain/observation/candidate.py` — read that first and match its voice. The constant is a **share of occurrences**, not a count, so it means the same at four doings and four thousand.

`standing_of` takes the alignment and the parameterisation and returns a standing per reference-frame index. It reads only counts and which parameter a frame's gesture fills; it must not call a model, and its docstring must say that ADR 004 is why.

- [ ] **Step 4: Run the tests, then the whole suite**

Run: `cd backend && uv run pytest tests/unit tests/contract -q` — expected PASS.

- [ ] **Step 5: Write ADR 015**

`docs/07-adr/015-a-step-is-decided-by-how-often-it-happens.md`. Read `docs/07-adr/013-a-tool-call-is-a-third-medium.md` and `docs/07-adr/014-a-preview-an-operator-read-is-a-review.md` first and match their shape, length and voice — both state the rejected alternative and why it lost, and 014 was sent back twice for asserting rather than arguing.

It must cover: why intersection fails at four and union fails at a thousand; what the threshold is and who may change it; **why a rare step with a value behind it is a branch and a rare one without is not**; why none of it is a model's judgement; and what it gives up — a genuinely rare branch demonstrated once, whose value correlation is itself weak evidence.

- [ ] **Step 6: Prove the tests and commit**

Revert the correlation rule so a rare step is always `NOISE`, and confirm only the branch test fails. Restore.

```bash
git add backend/src/sro/application/induction/frequency.py backend/tests/unit/application/test_what_makes_a_step_part_of_a_task.py docs/07-adr/015-a-step-is-decided-by-how-often-it-happens.md
git commit -m "feat(induction): a step's place is decided by how often it happens

Intersection loses every optional field; at four doings it produced a two-step
skill. Union would learn the task plus a thousand accidents. Frequency is the
signal neither has.

Rarity alone drops nothing. A step in three per cent of doings that appears
whenever one value was supplied is a branch -- that is the address lookup -- and
it is kept however rare, because a branch taken once in a hundred times is still
part of the task. A rare step with nothing explaining it is a fumble."
```

---

### Task 3: Induction builds the skill from every occurrence

**Files:**
- Modify: `backend/src/sro/application/induction/induce_skill.py:176-265`
- Modify: `backend/src/sro/application/observation/teach.py:202-203`, `:368-369`
- Test: `backend/tests/unit/application/test_induce_skill.py` (extend), plus a case in `test_a_task_done_many_ways.py`

**Interfaces:**
- Consumes: `align_all` (Task 1), `standing_of` and `Standing` (Task 2).
- Produces: no new signature; `InduceSkill.execute` keeps `first`, `second`, `others` and changes what it does with `others`.

This is the task that closes the defect. The two previous tasks are inert until this one calls them.

- [ ] **Step 1: Write the failing test**

Add to `test_a_task_done_many_ways.py` a test that runs `InduceSkill.execute` over four recordings shaped like the real carrier cross reference case — three short doings and one containing an extra lookup step correlated with a parameter — and asserts:

- the induced version has a step for **every** parameter it declares (the rule that "never name a parameter with no step to fill it" is now enforced)
- the lookup step carries `when` naming the parameter that drives it
- the step count is not the longest common subsequence of two of them

Build the recordings with local helpers; read `backend/tests/unit/application/test_induce_skill.py` for how a recording reaches `InduceSkill` and copy that setup rather than inventing one.

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/application/test_a_task_done_many_ways.py -v`
Expected: FAIL — the induced skill has fewer steps than parameters, which is today's behaviour.

- [ ] **Step 3: Change induction**

In `induce_skill.py`, replace the two-run alignment with the N-way one:

- `align_all` over `[frames_a, frames_b, *history]` rather than `align(frames_a, frames_b)`.
- `standing_of` decides which aligned steps become `SkillStep`s and which become `when` conditionals.
- Steps whose standing is `NOISE` are dropped, and the reason is recorded where a reviewer can read it.
- `parameterise` keeps its existing `others=history` behaviour — it was already right; it was the steps that were wrong.
- `loops.detect` and the `frames[:keep]` truncation keep working exactly as they do. Loop detection is about one run being several turns of a block, which is a different question from how many runs saw a step. **If they interact, stop and report rather than guessing** — a wrong answer here silently changes what a looping skill does.
- The existing `_conditionals(parameterisation, optional_fills(frames_a, frames_b))` path becomes a special case of the general one. Either fold it in or delete it, but do not leave two mechanisms producing `when`.

In `teach.py`, both call sites pass all sealed occurrences rather than the first two.

- [ ] **Step 4: Run everything**

Run: `cd backend && uv run pytest tests/unit tests/contract -q`
Expected: PASS. Existing induction tests are the real gate here — if any fails, read it before changing it. Several encode deliberate two-run behaviour and a reviewer will ask why it moved.

- [ ] **Step 5: Prove it against the real evidence**

The four recordings from the live failure are in the developer's database. Re-induce that candidate and confirm the skill now has a step per parameter and a `when` on the address lookup. Report the before and after step counts in your report. If the real data still produces a thin skill, **say so plainly** rather than adjusting the test until it passes — that is the whole point of this task.

- [ ] **Step 6: Commit**

```bash
git add backend/src/sro/application/induction/induce_skill.py backend/src/sro/application/observation/teach.py backend/tests
git commit -m "feat(induction): build the skill from every occurrence

Two recordings went to align() for the steps and the rest went to parameterise()
as history, so the other doings shaped the parameters and never the steps. A
real skill came out of four demonstrations with four correct parameters, two
steps, and no step that could fill cod_address_id -- a parameter derived from a
demonstration whose steps were discarded.

Now the steps read the same evidence the parameters already did."
```

---

### Task 4: Provenance says what was actually read

**Files:**
- Modify: `backend/src/sro/domain/skill/skill.py` (`Provenance`)
- Test: `backend/tests/unit/domain/test_a_preview_is_a_review.py` is the wrong home; create `backend/tests/unit/domain/test_what_a_skill_was_built_from.py`

- [ ] **Step 1: Write the failing test**

A skill induced from four occurrences records four, and each is marked for what it contributed — aligned for steps, or read for parameters only. Before this change a reader could not tell the two apart, which is how the defect stayed invisible: the provenance said four demonstrations and the steps came from two.

- [ ] **Step 2: Run it, watch it fail, implement, run again**

Run: `cd backend && uv run pytest tests/unit/domain/test_what_a_skill_was_built_from.py -v`

Skill versions are a JSONB document through a pydantic `TypeAdapter` (`backend/src/sro/infrastructure/db/codec.py`), so a new field on `Provenance` needs **no migration** — the same precedent as `systems` and `loops`. Confirm that by reading the codec before assuming it.

- [ ] **Step 3: Prove, gate and commit**

```bash
cd backend && uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run lint-imports && uv run pytest tests/unit tests/contract -q
cd .. && make types
git add backend/src backend/tests frontend/openapi.json frontend/src/lib/api/generated.ts
git commit -m "feat(skill): provenance says what each demonstration contributed

It recorded four recording ids for a skill whose steps came from two. Both
statements were true and together they misled: a reader checking why a skill had
a parameter it could not fill would have found four demonstrations listed and no
sign that two of them only ever touched the parameters."
```

---

### Task 5: The offer never hands over a skill it could not build

**Files:**
- Modify: `backend/src/sro/application/induction/induce_skill.py`
- Test: `backend/tests/unit/application/test_a_task_done_many_ways.py` (extend)

The spec's refusal: *never name a parameter it has no step to fill.* Task 3 should make that unreachable. This task makes it enforced rather than hoped for, because the panel now induces silently on a press and an operator sees whatever comes out.

- [ ] **Step 1: Write the failing test**

Induction refuses, with a sentence an operator would understand, when the version it is about to return declares a parameter no step uses. Assert on the message as well as the type — it reaches a warehouse operator's screen through the panel's teach-refusal path, which renders the reason.

- [ ] **Step 2: Run, implement, run**

The refusal belongs where the version is constructed, after conditionals are folded in. `InductionFailed` already carries `step_index`; read it before adding a new error type.

- [ ] **Step 3: Prove by reverting, gate, commit**

Revert Task 3's change so the old two-run alignment returns, and confirm this refusal fires on the four-doing case — that is the test proving the two tasks are wired to each other.

```bash
git add backend/src backend/tests
git commit -m "feat(induction): refuse a skill with a parameter nothing fills

The panel induces on a press now and shows an operator whatever comes out, so a
skill that names a value it has no step to type is not a curiosity in a database
-- it is something somebody is about to be offered."
```
