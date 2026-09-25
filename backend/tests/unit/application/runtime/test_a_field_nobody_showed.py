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
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name", held="ops"),
        answer=PageAnswer(ok=True, matched_by="within_role_name", pin="p1"),
        outline=DEPARTMENT_OUTLINE,
        holds=True,
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "Operations", write, lane_context(by_id)
    )

    assert (filled.lane, filled.asks, filled.held) == (Lane.UI, "", "ops")
    assert len(driver.resolved) == 2
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

    assert (filled.lane, filled.asks, filled.detail) == (None, "", "sight could not set the field")


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


async def test_the_operators_value_is_the_outlines_own_option_label() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        answer=PageAnswer(ok=True, matched_by="within_role_name", pin="p1"),
        outline=DEPARTMENT_OUTLINE,
        holds=True,
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), " operations", write, lane_context(by_id)
    )

    assert filled.lane == Lane.UI
    assert driver.acted[-1][2]["value"] == "Operations"
    assert driver.waited_for[-1]["expect"] == {"value": "Operations"}


async def test_two_options_equal_but_for_case_are_asked_not_picked() -> None:
    twice = {"fields": [{"role": "combobox", "label": "Department", "options": ["IT", "It"]}]}
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        outline=twice,
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "it", write, lane_context(by_id)
    )

    assert (filled.asks, filled.options) == ("ambiguous", ("IT", "It"))
    assert driver.acted == []


@pytest.mark.parametrize("kind", ["frame_ambiguous", "frame_not_found"])
async def test_a_frame_that_cannot_be_chosen_fails_without_a_question(kind: str) -> None:
    driver = scripted_driver(resolved=PageAnswer(ok=False, error_kind=kind))
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "Finance", write, lane_context(by_id)
    )

    assert (filled.lane, filled.asks) == (None, "")
    assert driver.acted == []


async def test_sight_checks_the_labelled_control_never_the_learned_locator() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="learned", held="Finance"),
        answer=PageAnswer(ok=False, error_kind="not_actionable"),
    )
    sight = RecordingSight(
        StepResult("done", Lane.SIGHT, learned={"strategy": "xpath", "query": "/x"})
    )
    write, by_id = save_step(status=201)
    learned = LearnedStep(write.order - 1, "xpath", "/html/body/select[1]", "sight")

    filling = FillField(driver, sight)
    filled = await filling.fill(
        _field(write.order), "Finance", write, lane_context(by_id), learned=learned
    )

    assert sight.checked[-1]["learned"] is None
    assert sight.checked[-1]["target"]["name"] == "Department"
    assert (filled.lane, filled.held) == (Lane.SIGHT, "Finance")


async def test_the_operators_value_never_reaches_the_detail() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        answer=PageAnswer(ok=False, detail="no option Legal-7", error_kind="not_actionable"),
        outline={"fields": []},
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "Legal-7", write, lane_context(by_id)
    )

    assert filled.lane is None and filled.detail
    assert "Legal-7" not in filled.detail
