"""Domain errors to RFC 9457 problem details, in one place.

Routers never catch domain errors. If a use case raises, the mapping happens
here, so every endpoint reports the same failure the same way.
"""

from __future__ import annotations

import logging
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
    DomainError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InductionFailed: status.HTTP_422_UNPROCESSABLE_CONTENT,
    BrowserUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    VaultUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    AskerUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    SchedulerUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    TargetUnreachable: status.HTTP_503_SERVICE_UNAVAILABLE,
    ToolsUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    UiUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    VisionUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    DispatchFailed: status.HTTP_409_CONFLICT,
    NotAuthenticated: status.HTTP_409_CONFLICT,
    Refused: status.HTTP_409_CONFLICT,
    NotRunnable: status.HTTP_409_CONFLICT,
    NoSessionForSystem: status.HTTP_409_CONFLICT,
    ObservationRefused: status.HTTP_409_CONFLICT,
    TriggerRefused: status.HTTP_409_CONFLICT,
    InboundRefused: status.HTTP_404_NOT_FOUND,
    NoCredentials: status.HTTP_409_CONFLICT,
    SignInFailed: status.HTTP_409_CONFLICT,
    TokenRefused: status.HTTP_409_CONFLICT,
    NotYours: status.HTTP_403_FORBIDDEN,
    NotYoursToRevise: status.HTTP_403_FORBIDDEN,
    NotDrivingThisRun: status.HTTP_403_FORBIDDEN,
    OfferRefused: status.HTTP_400_BAD_REQUEST,
    RunRefused: status.HTTP_400_BAD_REQUEST,
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
    status.HTTP_413_CONTENT_TOO_LARGE: "content_too_large",
    status.HTTP_429_TOO_MANY_REQUESTS: "too_many_requests",
}
"""The ``type`` a client matches on. Only for the statuses FastAPI raises by
itself; a domain error brings its own ``code``."""


def _status_for(exc: Exception) -> int:
    for klass in type(exc).__mro__:
        if klass in _STATUS_BY_ERROR:
            return _STATUS_BY_ERROR[klass]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


logger = logging.getLogger(__name__)


def _refused(request: Request, code: int, why: str, kind: str) -> None:
    """Say that a door refused, and what it refused with.

    Every refusal this API makes passes through one of the three renderers
    below, and until now none of them said anything: a 404 answered a problem
    document and left no trace behind it. An operator whose button did nothing
    has a refusal with a reason in it, and the only copy of that reason was in
    their browser.

    Attributed like everything else -- the tenant and the principal are on the
    task by the time a handler runs, so a refusal names who was refused without
    being told. `instance` is the path FastAPI matched, which carries ids and
    no values.

    A server fault is an error and a caller's mistake is a warning, which is
    the ordinary split -- and a 404 on a poll is noise a deployment can filter
    by level rather than something this has to decide for it.
    """
    logger.log(
        logging.ERROR if code >= 500 else logging.WARNING,
        "%s %s refused %s: %s",
        request.method,
        request.url.path,
        code,
        why.replace("\n", " ")[:K_WHY],
        extra={"refusal": kind},
    )


K_WHY = 300
"""How much of a refusal's reason is logged. A problem detail is a sentence for
a person; anything longer is a stack trace somebody put in a detail field."""


def _problem_type(exc: Exception) -> str:
    """The URI naming this KIND of problem, or `about:blank` when there is none."""
    code = getattr(exc, "code", "")
    return f"https://ai-sro.dev/problems/{code}" if code else "about:blank"


def _problem(request: Request, exc: Exception) -> JSONResponse:
    code = _status_for(exc)
    _refused(request, code, str(exc), type(exc).__name__)
    return JSONResponse(
        status_code=code,
        media_type="application/problem+json",
        content={
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
    _refused(request, status.HTTP_422_UNPROCESSABLE_CONTENT, detail, "RequestValidationError")
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
    _refused(request, code, str(getattr(exc, "detail", "") or ""), "HTTPException")
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
        SignInFailed,
        TokenRefused,
        AskerUnavailable,
        OverCap,
        TargetUnreachable,
        ToolsUnavailable,
        UiUnavailable,
        VisionUnavailable,
        DispatchFailed,
        RunRefused,
        NotYours,
        NotYoursToRevise,
    ):
        app.add_exception_handler(error_type, _problem)
