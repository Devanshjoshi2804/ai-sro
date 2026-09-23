# Notes for `backend/src/sro/application/ports/http.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/http.py`](../../../../../../../backend/src/sro/application/ports/http.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/http.py#L1): Docstring

> The call the executor makes. Deliberately narrow.
>
> Nothing here follows redirects, retries, or reads a cookie jar. An executor that
> quietly retried a `PUT` would double a warehouse adjustment, and one that kept a
> cookie jar between runs would carry a session it was never given. Both are the
> caller's decisions, made where they can be recorded.

## `TargetUnreachable`, [line 31](../../../../../../../backend/src/sro/application/ports/http.py#L31): Docstring

> The system did not answer. Not a ``DomainError``: the plan was fine.
>
> Distinguished from an error status on purpose. A 422 proves the call
> arrived; a timeout leaves a mutation in an unknown state, and only the
> caller knows whether that is safe to retry.

## `MalformedRequest`, [line 35](../../../../../../../backend/src/sro/application/ports/http.py#L35): Docstring

> Nothing was sent, and the reason is this end rather than the far one.
>
> A URL a template rendered into something that is not a URL, a scheme no
> client speaks, a request the protocol will not frame. The system never had
> the chance to answer, but that is not a fact about the system: it is a fact
> about the skill, and a run that fails this way is evidence the recipe has
> drifted from what it was taught on.
>
> A subclass, so every caller that only wants "it did not answer" keeps
> working unchanged. Execution asks the narrower question in exactly one
> place -- where the difference decides whether the skill is marked down.

## `HttpCaller.send`, [line 20](../../../../../../../backend/src/sro/application/ports/http.py#L20): Docstring

> Send exactly this, once.
