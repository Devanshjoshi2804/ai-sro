"""Domain errors to RFC 9457 problem details, in one place.

Routers never catch domain errors. If a use case raises, the mapping happens
here, so every endpoint reports the same failure the same way.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from sro.application.connection.connect_system import NotAuthenticated
from sro.application.execution.execute_skill import Refused
from sro.application.induction.errors import InductionFailed
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.vault import VaultUnavailable
from sro.domain.shared.errors import Conflict, DomainError, InvariantViolation, NotFound

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    NotFound: status.HTTP_404_NOT_FOUND,
    Conflict: status.HTTP_409_CONFLICT,
    InvariantViolation: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InductionFailed: status.HTTP_422_UNPROCESSABLE_CONTENT,
    BrowserUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    VaultUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    NotAuthenticated: status.HTTP_409_CONFLICT,
    Refused: status.HTTP_409_CONFLICT,
}

_TITLES = {
    status.HTTP_404_NOT_FOUND: "Not found",
    status.HTTP_409_CONFLICT: "Conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "Request cannot be processed",
    status.HTTP_503_SERVICE_UNAVAILABLE: "Dependency unavailable",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Internal error",
}


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


def install_error_handlers(app: FastAPI) -> None:
    for error_type in (
        DomainError,
        InductionFailed,
        BrowserUnavailable,
        VaultUnavailable,
        NotAuthenticated,
    ):
        app.add_exception_handler(error_type, _problem)
