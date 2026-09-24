# Notes for `backend/src/sro/application/analytics/summary.py`

Comments and docstrings moved out of [`backend/src/sro/application/analytics/summary.py`](../../../../../../../backend/src/sro/application/analytics/summary.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/analytics/summary.py#L1): Docstring

> What the system has watched, noticed and done.
>
> Every number here is derived from rows somebody can open. Nothing is a counter
> kept alongside the truth and updated by hand -- a metric that can drift from what
> happened is worse than no metric, because it is believed.
>
> The runs are the mined jobs' runs (`workflow_runs`), counted by the outcome
> each one ended with -- the outcome the run itself recorded, not a second
> judgement made here. The old engine's `runs` table was read until 2026-09-24,
> and on a deployment whose work is all mined jobs it read zero.

## module, [line 11](../../../../../../../backend/src/sro/application/analytics/summary.py#L11): Note on the line above

Code: `MOST = 10`

> How many tasks the summary names. A list nobody scrolls is a list nobody
> reads.

## `Watching`, [line 19](../../../../../../../backend/src/sro/application/analytics/summary.py#L19): Note on the line above

Code: `hours: float`

> Hours of work observed. The span of the batches, not their number: an
> extension that uploads every minute would otherwise look like more work.

## `Noticing`, [line 25](../../../../../../../backend/src/sro/application/analytics/summary.py#L25): Note on the line above

Code: `by_kind: dict[str, int]`

> Create, Update, Read, Remove -- taken from the calls each task makes, not
> from anything a person filled in.

## `ReadSummary.execute`, [line 61](../../../../../../../backend/src/sro/application/analytics/summary.py#L61): Note

Code: `noticed = await uow.workflows.noticed_since(ctx.tenant_id, since=since)`

> The jobs mined inside the window, newest first, read without their steps
> (a count comes back instead). A job mined before the window is not "noticed"
> in it, and the list shows the latest jobs rather than the oldest ten.

## `kind_of`, [line 107](../../../../../../../backend/src/sro/application/analytics/summary.py#L107): Docstring

> The verb a mined title starts with. Any other title falls back to "other"
> rather than being guessed at.

## `TaskLine`, [line 37](../../../../../../../backend/src/sro/application/analytics/summary.py#L37): Comment

Code: `id: str`

> Two jobs can carry the same host and the same title. Without this the
> console keyed rows on host+title, React warned that it could drop
> one of them, and a reviewer had no way to tell the pair apart.

