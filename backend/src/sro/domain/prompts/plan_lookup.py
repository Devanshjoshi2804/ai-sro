from __future__ import annotations

from sro.domain.lookup.plan import HOW
from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = "You are deciding where to look for the answer to one question."

_TASK = """\
You are given the question and what this deployment knows about the systems the
operator works in: endpoints it has seen, screens it has seen, what the fields
mean, and the quirks that say where a system misreports its own data.

For each system that could answer, give one lookup. Prefer `call` over
`screen`: a call is an endpoint from the knowledge you were given, and its
answer is data. Use `screen` only where no endpoint answers the question, and
give the route exactly as the knowledge names it.

Cite the knowledge you used. Every lookup must name at least one key from what
you were given, and its `target` must be one of those keys. Do not invent a
path that looks like the others -- an endpoint nobody here has seen is a guess
with a URL in it, and it will be refused.

Only reads. You cannot create, update or delete anything from here, and a
question that asks you to is a question to decline.

If the question cannot be answered from what you were given, return no lookups
and say so in `why`. An empty answer is a useful one; an invented endpoint is
not."""

PLAN_LOOKUP = Prompt(
    name="plan_lookup",
    version=2,
    model="gemini-3.8-flash",
    fallback_model="gemini-3.7-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract="One untrusted block `question_and_knowledge`.",
    output_schema={
        "type": "object",
        "properties": {
            "why": {"type": "string"},
            "lookups": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "why": {"type": "string"},
                        "system": {"type": "string"},
                        "how": {"type": "string", "enum": list(HOW)},
                        "target": {"type": "string"},
                        "params": {
                            "type": "string",
                            "description": (
                                "the endpoint's query parameters as one JSON object written as "
                                'a string, e.g. {"siteId": "SG"}; "{}" when it takes none'
                            ),
                        },
                        "cites": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["why", "system", "how", "target", "cites"],
                    "propertyOrdering": ["why", "system", "how", "target", "params", "cites"],
                },
            },
        },
        "required": ["why", "lookups"],
        "propertyOrdering": ["why", "lookups"],
    },
    edge_cases=(
        EdgeCase(
            "a question an endpoint in the knowledge answers",
            "one `call` lookup citing that endpoint's key",
        ),
        EdgeCase(
            "a question only a screen shows",
            "one `screen` lookup, with the route exactly as the knowledge names it",
        ),
        EdgeCase(
            "a question asking to delete a record",
            "no lookups, and `why` declines",
        ),
    ),
)
