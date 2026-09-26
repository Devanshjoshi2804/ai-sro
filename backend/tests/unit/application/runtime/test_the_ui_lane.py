import asyncio
import json
from dataclasses import replace
from typing import NoReturn

import pytest

from sro.application.ports.page import PageAnswer, PageGone
from sro.application.runtime.step import Stopped
from sro.application.runtime.ui_lane import UiLane, same_call, ui_payload
from sro.domain.execution.compose import Adding
from sro.domain.execution.lanes import Lane, SeenCall
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.observation.gesture import (
    Action,
    AfterState,
    Body,
    Call,
    Component,
    Gesture,
    Target,
)
from sro.domain.skill.workflow import Step
from tests.unit.fakes import FakePageDriver
from tests.unit.runtime_support import (
    lane_context,
    read_step,
    save_step,
    scripted_driver,
    type_step,
    type_then_save_step,
)

SHOWN = AfterState(value=None, visible=True, enabled=True)
SAVED = SeenCall("POST", "https://wms.example/api/customer-types", 201, '{"id": "ct-9"}')


async def test_a_write_the_page_confirms_is_done_with_no_model_and_no_sleep() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"),
        calls=[SeenCall("POST", "https://wms.example/api/customer-types", 201, '{"id": "ct-9"}')],
    )
    step, by_id = save_step(status=201)
    written: list[int] = []

    async def wrote(lane: Lane) -> None:
        written.append(step.order)

    ctx = lane_context(by_id, about_to_write=wrote)

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, ctx)

    assert (result.verdict, result.lane.value) == ("done", "ui")
    assert result.read == {"id": "ct-9"}
    assert written == [step.order]


async def test_a_write_nothing_confirms_is_unknown_never_done() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="css_path"), calls=[])
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_typed_value_is_confirmed_by_the_state_it_left() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="attributes"), holds=True)
    step, by_id = type_step(after=AfterState(value="GT1", visible=True, enabled=True))

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id))

    assert result.verdict == "done"
    assert driver.waited_for[-1]["expect"] == {"value": "GT2", "visible": True, "enabled": True}


async def test_a_missing_control_on_a_sign_in_page_is_an_expired_session() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"),
        sign_in=True,
        url="https://idp.example/login",
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.expired and result.verdict == "failed"


async def test_a_password_form_on_the_recorded_page_itself_is_not_an_expired_session() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"),
        sign_in=True,
        url="https://wms.example/app",
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert not result.expired and result.verdict == "failed"


async def test_a_page_that_never_settled_before_any_write_never_left() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"), unsettled=True
    )
    step, by_id = type_step()

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and result.never_left


async def test_a_page_that_never_settled_after_about_to_write_is_unknown() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=False, error_kind="control_not_found"), unsettled=True
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown" and not result.never_left


async def test_a_missing_control_is_fingerprinted_for_the_known_broken_list() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"))
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and result.fingerprint


async def test_a_save_button_that_is_still_there_does_not_confirm_a_write() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"), holds=True)
    step, by_id = save_step(status=201, after=SHOWN)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_typing_the_value_of_a_write_is_not_the_write() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="attributes"), holds=True)
    step, by_id = type_then_save_step()

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id))

    assert driver.acted[-1][2]["action"] == "type"
    assert result.verdict == "unknown"


async def test_a_call_log_lost_to_a_reconnect_leaves_the_write_unknown() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"), before=[SAVED], holds=True
    )
    step, by_id = save_step(status=201, after=SHOWN)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_call_numbered_before_the_mark_is_not_this_steps_write() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"), before=[SAVED])
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert (result.verdict, result.read) == ("unknown", {})


async def test_a_same_shape_2xx_from_another_frame_does_not_confirm_a_write() -> None:
    background = SeenCall(
        "POST", "https://wms.example/api/customer-types", 201, '{"id": "ct-9"}', own_frame=False
    )
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"), calls=[background])
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_same_shape_2xx_from_another_host_does_not_confirm_a_write() -> None:
    elsewhere = SeenCall("POST", "https://other.example/api/customer-types", 201, '{"id": "ct-9"}')
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"), calls=[elsewhere])
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_same_shape_2xx_with_different_body_keys_does_not_confirm_a_write() -> None:
    other_fields = SeenCall(
        "POST",
        "https://wms.example/api/customer-types",
        201,
        '{"id": "ct-9"}',
        request_body='{"other": "x"}',
        request_content_type="application/json",
    )
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"), calls=[other_fields]
    )
    step, by_id = save_step(
        status=201, body=Body(text='{"name": "GT2"}', mime_type="application/json")
    )

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_same_shape_2xx_with_matching_body_keys_confirms_the_write() -> None:
    same_fields = SeenCall(
        "POST",
        "https://wms.example/api/customer-types",
        201,
        '{"id": "ct-9"}',
        request_body='{"name": "GT2"}',
        request_content_type="application/json",
    )
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"), calls=[same_fields]
    )
    step, by_id = save_step(
        status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json")
    )

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert (result.verdict, result.read) == ("done", {"id": "ct-9"})


async def test_an_after_state_that_does_not_hold_turns_a_confirmed_write_unknown() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"), calls=[SAVED], holds=False
    )
    step, by_id = save_step(status=201, after=SHOWN)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


@pytest.mark.parametrize(("status", "verdict"), [(422, "failed"), (503, "unknown")])
async def test_an_after_state_never_turns_a_rejected_or_unanswered_write_done(
    status: int, verdict: str
) -> None:
    rejected = SeenCall("POST", "https://wms.example/api/customer-types", status)
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"), calls=[rejected], holds=True
    )
    step, by_id = save_step(status=201, after=SHOWN)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == verdict


async def test_the_created_record_comes_only_from_the_writes_own_call() -> None:
    audit = SeenCall("POST", "https://wms.example/api/audit", 201, '{"id": "audit-1"}')
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"), calls=[audit, SAVED]
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert (result.verdict, result.read) == ("done", {"id": "ct-9"})


async def test_a_read_takes_only_the_call_the_recording_made() -> None:
    polled = SeenCall("GET", "https://wms.example/api/notifications", 200, '{"id": "n-1"}')
    telemetry = SeenCall("POST", "https://wms.example/api/telemetry", 200, '{"id": "t-1"}')
    orders = SeenCall("GET", "https://wms.example/api/orders?page=1", 200, '{"orderId": "o-7"}')
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="role_and_name"), calls=[polled, orders, telemetry]
    )
    step, by_id = read_step()

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert (result.verdict, result.read) == ("read", {"orderId": "o-7"})


async def test_a_read_whose_own_call_never_came_is_not_read_from_another() -> None:
    polled = SeenCall("GET", "https://wms.example/api/notifications", 200, '{"id": "n-1"}')
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="role_and_name"), calls=[polled])
    step, by_id = read_step()

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict != "read" and result.read == {}


async def test_a_repaired_match_with_no_after_state_is_never_done() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="repair", repaired=True))
    step, by_id = read_step()

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_repaired_match_whose_state_holds_is_unknown_not_done_or_broken() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="repair", repaired=True), holds=True
    )
    step, by_id = read_step(after=SHOWN)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert (result.verdict, result.fingerprint) == ("unknown", "")


async def test_the_pin_act_answered_is_the_element_holds_checks() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="attributes", pin="pin-7"), holds=True
    )
    step, by_id = type_step(after=SHOWN)

    await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id))

    assert driver.waited_for[-1]["pin"] == "pin-7"


def test_only_a_step_that_does_not_write_is_marked_write_false() -> None:
    saving, saved_by = save_step(status=201)
    reading, read_by = read_step()

    wrote = ui_payload(saving, saved_by["ges_save"], None, None, saved_by)
    read = ui_payload(reading, read_by["ges_orders"], None, None, read_by)

    assert "write" not in wrote
    assert read["write"] is False


HOPS = [{"index": 1, "url": "/frames/form"}]
SIGHTED = LearnedStep(1, "component", "#saveButton", "sight", frame_path=json.dumps(HOPS))


async def test_a_sight_learned_locator_alone_is_looked_for_in_its_own_frame() -> None:
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="learned"),
        calls=[SeenCall("POST", "https://wms.example/api/customer-types", 201)],
    )
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id, learned={1: SIGHTED}))

    assert result.verdict == "done"
    [(_, _, asked)] = driver.acted
    assert asked["frame_path"] == HOPS and asked["target"] == {}
    assert asked["learned"] == {"strategy": "component", "query": "#saveButton"}


async def test_the_recorded_locators_keep_their_recorded_frame() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"))
    step, by_id = save_step(status=201)

    await UiLane(driver).execute(step, {}, lane_context(by_id, learned={1: SIGHTED}))

    first, then = (asked for _, _, asked in driver.acted)
    assert first["frame_path"] == HOPS and first["target"] == {}
    assert then["frame_path"] is None and then["learned"] is None
    assert then["target"] == ui_payload(step, by_id["ges_save"], None, None, by_id)["target"]


async def test_a_control_that_was_never_found_never_left() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"))
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert (result.verdict, result.never_left) == ("failed", True)


class _Breaks:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    async def __call__(self, *args: object, **kwargs: object) -> NoReturn:
        raise self.error


@pytest.mark.parametrize("error", [PageGone("tab gone"), RuntimeError("Frame was detached")])
async def test_anything_that_breaks_after_the_write_is_announced_is_unknown(
    error: Exception,
) -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"))
    driver.calls_since = _Breaks(error)  # type: ignore[method-assign]
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert (result.verdict, result.never_left) == ("unknown", False)


@pytest.mark.parametrize("error", [Stopped("stopped"), asyncio.CancelledError()])
async def test_a_stop_or_a_cancel_after_the_write_is_announced_still_propagates(
    error: BaseException,
) -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"))
    driver.act = _Breaks(error)  # type: ignore[method-assign]
    step, by_id = save_step(status=201)

    with pytest.raises(type(error)):
        await UiLane(driver).execute(step, {}, lane_context(by_id))


def _saved(body: str) -> SeenCall:
    return SeenCall(
        "POST",
        "https://wms.example/api/customer-types",
        201,
        request_body=body,
        request_content_type="application/json",
    )


async def test_the_save_call_that_carries_the_new_field_keys_it() -> None:
    step, by_id = save_step(
        status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json")
    )
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"),
        calls=[_saved('{"name": "GT9", "department": "Operations"}')],
    )
    ctx = lane_context(by_id, adding={step.order: Adding(fresh={"department": "Operations"})})

    result = await UiLane(driver).execute(step, {}, ctx)

    assert result.verdict == "done"
    assert dict(result.keyed) == {"department": "department"}


async def test_a_save_call_without_the_new_field_is_done_and_keys_nothing() -> None:
    step, by_id = save_step(
        status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json")
    )
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"), calls=[_saved('{"name": "GT9"}')]
    )
    ctx = lane_context(by_id, adding={step.order: Adding(fresh={"department": "Operations"})})

    result = await UiLane(driver).execute(step, {}, ctx)

    assert (result.verdict, dict(result.keyed)) == ("done", {})


async def test_more_new_keys_than_fields_filled_is_not_this_writes_own_call() -> None:
    step, by_id = save_step(
        status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json")
    )
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"),
        calls=[_saved('{"name": "GT9", "department": "Operations", "owner": "x"}')],
    )
    ctx = lane_context(by_id, adding={step.order: Adding(fresh={"department": "Operations"})})

    result = await UiLane(driver).execute(step, {}, ctx)

    assert result.verdict == "unknown"


RECORDED_NAME = Body(text='{"name": "GT1"}', mime_type="application/json")
RECORDED = Call(
    "POST", "https://wms.example/api/customer-types", 201, 1.0, request_body=RECORDED_NAME
)


@pytest.mark.parametrize(
    "body",
    [
        '{"name": "GT9", "validateOnly": true}',
        '{"name": "GT9", "department": null}',
        '{"name": "GT9", "department": "Finance"}',
    ],
)
def test_an_extra_key_that_is_not_the_filled_controls_value_is_not_the_writes_own(
    body: str,
) -> None:
    held = Adding(fresh={"department": "3"})

    assert same_call(_saved(body), RECORDED, held) is None


def test_a_select_sending_its_option_code_keys_the_field() -> None:
    held = Adding(fresh={"department": "3"})

    assert same_call(_saved('{"name": "GT9", "department": "3"}'), RECORDED, held) == {
        "department": "department"
    }


async def test_the_keys_come_from_the_call_that_confirmed_the_write() -> None:
    step, by_id = save_step(status=201, body=RECORDED_NAME)
    refused = replace(_saved('{"name": "GT9", "department": "Operations"}'), status=409)
    driver = scripted_driver(
        answer=PageAnswer(ok=True, matched_by="component"),
        calls=[refused, _saved('{"name": "GT9"}')],
    )
    ctx = lane_context(by_id, adding={step.order: Adding(fresh={"department": "Operations"})})

    result = await UiLane(driver).execute(step, {}, ctx)

    assert (result.verdict, dict(result.keyed)) == ("done", {})


def _two_fields(*labels: str) -> tuple[Step, dict[str, Gesture]]:
    """One step typing two fields, as demonstrated: "GT1" and "north"."""
    by_id: dict[str, Gesture] = {}
    for nth, (label, typed) in enumerate(zip(labels, ("GT1", "north"), strict=True)):
        gesture = Gesture(
            id=f"ges_field_{nth}",
            tenant="acme",
            stream_id="stream-1",
            batch_id="batch-1",
            at=float(nth + 1),
            url="https://wms.example/app",
            system="https://wms.example",
            tab_id=1,
            frame_url=None,
            action=Action(
                kind="type",
                at=float(nth + 1),
                value=typed,
                target=Target(role="textbox", name=label, component=Component(field_label=label)),
            ),
        )
        by_id[gesture.id] = gesture
    step = Step(
        order=0,
        says="Fill the customer type",
        system="https://wms.example",
        cites=list(by_id),
        parameters=["Customer Type", "Description"],
    )
    return step, by_id


def _typed(driver: FakePageDriver) -> list[object]:
    return [payload.get("value") for _, _, payload in driver.acted]


async def test_a_step_with_one_of_its_two_values_types_only_that_one() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"), holds=True)
    step, by_id = _two_fields("Customer Type", "Description")

    await UiLane(driver).execute(step, {"Description": "south"}, lane_context(by_id))

    assert _typed(driver) == ["south"]
    assert driver.acted[0][2]["target"]["name"] == "Description"


async def test_a_control_whose_own_value_is_absent_is_never_typed_another_s() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"), holds=True)
    step, by_id = _two_fields("Type", "Desc")

    result = await UiLane(driver).execute(step, {"Description": "south"}, lane_context(by_id))

    assert result.verdict == "failed"
    assert _typed(driver) == []
    assert not {"GT1", "north", "south"} & {str(one) for one in _typed(driver)}
