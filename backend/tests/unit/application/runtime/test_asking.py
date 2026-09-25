import asyncio

import pytest

from sro.application.runtime.answer_run import AnswerRun
from sro.domain.execution.account import K_LEASE_TTL, LeaseState
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.progress import MAIN, Progress
from sro.domain.execution.waiting import as_said, waiting_on
from sro.domain.shared.errors import Conflict
from sro.domain.skill.signing_in import PageSignals
from tests.unit.fakes import FakeDurableExecution, FakeUnitOfWork
from tests.unit.runtime_support import (
    APP,
    CTX,
    NOW,
    QID,
    TENANT,
    SteelRun,
    asking_steel_run,
    save_step,
    steel_run,
    type_step,
)


async def test_a_question_is_said_to_the_operator_and_the_run_holds_nothing_while_it_waits() -> (
    None
):
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.run_steps.release(CTX, world.run_id)

    assert outcome.asking
    said = (await world.thread_says())[-1]
    assert said["decision"] == {
        "kind": "run_asks",
        "run_id": world.run_id,
        "question_id": outcome.asking,
        "asks": "step",
    }
    assert world.driver.tabs == {}


async def test_a_password_never_travels_in_an_answer() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await asking_steel_run(uow, kind="password")

    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="hunter2")
    await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="")

    assert durable.answered == [(run.id, QID, "", "")]


async def test_an_answer_to_another_question_is_refused() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await asking_steel_run(uow, kind="step")

    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id="q-other", value="")

    assert durable.answered == []


async def test_an_answer_to_a_withdrawn_question_is_passed_on_bare_and_changes_nothing() -> None:
    world = await steel_run(steps=[save_step(status=201), type_step()])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    asked = (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking
    progress = Progress.of((await world.saved_run()).progress)
    progress.settle(0, lane="ui", verdict="done")
    progress.step, progress.asking = 1, {}
    assert await world.uow.workflow_runs.record_progress(TENANT, world.run_id, progress.as_json())
    durable = FakeDurableExecution()

    await AnswerRun(world.uow, durable).execute(
        CTX, run_id=world.run_id, question_id=asked, value="hunter2"
    )
    await world.run_steps.answered(CTX, world.run_id, asked, "done")

    assert durable.answered == [(world.run_id, asked, "", "")]
    assert Progress.of((await world.saved_run()).progress).as_json() == progress.as_json()
    assert world.lanes.ui.calls == 1


async def test_an_answered_value_is_kept_under_its_name_and_the_question_stops_standing() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.asks({"id": QID, "kind": "value", "name": "Customer Type", "text": "which?"})

    await world.run_steps.answered(CTX, world.run_id, QID, "GT9")

    run = await world.saved_run()
    assert run.values["Customer Type"] == "GT9"
    assert Progress.of(run.progress).asking == {}


async def test_a_one_time_code_keeps_its_lease_and_page_while_waiting_and_resumes_on_them() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.vault.store(world.account.vault_key("password"), "pw")
    await world.run_steps.prepare(CTX, world.run_id)
    world.driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))

    asked = await world.run_steps.acquire(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)

    waiting = Progress.of((await world.saved_run()).progress)
    assert waiting.asking["kind"] == "code"
    assert waiting.tabs[MAIN] in world.driver.tabs
    assert world.uow.browser_sessions.leases[waiting.lease].state is LeaseState.WAITING

    await world.run_steps.answered(CTX, world.run_id, asked, "")
    world.driver.signals_for_every_tab = PageSignals(APP)
    assert await world.run_steps.acquire(CTX, world.run_id) == ""

    resumed = Progress.of((await world.saved_run()).progress)
    assert (resumed.lease, resumed.tabs) == (waiting.lease, waiting.tabs)
    assert world.uow.browser_sessions.leases[resumed.lease].state is LeaseState.READY


async def test_a_stored_password_ends_the_park_at_once_and_the_run_signs_in_afresh() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    parked = Progress.of((await world.saved_run()).progress).lease
    assert await world.uow.browser_sessions.settle(
        TENANT,
        parked,
        state=LeaseState.WAITING,
        until=world.clock.now() + K_LEASE_TTL,
        waits_for="password",
    )
    await world.asks({"id": QID, "kind": "password", "text": "store a new one"})
    await world.run_steps.release(CTX, world.run_id)

    await world.run_steps.answered(CTX, world.run_id, QID, "")

    assert await world.run_steps.acquire(CTX, world.run_id) == ""
    fresh = Progress.of((await world.saved_run()).progress).lease
    assert fresh != parked
    assert world.uow.browser_sessions.leases[parked].state is LeaseState.EXPIRED


async def test_a_finished_steel_run_waits_on_its_mail_thread_no_longer() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    run = await world.saved_run()
    run.awaiting = as_said(waiting_on("gmail", "t-9", now=NOW))
    await world.uow.workflow_runs.save(run)

    await world.run_steps.finish(CTX, world.run_id)

    assert (await world.saved_run()).awaiting is None


async def _asked_about_a_write_in_doubt() -> tuple[SteelRun, str]:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    await world.mark_sending(0)
    asked = (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking
    assert asked
    return world, asked


async def test_an_operator_who_says_the_write_was_done_settles_it_and_nothing_sends_it_again() -> (
    None
):
    world, asked = await _asked_about_a_write_in_doubt()

    await world.run_steps.answered(CTX, world.run_id, asked, "", verdict="done")
    after = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert Progress.of(run.progress).written(0)
    assert Progress.of(run.progress).asking == {}
    assert (run.steps[-1].verdict, run.steps[-1].verdict_by) == ("held", "operator")
    assert after.more is False
    assert (world.lanes.ui.calls, world.lanes.sight.calls) == (0, 0)


async def test_an_operator_who_says_the_write_was_not_done_lets_the_lanes_try_it_again() -> None:
    world, asked = await _asked_about_a_write_in_doubt()
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    await world.run_steps.answered(CTX, world.run_id, asked, "", verdict="not_done")
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.lanes.ui.calls == 1
    assert Progress.of((await world.saved_run()).progress).step == 1


async def test_an_answer_about_a_write_in_doubt_that_says_nothing_of_it_is_refused() -> None:
    world, asked = await _asked_about_a_write_in_doubt()
    durable = FakeDurableExecution()

    with pytest.raises(Conflict):
        await AnswerRun(world.uow, durable).execute(
            CTX, run_id=world.run_id, question_id=asked, value="looks fine"
        )
    await AnswerRun(world.uow, durable).execute(
        CTX, run_id=world.run_id, question_id=asked, value="", verdict="done"
    )

    assert durable.answered == [(world.run_id, asked, "", "done")]


async def test_a_one_time_code_never_travels_in_an_answer() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await asking_steel_run(uow, kind="code")

    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="123456")

    assert durable.answered == []


async def test_a_password_answer_never_ends_a_park_on_a_one_time_code() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.vault.store(world.account.vault_key("password"), "pw")
    await world.run_steps.prepare(CTX, world.run_id)
    world.driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))
    await world.run_steps.acquire(CTX, world.run_id)
    lease = Progress.of((await world.saved_run()).progress).lease
    parked = world.uow.browser_sessions.leases[lease]
    await world.asks({"id": QID, "kind": "password", "text": "store a new one"})

    await world.run_steps.answered(CTX, world.run_id, QID, "")

    assert world.uow.browser_sessions.leases[lease] == parked
    assert parked.waits_for == "code"
