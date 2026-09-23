from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from sro.domain.execution.evidence import READ_METHODS
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.skill.workflow import Step, Workflow

K_SHORTEST = 3


def uses_edges(workflow: Workflow, by_id: Mapping[str, Gesture]) -> dict[int, list[int]]:
    ordered = sorted(workflow.steps, key=lambda one: one.order)
    made: dict[int, list[frozenset[str]]] = {step.order: _made_by(step, by_id) for step in ordered}
    edges: dict[int, list[int]] = {}
    for position, step in enumerate(ordered):
        took = _took(step, by_id)
        if not any(took):
            continue
        for earlier in ordered[:position]:
            if set(step.cites) & set(earlier.cites):
                continue
            if _every_doing_took_it(took, made.get(earlier.order, [])):
                edges.setdefault(step.order, []).append(earlier.order)
    return edges


def _every_doing_took_it(took: Sequence[frozenset[str]], made: Sequence[frozenset[str]]) -> bool:
    shared = [(one, other) for one, other in zip(took, made, strict=False) if one and other]
    if not shared:
        return False
    return all(one & other for one, other in shared)


def _made_by(step: Step, by_id: Mapping[str, Gesture]) -> list[frozenset[str]]:
    made: list[frozenset[str]] = []
    for gesture in _doings(step, by_id):
        minted: set[str] = set()
        for call in _writes(gesture):
            back = {value for _, value in _record(_text(call.response_body))}
            minted |= back - _sent(call)
        made.append(frozenset(minted))
    return made


def _sent(call: Call) -> frozenset[str]:
    return frozenset(value for _, value in _record(_text(call.request_body)))


def _text(body: object) -> str | None:
    said = getattr(body, "text", None)
    return said if isinstance(said, str) else None


def _took(step: Step, by_id: Mapping[str, Gesture]) -> list[frozenset[str]]:
    took: list[frozenset[str]] = []
    for gesture in _doings(step, by_id):
        values = set()
        typed = gesture.action.value
        if isinstance(typed, str) and typed.strip():
            values.add(typed.strip())
        for call in gesture.requests:
            values.update(_sent(call))
        took.append(frozenset(values))
    return took


def _doings(step: Step, by_id: Mapping[str, Gesture]) -> list[Gesture]:
    return [by_id[cited] for cited in step.cites if cited in by_id]


def _writes(gesture: Gesture) -> list[Call]:
    return [
        call
        for call in gesture.requests
        if call.response_body is not None and call.method.upper() not in READ_METHODS
    ]


def _record(text: str | None) -> list[tuple[str, str]]:
    if text is None:
        return []
    try:
        document = json.loads(text)
    except ValueError:
        return []
    if not isinstance(document, dict):
        return []
    inner = document.get("data")
    record = inner if isinstance(inner, dict) else document
    return [
        (key, value.strip())
        for key, value in record.items()
        if isinstance(value, str) and len(value.strip()) >= K_SHORTEST
    ]


__all__ = ["K_SHORTEST", "uses_edges"]
