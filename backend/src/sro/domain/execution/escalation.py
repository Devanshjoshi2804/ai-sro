"""When a rung fails, what may try next -- as a table rather than as branches.

Every entry is a claim about *why* the step failed, and whether a slower medium
could plausibly do better. Three of them are refusals, and those matter most: a
browser cannot fix a missing credential, pointing one at a system that just
timed out turns an outage into a heavier outage, and a step that never asked the
server anything has nothing for a network run to escalate.

**A step may escalate; a task escalates better.** A run that swaps medium
half way through leaves the browser without the screen state the earlier steps
would have produced, so a lone UI step often cannot find its control. The
coherent unit is the whole task: run it over the network, and if that fails in a
way the table says the interface can handle, run the task again in the browser
from the first step. Choosing that automatically is Phase 5's job -- it is the
same decision as the circuit breaker -- so today the medium is chosen when the
run is requested, and this table says which failures make that choice sensible.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.execution.run import Medium


class FailureKind(StrEnum):
    NO_PLAN = "no_plan"
    """This rung has nothing to perform. Not a failure of the system."""

    UNREPLAYABLE = "unreplayable"
    """The recorded call cannot be reproduced as a call at all."""

    STATUS_MISMATCH = "status_mismatch"
    """The call went out and the system answered differently than it did for the
    human. Often the UI has moved on and the recorded endpoint has not."""

    ASSERTION_FAILED = "assertion_failed"
    """It answered, and the answer was not the one the demonstration proved."""

    CREDENTIAL_MISSING = "credential_missing"
    UNREACHABLE = "unreachable"
    CONTROL_NOT_FOUND = "control_not_found"
    """A UI rung could not find the control. The skill has drifted from the
    system it was taught on."""


@dataclass(frozen=True, slots=True)
class EscalationRule:
    when: FailureKind
    at: Medium
    then: Medium | None
    """``None`` means stop. Stopping is a decision with a reason, not an
    absence of one."""

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
    """The rule that applies, or ``None`` when nothing does.

    An unmatched combination stops the step. Silence is the safe default here:
    a missing rule means nobody has decided this case, and inventing an
    escalation for it points a less deterministic medium at a live warehouse.
    """
    for rule in _POLICY:
        if rule.when is failure and rule.at is at:
            return rule
    return None
