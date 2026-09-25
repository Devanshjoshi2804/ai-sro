from dataclasses import replace

import pytest

from sro.application.ports.vision import ProposedGesture
from sro.application.runtime.sight_lane import SightLane
from sro.domain.execution.lanes import K_SIGHT_ACTIONS, SeenCall
from sro.domain.recording.events import ActionKind
from tests.unit.fakes import FakeVisionDriver
from tests.unit.runtime_support import lane_context, read_step, save_step, scripted_driver

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
    [
        None,
        {
            "strategy": None,
            "query": None,
            "unreachable": "cross_origin_frame",
            "frame_path": [{"index": 0, "url": "https://widgets.example/"}],
            "x": 3,
            "y": 4,
        },
        {"strategy": "component", "query": "#saveButton"},
    ],
    ids=["nothing", "cross_origin_frame", "no_frame_path"],
)
async def test_a_hit_without_a_reachable_frame_teaches_nothing(
    hit: dict[str, object] | None,
) -> None:
    driver = scripted_driver(url=APP, hit=hit, calls=[SAVED])
    step, by_id = save_step(status=201)

    result = await SightLane(driver, clicks_then_done(), None).execute(
        step, {}, lane_context(by_id)
    )

    assert result.verdict == "done" and dict(result.learned) == {}


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
