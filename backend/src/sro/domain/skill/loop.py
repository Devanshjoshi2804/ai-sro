"""A block of steps the task does once per thing in a list.

"Adjust every short-shipped line on this order" is one task, and until this
existed it was not expressible: a skill was a flat list of steps, so two honest
demonstrations of it -- one order with two short lines, one with three --
disagreed about how many steps the task has, and induction refused the pair
saying they were not two runs of one task. They were.

What a loop is here is narrower than it sounds, and deliberately so. The list is
one an earlier step's *response* carried: the system said which lines are short,
and the operator acted on each. So the iteration count is the system's own
answer at run time rather than a number anybody guessed, and every value the
body sends is a field of the element it is acting on.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class Binding:
    """A parameter of the loop's body, and where in the element it comes from."""

    parameter: str
    pointer: str
    """A JSON pointer *within one element*, e.g. `/lineId`. Relative because the
    element changes every iteration and the pointer does not."""

    def __post_init__(self) -> None:
        if not self.parameter.isidentifier():
            raise InvariantViolation(f"parameter name {self.parameter!r} is not an identifier")
        if not self.pointer.startswith("/"):
            raise InvariantViolation(f"{self.pointer!r} is not a JSON pointer")


@dataclass(frozen=True, slots=True)
class Loop:
    over_step_index: int
    """The step whose response carried the list."""

    over_pointer: str
    """JSON pointer to the list in that response."""

    first_step: int
    last_step: int
    """The body, inclusive. Contiguous by construction: a demonstration does the
    steps of one iteration one after another, and a body with a hole in it would
    be two loops somebody has to be able to see separately."""

    binds: tuple[Binding, ...]

    def __post_init__(self) -> None:
        if self.first_step > self.last_step:
            raise InvariantViolation("a loop's body ends before it begins")
        if self.over_step_index >= self.first_step:
            raise InvariantViolation(
                "a loop iterates over a list an earlier step produced; "
                f"step {self.over_step_index} is not before {self.first_step}"
            )
        if min(self.over_step_index, self.first_step) < 0:
            raise InvariantViolation("step indices are non-negative")
        if not self.over_pointer.startswith("/"):
            raise InvariantViolation(f"{self.over_pointer!r} is not a JSON pointer")
        if not self.binds:
            raise InvariantViolation(
                "a loop that binds nothing would send the same call once per element, "
                "which is a task nobody demonstrated"
            )
        names = [binding.parameter for binding in self.binds]
        if len(names) != len(set(names)):
            raise InvariantViolation("a loop binds each parameter once")

    @property
    def body(self) -> range:
        return range(self.first_step, self.last_step + 1)

    def covers(self, step_index: int) -> bool:
        return self.first_step <= step_index <= self.last_step

    def describe(self) -> str:
        """For the reviewer, above the band of steps it wraps."""
        listed = self.over_pointer.rsplit("/", 1)[-1]
        return f"once for each {listed} step {self.over_step_index} found"
