from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.errors import InvariantViolation

STRIP = "strip"
UPPER = "upper"
LOWER = "lower"
PAD = "pad"
PREFIX = "prefix"
SUFFIX = "suffix"

_ARITY = {STRIP: 0, UPPER: 0, LOWER: 0, PAD: 2, PREFIX: 1, SUFFIX: 1}


@dataclass(frozen=True, slots=True)
class Transform:
    ops: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self) -> None:
        for op in self.ops:
            if not op or op[0] not in _ARITY:
                raise InvariantViolation(f"unknown transformation {op!r}")
            if len(op) - 1 != _ARITY[op[0]]:
                raise InvariantViolation(
                    f"transformation {op[0]!r} takes {_ARITY[op[0]]} arguments"
                )
            if op[0] == PAD and (not op[1].isdigit() or len(op[2]) != 1):
                raise InvariantViolation("padding takes a width and a single character")

    def apply(self, value: str) -> str:
        for op in self.ops:
            match op[0]:
                case "strip":
                    value = value.strip()
                case "upper":
                    value = value.upper()
                case "lower":
                    value = value.lower()
                case "pad":
                    value = value.rjust(int(op[1]), op[2])
                case "prefix":
                    value = op[1] + value
                case "suffix":
                    value = value + op[1]
        return value

    def said_plainly(self) -> str:
        words = []
        for op in self.ops:
            match op[0]:
                case "strip":
                    words.append("trimmed")
                case "upper" | "lower":
                    words.append(f"{op[0]}cased")
                case "pad":
                    words.append(f"padded to {op[1]} with {op[2]!r}")
                case "prefix":
                    words.append(f"prefixed with {op[1]!r}")
                case "suffix":
                    words.append(f"followed by {op[1]!r}")
        return ", then ".join(words)
