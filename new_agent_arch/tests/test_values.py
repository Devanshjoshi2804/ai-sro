from rig.correlate import correlate
from rig.records import Intent, ValueSeen
from rig.values import K_MIN_VALUE_LEN, shared_values, trivial, typed_values
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
