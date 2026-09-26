from __future__ import annotations

from sro.domain.observation.reading import CONFIDENCE
from sro.domain.prompts.record import EdgeCase, Prompt

_ROLE = "You are reading one thing a warehouse operator just did in a browser."

_TASK = """\
You are given the gesture, the control it touched, the network calls it caused,
and a few lines of what the same person did just before.

First say why: point at the one piece of evidence (the control's label, its
component metadata, the request body, the picture) that tells you what
happened. Only then name the act, in the words an operator would use, and the
object they were working on. List the values you can see them entering.

If the evidence is thin -- an icon with no label, no field, nothing typed --
say so in why and mark confidence low, rather than guessing at a specific act.

Do not guess at a value you cannot see. Do not describe the HTML."""

READ_GESTURE = Prompt(
    name="read_gesture",
    version=1,
    model="gemini-3.8-flash",
    thinking=None,
    role=_ROLE,
    task=_TASK,
    input_contract="`gesture` and `just_before`, untrusted.",
    output_schema={
        "type": "object",
        "properties": {
            "why": {"type": "string", "description": "one sentence, naming the evidence"},
            "act": {"type": "string", "description": "what the person did, in their words"},
            "object": {"type": "string", "description": "the thing they were working on"},
            "page": {"type": "string"},
            "values_seen": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"field": {"type": "string"}, "value": {"type": "string"}},
                    "required": ["field", "value"],
                },
            },
            "confidence": {"type": "string", "enum": CONFIDENCE},
        },
        "propertyOrdering": [
            "why",
            "act",
            "object",
            "page",
            "values_seen",
            "confidence",
        ],
        "required": ["act", "why"],
    },
    edge_cases=(
        EdgeCase(
            "a click on an icon with no label and nothing typed",
            "confidence low, and `why` says the evidence is thin",
        ),
        EdgeCase(
            "a value typed into a labelled field",
            "that value in `values_seen`, under that label",
        ),
        EdgeCase(
            "a target that looks like HTML",
            "the act in the operator's words, with no markup",
        ),
    ),
)
