import asyncio
import json
from dataclasses import replace

import pytest

from sro.application.context import RequestContext
from sro.application.runtime.answer_run import AnswerRun
from sro.application.runtime.fill_field import Filled
from sro.application.runtime.step import Superseded
from sro.domain.execution.progress import Progress
from sro.domain.observation.gesture import Outline, OutlineField
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import PrincipalId
from tests.unit.runtime_support import CTX, TENANT, SteelRun, save_step, steel_run

FIELDS = (
    OutlineField("combobox", "Department", None, ("Finance", "Operations")),
    OutlineField("textbox", "Region"),
)


async def _asked_where_cost_centre_goes() -> tuple[SteelRun, str]:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=FIELDS))],
        values={"cost centre": "Finance"},
    )
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    asking = world.progress().asking
    assert (asking["kind"], asking["name"]) == ("field", "cost centre")
    return world, outcome.asking


async def _again(world: SteelRun, values: dict[str, str]) -> str:
    first = await world.saved_run()
    again = replace(first, id="run_again", values=values, progress={}, steps=[], unasked=[])
    async with world.uow:
        await world.uow.workflow_runs.save(again)
        await world.uow.commit()
    return again.id


async def test_a_label_the_operator_picks_becomes_an_alias_for_that_job() -> None:
    world, asked = await _asked_where_cost_centre_goes()

    await world.answer(asked, value="Department")

    job = await world.job()
    (alias,) = await world.uow.workflows.aliases_for(TENANT, job.id)
    assert (alias.wording, alias.field, alias.confirmed_by) == (
        "cost centre",
        "Department",
        "clerk",
    )


async def test_leaving_the_value_out_teaches_nothing() -> None:
    world, asked = await _asked_where_cost_centre_goes()

    await world.answer(asked, value="")

    assert await world.uow.workflows.aliases_for(TENANT, (await world.job()).id) == ()


async def test_an_option_is_a_value_not_a_field_and_teaches_nothing() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=FIELDS))],
        values={"department": "Legal"},
    )
    world.fill.answers(Filled(None, "no_option", options=("Finance", "Operations")))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    await world.answer(outcome.asking, value="Operations")

    assert await world.uow.workflows.aliases_for(TENANT, (await world.job()).id) == ()


async def test_the_next_run_places_the_wording_without_asking() -> None:
    world, asked = await _asked_where_cost_centre_goes()
    await world.answer(asked, value="Department")
    again = await _again(world, {"cost centre": "Operations"})

    prepared = await world.run_steps.prepare(CTX, again)

    assert prepared.asking == ""
    progress = Progress.of((await world.uow.workflow_runs.get(TENANT, again)).progress)
    assert [(one["name"], one["label"]) for one in progress.composed] == [
        ("cost centre", "Department")
    ]


async def test_a_later_answer_for_the_same_wording_replaces_the_alias() -> None:
    world, first = await _asked_where_cost_centre_goes()
    again = await _again(world, {"cost centre": "North"})
    await world.run_steps.prepare(CTX, again)
    later = (await world.run_steps.step(CTX, again, stop=asyncio.Event())).asking
    assert later

    await world.answer(first, value="Department")
    await AnswerRun(world.uow, world.durable).execute(
        CTX, run_id=again, question_id=later, value="Region"
    )
    await world.run_steps.answered(CTX, again, later)

    (alias,) = await world.uow.workflows.aliases_for(TENANT, (await world.job()).id)
    assert (alias.wording, alias.field) == ("cost centre", "Region")


async def test_an_answer_applied_twice_teaches_once() -> None:
    world, asked = await _asked_where_cost_centre_goes()

    await world.answer(asked, value="Department")
    await world.run_steps.answered(CTX, world.run_id, asked)

    assert len(await world.uow.workflows.aliases_for(TENANT, (await world.job()).id)) == 1


async def test_an_answer_another_attempt_moved_past_teaches_nothing() -> None:
    world, asked = await _asked_where_cost_centre_goes()
    await AnswerRun(world.uow, world.durable).execute(
        CTX, run_id=world.run_id, question_id=asked, value="Department"
    )
    moved = world.uow.workflow_runs.record_progress

    async def lost(*args: object, **kwargs: object) -> bool:
        return False

    world.uow.workflow_runs.record_progress = lost  # type: ignore[method-assign]
    with pytest.raises(Superseded):
        await world.run_steps.answered(CTX, world.run_id, asked)
    world.uow.workflow_runs.record_progress = moved  # type: ignore[method-assign]

    assert await world.uow.workflows.aliases_for(TENANT, (await world.job()).id) == ()


async def test_a_field_the_page_lacked_this_run_teaches_nothing() -> None:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=FIELDS))],
        values={"Region": "North"},
    )
    world.fill.answers(Filled(None, "no_field"))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert "Department" in json.loads(world.progress().asking["choices"])

    await world.answer(outcome.asking, value="Department")

    assert await world.uow.workflows.aliases_for(TENANT, (await world.job()).id) == ()


async def _asked(values: dict[str, str], *fields: OutlineField) -> tuple[SteelRun, str]:
    world = await steel_run(
        steps=[save_step(status=201, outline=Outline(fields=fields))], values=values
    )
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert world.progress().asking["kind"] == "field"
    return world, outcome.asking


async def test_a_wording_that_is_already_a_label_on_the_form_teaches_nothing() -> None:
    two = (OutlineField("combobox", "Department"), OutlineField("textbox", "Department"))
    world, asked = await _asked({"Department": "Finance"}, *two)

    await world.answer(asked, value="Department (textbox)")

    assert world.progress().composed[0]["role"] == "textbox"
    assert await world.uow.workflows.aliases_for(TENANT, (await world.job()).id) == ()


async def test_a_generic_wording_teaches_nothing() -> None:
    world, asked = await _asked({"value": "Finance"}, *FIELDS)

    await world.answer(asked, value="Department")

    assert await world.uow.workflows.aliases_for(TENANT, (await world.job()).id) == ()


async def test_one_of_two_same_labels_is_taught_with_its_role_and_not_asked_again() -> None:
    two = (OutlineField("combobox", "Department"), OutlineField("textbox", "Department"))
    world, asked = await _asked({"cost centre": "CC-9"}, *two)

    await world.answer(asked, value="Department (textbox)")
    again = await _again(world, {"cost centre": "CC-7"})
    await world.run_steps.prepare(CTX, again)

    (alias,) = await world.uow.workflows.aliases_for(TENANT, (await world.job()).id)
    assert (alias.field, alias.role) == ("Department", "textbox")
    progress = Progress.of((await world.uow.workflow_runs.get(TENANT, again)).progress)
    assert [(one["label"], one["role"]) for one in progress.composed] == [("Department", "textbox")]


async def test_a_second_operators_press_on_an_answered_field_is_refused() -> None:
    world, asked = await _asked_where_cost_centre_goes()
    lead = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("lead"))
    press = AnswerRun(world.uow, world.durable).execute
    await press(CTX, run_id=world.run_id, question_id=asked, value="Department")
    await press(CTX, run_id=world.run_id, question_id=asked, value="Department")

    with pytest.raises(Conflict, match="only the operator who started this run"):
        await press(lead, run_id=world.run_id, question_id=asked, value="Department")


async def test_an_answer_whose_unit_of_work_rolls_back_leaves_no_alias() -> None:
    world, asked = await _asked_where_cost_centre_goes()
    await AnswerRun(world.uow, world.durable).execute(
        CTX, run_id=world.run_id, question_id=asked, value="Department"
    )
    world.uow.commit_raises = RuntimeError("the database went away")

    with pytest.raises(RuntimeError):
        await world.run_steps.answered(CTX, world.run_id, asked)
    world.uow.commit_raises = None

    assert await world.uow.workflows.aliases_for(TENANT, (await world.job()).id) == ()
