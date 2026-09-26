import logging
from dataclasses import replace

import pytest

from sro.application.skill.job_facts import job_facts
from sro.domain.execution.lanes import K_BROKEN_COOL_DOWN, Broken, Lane, cites_key
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry, KnowledgeId
from sro.domain.skill.workflow import Workflow
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.runtime_support import NOW, TENANT, proven_write_step, save_job, save_step


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
        (facts,) = await job_facts(uow, TENANT, [job], now=NOW)

    assert set(facts.by_id) == set(step.cites)
    assert facts.broken == (Broken(step.order, Lane.UI, "f"),)
    assert facts.learned == {step.order: LearnedStep(step.order, "text", "Save", "sight")}
    assert facts.aliases == ()
    assert facts.compiled.view["job"] == job.id


async def test_a_job_that_cannot_run_is_logged_once_per_change_and_not_every_tick(
    caplog: pytest.LogCaptureFixture,
) -> None:
    uow = FakeUnitOfWork()
    step, by_id = save_step()
    await uow.gestures.add_gestures(tuple(by_id.values()))
    cannot = Workflow(
        id="wfl_logged_once",
        tenant=TENANT.value,
        title="Save",
        narrative="",
        steps=[step],
        parameters=[{"name": "Department", "required": True}],
    )
    worse = replace(cannot, steps=[replace(step, cites=["gone"])])

    with caplog.at_level(logging.INFO):
        async with uow:
            for job in (cannot, cannot, worse, worse):
                (facts,) = await job_facts(uow, TENANT, [job], now=NOW)
                assert not facts.compiled.runnable

    said = [one.getMessage() for one in caplog.records if "wfl_logged_once" in one.getMessage()]
    assert said == [
        "acme: wfl_logged_once cannot run: unbound_parameter",
        "acme: wfl_logged_once cannot run: unbound_parameter, no_lane",
    ]


async def test_a_lane_broken_before_its_cool_down_is_not_a_fact_any_more() -> None:
    uow = FakeUnitOfWork()
    step, by_id, _ = proven_write_step(read_back=None)
    job = Workflow(id="wfl_cool", tenant=TENANT.value, title="Save", narrative="", steps=[step])
    await uow.gestures.add_gestures(tuple(by_id.values()))
    broke = Broken(step.order, Lane.UI, "f")
    await uow.workflows.break_lane(TENANT, job.id, broke, cites=cites_key(step), at=NOW)

    async with uow:
        (fresh,) = await job_facts(uow, TENANT, [job], now=NOW)
        (cooled,) = await job_facts(uow, TENANT, [job], now=NOW + K_BROKEN_COOL_DOWN)

    assert fresh.broken == (broke,)
    assert cooled.broken == ()


async def test_a_knowledge_base_limit_reaches_compiled_fields_for_a_page_with_none() -> None:
    uow = FakeUnitOfWork()
    job = await save_job(uow, "wfl_kb_limit")
    await uow.knowledge.add(
        KnowledgeEntry(
            id=KnowledgeId("kn-customerType"),
            tenant_id=TENANT,
            system="blue_yonder",
            kind=EntryKind.FIELD,
            key="customerType",
            title="Customer Type (customerType)",
            body={"labels": ["Customer Type"], "max_length": 4},
            source="catalogue",
            evidence=EvidenceLevel.ASSERTED,
            observed_at=NOW,
        )
    )

    async with uow:
        (facts,) = await job_facts(uow, TENANT, [job], now=NOW)

    fields = {one.name: one for one in facts.compiled.fields}
    assert fields["Customer Type"].limits.max_length == 4
