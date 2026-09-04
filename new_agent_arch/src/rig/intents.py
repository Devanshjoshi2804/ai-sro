"""A3 — one model call per gesture, and never a batch of them.

Batching stream items into a shared call degrades each item through semantic
interference and diluted attention; measured accuracy decays roughly
A(T) = A_max * e^(-b(T-1)) in batch size while throughput only saturates. The
saving is small and the cost is per-item quality. So: one gesture, one call.
"""

import json
from typing import Any

from rig.models import Asker
from rig.records import Gesture, Intent, ValueSeen
from rig.trim import is_secret, thin, trim

TAIL = 8

INSTRUCTIONS = """You are reading one thing a warehouse operator just did in a browser.

You are given the gesture, the control it touched, the network calls it caused,
and a few lines of what the same person did just before.

Say what they did, in the words an operator would use. Name the object they were
working on. List the values you can see them entering. Say whether this looks
like a continuation of the previous doing.

Do not guess at a value you cannot see. Do not describe the HTML."""

INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "act": {"type": "string", "description": "what the person did, in their words"},
        "object": {"type": "string", "description": "the thing they were working on"},
        "system": {"type": "string"},
        "page": {"type": "string"},
        "values_seen": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"field": {"type": "string"}, "value": {"type": "string"}},
                "required": ["field", "value"],
            },
        },
        "continues": {"type": "string", "description": "empty unless it continues the last doing"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "why": {"type": "string", "description": "one sentence"},
    },
    "required": ["act", "why"],
}

# Derived, not restated: the schema's enum is the one declaration.
CONFIDENCE_VALUES = frozenset(INTENT_SCHEMA["properties"]["confidence"]["enum"])


def one_line(intent: Intent) -> str:
    parts = [intent.act or "(unread)"]
    if intent.object:
        parts.append(f"on {intent.object}")
    return " ".join(parts).replace("\n", " ")


def _string_field(data: dict[str, Any], key: str) -> str | None:
    """The schema is advisory, not enforced. A model can return `"act": [...]`
    and nothing here validates it before it reaches `Intent`. Treating a
    wrong-typed field as unusable is what stops that field poisoning `one_line`
    the next time this intent is pulled into somebody else's tail context.
    """
    value = data.get(key)
    return value if isinstance(value, str) else None


async def read_gesture(
    gesture: Gesture,
    *,
    tail: list[Intent],
    asker: Asker,
    model: str,
    image: bytes | None = None,
) -> Intent:
    recent = [one_line(intent) for intent in tail[-TAIL:]]
    evidence = json.dumps(
        {"gesture": trim(gesture), "just_before": recent},
        indent=2,
        sort_keys=True,
    )

    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=evidence,
        schema=INTENT_SCHEMA,
        image=image if thin(gesture.gesture.target) else None,
    )

    intent = Intent(
        gesture_id=gesture.id,
        tenant=gesture.tenant,
        model=model,
        in_tokens=answer.in_tokens,
        out_tokens=answer.out_tokens,
        cost_usd=answer.cost_usd,
        unpriced=answer.unpriced,
        error=answer.error,
    )
    if answer.data is None:
        return intent

    data = answer.data
    intent.act = _string_field(data, "act")
    intent.object = _string_field(data, "object")
    intent.system = _string_field(data, "system")
    intent.page = _string_field(data, "page")
    intent.continues = _string_field(data, "continues") or None
    confidence = _string_field(data, "confidence")
    intent.confidence = confidence if confidence in CONFIDENCE_VALUES else None
    intent.why = _string_field(data, "why")

    seen_list = data.get("values_seen")
    # The third place a guard covered the typed value and let values_seen
    # through -- after as_evidence and typed_values, and the only one of the
    # three that reaches storage. save_intent writes this verbatim and
    # GET /v1/gestures serves it back, so a password the model echoed into a
    # field it had named was persisted and rendered. The field name is kept:
    # that the operator typed a password is worth reading, what they typed is
    # not. This is the single point every stored values_seen passes through.
    hide = is_secret(gesture)
    intent.values_seen = [
        # `field` unusable unless it's a str; a non-str `value` is treated as
        # unseen ("") rather than fabricated by str()-coercing it -- same rule
        # as `_string_field` above.
        ValueSeen(
            field=seen["field"],
            value="" if hide else (seen["value"] if isinstance(seen.get("value"), str) else ""),
        )
        for seen in (seen_list if isinstance(seen_list, list) else [])
        if isinstance(seen, dict) and isinstance(seen.get("field"), str) and seen["field"]
    ]
    return intent
