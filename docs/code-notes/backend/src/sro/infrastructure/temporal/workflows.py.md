# Notes for `backend/src/sro/infrastructure/temporal/workflows.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/workflows.py`](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L1): Docstring

> Workflows: deterministic plans. No I/O, no clock, no randomness, no LLM.
>
> Everything effectful is an activity call. A workflow that read the database
> directly would replay differently after a restart and lose the durability that
> is the only reason Temporal is here.

## `RecordingSessionWorkflow`, [line 23](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L23): Docstring

> Watches one demonstration and reaps it if the operator walks away.
>
> The capture session itself lives in the API process, attached to CDP. What
> is durable here is the deadline: a browser session left open costs money and
> holds a scarce slot.

## `ExecutionWorkflow`, [line 64](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L64): Docstring

> Perform a skill, one step per activity.
>
> The step is the unit of durability because it is the unit of damage. If this
> process dies after step 7, the workflow resumes at step 8 -- and because the
> run already records step 7, an activity asked to repeat it returns what
> happened rather than doing it again.

## `TriggerWorkflow`, [line 112](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L112): Docstring

> One firing of one trigger.
>
> Thin on purpose: everything it could decide -- whether the trigger is still
> enabled, whether the skill still runs, whose authorisation applies -- is a
> fact about now, and a workflow replays. It asks once and reports what it was
> told.

## `ExecutionWorkflow.run`, [line 66](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L66): Docstring

> Returns the run id. What happened is on the run itself, which is the
> record everything else reads.

## module, [line 55](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L55): Comment

Code: `_READ_RETRY = RetryPolicy(`

> A read that failed to connect is worth another attempt. A write is not: the
> first attempt may have arrived, and the target system has no way to tell us.

## module, [line 58](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L58): Comment

Code: `non_retryable_error_types=["NotRunnable"],`

> A skill that may not be run is refused the same way every time.

## `ExecutionWorkflow.run`, [line 70](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L70): Comment

Code: `result_type=StartedRun,`

> Named activities carry no type information, so the converter
> hands back a dict unless the shape is stated here.

## `ExecutionWorkflow.run`, [line 81](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L81): Comment

Code: `index = 0`

> Positions rather than a count of steps: a skill whose body runs once
> per thing in a list does not know how long it is until the system
> answers, so how far to go is asked of each step rather than decided
> here. Determinism is unaffected -- what the activity answered is in
> the history, and a replay reads the same answers.

## `ExecutionWorkflow.run`, [line 93](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L93): Comment

Code: `retry_policy=_WRITE_RETRY,`

> Chosen per step: whether this one writes is known only after
> the first attempt, so the conservative policy applies to every
> step and the read-only ones lose a retry they rarely need.

## `ExecutionWorkflow.run`, [line 96](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L96): Comment

Code: `break`

> Later steps depend on this one having worked. Continuing would
> send calls built from values the system never returned.

## `TriggerWorkflow.run`, [line 119](../../../../../../../backend/src/sro/infrastructure/temporal/workflows.py#L119): Comment

Code: `retry_policy=RetryPolicy(maximum_attempts=1),`

> Started, not retried. A trigger that fired and whose run went bad
> has a run to look at; a second firing would be a second set of
> writes against the same records, minutes apart, with nobody there.
