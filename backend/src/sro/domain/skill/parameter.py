"""Skill parameters. See docs/07-adr/004-diff-parameterisation.md."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.lookup import Options
from sro.domain.skill.transform import Transform

_BREAKS_OUT = re.compile(r'["\\\x00-\x1f]')
"""What a value cannot carry into a quoted slot: the quote that ends the
string, the backslash that escapes whatever follows it, and the control
characters JSON does not allow inside one unescaped."""


def json_type_of(value: object) -> str:
    """What JSON calls this Python value: the vocabulary both the diff and the
    renderer use to say what a slot holds. `bool` before `int`, because in
    Python a boolean is one."""
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

    unquoted_as: str | None = None
    """The JSON type the body slot holds, where the template leaves that slot
    without quotes round it -- `"number"`, `"boolean"`, `"string"`.

    Two separate facts decide the two halves of this. Whether the slot can be
    quoted is decided by the absent form: a quoted slot renders `"null"`, the
    four characters, where the demonstration sent a JSON `null`. What a
    supplied value has to be is decided by the type the other demonstration
    actually filled -- and those disagree in both directions. A form that
    nulls an untouched *text* box gives a text field an unquoted slot, and a
    value going in there is JSON-encoded rather than pasted in raw; a number
    field whose form empties to `""` keeps its quotes, and its slot renders
    the empty string the demonstration sent.

    `None` where every site this parameter fills is quoted, which is every
    required field: nothing has shown what such a field's absence looks like,
    so its slot keeps the quotes the recorded body had."""

    def rejects(self, value: str) -> str | None:
        """Why this value cannot be put in this parameter's slot, or ``None``.

        A template substitutes as text, so whatever is supplied lands inside
        the body a demonstration sent and can write more of that body than its
        own field. An unquoted slot is the plain case: `2,"approved":true` in
        a quantity renders a valid write carrying a field nobody ever
        demonstrated, straight to a live warehouse. A quoted slot is milder
        and not safe -- a value carrying a `"` ends its own string and writes
        the rest itself -- and a control character breaks the string it sits
        in whether it is meant to or not.

        Said as a sentence rather than a boolean because the answer is shown
        to whoever supplied the value, and "no" on its own is not something
        anybody can act on.
        """
        if value == self.absent_as:
            # The form the demonstration itself sent, put here by execution
            # when nobody supplied a value. It is JSON by construction.
            return None
        match self.unquoted_as:
            case None:
                if _BREAKS_OUT.search(value):
                    return (
                        f"{self.name} is sent inside a quoted string and "
                        f"{value!r} would end it early"
                    )
            case "string":
                # Encoded on its way into the body, quotes and all, so there is
                # nothing here a value can end.
                pass
            case wanted:
                try:
                    decoded = json.loads(value)
                except json.JSONDecodeError:
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
        if self.optional and self.absent_as is None:
            raise InvariantViolation(
                f"optional parameter {self.name!r} has no absent form, so there is nothing "
                "to send when nobody supplies it"
            )
        if self.absent_as is not None:
            try:
                json.loads(self.absent_as)
            except json.JSONDecodeError as error:
                raise InvariantViolation(
                    f"absent_as for {self.name!r} is not valid JSON: {self.absent_as!r}"
                ) from error
