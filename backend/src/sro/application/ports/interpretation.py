"""Reading one demonstration as a workflow.

The two-run diff proves things. This does not: it *reads* a single
demonstration -- the gestures, the calls, the responses, the narration -- and
says what the operator was doing and which values look like inputs. That is a
model's opinion, and everything it produces is labelled as one.

What it is allowed to change is nothing. The calls stay exactly as captured; the
interpretation adds a title, a description, a sentence per step, and candidate
parameters. A candidate whose value never appears in the evidence is discarded
before it reaches the skill, because a parameter nobody can point at in a
payload is a hallucination with a name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StepReading:
    index: int
    what: str
    """One sentence: what this step did, in the warehouse's own words."""

    why: str = ""
    """Why it was done, where the narration or the response says so."""


@dataclass(frozen=True, slots=True)
class CandidateParameter:
    name: str
    value: str
    """The literal seen in this run. Checked against the captured payloads
    before it is believed."""

    description: str = ""
    step_index: int | None = None


@dataclass(frozen=True, slots=True)
class Reading:
    """What one demonstration appears to have been."""

    title: str = ""
    summary: str = ""
    when_to_use: str = ""
    steps: tuple[StepReading, ...] = ()
    parameters: tuple[CandidateParameter, ...] = field(default_factory=tuple)
    caveat: str = ""
    """Anything the model could not account for. Kept, because "I did not
    understand step 4" is the most useful thing it can say."""


class WorkflowInterpreter(Protocol):
    @property
    def available(self) -> bool: ...

    async def read(self, evidence: str) -> Reading:
        """Interpret one demonstration, rendered as text.

        Takes text rather than the aggregate on purpose: what gets sent to a
        hosted model is assembled and redacted by the caller, so the adapter has
        no way to widen it.
        """
        ...
