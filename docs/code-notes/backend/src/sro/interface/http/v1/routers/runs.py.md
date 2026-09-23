# Notes for `backend/src/sro/interface/http/v1/routers/runs.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/runs.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/runs.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `run_skill`, [line 73](../../../../../../../../../backend/src/sro/interface/http/v1/routers/runs.py#L73): Comment

Code: `started = await container.execute_skill().begin(ctx, request)`

> Performed here rather than handed to the worker, because the browser
> this run needs is a laptop. Durability across a restart would mean
> resuming into a Chrome that may be closed, on a page that has moved,
> halfway through a task -- and a step that has already been recorded as
> sent must never be sent again to find out.
>
> Answered as soon as the row exists, though, rather than when the last
> step lands. A run in somebody's own browser is the one a person sits
> and watches, and they could not: the id arrived with the result, so
> `/runs/{id}/stream` had nothing to subscribe to until there was
> nothing left to see.

## `get_run`, [line 228](../../../../../../../../../backend/src/sro/interface/http/v1/routers/runs.py#L228): Comment

Code: `skills = await container.list_skills().execute(ctx, limit=_LIBRARY_PAGE)`

> Only a run that actually made something is a candidate for an undo --
> a failed run has nothing settled to take back, and computing this
> needs the tenant's whole skill library, which the list endpoint must
> not pay for on every row.
