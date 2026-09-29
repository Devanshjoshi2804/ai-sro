# T1 report: tab roles, learned by code from the evidence and stored on the step

Branch `d2/t1`, from `feat/execution-runtime` at its tip.

## Commits

- `ec9e434` feat(tabs): each step's tab role is learned from the evidence and stored
- (this report) docs(t1): cloud report

## Files changed

Created:
- `backend/src/sro/domain/skill/tabs.py` — `OPENED_FROM`, `POPUP`, `tab_roles`, `unresolved`; re-exports `MAIN`.
- `backend/migrations/versions/20260927_0086_a_step_knows_its_tab.py` — `workflow_steps.tab TEXT NOT NULL DEFAULT 'main'`, revision `0086`, down `0085`.
- `backend/tests/unit/domain/test_tab_roles.py`
- `docs/code-notes/backend/src/sro/domain/skill/tabs.py.md`

Modified:
- `backend/src/sro/domain/skill/workflow.py` — `MAIN = "main"`; `Step.tab: str = MAIN`.
- `backend/src/sro/domain/execution/progress.py` — its own `MAIN` removed.
- `backend/src/sro/application/runtime/run_steps.py` — imports `MAIN` from `domain/skill/tabs.py`.
- `backend/src/sro/infrastructure/db/models.py` — `WorkflowStepRow.tab`.
- `backend/src/sro/infrastructure/db/workflows.py` — `_step_values`, `_row_to_step`.
- `backend/src/sro/application/observation/mining_pass.py` — roles set right after `uses_edges`, over the pass's whole `by_id`.
- `backend/src/sro/domain/observation/window.py` — `as_evidence` adds `"tab"` and `"opened"`.
- `backend/src/sro/interface/http/schemas.py` — `WorkflowStepModel.tab`; `make types` run, so `frontend/openapi.json` and `frontend/src/lib/api/generated.ts` are regenerated.
- `backend/src/sro/domain/execution/compiled.py` — reasons `tab_role_unresolved` and `tab_roles_unlearned`; `"tab"` in each step's view.
- Tests: `test_compiling_a_job.py`, `rig/test_window.py`, `rig/test_mine.py`, `interface/test_workflows_route.py` (the wire now has `tab`), `runtime/test_run_steps.py`, `runtime/test_asking.py`, `integration/test_runs_on_local_steel.py` (these import `MAIN` from `tabs` now), `integration/test_workflow_repositories.py`.
- Code notes: `tabs.py.md` (new), `window.py.md`, `compiled.py.md`, plus anchors that `check_code_notes.py --fix` moved. I re-anchored three ambiguous `mining_pass.py.md` anchors by hand (`learn_parameters` 180→181, `_one_pass` 495→499 and 525→529).

## Tests added

Unit tests (all written first and seen failing, then passing):
- `tests/unit/domain/test_tab_roles.py` — the brief's five tests, verbatim apart from formatting.
- `tests/unit/domain/test_compiling_a_job.py`:
  - `test_a_job_whose_doing_used_two_tabs_but_every_step_says_main_is_unlearned` (also checks that the same job with its roles learned is not flagged);
  - `test_a_step_in_a_tab_no_earlier_step_opened_is_unresolved` (also checks `view.steps[].tab`).
- `tests/unit/domain/rig/test_window.py::test_evidence_shows_the_tab_and_the_tabs_it_opened`: only `popup_opened` marks are listed.
- `tests/unit/application/rig/test_mine.py::test_a_doing_that_crossed_into_a_popup_is_kept_with_each_steps_tab`: a full pass stores `["main", "opened_from:main"]`.

Integration test, **written, not run**:
- `tests/integration/test_workflow_repositories.py::TestAStepNamesWhatItUses::test_a_steps_tab_survives_a_save`

## Gate results (from `backend/`)

- `uv run pytest tests/unit tests/contract -q`: **4651 passed**, 79 errors. The 79 are all Docker-bound. 78 are the `[sql]` parametrisations of `tests/contract/test_the_repositories_agree.py`, and 1 is `tests/contract/test_openapi.py::TestFuzz`. Each fails with `DockerException`, because this cloud session has no Docker. None of them is a failure.
- `uv run mypy src tests evals`: Success, no issues in 815 files. The two pre-existing errors the GC allows are gone on this tip.
- `uv run ruff check .` / `uv run ruff format --check .`: clean.
- `uv run lint-imports`: 4 kept, 0 broken.
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead.
- `grep -rn "unit_of_work()" backend/src/sro/interface/`: nothing.
- `frontend`: `npx tsc --noEmit` is clean.
- **LIVE EVAL** (the user runs it): `make eval suite=mining`. `as_evidence` changes the miner's input. `MINE`'s text, schema and model are unchanged, so its version is not bumped. Compare the report against the P3 baseline.

## Rulings

- Ruling: migration is `20260927_0086_a_step_knows_its_tab.py`, revision `0086`, down_revision `0085`, not the brief's `0079`/`0078` — the tip's head is `0085` (0078–0083 and 0085 are already taken; 0084 is absent) so 0086 is the next free number after it, per the brief's migration rule and GC 7 — cost if wrong: the controller renumbers at merge, as planned.
- Ruling: `MAIN` is defined once, in `domain/skill/workflow.py`, and re-exported from `domain/skill/tabs.py` (`__all__`). Every other caller imports it from `tabs`. The brief wanted it defined in `tabs.py`, but `Step.tab` defaults to `MAIN` and `tabs.py` imports `evidence.py` and `asked_by.py`. Both of those import `workflow.py`, so `workflow.py` importing from `tabs.py` is a real import cycle: importing `workflow` first fails. The code wins (Invariant 15). Cost if wrong: one line moves if a later task breaks the cycle another way.
- Ruling: `progress.py` no longer holds `MAIN` at all, not even as a re-import. `run_steps.py` and three tests now import it from `tabs.py`. After the change `progress.py` did not use `MAIN` itself, so a re-import was an unused import (ruff F401), and a re-export would have been a second public home for it. Cost if wrong: none, since the value and all users are unchanged.
- Ruling: in `tab_roles`, `elif parent is not None and parent in of_tab`, where the brief had `elif parent in of_tab`. mypy cannot narrow `int | None` through `in`, so this is typing only and behaves the same.
- Ruling: I added unit tests the brief does not list, for `as_evidence` and for the mining pass writing roles, and I updated `test_workflows_route.py`'s whole-wire fixture. The brief says every behaviour gets a failing test first, and the wire test asserts the exact step shape. Cost if wrong: extra tests only.

## Concerns

- **Worker restart needed.** Mining and compile both run in the worker, so this is not live until it restarts.
- The integration test and the migration were not run here, because there is no Postgres. The controller should run `tests/integration/test_workflow_repositories.py` and check `alembic heads` for a single head after renumbering.
- `tab_roles_unlearned` makes every two-tab job mined before this change unrunnable (not offered) until a mining pass grows it. The brief intends this, but the operator will see such jobs drop out of offers until they are re-mined.
- The runtime does not act on roles yet: `run_steps` still keeps only `progress.tabs[MAIN]`. Opening and switching tabs by role is T2's work, not this task's.
- The spec's ceiling applies: two popups opened from one role share a role name. This is noted in `tabs.py.md` together with its upgrade path.

---

## Round 1

### Commits

- `7049712` fix(tabs): undecided steps are backfilled by the sweep, and roles follow the doing
- (this report update) docs(t1): round 1 report

### Findings, and what was done

- **C1** `models.py`: `WorkflowStepRow.tab` has no Python-side default (and, per I3, no server default either), so an insert into a pre-0086 schema that names no tab sends no column. `_step_values` always sends `step.tab`. I can't run `test_0082_pins_every_steel_run_still_going_and_back` here. The unit probe `test_a_step_row_leaves_its_tab_to_the_caller` checks that a compiled insert naming no tab carries no `tab` param, and it failed before the fix.
- **I1** A pre-T1 pin (no `"tab"` on its steps) loads with `tab=None`, reads as `main` through `Step.role`, and `unresolved()` returns `[]`. Test: `test_a_pin_from_before_steps_knew_their_tab_reads_as_main`. See the Ruling below on why this is not `row.tab or MAIN`.
- **I2**
  - `with_field` copies `tab` from the step it is inserted before, the same neighbour it copies `system` from. Test: `test_a_composed_field_acts_in_the_tab_of_the_form_it_fills`.
  - `keeping_fields` gives a carried field step the tab of the step before it in the grown job, or `main` when it comes first. Test: `test_a_field_a_grown_job_carries_takes_the_tab_of_the_step_before_it`.
- **I3** Refusing until the job is relearned is gone. Instead:
  - **Migration:** `0086` adds `tab` as nullable with no default, so existing rows are NULL (undecided).
  - **Port:** gains `tabs_undecided()`, which returns live jobs with any NULL step, ordered like `undecided()`. It also gains `decide_tab(tenant_id, workflow_id, order, tab)`, a column-only update `WHERE tab IS NULL`, scoped to the tenant's job. Both are implemented in SQL and in the fake.
  - **Sweep:** `mining_pass.decide_tabs` runs `tab_roles` over `evidence_of(...)`. `MineLately._decide` runs it per tenant beside `decide_sign_ins`, under the same mining lock and in the same unit of work.
  - **Compile:** an undecided job gets the warning `tab_roles_undecided` and stays runnable. A decided job gets `tab_role_unresolved` per bad step. `tab_roles_unlearned` is deleted.
  - **Readers:** the wire and the compile view use `Step.role`.
  - **Tests:** the unit sweep test `test_a_quiet_sweep_decides_the_tab_of_every_step_stored_before_steps_knew_it`, the contract test `test_deciding_a_tab_sets_only_an_undecided_step_and_never_overwrites_one` (fake leg run; `[sql]` leg written, not run), and the compile test `test_a_job_whose_tabs_are_undecided_runs_with_a_warning`.
- **M1** Popup marks count only when `start <= mark.at <= end`, where the span runs from the doing's first acting gesture to its last. Test: `test_a_popup_mark_from_another_sitting_does_not_name_a_tab`.
- **M2** A step's gesture is its `primary_gesture`, and it counts only in the doing's stream and outside a mailbox. Test: `test_a_steps_tab_is_the_tab_of_its_primary_gesture_not_its_first_cite`.
- **M3** `opened` is omitted when empty. `MINE` is version 3, and its `input_contract` explains `tab` and `opened`. `test_the_rendered_mining_request_is_pinned` has its hash updated in the same commit as the version. The `"mine v2"` error-text asserts now read `"mine v3"`. Tests: `test_evidence_shows_the_tab_and_the_tabs_it_opened` and `test_the_miner_is_told_what_a_tab_and_an_opened_tab_are`. **LIVE EVAL**: `make eval suite=mining`, v3 against v2.
- **M4** `PageEventKind.POPUP_OPENED` is used in both `tabs.py` and `window.py`, and the `POPUP` constant is deleted. `window.py` no longer imports `tabs.py`.
- **M5** Tabs are named in the order of their first acting gesture's time.
  - `tab_N` is given only to a tab with no known opener on a system that an already-named tab is on. Test: `test_a_new_tab_on_another_system_with_no_opener_is_not_a_second_tab`.
  - A popup cited before its opener becomes `opened_from:main`, and `unresolved` flags it. Test: `test_a_popup_cited_before_its_opener_is_not_main`.
- **M8** Integration test `test_0086_leaves_every_stored_step_undecided_and_back`: an existing step is NULL after upgrade, a new row keeps its tab, and the downgrade drops the column. **Written, not run.**

### Tests added this round

Unit (all seen failing first, then passing):
- `test_tab_roles.py`:
  - `test_a_popup_mark_from_another_sitting_does_not_name_a_tab`
  - `test_a_steps_tab_is_the_tab_of_its_primary_gesture_not_its_first_cite`
  - `test_a_new_tab_on_another_system_with_no_opener_is_not_a_second_tab`
  - `test_a_popup_cited_before_its_opener_is_not_main`
  - `test_an_undecided_step_reads_as_main_and_resolves`
  - `test_a_field_a_grown_job_carries_takes_the_tab_of_the_step_before_it`
- `test_compiling_a_job.py::test_a_job_whose_tabs_are_undecided_runs_with_a_warning`, which replaces the `tab_roles_unlearned` test.
- `test_composing_a_field.py::test_a_composed_field_acts_in_the_tab_of_the_form_it_fills`
- `test_a_pin_outlives_a_dropped_column.py`:
  - `test_a_pin_from_before_steps_knew_their_tab_reads_as_main`
  - `test_a_step_row_leaves_its_tab_to_the_caller`
- `test_mine_lately.py::test_a_quiet_sweep_decides_the_tab_of_every_step_stored_before_steps_knew_it`
- `test_the_miner_reads_nothing_dead.py::test_the_miner_is_told_what_a_tab_and_an_opened_tab_are`
- `rig/test_window.py`: the existing tab test now also checks that `opened` is absent when empty.

Contract: `test_deciding_a_tab_sets_only_an_undecided_step_and_never_overwrites_one`. The `[fake]` leg was run; the `[sql]` leg is written, not run.

Integration, **written, not run**: `test_the_migrations_run.py::test_0086_leaves_every_stored_step_undecided_and_back`.

### Gate results

- `pytest tests/unit tests/contract`: **4663 passed**, 80 errors. All 80 are Docker-bound: the `[sql]` contract legs (one more than last round, the new CAS test) and `TestFuzz`. There is no Docker in this session.
- mypy `src tests evals`: clean. ruff check / format: clean. lint-imports: 4 kept. `check_code_notes.py`: 0 stale, 0 dead. The schema is unchanged in type, and the committed-schema contract test passes.
- `make eval-ci` exits "no committed cases under backend/evals/ci". That is a pre-existing state of the repo, not caused by this change.

### Rulings

- Ruling: `_row_to_step` keeps `tab=row.tab` (None stays None), and readers go through a new `Step.role` (`self.tab or MAIN`), rather than `tab=row.tab or MAIN` as I1 asked — I3 needs the domain to tell an undecided step from a decided `main` one: compile warns on undecided, and the sweep decides only NULL steps. Mapping NULL to `main` at the row boundary would erase exactly that. I1's behaviour (a pre-T1 pin reads as `main`, and `unresolved` does not raise) holds through `role` — cost if wrong: one line in `_row_to_step`, but then I3's warning and the sweep's domain view both go blind.
- Ruling: `Step.tab: str | None = MAIN`. The default stays `MAIN`, so every step code builds is decided, and `None` arises only from a pre-0086 row or pin. This means "new rows always write it": the only path that stores new jobs is mining, and it computes the roles — cost if wrong: a future job-creating path that forgets `tab_roles` would store `main` rather than undecided, and the sweep would not rescue it.
- Ruling: a new tab with no known opener on a system that no named tab is on gets no role of its own. Its steps keep the role of the step before them, so the run navigates there. M5 limits `tab_N` to a second tab of the same system and does not say what the other case is. This reuses the rule for a step with no gesture, instead of minting a fourth kind of role — cost if wrong: a job that needs two systems open side by side is run in one tab. It would then become a `tab_N`-style rule for other systems as well, a change confined to `tab_roles`.
- Ruling: the time span for M1 runs from the doing's first acting gesture to its last, inclusive, and is compared against `mark.at`. A popup opened after the last acting step can't be one the job acted in — cost if wrong: none for acting tabs.
- Ruling: `with_field` takes its tab from the step at `composed.before` (the same neighbour as `system`), falling back to `MAIN` when there is none. `compose` only ever places a field before an existing write, so the fallback is unreachable in practice.
- Ruling: `decide_tab` is scoped to the tenant through a sub-select on `workflows` (`workflow_id IN (SELECT id FROM workflows WHERE tenant_id = … AND id = …)`), because `workflow_steps` has no tenant column.
- Ruling: the per-tenant `_decide` loop now takes the union of tenants that have jobs undecided on sign-in or on tabs, instead of `groupby` over the sign-in list only. One lock and one unit of work cover both decisions, and the failure log names both.

### Concerns

- **Worker restart needed**: the sweep, mining and compile all run in the worker.
- Not run here (no Postgres): `test_0082_...` (C1), `test_0086_...` (M8), `test_workflow_repositories.py::...test_a_steps_tab_survives_a_save`, and the `[sql]` leg of the new contract test.
- The sweep decides from `evidence_of`. A job whose cited gestures are gone decides every NULL step as `main`, just as `_judged` decides `signs_in = false` without evidence.
- The runtime still acts only in `progress.tabs[MAIN]`. Acting by role is T2.
