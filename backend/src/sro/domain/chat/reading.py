"""What the chat door reads with, and what the reading cost.

The words and the response schema are here rather than beside the use case for
one reason that has already cost this door a day: every schema this package
asks under is walked by
``tests/unit/domain/rig/test_planning.py::test_no_schema_in_the_package_uses_what_the_developer_api_refuses``,
and that walker only reaches ``sro.domain``. A schema declared in the
application layer is a schema nothing checks. The half that asks is
``sro.application.chat.understand``.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

UNDERSTAND_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "workflow_id": {"type": "string", "nullable": True},
        # A list of pairs, not a map: the Gemini Developer API refuses
        # `additionalProperties` with a 400 -- "only supported in Gemini
        # Enterprise Agent Platform mode" -- and a map of parameter name to
        # value is exactly that. Found the first time this door met the real
        # API, which it had shipped without ever doing.
        "values": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "value": {"type": "string"}},
                "required": ["name", "value"],
                "propertyOrdering": ["name", "value"],
            },
        },
        "missing": {"type": "array", "items": {"type": "string"}},
        # How sure, and what else it nearly was.
        #
        # The door always named a job. Asked "lets create warehouse equipment
        # type" by an operator whose tenant holds exactly that job, an earlier
        # version of this system answered "Create a customer type does that"
        # with no way for anything downstream to know it had guessed -- and a
        # guess that creates one wrong record is a nuisance, while the same
        # guess against a list of twenty is twenty wrong records in a
        # warehouse.
        #
        # `sure` is the model's own reading of whether the sentence names ONE
        # of these jobs plainly. `also` is what it nearly said instead, which
        # is what a person is asked to choose between.
        "sure": {"type": "boolean"},
        "also": {"type": "array", "items": {"type": "string"}},
        # Several things, one job. "Add these three equipment types" is one
        # job done three times, and until this existed the door could only
        # answer the first: the values of one thing, in `values`, and the
        # other two lost between a mail and a browser that had just proved it
        # could do them.
        #
        # A list of lists of pairs, for the same reason `values` is a list of
        # pairs one level up: the Developer API refuses `additionalProperties`,
        # so a map of parameter name to value cannot be asked for at any depth.
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "values": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["name", "value"],
                            "propertyOrdering": ["name", "value"],
                        },
                    }
                },
                "required": ["values"],
                "propertyOrdering": ["values"],
            },
        },
    },
    "required": ["workflow_id", "values", "missing", "sure"],
    "propertyOrdering": ["workflow_id", "sure", "also", "values", "missing", "items"],
}

INSTRUCTIONS = """An operator has said what they want done. You are given the jobs this system
can do, each with the parameters it takes and the values it has seen. Answer
which job they mean (its id, or null if none fits), the values they gave for
its parameters, and which parameters are still missing. Never invent a value.

A job is a kind of work, not the one time it was done. Its title and narrative
were read from a demonstration and carry that demonstration's values: "Create
Work Area NEWTESTS" is the job of creating a work area, done once with the name
NEWTESTS. An operator asking for the same work with other values -- a work area
called NEWTEST9 -- means that job. Match on what the job does. Answer null only
when no job here does that kind of work at all. When two jobs do the same work,
name the one whose demonstration is closest to what was said.

Say whether you are SURE. You are sure when the sentence plainly names one of
these jobs and no other job here does that kind of work. You are not sure when
two or more could be meant, when the sentence names a kind of work none of
them quite does, or when you are choosing on a detail rather than on what the
work is. Where you are not sure, still answer the closest job, and list the
others you considered in `also` -- a person will be asked which. Guessing
confidently is worse than saying you are unsure: what gets done with this
answer is work in a warehouse, and there may be twenty of it.

Some jobs carry `asked_by`: the mails this operator acted on before doing that
job, as their mailbox recorded them. That is what a REQUEST for the job looks
like, which is not the same thing as what the job is called -- a request rarely
uses the job's words, and "please set up a new client category" is a request
for `Create a Customer Type` however little the two sentences share. Read them
as examples of the kind of ask, and prefer a job whose examples are asking for
the same work as what was said.

Never take a value out of one. They are somebody's old requests, and the codes
and names in them belong to records that already exist -- answering with one
would do the job again for the wrong thing. A job with no `asked_by` is not a
job nobody asks for: it is a job whose demonstration began on a page, so match
it on its title and narrative as you would have anyway. And examples raise your
confidence about which job, never about whether you were told enough: a value
the operator did not give is still missing.

An operator may name several things for one job: three equipment types in one
mail, four work areas in one sentence. That is one job done once per thing.
Answer one entry in `items` for each thing, carrying that thing's own values,
and put in `values` only what is true of all of them. Where they named one
thing, leave `items` empty and put its values in `values`. Never split one
thing into several, and never merge two things into one."""
"""The second paragraph is the product.

A mined job is named after the one demonstration it was read from, values and
all, so a door told only "answer which job they mean" compares an operator's
sentence against a title that describes a single past doing and answers null.
Without that paragraph the door named no job for five real operator sentences;
with it, five of five."""


def new_chat_id() -> str:
    """The shape every other id in the backend has. The rig minted this inside
    its ``/v1/chat`` route; here the reading is a record before it is a row."""
    return "cht_" + secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class ChatReading:
    """One sentence the chat door read, and what the reading cost.

    The sentence is not kept: it is an operator's words about a warehouse,
    and the bill is what this record is for.
    """

    id: str
    tenant: str
    at: str
    workflow_id: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    error: str | None = None
