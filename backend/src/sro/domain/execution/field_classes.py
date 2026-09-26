from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from sro.domain.execution.compose import normal, screens
from sro.domain.execution.learned_step import LearnedStep, limits_for
from sro.domain.observation.gesture import Gesture, OutlineField
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.skill.learned import demanded
from sro.domain.skill.workflow import Workflow

FieldKind = Literal["required", "always", "sometimes", "never"]


def _typed_caps(workflow: Workflow, by_id: Mapping[str, Gesture]) -> dict[str, int]:
    caps: dict[str, int] = {}
    for step in workflow.steps:
        if len(step.parameters) != 1:
            continue
        (name,) = step.parameters
        for cited in step.cites:
            gesture = by_id.get(cited)
            target = gesture.action.target if gesture else None
            raw = target.attributes.get("maxlength") if target else None
            if isinstance(raw, str) and raw.isdigit():
                caps[name] = min(int(raw), caps.get(name, int(raw)))
    return caps


@dataclass(frozen=True, slots=True)
class FieldLimits:
    max_length: int | None = None
    options: tuple[str, ...] | None = None
    required_on_screen: bool | None = None

    def refuses(self, value: str) -> str:
        if self.max_length is not None and len(value) > self.max_length:
            return f"longer than {self.max_length} characters"
        if self.options is not None and normal(value) not in {normal(one) for one in self.options}:
            return "not one of " + ", ".join(self.options)
        return ""


@dataclass(frozen=True, slots=True)
class FieldClass:
    name: str
    kind: FieldKind
    labels: tuple[str, ...]
    limits: FieldLimits


def field_classes(
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
    learned: Mapping[int, LearnedStep],
    declared: Mapping[str, int] = MappingProxyType({}),
) -> tuple[FieldClass, ...]:
    on_screen: dict[str, OutlineField] = {}
    ambiguous: set[str] = set()
    for _, fields in screens(workflow, by_id):
        for one in fields:
            key = normal(one.label)
            if key in on_screen and on_screen[key] != one:
                ambiguous.add(key)
                continue
            on_screen.setdefault(key, one)
    for key in ambiguous:
        on_screen.pop(key, None)
    held = limits_for(workflow.steps, learned.values(), declared)
    typed = _typed_caps(workflow, by_id)
    found: list[FieldClass] = []
    claimed: set[str] = set()
    for parameter in workflow.parameters:
        name = parameter.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        listed = parameter.get("names")
        labels = tuple(
            dict.fromkeys(
                [name, *(str(one) for one in listed)] if isinstance(listed, list) else [name]
            )
        )
        claimed.update(normal(one) for one in labels)
        seen = next((on_screen[normal(one)] for one in labels if normal(one) in on_screen), None)
        caps = [cap for cap in (held.get(name), typed.get(name)) if cap is not None]
        kind: FieldKind = (
            "required"
            if demanded(parameter)
            else "always"
            if parameter.get("in_all") is True
            else "sometimes"
        )
        found.append(
            FieldClass(
                name,
                kind,
                labels,
                FieldLimits(
                    min(caps) if caps else None,
                    seen.options if seen else None,
                    seen.required if seen else None,
                ),
            )
        )
    for key, one in on_screen.items():
        if key not in claimed and not is_secret_field(one.label):
            found.append(
                FieldClass(
                    one.label, "never", (one.label,), FieldLimits(None, one.options, one.required)
                )
            )
    return tuple(found)
