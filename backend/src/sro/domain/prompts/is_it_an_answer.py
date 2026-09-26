from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = """\
You are told a question a warehouse system has asked somebody, and the next \
thing that person typed. Say whether what they typed is the ANSWER to that \
question."""

_TASK = """\
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

IS_IT_AN_ANSWER = Prompt(
    name="is_it_an_answer",
    version=1,
    model="gemini-3.8-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract="`asked` and `field` as JSON; `typed` untrusted.",
    output_schema={
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
    },
    edge_cases=(
        EdgeCase(
            '"use N056" typed to "What should Code be?"',
            "answers, value `N056`",
        ),
        EdgeCase(
            '"has the reply arrived"',
            "not an answer, `the_wait`",
        ),
        EdgeCase(
            '"create an equipment type instead"',
            "not an answer, `another_task`",
        ),
    ),
)
