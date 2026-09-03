"""A6 — a value that crossed a system boundary.

Cross-organisational process mining reconstructs one process from logs with no
shared case identifier -- our exact problem -- at over 98.4% precision and 94.2%
recall, by linking on shared data items across the separate logs. No model
anywhere in it. A supplier name typed into one system and appearing in a call to
another is that signal, and it is arithmetic over evidence already stored.

A hint, not a gate: this is handed to the umbrella pass as a labelled section
and the model decides what it means. Nothing is joined on this score alone.
"""

import json
from collections import defaultdict

from rig.records import Gesture, Intent
from rig.store import Store
from rig.trim import is_secret

K_MIN_VALUE_LEN = 4
K_UBIQUITY = 0.25

_NEVER = frozenset({"true", "false", "null", "none", "0", "1", ""})


def typed_values(gesture: Gesture, intent: Intent | None) -> set[str]:
    """What this gesture put into the world: what was typed, and what a reading
    saw entered. A credential is never here -- is_secret() is the one place
    that rule lives, and this asks it rather than restating it.

    The whole gesture is refused rather than only its typed value. values_seen
    comes back from the model, which is shown the field it was typed into, so
    guarding the typed value alone let a password return by the other route and
    become a cross-system link -- the same leak found in as_evidence, in a
    second place. wire.Gesture nulls the value at parse time and so hides this
    from a test built on the fixture; the model's echo is not nulled by
    anything."""
    if is_secret(gesture):
        return set()
    found: set[str] = set()
    if gesture.gesture.value:
        found.add(gesture.gesture.value)
    if intent is not None:
        found.update(seen.value for seen in intent.values_seen if seen.value)
    return found


def trivial(value: str, frequency: float) -> bool:
    """Too short, too common, or a literal that means nothing on its own."""
    text = value.strip()
    return len(text) < K_MIN_VALUE_LEN or text.lower() in _NEVER or frequency > K_UBIQUITY


def frequencies_over(store: Store, tenant: str) -> dict[str, float]:
    """How often each seen value appears across the tenant's readings.

    Arithmetic, not a pattern, and the only thing here that needs history: a
    value carried by a quarter of everything is furniture rather than a link.
    """
    rows = store.query("SELECT values_seen FROM intents WHERE tenant = ?", (tenant,))
    if not rows:
        return {}

    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for seen in json.loads(row["values_seen"] or "[]"):
            value = str(seen.get("value", "")).strip()
            if value:
                counts[value] += 1
    return {value: count / len(rows) for value, count in counts.items()}


def shared_values(
    gestures: list[Gesture],
    intents: dict[str, Intent],
    frequencies: dict[str, float],
) -> dict[str, list[str]]:
    """Values appearing in more than one system, and the gestures carrying them."""
    seen: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for gesture in gestures:
        for value in typed_values(gesture, intents.get(gesture.id)):
            if trivial(value, frequencies.get(value, 0.0)):
                continue
            seen[value].append((gesture.id, gesture.system or ""))

    crossings: dict[str, list[str]] = {}
    for value, occurrences in seen.items():
        if len({system for _, system in occurrences}) >= 2:
            crossings[value] = [gesture_id for gesture_id, _ in occurrences]
    return crossings
