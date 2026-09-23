# Notes for `backend/src/sro/application/analytics/summary.py`

Comments and docstrings moved out of [`backend/src/sro/application/analytics/summary.py`](../../../../../../../backend/src/sro/application/analytics/summary.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/analytics/summary.py#L1): Docstring

> What the system has watched, noticed and done.
>
> Every number here is derived from rows somebody can open. Nothing is a counter
> kept alongside the truth and updated by hand -- a metric that can drift from what
> happened is worse than no metric, because it is believed.
>
> The run outcomes are judged with ``judge``, the same function that classified
> each run when it finished. A screen that scored runs its own way would sooner or
> later disagree with the promotion ladder, and then two things in the same
> building would be saying different words about the same afternoon.

## module, [line 14](../../../../../../../backend/src/sro/application/analytics/summary.py#L14): Note on the line above

Code: `MOST = 10`

> How many tasks the summary names. A list nobody scrolls is a list nobody
> reads.

## `Watching`, [line 22](../../../../../../../backend/src/sro/application/analytics/summary.py#L22): Note on the line above

Code: `hours: float`

> Hours of work observed. The span of the batches, not their number: an
> extension that uploads every minute would otherwise look like more work.

## `Noticing`, [line 31](../../../../../../../backend/src/sro/application/analytics/summary.py#L31): Note on the line above

Code: `by_kind: dict[str, int]`

> Create, Update, Read, Remove -- taken from the calls each task makes, not
> from anything a person filled in.

## `Doing`, [line 41](../../../../../../../backend/src/sro/application/analytics/summary.py#L41): Note on the line above

Code: `unreachable: int`

> Runs that never reached the system they were aiming at. Its own number
> because it is neither a success nor a fault, and folding it into either
> would make a week of closed laptops read as a week of a broken skill.

## `kind_of`, [line 165](../../../../../../../backend/src/sro/application/analytics/summary.py#L165): Docstring

> The verb a mined title starts with. Any other title falls back to "other"
> rather than being guessed at.

## `TaskLine`, [line 49](../../../../../../../backend/src/sro/application/analytics/summary.py#L49): Comment

Code: `id: str`

> Two jobs can carry the same host and the same title. Without this the
> console keyed rows on host+title, React warned that it could drop
> one of them, and a reviewer had no way to tell the pair apart.

