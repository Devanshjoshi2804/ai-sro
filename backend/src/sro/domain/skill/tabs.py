from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.domain.chat.asked_by import from_a_mailbox
from sro.domain.execution.evidence import primary_gesture
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import MAIN, Step, Workflow

OPENED_FROM = "opened_from:"
POPUP = "popup_opened"
_EXTRA = "tab_"


def _in_one_doing(step: Step, by_id: Mapping[str, Gesture], stream: str) -> Gesture | None:
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is not None and gesture.stream_id == stream and not from_a_mailbox(gesture):
            return gesture
    return None


def tab_roles(workflow: Workflow, by_id: Mapping[str, Gesture]) -> dict[int, str]:
    ordered = sorted(workflow.steps, key=lambda one: one.order)
    first = next(
        (
            gesture
            for step in ordered
            if (gesture := primary_gesture(step, by_id)) is not None and not from_a_mailbox(gesture)
        ),
        None,
    )
    if first is None:
        return {step.order: MAIN for step in ordered}
    opener = {
        mark.tab_id: mark.opener_tab_id
        for gesture in by_id.values()
        if gesture.stream_id == first.stream_id
        for mark in gesture.page_events
        if mark.page_kind == POPUP and mark.tab_id is not None
    }
    of_tab: dict[int, str] = {}
    roles: dict[int, str] = {}
    current = MAIN
    for step in ordered:
        gesture = _in_one_doing(step, by_id, first.stream_id)
        tab = None if gesture is None else gesture.tab_id
        if tab is not None:
            if tab not in of_tab:
                parent = opener.get(tab)
                if not of_tab:
                    of_tab[tab] = MAIN
                elif parent is not None and parent in of_tab:
                    of_tab[tab] = OPENED_FROM + of_tab[parent]
                else:
                    extra = sum(role.startswith(_EXTRA) for role in of_tab.values())
                    of_tab[tab] = f"{_EXTRA}{extra + 2}"
            current = of_tab[tab]
        roles[step.order] = current
    return roles


def unresolved(steps: Sequence[Step]) -> list[int]:
    seen: set[str] = set()
    extra = 1
    bad: list[int] = []
    for step in sorted(steps, key=lambda one: one.order):
        role = step.tab
        if role.startswith(OPENED_FROM) and role.removeprefix(OPENED_FROM) not in seen:
            bad.append(step.order)
        elif role.startswith(_EXTRA) and role not in seen:
            if role != f"{_EXTRA}{extra + 1}":
                bad.append(step.order)
            extra += 1
        seen.add(role)
    return bad


__all__ = ["MAIN", "OPENED_FROM", "POPUP", "tab_roles", "unresolved"]
