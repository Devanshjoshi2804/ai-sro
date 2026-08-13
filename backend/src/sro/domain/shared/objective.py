"""Structured identity of a task. See docs/06-glossary.md#objective-key."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation

_REQUIRED = ("objective_type", "target_system", "entity_type", "facility")


class Direction(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class ObjectiveKey:
    """What a demonstration demonstrates. Equality is exact, never fuzzy."""

    objective_type: str
    target_system: str
    entity_type: str
    facility: str
    direction: Direction

    def __post_init__(self) -> None:
        blank = [name for name in _REQUIRED if not getattr(self, name).strip()]
        if blank:
            raise InvariantViolation(f"ObjectiveKey fields cannot be blank: {', '.join(blank)}")

    def slug(self) -> str:
        return "/".join(
            (
                self.target_system,
                self.facility,
                self.entity_type,
                self.direction.value,
                self.objective_type,
            )
        )
