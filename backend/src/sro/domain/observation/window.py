import json
from dataclasses import dataclass, field, replace

from sro.domain.observation.gesture import Gesture, Intent
from sro.domain.observation.trim import is_secret, trim

K_WINDOW_TOKENS = 100_000
K_LEAD_UP_S = 180.0

K_MIN_GESTURES = 25
K_MAX_GESTURE_TOKENS = 2_000
K_ENDS = 12
K_POOL_WAIT = 0.5

K_POOL_BONUS = 0.5
K_MAX_TEXT_CHARS = 400
K_MAX_ITEMS = 40


def tokens(text: str) -> int:
    return len(text) // 4


def evidence_tokens(evidence: dict[str, object]) -> int:
    return tokens(json.dumps([evidence], indent=1, ensure_ascii=False))


@dataclass
class Packed:
    gesture_id: str
    at: float
    evidence: dict[str, object]
    strength: float
    tokens: int

    stream_id: str = ""


@dataclass
class Window:
    items: list[Packed] = field(default_factory=list)
    spent: int = 0
    left_out: list[str] = field(default_factory=list)


def _clip(value: object) -> object:
    if isinstance(value, str):
        return value[:K_MAX_TEXT_CHARS]
    if isinstance(value, list):
        return [_clip(item) for item in value]
    if isinstance(value, dict):
        return {key: _clip(item) for key, item in value.items()}
    return value


def _map(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _seq(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def as_evidence(gesture: Gesture, intent: Intent | None) -> dict[str, object]:
    hide = is_secret(gesture)
    body: dict[str, object] = _map(
        _clip(
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
    )
    if tokens(json.dumps(body, ensure_ascii=False)) <= K_MAX_GESTURE_TOKENS:
        return body

    body["truncated"] = True
    trimmed = _map(body["gesture"])
    trimmed["calls"] = [
        {"method": call["method"], "path": call["path"], "status": call["status"]}
        for call in (_map(item) for item in _seq(trimmed["calls"]))
    ]
    if tokens(json.dumps(body, ensure_ascii=False)) <= K_MAX_GESTURE_TOKENS:
        return body

    trimmed["calls"] = _seq(trimmed["calls"])[:K_MAX_ITEMS]
    trimmed["page"] = _seq(trimmed["page"])[:K_MAX_ITEMS]
    if body["intent"] is not None:
        reading = _map(body["intent"])
        reading["values_seen"] = _seq(reading["values_seen"])[:K_MAX_ITEMS]
    if tokens(json.dumps(body, ensure_ascii=False)) <= K_MAX_GESTURE_TOKENS:
        return body

    return {
        "id": body["id"],
        "at": body["at"],
        "system": body["system"],
        "gesture": {"kind": trimmed["kind"], "url": trimmed["url"]},
        "intent": None if intent is None else {"act": _map(body["intent"])["act"]},
        "truncated": True,
    }


def _mutates(gesture: Gesture) -> bool:
    return any(request.method != "GET" for request in gesture.requests)


def _wrote(item: Packed) -> bool:
    gesture = item.evidence.get("gesture")
    if not isinstance(gesture, dict):
        return False
    calls = gesture.get("calls")
    if not isinstance(calls, list):
        return False
    return any(
        isinstance(call, dict) and str(call.get("method", "")).upper() not in ("GET", "")
        for call in calls
    )


def strength(gesture: Gesture, intent: Intent | None, linked: set[str]) -> float:
    score = 1.0
    if _mutates(gesture):
        score += 1.0
    if intent is not None and intent.confidence == "high":
        score += 0.5
    if gesture.action.kind in ("type", "select", "upload"):
        score += 0.5
    if gesture.id in linked:
        score += 1.0
    return score


def arrange(items: list[Packed]) -> list[Packed]:
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
    known: list[dict[str, object]],
    kb: str,
    budget: int = K_WINDOW_TOKENS,
    linked: set[str] | None = None,
    read: frozenset[str] = frozenset(),
) -> Window:
    linked = linked or set()
    candidates: list[Packed] = [
        replace(item, strength=item.strength + K_POOL_BONUS) for item in pool
    ]
    writing = {gesture.id for gesture in gestures if _mutates(gesture)}
    writing |= {item.gesture_id for item in pool if _wrote(item)}
    for gesture in gestures:
        intent = intents.get(gesture.id)
        evidence = as_evidence(gesture, intent)
        candidates.append(
            Packed(
                gesture_id=gesture.id,
                at=gesture.at,
                evidence=evidence,
                strength=strength(gesture, intent, linked),
                tokens=evidence_tokens(evidence),
                stream_id=gesture.stream_id,
            )
        )

    from sro.domain.skill.umbrella import PROMPT_OVERHEAD_TOKENS

    room = (
        budget
        - PROMPT_OVERHEAD_TOKENS
        - tokens(json.dumps(known, indent=1, ensure_ascii=False))
        - tokens(kb)
    )
    by_stream: dict[str, list[Packed]] = {}
    for item in candidates:
        by_stream.setdefault(item.stream_id, []).append(item)
    for run in by_stream.values():
        run.sort(key=lambda item: item.at)

    chosen: list[Packed] = []
    taken: set[str] = set()
    spent = 0
    for item in sorted(candidates, key=lambda i: (i.gesture_id in read, -i.strength, -i.at)):
        if item.gesture_id in taken:
            continue
        group = [item]
        if item.gesture_id in writing:
            group = [
                one
                for one in by_stream.get(item.stream_id, ())
                if one.gesture_id not in taken
                and one.gesture_id != item.gesture_id
                and item.at - K_LEAD_UP_S <= one.at < item.at
            ] + group
        cost = sum(one.tokens for one in group)
        if spent + cost > room:
            if len(chosen) >= K_MIN_GESTURES:
                continue
            group, cost = [item], item.tokens
        chosen.extend(group)
        taken |= {one.gesture_id for one in group}
        spent += cost
    left_out = [one.gesture_id for one in candidates if one.gesture_id not in taken]

    chosen.sort(key=lambda item: item.at)
    return Window(items=chosen, spent=spent, left_out=left_out)
