"""Asking for what a job still needs, one question at a time.

A job is offered as a decision: *"Create a Customer Type — want me to do it?"*
The press means yes, and after it the run goes and looks for whatever nobody
typed -- in the mail that asked for the job, and in time in the systems
themselves. Mostly it finds them. When it does not, the run has a choice
between two bad answers and this module is the third one.

The two bad answers, both of which this system has shipped:

**Boxes on the card.** One text input per declared parameter, drawn before
anybody knows whether a value is needed at all, and the press disabled until
they are full. It asks everybody for what it usually finds by itself, and on
`Create a Customer Type` it asked four times for two values, because that job
declares each field twice -- the label a person reads and the body key a form
posts.

**Stopping.** "nobody gave a value for X, and your mail does not say either."
True, and the end of it: the operator starts over, and the run that knew
everything except one word is gone.

So the third answer is a conversation. The run ends, and what it could not
find becomes a question in the operator's own thread -- one question, for one
value, in words. They answer, the next question comes, and when the last one
lands the job runs with the full set and the press they already gave.

**The state is the thread.** Not a session, not a row: every question carries
what is established so far and what is still missing, so the answer to it is
readable off the last thing the assistant said. An operator who answers two
questions over five minutes does not depend on a process staying up, and a
second browser reading the same thread sees the same state.

Pure: given the messages, say what is being waited on. Nothing here reads a
clock, a repository or a model.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sro.domain.chat.thread import Message, Speaker

NEEDS = "needs_values"
"""The decision kind of a question waiting on a value. Named here because two
sides read it: the door that writes it and the panel that draws it."""

K_SAID = 200
"""How much of one answer is taken as a value. A parameter is a customer type
or a description, and a paragraph pasted into the panel is somebody talking,
not a field. Long enough for a description, short enough that a mail body
pasted whole cannot become a warehouse record."""

LET_GO = frozenset(
    {
        "no",
        "no thanks",
        "nope",
        "stop",
        "cancel",
        "forget it",
        "never mind",
        "nevermind",
        "drop it",
        "leave it",
    }
)
"""Answers that are not values. Without this "no" becomes the customer type.

Matched whole and lowercased, never by substring: "no" is a refusal and
"NORTH DOCK" is a dock. A sentence that merely contains one of these words is
a value -- an operator who means to stop can say the word by itself, and a run
refused because a description said "leave it in receiving" is worse than one
question too many.
"""


@dataclass(frozen=True)
class Pending:
    """A job that has been said yes to and is short of values.

    `values` is everything established so far, `missing` what is still to ask
    about, in the order it will be asked. `items` rides along untouched: a job
    done once per thing in a list is still that job, and the values asked for
    here are the ones shared across all of them.
    """

    workflow_id: str
    title: str
    values: Mapping[str, str]
    missing: tuple[str, ...]
    items: tuple[Mapping[str, str], ...] = ()
    watched: bool = True

    @property
    def asking_for(self) -> str:
        """The one value this question is about."""
        return self.missing[0] if self.missing else ""

    @property
    def ready(self) -> bool:
        return not self.missing


def question(pending: Pending) -> str:
    """The question, in words rather than as a field name and a box.

    The name as the job declares it, because that is the word the operator
    will see again on the form and in the record. A prettier rendering of
    `customertype-longDescription` would be this system choosing a name for a
    field somebody else named.
    """
    return f"What should {pending.asking_for} be?"


def pending_job(messages: Sequence[Message]) -> Pending | None:
    """What the conversation is waiting on, or None.

    The LAST thing the assistant decided, and only that. Each answer produces a
    new decision carrying the remaining questions, so the most recent one is
    the whole state -- and a thread that went on to talk about something else
    has a newer decision that is not a question, which ends the waiting exactly
    as it should. Reading further back would let a job abandoned twenty minutes
    ago claim the next sentence somebody typed.
    """
    for message in reversed(messages):
        decision = message.decision
        if message.speaker is not Speaker.ASSISTANT or not decision:
            continue
        if decision.get("kind") != NEEDS:
            return None
        listed = decision.get("missing")
        missing = tuple(str(one) for one in listed) if isinstance(listed, list | tuple) else ()
        if not missing or not decision.get("workflow_id"):
            return None
        items = decision.get("items")
        return Pending(
            workflow_id=str(decision["workflow_id"]),
            title=str(decision.get("title") or ""),
            values=_strings(decision.get("values")),
            missing=missing,
            items=tuple(_strings(one) for one in items) if isinstance(items, list | tuple) else (),
            watched=bool(decision.get("watched", True)),
        )
    return None


def _strings(said: object) -> dict[str, str]:
    """A decision's mapping, as strings. A decision is JSON off a row and its
    values are `object` to anything reading it honestly."""
    return {str(key): str(value) for key, value in said.items()} if isinstance(said, dict) else {}


def let_go(said: str) -> bool:
    """Whether that answer was somebody calling it off."""
    return said.strip().strip(".!").lower() in LET_GO


def answered(pending: Pending, said: str) -> Pending:
    """The same job with this answer in it, and the next question outstanding.

    The answer fills the name that was asked about **and every name that is
    that same field under another spelling**. `Create a Customer Type` declares
    `Customer Type` and `customertype-customerType`, which is one value and two
    parameters, and asking twice for one word is the form this conversation
    exists to replace.

    ponytail: the twin rule is a suffix match on the normalised names, which is
    a patch over a mining defect -- the job should declare each field once. When
    mining stops writing both, delete `_twins` and this paragraph.
    """
    value = said.strip()[:K_SAID]
    if not value or not pending.missing:
        return pending
    asked = pending.missing[0]
    filled = {asked, *_twins(asked, pending.missing[1:])}
    return Pending(
        workflow_id=pending.workflow_id,
        title=pending.title,
        values={**pending.values, **dict.fromkeys(filled, value)},
        missing=tuple(name for name in pending.missing if name not in filled),
        items=pending.items,
        watched=pending.watched,
    )


def _twins(asked: str, rest: Iterable[str]) -> set[str]:
    """The other names for the field just answered.

    `Customer Type` and `customertype-customerType` normalise to `customertype`
    and `customertypecustomertype`, and one ends with the other. Direction
    matters: the body key carries the form's name as a prefix, so the longer
    name ends with the shorter. Nothing matches when neither contains the
    other, which is the ordinary case of two unrelated fields.
    """
    one = _plain(asked)
    return {other for other in rest if _shares(one, _plain(other))}


def _plain(name: str) -> str:
    return "".join(letter for letter in name.lower() if letter.isalnum())


def _shares(one: str, other: str) -> bool:
    if not one or not other:
        return False
    return one.endswith(other) or other.endswith(one)
