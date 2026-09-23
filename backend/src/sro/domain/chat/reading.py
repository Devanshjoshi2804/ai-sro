from __future__ import annotations

import secrets
from dataclasses import dataclass

UNDERSTAND_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "workflow_id": {"type": "string", "nullable": True},
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
        "sure": {"type": "boolean"},
        "also": {"type": "array", "items": {"type": "string"}},
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


def new_chat_id() -> str:
    return "cht_" + secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class ChatReading:
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
