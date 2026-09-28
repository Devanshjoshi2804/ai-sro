from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from urllib.parse import urlsplit

from sro.domain.chat.asked_by import K_MAILBOXES
from sro.domain.execution.evidence import primary_gesture, stood_on
from sro.domain.execution.what_it_writes import what_it_writes
from sro.domain.observation.gesture import Gesture
from sro.domain.observation.identity import shape_key, target_identity
from sro.domain.shared.hosts import page_of, system_of
from sro.domain.skill.learned import control_key, control_names, same_control
from sro.domain.skill.offers import K_OFFER_AFTER, Counsel
from sro.domain.skill.tabs import MAIN
from sro.domain.skill.workflow import Step, Workflow, field_key, ordered_cites


@dataclass(frozen=True, slots=True)
class Shape:
    id: str
    title: str
    starts_on: str | None
    hosts: list[str]
    shape: list[list[str]]
    parameters: list[dict[str, object]]
    writes: list[dict[str, str]] = field(default_factory=list)

    held_runs: int = 0
    offer_after: int = K_OFFER_AFTER
    quiet_until: str | None = None

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def _all_in_a_mailbox(gestures: Sequence[Gesture]) -> bool:
    for one in gestures:
        source = one.url or one.system
        if not source or urlsplit(source).netloc.split(":")[0] not in K_MAILBOXES:
            return False
    return True


def in_time_order(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[Gesture]:
    return sorted((by_id[cited] for cited in ordered_cites(workflow) if cited in by_id), key=_when)


def _when(gesture: Gesture) -> tuple[float, str]:
    return (gesture.at, gesture.id)


def cited_pairs(workflow: Workflow, by_id: Mapping[str, Gesture]) -> list[tuple[Gesture, Step]]:
    return sorted(
        (
            (by_id[cited], step)
            for step in sorted(workflow.steps, key=lambda s: s.order)
            for cited in step.cites
            if cited in by_id
        ),
        key=lambda pair: _when(pair[0]),
    )


def put_by(gesture: Gesture) -> set[str]:
    if gesture.action.secret or (gesture.action.target and gesture.action.target.secret):
        return set()
    found: set[str] = set()
    if gesture.action.value is not None:
        found.add(str(gesture.action.value).strip())
    target = gesture.action.target
    if gesture.action.kind == "click" and target and target.text:
        found.add(target.text.strip())
    return {value for value in found if value}


def typed_at(cited: list[tuple[Gesture, Step]], parameter: dict[str, object]) -> int | None:
    name = str(parameter["name"])
    values = parameter.get("seen_values")
    seen: set[str] = {str(v) for v in values} if isinstance(values, list) else set()
    for index, (gesture, step) in enumerate(cited):
        if name in step.parameters and seen & put_by(gesture):
            return index
    for index, (gesture, _) in enumerate(cited):
        if same_control((name,), control_names(gesture), theirs=control_key(gesture)) and (
            seen & put_by(gesture)
        ):
            return index
    return None


def walkable(cited: list[tuple[Gesture, Step]]) -> list[tuple[Gesture, Step]]:
    return [pair for pair in cited if target_identity(pair[0]) != "anon|scroll"]


def resumes_at(workflow: Workflow, by_id: Mapping[str, Gesture], matched: int) -> int:
    if matched <= 0:
        return 0
    walk = walkable(cited_pairs(workflow, by_id))
    if not walk:
        return 0
    _, step = walk[min(matched, len(walk)) - 1]
    return step.order


def shape_of(
    workflow: Workflow, cited: list[tuple[Gesture, Step]], *, held: int, advice: Counsel
) -> Shape | None:
    if not cited:
        return None
    gestures = [gesture for gesture, _ in cited]
    if _all_in_a_mailbox(gestures):
        return None
    by_id = {g.id: g for g in gestures}
    first_step = min(workflow.steps, key=lambda s: s.order)
    first = primary_gesture(first_step, by_id) or gestures[0]
    starts_on = page_of(first.page_url or first.url)
    hosts = sorted(stood_on(workflow, by_id))
    if system_of(starts_on) not in hosts:
        return None
    walk = walkable(cited)
    if len(walk) <= K_OFFER_AFTER:
        return None
    return Shape(
        id=workflow.id,
        title=workflow.title,
        starts_on=starts_on,
        hosts=hosts,
        shape=[list(triple) for triple in shape_key([g for g, _ in walk])],
        parameters=[
            {"name": str(p["name"]), "at": typed_at(walk, p)}
            for p in workflow.parameters
            if isinstance(p, dict) and p.get("name")
        ],
        writes=what_it_writes(workflow, by_id),
        held_runs=held,
        offer_after=max(K_OFFER_AFTER, min(advice.offer_after, len(walk) - 1)),
        quiet_until=advice.quiet_until,
    )


def where_steps_moved(
    was: Sequence[Step], now: Sequence[Step], by_id: Mapping[str, Gesture]
) -> dict[int, int]:
    places: dict[tuple[tuple[str, ...], ...], list[int]] = {}
    for step in now:
        places.setdefault(_did(step, by_id), []).append(step.order)
    moved: dict[int, int] = {}
    for step in was:
        same = places.get(_did(step, by_id))
        if same:
            moved[step.order] = same.pop(0)
    return moved


def keeping_fields(
    was: Workflow, now: Sequence[Step], by_id: Mapping[str, Gesture]
) -> tuple[list[Step], dict[int, int]]:
    fields = [one for one in was.steps if field_key(was, one)]
    moved = where_steps_moved([one for one in was.steps if one not in fields], now, by_id)
    before: dict[int, list[Step]] = {}
    waiting: list[Step] = []
    for one in sorted(was.steps, key=lambda step: step.order):
        if one in fields:
            waiting.append(one)
        elif one.order in moved and waiting:
            before.setdefault(moved[one.order], []).extend(waiting)
            waiting = []
    placed: list[tuple[Step, bool]] = []
    for one in sorted(now, key=lambda step: step.order):
        placed += [(field, True) for field in before.get(one.order, [])]
        placed.append((one, False))
    renumber = {one.order: n for n, (one, kept) in enumerate(placed) if not kept}
    steps: list[Step] = []
    for n, (one, kept) in enumerate(placed):
        if kept:
            steps.append(replace(one, order=n, tab=steps[-1].tab if steps else MAIN))
        else:
            steps.append(replace(one, order=n, uses=[renumber.get(use, use) for use in one.uses]))
    kept_at = {one.order: n for n, (one, kept) in enumerate(placed) if kept}
    return steps, {**{old: renumber[new] for old, new in moved.items()}, **kept_at}


def _did(step: Step, by_id: Mapping[str, Gesture]) -> tuple[tuple[str, ...], ...]:
    gestures = sorted((by_id[one] for one in step.cites if one in by_id), key=_when)
    return tuple(shape_key(gestures))
