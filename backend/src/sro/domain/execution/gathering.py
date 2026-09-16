"""What a search for a job's values may decide, and when it has to stop.

The pure half of the context gather. A run of a mined job needs a value for
every parameter the job declares, and until now there was exactly one source:
somebody typed them into the press. The live failure that named this was step 1
of `Create a Customer Type` -- "Open an email requesting a new customer type"
-- refusing with *"The open email is for customer type GPDP rather than the
requested ZQ41"*. The run had values and the mailbox had a different request,
and nothing could go and look.

**A value is found or it is missing, and a missing one is said.** The rule the
rest of this system keeps: `write_plan_for` refuses rather than guessing, and
so does this. A gather that returned its best effort would put a model's
reading of somebody's mail into a warehouse write, which is the one place this
codebase spends its care avoiding.

**Every value carries where it came from.** `Found.from_message` and
`Found.quoting` are not decoration: "evidence decides identity, a model writes
the sentence" is the governing rule, and a value read out of a mail is only as
good as the mail it was read from. A person asked to approve a write can go and
look at the message; an audit a month later can too.

Pure, so the loop's stopping rules can be tested without a model or a mailbox:
what counts as done, what counts as progress, and what a round may ask for next.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

K_ROUNDS = 6
"""How many times a gather may look before it gives up.

Bounded because an unbounded gather is a bill and a stall, not a better answer.
Six is enough for the shape these mailboxes actually have -- search, read the
likeliest, read one more, and a couple of narrower searches when the first
query was wrong -- and small enough that a loop going nowhere costs a handful
of calls rather than an afternoon.
"""

K_NOTE = 240
"""How much of what a search or a read answered is kept as history.

The whole mail is not kept, and that is deliberate. The failure modes of a
gather loop are context poisoning, distraction and confusion -- a model leaning
on accumulated history instead of re-reading the question -- and the mitigation
every account of them agrees on is structured note-taking rather than raw
accumulation. What the next round needs is "this search found three messages
and here are their subjects", not four screens of somebody's mail.
"""


K_HIT = 160
"""How much of ONE row of a search result is kept.

A search answers with a list, and a list trimmed by length is one row. Measured
on the deployment 2026-09-16: `search_threads` came back with five threads and
`K_NOTE` cut the whole answer after the first, mid-snippet -- so four message
ids the next round could have read were never shown to it, and it answered
`done` with nothing. "The mailbox does not hold this" said about a prompt
again, which is the exact failure the deterministic opening search was added to
end.

Per row, so every hit's id survives and no hit's body arrives whole.
"""

K_BODY = 1200
"""How much of a message a read is allowed to show the next round.

`K_NOTE` is the cap for an answer nothing is being read out of. A read is the
opposite: it is the one call whose whole point is the text a value is quoted
from, and 240 characters of it cannot hold a request that opens with a greeting
and a line of context. Still bounded -- six rounds of this is the ceiling --
but bounded at the size of a mail rather than of a snippet.
"""


@dataclass(frozen=True, slots=True)
class Found:
    """One value, and the message it was read out of."""

    value: str
    from_message: str
    quoting: str = ""
    """The span the value was read from, short. What a person checks the
    reading against without opening the mail."""


@dataclass(frozen=True, slots=True)
class Gathered:
    """What one gather came back with."""

    values: Mapping[str, Found] = field(default_factory=dict)
    missing: tuple[str, ...] = ()
    """Parameters nothing could be found for. Said rather than guessed, and
    said rather than left out: a caller has to be able to tell "there is no
    value" from "nobody looked"."""

    looked: tuple[str, ...] = ()
    """What was searched and read, in order. The audit trail for a value that
    came from somebody's mailbox rather than from a person typing it."""

    why: str = ""

    @property
    def complete(self) -> bool:
        return not self.missing


def still_wanted(wanted: Sequence[str], found: Mapping[str, Found]) -> tuple[str, ...]:
    """The parameters with no value yet, in the order the job declares them.

    Order matters for the sentence a person reads: a job that declares a code
    and a description should say them in that order every time, rather than in
    whatever order a dict happened to iterate.
    """
    return tuple(name for name in wanted if name not in found)


def keep(values: Mapping[str, Found], wanted: Sequence[str]) -> dict[str, Found]:
    """The values that answer a parameter this job actually declares.

    A model asked for two values and offering a third is not a bonus, it is a
    reading of the mail nobody asked for -- and a run that carried it would
    send a field the job never had. Dropped silently rather than refused: the
    two it was asked for may be perfectly good, and the third costs nothing to
    ignore.

    Empty and blank values are dropped for the same reason `typed_values` drops
    them: a parameter answered with "" is a parameter nobody answered.
    """
    allowed = set(wanted)
    return {
        name: found
        for name, found in values.items()
        if name in allowed and found.value.strip() and found.from_message.strip()
    }


def note(what: str, answered: str) -> str:
    """One line of history: what was asked, and a trimmed sight of the answer.

    Trimmed here rather than at the call site so every round is the same size
    in the prompt, whatever the mailbox handed back -- and trimmed by the SHAPE
    of what came back, because the three shapes a mailbox answers in do not
    survive the same cut. A list of hits is trimmed row by row so every id
    reaches the round that could read it; a message is given room for its body,
    which is the text the value gets quoted from; anything else is a snippet.
    """
    rows = _messages(answered)
    if rows is not None:
        return f"{what} -> " + (" | ".join(_row(row) for row in rows) if rows else "no messages")
    return f"{what} -> {_trimmed(answered, K_BODY if _is_a_message(answered) else K_NOTE)}"


def _messages(answered: str) -> list[dict[str, object]] | None:
    """The hits in a search answer, or `None` if this was not one."""
    try:
        said = json.loads(answered)
    except ValueError:
        return None
    if not isinstance(said, dict) or not isinstance(rows := said.get("messages"), list):
        return None
    return [row for row in rows if isinstance(row, dict)]


def _is_a_message(answered: str) -> bool:
    """One message, read whole. The answer a value is quoted out of."""
    try:
        said = json.loads(answered)
    except ValueError:
        return False
    return isinstance(said, dict) and "body" in said


def _row(row: Mapping[str, object]) -> str:
    """One hit, short enough that five of them are still a note.

    The id first and never trimmed away: it is the only part of a hit the next
    round can act on, and a row whose id was cut is a message nobody can ask
    for.
    """
    said = " ".join(
        str(row.get(part) or "").strip() for part in ("id", "subject", "snippet", "body")
    )
    return _trimmed(said, K_HIT)


def _trimmed(said: str, cap: int) -> str:
    """One line, at most `cap` characters of it."""
    said = " ".join(said.split())
    return said if len(said) <= cap else said[:cap] + "…"
