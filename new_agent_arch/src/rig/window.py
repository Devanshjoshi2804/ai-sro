"""A4 — pack a window of evidence under a token budget.

The window is built from trimmed evidence rather than full request bodies, and
that is a measurement rather than a preference. Across 81 real gestures from the
acme tenant, bodies inline ran a median of 72 tokens and a MEAN of 8,388 --
three of the eighty-one held 71% of all request bytes and two individually
exceeded the entire window. "Inline until the budget is spent" does not degrade
gracefully; it lets one click starve the day, and which click wins is an
accident of iteration order. Trimmed, the same evidence is a median of 88 and a
mean of 204, and a whole day fits.
"""

import json
from dataclasses import dataclass, field, replace
from typing import Any

from rig.records import Gesture, Intent
from rig.trim import is_secret, trim

K_WINDOW_TOKENS = 150_000
K_MIN_GESTURES = 25
K_MAX_GESTURE_TOKENS = 2_000
K_ENDS = 12
K_POOL_BONUS = 0.5
K_MAX_TEXT_CHARS = 400
K_MAX_ITEMS = 40


def tokens(text: str) -> int:
    """Four characters to a token. Close enough to budget with, and it never
    lies in the expensive direction the way a model-specific tokeniser would
    when the model changes."""
    return len(text) // 4


@dataclass
class Packed:
    gesture_id: str
    at: float
    evidence: dict[str, Any]
    strength: float
    tokens: int


@dataclass
class Window:
    items: list[Packed] = field(default_factory=list)
    spent: int = 0
    left_out: list[str] = field(default_factory=list)


def _clip(value: Any) -> Any:
    """Bound every string and every list anywhere in the evidence.

    The cap has to hold against the whole body rather than against the one part
    of it that happened to be large the day it was written. A cap that shrank
    only request bodies was passed by four routes -- a huge typed value, a URL
    with nothing to split on, two thousand calls on one gesture, and model
    output returned at a million characters -- by 15x to 1000x. Nothing
    upstream bounds the length of what a model returns (see
    intents._string_field), so this is where it is bounded.
    """
    if isinstance(value, str):
        return value[:K_MAX_TEXT_CHARS]
    if isinstance(value, list):
        return [_clip(item) for item in value[:K_MAX_ITEMS]]
    if isinstance(value, dict):
        return {key: _clip(item) for key, item in value.items()}
    return value


def as_evidence(gesture: Gesture, intent: Intent | None) -> dict[str, Any]:
    """One gesture as the umbrella pass sees it: what it was, and what a model
    already made of it. Capped -- and the cap is a guarantee rather than an
    attempt: nothing over K_MAX_GESTURE_TOKENS leaves here by any route.
    """
    # values_seen is model output, and the model is shown what the operator
    # typed. trim() nulls a credential; nothing nulled it on the way back, so a
    # password the model echoed into a field it had named went into the window
    # intact. Same rule, same gesture, applied on both paths.
    hide = is_secret(gesture)
    body: dict[str, Any] = _clip(
        {
            "id": gesture.id,
            "at": gesture.at,
            "system": gesture.system,
            "gesture": trim(gesture),
            "intent": None
            if intent is None
            else {
                "act": intent.act,
                "object": intent.object,
                "page": intent.page,
                "why": intent.why,
                "confidence": intent.confidence,
                "values_seen": [
                    {"field": value.field, "value": None if hide else value.value}
                    for value in intent.values_seen
                ],
            },
        }
    )
    if tokens(json.dumps(body)) <= K_MAX_GESTURE_TOKENS:
        return body

    # Over the cap: keep what names the gesture, drop what merely bulks it out.
    # The full evidence stays in the store, reachable by this id.
    body["truncated"] = True
    body["gesture"]["calls"] = [
        {"method": call["method"], "path": call["path"], "status": call["status"]}
        for call in body["gesture"]["calls"]
    ]
    if tokens(json.dumps(body)) <= K_MAX_GESTURE_TOKENS:
        return body

    # Still over, which means something pathological is in here. Keep what
    # identifies the gesture and nothing else: one unreadable item in a window
    # is worth more than a window that could not be built.
    return {
        "id": body["id"],
        "at": body["at"],
        "system": body["system"],
        "gesture": {"kind": body["gesture"]["kind"], "url": body["gesture"]["url"]},
        "intent": None if intent is None else {"act": body["intent"]["act"]},
        "truncated": True,
    }


def strength(gesture: Gesture, intent: Intent | None, linked: set[str]) -> float:
    """What earns a place at the ends of the window. Never stated in the prompt:
    telling a model which evidence is most relevant was measured to reduce
    accuracy in all five languages tested."""
    score = 1.0
    if any(request.method != "GET" for request in gesture.requests):
        score += 1.0
    if intent is not None and intent.confidence == "high":
        score += 0.5
    if gesture.gesture.kind in ("type", "select", "upload"):
        score += 0.5
    if gesture.id in linked:
        score += 1.0
    return score


def arrange(items: list[Packed]) -> list[Packed]:
    """Strongest at both ends, weakest in the middle.

    The middle stays in temporal order. Order-invariant representations were
    measured to degrade cross-application reconstruction specifically, and a
    workflow is a sequence -- scrambling it to chase a position effect would
    trade the thing we are reading for points on somebody else's benchmark.
    """
    by_strength = sorted(items, key=lambda item: (-item.strength, item.at))
    head: list[Packed] = []
    tail: list[Packed] = []
    middle: list[Packed] = []
    for index, item in enumerate(by_strength):
        if index < K_ENDS:
            (head if index % 2 == 0 else tail).append(item)
        else:
            middle.append(item)
    return head + sorted(middle, key=lambda item: item.at) + list(reversed(tail))


def pack(
    gestures: list[Gesture],
    intents: dict[str, Intent],
    pool: list[Packed],
    known: list[dict[str, Any]],
    kb: str,
    budget: int = K_WINDOW_TOKENS,
    linked: set[str] | None = None,
) -> Window:
    """Fill the window strongest-first, then put it back in time order."""
    linked = linked or set()
    candidates: list[Packed] = [
        replace(item, strength=item.strength + K_POOL_BONUS) for item in pool
    ]
    for gesture in gestures:
        intent = intents.get(gesture.id)
        evidence = as_evidence(gesture, intent)
        candidates.append(
            Packed(
                gesture_id=gesture.id,
                at=gesture.at,
                evidence=evidence,
                strength=strength(gesture, intent, linked),
                tokens=tokens(json.dumps(evidence)),
            )
        )

    room = budget - tokens(json.dumps(known)) - tokens(kb)
    chosen: list[Packed] = []
    left_out: list[str] = []
    spent = 0
    for item in sorted(candidates, key=lambda i: (-i.strength, i.at)):
        if spent + item.tokens > room and len(chosen) >= K_MIN_GESTURES:
            left_out.append(item.gesture_id)
            continue
        chosen.append(item)
        spent += item.tokens

    chosen.sort(key=lambda item: item.at)
    return Window(items=chosen, spent=spent, left_out=left_out)
