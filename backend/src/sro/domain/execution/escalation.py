from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.execution.run import Medium


class FailureKind(StrEnum):
    NO_PLAN = "no_plan"

    UNREPLAYABLE = "unreplayable"

    STATUS_MISMATCH = "status_mismatch"

    ASSERTION_FAILED = "assertion_failed"

    CREDENTIAL_MISSING = "credential_missing"

    UNREACHABLE = "unreachable"
    TOOL_UNAVAILABLE = "tool_unavailable"

    CONTROL_NOT_FOUND = "control_not_found"


@dataclass(frozen=True, slots=True)
class EscalationRule:
    when: FailureKind
    at: Medium
    then: Medium | None

    because: str


_POLICY: tuple[EscalationRule, ...] = (
    EscalationRule(
        when=FailureKind.NO_PLAN,
        at=Medium.NETWORK,
        then=None,
        because=(
            "the demonstration moved the interface without asking the server anything, "
            "so a run going over the network has nothing to perform here"
        ),
    ),
    EscalationRule(
        when=FailureKind.UNREPLAYABLE,
        at=Medium.NETWORK,
        then=Medium.UI,
        because="the call cannot be reproduced, but the gesture that made it can",
    ),
    EscalationRule(
        when=FailureKind.STATUS_MISMATCH,
        at=Medium.NETWORK,
        then=Medium.UI,
        because="the endpoint has moved on; the screen is the surface that is kept working",
    ),
    EscalationRule(
        when=FailureKind.ASSERTION_FAILED,
        at=Medium.NETWORK,
        then=Medium.UI,
        because="the response changed shape; the interface still shows the outcome",
    ),
    EscalationRule(
        when=FailureKind.CREDENTIAL_MISSING,
        at=Medium.NETWORK,
        then=None,
        because="a browser cannot invent a session either; connect the system instead",
    ),
    EscalationRule(
        when=FailureKind.UNREACHABLE,
        at=Medium.NETWORK,
        then=None,
        because="the system did not answer at all, and a browser would ask it again harder",
    ),
    EscalationRule(
        when=FailureKind.TOOL_UNAVAILABLE,
        at=Medium.TOOL,
        then=None,
        because=(
            "the connector this step was mapped onto is not there to answer, and "
            "the gesture it replaced was mapped away on purpose -- falling back to it "
            "would perform by clicking a step somebody decided should be a call"
        ),
    ),
    EscalationRule(
        when=FailureKind.STATUS_MISMATCH,
        at=Medium.TOOL,
        then=None,
        because=(
            "a tool answered and said no. There is no lower rung that knows better: "
            "the connector is the system's own door, and clicking at it instead would "
            "be doing again what it just refused"
        ),
    ),
    EscalationRule(
        when=FailureKind.ASSERTION_FAILED,
        at=Medium.TOOL,
        then=None,
        because=(
            "the tool answered something the mapping did not expect. Nobody "
            "demonstrated this call, so there is no recorded gesture behind it to "
            "fall back to -- this is a question for whoever mapped it"
        ),
    ),
    EscalationRule(
        when=FailureKind.UNREACHABLE,
        at=Medium.TOOL,
        then=None,
        because="the connector did not answer at all, and a browser would ask it again harder",
    ),
    EscalationRule(
        when=FailureKind.CREDENTIAL_MISSING,
        at=Medium.TOOL,
        then=None,
        because="a browser cannot invent a connector's credential either; configure it instead",
    ),
    EscalationRule(
        when=FailureKind.CONTROL_NOT_FOUND,
        at=Medium.UI,
        then=Medium.VISION,
        because=(
            "the control the demonstration recorded is gone, and what is on the screen "
            "instead is a question about pixels rather than about selectors"
        ),
    ),
    EscalationRule(
        when=FailureKind.CONTROL_NOT_FOUND,
        at=Medium.VISION,
        then=None,
        because="a human is the rung above vision, and there is no rung above a human",
    ),
)


def next_medium(failure: FailureKind, at: Medium) -> EscalationRule | None:
    for rule in _POLICY:
        if rule.when is failure and rule.at is at:
            return rule
    return None
