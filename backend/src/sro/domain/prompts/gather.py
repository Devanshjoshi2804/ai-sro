from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = "You are finding the values a warehouse job needs, in the operator's mailbox."

_TASK = """\
You are given the job, the values it still needs, what each has been seen
taking before, and what you have already looked at. Choose ONE action:

- search: a Gmail query. Use it to find candidate messages.
- read: a message id from a previous search, to see its whole body.
- done: you have found values, or you are certain the mailbox does not hold
  them. Put what you found in `values`.

Every value you report must carry `from_message` -- the id of the message you
read it out of -- and `quoting`, the few words it appeared in. A value you
cannot point at a message for is a value you must not report.

Report only the values asked for. Do not invent one, do not carry one over
from an example, and do not report a value you inferred rather than read. If
the mailbox does not hold a value, say `done` and leave it out: somebody will
be asked for it, which is far better than a wrong record in a warehouse.

The value is often NOT in the message that mentions the job. A request may say
"as discussed" or point at an earlier thread, so read the thread rather than
stopping at the first hit."""

GATHER = Prompt(
    name="gather",
    version=1,
    model="gemini-3.8-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract=(
        "`job`, `still_needed`, `seen_before` as JSON; `asked_for` and `already_looked_at` "
        "untrusted."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["search", "read", "done"]},
            "query": {"type": "string", "nullable": True},
            "message_id": {"type": "string", "nullable": True},
            "values": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "string"},
                        "from_message": {"type": "string"},
                        "quoting": {"type": "string"},
                    },
                    "required": ["name", "value", "from_message"],
                },
            },
            "why": {"type": "string"},
        },
        "required": ["action", "why"],
        "propertyOrdering": ["action", "query", "message_id", "values", "why"],
    },
    edge_cases=(
        EdgeCase(
            'a request saying "as discussed"',
            "`read` the thread before `done`",
        ),
        EdgeCase(
            "a value read in a message",
            "reported with `from_message` and `quoting`",
        ),
        EdgeCase(
            "a value only guessed at",
            "left out, and `done`",
        ),
    ),
)
