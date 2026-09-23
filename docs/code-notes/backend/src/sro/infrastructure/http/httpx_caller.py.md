# Notes for `backend/src/sro/infrastructure/http/httpx_caller.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/http/httpx_caller.py`](../../../../../../../backend/src/sro/infrastructure/http/httpx_caller.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/http/httpx_caller.py#L1): Docstring

> HttpCaller over httpx.

## `HttpxCaller.__init__`, [line 12](../../../../../../../backend/src/sro/infrastructure/http/httpx_caller.py#L12): Comment

Code: `self._client = client or httpx.AsyncClient(follow_redirects=False, cookies=None)`

> No cookie jar and no redirect following: a session the executor was
> not handed is a session it must not acquire, and a 302 on a mutation
> is a fact the run should record rather than chase.

## `HttpxCaller.send`, [line 37](../../../../../../../backend/src/sro/infrastructure/http/httpx_caller.py#L37): Comment

Code: `raise MalformedRequest(str(wrong) or type(wrong).__name__) from wrong`

> This end got it wrong: the URL a template rendered is not a URL,
> the scheme is one no client speaks, the request could not be
> framed. Separated from the network errors below because a step
> that failed here failed for a reason the skill owns, and letting
> it look like a closed laptop is how a broken skill stops being
> counted as broken. `InvalidURL` is not an `httpx.HTTPError` at
> all, so until now it escaped the executor and took the run with
> it rather than being recorded as a failed step.

## `HttpxCaller.send`, [line 39](../../../../../../../backend/src/sro/infrastructure/http/httpx_caller.py#L39): Comment

Code: `raise TargetUnreachable(str(error) or type(error).__name__) from error`

> httpx raises several of these with an empty message -- a read
> error carries nothing but its class -- and a run that failed with
> a blank reason costs an afternoon to attribute. The class name is
> not much, and it is the difference between "unreachable" and
> "nothing happened".
