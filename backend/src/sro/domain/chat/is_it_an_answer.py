from __future__ import annotations

from sro.domain.chat.asking import Pending

K_ONE_WORD = 60

K_SENTENCE = "?!,;:"

K_PROSE = 200


def plainly_a_value(pending: Pending, said: str) -> bool:
    value = said.strip()
    if not value:
        return False
    holds = pending.limits.get(pending.asking_for)
    if holds is not None and holds >= K_PROSE:
        return len(value) <= holds and "?" not in value
    if len(value.split()) != 1 or len(value) > K_ONE_WORD:
        return False
    if any(mark in value for mark in K_SENTENCE):
        return False
    return holds is None or len(value) <= holds


K_SAID_AS = (":", "=")


def said_as_the_value(pending: Pending, said: str) -> str | None:
    value = said.strip()
    for mark in K_SAID_AS:
        head, found, rest = value.partition(mark)
        if not found:
            continue
        return rest.strip() or None if _plainly(head) == _plainly(pending.asking_for) else None
    return None


def _plainly(name: str) -> str:
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
    "K_PROSE",
    "K_SAID_AS",
    "plainly_a_value",
    "said_as_the_value",
]
