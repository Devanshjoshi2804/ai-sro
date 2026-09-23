# Notes for `backend/src/sro/infrastructure/http/api_runs.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/http/api_runs.py`](../../../../../../../backend/src/sro/infrastructure/http/api_runs.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/http/api_runs.py#L1): Docstring

> Asking the process that holds a browser to run something.
>
> The channel to an operator's Chrome is held by whichever process the extension
> connected to, and the scheduler's worker is not that one. So a scheduled run
> bound to a device is *asked for* over the same public endpoint a person uses,
> with a short-lived credential minted for the trigger's own principal.
>
> Deliberately that endpoint and no other. An internal "send this browser a
> command" route would be a way to drive somebody's signed-in session anywhere,
> which no taught skill can do; this can only start a skill that was taught, with
> values a trigger already recorded.

## module, [line 17](../../../../../../../backend/src/sro/infrastructure/http/api_runs.py#L17): Note on the line above

Code: `CREDENTIAL_HOURS = 0.05`

> Three minutes. Long enough to make one call, short enough that a copy of it
> found in a log later is worth nothing.

## `_why`, [line 115](../../../../../../../backend/src/sro/infrastructure/http/api_runs.py#L115): Docstring

> The problem document's own sentence, when there is one. A status code on
> its own sends whoever reads the log to the wrong place.

## `ApiRunDispatcher.start_job`, [line 73](../../../../../../../backend/src/sro/infrastructure/http/api_runs.py#L73): Docstring

> `POST /v1/workflow-runs`, the same door the console's press uses.
>
> The job half of `start`, and it exists for the same reason: the socket
> to that Chrome is held by whichever process the extension connected to,
> and the scheduler's worker is not that one. Without this a scheduled
> job could only ever be skipped with "not connected", because the worker
> looks for the browser in its own empty register.
>
> `live=True` always. A dry run of a scheduled job sends nothing and
> verifies nothing -- it is a trigger that appears to work -- and what
> keeps a live one safe is not dryness but the ladder the run climbs: a
> write parks for a person until the job has earned the right.
>
> No `started_by` in the body, deliberately. The API reads the starter off
> the credential minted above, which is the trigger's own principal.

## `ApiRunDispatcher.start`, [line 50](../../../../../../../backend/src/sro/infrastructure/http/api_runs.py#L50): Comment

Code: `"authorized_by": ctx.principal_id.value if authorized_by else None,`

> The API turns this into the principal on the credential above --
> which is the trigger's authoriser, because that is who the
> credential was minted for.
