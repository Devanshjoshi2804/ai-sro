from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from sro.domain.observation.gesture import Gesture, Intent, ValueSeen
from sro.domain.observation.redaction import is_secret_name
from sro.domain.observation.trim import is_secret
from sro.domain.observation.values import K_MIN_VALUE_LEN
from sro.domain.shared.prices import Answer

TAIL = 8

INSTRUCTIONS = """You are reading one thing a warehouse operator just did in a browser.

You are given the gesture, the control it touched, the network calls it caused,
and a few lines of what the same person did just before.

First say why: point at the one piece of evidence (the control's label, its
component metadata, the request body, the picture) that tells you what
happened. Only then name the act, in the words an operator would use, and the
object they were working on. List the values you can see them entering. Say
whether this looks like a continuation of the previous doing.

If the evidence is thin -- an icon with no label, no field, nothing typed --
say so in why and mark confidence low, rather than guessing at a specific act.

Do not guess at a value you cannot see. Do not describe the HTML."""

_CONFIDENCE = ["high", "medium", "low"]

INTENT_SCHEMA: dict[str, object] = {
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
        "continues": {"type": "string", "description": "empty unless it continues the last doing"},
        "confidence": {"type": "string", "enum": _CONFIDENCE},
    },
    "propertyOrdering": [
        "why",
        "act",
        "object",
        "page",
        "values_seen",
        "continues",
        "confidence",
    ],
    "required": ["act", "why"],
}

CONFIDENCE_VALUES = frozenset(_CONFIDENCE)


def one_line(intent: Intent) -> str:
    parts = [intent.act or "(unread)"]
    if intent.object:
        parts.append(f"on {intent.object}")
    return " ".join(parts).replace("\n", " ")


def _string_field(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def intent_from(
    data: dict[str, object] | None, gesture: Gesture, answer: Answer, *, model: str
) -> Intent:
    intent = Intent(
        gesture_id=gesture.id,
        tenant=gesture.tenant,
        model=model,
        in_tokens=answer.in_tokens,
        out_tokens=answer.out_tokens,
        thought_tokens=answer.thought_tokens,
        cost_usd=answer.cost_usd,
        unpriced=answer.unpriced,
        error=answer.error,
    )
    if data is None:
        return intent

    intent.act = _string_field(data, "act")
    intent.object = _string_field(data, "object")
    intent.page = _string_field(data, "page")
    intent.continues = _string_field(data, "continues") or None
    confidence = _string_field(data, "confidence")
    intent.confidence = confidence if confidence in CONFIDENCE_VALUES else None
    intent.why = _string_field(data, "why")
    intent.values_seen = _values_seen(data, hide=is_secret(gesture))
    return intent


def _values_seen(data: dict[str, object], *, hide: bool) -> list[ValueSeen]:
    seen_list = data.get("values_seen")
    found: list[ValueSeen] = []
    for seen in seen_list if isinstance(seen_list, list) else []:
        if not isinstance(seen, dict):
            continue
        field = seen.get("field")
        if not isinstance(field, str) or not field:
            continue
        value = seen.get("value")
        found.append(
            ValueSeen(
                field=field,
                value=""
                if hide or is_secret_name(field)
                else (value if isinstance(value, str) else ""),
            )
        )
    return found


_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH"})


def is_write(gesture: Gesture) -> bool:
    return any(
        call.status is not None
        and 200 <= call.status < 300
        and call.method.upper() in _WRITE_METHODS
        for call in gesture.requests
    )


def field_of(gesture: Gesture) -> str | None:
    target = gesture.action.target
    if target is None:
        return None
    component = target.component
    if component is not None:
        for name in (component.field_label, component.name):
            if name and name.strip():
                return name.strip()
    return target.name.strip() if target.name and target.name.strip() else None


def _typed_before(recent: Sequence[Gesture]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for prior in recent:
        if prior.action.kind != "type" or prior.action.secret or is_secret(prior):
            continue
        value = (prior.action.value or "").strip()
        field = field_of(prior)
        if value and field and not is_secret_name(field):
            found.append((field, value))
    return found


def _carried_any(gesture: Gesture, typed: Sequence[tuple[str, str]]) -> bool:
    sent = "\n".join(
        call.request_body.text
        for call in gesture.requests
        if call.status is not None
        and 200 <= call.status < 300
        and call.method.upper() in _WRITE_METHODS
        and call.request_body is not None
        and call.request_body.text
    )
    if not sent:
        return False
    return any(len(value) >= K_MIN_VALUE_LEN and value in sent for _, value in typed)


def with_recent_values(intent: Intent, gesture: Gesture, recent: Sequence[Gesture]) -> Intent:
    if not is_write(gesture):
        return intent
    typed = _typed_before(recent)
    if not _carried_any(gesture, typed):
        return intent
    merged: dict[str, str] = dict(typed)
    for seen in intent.values_seen:
        merged[seen.field] = seen.value
    return replace(
        intent,
        values_seen=[ValueSeen(field=field, value=value) for field, value in merged.items()],
    )
