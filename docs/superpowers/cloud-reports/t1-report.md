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
