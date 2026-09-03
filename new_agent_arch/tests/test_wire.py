import pytest
from pydantic import ValidationError

from rig.wire import Batch, GestureEvent, RequestEvent
from tests.fixtures import (
    BATCH,
    GESTURE_CLICK,
    GESTURE_SECRET,
    GESTURE_TYPE,
    REQUEST_FAILED,
    REQUEST_POST,
)


def test_the_committed_batch_parses_unchanged() -> None:
    batch = Batch.model_validate(BATCH)

    assert batch.device_id == "dev_browsertest"
    assert batch.mode == "passive"
    assert len(batch.events) == len(BATCH["events"])


def test_a_batch_id_is_not_required_to_be_hex() -> None:
    """The real one is bat_browsertest_418908ee_1."""
    assert Batch.model_validate(BATCH).batch_id.startswith("bat_")


def test_an_extjs_control_keeps_its_component_chain() -> None:
    event = GestureEvent.model_validate(GESTURE_TYPE)

    assert event.gesture.target.component is not None
    assert event.gesture.target.component.itemId == "clientCode"
    assert event.gesture.target.component.query == "panel#clients textfield#clientCode"


def test_a_plain_html_control_has_component_null() -> None:
    """Only ExtJS widgets carry one. It is an explicit null, not an absent key."""
    select = next(
        e
        for e in BATCH["events"]
        if e["kind"] == "gesture" and e["gesture"]["kind"] == "select"
    )

    event = GestureEvent.model_validate(select)

    assert event.gesture.target.component is None


def test_a_click_carries_neither_value_nor_secret() -> None:
    assert "value" not in GESTURE_CLICK["gesture"]
    assert "secret" not in GESTURE_CLICK["gesture"]

    event = GestureEvent.model_validate(GESTURE_CLICK)

    assert event.gesture.value is None
    assert event.gesture.secret is False


def test_a_credential_value_does_not_survive_parsing() -> None:
    """AGENTS.md: credential values never reach storage. This is the boundary."""
    loud = {**GESTURE_SECRET}
    loud["gesture"] = {**GESTURE_SECRET["gesture"], "value": "hunter2"}

    event = GestureEvent.model_validate(loud)

    assert event.gesture.secret is True
    assert event.gesture.value is None
    assert "hunter2" not in event.model_dump_json()


def test_a_request_event_carries_its_own_tab() -> None:
    """A1 relies on this instead of guessing a tab from a host."""
    event = RequestEvent.model_validate(REQUEST_POST)

    assert event.tab_id is not None


def test_a_failed_request_has_no_status_and_no_bodies() -> None:
    event = RequestEvent.model_validate(REQUEST_FAILED)

    assert event.request.status is None
    assert event.request.response_body is None
    assert event.request.failure_reason


def test_a_target_with_no_usable_signal_is_refused() -> None:
    naked = {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "target": {"tag": "div", "component": None},
            "at": 1.0,
            "url": "https://wms.example/",
        },
        "tab_id": 1,
    }

    with pytest.raises(ValidationError):
        GestureEvent.model_validate(naked)
