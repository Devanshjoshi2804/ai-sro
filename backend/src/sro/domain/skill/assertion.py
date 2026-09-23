from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.template import Template


class AssertionKind(StrEnum):
    HTTP_STATUS = "http_status"
    RESPONSE_FIELD_PRESENT = "response_field_present"
    RESPONSE_FIELD_EQUALS = "response_field_equals"
    UI_TEXT_VISIBLE = "ui_text_visible"


_POINTER_KINDS = frozenset(
    {AssertionKind.RESPONSE_FIELD_PRESENT, AssertionKind.RESPONSE_FIELD_EQUALS}
)


@dataclass(frozen=True, slots=True)
class Assertion:
    kind: AssertionKind
    expected: Template
    pointer: str | None = None

    written_by: PrincipalId | None = None

    def __post_init__(self) -> None:
        needs_pointer = self.kind in _POINTER_KINDS
        if needs_pointer and not self.pointer:
            raise InvariantViolation(f"{self.kind} assertion requires a JSON Pointer")
        if not needs_pointer and self.pointer:
            raise InvariantViolation(f"{self.kind} assertion must not carry a JSON Pointer")
        if self.kind is AssertionKind.RESPONSE_FIELD_PRESENT and not self.expected.is_literal:
            raise InvariantViolation(
                "a presence assertion cannot depend on a parameter; "
                "use RESPONSE_FIELD_EQUALS if the value matters"
            )
