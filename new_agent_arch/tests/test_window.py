import copy
import json

from rig.correlate import correlate
from rig.records import Intent, ValueSeen
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
    gesture = next(g for g in _gestures() if g.requests and g.requests[0].response_body)
    gesture.requests[0].response_body.text = "x" * 400_000

    evidence = as_evidence(gesture, None)

    assert tokens(json.dumps(evidence)) <= K_MAX_GESTURE_TOKENS


def test_the_cap_holds_by_every_route() -> None:
    """The test above passes with the cap deleted: trim() already truncates a
    body to VALUE_CHARS before as_evidence sees it. These are the routes that
    actually reach the cap, each measured past a body-only cap by 15x to 1000x.
    """
    huge = "x" * 4_000_000
    base = next(g for g in _gestures() if g.requests)

    value = copy.deepcopy(base)
    value.gesture.value = huge

    url = copy.deepcopy(base)
    url.url = "https://acme.example/" + huge

    many = copy.deepcopy(base)
    many.requests = [base.requests[0].model_copy(deep=True) for _ in range(2_000)]

    for name, gesture in (("value", value), ("url", url), ("calls", many)):
        size = tokens(json.dumps(as_evidence(gesture, None)))
        assert size <= K_MAX_GESTURE_TOKENS, f"{name}: {size}"

    # Model output, and nothing upstream bounds its length.
    loud = Intent(
        gesture_id=base.id,
        tenant="acme",
        act=huge,
        object=huge,
        page=huge,
        why=huge,
        confidence="high",
        values_seen=[ValueSeen(field=huge, value=huge)],
    )
    size = tokens(json.dumps(as_evidence(base, loud)))
    assert size <= K_MAX_GESTURE_TOKENS, f"intent: {size}"


def test_a_credential_the_model_echoed_back_does_not_reach_the_window() -> None:
    """trim() nulls the typed value. values_seen comes back from the model with
    the field already named, and went into the window unchecked."""
    gesture = copy.deepcopy(_gestures()[0])
    gesture.gesture.secret = True
    intent = Intent(
        gesture_id=gesture.id,
        tenant="acme",
        act="typed a password",
        values_seen=[ValueSeen(field="password", value="hunter2")],
    )

    evidence = as_evidence(gesture, intent)

    assert "hunter2" not in json.dumps(evidence)
    assert evidence["intent"]["values_seen"][0]["field"] == "password"


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
    """Equal strength, and the pool item is the latest thing in the window, so
    the tie-break on `at` sends it to the back. Only K_POOL_BONUS keeps it.

    The budget has to bite for the slot to be contested at all: the version of
    this test that packed two gestures into 150,000 tokens passed with the
    bonus deleted.
    """
    from rig.window import Packed

    # The committed fixture has seven gestures; only two -- one "click", one
    # "press" -- carry neither a request nor a type/select/upload bonus, so
    # only those two sit at strength 1.0, equal to the pool item's own raw
    # strength. (The brief's `kind == "click"` filter alone yields exactly
    # one such gesture in this fixture, not the four it assumes; broadened
    # here to the two kinds that share the same baseline strength, which
    # keeps the tie the test depends on.)
    base = [g for g in _gestures() if not g.requests and g.gesture.kind in ("click", "press")]
    assert len(base) >= 2, "fixture must offer plain clicks/presses to contest with"
    plain = []
    for run in range(K_MIN_GESTURES):
        for gesture in base:
            dup = copy.deepcopy(gesture)
            dup.id = f"{gesture.id}_{run}"
            plain.append(dup)

    pooled = [Packed("ges_pool", max(g.at for g in plain) + 1000.0, {"id": "ges_pool"}, 1.0, 10)]

    # 6_000 (the brief's figure) does not bite against only 50 candidates at
    # ~107 tokens each -- everything fits and nothing is contested. 2_680 sits
    # in the middle of a wide, empirically-checked band (2_650-2_700) where
    # the K_MIN_GESTURES floor is exactly met and the pool slot is genuinely
    # contested.
    window = pack(plain, {}, pooled, [], "", budget=2_680)

    assert window.left_out, "budget must bite, or no slot is contested"
    assert "ges_pool" in {item.gesture_id for item in window.items}


def test_packing_twice_does_not_compound_the_pool_bonus() -> None:
    from rig.window import Packed

    pooled = [Packed("ges_pool", 0.0, {"id": "ges_pool"}, 1.0, 10)]

    pack(_gestures(), {}, pooled, [], "", budget=150_000)
    pack(_gestures(), {}, pooled, [], "", budget=150_000)

    assert pooled[0].strength == 1.0
