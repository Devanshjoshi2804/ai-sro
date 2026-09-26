import asyncio

import pytest

from sro.application.runtime.answer_run import AnswerRun
from sro.application.runtime.step import WaitingForAPerson
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


async def _asked_a_failed_step() -> tuple[SteelRun, str]:
    world = await steel_run(steps=[save_step(status=201), type_step()])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    asked = (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking
    assert asked
    return world, asked


async def _asked_about_a_write_in_doubt() -> tuple[SteelRun, str]:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    await world.mark_sending(0)
    asked = (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking
    assert asked
    return world, asked


async def test_question_ids_cannot_be_guessed_from_the_run_or_its_step() -> None:
    one, first = await _asked_a_failed_step()
    two, second = await _asked_a_failed_step()

    assert first != second
    assert one.run_id not in first and two.run_id not in second


@pytest.mark.parametrize("kind", ["password", "code", "step"])
async def test_only_a_question_for_a_value_takes_one_and_nothing_else_reaches_the_signal(
    kind: str,
) -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await asking_steel_run(uow, kind=kind)

    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(
            CTX, run_id=run.id, question_id=QID, value="use pw Hunter2!"
        )
    await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="")

    assert durable.answered == [(run.id, QID)]
    saved = await uow.workflow_runs.get(TENANT, run.id)
    assert saved is not None
    assert "Hunter2" not in str(saved.progress)


async def test_an_answer_to_another_question_or_to_none_is_refused() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await asking_steel_run(uow, kind="step")

    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id="q-other", value="")
    assert await uow.workflow_runs.record_progress(TENANT, run.id, {})
    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="")

    assert durable.answered == []


async def test_an_answer_to_a_withdrawn_question_is_refused_and_the_step_never_runs_again() -> None:
    world, asked = await _asked_a_failed_step()
    progress = Progress.of((await world.saved_run()).progress)
    progress.settle(0, lane="ui", verdict="done")
    progress.step, progress.asking = 1, {}
    assert await world.uow.workflow_runs.record_progress(TENANT, world.run_id, progress.as_json())

    with pytest.raises(Conflict):
        await world.answer(asked)
    await world.run_steps.answered(CTX, world.run_id, asked)

    assert world.durable.answered == []
    assert Progress.of((await world.saved_run()).progress).as_json() == progress.as_json()
    assert world.lanes.ui.calls == 1


async def test_the_first_answer_wins_and_a_different_second_one_is_refused() -> None:
    world, asked = await _asked_about_a_write_in_doubt()

    await AnswerRun(world.uow, world.durable).execute(
        CTX, run_id=world.run_id, question_id=asked, value="", verdict="done"
    )
    with pytest.raises(Conflict):
        await AnswerRun(world.uow, world.durable).execute(
            CTX, run_id=world.run_id, question_id=asked, value="", verdict="not_done"
        )
    await AnswerRun(world.uow, world.durable).execute(
        CTX, run_id=world.run_id, question_id=asked, value="", verdict="done"
    )
    await world.run_steps.answered(CTX, world.run_id, asked)

    assert world.durable.answered == [(world.run_id, asked), (world.run_id, asked)]
    assert Progress.of((await world.saved_run()).progress).written(0)


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

    await world.answer(asked)
    world.driver.signals_for_every_tab = PageSignals(APP)
    assert await world.run_steps.acquire(CTX, world.run_id) == ""

    resumed = Progress.of((await world.saved_run()).progress)
    assert (resumed.lease, resumed.tabs) == (waiting.lease, waiting.tabs)
    assert world.uow.browser_sessions.leases[resumed.lease].state is LeaseState.READY


async def test_a_run_that_ends_while_a_code_is_asked_ends_its_park_and_closes_its_page() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.vault.store(world.account.vault_key("password"), "pw")
    await world.run_steps.prepare(CTX, world.run_id)
    world.driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))
    await world.run_steps.acquire(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)
    waiting = Progress.of((await world.saved_run()).progress)

    await world.run_steps.finish(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)

    lease = world.uow.browser_sessions.leases[waiting.lease]
    assert lease.expires_at <= world.clock.now()
    assert waiting.tabs[MAIN] not in world.driver.tabs


async def _parked_on_a_password(world: SteelRun) -> str:
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
    return parked


async def test_a_stored_password_ends_the_park_at_once_and_the_run_signs_in_afresh() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    parked = await _parked_on_a_password(world)
    await world.run_steps.release(CTX, world.run_id)
    assert world.uow.browser_sessions.leases[parked].expires_at > world.clock.now()

    await world.answer(QID)

    assert await world.run_steps.acquire(CTX, world.run_id) == ""
    fresh = Progress.of((await world.saved_run()).progress).lease
    assert fresh != parked
    assert world.uow.browser_sessions.leases[parked].state is LeaseState.EXPIRED


async def test_a_run_that_ends_while_a_password_is_asked_ends_its_park() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    parked = await _parked_on_a_password(world)

    await world.run_steps.finish(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)

    assert world.uow.browser_sessions.leases[parked].expires_at <= world.clock.now()


async def test_a_finished_steel_run_waits_on_its_mail_thread_no_longer() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    run = await world.saved_run()
    run.awaiting = as_said(waiting_on("gmail", "t-9", now=NOW))
    await world.uow.workflow_runs.save(run)

    await world.run_steps.finish(CTX, world.run_id)

    assert (await world.saved_run()).awaiting is None


async def test_an_operator_who_says_the_write_was_done_settles_it_and_nothing_sends_it_again() -> (
    None
):
    world, asked = await _asked_about_a_write_in_doubt()

    await world.answer(asked, verdict="done")
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

    await world.answer(asked, verdict="not_done")
    said = (await world.saved_run()).steps[-1]
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert (said.verdict, said.verdict_by) == ("failed", "operator")
    assert world.lanes.ui.calls == 1
    assert Progress.of((await world.saved_run()).progress).step == 1


async def test_an_answer_about_a_write_in_doubt_that_says_nothing_of_it_is_refused() -> None:
    world, asked = await _asked_about_a_write_in_doubt()

    with pytest.raises(Conflict):
        await world.answer(asked)

    assert world.durable.answered == []
    assert Progress.of((await world.saved_run()).progress).asking["id"] == asked


async def test_a_password_answer_never_ends_a_park_on_a_one_time_code() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.vault.store(world.account.vault_key("password"), "pw")
    await world.run_steps.prepare(CTX, world.run_id)
    world.driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))
    await world.run_steps.acquire(CTX, world.run_id)
    lease = Progress.of((await world.saved_run()).progress).lease
    parked = world.uow.browser_sessions.leases[lease]
    await world.asks({"id": QID, "kind": "password", "text": "store a new one"})

    await world.answer(QID)

    assert world.uow.browser_sessions.leases[lease] == parked
    assert parked.waits_for == "code"


async def test_a_value_answer_s_text_is_never_kept_on_the_run() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.asks({"id": QID, "kind": "value", "text": "which type?"})

    await AnswerRun(world.uow, world.durable).execute(
        CTX, run_id=world.run_id, question_id=QID, value="GU9, pw Hunter2!"
    )
    kept = await world.saved_run()
    await world.run_steps.finish(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)

    assert "Hunter2" not in str(kept.progress)
    assert "Hunter2" not in str(await world.saved_run())


async def test_a_code_question_withdrawn_under_the_wait_still_ends_its_park_when_the_run_ends() -> (
    None
):
    world = await steel_run(steps=[save_step(status=201)])
    await world.vault.store(world.account.vault_key("password"), "pw")
    await world.run_steps.prepare(CTX, world.run_id)
    world.driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))
    await world.run_steps.acquire(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)
    waiting = Progress.of((await world.saved_run()).progress)
    await world.asks({})

    await world.run_steps.finish(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)

    assert world.uow.browser_sessions.leases[waiting.lease].state is not LeaseState.WAITING
    assert waiting.tabs[MAIN] not in world.driver.tabs


async def test_a_run_ends_only_its_own_park_never_one_a_sibling_on_its_account_made() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.another_run("run_b")
    await world.vault.store(world.account.vault_key("password"), "pw")
    for run_id in (world.run_id, "run_b"):
        await world.run_steps.prepare(CTX, run_id)
        await world.run_steps.acquire(CTX, run_id)
    mine = Progress.of((await world.saved_run()).progress)
    world.driver.expire_session()
    world.driver.shows_sign_in_until_signed = False
    world.driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))
    held = await world.broker.reattach(CTX, mine.lease, mine.tabs[MAIN], holder=world.run_id)
    with pytest.raises(WaitingForAPerson):
        await world.broker.reauth(CTX, held, APP)
    await world.run_steps.beat(CTX, "run_b")

    await world.run_steps.finish(CTX, "run_b")
    await world.run_steps.release(CTX, "run_b")
    after_b = world.uow.browser_sessions.leases[mine.lease]
    await world.run_steps.finish(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)

    assert (after_b.state, after_b.holder) == (LeaseState.WAITING, world.run_id)
    assert world.uow.browser_sessions.leases[mine.lease].state is not LeaseState.WAITING
    assert mine.tabs[MAIN] not in world.driver.tabs
