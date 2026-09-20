"""Whether what somebody typed is the answer to the question standing in front
of them, or something else entirely.

Until now it was neither asked nor answerable: a question standing in the
conversation took the next sentence as its value, whatever the sentence was.
That is right for `GU9` and wrong for everything else a person types while
waiting -- and what they type while waiting is usually about the waiting.

Measured on the deployment 2026-09-18. A question stood asking for
`Customer Type`. The operator, who had already sent the answer by MAIL and was
watching for it to arrive, typed `has reply arrived` into the panel to ask
this system a question. It was taken as the value, a run started one
millisecond later, and `HAS REPLY ARRIVED` was typed into a four-character box
in a live warehouse system, which refused it. Nothing in the path asked whether
that sentence was an answer, because nothing could.

Two tiers, and the cheap one first. A value is usually a value and looks like
one -- one word, no punctuation of the kind sentences have -- and a reading
spent on `S057` is a reading spent proving the obvious. What is not obviously a
value goes to the model, which is asked one question and given the words that
were actually said.

Pure. The model call lives in `application.chat.reading_an_answer`; what is
here is the shape of the question and the half that needs nobody to answer it.
"""

from __future__ import annotations

from sro.domain.chat.asking import Pending

K_ONE_WORD = 60
"""How long a single word may be and still read as a value without asking.

A code, an id, a quantity, a date. Past this a lone token is a sentence with
its spaces eaten -- a url, a pasted line -- and worth a reading."""

K_SENTENCE = "?!,;:"
"""Punctuation a value does not carry. A question mark is the clearest signal a
person ever gives that they are asking rather than answering, and this system
threw it away."""


def plainly_a_value(pending: Pending, said: str) -> bool:
    """Whether this is a value with no doubt about it -- no reading needed.

    Deliberately narrow. What it returns False for is not "not an answer": it
    is "worth asking about", and the caller asks. The cost of being narrow is a
    model call on a sentence that turned out to be a value; the cost of being
    wide is what happened on 2026-09-18.
    """
    value = said.strip()
    if not value or len(value.split()) != 1 or len(value) > K_ONE_WORD:
        return False
    if any(mark in value for mark in K_SENTENCE):
        return False
    # And it has to fit the box it is for. A lone word too long for the field
    # is already refused further down, but it is not OBVIOUSLY a value either,
    # and the question this asks is about obviousness.
    holds = pending.limits.get(pending.asking_for)
    return holds is None or len(value) <= holds


K_SAID_AS = (":", "=")
"""How somebody names the field themselves. `Address: SRO Depot One`."""


def said_as_the_value(pending: Pending, said: str) -> str | None:
    """The value where the person named the field themselves, or None.

    The way out. A reading that refuses is told to refuse when it is unsure,
    and that is the right default -- but it leaves an operator who typed a
    real value with no move except typing it again and being refused again,
    which is the loop `question` exists to not be. `Address: testing for new
    purpose` is somebody saying what the sentence is FOR, and nothing needs to
    be read to know it.

    Only the field standing in front of them. `url: http://…` typed under a
    question about Address is not a value named for Address, and taking it
    would be the substring matching this whole module replaced.
    """
    value = said.strip()
    for mark in K_SAID_AS:
        head, found, rest = value.partition(mark)
        if not found:
            continue
        return rest.strip() or None if _plainly(head) == _plainly(pending.asking_for) else None
    return None


def _plainly(name: str) -> str:
    """A field name as a person would type it. `long_description` and
    `Long Description` are the same name, and the one on the form is not
    always the one the job declares."""
    return " ".join(name.replace("_", " ").replace("-", " ").lower().split())


HOW_TO_READ = """You are told a question a warehouse system has asked somebody, and the next \
thing that person typed. Say whether what they typed is the ANSWER to that \
question.

It is an answer when it supplies the value asked for -- on its own (`GU9`), or \
in a sentence that gives it (`use N056`, `the code is S057`, `call it north \
dock`).

It is NOT an answer when the person is saying something else: asking this \
system a question ("has the reply arrived", "what are you waiting for"), \
talking about a different job, commenting, or thinking aloud. A person waiting \
for an answer to arrive from somewhere else often asks about the waiting, and \
that is not them answering.

When it is not an answer, say what it IS instead:

- `the_wait` -- about this request, or about the mail that was sent about it, \
or about what this system is doing right now. "has the reply arrived", "check \
now", "any update", "are you still going".
- `another_task` -- asking for a DIFFERENT piece of work to be done. "create \
an equipment type instead", "cancel that and show me the orders".
- `something_else` -- anything else at all.

`the_wait` is the common one, and the one to prefer when you are unsure \
between it and `another_task`: a person who is waiting is usually asking about \
the waiting, and answering them about the wait costs a sentence where starting \
the wrong job costs a record in a warehouse.

If you are not sure, say it is not an answer. A question left standing costs \
one more sentence. A wrong value is typed into a live warehouse system.

When it IS an answer, give the value alone -- not the sentence around it."""

IS_IT_AN_ANSWER_SCHEMA: dict[str, object] = {
    "type": "object",
    # No `additionalProperties`: the developer API refuses a schema carrying
    # it, and `test_no_schema_in_the_package_uses_what_the_developer_api_refuses`
    # walks every `*_SCHEMA` in the package to keep it that way.
    "required": ["answers", "value", "why", "about"],
    "properties": {
        "answers": {"type": "boolean"},
        "about": {
            "type": "string",
            "enum": ["the_wait", "another_task", "something_else"],
            "description": "What the sentence is about, when it is not an answer.",
        },
        "value": {
            "type": "string",
            "description": "The value itself when this answers, else an empty string.",
        },
        "why": {
            "type": "string",
            "description": "One short clause, for the log. Never shown to anybody.",
        },
    },
}


__all__ = [
    "HOW_TO_READ",
    "IS_IT_AN_ANSWER_SCHEMA",
    "K_ONE_WORD",
    "K_SAID_AS",
    "plainly_a_value",
    "said_as_the_value",
]
