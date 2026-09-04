"""A6 — a value that crossed a system boundary.

Cross-organisational process mining reconstructs one process from logs with no
shared case identifier -- our exact problem -- at over 98.4% precision and 94.2%
recall, by linking on shared data items across the separate logs. No model
anywhere in it. A supplier name typed into one system and appearing in a call to
another is that signal, and it is arithmetic over evidence already stored.

A hint, not a gate: this is handed to the umbrella pass as a labelled section
and the model decides what it means. Nothing is joined on this score alone.

This is arithmetic over what was typed and what a reading reported, and it
never reads gesture.requests. A value that appears only inside another
system's request body is therefore found only when the model echoed it into
values_seen -- trim() does put body_keys in front of the model, so the path
exists, but it runs through the model rather than around it.
"""

from collections import defaultdict

from rig.records import Gesture, Intent
from rig.trim import is_secret

K_MIN_VALUE_LEN = 4
K_UBIQUITY = 0.25

_NEVER = frozenset({"true", "false", "null", "none", "0", "1", ""})

K_MIN_LONE_WORD = 6
"""A value that is one bare word has to be longer than one that is not.

`test` is exactly K_MIN_VALUE_LEN and, on an all-tabs day, appeared in five
hosts at a ubiquity of 0.025 -- under the furniture threshold, over the length
floor, and so published as a cross-system link. A junk crossing is worse than
noise: `strength` uses crossings to pull evidence INTO the window, so it
displaces real signal.

Blocklisting the word is what this looked like it needed, and the corpus says
otherwise: `Test Drive LLC` is a real carrier in this tenant's capture and a
genuine crossing, and it contains `Test` as a whole word. The same trap as
`pin` in `shippingPhone`.

What actually separates them is shape. A lone short word collides by accident
across five applications; two words, or one long one, do not. Measured over
every distinct value in the real capture: this rejects `test` and keeps
`AITEST9`, `Enveyo`, `Test Drive LLC`, `005-BEST METHOD`, `ConnectShip
(TanData)` and every other real identifier."""


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
    # Stripped here, which is the only place it happens: this is a set, so a
    # gesture whose typed value is "Supplier-X" and whose reading reported
    # " Supplier-X" collapses to one value rather than appending the same
    # gesture id twice under one key -- two pieces of evidence, downstream,
    # where there is one. Stripping in the caller instead deduplicated
    # nothing, because the set had already been built from the raw pair.
    found: set[str] = set()
    typed = str(gesture.gesture.value).strip() if gesture.gesture.value else ""
    if typed:
        found.add(typed)
    if intent is not None:
        found.update(text for seen in intent.values_seen if (text := str(seen.value).strip()))
    return found


def trivial(value: str, frequency: float) -> bool:
    """Too short, too common, or a literal that means nothing on its own."""
    text = str(value).strip()
    if len(text) < K_MIN_VALUE_LEN or text.lower() in _NEVER or frequency > K_UBIQUITY:
        return True
    # One bare word, and a short one: `test` in five applications is a
    # coincidence, `Test Drive LLC` in three is a carrier.
    lone = not any(character in text for character in " -_/.:@")
    return lone and len(text) < K_MIN_LONE_WORD


def frequencies_over(gestures: list[Gesture], intents: dict[str, Intent]) -> dict[str, float]:
    """How often each value appears across the tenant's gestures.

    Arithmetic, not a pattern, and the only thing here that needs history: a
    value carried by a quarter of everything is furniture rather than a link.

    Counted through typed_values, which is the same function shared_values
    below counts through. It used to read `values_seen` out of the intents
    table alone -- model output only -- so a value the operator actually TYPED
    on every gesture and that no reading ever echoed looked up at 0.0 and could
    never be classified as furniture, however ubiquitous it was. The two halves
    of one signal were being weighed on different scales.

    The ruling that still holds: the numerator is the number of GESTURES
    carrying a value, never the number of mentions, because K_UBIQUITY is a
    coverage fraction. typed_values returns a set, so a value named five times
    on one gesture is one gesture. The unit moved from "reading" to "gesture"
    with the source -- they are the same unit whenever a gesture has been read,
    and the gesture is the unit shared_values already divides the world into.
    """
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
    """Values appearing in more than one system, and the gestures carrying them."""
    seen: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for gesture in gestures:
        # A gesture whose system could not be established contributes nothing.
        # An unknown system is not a second system, and `system or ""` made it
        # one -- so one unattributable gesture beside one real system reported
        # a crossing. Same rule correlate._owner already applies to requests.
        if not gesture.system:
            continue
        for value in typed_values(gesture, intents.get(gesture.id)):
            # Already stripped by typed_values, so the frequency lookup and
            # the key agree with trivial() and frequencies_over(). They did not
            # before: the lookup missed, and furniture at frequency 1.0 was
            # published as a link, while one real crossing split four ways
            # across "Supplier-X", " Supplier-X" and "Supplier-X\n" became no
            # crossing at all. Not case-folded: the fixture has a `D3`, and
            # welding codes that differ only in case is the worse error.
            if trivial(value, frequencies.get(value, 0.0)):
                continue
            seen[value].append((gesture.id, gesture.system))

    crossings: dict[str, list[str]] = {}
    for value, occurrences in seen.items():
        if len({system for _, system in occurrences}) >= 2:
            crossings[value] = [gesture_id for gesture_id, _ in occurrences]
    return crossings
