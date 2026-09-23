from __future__ import annotations

from dataclasses import dataclass

from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True, slots=True)
class Binding:
    parameter: str
    pointer: str

    def __post_init__(self) -> None:
        if not self.parameter.isidentifier():
            raise InvariantViolation(f"parameter name {self.parameter!r} is not an identifier")
        if not self.pointer.startswith("/"):
            raise InvariantViolation(f"{self.pointer!r} is not a JSON pointer")


@dataclass(frozen=True, slots=True)
class Loop:
    over_step_index: int

    over_pointer: str

    first_step: int
    last_step: int

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
        listed = self.over_pointer.rsplit("/", 1)[-1]
        return f"once for each {listed} step {self.over_step_index} found"
