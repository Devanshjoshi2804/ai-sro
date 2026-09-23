# Notes for `backend/src/sro/interface/http/errors.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/errors.py`](../../../../../../../backend/src/sro/interface/http/errors.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 48](../../../../../../../backend/src/sro/interface/http/errors.py#L48): Comment

Code: `DomainError: status.HTTP_422_UNPROCESSABLE_CONTENT,`

> The base case, so a domain error nobody mapped is still the request's
> fault rather than "Internal error". Asking for a field that has no list
> behind it answered 500 with the right sentence in it, which tells an
> operator to report an outage and a developer to look in the wrong place.

## module, [line 52](../../../../../../../backend/src/sro/interface/http/errors.py#L52): Comment

Code: `AskerUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,`

> Not a DomainError either, and the same shape as the two above: the
> request was fine and the deployment has no model to answer it with.
> Without its own entry the MRO walk finds nothing and it is a 500.

## module, [line 54](../../../../../../../backend/src/sro/interface/http/errors.py#L54): Comment

Code: `TargetUnreachable: status.HTTP_503_SERVICE_UNAVAILABLE,`

> The four port failures, on the same argument: the request was fine and a
> thing this deployment depends on is not answering. Every one of them was
> a 500 in `text/plain` until now, and the reason none of them had been
> noticed is that each is caught at every call site that exists TODAY --
> `UiUnavailable` was the exception that proved it, escaping
> `vision_step.py`'s one unguarded `perform_at` to `POST
> /v1/skills/{id}/batch`. Safety by review does not survive the next call
> site; these five lines make it safe by default instead.

## module, [line 58](../../../../../../../backend/src/sro/interface/http/errors.py#L58): Comment

Code: `DispatchFailed: status.HTTP_409_CONFLICT,`

> 409 and not 503, because it is not this deployment that is down: the
> other process refused or its laptop is closed, and the same tap succeeds
> when it opens. `AnswerConfirmation.approve` calls the same `start_for`
> that `FireTrigger` guards at `fire_trigger.py:143` and does not guard it,
> so tapping Approve on a card whose browser is away answered 500 in
> `text/plain` -- on the one door whose whole job is a person authorising
> an unattended write.

## module, [line 61](../../../../../../../backend/src/sro/interface/http/errors.py#L61): Comment

Code: `NotRunnable: status.HTTP_409_CONFLICT,`

> The durable path re-raises every refusal as NotRunnable, so without this
> a tripped circuit breaker reached the operator as a 500 -- "internal
> error" for the one outcome the system was most deliberate about.

## module, [line 63](../../../../../../../backend/src/sro/interface/http/errors.py#L63): Comment

Code: `ObservationRefused: status.HTTP_409_CONFLICT,`

> Not 403: the credential was fine and the request was well formed. The
> deployment has not agreed to store this, and that is state, not identity.

## module, [line 66](../../../../../../../backend/src/sro/interface/http/errors.py#L66): Comment

Code: `InboundRefused: status.HTTP_404_NOT_FOUND,`

> Vague on purpose: an unauthenticated caller with a wrong id and one with
> a wrong token must not be able to tell which they got wrong.

## module, [line 68](../../../../../../../backend/src/sro/interface/http/errors.py#L68): Comment

Code: `SignInFailed: status.HTTP_409_CONFLICT,`

> A login that did not complete is about the system's state, not the
> request's shape: a stale password, a second factor, a changed page. All
> of them are resolved by a human signing in once.

## module, [line 69](../../../../../../../backend/src/sro/interface/http/errors.py#L69): Comment

Code: `TokenRefused: status.HTTP_409_CONFLICT,`

> The identity provider's own answer, in its own words. "Invalid client"
> and "invalid_grant" want different people to do different things, and a
> 500 tells neither of them anything.

## module, [line 70](../../../../../../../backend/src/sro/interface/http/errors.py#L70): Comment

Code: `NotYours: status.HTTP_403_FORBIDDEN,`

> The caller is authenticated and the run exists; they are simply not the
> one person who saw what it produced. That is an identity mismatch, not a
> missing resource or a conflicting state.

## module, [line 71](../../../../../../../backend/src/sro/interface/http/errors.py#L71): Comment

Code: `NotYoursToRevise: status.HTTP_403_FORBIDDEN,`

> The same refusal on the sibling door that changes a run's values.
> A separate class with the same name, in a different module, and it
> was in neither this table nor the handler list -- so `/v1/runs/{id}/values`
> answered a wrong principal with a 500.

## module, [line 72](../../../../../../../backend/src/sro/interface/http/errors.py#L72): Comment

Code: `NotDrivingThisRun: status.HTTP_403_FORBIDDEN,`

> A browser reaching for a run some other browser is driving. Same shape as
> the entry above and the same 403: the credential was accepted and the
> browser proved it is itself, it is simply not the one that may answer for
> this run. A `DomainError`, so the handler registered below reaches it
> without being named -- which is the one way it differs from the two
> `NotYours` classes above, which are plain `Exception`s and had to be
> listed by name before their 403s could fire at all.

## module, [line 73](../../../../../../../backend/src/sro/interface/http/errors.py#L73): Comment

Code: `OfferRefused: status.HTTP_400_BAD_REQUEST,`

> The rig's own answer, kept: a body field naming a job that is not one is
> a bad request and never a missing endpoint. 400 rather than the 422 a
> malformed body gets, because the body parsed and its shape was right --
> what it named was not there.

## module, [line 74](../../../../../../../backend/src/sro/interface/http/errors.py#L74): Comment

Code: `RunRefused: status.HTTP_400_BAD_REQUEST,`

> The rig's 400 again, for the press: a `from_step` that is not a step of
> this job, or a declared parameter with no value, is a bad request about a
> body that parsed. Not a `DomainError`, so without this it is a 500.

## module, [line 75](../../../../../../../backend/src/sro/interface/http/errors.py#L75): Comment

Code: `OverCap: status.HTTP_429_TOO_MANY_REQUESTS,`

> Budget, not identity and not shape: the same request is accepted
> tomorrow or under a larger cap. 429 is the one status that means
> "later, not never".

## module, [line 97](../../../../../../../backend/src/sro/interface/http/errors.py#L97): Comment

Code: `status.HTTP_413_CONTENT_TOO_LARGE: "content_too_large",`

> The size belts on the two observation doors raise a bare `HTTPException`,
> so without this line both would answer `.../problems/error` and the title
> "Error" -- the locator that promises a page nobody can write, removed from
> this file once already.

## module, [line 98](../../../../../../../backend/src/sro/interface/http/errors.py#L98): Comment

Code: `status.HTTP_429_TOO_MANY_REQUESTS: "too_many_requests",`

> `OverCap` brings its own `code`, so this is not for it. It is for the
> bare 429 any future rate limiter raises: a hole in this table is how
> `problem.type` was `undefined` for every 401.

## `_status_for`, [line 105](../../../../../../../backend/src/sro/interface/http/errors.py#L105): Comment

Code: `for klass in type(exc).__mro__:`

> Walk the MRO so a new subclass of an already-mapped error inherits its
> status rather than silently becoming a 500.

## `_problem`, [line 161](../../../../../../../backend/src/sro/interface/http/errors.py#L161): Comment

Code: `"type": _problem_type(exc),`

> `about:blank` where an error carries no `code`, and not
> `.../problems/error`. RFC 9457 §3.1.1: when `type` is a locator,
> "dereferencing it should provide human-readable documentation for
> the problem type" -- so a URI under `/problems/` is a promise that
> this is a documented KIND of problem. `error` is not a kind; it is
> the absence of one, and pointing a locator at it promises a page
> that can never exist. The spec's own value for "adds no semantics
> beyond the status code" is `about:blank`, which is also what a
> consumer assumes when `type` is missing entirely.
>
> Every error in `_STATUS_BY_ERROR` carries a code today, so this
> branch is unreached by anything mapped -- it exists for the next
> error type somebody adds and forgets, and it should tell them
> nothing rather than tell them a lie.

## `install_error_handlers`, [line 231](../../../../../../../backend/src/sro/interface/http/errors.py#L231): Comment

Code: `SignInFailed,`

> Not a DomainError, so it needs saying: without this a failed login is
> a 500 and the operator is told nothing they can act on.

## `install_error_handlers`, [line 233](../../../../../../../backend/src/sro/interface/http/errors.py#L233): Comment

Code: `AskerUnavailable,`

> Neither is a DomainError, so neither is reached by the line above:
> without these two a route with no model answers 500, and a tenant
> at its cap is told the server broke.

## `install_error_handlers`, [line 235](../../../../../../../backend/src/sro/interface/http/errors.py#L235): Comment

Code: `TargetUnreachable,`

> None of the five is a `DomainError`, so the line above does not reach
> them and their entries in the table above would do nothing on their
> own. A status with no handler and a handler with no status are both
> a 500; two doors answered one for the life of this codebase because
> only one half was ever written.

## `install_error_handlers`, [line 240](../../../../../../../backend/src/sro/interface/http/errors.py#L240): Comment

Code: `RunRefused,`

> Neither is `OfferRefused`, which is a `DomainError` and is reached by
> the line above. This one is not, so it needs saying by name.

## `install_error_handlers`, [line 241](../../../../../../../backend/src/sro/interface/http/errors.py#L241): Comment

Code: `NotYours,`

> Neither is a `DomainError` either, and until this line their 403s
> above never fired: a caller who is not the person a run was
> performed for was told the server broke, in text/plain, on both
> `/v1/runs/{run_id}/wrong` and `/v1/runs/{run_id}/values`.
