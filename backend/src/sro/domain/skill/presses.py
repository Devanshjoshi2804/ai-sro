from __future__ import annotations

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Workflow

SOON_S = 20.0

CONTROLS = frozenset({"button", "a", "input", "select", "summary", "option", "label"})

ROLES = frozenset(
    {
        "button",
        "link",
        "menuitem",
        "menuitemcheckbox",
        "tab",
        "option",
        "checkbox",
        "radio",
        "switch",
    }
)


def _is_a_control(gesture: Gesture) -> bool:
    target = gesture.action.target
    if target is None:
        return False
    return (
        (target.tag or "").lower() in CONTROLS
        or (target.role or "").lower() in ROLES
        or bool(target.test_id)
    )


def with_the_press(workflow: Workflow, gestures: dict[str, Gesture]) -> int:
    cited_anywhere = {gesture_id for step in workflow.steps for gesture_id in step.cites}
    changed = 0

    for step in workflow.steps:
        mine = [gestures[one] for one in step.cites if one in gestures]
        clicks = [one for one in mine if one.action.kind == "click"]
        if not clicks or any(_is_a_control(one) for one in clicks):
            continue

        after = max(one.at for one in mine)
        systems = {origin_of(one.url or "") for one in mine}
        presses = [
            one
            for one in gestures.values()
            if one.id not in cited_anywhere
            and one.action.kind == "click"
            and _is_a_control(one)
            and after <= one.at <= after + SOON_S
            and origin_of(one.url or "") in systems
        ]
        if not presses:
            continue

        press = min(presses, key=lambda one: one.at)
        step.cites = [press.id] + [
            one for one in step.cites if one in gestures and gestures[one].action.kind != "click"
        ]
        cited_anywhere.add(press.id)
        changed += 1

    return changed
