# Notes for `backend/src/sro/infrastructure/temporal/durable.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/durable.py`](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L1): Docstring

> Temporal behind the ``DurableExecution`` port.
>
> The client connects lazily and is cached: building the container is synchronous,
> and a Temporal outage at boot must not stop the API from serving reads.

## `_root_message`, [line 79](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L79): Docstring

> The deepest message in a Temporal failure chain.
>
> Temporal wraps a failure once per layer it crossed, and every wrapper reads
> "Activity task failed". The message worth showing a supervisor is at the
> bottom: the reason the pair could not be induced.

## `TemporalDurableExecution.__init__`, [line 28](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L28): Comment

Code: `self._address = address`

> The queue is overridable so a test can have its own. Two workers on one
> queue must be looking at the same data; a worker pointed at another
> database will happily accept the work and fail to find the run.

## `TemporalDurableExecution.execute_skill`, [line 66](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L66): Comment

Code: `id=f"run-{skill_id}-{uuid.uuid4().hex[:8]}",`

> Unique per attempt: running the same skill again with the same
> parameters is a second, deliberate act -- not a duplicate to be
> folded into the first run's history.

## `TemporalDurableExecution.execute_skill`, [line 70](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L70): Comment

Code: `return run_id`

> Started, not finished. The caller named the run before it began
> precisely so it can watch the steps land instead of holding a
> request open for as long as the warehouse takes.

## `_root_message`, [line 83](../../../../../../../backend/src/sro/infrastructure/temporal/durable.py#L83): Comment

Code: `message = getattr(current, "message", None)`

> ApplicationError carries the original message without the class name
> str() would prepend; the supervisor reads this, not a Python type.
