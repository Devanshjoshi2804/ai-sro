# Notes for `backend/src/sro/infrastructure/temporal/workflows.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/workflows.py`](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L1): Docstring

> Workflows: deterministic plans. No I/O, no clock, no randomness, no LLM.
>
> Everything effectful is an activity call. A workflow that read the database
> directly would replay differently after a restart and lose the durability that
> is the only reason Temporal is here.

## `ExecutionWorkflow`, [line 51](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L51): Docstring

> Perform a skill, one step per activity.
>
> The step is the unit of durability because it is the unit of damage. If this
> process dies after step 7, the workflow resumes at step 8 -- and because the
> run already records step 7, an activity asked to repeat it returns what
> happened rather than doing it again.

## `TriggerWorkflow`, [line 99](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L99): Docstring

> One firing of one trigger.
>
> Thin on purpose: everything it could decide -- whether the trigger is still
> enabled, whether the skill still runs, whose authorisation applies -- is a
> fact about now, and a workflow replays. It asks once and reports what it was
> told.

## `ExecutionWorkflow.run`, [line 53](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L53): Docstring

> Returns the run id. What happened is on the run itself, which is the
> record everything else reads.

## module, [line 22](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L22): Comment

Code: `_READ_RETRY = RetryPolicy(`

> A read that failed to connect is worth another attempt. A write is not: the
> first attempt may have arrived, and the target system has no way to tell us.

## module, [line 25](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L25): Comment

Code: `non_retryable_error_types=["NotRunnable"],`

> A skill that may not be run is refused the same way every time.

## `ExecutionWorkflow.run`, [line 57](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L57): Comment

Code: `result_type=StartedRun,`

> Named activities carry no type information, so the converter
> hands back a dict unless the shape is stated here.

## `ExecutionWorkflow.run`, [line 68](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L68): Comment

Code: `index = 0`

> Positions rather than a count of steps: a skill whose body runs once
> per thing in a list does not know how long it is until the system
> answers, so how far to go is asked of each step rather than decided
> here. Determinism is unaffected -- what the activity answered is in
> the history, and a replay reads the same answers.

## `ExecutionWorkflow.run`, [line 80](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L80): Comment

Code: `retry_policy=_WRITE_RETRY,`

> Chosen per step: whether this one writes is known only after
> the first attempt, so the conservative policy applies to every
> step and the read-only ones lose a retry they rarely need.

## `ExecutionWorkflow.run`, [line 83](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L83): Comment

Code: `break`

> Later steps depend on this one having worked. Continuing would
> send calls built from values the system never returned.

## `TriggerWorkflow.run`, [line 106](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L106): Comment

Code: `retry_policy=RetryPolicy(maximum_attempts=1),`

> Started, not retried. A trigger that fired and whose run went bad
> has a run to look at; a second firing would be a second set of
> writes against the same records, minutes apart, with nobody there.

## module, [line 28](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L28): Note

Code: `_NEVER_AGAIN = ["NeedsAPerson", "WaitingForAPerson", "Stopped"]`

> Temporal matches an error by its class name, not its ancestry, so the
> subclass that parks on a one-time code is named as well. `Superseded` (an
> attempt that lost the run to another) is left out on purpose: the retry
> reads what the winner recorded.

## module, [line 29](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L29): Note

Code: `_STEP_RETRY = RetryPolicy(`

> A step retry is safe: `progress` guards every write, and a write already
> marked is only ever read back. Retried without an attempt limit, with
> backoff, because a busy account (another run's sign-in waiting on a
> person) and a Steel container coming back (`BrowserUnavailable`) clear by
> themselves. Bounded by the run's own deadline (`schedule_to_close`), never
> by the workflow timeout, so `finish` and `release` still run.

## module, [line 35](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L35): Note

Code: `_QUEUE_RETRY = RetryPolicy(`

> `run.acquire` retries without limit on `PoolFull`: a run beyond capacity
> waits its turn (D8), inside its budget.

## module, [line 41](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L41): Note

Code: `_PREPARE_RETRY = RetryPolicy(`

> A person-needed failure at prepare is asked, never retried.

## `RunWorkflow`, [line 112](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L112): Class

> Every Steel run is one of these on `RUNS_QUEUE` (spec §7.2). It holds only
> ids and its budget, so it stays deterministic; every activity loads the run
> and its `progress`. `finish` and `release` run on every way out: a stop
> (after the running activity has wound down, `WAIT_CANCELLATION_COMPLETED`),
> a failure, and the budget running out. A question at prepare, acquire or a
> step ends the loop; D5 adds the wait for the answer. A code change is live
> only after the worker restarts (AGENTS.md).

## `RunWorkflow.run`, [line 115](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L115): Note

Code: `deadline = workflow.info().start_time + timedelta(seconds=ref.budget_s)`

> The run's budget is kept in workflow time, so it is deterministic and
> survives a worker restart. `execution_timeout` is only a backstop past it:
> a workflow Temporal times out runs no `finish` and no `release`.

## `RunWorkflow._driven`, [line 155](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L155): Note

Code: `schedule_to_close_timeout=max(deadline - workflow.now(), _AT_LEAST),`

> Acquire and each step get whatever is left of the budget, across all their
> retries; both heartbeat, so a stop reaches them and is waited for.
