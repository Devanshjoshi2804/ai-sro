import asyncio

import pytest

from sro.application.ports.locks import AccountBusy
from sro.domain.execution.account import LeaseState
from sro.domain.execution.lanes import Broken, Lane, StepResult, cites_key
from sro.domain.execution.progress import MAIN, Progress, StepMark
from tests.unit.runtime_support import (
    CTX,
    TENANT,
    mail_send_step,
    save_step,
    steel_run,
    type_step,
)


async def test_a_run_advances_one_step_per_call_and_says_when_it_is_done() -> None:
    world = await steel_run(steps=[type_step(), save_step(status=201)])
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))

    first = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    second = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert (first.more, second.more) == (True, False)
    run = await world.saved_run()
    assert [one.verdict for one in run.steps] == ["held", "held"]
    assert [one.verdict_by for one in run.steps] == ["ui", "ui"]
    assert Progress.of(run.progress).step == 2


async def test_a_mail_only_job_takes_no_browser() -> None:
    world = await steel_run(steps=[mail_send_step()])

    prepared = await world.run_steps.prepare(CTX, world.run_id)

    assert prepared.browser is False


async def test_a_write_is_marked_before_it_is_sent() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write())
    world.lanes.ui.answers(StepResult("done", Lane.UI))
    seen: list[str] = []
    world.uow.workflow_runs.on_save = lambda run: seen.append(
        Progress.of(run.progress).marks.get(0, StepMark()).wrote
    )

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert seen[:2] == ["sending", "done"]


async def test_a_step_no_lane_could_do_asks_a_person() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert Progress.of((await world.saved_run()).progress).asking["kind"] == "step"


async def test_a_retry_after_a_send_never_runs_a_lane_and_settles_by_read_back() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.mark_sending(0)
    world.lanes.api.settles = "done"

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False
    assert (world.lanes.ui.calls, world.lanes.sight.calls) == (0, 0)
    run = await world.saved_run()
    assert [(one.verdict, one.verdict_by) for one in run.steps] == [("held", "api")]
    assert Progress.of(run.progress).written(0)


async def test_a_retry_after_a_send_no_read_back_can_settle_asks_and_stays_in_doubt() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.mark_sending(0)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert (world.lanes.ui.calls, world.lanes.sight.calls) == (0, 0)
    progress = Progress.of((await world.saved_run()).progress)
    assert progress.in_doubt(0)
    assert progress.step == 0


async def test_an_unknown_write_after_an_expiry_is_read_back_signed_in_afresh() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write())
    world.lanes.ui.answers(StepResult("unknown", Lane.UI, "no answer", expired=True))
    world.lanes.api.settles = "done"

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False
    assert world.lanes.api.contexts[-1].reauthed is True
    run = await world.saved_run()
    assert [one.verdict for one in run.steps] == ["held"]
    assert Progress.of(run.progress).written(0)


async def test_an_unknown_write_nothing_can_settle_is_asked_and_never_sent_again() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write())
    world.lanes.ui.answers(StepResult("unknown", Lane.UI, "no answer"))

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert world.lanes.api.contexts[-1].reauthed is False
    assert Progress.of((await world.saved_run()).progress).marks[0].wrote == "unknown"
    again = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert again.asking
    assert world.lanes.ui.calls == 1


async def test_a_busy_account_is_taught_what_was_tried_and_raised_for_a_retry() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    lease = Progress.of((await world.saved_run()).progress).lease
    assert await world.uow.browser_sessions.settle(TENANT, lease, state=LeaseState.WAITING)
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, "signed out", expired=True))

    with pytest.raises(AccountBusy):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    job = await world.uow.workflows.get(TENANT, "wfl_test")
    step = job.steps[0]
    assert await world.uow.workflows.broken_for(TENANT, job.id, {step.order: cites_key(step)}) == (
        Broken(0, Lane.UI, "f"),
    )
    assert Progress.of((await world.saved_run()).progress).step == 0


async def test_a_stopped_step_aborts_the_run_and_says_where() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    stop = asyncio.Event()
    stop.set()
    world.lanes.ui.on_execute(lambda ctx: ctx.check_stop())

    outcome = await world.run_steps.step(CTX, world.run_id, stop=stop)

    assert (outcome.more, outcome.failed) == (False, True)
    run = await world.saved_run()
    assert run.outcome == "aborted"
    assert await world.run_steps.finish(CTX, world.run_id) == "aborted"


async def test_a_dry_run_withholds_the_write() -> None:
    world = await steel_run(steps=[save_step(status=201)], live=False)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert [one.verdict for one in (await world.saved_run()).steps] == ["withheld"]
    assert world.lanes.ui.calls == 0
    assert await world.run_steps.finish(CTX, world.run_id) == "held"


async def test_a_run_that_stopped_short_finishes_failed() -> None:
    world = await steel_run(steps=[type_step(), save_step(status=201)])
    world.lanes.ui.answers(StepResult("done", Lane.UI))
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert await world.run_steps.finish(CTX, world.run_id) == "failed"
    assert (await world.saved_run()).finished_at is not None


async def test_two_runs_on_one_account_share_the_lease_as_two_tabs_and_close_their_own() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.another_run("run_b")
    for run_id in (world.run_id, "run_b"):
        await world.run_steps.prepare(CTX, run_id)
        await world.run_steps.acquire(CTX, run_id)
    a = Progress.of((await world.saved_run()).progress)
    b = Progress.of((await world.saved_run("run_b")).progress)

    assert a.lease == b.lease
    assert a.tabs[MAIN] != b.tabs[MAIN]

    await world.run_steps.release(CTX, "run_a")

    assert a.tabs[MAIN] not in world.driver.tabs
    assert b.tabs[MAIN] in world.driver.tabs
    assert Progress.of((await world.saved_run()).progress).tabs == {}


async def test_a_tab_lost_between_steps_is_opened_again_and_its_id_kept() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    lost = Progress.of((await world.saved_run()).progress).tabs[MAIN]
    del world.driver.tabs[lost], world.driver.owners[lost]
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    held = world.lanes.ui.contexts[-1].held
    assert held is not None and held.target_id != lost
    assert Progress.of((await world.saved_run()).progress).tabs[MAIN] == held.target_id
