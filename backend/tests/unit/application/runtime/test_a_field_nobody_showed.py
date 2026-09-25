from collections.abc import Mapping

import pytest

from sro.application.ports.page import PageAnswer
from sro.application.runtime.fill_field import FillField
from sro.application.runtime.step import LaneContext
from sro.domain.execution.compose import Composed
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.skill.workflow import Step
from tests.unit.runtime_support import lane_context, save_step, scripted_driver

DEPARTMENT_OUTLINE = {
    "fields": [{"role": "combobox", "label": "Department", "options": ["Finance", "Operations"]}]
}


class RecordingSight:
    def __init__(self, result: StepResult) -> None:
        self.result = result
        self.said: list[str] = []
        self.checked: list[Mapping[str, object]] = []

    async def fill(
        self, says: str, write: Step, ctx: LaneContext, check: Mapping[str, object]
    ) -> StepResult:
        self.said.append(says)
        self.checked.append(check)
        return self.result


def _field(write_order: int) -> Composed:
    return Composed("department", "Department", "combobox", write_order, ("Finance", "Operations"))


async def test_a_field_found_once_by_its_label_is_selected_and_holds() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        answer=PageAnswer(ok=True, matched_by="within_role_name", pin="p1"),
        outline=DEPARTMENT_OUTLINE,
        holds=True,
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "Operations", write, lane_context(by_id)
    )

    assert (filled.lane, filled.asks) == (Lane.UI, "")
    assert dict(filled.learned) == {"strategy": "role_and_name", "query": "combobox|Department"}
    acted = driver.acted[-1][2]
    assert (acted["action"], acted["value"], acted["write"]) == ("select", "Operations", False)
    assert acted["target"] == {"role": "combobox", "name": "Department", "landmarks": []}
    assert driver.waited_for[-1]["expect"] == {"value": "Operations"}


@pytest.mark.parametrize(
    ("found", "asks"),
    [
        (PageAnswer(ok=False), "no_field"),
        (PageAnswer(ok=True, candidates=2, matched_by="within_role_name"), "ambiguous"),
        (PageAnswer(ok=False, error_kind="frame_ambiguous"), "ambiguous"),
    ],
)
async def test_a_label_missing_or_twice_on_the_live_page_is_asked(
    found: PageAnswer, asks: str
) -> None:
    driver = scripted_driver(resolved=found)
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "Finance", write, lane_context(by_id)
    )

    assert filled.asks == asks
    assert driver.acted == []


async def test_a_guessed_repair_is_never_the_labelled_control() -> None:
    driver = scripted_driver(resolved=PageAnswer(ok=True, candidates=1, matched_by="repair"))
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "Finance", write, lane_context(by_id)
    )

    assert filled.asks == "no_field"
    assert driver.acted == []


async def test_a_dropdown_without_the_option_is_asked_with_the_options_it_has() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        outline=DEPARTMENT_OUTLINE,
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "Legal", write, lane_context(by_id)
    )

    assert (filled.asks, filled.options) == ("no_option", ("Finance", "Operations"))
    assert driver.acted == []


@pytest.mark.parametrize(
    ("answer", "holds"),
    [
        (PageAnswer(ok=False, error_kind="not_actionable"), True),
        (PageAnswer(ok=True, matched_by="within_role_name", pin="p1"), False),
    ],
)
async def test_a_control_that_will_not_take_the_value_falls_back_to_sight(
    answer: PageAnswer, holds: bool
) -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        answer=answer,
        outline={"fields": []},
        holds=holds,
    )
    taught: Mapping[str, str] = {"strategy": "xpath", "query": "/html/body/select[1]"}
    sight = RecordingSight(StepResult("done", Lane.SIGHT, learned=taught))
    write, by_id = save_step(status=201)

    filling = FillField(driver, sight)
    filled = await filling.fill(_field(write.order), "Finance", write, lane_context(by_id))

    assert (filled.lane, dict(filled.learned)) == (Lane.SIGHT, taught)
    assert sight.said == ["Set Department to Finance"]
    assert sight.checked[-1]["target"] == driver.resolved[-1]["target"]
    assert sight.checked[-1]["expect"] == {"value": "Finance"}


async def test_a_sight_fill_it_cannot_confirm_is_not_a_fill() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        answer=PageAnswer(ok=False, error_kind="not_actionable"),
    )
    sight = RecordingSight(StepResult("unknown", Lane.SIGHT, "only the model says so"))
    write, by_id = save_step(status=201)

    filling = FillField(driver, sight)
    filled = await filling.fill(_field(write.order), "Finance", write, lane_context(by_id))

    assert (filled.lane, filled.asks, filled.detail) == (None, "", "only the model says so")


async def test_a_learned_field_step_is_found_by_its_learned_locator() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="learned"),
        answer=PageAnswer(ok=True, matched_by="learned", pin="p1"),
        holds=True,
    )
    write, by_id = save_step(status=201)
    learned = LearnedStep(write.order - 1, "xpath", "/html/body/select[1]", "sight")

    filled = await FillField(driver, None).fill(
        _field(write.order), "Finance", write, lane_context(by_id), learned=learned
    )

    locator = {"strategy": "xpath", "query": "/html/body/select[1]"}
    assert driver.resolved[-1]["learned"] == locator
    assert (filled.lane, dict(filled.learned)) == (Lane.UI, locator)
