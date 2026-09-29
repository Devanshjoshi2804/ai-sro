# Notes for `backend/src/sro/infrastructure/temporal/durable.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/durable.py`](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L1): Docstring

> Temporal behind the ``DurableExecution`` port.
>
> The client connects lazily and is cached: building the container is synchronous,
> and a Temporal outage at boot must not stop the API from serving reads.

## `_root_message`, [line 122](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L122): Docstring

> The deepest message in a Temporal failure chain.
>
> Temporal wraps a failure once per layer it crossed, and every wrapper reads
> "Activity task failed". The message worth showing a supervisor is at the
> bottom: the reason the pair could not be induced.

## `TemporalDurableExecution.__init__`, [line 35](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L35): Comment

Code: `self._address = address`

> The queue is overridable so a test can have its own. Two workers on one
> queue must be looking at the same data; a worker pointed at another
> database will happily accept the work and fail to find the run.

## `TemporalDurableExecution.execute_skill`, [line 73](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L73): Comment

Code: `id=f"run-{skill_id}-{uuid.uuid4().hex[:8]}",`

> Unique per attempt: running the same skill again with the same
> parameters is a second, deliberate act -- not a duplicate to be
> folded into the first run's history.

## `TemporalDurableExecution.execute_skill`, [line 77](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L77): Comment

Code: `return run_id`

> Started, not finished. The caller named the run before it began
> precisely so it can watch the steps land instead of holding a
> request open for as long as the warehouse takes.

## `_root_message`, [line 126](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L126): Comment

Code: `message = getattr(current, "message", None)`

> ApplicationError carries the original message without the class name
> str() would prepend; the supervisor reads this, not a Python type.

## `TemporalDurableExecution.start_run`, [line 87](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L87): Note

Code: `with contextlib.suppress(WorkflowAlreadyStartedError):`

> One workflow per run id, ever (`REJECT_DUPLICATE`): a second start --
> while it runs or after it ended -- starts nothing, so a finished run's
> remaining steps are never executed again. Starting a run is idempotent.
> Bounded by the job's budget plus `K_BUDGET_MARGIN_S`, a backstop only;
> the workflow keeps the budget itself (§7.5).

## `TemporalDurableExecution.cancel_run`, [line 107](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L107): Note

Code: `await (await self._connect()).get_workflow_handle(f"workflow-run-{run_id}").cancel()`

> The operator's stop. A cancel request through the server is the one signal
> `RunWorkflow` reads as a stop (`workflow.cancellation_reason()`); a heartbeat
> timeout or a worker shutdown never is.

## `TemporalDurableExecution.run_state`, [line 109](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L109): Note

> `describe` on the run's workflow id. `RUNNING` is open and every other
> status (completed, failed, cancelled, terminated, timed out) is closed. A
> workflow Temporal has no record of is `unknown`, not closed: a row is saved a
> moment before its workflow is started, and treating that gap as closed would
> close a run that is starting. Any other error propagates; the sweep logs it
> and tries again next pass.
