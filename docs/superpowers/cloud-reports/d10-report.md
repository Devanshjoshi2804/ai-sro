# D10 report: runs stuck at "running" are closed honestly

Branch `d2/d10`, cut from `origin/feat/execution-runtime` at **`84d41633`** (`git merge-base --is-ancestor 339e0f13 HEAD` succeeds).

## Commits

- `5f65dc5` feat(runtime): close runs stuck at "running" honestly (D10)
- this report (next commit)

No migration. Every column the sweep needs (`outcome`, `finished_at`, `progress`, `awaiting`, `needs`, `executor`, `pinned`, `started_at`) already exists.

**Worker restart required:** the sweep runs in the worker's keeper loop (`keep_sessions_open`), so it is not live until the worker restarts (constraint 19).

## What it does

1. **Rule, in the domain:** `domain/execution/waiting.stuck(run, budget_s, now, durable)`.
   - If the run has ended, or Temporal says its workflow is `open`, it is not stuck, however late.
   - If Temporal says the workflow is `closed`, the run is stuck at once.
   - Otherwise (`unknown`: an extension run, or a workflow Temporal never heard of), the clock decides: `started_at + budget × max(1, items) + K_BUDGET_MARGIN_S` has passed, and the run is not waiting on a person. Waiting means `asks_a_person`, or any step with `verdict == "awaiting"` (an extension run parked on an approval).
2. **Port:** one method added to the existing `DurableExecution`: `run_state(run_id) -> Durably` (`"open" | "closed" | "unknown"`). The Temporal adapter calls `handle.describe()`: `RUNNING` is open, every other status is closed, and `NOT_FOUND` is unknown. No new port.
3. **Repository:** `WorkflowRunRepository.running()` (every tenant, oldest first) and `close_stuck(tenant_id, run_id, *, reason, at, was) -> bool`. It is one `UPDATE ... WHERE outcome='running' AND progress = :was RETURNING id` that sets `failed`, `finished_at`, and clears `awaiting` unless `needs` is set (as `finish` does). When it wins, the reason lands on the last step, or on a new step 0 if the run had none, the same as `fail_orphans`. Both the SQL and fake versions are included.
4. **Use case:** `application/execution/stuck_runs.CloseStuckRuns`. For each running row it recomputes the budget the way `start_on_steel` does (pinned job + cited evidence), asks the durable side (Steel only), and decides with `stuck`. It then closes the row by compare-and-set. **Only the winner** does the rest: on a Steel run it calls `RunSteps.release`, which closes the run's tab and ends a lease parked for this run; then it says one line to the operator. A failure on one row is logged and the loop moves to the next row.
5. **Wiring:** `Container.close_stuck_runs()`. The worker's `keep_sessions_open` pass runs it after expiring confirmations and **before** the session keeper's sweep, so a lease the closed run stopped beating is expired and its context closed in the same pass.

The reason text is used verbatim: "the run stopped responding and was closed after its time ran out". The operator's thread gets `"<job title> did not finish: <reason>."` with `decision={"kind": "note", "run_id": ...}`.

## Files changed

- `backend/src/sro/application/execution/stuck_runs.py` (new)
- `backend/src/sro/application/ports/durable.py`: `run_state`
- `backend/src/sro/application/ports/repositories.py`: `running`, `close_stuck`
- `backend/src/sro/container.py`: `close_stuck_runs`
- `backend/src/sro/domain/execution/waiting.py`: `STUCK`, `Durably`, `stuck`
- `backend/src/sro/infrastructure/db/workflow_runs.py`: `running`, `close_stuck`
- `backend/src/sro/infrastructure/temporal/durable.py`: `run_state`
- `backend/src/sro/infrastructure/temporal/worker.py`: the sweep in the keeper pass
- `backend/tests/unit/fakes.py`: `FakeWorkflowRunRepository.running` / `close_stuck`, and `FakeDurableExecution.run_state` + `ended`
- Tests (listed below) and `docs/code-notes/...` (the new `stuck_runs.py.md`, notes on every new function, the README index; `check_code_notes.py --fix` re-anchored the notes that moved).

No area owned by S2/S3/S4/F4 was edited: `run_steps.py` is called (`release`, and `finish` in tests), never changed.

## Tests added

Unit, all run and passing:

- `tests/unit/domain/test_a_run_that_stopped_responding.py` (7): the time rule, the budget per item, ended runs, the approval wait, the question wait, Temporal open, and Temporal closed while asking.
- `tests/unit/application/runtime/test_a_run_that_stopped_responding.py` (9). Every run here is **started through `StartWorkflowRun.execute` + `start_on_steel`** and driven by the real `RunSteps` over a real `SessionBroker`:
  - a run whose workflow timed out is closed with its reason and its step verdict, its **tab is closed**, and the thread gets one line;
  - a run parked on a one-time code has its **WAITING lease expired** and its tab closed;
  - a run Temporal never heard of is closed by the clock, exactly at `budget + margin` and not one second before;
  - a run still open in Temporal is left alone at ten times its time;
  - a run that finished normally is byte-for-byte untouched;
  - a run waiting on a question is not closed by the clock;
  - **race**: the real `finish` lands between the sweep's read and its CAS, so `finish` wins, no reason is written, and nothing is said;
  - **two sweeps at once** (both read the row before either closes it) close it once and say it once;
  - an extension run (started through `StartWorkflowRun` without Steel) past its time is closed without asking Temporal.
- `tests/unit/application/rig/test_runner.py::test_a_run_waiting_on_an_approval_is_never_closed_as_stuck`: an extension run parked on an approval through the real `run_workflow` survives a sweep 30 days later with no error logged, and the approval still lands (outcome `held`).
- `tests/unit/infrastructure/test_expired_cards_are_swept.py`: the sweep runs before the session sweep and its closed runs are logged; a failing sweep does not stop the keeper. The two existing call-order assertions were extended.

Mutation checks, each run by hand and then restored:

- Removing the "awaiting" exclusion fails the approval test.
- Removing the `RunSteps.release` call fails both release tests.
- Removing `outcome == 'running'` from the fake CAS fails the race test.
- Removing both CAS guards fails the race and two-sweeps tests.

The approval test first passed vacuously: the fixture's job belongs to another tenant, so the sweep raised `NotFound`. That exposed a real gap, now fixed with a floor budget, and the test now asserts no error was logged.

Contract (`tests/contract/test_the_repositories_agree.py`, fake half run and passing; **SQL half written, not run**):

- `running` lists every tenant's running rows, oldest first.
- `close_stuck` closes once, puts the reason on the last step (or on step 0), and clears `awaiting`.
- `close_stuck` leaves an ended row, a moved row (progress ≠ `was`) and another tenant's row alone.

Integration, **written, not run** (no Postgres or Temporal here):

- `tests/integration/test_workflow_run_repositories.py::TestStuckRuns`. The waits on the row lock use `pg_stat_activity`, not sleeps:
  - `test_a_finish_that_holds_the_row_wins_and_the_sweep_does_nothing`: `finish` holds the row lock, the sweep blocks on it, `finish` commits, and the sweep gets `False`.
  - `test_a_sweep_that_holds_the_row_wins_and_the_late_finish_cannot_rewrite_it`: the ENDED guard in `save`.
  - `test_two_sweeps_at_once_close_the_row_once`
  - `test_a_run_that_moved_since_the_sweep_read_it_is_not_closed`
- `tests/integration/test_run_workflow.py::test_the_durable_side_says_whether_a_run_s_workflow_is_still_open`: `run_state` goes from unknown to open to closed against real Temporal (terminate).

## Gate results (from `backend/`)

- `uv run pytest tests/unit -q -o faulthandler_timeout=120`: **4919 passed**
- `uv run pytest tests/contract -q -k "not sql"`: 107 passed, 1 error. The error is `test_openapi.py::TestFuzz`, which needs Docker (`DockerException`); it is environmental and not this change. The `[sql]` halves need Postgres and were not run.
- `uv run mypy src tests`: Success, no issues (836 files)
- `uv run ruff check .` / `uv run ruff format --check .`: clean
- `uv run lint-imports`: 4 contracts kept
- `grep -rn "unit_of_work()" src/sro/interface/`: nothing
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead
- No wire schema change, so `make types` was not needed.

## Rulings

- Ruling: the outcome is `failed`, not `timed_out`. `OUTCOMES` has no `timed_out`, and the console maps `failed` to "did not finish". Inventing one would need a check-constraint change and console work. Cost if wrong: a later migration and a relabel; rows closed until then read `failed` with the reason on their step.
- Ruling: "the lease and the Steel/browser session are released" means `RunSteps.release`, the activity the workflow itself runs last. It closes the run's tab through `SessionBroker.release` and expires a lease parked on a person for this run through `unpark`. `Browsers.release` is **not** called. A run never claims a `Browsers` session (that path is for recordings and self-heal), and the lease's Steel session is shared by the account's other runs; closing it would kill a sibling run. The account-level lease expires through the existing `ReleaseStrayBrowsers.expire_leases` once nothing beats it, and the sweep is ordered before it in the same pass. Cost if wrong: a stuck run's READY lease lives until its 2-minute TTL, which the keeper already reaps.
- Ruling: for a Steel run, Temporal is the authority whenever it answers. `open` is never closed, however late, since Temporal's `execution_timeout` is the same `budget + margin`. `closed` is closed at once, **even when the run is waiting on a question**, because the answer is a signal to a workflow that no longer exists. The "never close a waiting run" rule governs the clock (extension runs, and Steel runs Temporal cannot find). Cost if wrong: a waiting Steel run whose workflow was terminated is closed rather than left `running` for ever; the operator is told why.
- Ruling: a workflow Temporal has no record of (`NOT_FOUND`) is `unknown`, not closed, and the clock decides. The row is saved just before `start_workflow`, so treating "not found" as closed would race a starting run. Cost if wrong: a run whose handoff was lost waits out its budget + 10 minutes before closing.
- Ruling: any other Temporal error propagates. That row is skipped and logged for this pass, and the others proceed. Cost if wrong: during a Temporal outage no Steel row is closed until it is back.
- Ruling: the budget is recomputed with `run_budget` from the pinned job and its evidence, and multiplied by the number of things in a list run (`max(1, len(items))`). The budget was never stored, `run_budget` prices one pass of a job, and an extension list run does the job once per line; without the multiplier a long legitimate list run would be closed mid-flight. Cost if wrong: a list run's stuck row waits longer before closing.
- Ruling: if the job can no longer be found (retired, or an unpinned older row), the budget is `K_BUDGET_FLOOR_S` and the line says "A run" rather than raising. Raising would leave exactly the rows nothing else will ever close erroring on every pass. Cost if wrong: such a row closes sooner (floor + margin).
- Ruling: the compare-and-set also matches the `progress` the sweep read. A run whose progress moved since the read is alive, so the sweep does not close it. This mirrors `record_progress(was=...)`. Cost if wrong: none; the check can only make the sweep close less.
- Ruling: the reason lands on the run's last step, overwriting its verdict with `failed`/`none`, or on a new step 0. This is the house convention of `fail_orphans` and `StartWorkflowRun._close`, both tested ("the reason lands on the step the orphan died in"). A write that landed is still recorded as done in `progress.marks`, which is what replay reads. Cost if wrong: the audit shows `failed` on a step that had `held`; switching to an appended step is a one-function change.
- Ruling: there is no run-finished message path (`finish` only says `answered_elsewhere`), so the one line goes through `SayWhatHappened.execute` to the operator's current thread. That is the path every other run note (`run_asks`, needs, offers) takes. It is said only when `started_by` is set, and only by the sweep that won. Cost if wrong: if "the thread that started the run" must be a specific older thread, the line goes to the current one instead.
- Ruling: `awaiting` is cleared on close unless `needs` is set, mirroring `finish`, so a closed run does not go on claiming it is waiting on a mail thread.
- Ruling: the sweep rides the existing keeper loop (`session_sweep_seconds`, 600 s by default) rather than getting its own interval setting. There is no config for a constant, and it is placed before the keeper so released leases expire in the same pass.

## Concurrency story (invariant 12)

- **Two sweeps:** the second `UPDATE` waits on the first's row lock, then matches nothing (`outcome` is no longer `running`). Only the winner releases and speaks. This is tested in unit (both read first) and in integration.
- **`finish` vs sweep:** whichever commits first owns the row. `finish` first means the sweep's CAS matches nothing, so nothing is written, released or said. The sweep first means `finish`'s later `save` keeps the ended outcome (the ENDED guard in `save`), and `finish` does not reopen it. Both orders are tested in integration; the first is also tested in unit.
- **Crash between the CAS commit and the release:** the row is closed and the release never happens, and no later sweep retries it because the row is no longer running. The tab dies with its context when the keeper expires the unbeaten lease (TTL 2 minutes; a WAITING lease expires at its `until`, at most `K_CODE_WAIT` = 10 minutes).
- **Stop mid-way:** a stop cancels the workflow, whose cleanup runs `finish`/`release`. If that cleanup lands first, it wins; if the workflow dies without it, the sweep closes the run. The sweep never cancels anything.

## Concerns

- If an extension run's in-process loop is actually still alive past `budget × items + 10 minutes` and not parked on an approval (for example a very slow page), the sweep closes it. `run_workflow` then keeps driving the browser until its next `outcome != "running"` check, and its later saves cannot reopen the row (ENDED guard). The progress CAS does not catch this, because extension runs do not write `progress`. `run_budget` is generous (4× the demonstrated time + 60 s per step, floor 120 s), plus 10 minutes. The controller may want a heartbeat on extension runs later.
- `close_stuck` updates the last step by `max(ord)`. A stuck-but-alive Steel worker that later upserts a step at the same `ord` would overwrite the reason. This is the same exposure as `fail_orphans`.
- The integration tests and the `[sql]` contract halves were **written, not run**. Please run `tests/integration/test_workflow_run_repositories.py::TestStuckRuns`, `tests/integration/test_run_workflow.py::test_the_durable_side_says_whether_a_run_s_workflow_is_still_open`, and `tests/contract/test_the_repositories_agree.py -k "running or close_stuck"`.
- Cross-task (invariant 13): S4 touches `run_steps`. The sweep depends on `RunSteps.release` still (a) closing the tab and (b) unparking a WAITING lease when `outcome != "running"`, and on `finish` leaving an ended outcome alone. `tests/unit/application/runtime/test_a_run_that_stopped_responding.py` should be run after S4 merges.
