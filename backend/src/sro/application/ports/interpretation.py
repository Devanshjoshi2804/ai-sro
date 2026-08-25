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


@dataclass(frozen=True, slots=True)
class TaskName:
    """One line a warehouse person would recognise, for a task the miner found.

    Cosmetic by construction: what a candidate *is* stays its signature, so two
    candidates named differently are still one candidate and two named the same
    are still two. Empty means the model had nothing to say, and the derived
    title stands.
    """

    title: str = ""
    because: str = ""


@dataclass(frozen=True, slots=True)
class Judgement:
    """Whether two candidates are one piece of work, and why the model thinks so.

    A suggestion about candidates, never a change to them. Nothing downstream
    reads it: a person does.
    """

    joined: bool = False
    because: str = ""


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

    async def name_task(self, evidence: str) -> TaskName:
        """Name a task the miner found, from what it is made of.

        The derived title is honest and unreadable -- `Adjust inventory on
        bf56-kms-wms-web-np2.jdadelivers.com` -- and this is the one thing a
        model is unambiguously better at. It renames nothing else: the
        signature is the identity, and it is not shown this method's answer.
        """
        ...

    async def judge_join(self, kind: str, first: str, second: str) -> Judgement:
        """Are these two candidates the same piece of work (`variant`), or two
        halves of one (`workflow`)?

        Asked only about a pair a deterministic filter already found plausible,
        because the answer is a suggestion on a screen and a model call per pair
        of a day's candidates is not something to spend by default.
        """
        ...
