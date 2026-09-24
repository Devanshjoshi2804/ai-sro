# Notes for `backend/src/sro/infrastructure/temporal/durable.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/durable.py`](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L1): Docstring

> Temporal behind the ``DurableExecution`` port.
>
> The client connects lazily and is cached: building the container is synchronous,
> and a Temporal outage at boot must not stop the API from serving reads.

## `_root_message`, [line 126](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L126): Docstring

> The deepest message in a Temporal failure chain.
>
> Temporal wraps a failure once per layer it crossed, and every wrapper reads
> "Activity task failed". The message worth showing a supervisor is at the
> bottom: the reason the pair could not be induced.

## `_watch_id`, [line 134](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L134): Docstring

> One deadline per recording, addressable without storing a handle.

## `TemporalDurableExecution.__init__`, [line 37](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L37): Comment

Code: `self._address = address`

> Queues are overridable so a test can have its own. Two workers on one
> queue must be looking at the same data; a worker pointed at another
> database will happily accept the work and fail to find the recording.

## `TemporalDurableExecution.execute_skill`, [line 76](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L76): Comment

Code: `id=f"run-{skill_id}-{uuid.uuid4().hex[:8]}",`

> Unique per attempt: running the same skill again with the same
> parameters is a second, deliberate act -- not a duplicate to be
> folded into the first run's history.

## `TemporalDurableExecution.execute_skill`, [line 80](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L80): Comment

Code: `return run_id`

> Started, not finished. The caller named the run before it began
> precisely so it can watch the steps land instead of holding a
> request open for as long as the warehouse takes.

## `TemporalDurableExecution.watch_recording`, [line 111](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L111): Comment

Code: `logger.exception("could not start the session deadline for %s", recording_id)`

> Deliberately broad: the demonstration is already durable, and no
> scheduler problem is worth refusing to record a human's work.

## `TemporalDurableExecution.recording_finished`, [line 121](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L121): Comment

Code: `logger.debug("no session deadline to signal for %s", recording_id)`

> No deadline was running -- it was never started, or it already
> fired. Either way there is nothing to cancel.

## `_root_message`, [line 130](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L130): Comment

Code: `message = getattr(current, "message", None)`

> ApplicationError carries the original message without the class name
> str() would prepend; the supervisor reads this, not a Python type.
