import json

from rig.correlate import correlate
from rig.records import Gesture
from rig.trim import path_shape, thin, trim
from rig.wire import Batch, Target
from rig.wire import Gesture as WireGesture
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


def test_an_ordinary_hyphenated_route_survives() -> None:
    """The rule this replaced starred any long hyphenated segment, erasing the
    route information that says what the operator actually did."""
    assert path_shape("https://x/api/client-code-detail") == "/api/client-code-detail"
    assert path_shape("https://x/api/order-status") == "/api/order-status"


def test_a_segment_that_is_mostly_digits_is_an_id() -> None:
    assert path_shape("https://x/api/sku-123456") == "/api/*"
    assert path_shape("https://x/api/product-8834726591") == "/api/*"


def test_a_uuid_is_an_id() -> None:
    assert path_shape("https://x/v1/f47ac10b-58cc-4372-a567-0e02b2c3d479/edit") == "/v1/*/edit"


def test_a_targetless_scroll_trims_and_thins_without_a_crash() -> None:
    """The committed batch has no scroll, and correlate() only ever produces
    a Gesture from a parsed event -- so this builds the records.Gesture
    directly, the way correlate() itself does, rather than going through it."""
    scroll = Gesture(
        id="ges_scroll",
        tenant="new",
        stream_id="dev_test",
        batch_id="bat_test",
        at=1.0,
        url="https://wms.example/portal/page",
        system="https://wms.example",
        tab_id=8,
        frame_url="https://wms.example/portal/page",
        gesture=WireGesture(kind="scroll", value="0", at=1.0),
    )

    assert thin(scroll.gesture.target) is True

    trimmed = trim(scroll)

    assert trimmed["target"]["role"] is None
    assert trimmed["target"]["name"] is None
    assert trimmed["target"]["text"] is None
    assert trimmed["target"]["testId"] is None
    assert trimmed["target"]["itemId"] is None
    assert trimmed["target"]["fieldLabel"] is None
    assert trimmed["target"]["xtype"] is None
    assert trimmed["target"]["query"] is None


def test_a_credential_cannot_be_reached_by_mutating_the_target() -> None:
    """trim() holds this itself rather than inheriting it from wire.Gesture,
    whose validator does not re-run when a nested Target is mutated."""
    gestures, _, _ = correlate(Batch.model_validate(BATCH), "new")
    ordinary = next(g for g in gestures if g.gesture.kind == "type" and not g.gesture.secret)

    ordinary.gesture.target.secret = True

    assert trim(ordinary)["value"] is None
