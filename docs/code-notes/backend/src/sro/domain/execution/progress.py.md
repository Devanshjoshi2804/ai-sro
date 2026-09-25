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

## `Account`, [line 30](../../../../../../../backend/src/sro/domain/execution/progress.py#L30): Docstring

> Which account is driving the run, never what proves it. `origin` and
> `username` are the whole type -- not a `dict[str, str]` filtered at the
> edges, because a filter checked only on the way OUT (`as_json`, toward the
> row) can be skipped by whoever builds a `Progress` directly, and a filter
> checked only on the way IN (`Progress.of`, from the row) does nothing about
> what a caller writes. `Account` cannot hold a third key at all: the
> dataclass itself refuses `Account(origin=..., username=..., password=...)`
> with a `TypeError`, before a value the type disallows is ever assigned to
> anything, so a password or a session cookie can never reach a
> `workflow_runs` row, a log, or evidence through this field. Global
> constraint 10 -- a credential lives in the vault only.

## `Progress.account`, [line 42](../../../../../../../backend/src/sro/domain/execution/progress.py#L42): Comment

Code: `account: Account = field(default_factory=Account)`

> Typed, not filtered: see `Account`.

## `Progress.of`, [line 47](../../../../../../../backend/src/sro/domain/execution/progress.py#L47): Docstring

> Raises on a malformed row rather than reading it as empty. `step` that is
> not an integer, or a mark keyed by something that is not a step order,
> fails loudly here -- because reading either as "no progress yet" would
> restart a retried activity from step zero and resend every write it had
> already made. An unrecognised `wrote` value is the one exception: `_wrote`
> drops it to `""` rather than raising, since it names a state this code
> never wrote and the safest reading of an unknown mark is "not sent".

## `Progress.settle`, [line 78](../../../../../../../backend/src/sro/domain/execution/progress.py#L78): Docstring

> `done` is sticky: both `sending` and `settle` return before touching a mark
> already `done`, so nothing after the write was confirmed -- a retried
> activity, a late `failed` from an abandoned verification read -- can un-send
> it. A verdict of `failed` on a write that was `sending` is never read as
> "safe to retry" on its own: the lane may have submitted the form before it
> lost the page, so the mark becomes `unknown` unless the caller can say,
> with `never_left=True`, that this specific attempt is confirmed never to
> have left -- the one case narrow enough to clear it outright.

## `run_budget`, [line 122](../../../../../../../backend/src/sro/domain/execution/progress.py#L122): Docstring

> Derived from the demonstration because nothing else in a `Workflow` carries
> a duration -- it is a sequence of steps and cited gestures, not a timing.
> The recording that taught the job is the only account of how long a
> legitimate run of it takes, so the budget is read off the span between the
> earliest and latest cited gesture, in the order the steps use them, and
> never off a single constant that would starve a long job or over-allow a
> short one.
>
> ponytail: `shown` is the raw span, idle time included -- a recording with a
> multi-hour pause between two cited gestures yields a budget of the same
> order. Trim idle gaps out of `shown`, or cap it outright, once a real job's
> demonstrated pause makes a run's budget meaningless.

## `Progress`, [line 44](../../../../../../../backend/src/sro/domain/execution/progress.py#L44): Note

Code: `asking: dict[str, str] = field(default_factory=dict)`

> The question a step stands on (`id`, `kind`, `text`), written by D2 when
> no lane can do the step and read by D5 when the answer comes.
