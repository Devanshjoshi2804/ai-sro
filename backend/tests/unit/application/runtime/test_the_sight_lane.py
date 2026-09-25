import asyncio
from dataclasses import replace
from typing import Any

import pytest

from sro.application.ports.page import PageGone
from sro.application.ports.vision import ProposedGesture
from sro.application.runtime.sight_lane import SightLane
from sro.application.runtime.step import Stopped
from sro.domain.execution.lanes import K_SIGHT_ACTIONS, SeenCall
from sro.domain.observation.gesture import AfterState, Gesture, PageMark
from sro.domain.recording.events import ActionKind
from sro.domain.skill.workflow import Step
from tests.unit.fakes import FakeVisionDriver
from tests.unit.runtime_support import (
    lane_context,
    read_step,
    save_step,
    scripted_driver,
    type_step,
    type_then_save_step,
)

APP = "https://wms.example/app"
SAVED = SeenCall("POST", "https://wms.example/api/customer-types", 201)
HIT = {"strategy": "component", "query": "#saveButton", "frame_path": []}


def clicks_then_done() -> FakeVisionDriver:
    return FakeVisionDriver(
        ProposedGesture(ActionKind.CLICK, x=400, y=20),
        ProposedGesture(ActionKind.HOVER, done=True),
    )


async def test_sight_acts_by_points_and_teaches_the_control_it_hit() -> None:
    driver = scripted_driver(url=APP, hit=HIT, calls=[SAVED])
    step, by_id = save_step(status=201)
    written: list[int] = []

    async def wrote() -> None:
        written.append(step.order)

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, {}, lane_context(by_id, about_to_write=wrote)
    )

    assert result.verdict == "done"
    assert dict(result.learned) == {
        "strategy": "component",
        "query": "#saveButton",
        "frame_path": "[]",
    }
    assert driver.pointed == [("click", 400, 20, None)]
    assert written == [step.order]


async def test_the_model_saying_done_never_confirms_a_write() -> None:
    driver = scripted_driver(url=APP, hit=HIT, calls=[])
    step, by_id = save_step(status=201)

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "unknown"


async def test_a_call_from_another_frame_is_not_the_writes_own_call() -> None:
    other = SeenCall("POST", SAVED.url, 201, own_frame=False)
    driver = scripted_driver(url=APP, hit=HIT, calls=[other])
    step, by_id = save_step(status=201)

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "unknown"


async def test_a_read_is_settled_by_its_call_not_by_the_model() -> None:
    step, by_id = read_step()
    listed = SeenCall("GET", "https://wms.example/api/orders", 200, '{"id": "o-1"}')

    heard = await SightLane(
        scripted_driver(url=APP, hit=HIT, calls=[listed]), clicks_then_done(), None
    ).execute(step, {}, lane_context(by_id))
    unheard = await SightLane(scripted_driver(url=APP, hit=HIT), clicks_then_done(), None).execute(
        step, {}, lane_context(by_id)
    )

    assert heard.verdict == "read"
    assert unheard.verdict == "unknown"


@pytest.mark.parametrize(
    "hit",
    [None, {"strategy": "component", "query": "#saveButton"}],
    ids=["nothing", "no_frame_path"],
)
async def test_a_hit_without_a_frame_path_teaches_nothing(
    hit: dict[str, object] | None,
) -> None:
    driver = scripted_driver(url=APP, hit=hit, calls=[SAVED])
    step, by_id = save_step(status=201)

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "done" and dict(result.learned) == {}


async def test_a_point_that_lands_in_a_cross_origin_frame_is_never_made() -> None:
    unreachable = {
        "strategy": None,
        "query": None,
        "unreachable": "cross_origin_frame",
        "frame_path": [{"index": 0, "url": "https://widgets.example/"}],
        "x": 3,
        "y": 4,
    }
    driver = scripted_driver(url=APP, hit=unreachable, calls=[SAVED])
    step, by_id = type_step()
    flash = FakeVisionDriver(ProposedGesture(ActionKind.TYPE, x=5, y=5, value="GT2"))

    result = await SightLane(driver, flash, None).execute(
        step, {"Customer Type": "GT2"}, lane_context(by_id)
    )

    assert result.verdict == "failed" and driver.pointed == []


async def test_once_the_writes_call_is_sent_sight_stops_and_never_escalates() -> None:
    driver = scripted_driver(url=APP, hit=HIT, calls=[SAVED])
    step, by_id = save_step(status=201)
    flash = FakeVisionDriver(
        ProposedGesture(ActionKind.CLICK, x=400, y=20),
        ProposedGesture(ActionKind.HOVER, refusal="the form still shows"),
    )
    pro = FakeVisionDriver(ProposedGesture(ActionKind.CLICK, x=400, y=20))

    result = await SightLane(driver, flash, pro).execute(step, {}, lane_context(by_id))

    assert driver.pointed == [("click", 400, 20, None)]
    assert (len(flash.asked), pro.asked) == (1, [])
    assert result.verdict == "done"


async def test_a_write_sent_and_not_yet_answered_stops_sight_as_unknown() -> None:
    sent = SeenCall("POST", SAVED.url, None)
    driver = scripted_driver(url=APP, hit=HIT, calls=[sent])
    step, by_id = save_step(status=201)
    again = ProposedGesture(ActionKind.CLICK, x=400, y=20)
    flash, pro = FakeVisionDriver(again, again), FakeVisionDriver(again)

    result = await SightLane(driver, flash, pro).execute(step, {}, lane_context(by_id))

    assert driver.pointed == [("click", 400, 20, None)] and pro.asked == []
    assert result.verdict == "unknown" and not result.never_left


async def test_the_home_origin_is_the_recorded_url_never_the_steps_system_text() -> None:
    step, by_id = save_step(status=201)
    flash = FakeVisionDriver(ProposedGesture(ActionKind.CLICK, x=1, y=1))
    evil = scripted_driver(url="https://evil.example/app", hit=HIT)

    widened = await SightLane(evil, flash, None).execute(
        replace(step, system="https://evil.example"), {}, lane_context(by_id)
    )
    named = scripted_driver(url=APP, hit=HIT, calls=[SAVED])
    kept = await SightLane(named, clicks_then_done(), None).execute(
        replace(step, system="Blue Yonder WMS"), {}, lane_context(by_id)
    )

    assert widened.verdict == "failed" and evil.pointed == []
    assert kept.verdict == "done" and named.pointed == [("click", 400, 20, None)]


async def test_a_downgrade_to_http_on_the_same_host_is_off_the_system() -> None:
    step, by_id = save_step(status=201)
    driver = scripted_driver(url="http://wms.example/app", hit=HIT)
    flash = FakeVisionDriver(ProposedGesture(ActionKind.CLICK, x=1, y=1))

    result = await SightLane(driver, flash, None).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and driver.pointed == []


class _Breaks:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    async def __call__(self, *args: object, **kwargs: object) -> None:
        raise self.error


async def test_a_write_whose_first_point_breaks_is_unknown_not_raised() -> None:
    driver = scripted_driver(url=APP, hit=HIT)
    driver.point = _Breaks(PageGone("the save navigated away"))  # type: ignore[method-assign]
    step, by_id = save_step(status=201)

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "unknown" and not result.never_left


@pytest.mark.parametrize("error", [Stopped("stop"), asyncio.CancelledError()])
async def test_a_stop_during_a_write_still_propagates(error: BaseException) -> None:
    driver = scripted_driver(url=APP, hit=HIT)
    driver.point = _Breaks(error)  # type: ignore[method-assign]
    step, by_id = save_step(status=201)

    with pytest.raises(type(error)):
        await SightLane(driver, clicks_then_done(), None).execute(step, {}, lane_context(by_id))


DEPARTMENT = {
    "strategy": "role_and_name",
    "query": "textbox|Customer Type",
    "frame_path": [],
    "pin": "p-ct",
}
CANCEL = {"strategy": "role_and_name", "query": "button|Cancel", "frame_path": [], "pin": "p-x"}


async def test_a_blur_click_on_cancel_never_teaches_a_write() -> None:
    step, by_id = type_then_save_step()
    driver = scripted_driver(url=APP)
    driver.hits = {(10, 10): DEPARTMENT, (90, 90): CANCEL}
    driver.calls_on = {(90, 90): [SAVED]}
    flash = FakeVisionDriver(
        ProposedGesture(ActionKind.TYPE, x=10, y=10, value="GT2"),
        ProposedGesture(ActionKind.CLICK, x=90, y=90),
    )

    result = await SightLane(driver, flash, None).execute(
        step, {"Customer Type": "GT2"}, lane_context(by_id)
    )

    assert result.verdict == "done" and dict(result.learned) == {}


async def test_a_typed_step_learns_the_field_that_holds_the_value_not_the_blur_click() -> None:
    step, by_id = type_step()
    driver = scripted_driver(url=APP, holds=True)
    driver.hits = {(10, 10): DEPARTMENT, (90, 90): CANCEL}
    flash = FakeVisionDriver(
        ProposedGesture(ActionKind.TYPE, x=10, y=10, value="GT2"),
        ProposedGesture(ActionKind.CLICK, x=90, y=90),
        ProposedGesture(ActionKind.HOVER, done=True),
    )

    result = await SightLane(driver, flash, None).execute(
        step, {"Customer Type": "GT2"}, lane_context(by_id)
    )

    assert result.verdict == "done"
    assert dict(result.learned) == {
        "strategy": "role_and_name",
        "query": "textbox|Customer Type",
        "frame_path": "[]",
    }
    [asked] = driver.waited_for
    assert asked["pin"] == "p-ct" and asked["expect"] == {
        "value": "GT2",
        "visible": None,
        "enabled": None,
    }
    assert asked["target"]["name"] == "Customer Type"
    assert asked.get("write") is not False and asked["learned"] is None


async def test_an_autosave_before_the_first_point_is_never_the_writes_call() -> None:
    driver = scripted_driver(url=APP, hit=HIT)
    step, by_id = save_step(status=201)

    class Autosaves(FakeVisionDriver):
        async def propose(self, **kwargs: Any) -> ProposedGesture:
            if not self.asked:
                driver.arrive(SAVED)
            return await super().propose(**kwargs)

    flash = Autosaves(
        ProposedGesture(ActionKind.CLICK, x=400, y=20),
        ProposedGesture(ActionKind.HOVER, done=True),
    )

    result = await SightLane(driver, flash, None).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"
    assert driver.pointed == [("click", 400, 20, None)]


PINNED = {**HIT, "pin": "p-1"}


@pytest.mark.parametrize(
    ("holds", "verdict"), [(True, "done"), (False, "unknown")], ids=["holds", "does_not"]
)
async def test_a_step_without_a_call_is_done_only_when_the_recorded_control_holds(
    holds: bool, verdict: str
) -> None:
    step, by_id = type_step(after=AfterState(value="GT1", visible=True, enabled=True))
    driver = scripted_driver(url=APP, hit=PINNED, holds=holds)
    flash = FakeVisionDriver(
        ProposedGesture(ActionKind.TYPE, x=5, y=5, value="NEW"),
        ProposedGesture(ActionKind.HOVER, done=True),
    )

    result = await SightLane(driver, flash, None).execute(
        step, {"Customer Type": "NEW"}, lane_context(by_id)
    )

    assert result.verdict == verdict
    [asked] = driver.waited_for
    assert asked["pin"] == "p-1" and asked["expect"]["value"] == "NEW"
    assert "Afterwards the control should show 'NEW'" in str(flash.asked[0]["goal"])


async def test_a_click_that_records_only_visible_and_enabled_still_needs_the_recorded_control() -> (
    None
):
    step, by_id = read_step(after=AfterState(visible=True, enabled=True), role="button")
    driver = scripted_driver(url=APP, hit=PINNED, holds=False)

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "unknown"
    [asked] = driver.waited_for
    assert asked["pin"] == "p-1" and asked["target"]["name"] == "Orders"


async def test_a_hit_without_a_pin_is_never_checked_and_never_done() -> None:
    step, by_id = type_step()
    driver = scripted_driver(url=APP, hit=HIT, holds=True)
    flash = FakeVisionDriver(
        ProposedGesture(ActionKind.TYPE, x=5, y=5, value="GT2"),
        ProposedGesture(ActionKind.HOVER, done=True),
    )

    result = await SightLane(driver, flash, None).execute(
        step, {"Customer Type": "GT2"}, lane_context(by_id)
    )

    assert result.verdict == "unknown" and driver.waited_for == []


def open_order_step() -> tuple[Step, dict[str, Gesture]]:
    step, by_id = read_step()
    [gesture] = by_id.values()
    opened = replace(
        gesture,
        url="https://wms.example/orders",
        requests=[],
        page_events=[PageMark(at=1.2, page_kind="navigated", url="https://wms.example/orders/999")],
    )
    return replace(step, parameters=["Order"]), {opened.id: opened}


@pytest.mark.parametrize(
    ("start", "lands", "values", "verdict"),
    [
        ("https://wms.example/orders", "https://wms.example/orders/123", {"Order": "123"}, "done"),
        (
            "https://wms.example/orders",
            "https://wms.example/orders/456",
            {"Order": "123"},
            "unknown",
        ),
        (
            "https://wms.example/orders",
            "https://wms.example/orders/999",
            {"Order": "123"},
            "unknown",
        ),
        ("https://wms.example/orders", "https://wms.example/orders/999", {}, "done"),
        ("https://wms.example/orders/5", "https://wms.example/orders/5", {"Order": "5"}, "unknown"),
    ],
    ids=[
        "its_record",
        "wrong_record",
        "the_recorded_record_not_this_runs",
        "constant",
        "already_there",
    ],
)
async def test_a_navigation_is_done_only_on_the_recorded_next_page_with_its_ids_confirmed(
    start: str, lands: str, values: dict[str, str], verdict: str
) -> None:
    step, by_id = open_order_step()
    driver = scripted_driver(url=start, hit=PINNED, holds=True)
    driver.lands = lands

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, values, lane_context(by_id)
    )

    assert result.verdict == verdict


async def test_waiting_waits_on_the_page_settling_not_on_the_cap() -> None:
    step, by_id = read_step()
    flash = FakeVisionDriver(*[ProposedGesture(ActionKind.HOVER, wait=True)] * K_SIGHT_ACTIONS)
    pro = FakeVisionDriver(ProposedGesture(ActionKind.HOVER, refusal="no"))
    driver = scripted_driver(url=APP, unsettled=True)

    result = await SightLane(driver, flash, pro).execute(step, {}, lane_context(by_id))

    assert (len(flash.asked), len(pro.asked)) == (1, 1)
    assert result.verdict == "failed"


async def test_the_reason_is_never_a_refusal_the_next_model_acted_past() -> None:
    step, by_id = save_step(status=201)
    flash = FakeVisionDriver(ProposedGesture(ActionKind.HOVER, refusal="cannot see it"))
    driver = scripted_driver(url=APP, hit=HIT)

    result = await SightLane(driver, flash, clicks_then_done()).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "unknown" and "cannot see it" not in result.reason


async def test_sight_escalates_once_and_then_gives_up() -> None:
    flash = FakeVisionDriver(ProposedGesture(ActionKind.HOVER, refusal="cannot see it"))
    pro = FakeVisionDriver(ProposedGesture(ActionKind.HOVER, refusal="nor can I"))
    step, by_id = save_step(status=201)

    result = await SightLane(scripted_driver(url=APP), flash, pro).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "failed" and result.never_left
    assert (len(flash.asked), len(pro.asked)) == (1, 1)


async def test_each_model_acts_at_most_the_cap() -> None:
    step, by_id = read_step()
    again = [ProposedGesture(ActionKind.SCROLL, x=5, y=5)] * (K_SIGHT_ACTIONS + 3)
    flash, pro = FakeVisionDriver(*again), FakeVisionDriver(*again)
    driver = scripted_driver(url=APP)

    await SightLane(driver, flash, pro).execute(step, {}, lane_context(by_id))

    assert (len(flash.asked), len(pro.asked)) == (K_SIGHT_ACTIONS, K_SIGHT_ACTIONS)
    assert len(driver.pointed) == 2 * K_SIGHT_ACTIONS


async def test_sight_never_acts_off_the_system() -> None:
    flash = FakeVisionDriver(ProposedGesture(ActionKind.CLICK, x=1, y=1))
    step, by_id = save_step(status=201)
    driver = scripted_driver(url="https://evil.example/")

    result = await SightLane(driver, flash, None).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and driver.pointed == [] and flash.asked == []


async def test_a_step_that_needs_a_secret_is_refused() -> None:
    step, saved = save_step(status=201)
    by_id = {
        key: replace(one, action=replace(one.action, secret=True)) for key, one in saved.items()
    }
    flash = FakeVisionDriver(ProposedGesture(ActionKind.TYPE, x=1, y=1, value="hunter2"))
    driver = scripted_driver(url=APP)

    result = await SightLane(driver, flash, None).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and driver.pointed == [] and flash.asked == []


FIELD = {"target": {"role": "combobox", "name": "Department"}, "expect": {"value": "Finance"}}
SELECT_HIT = {"strategy": "xpath", "query": "/html/body/select[1]", "frame_path": [], "pin": "h1"}


def types_then_done() -> FakeVisionDriver:
    return FakeVisionDriver(
        ProposedGesture(ActionKind.TYPE, x=40, y=60, value="Finance"),
        ProposedGesture(ActionKind.HOVER, done=True),
    )


@pytest.mark.parametrize(("holds", "verdict"), [(True, "done"), (False, "unknown")])
async def test_a_field_sight_fills_is_done_only_when_the_labelled_control_holds_it(
    holds: bool, verdict: str
) -> None:
    driver = scripted_driver(url=APP, hit=SELECT_HIT, holds=holds)
    write, by_id = save_step(status=201)
    written: list[int] = []

    async def wrote() -> None:
        written.append(write.order)

    result = await SightLane(driver, types_then_done(), None).fill(
        "Set Department to Finance", write, lane_context(by_id, about_to_write=wrote), FIELD
    )

    assert result.verdict == verdict
    assert driver.waited_for[-1] == {**FIELD, "pin": "h1"}
    assert written == []
    assert bool(result.learned) is holds


async def test_a_fill_that_sends_the_save_stops_and_is_never_done() -> None:
    driver = scripted_driver(url=APP, hit=SELECT_HIT, holds=True, calls=[SAVED])
    write, by_id = save_step(status=201)
    model = FakeVisionDriver(
        ProposedGesture(ActionKind.CLICK, x=400, y=20),
        ProposedGesture(ActionKind.TYPE, x=40, y=60, value="Finance"),
    )

    result = await SightLane(driver, model, None).fill(
        "Set Department to Finance", write, lane_context(by_id), FIELD
    )

    assert result.verdict == "unknown"
    assert len(driver.pointed) == 1


async def test_a_fill_whose_point_breaks_is_unknown_because_the_write_may_have_gone() -> None:
    driver = scripted_driver(url=APP, hit=SELECT_HIT, holds=True)
    driver.point = _Breaks(PageGone("the page navigated away"))  # type: ignore[method-assign]
    write, by_id = save_step(status=201)

    result = await SightLane(driver, types_then_done(), None).fill(
        "Set Department to Finance", write, lane_context(by_id), FIELD
    )

    assert result.verdict == "unknown"
    assert "the write may have gone" in result.reason


async def test_a_fill_waits_on_its_last_point_for_the_write_before_it_is_done() -> None:
    driver = scripted_driver(url=APP, hit=SELECT_HIT, holds=True)
    shown = driver.wait_for_call

    async def late(*args: Any, **kwargs: Any) -> bool:
        driver.arrive(SAVED)
        return await shown(*args, **kwargs)

    driver.wait_for_call = late  # type: ignore[method-assign]
    write, by_id = save_step(status=201)

    result = await SightLane(driver, types_then_done(), None).fill(
        "Set Department to Finance", write, lane_context(by_id), FIELD
    )

    assert result.verdict == "unknown"
