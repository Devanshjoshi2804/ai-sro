import json
from dataclasses import replace

import pytest

from sro.application.runtime.teach import Teach
from sro.domain.execution.compose import Composed, without_slots
from sro.domain.execution.lanes import Broken, Lane, SeenCall, StepResult, cites_key
from sro.domain.execution.write_plan import learned_slots
from sro.domain.skill.workflow import field_key
from tests.unit.domain.test_a_learned_key_is_a_slot import _job as _learned_job
from tests.unit.fakes import FakeClock, FakeUnitOfWork
from tests.unit.runtime_support import (
    CTX,
    NOW,
    TENANT,
    WORKFLOW,
    proven_write_step,
    save_step,
)

FRAME = json.dumps([{"index": 1, "url": "https://wms.example/frames/form"}])
SIGHTED = {"strategy": "component", "query": "#saveButton", "frame_path": FRAME}
URL = "https://wms.example/api/customer-types"


async def test_a_learned_field_moves_the_write_and_everything_known_about_it() -> None:
    uow = FakeUnitOfWork()
    step, _ = save_step(status=201)
    job = replace(WORKFLOW, steps=[step])
    await uow.workflows.save(job)
    await uow.workflows.break_lane(
        TENANT, job.id, Broken(step.order, Lane.API, "f"), cites=cites_key(step), at=NOW
    )

    await Teach(uow, FakeClock()).learn_field(
        CTX,
        job,
        Composed("department", "Department", "combobox", step.order),
        key="department",
        value="Finance",
        learned={"strategy": "role_and_name", "query": "combobox|Department"},
        lane=Lane.UI,
        run_id="run_1",
    )

    grown = await uow.workflows.get(TENANT, job.id)
    assert [(one.order, one.says) for one in grown.steps] == [
        (1, "Fill Department"),
        (2, "Save the customer type"),
    ]
    moved = {2: cites_key(step)}
    assert await uow.workflows.broken_for(TENANT, job.id, moved, now=NOW) == (
        Broken(2, Lane.API, "f"),
    )
    assert [(one.ord, one.found_by) for one in await uow.workflows.learned_for(job.id)] == [
        (1, "composed")
    ]


async def test_a_field_whose_step_was_lost_is_learned_again_under_its_one_parameter() -> None:
    uow = FakeUnitOfWork()
    step, _ = save_step(status=201)
    was = [{"name": "department", "required": False, "body_key": "department"}]
    job = replace(WORKFLOW, steps=[step], parameters=was)
    await uow.workflows.save(job)
    field = Composed("department", "Department", "combobox", step.order)
    teach = Teach(uow, FakeClock())

    for _ in range(2):
        await teach.learn_field(
            CTX,
            job,
            field,
            key="department",
            value="Finance",
            learned={},
            lane=Lane.UI,
            run_id="run_1",
        )

    grown = await uow.workflows.get(TENANT, job.id)
    assert [one.says for one in grown.steps] == ["Fill Department", step.says]
    assert [one["name"] for one in grown.parameters] == ["department"]


async def test_a_sight_success_is_learned_into_the_ui_lane() -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id = save_step(status=201)
    await uow.workflows.break_lane(
        TENANT, WORKFLOW.id, Broken(step.order, Lane.UI, "f"), cites=cites_key(step), at=NOW
    )
    tried = (
        StepResult("failed", Lane.UI, fingerprint="f"),
        StepResult("done", Lane.SIGHT, learned=SIGHTED),
    )

    await Teach(uow, FakeClock()).learn(
        CTX, WORKFLOW, by_id, step, tried, run_id="run_1", values={}
    )

    learned = await uow.workflows.learned_for(WORKFLOW.id)
    assert [(one.strategy, one.query, one.found_by, one.frame_path) for one in learned] == [
        ("component", "#saveButton", "sight", FRAME)
    ]
    assert (
        await uow.workflows.broken_for(TENANT, WORKFLOW.id, {step.order: cites_key(step)}, now=NOW)
        == ()
    )


async def test_a_sight_hit_without_its_frame_path_teaches_no_locator() -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id = save_step(status=201)
    tried = (
        StepResult("done", Lane.SIGHT, learned={"strategy": "component", "query": "#saveButton"}),
    )

    await Teach(uow, FakeClock()).learn(
        CTX, WORKFLOW, by_id, step, tried, run_id="run_1", values={}
    )

    assert await uow.workflows.learned_for(WORKFLOW.id) == ()


async def test_a_failed_lane_joins_the_known_broken_list_but_a_session_problem_does_not() -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id = save_step(status=201)
    tried = (
        StepResult("failed", Lane.API, "missing_header", expired=True),
        StepResult("failed", Lane.UI, fingerprint="ui_gone", expired=True),
        StepResult("failed", Lane.SIGHT, fingerprint="sight_refused"),
    )

    await Teach(uow, FakeClock()).learn(
        CTX, WORKFLOW, by_id, step, tried, run_id="run_1", values={}
    )

    assert await uow.workflows.broken_for(
        TENANT, WORKFLOW.id, {step.order: cites_key(step)}, now=NOW
    ) == (Broken(step.order, Lane.SIGHT, "sight_refused"),)


async def test_an_unknown_outcome_mends_nothing() -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id = save_step(status=201)
    await uow.workflows.break_lane(
        TENANT, WORKFLOW.id, Broken(step.order, Lane.UI, "f"), cites=cites_key(step), at=NOW
    )

    await Teach(uow, FakeClock()).learn(
        CTX,
        WORKFLOW,
        by_id,
        step,
        (StepResult("unknown", Lane.UI, calls=(SeenCall("POST", URL, 201),)),),
        run_id="run_1",
        values={},
    )

    assert await uow.workflows.broken_for(
        TENANT, WORKFLOW.id, {step.order: cites_key(step)}, now=NOW
    ) == (Broken(step.order, Lane.UI, "f"),)


async def test_a_promotion_never_mends_an_api_lane_broken_before() -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id, _ = proven_write_step(read_back="/api/customer-types/{name}")
    await uow.workflows.break_lane(
        TENANT, WORKFLOW.id, Broken(step.order, Lane.API, "a"), cites=cites_key(step), at=NOW
    )
    call = SeenCall("POST", URL, 201, request_body='{"name": "GT2"}')

    await Teach(uow, FakeClock()).learn(
        CTX,
        WORKFLOW,
        by_id,
        step,
        (StepResult("done", Lane.UI, calls=(call,)),),
        run_id="run_1",
        values={"Customer Type": "GT2"},
    )

    ledger = await uow.workflows.learned_writes(TENANT)
    assert ("POST", "/api/customer-types") in {(one.method, one.path_pattern) for one in ledger}
    # A lane is cleared only by its own success: a promotion that mended the
    # API lane would send the rejected write again on the next run (X9 re-review).
    assert await uow.workflows.broken_for(
        TENANT, WORKFLOW.id, {step.order: cites_key(step)}, now=NOW
    ) == (Broken(step.order, Lane.API, "a"),)


async def test_a_ui_write_with_no_read_back_is_not_promoted() -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id, _ = proven_write_step(read_back=None)
    call = SeenCall("POST", URL, 201, request_body='{"name": "GT2"}')

    await Teach(uow, FakeClock()).learn(
        CTX,
        WORKFLOW,
        by_id,
        step,
        (StepResult("done", Lane.UI, calls=(call,)),),
        run_id="run_1",
        values={},
    )

    assert await uow.workflows.learned_writes(TENANT) == ()


@pytest.mark.parametrize(
    "call",
    [
        SeenCall("POST", URL, 201),
        SeenCall("POST", URL, 201, request_body='{"name": "GT2", "validateOnly": true}'),
        SeenCall("POST", URL, 201, request_body='{"name": "GT2"}', own_frame=False),
        SeenCall(
            "POST",
            "https://other.example/api/customer-types",
            201,
            request_body='{"name": "GT2"}',
        ),
    ],
    ids=["no_body", "a_key_nobody_filled", "another_frame", "another_host"],
)
async def test_a_call_that_is_not_the_writes_own_never_promotes(call: SeenCall) -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id, _ = proven_write_step(read_back="/api/customer-types/{name}")

    await Teach(uow, FakeClock()).learn(
        CTX,
        WORKFLOW,
        by_id,
        step,
        (StepResult("done", Lane.UI, calls=(call,)),),
        run_id="run_1",
        values={"Customer Type": "GT2"},
    )

    assert await uow.workflows.learned_writes(TENANT) == ()


async def test_a_promotion_never_clears_an_api_lane_that_failed_this_run() -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id, _ = proven_write_step(read_back="/api/customer-types/{name}")
    call = SeenCall("POST", URL, 201, request_body='{"name": "GT2"}')
    tried = (
        StepResult("failed", Lane.API, "the system answered 422", fingerprint="api422"),
        StepResult("done", Lane.UI, calls=(call,)),
    )

    await Teach(uow, FakeClock()).learn(
        CTX, WORKFLOW, by_id, step, tried, run_id="run_1", values={"Customer Type": "GT2"}
    )

    assert await uow.workflows.broken_for(
        TENANT, WORKFLOW.id, {step.order: cites_key(step)}, now=NOW
    ) == (Broken(step.order, Lane.API, "api422"),)


@pytest.mark.parametrize(
    "query",
    ["textbox|Customer gt2 notes", "#" + "x" * 81],
    ids=["holds_a_value_filled_this_run", "longer_than_a_name"],
)
async def test_a_locator_that_carries_a_run_value_or_runs_long_is_never_taught(
    query: str,
) -> None:
    uow = FakeUnitOfWork()
    await uow.workflows.save(WORKFLOW)
    step, by_id = save_step(status=201)
    sighted = {**SIGHTED, "strategy": "role_and_name", "query": query}

    await Teach(uow, FakeClock()).learn(
        CTX,
        WORKFLOW,
        by_id,
        step,
        (StepResult("done", Lane.SIGHT, learned=sighted),),
        run_id="run_1",
        values={"Customer Type": "GT2"},
    )

    assert await uow.workflows.learned_for(WORKFLOW.id) == ()


async def test_an_api_break_takes_the_learned_slot_out_of_the_write() -> None:
    uow = FakeUnitOfWork()
    job, write, by_id, _ = _learned_job("department")
    await uow.workflows.save(job)

    await Teach(uow, FakeClock()).learn(
        CTX,
        job,
        by_id,
        write,
        (StepResult("failed", Lane.API, "rejected", fingerprint="f"),),
        run_id="run_1",
        values={},
    )

    saved = await uow.workflows.get(TENANT, job.id)
    assert learned_slots(saved, write) == {}
    assert field_key(saved, saved.steps[0]) == "department", "it is still a learned field"


async def test_an_expired_api_failure_keeps_the_slot() -> None:
    uow = FakeUnitOfWork()
    job, write, by_id, _ = _learned_job("department")
    await uow.workflows.save(job)

    await Teach(uow, FakeClock()).learn(
        CTX,
        job,
        by_id,
        write,
        (StepResult("failed", Lane.API, "signed out", fingerprint="f", expired=True),),
        run_id="run_1",
        values={},
    )

    saved = await uow.workflows.get(TENANT, job.id)
    assert learned_slots(saved, write) == {"Department": "department"}


async def test_a_keyed_ui_write_puts_the_slot_back() -> None:
    uow = FakeUnitOfWork()
    job, write, by_id, _ = _learned_job("department")
    bare = without_slots(job, ["Department"])
    assert bare is not None
    await uow.workflows.save(bare)

    await Teach(uow, FakeClock()).learn(
        CTX,
        bare,
        by_id,
        write,
        (StepResult("done", Lane.UI, keyed={"Department": "department"}),),
        run_id="run_1",
        values={},
    )

    saved = await uow.workflows.get(TENANT, job.id)
    assert learned_slots(saved, write) == {"Department": "department"}


async def test_a_ui_write_that_did_not_key_the_field_leaves_the_slot_out() -> None:
    uow = FakeUnitOfWork()
    job, write, by_id, _ = _learned_job("department")
    bare = without_slots(job, ["Department"])
    assert bare is not None
    await uow.workflows.save(bare)

    await Teach(uow, FakeClock()).learn(
        CTX, bare, by_id, write, (StepResult("done", Lane.UI),), run_id="run_1", values={}
    )

    saved = await uow.workflows.get(TENANT, job.id)
    assert learned_slots(saved, write) == {}
