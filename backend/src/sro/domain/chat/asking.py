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
from dataclasses import dataclass, field

from sro.domain.chat.thread import Message, Speaker

NEEDS = "needs_values"
"""The decision kind of a question waiting on a value. Named here because two
sides read it: the door that writes it and the panel that draws it."""

JOB = "job"
"""The decision kind of a job this conversation has offered to do. The panel
builds its card from one; a sentence agreeing with one starts it."""

SAID_YES = frozenset(
    {
        "yes",
        "yes please",
        "yep",
        "yeah",
        "ok",
        "okay",
        "sure",
        "go",
        "go on",
        "go ahead",
        "do it",
        "do it now",
        "please do",
        "pls do",
        "plz do",
        "run it",
        "run it now",
        "yes do it",
        "yes run it",
        "that one",
    }
)
"""Answers that mean "the thing you just offered".

Measured on the deployment, 2026-09-17 at 03:17. The assistant said "Create a
Customer Type does that -- say the word and I will run it", the operator said
"pls do", and the reply was "Nothing has been taught for that": the sentence
went to the skills resolver, which had never heard of it, because nothing was
holding on to what had just been offered. A system that asks for a word and
then does not know the word is worse than one that never asked.

Matched whole and lowercased, like `LET_GO`. "do it" is a yes; "do it for the
red ones instead" is a new sentence and is placed as one.
"""

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
    can_find: bool = False
    """Whether a run of this job can go and look for what is missing. On an
    offer it decides what a yes means: start it and let the run find them, or
    ask for the first one here."""

    mail_thread: str = ""
    """The outside conversation this job was asked for in, where there is one.

    Carried so the run an ANSWER starts is findable by a reply to that mail,
    the same as one a press starts. Without it the two doors disagree about
    something a person cannot see: press the card and the run answers to the
    thread, answer the question and it answers to nobody -- and 3.2 exists
    precisely so the person who knows the missing value, who is usually
    whoever sent the request, can say it where they are."""

    offered: tuple[tuple[str, str], ...] = ()
    """Fields this job can fill that the page does not ask for, and what each
    held last time.

    Since 2026-09-22 an optional field no longer stops a run -- see
    `LearnedParameter.required` -- and the step that fills it is skipped where
    nothing was given for it. Skipping it silently is the other half of the
    old mistake: the operator is never told the job could have set Department,
    so a field they DID want goes unfilled and nothing on the screen says it
    was ever possible.

    Said once, in the opening, with what it was last time so the offer is
    answerable without going to look. Not asked for one at a time: they are
    optional, and four questions nobody has to answer is how a person learns
    to type "no" without reading.

    An answer arrives through the door that already exists -- "Department: IN"
    is taken by the same path that takes any named value -- so nothing here
    needs a new kind of reply.
    """

    from_step: int = 0
    """Which step of the job the run that asked this had reached.

    A run that comes up short ENDS -- it must, because a write with a blank in
    it is a wrong record -- and the answer starts another one. Starting that
    one at step 0 re-walks everything the first one did: on `Create a Customer
    Type` it re-opens the mail, re-navigates, presses Add again and re-types
    both fields, to reach the box it stopped in front of.

    So the run says where it stopped and the next one begins there. Safe by
    construction rather than by hope: `run.needs` is set only at the two
    truncation stops and by a gather that came back short, and all three
    happen BEFORE the step's command goes out. The step named here is one that
    did not complete, every step under it did, and every step over it never
    ran -- which is exactly what `from_step` means.

    Zero for a question asked about an OFFER, which has no run behind it yet
    and nothing to resume."""

    limits: Mapping[str, int] = field(default_factory=dict)
    """What the box behind a name will hold, where anything knows.

    Carried so the question can say WHY it is being asked. A person sent a
    value, it will not fit, and "What should Customer Type be?" gets the same
    ten characters back -- they have no way to know the box takes four, because
    the browser truncates in silence and nothing else has said so.

    It is also what makes the asking a loop rather than one question: an answer
    that still will not fit is not an answer, and `answered` keeps asking.
    Empty for every name nothing has measured or documented, which is most."""

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

    And the limit where there is one, because the two things that bring a job
    here want two different questions. A value nobody could find is "what
    should X be?". A value that will not fit is a person who HAS an answer and
    has been given no reason to change it: asked the first way they send the
    same ten characters back, and the loop is one nobody can get out of.
    """
    asked = pending.asking_for
    holds = pending.limits.get(asked)
    if holds is None:
        return f"What should {asked} be?"
    return f"{asked} takes {holds} characters. What should it be?"


def unusable(values: Mapping[str, str], limits: Mapping[str, int]) -> tuple[str, ...]:
    """Names holding a value the box will not take, in the order given.

    A value that will not fit is not a value. It is as outstanding as a name
    nobody supplied at all -- more so, because the person believes they have
    already answered it -- and the only difference is what the question has to
    say to get a usable answer back.

    The run path has always folded these together: `_too_long_for` puts the
    names on `run.needs` beside the ones nothing could find, and one question
    loop handles both. This is the same rule for an offer, which has not run
    and so has no `needs` of its own to put them on.
    """
    return tuple(
        name
        for name, value in values.items()
        if name in limits and isinstance(value, str) and len(value) > limits[name]
    )


K_SHOWN = 90
"""How much of an established value the opening repeats back.

Enough to recognise a request by, not enough to fill the panel: a description
may hold two thousand characters and a person checking which job this is about
needs the first line of it."""


def opening(pending: Pending, about: str = "") -> str:
    """The first thing said when a job is taken up but cannot yet run.

    The question alone is `Customer Type takes 4 characters. What should it
    be?`, and in a conversation that is a sentence with no subject. The card it
    came from said which request it was about, what had been read out of the
    mail, and what would not fit -- and then handed over to a thread that knew
    none of it. Somebody who steps away for a minute comes back to a bare
    question about a field, with four identical-looking ones above it.

    So the opening carries what the card carried: which job, which request
    where there is one to name, what is already established, and what is being
    asked for -- and then the question itself, which every answer after this
    one gets on its own.

    `about` is what the request was called. Empty for a job nobody named --
    a press on a page rather than a mail -- and the sentence simply does not
    claim one.
    """
    said = [f"{pending.title}{f' — {about}' if about.strip() else ''}."]
    held = [
        f"{name}: {_short(value)}"
        for name, value in pending.values.items()
        if name not in pending.missing and value.strip()
    ]
    if held:
        said.append("I have " + "; ".join(held) + ".")
    # What was supplied and will not fit is a different sentence from what was
    # never supplied, and running them together is how somebody re-sends the
    # value they already sent.
    for name in pending.missing:
        holds, was = pending.limits.get(name), pending.values.get(name, "")
        if holds is not None and was.strip():
            said.append(f"The request said {name} {_short(was)}, which is {len(was)} characters.")
    # What it could also set, once, before the question it must have answered.
    #
    # Before rather than after, because the question is what the next sentence
    # answers and a question buried above an offer gets the offer's answer.
    if also := also_set(pending):
        said.append(also)
    said.append(question(pending))
    return " ".join(said)


def also_set(pending: Pending) -> str:
    """What this job could ALSO fill, which nothing has to answer.

    Public because two doors ask the same question in different words and both
    have to make the same offer: `opening` for a job taken up from an offer,
    and `_ask_for_values` for a run that got half way and came up short. A
    sentence written twice is a sentence that drifts, and the drift here would
    be one door telling an operator about Department and the other not.

    Empty where there is nothing to offer, so a caller can append it without
    asking.
    """
    if not pending.offered:
        return ""
    return (
        "I can also set "
        + _listed([name for name, _ in pending.offered])
        + _last_time(pending.offered)
        + " — say so if you want any, or I will run without."
    )


def _listed(names: Sequence[str]) -> str:
    """`a`, `a and b`, `a, b and c`. A comma before the last is how a list of
    two reads as a list of three."""
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _last_time(offered: Sequence[tuple[str, str]]) -> str:
    """What each was last time, where anything was. An offer a person cannot
    answer without going to look at the last record is an offer they decline.
    """
    seen = [f"{name}: {_short(value)}" for name, value in offered if value.strip()]
    return f" — last time {'; '.join(seen)}" if seen else ""


def shortened(value: str) -> str:
    """One value, trimmed to something a sentence can carry. Named rather than
    private because the mail to the asker renders the same values and must trim
    them the same way -- two answers to "how much of this do we repeat back"
    is how one surface quotes a paragraph and another quotes a line."""
    return _short(value)


def _short(value: str) -> str:
    said = " ".join(value.split())
    return said if len(said) <= K_SHOWN else said[:K_SHOWN] + "…"


def too_long_for(pending: Pending, said: str) -> int | None:
    """The limit this answer breaks, or None if it fits.

    Measured on the value as it will be TAKEN -- trimmed and cut to `K_SAID` --
    rather than as it was typed, so the answer this reports on is the one that
    would be sent.
    """
    asked = pending.asking_for
    holds = pending.limits.get(asked)
    value = said.strip()[:K_SAID]
    return holds if holds is not None and len(value) > holds else None


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
            offered=_pairs(decision.get("offered")),
            items=tuple(_strings(one) for one in items) if isinstance(items, list | tuple) else (),
            watched=bool(decision.get("watched", True)),
            limits=_numbers(decision.get("limits")),
            from_step=_step(decision.get("from_step")),
            mail_thread=str(decision.get("mail_thread") or ""),
        )
    return None


def _pairs(said: object) -> tuple[tuple[str, str], ...]:
    """The offered fields as the decision stores them: a list of two-item
    lists, because JSON has no tuples. Anything else is nothing -- an offer
    read out of a shape nobody wrote is an offer to fill a field that may not
    exist."""
    if not isinstance(said, list | tuple):
        return ()
    return tuple(
        (str(one[0]), str(one[1]))
        for one in said
        if isinstance(one, list | tuple) and len(one) == 2
    )


def _step(said: object) -> int:
    """Which step a stored decision names, or 0. A bool is an int in Python and
    `from_step: true` would otherwise resume a job at its second step."""
    if isinstance(said, bool) or not isinstance(said, int) or said < 0:
        return 0
    return said


def _numbers(said: object) -> dict[str, int]:
    """A decision's limits, as whole numbers. JSON off a row, so anything that
    is not a usable count is not one -- a bool is an int in Python, and
    `limits: {"Code": true}` would otherwise read as a one-character field."""
    if not isinstance(said, dict):
        return {}
    return {
        str(key): value
        for key, value in said.items()
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    }


def _strings(said: object) -> dict[str, str]:
    """A decision's mapping, as strings. A decision is JSON off a row and its
    values are `object` to anything reading it honestly."""
    return {str(key): str(value) for key, value in said.items()} if isinstance(said, dict) else {}


def let_go(said: str) -> bool:
    """Whether that answer was somebody calling it off."""
    return _plainly(said) in LET_GO


def said_yes(said: str) -> bool:
    """Whether that sentence agrees with what was just offered."""
    return _plainly(said) in SAID_YES


def _plainly(said: str) -> str:
    """One answer, as it is matched: lowercased, without the punctuation
    somebody types around a short word."""
    return " ".join(said.strip().strip(".!?,").lower().split())


def _items(said: object) -> tuple[Mapping[str, str], ...]:
    """The things a job would be done for, as strings. A decision is JSON off a
    row, so its `items` is `object` to anything reading it honestly."""
    return tuple(_strings(one) for one in said) if isinstance(said, list | tuple) else ()


def offered_job(messages: Sequence[Message]) -> Pending | None:
    """The job this conversation has just offered to do, if it is still the
    last thing said.

    The same reading as `pending_job` and for the same reason: the newest
    assistant decision is the whole state, so a job offered twenty minutes ago
    and talked past cannot claim the next sentence. A question waiting on a
    value is NOT one of these -- `pending_job` owns that, and a sentence there
    is the value rather than a yes.
    """
    for message in reversed(messages):
        decision = message.decision
        if message.speaker is not Speaker.ASSISTANT or not decision:
            continue
        if decision.get("kind") != JOB or not decision.get("workflow_id"):
            return None
        listed = decision.get("missing")
        return Pending(
            workflow_id=str(decision["workflow_id"]),
            title=str(decision.get("title") or ""),
            values=_strings(decision.get("values")),
            missing=tuple(str(one) for one in listed) if isinstance(listed, list | tuple) else (),
            items=_items(decision.get("items")),
            watched=bool(decision.get("watched", True)),
            can_find=bool(decision.get("can_find", False)),
        )
    return None


def answered(pending: Pending, said: str) -> Pending:
    """The same job with this answer in it, and the next question outstanding.

    The answer fills the name that was asked about **and every name that is
    that same field under another spelling**. `Create a Customer Type` declares
    `Customer Type` and `customertype-customerType`, which is one value and two
    parameters, and asking twice for one word is the form this conversation
    exists to replace.

    ponytail: the twin rule is a suffix match on the normalised names, and the
    defect behind it is fixed -- mining records every name a control answers to
    and folds the entries a job already has (`domain/skill/learned.py`). This
    stays for the jobs whose fold has not happened yet: a job is repaired by
    the next pass that recognises it, and until then its offer still carries
    two names for one field. Delete it once no stored job has a pair.
    """
    value = said.strip()[:K_SAID]
    if not value or not pending.missing:
        return pending
    # An answer the box still will not hold leaves the question standing.
    #
    # The alternative is accepting it and stopping the run in front of the
    # form, which is the whole of what asking here was meant to replace: the
    # person is at the keyboard, and telling them NOW costs one more sentence
    # where telling them later costs the job.
    if too_long_for(pending, said) is not None:
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
        limits=pending.limits,
        from_step=pending.from_step,
        mail_thread=pending.mail_thread,
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
