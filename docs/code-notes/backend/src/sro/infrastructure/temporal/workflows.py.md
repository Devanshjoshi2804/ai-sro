# Notes for `backend/src/sro/infrastructure/temporal/workflows.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/workflows.py`](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L1): Docstring

> Workflows: deterministic plans. No I/O, no clock, no randomness, no LLM.
>
> Everything effectful is an activity call. A workflow that read the database
> directly would replay differently after a restart and lose the durability that
> is the only reason Temporal is here.

## `ExecutionWorkflow`, [line 45](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L45): Docstring

> Perform a skill, one step per activity.
>
> The step is the unit of durability because it is the unit of damage. If this
> process dies after step 7, the workflow resumes at step 8 -- and because the
> run already records step 7, an activity asked to repeat it returns what
> happened rather than doing it again.

## `TriggerWorkflow`, [line 93](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L93): Docstring

> One firing of one trigger.
>
> Thin on purpose: everything it could decide -- whether the trigger is still
> enabled, whether the skill still runs, whose authorisation applies -- is a
> fact about now, and a workflow replays. It asks once and reports what it was
> told.

## `ExecutionWorkflow.run`, [line 47](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L47): Docstring

> Returns the run id. What happened is on the run itself, which is the
> record everything else reads.

## module, [line 22](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L22): Comment

Code: `_READ_RETRY = RetryPolicy(`

> A read that failed to connect is worth another attempt. A write is not: the
> first attempt may have arrived, and the target system has no way to tell us.

## module, [line 25](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L25): Comment

Code: `non_retryable_error_types=["NotRunnable"],`

> A skill that may not be run is refused the same way every time.

## `ExecutionWorkflow.run`, [line 51](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L51): Comment

Code: `result_type=StartedRun,`

> Named activities carry no type information, so the converter
> hands back a dict unless the shape is stated here.

## `ExecutionWorkflow.run`, [line 62](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L62): Comment

Code: `index = 0`

> Positions rather than a count of steps: a skill whose body runs once
> per thing in a list does not know how long it is until the system
> answers, so how far to go is asked of each step rather than decided
> here. Determinism is unaffected -- what the activity answered is in
> the history, and a replay reads the same answers.

## `ExecutionWorkflow.run`, [line 74](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L74): Comment

Code: `retry_policy=_WRITE_RETRY,`

> Chosen per step: whether this one writes is known only after
> the first attempt, so the conservative policy applies to every
> step and the read-only ones lose a retry they rarely need.

## `ExecutionWorkflow.run`, [line 77](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L77): Comment

Code: `break`

> Later steps depend on this one having worked. Continuing would
> send calls built from values the system never returned.

## `TriggerWorkflow.run`, [line 100](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L100): Comment

Code: `retry_policy=RetryPolicy(maximum_attempts=1),`

> Started, not retried. A trigger that fired and whose run went bad
> has a run to look at; a second firing would be a second set of
> writes against the same records, minutes apart, with nobody there.

## module, [line 28](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L28): Note

Code: `_NEVER_AGAIN = ["NeedsAPerson", "WaitingForAPerson", "Stopped"]`

> Temporal matches an error by its class name, not its ancestry, so the
> subclass that parks on a one-time code is named as well.

## module, [line 29](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L29): Note

Code: `_STEP_RETRY = RetryPolicy(`

> A step retry is safe: `progress` guards every write, and a write already
> sent is only ever read back. Retried without an attempt limit, with
> backoff, because a busy account (another run's sign-in waiting on a
> person) and a Steel container coming back (`BrowserUnavailable`) clear by
> themselves; the run's budget (`execution_timeout`) bounds it.
> Ceiling: a step failing for good retries until the budget ends the
> workflow, and a timed-out workflow runs no `finish` or `release` (the
> lease expires by itself). Upgrade: a budget check inside the workflow.

## module, [line 35](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L35): Note

Code: `_QUEUE_RETRY = RetryPolicy(`

> `run.acquire` retries without limit on `PoolFull`: a run beyond capacity
> waits its turn (D8), inside its budget.

## `RunWorkflow`, [line 106](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L106): Class

> Every Steel run is one of these on `RUNS_QUEUE` (spec §7.2). It holds only
> ids, so it stays deterministic; every activity loads the run and its
> `progress`. `finish` and `release` run on every way out, a stop's
> cancellation included, after the step has recorded itself stopped
> (`WAIT_CANCELLATION_COMPLETED`). A step that asks ends the loop; D5 adds
> the wait for the answer. A code change is live only after the worker
> restarts (AGENTS.md).
