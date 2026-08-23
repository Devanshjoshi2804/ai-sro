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
from sro.application.execution.execute_skill import NotRunnable, Refused
from sro.application.induction.errors import InductionFailed
from sro.application.observation.ingest import ObservationRefused
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.sign_in import SignInFailed
from sro.application.ports.token import TokenRefused
from sro.application.ports.vault import VaultUnavailable
from sro.application.recording.start_recording import NoSessionForSystem
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
    NoCredentials: status.HTTP_409_CONFLICT,
    # A login that did not complete is about the system's state, not the
    # request's shape: a stale password, a second factor, a changed page. All
    # of them are resolved by a human signing in once.
    SignInFailed: status.HTTP_409_CONFLICT,
    # The identity provider's own answer, in its own words. "Invalid client"
    # and "invalid_grant" want different people to do different things, and a
    # 500 tells neither of them anything.
    TokenRefused: status.HTTP_409_CONFLICT,
}

_TITLES = {
    status.HTTP_404_NOT_FOUND: "Not found",
    status.HTTP_409_CONFLICT: "Conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Request cannot be processed",
    status.HTTP_503_SERVICE_UNAVAILABLE: "Dependency unavailable",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal error",
    status.HTTP_401_UNAUTHORIZED: "No credential",
    status.HTTP_403_FORBIDDEN: "Not allowed",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Method not allowed",
}

_SLUGS = {
    status.HTTP_401_UNAUTHORIZED: "unauthenticated",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
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


def _problem(request: Request, exc: Exception) -> JSONResponse:
    code = _status_for(exc)
    return JSONResponse(
        status_code=code,
        media_type="application/problem+json",
        content={
            "type": f"https://ai-sro.dev/problems/{getattr(exc, 'code', 'error')}",
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
        NotAuthenticated,
        # Not a DomainError, so it needs saying: without this a failed login is
        # a 500 and the operator is told nothing they can act on.
        SignInFailed,
        TokenRefused,
    ):
        app.add_exception_handler(error_type, _problem)
