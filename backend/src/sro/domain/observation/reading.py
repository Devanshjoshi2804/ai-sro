"""A3 — the words one gesture is read in, and what a model's answer becomes.

Everything here is arithmetic over an answer that has already come back: the
instructions, the response schema, the confidence vocabulary, the one line an
intent contributes to the next gesture's context, and the parsing that turns a
model's JSON into an `Intent`. The call itself is
`sro.application.observation.read_gesture`, which is the only half that needs a
port.

Ported from `new_agent_arch/src/rig/intents.py`. The schema is advisory --
nothing between the model and this file enforces it -- so every field is read
back defensively here rather than trusted, and a field that came back the wrong
type is treated as unusable rather than coerced into a plausible-looking one.
"""

from __future__ import annotations

from sro.domain.observation.gesture import Gesture, Intent, ValueSeen
from sro.domain.observation.redaction import is_secret_name
from sro.domain.observation.trim import is_secret
from sro.domain.shared.prices import Answer

TAIL = 8
"""How many previous readings a gesture is read against.

`continues` is decided from these lines, so this is the whole memory one
reading has of the doing it belongs to. Eight is what the measured day's
longest job fits inside; every reading pays for them in prompt tokens, once per
gesture, thousands of times a day."""

INSTRUCTIONS = """You are reading one thing a warehouse operator just did in a browser.

You are given the gesture, the control it touched, the network calls it caused,
and a few lines of what the same person did just before.

Say what they did, in the words an operator would use. Name the object they were
working on. List the values you can see them entering. Say whether this looks
like a continuation of the previous doing.

Do not guess at a value you cannot see. Do not describe the HTML."""

_CONFIDENCE = ["high", "medium", "low"]
"""The one declaration of the confidence vocabulary; the schema below and
`CONFIDENCE_VALUES` are both this list. Restated in two places they drift, and
a word the schema offers that the guard has never heard of is nulled on the way
in -- indistinguishable from a model that declined to give one."""

INTENT_SCHEMA: dict[str, object] = {
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
        "confidence": {"type": "string", "enum": _CONFIDENCE},
        "why": {"type": "string", "description": "one sentence"},
    },
    "required": ["act", "why"],
}

CONFIDENCE_VALUES = frozenset(_CONFIDENCE)


def one_line(intent: Intent) -> str:
    parts = [intent.act or "(unread)"]
    if intent.object:
        parts.append(f"on {intent.object}")
    return " ".join(parts).replace("\n", " ")


def _string_field(data: dict[str, object], key: str) -> str | None:
    """The schema is advisory, not enforced. A model can return `"act": [...]`
    and nothing here validates it before it reaches `Intent`. Treating a
    wrong-typed field as unusable is what stops that field poisoning `one_line`
    the next time this intent is pulled into somebody else's tail context.
    """
    value = data.get(key)
    return value if isinstance(value, str) else None


def intent_from(
    data: dict[str, object] | None, gesture: Gesture, answer: Answer, *, model: str
) -> Intent:
    """One reading, as it will be stored -- whatever came back in it.

    An answer that carried no data still becomes an intent: the model was
    asked, it answered, and it was billed, so the row exists and says why it is
    empty. `data` is passed beside `answer` rather than read off it because the
    caller has already decided what counts as usable JSON, and `model` beside
    both because `Answer` carries the bill but not the name it was run up
    against -- which is the one thing a reader of a $0.00 row needs.
    """
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
    intent.system = _string_field(data, "system")
    intent.page = _string_field(data, "page")
    # `or None`: the schema says "empty unless it continues the last doing", so
    # "" is what a model returns for most gestures. Stored verbatim it is
    # neither a link nor an absence, and `continues` is what the mining pass
    # walks to join gestures into one doing.
    intent.continues = _string_field(data, "continues") or None
    confidence = _string_field(data, "confidence")
    intent.confidence = confidence if confidence in CONFIDENCE_VALUES else None
    intent.why = _string_field(data, "why")
    intent.values_seen = _values_seen(data, hide=is_secret(gesture))
    return intent


def _values_seen(data: dict[str, object], *, hide: bool) -> list[ValueSeen]:
    """What the model reported the operator entering, with credentials blanked.

    The third place a guard covered the typed value and let values_seen
    through -- after `trim` and `typed_values`, and the only one of the three
    that reaches storage. `save_intent` writes this verbatim and the gestures
    route serves it back, so a password the model echoed into a field it had
    named was persisted and rendered. The field name is kept: that the operator
    typed a password is worth reading, what they typed is not. This is the
    single point every stored values_seen passes through.
    """
    seen_list = data.get("values_seen")
    found: list[ValueSeen] = []
    # Both containers are checked, not just the outer one: a mapping iterates
    # as its own keys and a string as its characters, so an outer guard alone
    # walks a `{"clientCode": "ACME-4471"}` straight into the per-entry code.
    for seen in seen_list if isinstance(seen_list, list) else []:
        if not isinstance(seen, dict):
            continue
        field = seen.get("field")
        # `field` unusable unless it's a non-empty str; a non-str `value` is
        # treated as unseen ("") rather than fabricated by str()-coercing it --
        # same rule as `_string_field` above.
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
