# Notes for `backend/src/sro/infrastructure/temporal/durable.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/durable.py`](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L1): Docstring

> Temporal behind the ``DurableExecution`` port.
>
> The client connects lazily and is cached: building the container is synchronous,
> and a Temporal outage at boot must not stop the API from serving reads.

## `_root_message`, [line 165](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L165): Docstring

> The deepest message in a Temporal failure chain.
>
> Temporal wraps a failure once per layer it crossed, and every wrapper reads
> "Activity task failed". The message worth showing a supervisor is at the
> bottom: the reason the pair could not be induced.

## `_watch_id`, [line 173](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L173): Docstring

> One deadline per recording, addressable without storing a handle.

## `TemporalDurableExecution.__init__`, [line 41](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L41): Comment

Code: `self._address = address`

> Queues are overridable so a test can have its own. Two workers on one
> queue must be looking at the same data; a worker pointed at another
> database will happily accept the work and fail to find the recording.

## `TemporalDurableExecution.induce_skill`, [line 75](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L75): Comment

Code: `id=f"induct-{first}-{second or 'alone'}-{uuid.uuid4().hex[:8]}",`

> Unique per attempt: re-inducing the same pair is a legitimate
> request that produces a new version, not a duplicate to fold
> into the previous run's history.

## `TemporalDurableExecution.induce_skill`, [line 79](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L79): Comment

Code: `raise InductionFailed(_root_message(exc)) from exc`

> The workflow marks a bad pair non-retryable. Unwrap it so the
> caller sees why induction was refused rather than the scheduler's
> own wrapper, which says only "Activity task failed".

## `TemporalDurableExecution.execute_skill`, [line 115](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L115): Comment

Code: `id=f"run-{skill_id}-{uuid.uuid4().hex[:8]}",`

> Unique per attempt: running the same skill again with the same
> parameters is a second, deliberate act -- not a duplicate to be
> folded into the first run's history.

## `TemporalDurableExecution.execute_skill`, [line 119](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L119): Comment

Code: `return run_id`

> Started, not finished. The caller named the run before it began
> precisely so it can watch the steps land instead of holding a
> request open for as long as the warehouse takes.

## `TemporalDurableExecution.watch_recording`, [line 150](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L150): Comment

Code: `logger.exception("could not start the session deadline for %s", recording_id)`

> Deliberately broad: the demonstration is already durable, and no
> scheduler problem is worth refusing to record a human's work.

## `TemporalDurableExecution.recording_finished`, [line 160](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L160): Comment

Code: `logger.debug("no session deadline to signal for %s", recording_id)`

> No deadline was running -- it was never started, or it already
> fired. Either way there is nothing to cancel.

## `_root_message`, [line 169](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L169): Comment

Code: `message = getattr(current, "message", None)`

> ApplicationError carries the original message without the class name
> str() would prepend; the supervisor reads this, not a Python type.
