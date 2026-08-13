"""Turn observed headers into a replayable header plan.

Every header the call carried is recorded. Classification decides only where the
value comes from at run time. See docs/11-capture-completeness.md.
"""

from __future__ import annotations

from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.sensitivity import Sensitivity, classify_header
from sro.domain.skill.plan import HeaderPlan
from sro.domain.skill.template import Template


def build_header_plans(
    request: CapturedRequest, *, target_system: str, facility: str
) -> tuple[HeaderPlan, ...]:
    """One HeaderPlan per observed header. Nothing is dropped."""
    plans: list[HeaderPlan] = []

    for name, value in request.request_headers.items():
        sensitivity = classify_header(name)

        match sensitivity:
            case Sensitivity.AUTH | Sensitivity.SESSION:
                plans.append(
                    HeaderPlan(
                        name=name,
                        sensitivity=sensitivity,
                        credential_ref=credential_key(target_system, facility, name),
                    )
                )
            case Sensitivity.CSRF | Sensitivity.TRACE:
                # The captured value is stale by construction. Recording that the
                # header is required is the useful part; the value is minted live.
                plans.append(HeaderPlan(name=name, sensitivity=sensitivity, mint=True))
            case Sensitivity.TRANSPORT:
                # Recorded for documentation. The HTTP client sets these, and
                # replaying a captured Content-Length is actively harmful.
                plans.append(
                    HeaderPlan(
                        name=name, sensitivity=sensitivity, value=Template(value), mint=False
                    )
                )
            case Sensitivity.SEMANTIC:
                plans.append(HeaderPlan(name=name, sensitivity=sensitivity, value=Template(value)))

    return tuple(plans)


def credential_key(target_system: str, facility: str, header_name: str) -> str:
    """Vault key for a credential. Scoped per system and facility, because a site
    has its own login even when the software is the same."""
    return f"{target_system}/{facility}/{header_name.lower()}"


def replayable_headers(plans: tuple[HeaderPlan, ...]) -> tuple[HeaderPlan, ...]:
    """Headers the executor sends verbatim, without resolving or minting."""
    return tuple(
        plan
        for plan in plans
        if plan.sensitivity is Sensitivity.SEMANTIC and plan.value is not None
    )
