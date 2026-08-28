"""Skill parameters. See docs/07-adr/004-diff-parameterisation.md."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.lookup import Options
from sro.domain.skill.transform import Transform


class ParameterKind(StrEnum):
    INPUT = "input"
    """Supplied by whoever runs the skill."""

    DERIVED = "derived"
    """Produced by an earlier step's response. Never prompted for."""

    ITERATED = "iterated"
    """A field of the thing a loop is acting on this time round.

    Never prompted for and never read straight out of a response either: the
    value is whichever element of the list the loop is on, so it exists only
    inside the loop's body and only once the list has arrived."""


class Evidence(StrEnum):
    """How firmly we know this is a parameter rather than a constant."""

    PROVEN = "proven"
    """Two demonstrations disagreed here. A fact, not a reading."""

    PROPOSED = "proposed"
    """One demonstration, and a model's reading of it. One value is just a
    value: nothing about a single run distinguishes the LPN the operator chose
    from the site code that is the same every time. Proposed parameters are
    shown as such, are confirmed by whoever runs the skill, and become proven
    the first time a second demonstration disagrees with the first."""


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    kind: ParameterKind
    description: str = ""
    observed_values: tuple[str, ...] = ()
    """The values that proved this field varies -- evidence for the reviewer."""

    evidence: Evidence = Evidence.PROVEN

    source_step_index: int | None = None
    source_pointer: str | None = None

    transform: Transform | None = None
    """What was done to the value between the response and the call that sent it.

    Absent for the ordinary case, where it was handed over unchanged. Present
    where two demonstrations agreed on a reformatting -- `42` answered, `LPN-00042`
    sent -- which is the shape of most work that crosses two systems."""

    options: Options | None = None
    """Where this value can be chosen from, where the screen chose it.

    A parameter with options is a dropdown, not a text box: the console fetches
    them from the system itself when it draws the field, so the operator picks a
    supplier's address the way they would have on the screen instead of
    reciting an id."""

    optional: bool = False
    """Whether a run may leave this out.

    Proved, not assumed: one demonstration filled this field and the other left
    it alone, and both created the record. A field filled in every
    demonstration there is stays required, because nothing has shown the task
    works without it."""

    absent_as: str | None = None
    """What to send when nobody supplies it, exactly as the demonstration that
    skipped it sent -- `"null"` for a number the form nulls, `""` for a text
    control it empties. Never chosen here: a form that wants one and gets the
    other rejects the write."""

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
