"""Skill parameters. See docs/07-adr/004-diff-parameterisation.md."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation


class ParameterKind(StrEnum):
    INPUT = "input"
    """Supplied by whoever runs the skill."""

    DERIVED = "derived"
    """Produced by an earlier step's response. Never prompted for."""


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    kind: ParameterKind
    description: str = ""
    observed_values: tuple[str, ...] = ()
    """The values that proved this field varies -- evidence for the reviewer."""

    source_step_index: int | None = None
    source_pointer: str | None = None

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise InvariantViolation(f"parameter name {self.name!r} is not a valid identifier")
        if self.kind is ParameterKind.DERIVED and self.source_step_index is None:
            raise InvariantViolation(
                f"derived parameter {self.name!r} must record which step produces it, "
                "otherwise nothing can populate it"
            )
        if self.source_step_index is not None and self.source_step_index < 0:
            raise InvariantViolation("source_step_index must be non-negative")
