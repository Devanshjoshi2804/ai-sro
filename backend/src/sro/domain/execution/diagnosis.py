"""What a failed step is actually complaining about, and what would fix it.

A table, for the same reason the escalation policy is one: every entry is a
claim that can be read, argued with and tested, where a chain of branches inside
the executor is none of those things.

The entries here were each paid for. A shadow run of the first task ever taught
came back ``302`` to the login page while the console reported the connection
signed in, and nothing in the run said why -- the session had rotated, and a
redirect to an identity provider is indistinguishable from being signed out.
Diagnosing that by hand took an afternoon. Doing it twice would be a choice.

Two rules bound every remedy, and neither is negotiable:

**A remedy repairs the session, never the skill.** Refreshing a cookie is
recovering something the system owns. Changing what a step sends is rewriting
evidence, and evidence is only rewritten by a demonstration.

**A write is retried only when the evidence says it never arrived.** A redirect
to a login page is proof the application never saw the request. A timeout, a 500
or a 409 are not, and retrying those risks doing a warehouse task twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.execution.escalation import FailureKind


class Remedy(StrEnum):
    NONE = "none"
    """Nothing safe to try. The honest answer for most failures: the system
    said no for a reason of its own, and guessing at it is how an executor
    turns one bad call into six."""

    REFRESH_SESSION = "refresh_session"
    """Sign the connection in again and take what it produces -- cookies, the
    tokens the application mints, the page it calls from. The remedy for a
    session that has aged out underneath a skill that is still correct."""

    REFRESH_SESSION_CONTEXT = "refresh_session_context"
    """The session is good but what the executor holds beside it is not: a
    token the page reissues, a per-session context in the Referer. Observed
    from the application again without a new login, which matters on a system
    that permits one session at a time -- signing in again would take the
    operator's own browser down with it."""

    ESCALATE_MEDIUM = "escalate_medium"
    """The call cannot be made to work as a call. The interface can still do
    it, and the escalation table already says when that is sensible."""


@dataclass(frozen=True, slots=True)
class Diagnosis:
    remedy: Remedy
    because: str
    safe_for_writes: bool
    """Whether the evidence proves the request never reached the application.
    False stops a mutating step even when the remedy would work, because a
    write that may have landed must be looked at by a person."""


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
    """Read the symptom. Never the skill, and never the operator's intent."""
    if missing_headers:
        return Diagnosis(
            remedy=Remedy.REFRESH_SESSION_CONTEXT,
            because=(
                "the executor holds no live value for "
                + ", ".join(missing_headers)
                + ", which the application mints rather than stores"
            ),
            # Nothing was sent: the step refused before the request was built.
            safe_for_writes=True,
        )

    if redirected_off_host or (status_code == 302 and failure is not FailureKind.NO_PLAN):
        return Diagnosis(
            remedy=Remedy.REFRESH_SESSION,
            because=_SIGNED_OUT,
            # A login page is proof the request was turned away before the
            # application saw it. This is the one status where that is provable.
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

    # Everything else on purpose. A 500 may have written half a task, a 409 is
    # the system disagreeing on facts, a timeout leaves the outcome unknown --
    # and none of them are fixed by trying again with the same request.
    return _NOTHING
