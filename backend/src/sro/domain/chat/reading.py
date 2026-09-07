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
    },
    "required": ["workflow_id", "values", "missing"],
    "propertyOrdering": ["workflow_id", "values", "missing"],
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
name the one whose demonstration is closest to what was said."""
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
