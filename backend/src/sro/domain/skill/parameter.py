from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.lookup import Options
from sro.domain.skill.transform import Transform

_BREAKS_THE_LINE = re.compile(r"[\x00-\x1f]")


def _not_json(constant: str) -> float:
    raise ValueError(f"{constant} is not JSON")


def json_type_of(value: object) -> str:
    match value:
        case bool():
            return "boolean"
        case int() | float():
            return "number"
        case str():
            return "string"
        case None:
            return "null"
        case _:
            return "structure"


class ParameterKind(StrEnum):
    INPUT = "input"

    DERIVED = "derived"

    ITERATED = "iterated"


class Evidence(StrEnum):
    PROVEN = "proven"

    PROPOSED = "proposed"


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    kind: ParameterKind
    description: str = ""
    observed_values: tuple[str, ...] = ()

    evidence: Evidence = Evidence.PROVEN

    source_step_index: int | None = None
    source_pointer: str | None = None

    transform: Transform | None = None

    options: Options | None = None

    absent_as: str | None = None

    unquoted_as: str | None = None

    is_the_body: bool = False

    @property
    def optional(self) -> bool:
        return self.absent_as is not None

    @property
    def absent_value(self) -> str | None:
        if self.absent_as is None:
            return None
        decoded = json.loads(self.absent_as)
        return decoded if isinstance(decoded, str) else self.absent_as

    def rejects(self, value: str) -> str | None:
        if value == self.absent_value:
            return None
        if self.is_the_body:
            return None
        if (carried := _BREAKS_THE_LINE.search(value)) is not None:
            return (
                f"{self.name} is substituted as text wherever it is sent, and no URL or "
                f"header can carry the {carried.group()!r} in {value!r}"
            )
        match self.unquoted_as:
            case None | "string":
                pass
            case wanted:
                try:
                    decoded = json.loads(value, parse_constant=_not_json)
                except ValueError:
                    return f"{self.name} is sent as a bare {wanted} and {value!r} is not one"
                if json_type_of(decoded) != wanted:
                    return f"{self.name} is sent as a bare {wanted} and {value!r} is not one"
        return None

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
        if self.absent_as is not None:
            try:
                json.loads(self.absent_as)
            except json.JSONDecodeError as error:
                raise InvariantViolation(
                    f"absent_as for {self.name!r} is not valid JSON: {self.absent_as!r}"
                ) from error
