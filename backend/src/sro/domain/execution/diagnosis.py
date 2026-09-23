from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.execution.escalation import FailureKind


class Remedy(StrEnum):
    NONE = "none"

    REFRESH_SESSION = "refresh_session"

    REFRESH_SESSION_CONTEXT = "refresh_session_context"

    ESCALATE_MEDIUM = "escalate_medium"


@dataclass(frozen=True, slots=True)
class Diagnosis:
    remedy: Remedy
    because: str
    safe_for_writes: bool


_SIGNED_OUT = "the system answered a signed-in session with its login page, so the session is gone"

_NOTHING = Diagnosis(
    remedy=Remedy.NONE,
    because="nothing here says what is wrong, and a guess would be a second failure",
    safe_for_writes=False,
)


def diagnose(
    *,
    failure: FailureKind | None,
    status_code: int | None,
    redirected_off_host: bool,
    missing_headers: tuple[str, ...] = (),
) -> Diagnosis:
    if missing_headers:
        return Diagnosis(
            remedy=Remedy.REFRESH_SESSION_CONTEXT,
            because=(
                "the executor holds no live value for "
                + ", ".join(missing_headers)
                + ", which the application mints rather than stores"
            ),
            safe_for_writes=True,
        )

    if redirected_off_host or (status_code == 302 and failure is not FailureKind.NO_PLAN):
        return Diagnosis(
            remedy=Remedy.REFRESH_SESSION,
            because=_SIGNED_OUT,
            safe_for_writes=True,
        )

    if status_code in {401, 419, 440}:
        return Diagnosis(
            remedy=Remedy.REFRESH_SESSION,
            because=f"the system rejected the session outright ({status_code})",
            safe_for_writes=True,
        )

    if status_code == 403:
        return Diagnosis(
            remedy=Remedy.REFRESH_SESSION_CONTEXT,
            because=(
                "the session was accepted and the request was not; on these systems that is "
                "an anti-forgery token the page reissues"
            ),
            safe_for_writes=True,
        )

    if failure is FailureKind.CONTROL_NOT_FOUND:
        return Diagnosis(
            remedy=Remedy.ESCALATE_MEDIUM,
            because="the control has moved; a rung that looks at the screen may still find it",
            safe_for_writes=True,
        )

    return _NOTHING
