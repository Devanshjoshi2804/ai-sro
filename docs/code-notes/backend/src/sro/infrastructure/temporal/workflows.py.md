# Notes for `backend/src/sro/infrastructure/temporal/workflows.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/workflows.py`](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L1): Docstring

> Workflows: deterministic plans. No I/O, no clock, no randomness, no LLM.
>
> Everything effectful is an activity call. A workflow that read the database
> directly would replay differently after a restart and lose the durability that
> is the only reason Temporal is here.

## `ExecutionWorkflow`, [line 60](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L60): Docstring

> Perform a skill, one step per activity.
>
> The step is the unit of durability because it is the unit of damage. If this
> process dies after step 7, the workflow resumes at step 8 -- and because the
> run already records step 7, an activity asked to repeat it returns what
> happened rather than doing it again.

## `TriggerWorkflow`, [line 108](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L108): Docstring

> One firing of one trigger.
>
> Thin on purpose: everything it could decide -- whether the trigger is still
> enabled, whether the skill still runs, whose authorisation applies -- is a
> fact about now, and a workflow replays. It asks once and reports what it was
> told.

## `ExecutionWorkflow.run`, [line 62](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L62): Docstring

> Returns the run id. What happened is on the run itself, which is the
> record everything else reads.

## module, [line 25](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L25): Comment

Code: `_READ_RETRY = RetryPolicy(`

> A read that failed to connect is worth another attempt. A write is not: the
> first attempt may have arrived, and the target system has no way to tell us.

## module, [line 28](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L28): Comment

Code: `non_retryable_error_types=["NotRunnable"],`

> A skill that may not be run is refused the same way every time.

## `ExecutionWorkflow.run`, [line 66](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L66): Comment

Code: `result_type=StartedRun,`

> Named activities carry no type information, so the converter
> hands back a dict unless the shape is stated here.

## `ExecutionWorkflow.run`, [line 77](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L77): Comment

Code: `index = 0`

> Positions rather than a count of steps: a skill whose body runs once
> per thing in a list does not know how long it is until the system
> answers, so how far to go is asked of each step rather than decided
> here. Determinism is unaffected -- what the activity answered is in
> the history, and a replay reads the same answers.

## `ExecutionWorkflow.run`, [line 89](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L89): Comment

Code: `retry_policy=_WRITE_RETRY,`

> Chosen per step: whether this one writes is known only after
> the first attempt, so the conservative policy applies to every
> step and the read-only ones lose a retry they rarely need.

## `ExecutionWorkflow.run`, [line 92](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L92): Comment

Code: `break`

> Later steps depend on this one having worked. Continuing would
> send calls built from values the system never returned.

## `TriggerWorkflow.run`, [line 115](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L115): Comment

Code: `retry_policy=RetryPolicy(maximum_attempts=1),`

> Started, not retried. A trigger that fired and whose run went bad
> has a run to look at; a second firing would be a second set of
> writes against the same records, minutes apart, with nobody there.

## module, [line 31](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L31): Note

Code: `_NEVER_AGAIN = ["NeedsAPerson", "WaitingForAPerson", "Stopped"]`

> Temporal matches an error by its class name, not its ancestry, so the
> subclass that parks on a one-time code is named as well. `Superseded` (an
> attempt that lost the run to another) is left out on purpose: the retry
> reads what the winner recorded.

## module, [line 32](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L32): Note

Code: `_STEP_RETRY = RetryPolicy(`

> A step retry is safe: `progress` guards every write, and a write already
> marked is only ever read back. Retried without an attempt limit, with
> backoff, because a busy account (another run's sign-in waiting on a
> person) and a Steel container coming back (`BrowserUnavailable`) clear by
> themselves. Bounded by the run's own deadline (`schedule_to_close`), never
> by the workflow timeout, so `finish` and `release` still run.

## module, [line 38](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L38): Note

Code: `_QUEUE_RETRY = RetryPolicy(`

> `run.acquire` retries without limit on `PoolFull`: a run beyond capacity
> waits its turn (D8), inside its budget.

## module, [line 44](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L44): Note

Code: `_PREPARE_RETRY = RetryPolicy(`

> A person-needed failure at prepare is asked, never retried.

## `RunWorkflow`, [line 121](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L121): Class

> Every Steel run is one of these on `RUNS_QUEUE` (spec §7.2). It holds only
> ids and its budget, so it stays deterministic; every activity loads the run
> and its `progress`. `finish` and `release` run on every way out: a stop
> (after the running activity has wound down, `WAIT_CANCELLATION_COMPLETED`),
> a failure, and the budget running out. A question at prepare, acquire or a
> step lets go of the browser and waits for the answer (`_answered`), then the
> run is prepared and acquired again and carries on from the step that asked,
> never from step 0. A code change is live
> only after the worker restarts (AGENTS.md).
>
> The patching rule. A run paused across a deploy (waiting on an answer,
> parked on a code, mid-retry) is replayed against the new code, and a
> replay that issues different commands fails the run. So any change to
> this workflow's commands -- activity order or names, timers, signals,
> waits -- goes behind `workflow.patched("<id>")`, and the old branch stays
> until no history still in flight needs it (then `deprecate_patch`, then
> delete). `tests/replay` proves it: every history in
> `tests/replay/histories` replays on the current code in `make test` and
> CI. After a change, `make record-histories` (real Temporal, `make up`)
> adds the new shape's histories next to the old ones; delete an old one
> only together with the branch it keeps.
> A set (files keyed by one hash of `RunWorkflow`'s source) can be deleted
> once no deployed worker could still hold a run recorded under it. Reordering `finish` and
> `release` without a patch fails all 17 recorded histories; the same
> reorder behind `patched()` replays clean.

## `RunWorkflow.run`, [line 127](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L127): Note

Code: `deadline = workflow.info().start_time + timedelta(seconds=ref.budget_s)`

> The run's budget is kept in workflow time, so it is deterministic and
> survives a worker restart. `execution_timeout` is only a backstop past it:
> a workflow Temporal times out runs no `finish` and no `release`.

## `RunWorkflow._driven`, [line 213](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L213): Note

Code: `schedule_to_close_timeout=max(deadline - workflow.now(), _AT_LEAST),`

> Acquire and each step get whatever is left of the budget, across all their
> retries; both heartbeat, so a stop reaches them and is waited for.

## `RunWorkflow._answered`, [line 170](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L170): Note

Code: `lambda: asking in self._answers, timeout=max(deadline - workflow.now(), _AT_LEAST)`

> The wait for an answer is bounded by what is left of the run's budget; a
> question nobody answers in time ends the run like the budget running out,
> through `finish` and `release`. A stop during the wait cancels the wait,
> and `run` catches that cancel like any other stop: the run is recorded
> aborted, then `finish` and `release` run, and `release` ends the run's own
> park.

## `RunWorkflow.run`, [line 150](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L150): Note

Code: `if workflow.cancellation_reason() is not None:`

> Only the operator's cancel (`cancel_run`) records the run as stopped; a
> budget running out or a failed activity is no stop, and `finish` decides
> those. By now the running step has finished its current primitive
> (`WAIT_CANCELLATION_COMPLETED`), because a click already dispatched cannot
> be recalled. `finish` and `release` then run through `_cleanup`, which a
> cancel can never skip.

## `RunWorkflow._driven`, [line 219](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L219): Note

Code: `if workflow.cancellation_reason() is not None:`

> A stop that lands while acquire or a step is finishing is not lost. With
> `WAIT_CANCELLATION_COMPLETED`, an activity that completes before its next
> heartbeat carries the cancel returns its result and the workflow's
> cancellation is spent; without this check the next step would run, and
> could send a write, after the operator stopped the run.

## `RunWorkflow._cleanup`, [line 187](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L187): Note

Code: `async def _cleanup(self, ref: RunRef, name: str) -> None:`

> The operator's Stop never cancels its own cleanup. Temporal delivers a
> workflow's cancel once, to whatever it is awaiting (asyncio rules, SDK
> README "Asyncio Cancellation"); when that is `finish` or `release`, the
> cancel is caught here, the stop is recorded, and the same activity is
> scheduled again, which no cancel reaches any more. An attempt the cancel
> cut short may still land later; outcome writes are compare-and-set
> (`ENDED`), so it cannot reopen the run.

## module, [line 49](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L49): Note

Code: `_UNTIL_RECORDED = RetryPolicy(`

> `run.stopped` is retried until it lands: if it gave up, its error would
> replace the cancel and `finish` would derive `held` or `failed` for a run
> the operator stopped. `Stopped` (the run is unknown) is the one answer not
> retried. Ceiling: a database that never comes back holds the workflow
> until `execution_timeout`.
