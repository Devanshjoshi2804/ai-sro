from __future__ import annotations

from sro.application.induction.sites import HeaderSite, Site
from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.sensitivity import REDACTED, Sensitivity, classify_header
from sro.domain.skill.plan import HeaderPlan
from sro.domain.skill.template import Template


def build_header_plans(
    request: CapturedRequest,
    *,
    target_system: str,
    facility: str,
    replacements: dict[Site, str] | None = None,
) -> tuple[HeaderPlan, ...]:
    plans: list[HeaderPlan] = []
    substitutions = replacements or {}

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
                plans.append(HeaderPlan(name=name, sensitivity=sensitivity, mint=True))
            case Sensitivity.TRANSPORT:
                plans.append(HeaderPlan(name=name, sensitivity=sensitivity, managed=True))
            case Sensitivity.SEMANTIC if REDACTED in value:
                plans.append(
                    HeaderPlan(
                        name=name,
                        sensitivity=sensitivity,
                        credential_ref=credential_key(target_system, facility, name),
                    )
                )
            case Sensitivity.SEMANTIC:
                placeholder = substitutions.get(HeaderSite(name))
                plans.append(
                    HeaderPlan(
                        name=name,
                        sensitivity=sensitivity,
                        value=Template(placeholder)
                        if placeholder is not None
                        else Template(value.replace("$", "$$")),
                    )
                )

    return tuple(plans)


def credential_key(target_system: str, facility: str, header_name: str) -> str:
    return f"{target_system}/{facility}/{header_name.lower()}"
