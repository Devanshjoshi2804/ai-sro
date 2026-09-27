import asyncio
from dataclasses import replace

import pytest

from sro.application.context import RequestContext
from sro.application.runtime.answer_run import AnswerRun
from sro.application.runtime.fill_field import Filled
from sro.application.runtime.step import Superseded
from sro.domain.execution.progress import Progress
from sro.domain.observation.gesture import Outline, OutlineField
from sro.domain.shared.identifiers import PrincipalId
from sro.domain.skill.aliases import JobAlias
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


async def test_the_alias_is_the_answering_operators_not_the_runs() -> None:
    world, asked = await _asked_where_cost_centre_goes()
    lead = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("lead"))

    await AnswerRun(world.uow, world.durable).execute(
        lead, run_id=world.run_id, question_id=asked, value="Department"
    )
    await world.run_steps.answered(CTX, world.run_id, asked)

    (alias,) = await world.uow.workflows.aliases_for(TENANT, (await world.job()).id)
    assert alias.confirmed_by == "lead"


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
    world, asked = await _asked_where_cost_centre_goes()
    await world.answer(asked, value="Department")
    job = await world.job()
    async with world.uow:
        await world.uow.workflows.confirm_alias(
            TENANT, job.id, JobAlias("Cost Centre", "Region", "lead", world.clock.now())
        )

    (alias,) = await world.uow.workflows.aliases_for(TENANT, job.id)
    assert (alias.wording, alias.field) == ("Cost Centre", "Region")


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
