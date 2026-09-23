# Notes for `backend/src/sro/domain/execution/safety.py`

Comments and docstrings moved out of [`backend/src/sro/domain/execution/safety.py`](../../../../../../../backend/src/sro/domain/execution/safety.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/safety.py#L1): Docstring

> What stops a run before it starts.
>
> Two limits, both computed from what recent runs actually did rather than from a
> counter somebody has to remember to increment. Derived state cannot drift from
> the thing it describes, and a restart cannot lose it.
>
> Both fail *closed to a human*: the answer is never "retry harder", it is "a
> person decides now". Retrying into a system that is already failing is how a
> degraded WMS becomes an unavailable one.

## module, [line 7](../../../../../../../backend/src/sro/domain/execution/safety.py#L7): Note on the line above

Code: `FAILURE_WINDOW = timedelta(minutes=15)`

> How far back the breaker looks. Long enough to see a pattern, short enough
> that a system which has recovered is usable again without an intervention.

## module, [line 9](../../../../../../../backend/src/sro/domain/execution/safety.py#L9): Note on the line above

Code: `TRIP_AFTER = 3`

> Failed runs against one system inside the window. Deliberately small: the
> third consecutive failure is not bad luck, and the fourth attempt is the one
> that turns an outage into an incident.

## module, [line 12](../../../../../../../backend/src/sro/domain/execution/safety.py#L12): Note on the line above

Code: `MAX_WRITES_PER_WINDOW = 60`

> Blast radius. A skill looping on a scheduler can do more damage in an hour
> than any single wrong write, and no legitimate operator-driven workload here
> needs more than one write a minute sustained.

## module, [line 14](../../../../../../../backend/src/sro/domain/execution/safety.py#L14): Note on the line above

Code: `MAX_ITEMS_PER_BATCH = 25`

> A batch bigger than this is a migration, and a migration is somebody's
> decision rather than a chat message.

## `RunFact`, [line 23](../../../../../../../backend/src/sro/domain/execution/safety.py#L23): Docstring

> The little a safety decision needs to know about a past run.

## `assess`, [line 39](../../../../../../../backend/src/sro/domain/execution/safety.py#L39): Docstring

> Whether another run against this system may start.
