import logging

import pytest

from sro.application.skill.job_facts import job_facts, runnable_jobs
from sro.domain.execution.lanes import Broken, Lane, cites_key
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.skill.workflow import Workflow
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.runtime_support import NOW, TENANT, proven_write_step, save_step


async def test_facts_load_what_the_runtime_loads_and_compile_it() -> None:
    uow = FakeUnitOfWork()
    step, by_id, _ = proven_write_step(read_back=None)
    job = Workflow(id="wfl_f", tenant=TENANT.value, title="Save", narrative="", steps=[step])
    await uow.workflows.save(job)
    await uow.gestures.add_gestures(tuple(by_id.values()))
    await uow.workflows.break_lane(
        TENANT, job.id, Broken(step.order, Lane.UI, "f"), cites=cites_key(step), at=NOW
    )
    await uow.workflows.remember_locator(job.id, LearnedStep(step.order, "text", "Save", "sight"))

    async with uow:
        (facts,) = await job_facts(uow, TENANT, [job])

    assert set(facts.by_id) == set(step.cites)
    assert facts.broken == (Broken(step.order, Lane.UI, "f"),)
    assert facts.learned == {step.order: LearnedStep(step.order, "text", "Save", "sight")}
    assert facts.aliases == ()
    assert facts.compiled.view["job"] == job.id


async def test_only_a_job_that_compiles_is_offered_and_the_rest_say_why_in_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    uow = FakeUnitOfWork()
    step, by_id = save_step()
    runs = Workflow(id="wfl_runs", tenant=TENANT.value, title="Save", narrative="", steps=[step])
    cannot = Workflow(
        id="wfl_cannot",
        tenant=TENANT.value,
        title="Save",
        narrative="",
        steps=[step],
        parameters=[{"name": "Department", "required": True}],
    )
    await uow.gestures.add_gestures(tuple(by_id.values()))

    with caplog.at_level(logging.INFO):
        async with uow:
            got = await runnable_jobs(uow, TENANT, [runs, cannot])

    assert [one.workflow.id for one in got] == ["wfl_runs"]
    assert "wfl_cannot cannot run and is not offered: unbound_parameter" in caplog.text
