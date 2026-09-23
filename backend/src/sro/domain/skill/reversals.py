from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from sro.domain.execution.evidence import recorded_call
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.skill.workflow import Workflow

K_CREATED = 201

REMOVES = frozenset({"DELETE"})


def identifies(undo: Workflow, gestures: Mapping[str, Gesture]) -> frozenset[str]:
    for step in sorted(undo.steps, key=lambda one: one.order):
        call = recorded_call(step, gestures)
        if call is None or call.method.upper() not in REMOVES:
            continue
        member = _pieces(path_shape(call.url))
        if not member:
            return frozenset()
        addressed = member[-1]
        body = call.request_body.text if call.request_body is not None else None
        return frozenset(
            key
            for key, value in _record(body).items()
            if value == addressed and key.strip() and value.strip()
        )
    return frozenset()


def asks_for(undo: Workflow) -> str | None:
    named = [
        str(one["name"]).strip()
        for one in undo.parameters
        if isinstance(one, Mapping) and str(one.get("name", "")).strip()
    ]
    return named[0] if len(named) == 1 else None


def _record(text: str | None) -> dict[str, str]:
    if not text:
        return {}
    try:
        document = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(document, dict):
        return {}
    inner = document.get("data")
    record = inner if isinstance(inner, dict) else document
    return {
        key: value.strip()
        for key, value in record.items()
        if isinstance(key, str) and isinstance(value, str)
    }


def addresses(
    made: Sequence[Mapping[str, str]], by: frozenset[str] = frozenset()
) -> tuple[str, str] | None:
    named = [one for one in made if one]
    if len(named) != 1:
        return None
    only = named[0]
    if by:
        shared = [key for key in by if only.get(key, "").strip()]
        if len(shared) != 1:
            return None
        return (shared[0], only[shared[0]].strip())
    if len(only) != 1:
        return None
    ((only_field, names),) = only.items()
    return (only_field, names.strip()) if names.strip() else None


def undoes(made: Workflow, gestures: dict[str, Gesture], among: Sequence[Workflow]) -> str | None:
    creates = _endpoint(made, gestures, statuses={K_CREATED})
    if creates is None:
        return None
    collection = _pieces(creates)
    if not collection:
        return None
    for other in among:
        if other.id == made.id:
            continue
        removes = _endpoint(other, gestures, methods=REMOVES)
        if removes is None:
            continue
        member = _pieces(removes)
        if len(member) == len(collection) + 1 and member[:-1] == collection:
            return other.id
    return None


def _pieces(shape: str) -> list[str]:
    return [one for one in shape.split("/") if one]


def _endpoint(
    workflow: Workflow,
    gestures: dict[str, Gesture],
    *,
    methods: frozenset[str] | None = None,
    statuses: set[int] | None = None,
) -> str | None:
    for step in sorted(workflow.steps, key=lambda one: one.order):
        call = recorded_call(step, gestures)
        if call is None:
            continue
        if methods is not None and call.method.upper() not in methods:
            continue
        if statuses is not None and call.status not in statuses:
            continue
        return path_shape(call.url)
    return None
