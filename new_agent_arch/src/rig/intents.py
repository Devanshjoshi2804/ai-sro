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
from rig.trim import thin, trim

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


def one_line(intent: Intent) -> str:
    parts = [intent.act or "(unread)"]
    if intent.object:
        parts.append(f"on {intent.object}")
    return " ".join(parts).replace("\n", " ")


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
    intent.act = data.get("act")
    intent.object = data.get("object")
    intent.system = data.get("system")
    intent.page = data.get("page")
    intent.continues = data.get("continues") or None
    intent.confidence = data.get("confidence")
    intent.why = data.get("why")
    intent.values_seen = [
        ValueSeen(field=str(seen.get("field", "")), value=str(seen.get("value", "")))
        for seen in data.get("values_seen") or []
        if seen.get("field")
    ]
    return intent
