"""What was done to a value between the response that produced it and the call
that sent it.

A derived parameter is a value an earlier step's response handed to a later one.
Often it is handed over verbatim, and then there is nothing here to record. Just
as often it is not: the WMS answers `42` and the ERP is sent `LPN-00042`, and a
system that can only recognise the verbatim case asks an operator for a number
the previous step already knew.

Small on purpose. Every operation here is one a person can read off two examples
and check by eye, because a transformation nobody can check is a guess with a
data structure around it. Anything more expressive belongs behind a
demonstration, not behind an inference.
"""

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
    """An ordered list of operations, applied left to right.

    Stored as plain strings rather than as a class hierarchy because a skill
    version is a document that has to survive being read back by a later version
    of this code: `("prefix", "LPN-")` still means what it meant.
    """

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
        """For the reviewer, who has to agree this is what the task does."""
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
