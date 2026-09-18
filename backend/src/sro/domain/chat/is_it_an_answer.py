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

If you are not sure, say it is not an answer. A question left standing costs \
one more sentence. A wrong value is typed into a live warehouse system.

When it IS an answer, give the value alone -- not the sentence around it."""

IS_IT_AN_ANSWER_SCHEMA: dict[str, object] = {
    "type": "object",
    # No `additionalProperties`: the developer API refuses a schema carrying
    # it, and `test_no_schema_in_the_package_uses_what_the_developer_api_refuses`
    # walks every `*_SCHEMA` in the package to keep it that way.
    "required": ["answers", "value", "why"],
    "properties": {
        "answers": {"type": "boolean"},
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
    "plainly_a_value",
]
