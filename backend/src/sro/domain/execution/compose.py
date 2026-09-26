from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from typing import Literal

from sro.domain.execution.evidence import primary_gesture, writes
from sro.domain.observation.gesture import Gesture, OutlineField
from sro.domain.observation.outline import last_outline
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.skill.aliases import JobAlias
from sro.domain.skill.checks import bindable
from sro.domain.skill.repeats import Repeat
from sro.domain.skill.workflow import Step, Workflow, field_key

SELECTS = frozenset({"combobox", "listbox"})


@dataclass(frozen=True, slots=True)
class Composed:
    name: str
    label: str
    role: str
    before: int
    options: tuple[str, ...] | None = None

    @property
    def action(self) -> str:
        return "select" if self.role in SELECTS else "type"


@dataclass(frozen=True, slots=True)
class Unplaced:
    name: str
    why: Literal["no_field", "ambiguous"]
    labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Adding:
    known: Mapping[str, str] = field(default_factory=dict)
    fresh: Mapping[str, str] = field(default_factory=dict)


def normal(label: str) -> str:
    return " ".join(label.replace("*", " ").split()).casefold()


def alias_map(aliases: Iterable[JobAlias]) -> dict[str, str]:
    return {normal(one.wording): one.field for one in aliases}


def _screens(
    workflow: Workflow, by_id: Mapping[str, Gesture]
) -> list[tuple[Step, tuple[OutlineField, ...]]]:
    gestures = sorted(by_id.values(), key=lambda one: one.at)
    found: list[tuple[Step, tuple[OutlineField, ...]]] = []
    for step in sorted(workflow.steps, key=lambda one: one.order):
        primary = primary_gesture(step, by_id)
        if primary is None or not writes(step, by_id):
            continue
        outline = last_outline(primary, [one for one in gestures if one.at < primary.at])
        if outline is not None:
            found.append((step, outline.fields))
    return found


def choices(workflow: Workflow, by_id: Mapping[str, Gesture]) -> dict[str, Composed]:
    hits = [(step, one) for step, fields in _screens(workflow, by_id) for one in fields]
    found: dict[str, Composed] = {}
    twice: set[str] = set()
    for step, one in hits:
        same = [(at, it) for at, it in hits if normal(it.label) == normal(one.label)]
        role = [at for at, it in same if it.role == one.role]
        if len(same) == 1:
            said = one.label
        elif len(role) == 1:
            said = f"{one.label} ({one.role})"
        elif [at.order for at in role].count(step.order) == 1:
            said = f"{one.label} ({one.role}, before '{step.says}')"
        else:
            continue
        if said in found:
            twice.add(said)
        found[said] = Composed("", one.label, one.role, step.order, one.options)
    return {said: one for said, one in found.items() if said not in twice}


def placed(
    workflow: Workflow, by_id: Mapping[str, Gesture], name: str, label: str
) -> tuple[Composed, ...]:
    return tuple(
        Composed(name, one.label, one.role, step.order, one.options)
        for step, fields in _screens(workflow, by_id)
        for one in fields
        if normal(one.label) == normal(label)
    )


def compose(
    workflow: Workflow, by_id: Mapping[str, Gesture], values: Mapping[str, str]
) -> tuple[tuple[Composed, ...], tuple[Unplaced, ...]]:
    filled = bindable(workflow, by_id)
    composed: list[Composed] = []
    unplaced: list[Unplaced] = []
    for name, value in values.items():
        if name in filled or not value.strip() or is_secret_field(name):
            continue
        hits = placed(workflow, by_id, name, name)
        if len(hits) == 1:
            composed.append(hits[0])
        else:
            why: Literal["no_field", "ambiguous"] = "ambiguous" if hits else "no_field"
            unplaced.append(Unplaced(name, why, tuple(choices(workflow, by_id))))
    return tuple(composed), tuple(unplaced)


def field_of(workflow: Workflow, by_id: Mapping[str, Gesture], step: Step) -> Composed | None:
    name = step.parameters[0]
    said = next(
        (
            str(names[0])
            for one in workflow.parameters
            if one.get("name") == name and isinstance(names := one.get("names"), list) and names
        ),
        name,
    )
    later = sorted(
        (one for one in workflow.steps if one.order > step.order and not field_key(workflow, one)),
        key=lambda one: one.order,
    )
    write = later[0] if later and writes(later[0], by_id) else None
    hits = [
        one
        for one in placed(workflow, by_id, name, said)
        if write is not None and one.before == write.order
    ]
    return hits[0] if len(hits) == 1 else None


def keyed(extra: Mapping[str, str], adding: Adding) -> dict[str, str] | None:
    found: dict[str, str] = {}
    for key, said in extra.items():
        named = adding.known.get(key)
        could = [named] if named is not None else [n for n in adding.fresh if n not in found]
        holding = [name for name in could if said and adding.fresh.get(name) == said]
        if len(holding) != 1 or holding[0] in found:
            return None
        found[holding[0]] = key
    return found


def with_field(
    workflow: Workflow, composed: Composed, *, key: str, value: str
) -> tuple[Workflow, dict[int, int]]:
    moved = {
        step.order: step.order + 1 if step.order >= composed.before else step.order
        for step in workflow.steps
    }
    system = next((one.system for one in workflow.steps if one.order == composed.before), None)
    steps = [
        replace(step, order=moved[step.order], uses=[moved.get(one, one) for one in step.uses])
        for step in workflow.steps
    ]
    steps.append(
        Step(
            order=composed.before,
            says=f"Fill {composed.label}",
            system=system,
            parameters=[composed.name],
        )
    )
    repeat = workflow.repeat
    if repeat is not None:
        repeat = Repeat(
            moved.get(repeat.first_step, repeat.first_step),
            moved.get(repeat.last_step, repeat.last_step),
        )
    parameter: dict[str, object] = {
        "name": composed.name,
        "required": False,
        "seen_values": [value],
        "names": [composed.label],
        "key": key,
    }
    grown = replace(
        workflow,
        steps=sorted(steps, key=lambda one: one.order),
        parameters=[
            *(one for one in workflow.parameters if one.get("name") != composed.name),
            parameter,
        ],
        repeat=repeat,
    )
    return grown, moved
