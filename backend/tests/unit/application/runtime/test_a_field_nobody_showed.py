import asyncio
import json
from collections.abc import Mapping
from dataclasses import replace

import pytest

from sro.application.ports.page import PageAnswer
from sro.application.runtime.fill_field import Filled, FillField
from sro.application.runtime.step import LaneContext
from sro.domain.execution.compose import Adding, Composed, with_field
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.progress import Progress
from sro.domain.observation.gesture import Outline, OutlineField
from sro.domain.shared.errors import Conflict
from sro.domain.skill.workflow import Step
from tests.unit.runtime_support import (
    CTX,
    WORKFLOW,
    SteelRun,
    lane_context,
    save_step,
    scripted_driver,
    steel_run,
)

DEPARTMENT = OutlineField("combobox", "Department", None, ("Finance", "Operations"))

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


async def test_a_sight_fill_that_sent_the_write_says_so() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1),
        answer=PageAnswer(ok=False, error_kind="not_actionable"),
        outline={"fields": []},
    )
    sight = RecordingSight(StepResult("unknown", Lane.SIGHT, "the write was sent"))
    write, by_id = save_step(status=201)

    filled = await FillField(driver, sight).fill(
        _field(write.order), "Finance", write, lane_context(by_id)
    )

    assert (filled.lane, filled.sent) == (None, True)


async def test_a_sight_fill_it_cannot_confirm_is_not_a_fill() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        answer=PageAnswer(ok=False, error_kind="not_actionable"),
    )
    sight = RecordingSight(StepResult("failed", Lane.SIGHT, "only the model says so"))
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


async def test_an_option_named_exactly_is_the_one_chosen_though_another_differs_by_case() -> None:
    twice = {"fields": [{"role": "combobox", "label": "Department", "options": ["IT", "It"]}]}
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1, matched_by="within_role_name"),
        answer=PageAnswer(ok=True, matched_by="within_role_name", pin="p1"),
        outline=twice,
        holds=True,
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(
        _field(write.order), "It", write, lane_context(by_id)
    )

    assert filled.lane is Lane.UI
    assert driver.acted[-1][2]["value"] == "It"


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


def test_a_held_value_never_reaches_a_repr() -> None:
    assert "4111" not in repr(PageAnswer(ok=True, held="4111111111111111"))
    assert "4111" not in repr(Filled(Lane.UI, held="4111111111111111"))


async def _started(world: SteelRun) -> None:
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)


async def test_a_value_with_no_field_on_the_form_is_asked_before_any_step_runs() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline())], values={"department": "Finance"}
    )
    await _started(world)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    asking = world.progress().asking
    assert (asking["kind"], asking["name"]) == ("field", "department")
    assert world.lanes.ui.calls == 0


async def test_leaving_the_field_out_drops_the_value_and_names_it_unasked() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline())], values={"department": "Finance"}
    )
    await _started(world)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    await world.answer(outcome.asking, value="")

    run = await world.saved_run()
    assert "department" not in run.values
    assert run.unasked == ["department"]


async def test_a_field_question_takes_only_a_label_it_offered_and_that_label_places_it() -> None:
    dept = OutlineField("combobox", "Dept", None, ("Finance",))
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=(dept,)))],
        values={"department": "Finance"},
    )
    await _started(world)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    said = (await world.thread_says())[-1]["decision"]

    with pytest.raises(Conflict):
        await world.answer(outcome.asking, value="Sales")
    await world.answer(outcome.asking, value="Dept")

    assert isinstance(said, dict) and (said["name"], said["choices"]) == ("department", ["Dept"])
    (field,) = world.progress().composed
    assert (field["name"], field["label"], field["before"]) == ("department", "Dept", 0)
    assert world.progress().asking == {}


async def test_an_option_the_dropdown_lacks_is_asked_and_the_one_chosen_replaces_it() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "Legal"},
    )
    world.fill.answers(Filled(None, "no_option", options=("Finance", "Operations")))
    await _started(world)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    await world.answer(outcome.asking, value="Operations")

    assert world.lanes.ui.calls == 0
    assert (await world.saved_run()).values["department"] == "Operations"


async def test_a_field_the_save_call_carried_is_done_and_learned_into_the_job() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "Finance"},
    )
    world.fill.answers(
        Filled(
            Lane.UI,
            learned={"strategy": "role_and_name", "query": "combobox|Department"},
            held="Finance",
        )
    )
    world.lanes.ui.answers(StepResult("done", Lane.UI, keyed={"department": "department"}))
    await _started(world)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.run_steps.finish(CTX, world.run_id)

    assert world.lanes.ui.contexts[-1].adding[0] == Adding(fresh={"department": "Finance"})
    (field,) = world.progress().composed
    assert (field["lane"], field["verdict"], field["key"]) == ("ui", "done", "department")
    job = await world.job()
    assert job.steps[0].parameters == ["department"]
    assert job.parameters[-1]["body_key"] == "department"
    assert [(one.strategy, one.found_by) for one in await world.learned()] == [
        ("role_and_name", "composed")
    ]
    assert (await world.saved_run()).outcome == "held"


async def test_a_field_the_save_call_did_not_carry_is_unknown_and_not_learned() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "Finance"},
    )
    world.fill.answers(
        Filled(Lane.UI, learned={"strategy": "role_and_name", "query": "combobox|Department"})
    )
    world.lanes.ui.answers(StepResult("done", Lane.UI))
    await _started(world)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.run_steps.finish(CTX, world.run_id)

    (field,) = world.progress().composed
    assert field["verdict"] == "unknown"
    assert [one.parameters for one in (await world.job()).steps] == [[]]
    assert (await world.saved_run()).outcome == "failed"


async def _a_learned_field(values: Mapping[str, str]) -> SteelRun:
    step, by_id = save_step(status=201, outline=Outline(fields=(DEPARTMENT,)))
    job, _ = with_field(
        replace(WORKFLOW, steps=[replace(step, order=0)]),
        Composed("department", "Department", "combobox", 0, DEPARTMENT.options),
        key="department",
        value="Finance",
    )
    world = await steel_run(steps=[(step, by_id)], job=job, values=values)
    await world.uow.workflows.remember_locator(
        job.id, LearnedStep(0, "role_and_name", "combobox|Department", "composed")
    )
    await _started(world)
    return world


async def test_a_learned_field_is_filled_by_its_locator_and_settled_by_its_known_key() -> None:
    world = await _a_learned_field({"department": "Operations"})
    world.fill.answers(Filled(Lane.UI, held="Operations"))
    world.lanes.ui.answers(StepResult("done", Lane.UI, keyed={"department": "department"}))

    for _ in range(2):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    outcome = await world.run_steps.finish(CTX, world.run_id)

    ((field, value, learned),) = world.fill.filled
    assert (field.label, value) == ("Department", "Operations")
    assert learned is not None and learned.query == "combobox|Department"
    assert world.lanes.ui.contexts[-1].adding[1] == Adding(
        known={"department": "department"}, fresh={"department": "Operations"}
    )
    assert world.progress().composed == []
    assert outcome == "held"
    assert len((await world.job()).steps) == 2


async def test_a_learned_field_with_no_value_is_passed_over() -> None:
    world = await _a_learned_field({})
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    for _ in range(2):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.fill.filled == []
    assert dict(world.lanes.ui.contexts[-1].adding) == {}


def test_a_malformed_composed_list_is_refused_like_any_other_progress() -> None:
    with pytest.raises(ValueError, match="composed"):
        Progress.of({"composed": [json.dumps({"name": "x"})]})


async def test_options_equal_but_for_case_are_offered_as_the_options() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "it"},
    )
    world.fill.answers(Filled(None, "ambiguous", options=("IT", "It")))
    await _started(world)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert json.loads(world.progress().asking["choices"]) == ["IT", "It"]
    await world.answer(outcome.asking, value="It")
    assert (await world.saved_run()).values["department"] == "It"


async def test_a_duplicate_label_is_answered_by_the_choice_that_tells_it_apart() -> None:
    fields = (OutlineField("combobox", "Department"), OutlineField("textbox", "Department"))
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=fields))],
        values={"department": "Finance"},
    )
    await _started(world)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    await world.answer(outcome.asking, value="Department (textbox)")

    (field,) = world.progress().composed
    assert (field["label"], field["role"]) == ("Department", "textbox")


async def test_a_save_that_did_not_carry_the_field_says_so_in_its_own_row() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "Finance"},
    )
    world.fill.answers(Filled(Lane.UI, held="Finance"))
    world.lanes.ui.answers(StepResult("done", Lane.UI))
    await _started(world)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    rows = [(one.says, one.verdict) for one in (await world.saved_run()).steps]
    assert ("Fill Department", "unclear") in rows


async def test_a_learned_field_that_cannot_be_filled_may_be_left_out() -> None:
    world = await _a_learned_field({"department": "Operations"})
    world.fill.answers(Filled(None, detail="the control did not take the value"))
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert world.progress().asking["kind"] == "field"
    await world.answer(outcome.asking, value="")
    for _ in range(2):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert "department" not in (await world.saved_run()).values
    assert world.lanes.ui.calls == 1


async def test_a_learned_field_is_filled_again_when_its_save_is_tried_again() -> None:
    world = await _a_learned_field({"department": "Operations"})
    world.fill.answers(Filled(Lane.UI, held="Operations"), Filled(Lane.UI, held="Operations"))
    world.lanes.ui.answers(
        StepResult("failed", Lane.UI, "the page reloaded", never_left=True),
        StepResult("done", Lane.UI, keyed={"department": "department"}),
    )
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, "the page reloaded"))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    asked = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.answer(asked.asking)
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert len(world.fill.filled) == 2
    assert await world.run_steps.finish(CTX, world.run_id) == "held"


async def test_a_learned_field_that_failed_is_tried_again_when_the_operator_chooses_it() -> None:
    world = await _a_learned_field({"department": "Operations"})
    world.fill.answers(
        Filled(None, detail="the control did not take the value"), Filled(Lane.UI, held="x")
    )

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.answer(outcome.asking, value="Department")
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert len(world.fill.filled) == 2
    assert world.progress().composed == []


SENT = Filled(None, detail="the write was sent while filling a field", sent=True)


async def _asked_about_the_write(world: SteelRun) -> str:
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert not outcome.asking
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert world.progress().asking["kind"] == "step"
    return outcome.asking


async def test_a_save_sent_while_filling_a_field_is_asked_about_and_never_sent_again() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "Finance"},
    )
    world.fill.answers(SENT)
    await _started(world)

    asked = await _asked_about_the_write(world)
    await world.answer(asked, verdict="done")
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.lanes.ui.calls == 0
    assert world.lanes.api.read_backs == 1
    assert world.progress().step == 1


async def test_a_save_sent_while_filling_a_learned_field_is_never_sent_again() -> None:
    world = await _a_learned_field({"department": "Operations"})
    world.fill.answers(SENT)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    asked = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.answer(asked.asking, verdict="done")

    assert world.lanes.ui.calls == 0
    assert world.progress().step == 2


async def test_a_save_sent_while_its_learned_field_is_filled_again_is_never_sent_again() -> None:
    world = await _a_learned_field({"department": "Operations"})
    world.fill.answers(Filled(Lane.UI, held="Operations"), SENT)
    world.lanes.ui.answers(StepResult("failed", Lane.UI, "the page reloaded", never_left=True))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, "the page reloaded"))
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    first = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.answer(first.asking)

    asked = await _asked_about_the_write(world)
    await world.answer(asked, verdict="done")

    assert world.lanes.ui.calls == 1
    assert world.progress().step == 2


NOTES = OutlineField("textbox", "Notes")


async def _two_learned_fields() -> SteelRun:
    step, by_id = save_step(status=201, outline=Outline(fields=(DEPARTMENT, NOTES)))
    job, _ = with_field(
        replace(WORKFLOW, steps=[replace(step, order=0)]),
        Composed("department", "Department", "combobox", 0, DEPARTMENT.options),
        key="department",
        value="Finance",
    )
    job, _ = with_field(job, Composed("notes", "Notes", "textbox", 1), key="notes", value="rush")
    world = await steel_run(
        steps=[(step, by_id)], job=job, values={"department": "Operations", "notes": "rush"}
    )
    await _started(world)
    return world


async def test_a_save_one_field_sent_is_never_sent_again_by_the_next_field() -> None:
    world = await _two_learned_fields()
    world.fill.answers(SENT)

    for _ in range(2):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    asked = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert world.progress().asking["kind"] == "step"
    await world.answer(asked.asking, verdict="done")

    assert len(world.fill.filled) == 1
    assert world.lanes.ui.calls == 0
    assert world.lanes.api.read_backs == 1
    assert world.progress().step == 3


async def test_a_retry_after_the_save_was_marked_sent_does_not_fill_again() -> None:
    world = await _a_learned_field({"department": "Operations"})
    await world.mark_sending(1, Lane.SIGHT)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    asked = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.fill.filled == []
    assert world.progress().asking["kind"] == "step"
    assert asked.asking


async def test_a_question_with_no_field_to_choose_only_offers_to_leave_it_out() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline())], values={"department": "Finance"}
    )
    await _started(world)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    text = world.progress().asking["text"]
    assert "choose" not in text and "leave it out" in text
