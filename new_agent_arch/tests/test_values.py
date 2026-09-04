from pathlib import Path

from rig.api import save_intent
from rig.correlate import correlate
from rig.records import Intent, ValueSeen
from rig.store import Store
from rig.values import (
    K_MIN_VALUE_LEN,
    K_UBIQUITY,
    frequencies_over,
    shared_values,
    trivial,
    typed_values,
)
from rig.wire import Batch
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def test_a_typed_value_is_found() -> None:
    typed = next(g for g in _gestures() if g.gesture.kind == "type" and g.gesture.value)

    assert typed.gesture.value in typed_values(typed, None)


def test_a_value_the_reading_saw_is_found_too() -> None:
    gesture = _gestures()[0]
    intent = Intent(
        gesture_id=gesture.id,
        tenant="acme",
        values_seen=[ValueSeen(field="supplier", value="TestYonder2")],
    )

    assert "TestYonder2" in typed_values(gesture, intent)


def test_a_credential_value_is_never_a_link() -> None:
    """It is not in the gesture to begin with, and must not arrive by any
    other route either.

    The first assertion alone cannot fail: wire.Gesture nulls a credential at
    parse time, so it holds with the is_secret guard deleted entirely. The
    route that can fail is the model's -- it is shown the field the value went
    into, and values_seen comes back unvalidated, so a password echoed there
    became a cross-system link."""
    secret = next(g for g in _gestures() if g.gesture.secret)

    assert typed_values(secret, None) == set()

    echoed = Intent(
        gesture_id=secret.id,
        tenant="acme",
        values_seen=[ValueSeen(field="password", value="hunter2")],
    )

    assert typed_values(secret, echoed) == set()


def test_something_too_short_links_nothing() -> None:
    assert trivial("SG", 0.0) is True
    assert trivial("x" * K_MIN_VALUE_LEN, 0.0) is False


def test_a_value_on_every_call_is_furniture() -> None:
    """A facility code every call carries links nothing; a supplier name typed
    once in two systems links a great deal."""
    assert trivial("DC1-WAREHOUSE", 0.9) is True
    assert trivial("DC1-WAREHOUSE", 0.01) is False


def test_a_value_seen_in_one_system_only_is_not_a_crossing() -> None:
    gestures = _gestures()
    intents = {
        g.id: Intent(
            gesture_id=g.id, tenant="acme", values_seen=[ValueSeen(field="f", value="ACME-4471")]
        )
        for g in gestures
    }

    assert shared_values(gestures, intents, {}) == {}


def test_a_value_in_two_systems_is_a_crossing() -> None:
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    intents = {
        g.id: Intent(
            gesture_id=g.id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="TestYonder2")],
        )
        for g in gestures
    }

    crossings = shared_values(gestures, intents, {})

    assert "TestYonder2" in crossings
    assert set(crossings["TestYonder2"]) == {gestures[0].id, gestures[1].id}


def test_furniture_with_whitespace_around_it_is_still_furniture() -> None:
    """trivial() and frequencies_over() strip; shared_values did not, so the
    frequency lookup missed and furniture at 1.0 was published as a link."""
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    intents = {
        g.id: Intent(
            gesture_id=g.id,
            tenant="acme",
            values_seen=[ValueSeen(field="site", value=" DC1-WAREHOUSE ")],
        )
        for g in gestures
    }

    assert shared_values(gestures, intents, {"DC1-WAREHOUSE": 1.0}) == {}


def test_one_value_written_four_ways_is_one_crossing() -> None:
    """Otherwise a real crossing splits into several and none of them cross."""
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    intents = {
        gestures[0].id: Intent(
            gesture_id=gestures[0].id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="Supplier-X")],
        ),
        gestures[1].id: Intent(
            gesture_id=gestures[1].id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="Supplier-X\n")],
        ),
    }

    crossings = shared_values(gestures, intents, {})

    assert set(crossings) == {"Supplier-X"}
    assert set(crossings["Supplier-X"]) == {gestures[0].id, gestures[1].id}


def test_a_gesture_with_no_known_system_does_not_make_a_crossing() -> None:
    """An unknown system is not a second system. `system or ""` made it one, so
    one unattributable gesture beside one real system reported a crossing."""
    gestures = _gestures()[:2]
    gestures[0].system = None
    gestures[1].system = "https://sap.example"
    intents = {
        g.id: Intent(
            gesture_id=g.id,
            tenant="acme",
            values_seen=[ValueSeen(field="supplier", value="SUPPLIER-X")],
        )
        for g in gestures
    }

    assert shared_values(gestures, intents, {}) == {}


def test_a_value_named_twice_in_one_reading_is_one_reading(tmp_path: Path) -> None:
    """K_UBIQUITY is a coverage fraction. Counting mentions instead of readings
    marked a value seen in a single reading out of ten as furniture at 0.3 and
    dropped it from every crossing."""
    store = Store(tmp_path / "rig.db")
    store.migrate()
    for n in range(10):
        seen = (
            [ValueSeen(field="supplier", value="SUPPLIER-X")] * 2
            if n == 0
            else [ValueSeen(field="site", value="DC1-WAREHOUSE")]
        )
        save_intent(store, Intent(gesture_id=f"ges_{n}", tenant="acme", values_seen=seen))

    frequencies = frequencies_over(store, "acme")

    assert frequencies["SUPPLIER-X"] == 0.1
    assert frequencies["SUPPLIER-X"] <= K_UBIQUITY


def test_one_gesture_saying_a_value_twice_is_cited_once() -> None:
    """typed_values is a set, so the same value typed and reported collapses --
    but only if it is stripped before the set is built. Stripping in the caller
    deduplicated nothing, and the gesture was cited twice for one doing."""
    gestures = _gestures()[:2]
    gestures[0].system = "https://wms.example"
    gestures[1].system = "https://sap.example"
    typed = gestures[0].gesture.value
    assert typed
    intents = {
        gestures[0].id: Intent(
            gesture_id=gestures[0].id,
            tenant="acme",
            values_seen=[ValueSeen(field="code", value=f" {typed} ")],
        ),
        gestures[1].id: Intent(
            gesture_id=gestures[1].id,
            tenant="acme",
            values_seen=[ValueSeen(field="code", value=typed)],
        ),
    }

    crossings = shared_values(gestures, intents, {})

    assert crossings[typed] == [gestures[0].id, gestures[1].id]


def test_a_non_str_value_from_the_store_does_not_take_the_crossing_down() -> None:
    """api._row_to_intent builds ValueSeen(**seen) from unvalidated stored JSON
    and ValueSeen is a plain dataclass, so a bare .strip() here raises
    AttributeError on an int. Unreachable today; the defence keeps it so."""
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "new")
    gesture = next(g for g in gestures if not g.gesture.secret)
    intent = Intent(
        gesture_id=gesture.id,
        tenant="new",
        values_seen=[ValueSeen(field="qty", value=42)],  # what ValueSeen(**seen) builds
    )

    assert "42" in typed_values(gesture, intent)
