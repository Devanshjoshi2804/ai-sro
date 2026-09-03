import json

from rig.correlate import correlate
from rig.trim import path_shape, thin, trim
from rig.wire import Batch, Target
from tests.fixtures import BATCH, GESTURE_TYPE


def _typed_gesture():
    gestures, _, _ = correlate(Batch.model_validate(BATCH), "new")
    return next(g for g in gestures if g.gesture.kind == "type" and not g.gesture.secret)


def test_the_component_chain_survives_because_it_is_what_names_the_control() -> None:
    trimmed = trim(_typed_gesture())

    assert trimmed["target"]["itemId"] == "clientCode"
    assert trimmed["target"]["fieldLabel"] == "Client Code"


def test_a_control_with_no_component_still_trims() -> None:
    gestures, _, _ = correlate(Batch.model_validate(BATCH), "new")
    select = next(g for g in gestures if g.gesture.kind == "select")

    trimmed = trim(select)

    assert trimmed["target"]["itemId"] is None
    assert trimmed["target"]["name"] == "Dock"


def test_cssPath_and_xpath_are_not_sent_to_the_model() -> None:
    """Long, meaningless to a model, and the two locators that break."""
    text = json.dumps(trim(_typed_gesture()))

    assert "cssPath" not in text
    assert "xpath" not in text
    assert "/html/body" not in text


def test_a_json_body_keeps_its_keys() -> None:
    gestures, _, _ = correlate(Batch.model_validate(BATCH), "new")
    with_post = next(g for g in gestures if any(r.method == "POST" for r in g.requests))

    calls = trim(with_post)["calls"]
    posted = next(c for c in calls if c["method"] == "POST")

    assert "clientCode" in posted["body_keys"]


def test_a_form_encoded_body_keeps_its_keys_too() -> None:
    """One of the committed calls is clientCode=ACME-4471&dock=D3."""
    from rig.trim import body_keys
    from rig.wire import Body

    body = Body(
        text="clientCode=ACME-4471&dock=D3",
        mime_type="application/x-www-form-urlencoded",
    )

    assert body_keys(body) == {"clientCode": "ACME-4471", "dock": "D3"}


def test_a_failed_call_with_no_body_does_not_explode() -> None:
    from rig.trim import body_keys

    assert body_keys(None) is None


def test_a_long_value_is_truncated() -> None:
    from rig.trim import VALUE_CHARS, body_keys
    from rig.wire import Body

    body = Body(text=json.dumps({"note": "x" * 500}), mime_type="application/json")

    assert len(body_keys(body)["note"]) <= VALUE_CHARS


def test_a_credential_gesture_carries_no_value() -> None:
    gestures, _, _ = correlate(Batch.model_validate(BATCH), "new")
    secret = next(g for g in gestures if g.gesture.secret)

    assert trim(secret)["value"] is None


def test_a_target_with_a_label_is_not_thin() -> None:
    assert thin(Target.model_validate(GESTURE_TYPE["gesture"]["target"])) is False


def test_a_target_with_only_a_css_path_is_thin() -> None:
    bare = Target.model_validate({"tag": "div", "cssPath": "div > div:nth-child(3)"})

    assert thin(bare) is True


def test_an_id_in_a_path_becomes_a_star() -> None:
    assert path_shape("https://x/data/WM/wm/addresses/1183") == "/data/WM/wm/addresses/*"
    assert path_shape("https://x/api/orders") == "/api/orders"
