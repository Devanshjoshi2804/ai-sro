from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.plan import HeaderPlan


@dataclass(frozen=True, slots=True)
class Options:
    url: str

    label: tuple[str, ...]

    value: str

    search: str | None = None

    headers: tuple[HeaderPlan, ...] = ()

    def __post_init__(self) -> None:
        if not self.label:
            raise InvariantViolation("options with nothing to show are a list of blank rows")
        if not self.value.strip():
            raise InvariantViolation("options must say which field carries the value")
