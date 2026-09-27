# R2 report: wording to fields (spec §4.2; L3)

Branch `d2/r2`, from `feat/execution-runtime` at `384e609`.

## Commits

- `deb1c1c` feat(aliases): the operator's answer teaches a job its words for a field
- (this report) docs: R2 report

## Files changed

- `backend/migrations/versions/20260927_0088_a_job_remembers_its_words.py` (new): table `job_aliases`, PK `(tenant_id, workflow_id, wording_key)`. **Revision 0088, down_revision 0085**, as the controller directed. The brief's `0078` filename was stale. The controller re-chains it at merge.
- `backend/src/sro/application/ports/repositories.py`: `WorkflowRepository.aliases_for` and `confirm_alias`.
- `backend/src/sro/infrastructure/db/models.py`: `JobAliasRow`, placed next to `JobRecipientRow`.
- `backend/src/sro/infrastructure/db/workflows.py`: `aliases_for` (oldest first, then by wording key) and `confirm_alias` (an upsert on `normal(wording)`).
- `backend/tests/unit/fakes.py`: `FakeWorkflowRepository.aliases: dict[tuple[str, str], dict[str, JobAlias]]` and the two methods.
- `backend/src/sro/application/skill/job_facts.py`: loads `aliases_for` for each job, replacing C1's `()`. The compile check (`compile_job`) and the reader therefore see the aliases too.
- `backend/src/sro/domain/execution/compose.py`: `compose(..., aliases=())`. A value name whose `normal` form is an alias's wording is matched against that alias's field label.
- `backend/src/sro/application/runtime/run_steps.py`:
  - `prepare` and the unplaced check in `step` (index 0) pass the job's aliases to `compose`.
  - `answered` builds the alias on a label answer.
  - `_write` confirms it inside its compare-and-set, just before the commit.
  - A new `_aliases` helper loads the job's aliases.
- `backend/src/sro/application/runtime/answer_run.py`: a `field` answer now also keeps `by` (the answering principal), as a `recipient` answer already does.
- Code notes: `compose.py.md`, `run_steps.py.md` (`answered`, `_write`) and `workflows.py.md` (`confirm_alias`). Stale anchors were fixed with `--fix`.

## Tests added

Unit:
- `tests/unit/test_only_an_answer_writes_an_alias.py`: the only source file that calls `confirm_alias(` is `application/runtime/run_steps.py`.
- `tests/unit/domain/test_composing_a_field.py`, two tests:
  - a confirmed alias places a wording that no label matches;
  - an alias outranks a label the wording also matches.
- `tests/unit/application/runtime/test_an_answer_teaches_an_alias.py`, eight tests:
  - a label the operator picks becomes the job's alias;
  - the alias is the answering operator's, not the run starter's;
  - leaving the value out teaches nothing;
  - an option (`no_option`) teaches nothing;
  - the next run places the wording without asking;
  - a later alias for the same normalised wording replaces the earlier one;
  - an answer applied twice teaches once;
  - an answer that another attempt moved past (`Superseded`) teaches nothing.

Contract (runs against both the fake and SQL):
- `tests/contract/test_the_repositories_agree.py::TestWorkflows::test_a_job_keeps_one_alias_per_wording_oldest_first_and_the_later_wins`. The fake half ran here. The `[sql]` half was **written, not run**.

Integration (**written, not run**):
- `tests/integration/test_job_aliases.py`:
  - `test_one_alias_per_wording_and_the_later_answer_wins` (also checks scoping per job and per tenant);
  - `test_aliases_come_back_oldest_first`.

## Gate results

- `uv run pytest tests/unit tests/contract -q -k "not sql" --deselect tests/contract/test_openapi.py::TestFuzz`: **4654 passed**.
  - The deselected `[sql]` contract params need Postgres. `TestFuzz` needs Docker, and it errors the same way on the base commit.
- `uv run mypy src tests`: no issues (807 files).
- `uv run ruff check .` and `uv run ruff format --check .`: clean.
- `uv run lint-imports`: 4 kept, 0 broken.
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead.
- **Worker restart needed** (`RunSteps`).

## Rulings

- Ruling: `answered` takes no `value` argument. The label is read from `asking["choice"]`, which `AnswerRun` stores. — That is how the real D5/X10 code works: `answered(ctx, run_id, question_id)`, and only the question id is signalled (GC invariant 11). The code wins (GC 15). — Cost if wrong: none, because the value is the same one the operator gave.
- Ruling: `confirmed_by` is the answering principal. `AnswerRun` keeps it as `asking["by"]`, and `answered` falls back to `ctx.principal_id` only for an answer stored before this change. — In the worker, the `run.answered` activity's `ctx` is the run's (`ref.principal_id`), not the answerer's. The brief's `ctx.principal_id.value` would credit the run's starter for a colleague's answer (GC invariant 5). This mirrors the existing `recipient` answer. — Cost if wrong: one extra key on the field answer. A second press of the same choice by a *different* operator is now refused as "already answered". It was idempotent before, and the recipient answer already behaves this way.
- Ruling: the alias is written by `_write`, inside the `record_progress` compare-and-set, just before the commit. It is not written in a separate unit of work. — The brief asks for "the same unit of work that stores the answer". Inside the CAS, a superseded or repeated answer teaches nothing, and a crash loses the alias and the progress together. — Cost if wrong: `_write` gains one optional keyword.
- Ruling: only the `choices()` branch teaches, that is `why` in `no_field` or `ambiguous`. A `failed` retry and a `no_option` answer save nothing. — A `failed` question re-offers the label the value was already placed on, so it is not a wording-to-field answer. A `no_option` choice is a value, as the brief says. — Cost if wrong: a retry answer does not refresh an alias's `at`.
- Ruling: the alias stores the form's label (`hit.label`), not the choice string as offered (for example `"Department (textbox)"`). — The brief and spec say "field label", and `compose` matches labels. — Cost if wrong: a wording aliased to a label that appears twice on the form is still asked about next run, as ambiguous. That errs toward asking, never toward guessing.
- Ruling: the tests use the existing `steel_run(...)` and `world.answer(...)` harness, not the brief's `asking_steel_run(kind=, name=, choices=)` / `world.start_again` / `world.progress(run_id)`. A second run is saved directly in the test (`_again`). — D5's `asking_steel_run` only leaves a bare question on a run with no form. The field question here must come from a real `compose`, over a real outline. — Cost if wrong: none to behaviour; the helpers could be moved into `runtime_support` later.
- Ruling: the brief's `compose` body (which inlines matching and uses `workflow.steps` parameters as `filled`) was not copied. Only the matched label changed: `placed(..., said.get(normal(name), name))`. — X10's real `compose` uses `bindable` and `placed`, and the code wins. — Cost if wrong: none.
- Ruling: `aliases_for` orders by `(at, wording_key)`, and the fake orders the same way. — This makes the order total when two aliases share an instant. — Cost if wrong: none.

## Concerns

- A wording aliased to a field is placed even when the request's own name is also an exact label on the form. This is spec §4.2 ("a confirmed alias outranks"), and it is tested. It means an operator's mistaken answer keeps misplacing that wording until a later answer replaces it. No UI yet lists or removes aliases; per spec §7 that is design 3.
- The `[sql]` contract half and the integration tests have not been run here, because there is no Postgres in this session.

---

## Round 1

Base: `origin/feat/execution-runtime` was merged into `d2/r2` as merge commit `9b5c357`, with no rebase, so R1 and K1 are in the base. The migration stays **0088** (down_revision 0085). Its table gains a `role` column.

### Fixes

- **I1**: R1's `field_of` (`domain/chat/request.py`) now resolves an alias's label through the same `normal` label match as any wording. This is the new `labelled(key, fields)` in `domain/execution/field_classes.py`. An aliased value therefore lands on the parameter that the label belongs to, and that parameter's limits apply. An alias whose label no field carries is still left aside, as before. `compile_job`'s unbound-parameter check (`domain/execution/compiled.py`) resolves the alias the same way. Its `field_classes` computation moved above that check.
- **I2**: only the reader's own question teaches. That is the `compose` question asked before the first step, which `_ask(..., wording=True)` marks with `asking["wording"] = "yes"`.
  - The `_fill_asks` `no_field`/`ambiguous` question moves this run's value and saves nothing.
  - No alias is ever saved whose wording already equals a label on the form.
- **M1**:
  - `AnswerRun` refuses a second operator's press on an answered field question, with the 409 "that question was already answered by another operator". The same operator pressing again is still accepted.
  - The router docstring (`workflow_runs.py`) now says this. `make types` regenerated `frontend/openapi.json` and `frontend/src/lib/api/generated.ts`.
- **M2**: `JobAlias` gains `role: str = ""`, and there is a matching `role` column. The role is saved only when the chosen option had to tell two same labels apart (`choice != hit.label`). `compose` then keeps only hits with that role, so the next run places the value without asking.
- **M4**: the replace test now goes through two real answers. Two runs of the job both ask about "cost centre": the first is answered Department, the second Region, and the alias ends up as Region.
- **M5**: `teaches(wording, labels)` in `compose.py` refuses words on a small named stoplist, `K_GENERIC`: value, values, name, field, data, text, input, info, item, entry, thing. It also refuses a label already on the form.

### Tests added or changed

- `test_reading_a_request.py::test_an_alias_lands_on_the_parameter_its_label_names_and_its_limits_apply`: alias "cost centre -> Department", Department max 5, value "Finance Team". It is refused with "longer than 5 characters", exactly as when given under "Department". (I1)
- `test_compiling_a_job.py::test_an_alias_binds_by_the_label_of_the_parameter_a_step_fills`. (I1, compiled)
- `test_composing_a_field.py`:
  - `test_an_alias_outranks_a_label_the_wording_also_matches` is removed, because such an alias is now never saved (I2).
  - New `test_an_alias_with_a_role_places_the_wording_on_that_one_of_two_same_labels` (M2).
  - New `test_a_generic_word_or_a_label_on_the_form_is_never_taught`, parametrised (M5, I2).
- `test_an_answer_teaches_an_alias.py`:
  - `test_a_field_the_page_lacked_this_run_teaches_nothing` (the I2 probe: the page lacks Region once, the operator picks Department, and no alias is saved);
  - `test_a_wording_that_is_already_a_label_on_the_form_teaches_nothing`;
  - `test_a_generic_wording_teaches_nothing`;
  - `test_one_of_two_same_labels_is_taught_with_its_role_and_not_asked_again`;
  - `test_a_second_operators_press_on_an_answered_field_is_refused`;
  - `test_a_later_answer_for_the_same_wording_replaces_the_alias`, rewritten (M4).
- The contract test and `tests/integration/test_job_aliases.py` now store a `role`. They are **written, not run** (Postgres).

Each new test was run before its fix and failed for the reason under test: an alias saved, `role` missing, the wrong 409 wording, or `('Department', False)` returned.

### Gates

- `pytest tests/unit tests/contract -k "not sql" --deselect TestFuzz`: **4714 passed**.
- `mypy src tests`: clean (811 files).
- `ruff check`, `ruff format --check` and `lint-imports`: clean.
- `check_code_notes.py`: 0 stale, 0 dead.
- `test_the_committed_schema_is_current.py`: passed.
- Frontend `npx tsc --noEmit`: clean.
- **Worker restart needed** (`RunSteps`, `AnswerRun`).

### Rulings

- Ruling: the "which field" question is marked by a stored flag, `asking["wording"] = "yes"`. It is not inferred from `why`. — `compose` and `_fill_asks` both use `no_field`/`ambiguous`, so `why` cannot tell them apart. — Cost if wrong: one extra key in `progress.asking`. A question already standing when this is deployed teaches nothing when answered.
- Ruling: the role is saved only when the choice was told apart by role (`choice != hit.label`). It is not saved on every alias. — This does what M2 asks without tying ordinary aliases to a role that the form may later change. — Cost if wrong: two same labels that also share a role, and differ only by step, are still asked about each run.
- Ruling: the round-1 answer to M2 supersedes the round-0 ruling "the alias stores the form's label, not the choice as offered". The label is still stored; the role is added beside it.
- Ruling: `K_GENERIC` lives in `domain/execution/compose.py` next to `normal`, not in `domain/skill/aliases.py`. — `aliases.py` importing `compose` would be circular. — Cost if wrong: none.
- Ruling: `field_of` returns `(aliased, False)` for an alias whose label resolves to no field, as it did before. — The value is then kept aside under that label. `compose` still places it by label at run time. — Cost if wrong: none new.

### Concerns

- `npm ci` was run in `frontend/` to get `openapi-typescript` for `make types`. Only the two generated files changed.

---

## Round 2

The migration is unchanged (0088, down_revision 0085). The controller re-chains it.

### Fixes

- **N1**: `_wordings` (`domain/chat/request.py`) now maps each alias wording to the parameter its label resolves to, not to the bare form label.
  - The resolution is a new `_aliased(label, candidate)` helper that uses `labelled`. `field_of` now uses the same helper for its alias branch.
  - Before this fix, the quote check in `_placed` saw "cost centre" name "Department" while the value landed on "department". It then refused every aliased value as "its quote names Department", even one within its limits.
- **M3**: the fake `confirm_alias` now honours the unit of work.
  - A write is staged. `FakeUnitOfWork.commit` keeps it; `rollback`, and an exit without a commit, discard it.
  - `aliases_for` reads the committed aliases plus this unit's staged ones, the same read-your-writes view a real session gives.
  - The other fake repositories still do not simulate rollback. This one now does, because the alias is written inside the answer's own commit.

### Tests added

- `test_reading_a_request.py::test_an_aliased_value_inside_its_limits_is_read_like_one_under_the_label`: "cost centre: Fin" and "Department: Fin" both read as `department = Fin`, with nothing refused. It sits next to Round 1's over-limit test. Before the fix it failed with `{}` and a "its quote names Department" refusal.
- `test_an_answer_teaches_an_alias.py::test_an_answer_whose_unit_of_work_rolls_back_leaves_no_alias`: the answer's commit raises, and no alias is left. Before the fix the alias stayed.

### Gates

- `pytest tests/unit tests/contract -k "not sql" --deselect TestFuzz`: **4716 passed**.
- `mypy src tests`: clean.
- `ruff check`, `ruff format --check` and `lint-imports`: clean.
- `check_code_notes.py`: 0 stale, 0 dead.

### Rulings

- Ruling: the fake discards staged aliases on any exit without a commit, not only on an exception. — A real session closed without a commit keeps nothing. — Cost if wrong: a test that writes an alias without committing now sees it vanish. No test does that.
