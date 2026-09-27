from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.domain.chat.asked_by import from_a_mailbox
from sro.domain.execution.evidence import primary_gesture
from sro.domain.observation.gesture import Gesture
from sro.domain.recording.state import PageEventKind
from sro.domain.skill.workflow import MAIN, Step, Workflow

OPENED_FROM = "opened_from:"
_EXTRA = "tab_"


def _acts_in(step: Step, by_id: Mapping[str, Gesture], stream: str) -> Gesture | None:
    gesture = primary_gesture(step, by_id)
    if gesture is None or gesture.stream_id != stream or from_a_mailbox(gesture):
        return None
    return gesture if gesture.tab_id is not None else None


def _openers(by_id: Mapping[str, Gesture], stream: str, start: float, end: float) -> dict[int, int]:
    return {
        mark.tab_id: mark.opener_tab_id
        for gesture in by_id.values()
        if gesture.stream_id == stream
        for mark in gesture.page_events
        if mark.page_kind == PageEventKind.POPUP_OPENED
        and mark.tab_id is not None
        and mark.opener_tab_id is not None
        and start <= mark.at <= end
    }


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
    acting = {
        step.order: gesture
        for step in ordered
        if first is not None and (gesture := _acts_in(step, by_id, first.stream_id)) is not None
    }
    of_tab: dict[int, str] = {}
    if first is not None and acting:
        times = [gesture.at for gesture in acting.values()]
        opener = _openers(by_id, first.stream_id, min(times), max(times))
        systems: set[str | None] = set()
        for gesture in sorted(acting.values(), key=lambda one: (one.at, one.id)):
            tab = gesture.tab_id
            if tab is None or tab in of_tab:
                continue
            parent = opener.get(tab)
            if not of_tab:
                of_tab[tab] = MAIN
            elif parent is not None and parent in of_tab:
                of_tab[tab] = OPENED_FROM + of_tab[parent]
            elif gesture.system in systems:
                extra = sum(role.startswith(_EXTRA) for role in of_tab.values())
                of_tab[tab] = f"{_EXTRA}{extra + 2}"
            else:
                continue
            systems.add(gesture.system)
    roles: dict[int, str] = {}
    current = MAIN
    for step in ordered:
        acted = acting.get(step.order)
        if acted is not None and acted.tab_id in of_tab:
            current = of_tab[acted.tab_id]
        roles[step.order] = current
    return roles


def undecided(steps: Sequence[Step]) -> bool:
    return any(step.tab is None for step in steps)


def unresolved(steps: Sequence[Step]) -> list[int]:
    seen: set[str] = set()
    extra = 1
    bad: list[int] = []
    for step in sorted(steps, key=lambda one: one.order):
        role = step.role
        if role.startswith(OPENED_FROM) and role.removeprefix(OPENED_FROM) not in seen:
            bad.append(step.order)
        elif role.startswith(_EXTRA) and role not in seen:
            if role != f"{_EXTRA}{extra + 1}":
                bad.append(step.order)
            extra += 1
        seen.add(role)
    return bad


__all__ = ["MAIN", "OPENED_FROM", "tab_roles", "undecided", "unresolved"]
