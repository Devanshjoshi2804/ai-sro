# Notes for `backend/src/sro/domain/execution/progress.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/progress.py`](../../../../../../../backend/src/sro/domain/execution/progress.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 12](../../../../../../../backend/src/sro/domain/execution/progress.py#L12): Note on the line above

Code: `K_STEP_HEARTBEAT_S = 30`

> Spec §7.5, step activity: heartbeat timeout 30 s. A step activity must call
> back to Temporal within this window or the workflow treats it as dead and
> retries; the running step itself sees a stop request no later than its next
> heartbeat, so this is also the outer bound on how long "stop" takes to land.

## module, [line 13](../../../../../../../backend/src/sro/domain/execution/progress.py#L13): Note on the line above

Code: `K_STEP_LIMIT_S = 300`

> Spec §7.5, step activity: start-to-close 5 min. A single step -- one lane's
> attempt at one action, including its model call and its read-back -- that
> is still running after this is stuck rather than merely slow, and Temporal
> fails the activity rather than let a wedged step hold the run forever.

## module, [line 14](../../../../../../../backend/src/sro/domain/execution/progress.py#L14): Note on the line above

Code: `K_BEAT_EVERY_S = 10`

> A third of `K_STEP_HEARTBEAT_S`, not a value the spec names on its own: an
> activity that beats every 10 s has two heartbeats of margin before a slow
> tick trips the 30 s timeout, which is the gap a GC pause or a busy event
> loop actually costs.

## module, [line 15](../../../../../../../backend/src/sro/domain/execution/progress.py#L15): Note on the line above

Code: `K_BUDGET_FLOOR_S = 120`

> Spec §7.5, run: bounded by a per-job budget derived from the job's recorded
> durations. A one-step job demonstrated in five seconds still needs room for
> a lease acquire, a model call and a retry, so the derived budget never
> drops below this floor regardless of how quickly the operator moved.

## module, [line 16](../../../../../../../backend/src/sro/domain/execution/progress.py#L16): Note on the line above

Code: `K_BUDGET_PER_STEP_S = 60`

> Per-step overhead the demonstration's own timing cannot see: a lease
> acquire, a sight call, a write and its verification read each cost the
> executor time the operator's click never spent, added once per step on top
> of the scaled demonstrated span.

## module, [line 17](../../../../../../../backend/src/sro/domain/execution/progress.py#L17): Note on the line above

Code: `K_BUDGET_FACTOR = 4`

> The demonstrated span is a human's pace, not the executor's ceiling: sight
> calls, an expired lease's re-auth and a retried step all run slower than a
> practised operator's click-through, so the budget scales the demonstrated
> span by four rather than taking it at face value.

## `run_budget`, [line 99](../../../../../../../backend/src/sro/domain/execution/progress.py#L99): Docstring

> Derived from the demonstration because nothing else in a `Workflow` carries
> a duration -- it is a sequence of steps and cited gestures, not a timing.
> The recording that taught the job is the only account of how long a
> legitimate run of it takes, so the budget is read off the span between the
> earliest and latest cited gesture, in the order the steps use them, and
> never off a single constant that would starve a long job or over-allow a
> short one.
