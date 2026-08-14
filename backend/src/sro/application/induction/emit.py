"""Build a SkillStep from run A's frame. See docs/07-adr/005-dual-recipe.md."""

from __future__ import annotations

from sro.application.induction.assertions import StepEvidence
from sro.application.induction.diff import Parameterisation
from sro.application.induction.headers import build_header_plans
from sro.application.induction.locators import build_locators
from sro.application.induction.sites import (
    ActionValueSite,
    Site,
    substitute_body,
    substitute_url,
)
from sro.domain.recording.events import ActionFrame, ActionKind
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.plan import NetworkPlan, UiPlan
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template

_HUMAN_ONLY_HINTS = ("mfa", "otp", "two-factor", "verification code", "approve", "signature")
_UNREPLAYABLE_RESOURCE_TYPES = frozenset({"websocket"})


def emit_step(
    index: int,
    frame: ActionFrame,
    parameterisation: Parameterisation,
    evidence: StepEvidence,
    objective: ObjectiveKey,
    other: ActionFrame | None = None,
) -> SkillStep:
    replacements = parameterisation.for_step(index)
    return SkillStep(
        index=index,
        intent=_describe_intent(frame),
        network_plan=_network_plan(frame, replacements, objective),
        ui_plan=_ui_plan(frame, replacements, evidence, other),
        assertions=evidence.assertions,
        requires_human=_requires_human(frame),
    )


def _network_plan(
    frame: ActionFrame, replacements: dict[Site, str], objective: ObjectiveKey
) -> NetworkPlan | None:
    request = frame.primary_request
    if request is None:
        return None

    replayable = request.resource_type.lower() not in _UNREPLAYABLE_RESOURCE_TYPES
    body = request.request_body

    return NetworkPlan(
        method=request.method.upper(),
        url=Template(substitute_url(request.url, replacements)),
        headers=build_header_plans(
            request,
            target_system=objective.target_system,
            facility=objective.facility,
            replacements=replacements,
        ),
        body=(
            Template(substitute_body(body.text, replacements))
            if body is not None and body.text is not None
            else None
        ),
        body_blob_uri=body.blob_uri if body is not None else None,
        expected_status=request.status,
        content_type=body.mime_type if body is not None else None,
        replayable=replayable,
        unreplayable_reason=(
            None if replayable else f"{request.resource_type} traffic cannot be replayed as a call"
        ),
    )


def _ui_plan(
    frame: ActionFrame,
    replacements: dict[Site, str],
    evidence: StepEvidence,
    other: ActionFrame | None = None,
) -> UiPlan | None:
    action = frame.action
    if action.target is None and action.kind is not ActionKind.NAVIGATE:
        return None

    value: Template | None = None
    if action.value is not None:
        placeholder = replacements.get(ActionValueSite())
        value = Template(placeholder if placeholder is not None else action.value)

    target_path = None
    if action.target is not None and frame.ax_graph is not None:
        target_path = frame.ax_graph.path(action.target)

    return UiPlan(
        action=action.kind,
        target=action.target,
        value=value,
        wait_for=evidence.wait_for,
        target_path=target_path,
        locators=build_locators(
            action.target,
            other.action.target if other is not None else None,
            value_placeholder=replacements.get(ActionValueSite()),
        ),
    )


def _describe_intent(frame: ActionFrame) -> str:
    action = frame.action
    target = action.target.describe() if action.target else None

    match action.kind:
        case ActionKind.NAVIGATE:
            return f"open {action.value}"
        case ActionKind.CLICK:
            return f"click {target}"
        case ActionKind.TYPE:
            return f"enter a value into {target}"
        case ActionKind.SELECT:
            return f"choose an option in {target}"
        case ActionKind.PRESS:
            return f"press {action.value}"
        case ActionKind.UPLOAD:
            return f"upload a file to {target}"
        case ActionKind.SCROLL:
            return "scroll"
        case ActionKind.HOVER:
            return f"hover over {target}"


def _requires_human(frame: ActionFrame) -> bool:
    """Keyword match, biased towards flagging.

    A step wrongly flagged costs an operator ten seconds; one wrongly cleared
    costs an MFA lockout.
    """
    target = frame.action.target
    haystack = " ".join(
        part.lower()
        for part in (
            target.accessible_name if target else None,
            target.text if target else None,
            frame.ax_graph.url if frame.ax_graph else None,
        )
        if part
    )
    return any(hint in haystack for hint in _HUMAN_ONLY_HINTS)
