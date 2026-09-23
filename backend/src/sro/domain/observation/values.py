from collections import defaultdict

from sro.domain.observation.gesture import Gesture, Intent, passed_through
from sro.domain.observation.trim import is_secret
from sro.domain.shared.hosts import origin_of

K_MIN_VALUE_LEN = 4
K_UBIQUITY = 0.25

_NEVER = frozenset({"true", "false", "null", "none", "0", "1", ""})

K_MIN_LONE_WORD = 6


def typed_values(gesture: Gesture, intent: Intent | None) -> set[str]:
    if is_secret(gesture):
        return set()
    found: set[str] = set()
    typed = str(gesture.action.value).strip() if gesture.action.value else ""
    if typed:
        found.add(typed)
    if intent is not None:
        found.update(text for seen in intent.values_seen if (text := str(seen.value).strip()))
    return found


def trivial(value: str, frequency: float) -> bool:
    text = str(value).strip()
    if len(text) < K_MIN_VALUE_LEN or text.lower() in _NEVER or frequency > K_UBIQUITY:
        return True
    lone = not any(character in text for character in " -_/.:@")
    return lone and len(text) < K_MIN_LONE_WORD


def frequencies_over(gestures: list[Gesture], intents: dict[str, Intent]) -> dict[str, float]:
    if not gestures:
        return {}

    counts: dict[str, int] = defaultdict(int)
    for gesture in gestures:
        for value in typed_values(gesture, intents.get(gesture.id)):
            counts[value] += 1
    return {value: count / len(gestures) for value, count in counts.items()}


def shared_values(
    gestures: list[Gesture],
    intents: dict[str, Intent],
    frequencies: dict[str, float],
) -> dict[str, list[str]]:
    seen: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for gesture in gestures:
        if not gesture.system:
            continue
        for value in typed_values(gesture, intents.get(gesture.id)):
            if trivial(value, frequencies.get(value, 0.0)):
                continue
            seen[value].append((gesture.id, gesture.system))

    crossings: dict[str, list[str]] = {}
    for value, occurrences in seen.items():
        if len({system for _, system in occurrences}) >= 2:
            crossings[value] = [gesture_id for gesture_id, _ in occurrences]
    return crossings


K_RETURNED_TO = 2


def worked_in_both(
    gestures: list[Gesture],
    *,
    gap: float,
    ours: frozenset[str] = frozenset(),
) -> set[str]:
    linked: set[str] = set()
    for stream in {gesture.stream_id for gesture in gestures}:
        timed = sorted(
            (
                gesture
                for gesture in gestures
                if gesture.stream_id == stream and gesture.at is not None and gesture.system
            ),
            key=lambda gesture: gesture.at or 0.0,
        )
        for sitting in _sittings(timed, gap):
            worked = _used_for_work(sitting, ours)
            if len(worked) < 2:
                continue
            linked |= {gesture.id for gesture in sitting if gesture.system in worked}
    return linked


def _sittings(gestures: list[Gesture], gap: float) -> list[list[Gesture]]:
    if not gestures:
        return []
    sittings: list[list[Gesture]] = []
    run = [gestures[0]]
    for gesture in gestures[1:]:
        if (gesture.at or 0.0) - (run[-1].at or 0.0) <= gap:
            run.append(gesture)
        else:
            sittings.append(run)
            run = [gesture]
    sittings.append(run)
    return sittings


def _used_for_work(sitting: list[Gesture], ours: frozenset[str]) -> set[str]:
    stretches: dict[str, int] = {}
    last: str | None = None
    for gesture in sitting:
        system = gesture.system or ""
        if system != last:
            stretches[system] = stretches.get(system, 0) + 1
            last = system
    doorways = {
        system
        for system in stretches
        if system and all(passed_through(g) for g in sitting if (g.system or "") == system)
    }
    return {
        system
        for system, runs in stretches.items()
        if system
        and runs >= K_RETURNED_TO
        and system not in doorways
        and origin_of(system) not in ours
    }
