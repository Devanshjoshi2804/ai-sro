# Notes for `backend/src/sro/application/shared/refusals.py`

Comments and docstrings moved out of [`backend/src/sro/application/shared/refusals.py`](../../../../../../../backend/src/sro/application/shared/refusals.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/shared/refusals.py#L1): Docstring

> Refusals that are neither the caller's fault nor a dependency being down.

## `OverCap`, [line 4](../../../../../../../backend/src/sro/application/shared/refusals.py#L4): Docstring

> This tenant has spent what it may spend on models today.
>
> Not a ``DomainError``: nothing about the request is wrong, and it will be
> accepted again tomorrow or with a larger cap. 429 rather than 402 or 403 --
> the caller is being rate-limited by budget, and 429 is the one status whose
> meaning is "later, not never".
>
> Carries ``over_cap``'s own sentence unchanged. It names both numbers -- what
> was spent and what the cap is -- plus how many of the day's calls came back
> unpriced, because a day stopped by blindness and a day stopped by cost need
> different people to do different things.

## `RunRefused`, [line 12](../../../../../../../backend/src/sro/application/shared/refusals.py#L12): Docstring

> The press named something this job cannot be performed with.
>
> The rig's own 400, kept: the body parsed and its shape was right -- what it
> named was not a step of this job, or a value this job needs was not in it.
> Not a `DomainError`, for `OfferRefused`'s reason: a 422 is what a malformed
> body gets, and this body was not malformed.
>
> Never echoes a value out of the body. `str(exc)` becomes the `detail` of a
> problem document, and a refusal quoting the values writes a warehouse's own
> data into every access log between the browser and here.
>
> Lives beside `OverCap` rather than in `workflow_runs`, which re-exports it:
> `Converse` catches it when a yes is refused its start, and `workflow_runs`
> imports `announce`, which imports `converse` -- a cycle at import time.
