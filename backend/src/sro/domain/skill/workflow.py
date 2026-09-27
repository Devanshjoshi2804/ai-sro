from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sro.domain.skill.repeats import Repeat

K_MIN_VALUE_LENGTH = 3

_DANGLING = frozenset(
    {"a", "an", "the", "and", "at", "by", "for", "from", "in", "of", "on", "to", "with"}
)


def new_workflow_id() -> str:
    return "wfl_" + secrets.token_hex(16)


@dataclass
class Step:
    order: int
    says: str
    system: str | None
    cites: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)

    uses: list[int] = field(default_factory=list)


@dataclass
class Workflow:
    id: str
    tenant: str
    title: str
    narrative: str
    systems: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    parameters: list[dict[str, object]] = field(default_factory=list)
    shape_key: list[list[str]] = field(default_factory=list)
    pass_id: str = ""

    repeat: Repeat | None = None

    signs_in: bool | None = None

    def generalise_title(self) -> None:
        seen: list[str] = []
        for parameter in self.parameters:
            values = parameter.get("seen_values")
            if isinstance(values, list):
                seen += [str(value).strip() for value in values]

        title = self.title
        for value in sorted(set(seen), key=len, reverse=True):
            if len(value) < K_MIN_VALUE_LENGTH:
                continue
            title = re.sub(rf"(?<!\w){re.escape(value)}(?!\w)", " ", title, flags=re.IGNORECASE)

        words = " ".join(title.split()).strip(" -:,").split()
        while words and words[-1].lower() in _DANGLING:
            words.pop()
        tidied = " ".join(words).strip(" -:,")
        if tidied:
            self.title = tidied


@dataclass(frozen=True, slots=True)
class Noticed:
    id: str
    title: str
    systems: tuple[str, ...]
    steps: int


def is_a_chore(workflow: Workflow) -> bool:
    return bool(workflow.signs_in)


def cited_ids(workflow: Workflow) -> set[str]:
    return {gesture_id for step in workflow.steps for gesture_id in step.cites}


def ordered_cites(workflow: Workflow) -> list[str]:
    return [cited for step in sorted(workflow.steps, key=lambda s: s.order) for cited in step.cites]


def field_key(workflow: Workflow, step: Step) -> str:
    if step.cites or len(step.parameters) != 1:
        return ""
    return next(
        (
            str(one["key"])
            for one in workflow.parameters
            if one.get("name") == step.parameters[0] and one.get("key")
        ),
        "",
    )
