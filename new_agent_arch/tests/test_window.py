import json

from rig.correlate import correlate
from rig.records import Intent
from rig.window import (
    K_MAX_GESTURE_TOKENS,
    K_MIN_GESTURES,
    arrange,
    as_evidence,
    pack,
    strength,
    tokens,
)
from rig.wire import Batch
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def test_tokens_is_a_length_not_a_guess() -> None:
    assert tokens("") == 0
    assert tokens("a" * 400) == 100


def test_evidence_carries_the_reading_beside_the_gesture() -> None:
    gesture = _gestures()[0]
    intent = Intent(gesture_id=gesture.id, tenant="acme", act="typed a code", why="because")

    evidence = as_evidence(gesture, intent)

    assert evidence["id"] == gesture.id
    assert evidence["intent"]["act"] == "typed a code"
    assert "target" in evidence["gesture"]


def test_a_gesture_with_no_reading_still_enters_the_window() -> None:
    """A failed reading must not remove the evidence from the pass."""
    evidence = as_evidence(_gestures()[0], None)

    assert evidence["intent"] is None
    assert evidence["gesture"]


def test_a_write_and_a_typed_value_are_stronger_than_a_read() -> None:
    gestures = _gestures()
    writing = next(g for g in gestures if any(r.method != "GET" for r in g.requests))
    reading = next(g for g in gestures if not g.requests)

    assert strength(writing, None, set()) > strength(reading, None, set())


def test_a_gesture_that_shares_a_value_across_systems_is_stronger() -> None:
    gesture = _gestures()[0]

    assert strength(gesture, None, {gesture.id}) > strength(gesture, None, set())


def test_no_single_gesture_may_eat_the_window() -> None:
    """Three of eighty-one real gestures held 71% of all request bytes, and two
    individually exceeded the whole budget."""
    # Only one gesture in the committed fixture carries requests -- the click
    # that every call attaches to. The first gesture has none.
    gesture = next(g for g in _gestures() if g.requests and g.requests[0].response_body)
    gesture.requests[0].response_body.text = "x" * 400_000

    evidence = as_evidence(gesture, None)

    assert tokens(json.dumps(evidence)) <= K_MAX_GESTURE_TOKENS


def test_the_middle_of_the_window_keeps_its_order() -> None:
    """Order-invariant representations degrade cross-application reconstruction.
    Only the ends are promoted; a workflow is a sequence."""
    from rig.window import Packed

    items = [Packed(f"ges_{n}", float(n), {}, float(n), 10) for n in range(40)]

    arranged = arrange(items)
    middle = [item.at for item in arranged[12:-12]]

    assert middle == sorted(middle)


def test_everything_that_fits_is_packed_in_time_order() -> None:
    gestures = _gestures()

    window = pack(gestures, {}, [], [], "", budget=150_000)

    assert len(window.items) == len(gestures)
    assert [i.at for i in window.items] == sorted(i.at for i in window.items)
    assert window.left_out == []


def test_a_budget_too_small_keeps_the_floor_and_reports_the_rest() -> None:
    """A quiet morning is still read, and what did not fit is named rather
    than silently missing."""
    gestures = _gestures() * 8

    window = pack(gestures, {}, [], [], "", budget=600)

    assert len(window.items) >= min(K_MIN_GESTURES, len(gestures))
    assert len(window.left_out) == len(gestures) - len(window.items)


def test_the_pool_is_favoured_over_equally_strong_new_evidence() -> None:
    from rig.window import Packed

    gestures = _gestures()[:2]
    pooled = [Packed("ges_pool", 0.0, {"id": "ges_pool"}, 1.0, 10)]

    window = pack(gestures, {}, pooled, [], "", budget=150_000)

    assert "ges_pool" in {item.gesture_id for item in window.items}
