from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StepReading:
    index: int
    what: str

    why: str = ""


@dataclass(frozen=True, slots=True)
class CandidateParameter:
    name: str
    value: str

    description: str = ""
    step_index: int | None = None


@dataclass(frozen=True, slots=True)
class Reading:
    title: str = ""
    summary: str = ""
    when_to_use: str = ""
    steps: tuple[StepReading, ...] = ()
    parameters: tuple[CandidateParameter, ...] = field(default_factory=tuple)
    caveat: str = ""


class WorkflowInterpreter(Protocol):
    @property
    def available(self) -> bool: ...

    async def read(self, evidence: str) -> Reading: ...
