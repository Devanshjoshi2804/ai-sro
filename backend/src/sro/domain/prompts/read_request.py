from __future__ import annotations

from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = (
    "You read a warehouse request -- a mail thread or a sentence -- and say which job it asks for."
)

_TASK = """\
You are given a few candidate jobs this system can do and the request. For each
job you see its fields: their names, the labels the screen shows for them, the
operator's own words for them (aliases), the values seen in them before, and
mails that asked for the job before (`asked_by`).

Answer the job's id, or null if no candidate does that kind of work. Match on
what the job does, not on one demonstration's values: "a work area called
NEWTEST9" asks for "Create Work Area NEWTESTS". A request rarely uses the job's
words; the `asked_by` mails show what a request for it looks like. Never take a
value out of an `asked_by` mail: those are old requests for records that exist.

For each value the request gives, answer `field` (the field's name, one of its
labels, or one of its aliases -- or the request's own word for it when no field
fits), `value` exactly as written, and `quote`: the few words of the request the
value appears in, copied exactly. A value you cannot quote is a value you must
not give. A value stated against a name -- "customer type :- RRF", "code: GT7"
-- belongs to the field that name is, and to no other. The operator's own
sign-in username or password is never a job's value; a job's own Username field
is filled like any other.

Say whether you are SURE: the request plainly names one of these jobs and no
other does that kind of work. When two could be meant, answer the closest and
list the others in `also`. Guessing confidently is worse than saying you are
unsure: what follows is work in a live warehouse.

When a question is standing, the request is the answer to it, never a new
request: give the value it answers under the field the question asks for.

Several things for one job -- three equipment types in one mail -- are one
entry in `items` per thing, each with its own values; put in `values` only what
is true of all of them."""

_VALUE = {
    "type": "object",
    "properties": {
        "field": {"type": "string"},
        "value": {"type": "string"},
        "quote": {"type": "string"},
    },
    "required": ["field", "value", "quote"],
    "propertyOrdering": ["field", "value", "quote"],
}

READ_REQUEST = Prompt(
    name="read_request",
    version=2,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract=(
        "`question` as JSON when one is standing; the request as the untrusted block `thread`; "
        "the candidate jobs as the untrusted block `candidates`."
    ),
    output_schema={
        "type": "object",
        "properties": {
            "job": {"type": "string", "nullable": True},
            "sure": {"type": "boolean"},
            "also": {"type": "array", "items": {"type": "string"}},
            "values": {"type": "array", "items": _VALUE},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"values": {"type": "array", "items": _VALUE}},
                    "required": ["values"],
                },
            },
        },
        "required": ["job", "sure", "values"],
        "propertyOrdering": ["job", "sure", "also", "values", "items"],
    },
    rules=(
        "Every value carries a quote copied exactly from the request.",
        "Only candidate ids are jobs.",
    ),
    edge_cases=(
        EdgeCase(
            '"a work area called NEWTEST9" and job "Create Work Area NEWTESTS"',
            "that job, value NEWTEST9 under the work area's field, quote \"work area called "
            'NEWTEST9"',
        ),
        EdgeCase(
            '"please set up a new client category" and an `asked_by` mail like it on '
            '"Create a Customer Type"',
            "that job, sure",
        ),
        EdgeCase(
            '"customer type :- RRF and description :- first run" beside "Create a Customer '
            'Type" and "Reply to Email"',
            "Create a Customer Type, sure, RRF under Customer Type and first run under its "
            "description",
        ),
        EdgeCase('"three equipment types: FORK1, FORK2, REACH1"', "three `items`, one value each"),
        EdgeCase(
            'the standing question "What should Customer Type be?" and the reply "use GT7"',
            'value GT7 under Customer Type, quote "use GT7"',
        ),
    ),
)
