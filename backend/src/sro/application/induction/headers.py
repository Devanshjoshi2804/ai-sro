"""Turn observed headers into a replayable header plan.

Every header the call carried is recorded. Classification decides only where the
value comes from at run time. See docs/11-capture-completeness.md.
"""

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
    """One HeaderPlan per observed header. Nothing is dropped.

    ``replacements`` carries the placeholders the diff produced. A semantic
    header that varied between the runs is a parameter like any other value:
    replaying run one's warehouse id when the operator asked for another
    warehouse is the same failure as replaying run one's wave id.
    """
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
                # The captured value is stale by construction. Recording that the
                # header is required is the useful part; the value is minted live.
                plans.append(HeaderPlan(name=name, sensitivity=sensitivity, mint=True))
            case Sensitivity.TRANSPORT:
                # Recorded because it was observed, never carried as a value:
                # the domain says these are not replayable, and a captured
                # Referer points at the page of a demonstration that is over.
                plans.append(HeaderPlan(name=name, sensitivity=sensitivity, managed=True))
            case Sensitivity.SEMANTIC if REDACTED in value:
                # The value was taken out by SHAPE -- a token this name rule
                # never recognised as one. `classify_header` judges by name
                # only, so the header reads semantic while its value is the
                # marker, and replaying it would put the literal characters
                # «redacted» on the wire and call the plan replayable. A value
                # removed because it looked like a credential is a credential,
                # and the executor resolves it the way it resolves the others.
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
                        # A placeholder is a deliberate `$name`; an observed
                        # value is a literal and means only itself. `Template`
                        # is `string.Template`, so a `$` in a captured header
                        # would report itself as a parameter the plan needs --
                        # and `SkillVersion` refuses a step referencing one it
                        # never declared, which takes down the whole build over
                        # a dollar sign in a header nobody parameterised.
                        value=Template(placeholder)
                        if placeholder is not None
                        else Template(value.replace("$", "$$")),
                    )
                )

    return tuple(plans)


def credential_key(target_system: str, facility: str, header_name: str) -> str:
    """Vault key for a credential. Scoped per system and facility, because a site
    has its own login even when the software is the same."""
    return f"{target_system}/{facility}/{header_name.lower()}"
