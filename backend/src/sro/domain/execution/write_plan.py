from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from sro.domain.execution.evidence import READ_METHODS, recorded_call
from sro.domain.execution.planning import unreplayable
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.observation.gesture import Call, Gesture
from sro.domain.shared.hosts import system_of
from sro.domain.skill.workflow import Step, Workflow


@dataclass(frozen=True, slots=True)
class WritePlan:
    method: str
    url: str
    body: str | None
    filled: Mapping[str, str]

    confirm: Mapping[str, str]

    entry: VerifiedWrite


def seen_values(workflow: Workflow) -> dict[str, frozenset[str]]:
    found: dict[str, frozenset[str]] = {}
    for parameter in workflow.parameters:
        name = parameter.get("name")
        raw = parameter.get("seen_values")
        if not isinstance(name, str) or not name or not isinstance(raw, list):
            continue
        values = frozenset(value for value in raw if isinstance(value, str) and value.strip())
        if values:
            found[name] = values
    return found


def _same_endpoint(call: Call, other: Call) -> bool:
    return (
        call.method.upper() == other.method.upper()
        and system_of(call.url) == system_of(other.url)
        and urlsplit(call.url).path == urlsplit(other.url).path
    )


def _bodies_of(step: Step, by_id: Mapping[str, Gesture], like: Call) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for call in gesture.requests:
            if not _same_endpoint(call, like) or unreplayable(call):
                continue
            body = call.request_body
            if body is None or body.text is None:
                continue
            try:
                document = json.loads(body.text)
            except ValueError:
                continue
            if isinstance(document, dict):
                found.append(document)
    return found


def _record(text: str | None) -> dict[str, object] | None:
    if text is None:
        return None
    try:
        document = json.loads(text)
    except ValueError:
        return None
    if not isinstance(document, dict):
        return None
    inner = document.get("data")
    return inner if isinstance(inner, dict) else document


def _echoed(step: Step, by_id: Mapping[str, Gesture], like: Call) -> frozenset[str] | None:
    echoed: set[str] | None = None
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for call in gesture.requests:
            if not _same_endpoint(call, like) or unreplayable(call):
                continue
            sent = _record(call.request_body.text if call.request_body else None)
            back = _record(call.response_body.text if call.response_body else None)
            if sent is None or back is None:
                continue
            agreed = {key for key, value in sent.items() if key in back and back[key] == value}
            echoed = agreed if echoed is None else (echoed & agreed)
    return None if echoed is None else frozenset(echoed)


def _returned(step: Step, by_id: Mapping[str, Gesture], like: Call) -> frozenset[str] | None:
    returned: set[str] | None = None
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for call in gesture.requests:
            if not _same_endpoint(call, like) or unreplayable(call):
                continue
            back = _record(call.response_body.text if call.response_body else None)
            if back is None:
                continue
            held = set(back)
            returned = held if returned is None else (returned & held)
    return None if returned is None else frozenset(returned)


def _slots(bodies: list[dict[str, object]]) -> frozenset[str]:
    if len(bodies) < 2:
        return frozenset()
    shared = set(bodies[0])
    for body in bodies[1:]:
        shared &= set(body)
    return frozenset(
        key for key in shared if len({json.dumps(body[key], sort_keys=True) for body in bodies}) > 1
    )


def _taken(bodies: list[dict[str, object]], slot: str) -> set[str]:
    return {
        value if isinstance(value, str) else json.dumps(value)
        for body in bodies
        if slot in body and not isinstance(value := body[slot], dict | list)
    }


def wanted_by(
    step: Step,
    by_id: Mapping[str, Gesture],
    seen: Mapping[str, frozenset[str]],
) -> frozenset[str]:
    call = recorded_call(step, by_id)
    if call is None or call.method.upper() in READ_METHODS or unreplayable(call):
        return frozenset()
    owner = _path_owner(step, by_id, call, seen)
    bodies = _bodies_of(step, by_id, call)
    if not bodies:
        return frozenset({owner}) if owner else frozenset()
    owners: set[str] = {owner} if owner else set()
    for slot in sorted(_slots(bodies)):
        taken = _taken(bodies, slot)
        if not taken:
            continue
        claiming = [name for name, observed in seen.items() if taken <= observed]
        if len(claiming) == 1:
            owners.add(claiming[0])
    return frozenset(owners)


def _assigned(
    slots: frozenset[str],
    bodies: list[dict[str, object]],
    values: Mapping[str, str],
    seen: Mapping[str, frozenset[str]],
    elsewhere: frozenset[str] = frozenset(),
) -> dict[str, str] | None:
    claimed: dict[str, str] = {}
    placed: set[str] = set()
    for slot in sorted(slots):
        taken = _taken(bodies, slot)
        if not taken:
            continue
        owners = [name for name, observed in seen.items() if name in values and taken <= observed]
        if len({values[name] for name in owners}) > 1:
            return None
        if owners and not isinstance(bodies[0][slot], str):
            return None
        if owners:
            claimed[slot] = owners[0]
            placed.update(owners)
    if len(set(claimed.values())) != len(claimed):
        return None
    carried = {values[name] for name in placed}
    if any(
        name not in placed and name not in elsewhere and values[name] not in carried
        for name in values
    ):
        return None
    return claimed


def _owned_by_nobody_given(
    slots: frozenset[str],
    bodies: list[dict[str, object]],
    values: Mapping[str, str],
    seen: Mapping[str, frozenset[str]],
) -> frozenset[str]:
    left_out: set[str] = set()
    for slot in slots:
        taken = _taken(bodies, slot)
        owners = [name for name, observed in seen.items() if taken and taken <= observed]
        if len(owners) == 1 and not values.get(owners[0], "").strip():
            left_out.add(slot)
    return frozenset(left_out)


def learned_slots(workflow: Workflow, step: Step) -> dict[str, str]:
    keys = {
        str(one["name"]): str(one["body_key"])
        for one in workflow.parameters
        if isinstance(one.get("name"), str)
        and isinstance(one.get("body_key"), str)
        and one["body_key"]
        and one.get("slot") is not False
    }
    by_order = {one.order: one for one in workflow.steps}
    slots: dict[str, str] = {}
    order = step.order - 1
    while (
        (field := by_order.get(order)) is not None
        and not field.cites
        and len(field.parameters) == 1
    ):
        (name,) = field.parameters
        if name in keys:
            slots[name] = keys[name]
        order -= 1
    return slots


def write_plan_for(
    step: Step,
    by_id: Mapping[str, Gesture],
    values: Mapping[str, str],
    verified: tuple[VerifiedWrite, ...],
    seen: Mapping[str, frozenset[str]],
    keys: Mapping[str, str] = MappingProxyType({}),
    learned: Mapping[str, str] = MappingProxyType({}),
) -> WritePlan | None:
    call = recorded_call(step, by_id)
    if call is None or call.method.upper() in READ_METHODS:
        return None
    if unreplayable(call):
        return None
    entry = verified_write_for(call, verified)
    if entry is None:
        return None
    if any(
        needs_a_secret(gesture)
        for gesture in (by_id.get(cited) for cited in step.cites)
        if gesture is not None
    ):
        return None

    bodies = _bodies_of(step, by_id, call)
    if not bodies:
        return _path_plan(step, by_id, call, values, seen, entry)
    owner = _path_owner(step, by_id, call, seen)
    if owner and not values.get(owner, "").strip():
        return None

    slots = _slots(bodies)
    echoed = _echoed(step, by_id, call)
    also = _undemonstrated(
        {**keys, **learned},
        values,
        bodies[0],
        slots,
        _returned(step, by_id, call),
        learned=learned,
    )
    named = frozenset(keys) | {name for name, slot in learned.items() if slot in also}
    claimed = _assigned(slots, bodies, values, seen, named)
    if claimed is None:
        return None
    if not claimed:
        return None

    left_out = _owned_by_nobody_given(slots, bodies, values, seen)
    aimed = {key: value for key, value in bodies[0].items() if key not in left_out}
    for slot, parameter in claimed.items():
        aimed[slot] = values[parameter]
    aimed.update(also)
    return WritePlan(
        method=call.method.upper(),
        url=call.url,
        body=json.dumps(aimed, ensure_ascii=False),
        filled={**claimed, **{slot: slot for slot in also}},
        confirm={
            **{
                slot: values[parameter]
                for slot, parameter in claimed.items()
                if echoed is None or slot in echoed
            },
            **also,
        },
        entry=entry,
    )


def _path_owner(
    step: Step, by_id: Mapping[str, Gesture], like: Call, seen: Mapping[str, frozenset[str]]
) -> str | None:
    head = urlsplit(like.url).path.rsplit("/", 1)[0]
    taken: set[str] = set()
    for cited in step.cites:
        gesture = by_id.get(cited)
        if gesture is None:
            continue
        for call in gesture.requests:
            if call.method.upper() != like.method.upper():
                continue
            if system_of(call.url) != system_of(like.url) or call.failure_reason:
                continue
            if call.status is None or not 200 <= call.status < 300:
                continue
            path = urlsplit(call.url).path
            if path.rsplit("/", 1)[0] == head:
                taken.add(unquote(path.rsplit("/", 1)[-1]))
    if len(taken) < 2:
        return None
    claiming = [name for name, observed in seen.items() if taken <= observed]
    return claiming[0] if len(claiming) == 1 else None


def _path_plan(
    step: Step,
    by_id: Mapping[str, Gesture],
    call: Call,
    values: Mapping[str, str],
    seen: Mapping[str, frozenset[str]],
    entry: VerifiedWrite,
) -> WritePlan | None:
    owner = _path_owner(step, by_id, call, seen)
    wanted = values.get(owner, "").strip() if owner else ""
    if not wanted:
        return None
    parts = urlsplit(call.url)
    head = parts.path.rsplit("/", 1)[0]
    url = urlunsplit(parts._replace(path=f"{head}/{quote(wanted, safe='')}"))
    if verified_write_for(replace(call, url=url), (entry,)) is None:
        return None
    return WritePlan(
        method=call.method.upper(),
        url=url,
        body=call.request_body.text if call.request_body else None,
        filled={"path": owner} if owner else {},
        confirm={},
        entry=entry,
    )


def demonstrated_writes(
    workflow: Workflow, by_id: Mapping[str, Gesture]
) -> tuple[VerifiedWrite, ...]:
    seen = seen_values(workflow)
    found: list[VerifiedWrite] = []
    for step in workflow.steps:
        call = recorded_call(step, by_id)
        if call is None or call.method.upper() in READ_METHODS or unreplayable(call):
            continue
        if _path_owner(step, by_id, call, seen) is None:
            continue
        head = urlsplit(call.url).path.rsplit("/", 1)[0]
        found.append(VerifiedWrite(call.method, f"{head}/{{id}}"))
    return tuple(found)


def _undemonstrated(
    keys: Mapping[str, str],
    values: Mapping[str, str],
    body: Mapping[str, object],
    slots: frozenset[str],
    returned: frozenset[str] | None,
    *,
    learned: Mapping[str, str] = MappingProxyType({}),
) -> dict[str, str]:
    if not keys or returned is None:
        return {}
    filled: dict[str, str] = {}
    for name, slot in keys.items():
        value = values.get(name)
        if (
            value is None
            or slot in slots
            or (slot not in body and learned.get(name) != slot)
            or slot not in returned
        ):
            continue
        filled[slot] = value
    return filled


def begins_again_at(workflow: Workflow, by_id: Mapping[str, Gesture], *, stopped_at: int) -> int:
    from sro.domain.execution.evidence import writes

    ordered = sorted(workflow.steps, key=lambda step: step.order)
    before = [step for step in ordered if step.order < stopped_at]
    since = 0
    for position, step in enumerate(before):
        if writes(step, by_id):
            since = position + 1
    return before[since].order if since < len(before) else stopped_at


def scaffolding_for(
    workflow: Workflow, by_id: Mapping[str, Gesture], *, write_step: int
) -> tuple[int, ...]:
    from sro.domain.execution.evidence import writes

    ordered = sorted(workflow.steps, key=lambda step: step.order)
    before = [step for step in ordered if step.order < write_step]
    since = 0
    for position, step in enumerate(before):
        if writes(step, by_id):
            since = position + 1
    return tuple(
        step.order
        for step in before[since:]
        if not writes(step, by_id)
        and not any(
            needs_a_secret(gesture)
            for gesture in (by_id.get(cited) for cited in step.cites)
            if gesture is not None
        )
    )
