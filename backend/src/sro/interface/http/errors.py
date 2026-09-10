"""Domain errors to RFC 9457 problem details, in one place.

Routers never catch domain errors. If a use case raises, the mapping happens
here, so every endpoint reports the same failure the same way.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from sro.application.connection.connect_system import NotAuthenticated
from sro.application.connection.sign_in import NoCredentials
from sro.application.execution.call_run_wrong import NotYours
from sro.application.execution.execute_skill import NotRunnable, Refused
from sro.application.execution.revise_run import NotYours as NotYoursToRevise
from sro.application.execution.workflow_runs import NotDrivingThisRun, RunRefused
from sro.application.induction.errors import InductionFailed
from sro.application.observation.ingest import ObservationRefused
from sro.application.observation.teach import NothingToTeach
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.dispatch import DispatchFailed
from sro.application.ports.http import TargetUnreachable
from sro.application.ports.model import AskerUnavailable
from sro.application.ports.schedule import SchedulerUnavailable
from sro.application.ports.sign_in import SignInFailed
from sro.application.ports.token import TokenRefused
from sro.application.ports.tools import ToolsUnavailable
from sro.application.ports.ui import UiUnavailable
from sro.application.ports.vault import VaultUnavailable
from sro.application.ports.vision import VisionUnavailable
from sro.application.recording.start_recording import NoSessionForSystem
from sro.application.shared.refusals import OverCap
from sro.application.skill.record_offer import OfferRefused
from sro.application.trigger.create_trigger import TriggerRefused
from sro.application.trigger.receive_inbound import InboundRefused
from sro.domain.shared.errors import Conflict, DomainError, InvariantViolation, NotFound

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    NotFound: status.HTTP_404_NOT_FOUND,
    Conflict: status.HTTP_409_CONFLICT,
    InvariantViolation: status.HTTP_422_UNPROCESSABLE_CONTENT,
    # The base case, so a domain error nobody mapped is still the request's
    # fault rather than "Internal error". Asking for a field that has no list
    # behind it answered 500 with the right sentence in it, which tells an
    # operator to report an outage and a developer to look in the wrong place.
    DomainError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InductionFailed: status.HTTP_422_UNPROCESSABLE_CONTENT,
    BrowserUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    VaultUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    # Not a DomainError either, and the same shape as the two above: the
    # request was fine and the deployment has no model to answer it with.
    # Without its own entry the MRO walk finds nothing and it is a 500.
    AskerUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    SchedulerUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    # The four port failures, on the same argument: the request was fine and a
    # thing this deployment depends on is not answering. Every one of them was
    # a 500 in `text/plain` until now, and the reason none of them had been
    # noticed is that each is caught at every call site that exists TODAY --
    # `UiUnavailable` was the exception that proved it, escaping
    # `vision_step.py`'s one unguarded `perform_at` to `POST
    # /v1/skills/{id}/batch`. Safety by review does not survive the next call
    # site; these five lines make it safe by default instead.
    TargetUnreachable: status.HTTP_503_SERVICE_UNAVAILABLE,
    ToolsUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    UiUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    VisionUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    # 409 and not 503, because it is not this deployment that is down: the
    # other process refused or its laptop is closed, and the same tap succeeds
    # when it opens. `AnswerConfirmation.approve` calls the same `start_for`
    # that `FireTrigger` guards at `fire_trigger.py:143` and does not guard it,
    # so tapping Approve on a card whose browser is away answered 500 in
    # `text/plain` -- on the one door whose whole job is a person authorising
    # an unattended write.
    DispatchFailed: status.HTTP_409_CONFLICT,
    NotAuthenticated: status.HTTP_409_CONFLICT,
    Refused: status.HTTP_409_CONFLICT,
    # The durable path re-raises every refusal as NotRunnable, so without this
    # a tripped circuit breaker reached the operator as a 500 -- "internal
    # error" for the one outcome the system was most deliberate about.
    NotRunnable: status.HTTP_409_CONFLICT,
    NoSessionForSystem: status.HTTP_409_CONFLICT,
    # Not 403: the credential was fine and the request was well formed. The
    # deployment has not agreed to store this, and that is state, not identity.
    ObservationRefused: status.HTTP_409_CONFLICT,
    NothingToTeach: status.HTTP_409_CONFLICT,
    TriggerRefused: status.HTTP_409_CONFLICT,
    # Vague on purpose: an unauthenticated caller with a wrong id and one with
    # a wrong token must not be able to tell which they got wrong.
    InboundRefused: status.HTTP_404_NOT_FOUND,
    NoCredentials: status.HTTP_409_CONFLICT,
    # A login that did not complete is about the system's state, not the
    # request's shape: a stale password, a second factor, a changed page. All
    # of them are resolved by a human signing in once.
    SignInFailed: status.HTTP_409_CONFLICT,
    # The identity provider's own answer, in its own words. "Invalid client"
    # and "invalid_grant" want different people to do different things, and a
    # 500 tells neither of them anything.
    TokenRefused: status.HTTP_409_CONFLICT,
    # The caller is authenticated and the run exists; they are simply not the
    # one person who saw what it produced. That is an identity mismatch, not a
    # missing resource or a conflicting state.
    NotYours: status.HTTP_403_FORBIDDEN,
    # The same refusal on the sibling door that changes a run's values.
    # A separate class with the same name, in a different module, and it
    # was in neither this table nor the handler list -- so `/v1/runs/{id}/values`
    # answered a wrong principal with a 500.
    NotYoursToRevise: status.HTTP_403_FORBIDDEN,
    # A browser reaching for a run some other browser is driving. Same shape as
    # the entry above and the same 403: the credential was accepted and the
    # browser proved it is itself, it is simply not the one that may answer for
    # this run. A `DomainError`, so the handler registered below reaches it
    # without being named -- which is the one way it differs from the two
    # `NotYours` classes above, which are plain `Exception`s and had to be
    # listed by name before their 403s could fire at all.
    NotDrivingThisRun: status.HTTP_403_FORBIDDEN,
    # The rig's own answer, kept: a body field naming a job that is not one is
    # a bad request and never a missing endpoint. 400 rather than the 422 a
    # malformed body gets, because the body parsed and its shape was right --
    # what it named was not there.
    OfferRefused: status.HTTP_400_BAD_REQUEST,
    # The rig's 400 again, for the press: a `from_step` that is not a step of
    # this job, or a declared parameter with no value, is a bad request about a
    # body that parsed. Not a `DomainError`, so without this it is a 500.
    RunRefused: status.HTTP_400_BAD_REQUEST,
    # Budget, not identity and not shape: the same request is accepted
    # tomorrow or under a larger cap. 429 is the one status that means
    # "later, not never".
    OverCap: status.HTTP_429_TOO_MANY_REQUESTS,
}

_TITLES = {
    status.HTTP_400_BAD_REQUEST: "Bad request",
    status.HTTP_404_NOT_FOUND: "Not found",
    status.HTTP_409_CONFLICT: "Conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Request cannot be processed",
    status.HTTP_503_SERVICE_UNAVAILABLE: "Dependency unavailable",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal error",
    status.HTTP_401_UNAUTHORIZED: "No credential",
    status.HTTP_403_FORBIDDEN: "Not allowed",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Method not allowed",
    status.HTTP_413_CONTENT_TOO_LARGE: "Content too large",
    status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests",
}

_SLUGS = {
    status.HTTP_401_UNAUTHORIZED: "unauthenticated",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    # The size belts on the two observation doors raise a bare `HTTPException`,
    # so without this line both would answer `.../problems/error` and the title
    # "Error" -- the locator that promises a page nobody can write, removed from
    # this file once already.
    status.HTTP_413_CONTENT_TOO_LARGE: "content_too_large",
    # `OverCap` brings its own `code`, so this is not for it. It is for the
    # bare 429 any future rate limiter raises: a hole in this table is how
    # `problem.type` was `undefined` for every 401.
    status.HTTP_429_TOO_MANY_REQUESTS: "too_many_requests",
}
"""The ``type`` a client matches on. Only for the statuses FastAPI raises by
itself; a domain error brings its own ``code``."""


def _status_for(exc: Exception) -> int:
    # Walk the MRO so a new subclass of an already-mapped error inherits its
    # status rather than silently becoming a 500.
    for klass in type(exc).__mro__:
        if klass in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[klass]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _problem_type(exc: Exception) -> str:
    """The URI naming this KIND of problem, or `about:blank` when there is none."""
    code = getattr(exc, "code", "")
    return f"https://ai-sro.dev/problems/{code}" if code else "about:blank"


def _problem(request: Request, exc: Exception) -> JSONResponse:
    code = _status_for(exc)
    return JSONResponse(
        status_code=code,
        media_type="application/problem+json",
        content={
            # `about:blank` where an error carries no `code`, and not
            # `.../problems/error`. RFC 9457 §3.1.1: when `type` is a locator,
            # "dereferencing it should provide human-readable documentation for
            # the problem type" -- so a URI under `/problems/` is a promise that
            # this is a documented KIND of problem. `error` is not a kind; it is
            # the absence of one, and pointing a locator at it promises a page
            # that can never exist. The spec's own value for "adds no semantics
            # beyond the status code" is `about:blank`, which is also what a
            # consumer assumes when `type` is missing entirely.
            #
            # Every error in `_STATUS_BY_ERROR` carries a code today, so this
            # branch is unreached by anything mapped -- it exists for the next
            # error type somebody adds and forgets, and it should tell them
            # nothing rather than tell them a lie.
            "type": _problem_type(exc),
            "title": _TITLES[code],
            "status": code,
            "detail": str(exc),
            "instance": str(request.url.path),
        },
    )


def _validation_problem(request: Request, exc: Exception) -> JSONResponse:
    """A malformed body is a problem document too.

    FastAPI's default answer is a list of objects, which breaks the contract
    every other failure here keeps -- and a client that renders `detail`
    crashes on it rather than showing the operator what was wrong.
    """
    errors: list[dict[str, Any]] = getattr(exc, "errors", lambda: [])()
    detail = "; ".join(
        f"{'.'.join(str(part) for part in error.get('loc', ())[1:]) or 'body'}: "
        f"{error.get('msg', 'is not valid')}"
        for error in errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        media_type="application/problem+json",
        content={
            "type": "https://ai-sro.dev/problems/invalid_request",
            "title": _TITLES[status.HTTP_422_UNPROCESSABLE_CONTENT],
            "status": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "detail": detail or "the request body is not valid",
            "instance": str(request.url.path),
        },
    )


def _http_problem(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI's own HTTPException, said the way everything else here says it.

    The credential checks raise it, so every 401 answered ``{"detail": "..."}``
    while every other failure answered a problem document. A client that reads
    ``problem.type`` -- which is how the console tells one refusal from another
    -- got undefined for the one failure it sees most.
    """
    code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    return JSONResponse(
        status_code=code,
        media_type="application/problem+json",
        headers=getattr(exc, "headers", None),
        content={
            "type": f"https://ai-sro.dev/problems/{_SLUGS.get(code, 'error')}",
            "title": _TITLES.get(code, "Error"),
            "status": code,
            "detail": str(getattr(exc, "detail", "") or ""),
            "instance": str(request.url.path),
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_problem)
    app.add_exception_handler(StarletteHTTPException, _http_problem)
    for error_type in (
        DomainError,
        InductionFailed,
        BrowserUnavailable,
        VaultUnavailable,
        SchedulerUnavailable,
        NotAuthenticated,
        # Not a DomainError, so it needs saying: without this a failed login is
        # a 500 and the operator is told nothing they can act on.
        SignInFailed,
        TokenRefused,
        # Neither is a DomainError, so neither is reached by the line above:
        # without these two a route with no model answers 500, and a tenant
        # at its cap is told the server broke.
        AskerUnavailable,
        OverCap,
        # None of the five is a `DomainError`, so the line above does not reach
        # them and their entries in the table above would do nothing on their
        # own. A status with no handler and a handler with no status are both
        # a 500; two doors answered one for the life of this codebase because
        # only one half was ever written.
        TargetUnreachable,
        ToolsUnavailable,
        UiUnavailable,
        VisionUnavailable,
        DispatchFailed,
        # Neither is `OfferRefused`, which is a `DomainError` and is reached by
        # the line above. This one is not, so it needs saying by name.
        RunRefused,
        # Neither is a `DomainError` either, and until this line their 403s
        # above never fired: a caller who is not the person a run was
        # performed for was told the server broke, in text/plain, on both
        # `/v1/runs/{run_id}/wrong` and `/v1/runs/{run_id}/values`.
        NotYours,
        NotYoursToRevise,
    ):
        app.add_exception_handler(error_type, _problem)
