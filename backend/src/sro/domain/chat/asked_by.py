"""The mails a job was asked for by, read out of the evidence.

A watch is a substring somebody typed once -- `subject contains "Short ship"`
-- and it will miss "please set up a new client category" for as long as it
exists. What decides which job a piece of text means is `understand`, and until
now it was shown each job's title, its narrative, its parameters and the values
those have taken. Never the thing that actually says what a request for this
job looks like: **the mails this operator acted on before doing it**.

They are already here. `Create a Customer Type` cites five gestures on the
operator's mailbox, and each one carries the mail's own words -- "a customer
type :- GGD / description :- leaning new SRO type 01". Nobody marked them and
nobody typed a rule: they are what the demonstration recorded, and a second
demonstration adds a sixth.

**Examples, never a rule.** A job matched because its examples are close is a
job that produces an OFFER, and the person is told which mails made it think
so. The same shape `seen_values` has one layer down: shown as what an answer
looks like, forbidden as an answer to copy.

`Delete a Customer Type` cites none, which is the honest half of this: a job
demonstrated from a page rather than from a request has no examples, gets none
invented for it, and is matched on its title and narrative exactly as before.

Pure, so what counts as one of these mails can be argued with and tested
without a mailbox, a model or a store.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow

K_EXAMPLES = 5
"""How many of a job's mails reach a prompt.

The newest, because a request that arrived this month is a better picture of
what one looks like than the same request six months ago -- and because this
goes into every reading of every sentence, where an unbounded list is a prompt
that grows with the tenant's history until it costs more than the answer.
"""

K_TEXT = 200
"""How much of one mail is kept.

A subject and the line under it. Enough to say what kind of request this is,
short enough that five of them are an example set rather than somebody's
correspondence -- and the same reasoning `gathering.K_HIT` keeps for a search
result, for the same failure modes.
"""

K_LEAST = 24
"""Shorter than this is furniture, not a request.

The cited gesture on a mailbox is usually the click that opened the message,
whose accessible name is the row's own text. Sometimes it is a toolbar: the
name reads "Inbox", "Archive", "More". Those match everything and mean nothing,
and a prompt that carried them would be teaching the model noise.
"""

K_MAILBOXES = ("mail.google.com", "outlook.office.com", "outlook.live.com")
"""Where a request arrives. Named, rather than "any host that is not the
warehouse": a job that spans two warehouse systems cites gestures on both, and
calling the second one a mailbox would put a page of stock levels into the
examples for what a request looks like. `gather.SERVER` names its one connector
for the same reason."""


@dataclass(frozen=True, slots=True)
class AskedBy:
    """One mail the operator acted on, and when they read it."""

    text: str
    at: float
    """The gesture's own clock. What orders these, and what a card saying "you
    did this after a mail like this one, on the 14th" reads."""


def mails_behind(workflow: Workflow, by_id: Mapping[str, Gesture]) -> tuple[AskedBy, ...]:
    """The mails this job was asked for by, newest first.

    Read off the gestures the job CITES rather than off everything the operator
    did that day: a cited gesture is one the miner decided was part of this
    job, and a mailbox open in another tab is not evidence about anything.

    Deduplicated by text, because one demonstration records the same row click
    several times -- five cited gestures on this deployment's own job are three
    distinct requests -- and five copies of one mail is one example wearing the
    weight of five.
    """
    found: dict[str, AskedBy] = {}
    for step in sorted(workflow.steps, key=lambda one: one.order):
        for cited in step.cites:
            gesture = by_id.get(cited)
            if gesture is None or not from_a_mailbox(gesture):
                continue
            said = _said(gesture)
            if said is None:
                continue
            # First wins on a tie, and the newest of the two is kept: the same
            # request read twice is one request, dated when it was last read.
            was = found.get(said)
            found[said] = AskedBy(text=said, at=max(gesture.at, was.at if was else gesture.at))
    newest = sorted(found.values(), key=lambda one: one.at, reverse=True)
    return tuple(newest[:K_EXAMPLES])


def texts(mails: Sequence[AskedBy]) -> list[str]:
    """Just the words, for a prompt that has no use for the clock."""
    return [one.text for one in mails]


def from_a_mailbox(gesture: Gesture) -> bool:
    """Whether this gesture happened where requests arrive."""
    where = f"{gesture.system or ''} {gesture.url or ''}"
    return any(host in where for host in K_MAILBOXES)


def only_reads_the_mail(step: Step, by_id: Mapping[str, Gesture]) -> bool:
    """Whether this step is somebody opening the request and nothing else.

    Every gesture it cites happened in a mailbox, and a step in a mailbox reads
    -- the request is already written, and what the operator did there was find
    it and look at it. Nothing about the warehouse is decided in it.

    It matters because such a step cannot be PERFORMED twice. What the recorder
    kept is the mail from that afternoon -- "a customer type :- GGD" -- so the
    plan clicks a link naming a message that will never be on the screen again,
    and on 2026-09-16 a run watching somebody's screen stopped at step 0 for
    exactly that. A job is asked for by a new mail every time; only the reading
    repeats, and the reading is done by the gather before the first step.

    A step with no citations is not one of these. An uncited step is a step
    nothing proves, and reading "all of nothing is in a mailbox" as "this is a
    mail step" would collapse it on the strength of the empty set.
    """
    cited = [by_id[one] for one in step.cites if one in by_id]
    return bool(cited) and all(from_a_mailbox(gesture) for gesture in cited)


def _said(gesture: Gesture) -> str | None:
    """What the mail said, as far as the recording holds it.

    The accessible name of what was clicked, which for a message row is the
    row's own text -- the subject and the first line, which is the whole of
    what a reader sees before opening it. Nothing else is read: the body is not
    in a gesture, and a value the operator typed is `action.value`, which
    belongs to the warehouse form rather than to the request.
    """
    target = gesture.action.target
    said = " ".join(((target.name if target else None) or "").split())
    if len(said) < K_LEAST:
        return None
    return said if len(said) <= K_TEXT else said[:K_TEXT] + "…"


__all__ = ["K_EXAMPLES", "K_LEAST", "K_TEXT", "AskedBy", "mails_behind", "texts"]
