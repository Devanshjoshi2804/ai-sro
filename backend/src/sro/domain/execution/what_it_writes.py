from __future__ import annotations

from collections.abc import Mapping

from sro.domain.execution.evidence import READ_METHODS, primary_gesture
from sro.domain.execution.records import names_in
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import system_of
from sro.domain.skill.reversals import K_CREATED, REMOVES
from sro.domain.skill.workflow import Workflow

DOES = {"POST": "create", "PUT": "change", "PATCH": "change", "DELETE": "remove"}


def what_it_writes(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[dict[str, str]]:
    said: list[dict[str, str]] = []
    for step in sorted(workflow.steps, key=lambda one: one.order):
        doing = primary_gesture(step, by_id)
        if doing is None:
            continue
        for call in doing.requests:
            method = call.method.upper()
            if method in READ_METHODS or not _made_something(call):
                continue
            record = _what_it_addresses(method, path_shape(call.url))
            if not record:
                continue
            said.append(
                {
                    "does": DOES.get(method, method),
                    "record": record,
                    "on": system_of(call.url) or "",
                    "step": str(step.order),
                }
            )
    return said


def _made_something(call: Call) -> bool:
    if call.method.upper() in REMOVES or call.status == K_CREATED:
        return True
    text = call.response_body.text if call.response_body is not None else None
    return bool(names_in(text))


def _what_it_addresses(method: str, shape: str) -> str:
    pieces = [one for one in shape.split("/") if one]
    if method == "DELETE" and len(pieces) > 1:
        pieces = pieces[:-1]
    named = [one for one in pieces if one != "*"]
    return named[-1] if named else ""


__all__ = ["DOES", "what_it_writes"]
