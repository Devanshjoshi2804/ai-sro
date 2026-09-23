from __future__ import annotations

from sro.domain.execution.evidence import PUTS_A_VALUE, primary_gesture
from sro.domain.execution.secrets import field_of
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step, Workflow


def with_passwords(workflow: Workflow, gestures: dict[str, Gesture]) -> int:
    cited = {
        gesture_id for step in workflow.steps for gesture_id in step.cites if gesture_id in gestures
    }
    if not cited:
        return 0

    within = [gestures[gesture_id] for gesture_id in cited]
    first, last = min(one.at for one in within), max(one.at for one in within)
    systems = {origin_of(one.url or "") for one in within}

    once: dict[tuple[str, str], Gesture] = {}
    for gesture in sorted(gestures.values(), key=lambda one: one.at):
        if not is_secret(gesture) or gesture.action.kind not in PUTS_A_VALUE:
            continue
        if not first <= gesture.at <= last:
            continue
        where = origin_of(gesture.url or "")
        if where not in systems:
            continue
        once.setdefault((where, field_of(gesture)), gesture)

    kept = {gesture.id for gesture in once.values()}
    spare = [
        step
        for step in workflow.steps
        if step.cites
        and all(one in gestures and is_secret(gestures[one]) for one in step.cites)
        and not any(one in kept for one in step.cites)
    ]
    for step in spare:
        workflow.steps.remove(step)

    aimed = set()
    for step in workflow.steps:
        at = primary_gesture(step, gestures)
        if at is not None and is_secret(at):
            aimed.add(at.id)
    added = 0
    for gesture in sorted(once.values(), key=lambda one: one.at):
        if gesture.id in aimed:
            continue
        workflow.steps.append(
            Step(
                order=0,
                says=f"Type the {field_of(gesture).replace('-', ' ')}.",
                system=gesture.system,
                cites=[gesture.id],
                parameters=[],
            )
        )
        added += 1

    if added or spare:
        _in_the_order_it_happened(workflow, gestures)
    return added + len(spare)


def _in_the_order_it_happened(workflow: Workflow, gestures: dict[str, Gesture]) -> None:

    def when(step: Step) -> float:
        times = [gestures[one].at for one in step.cites if one in gestures]
        return min(times) if times else float(step.order)

    for position, step in enumerate(sorted(workflow.steps, key=when)):
        step.order = position
