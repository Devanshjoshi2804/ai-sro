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
