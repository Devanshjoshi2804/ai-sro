import asyncio

import pytest

from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone
from sro.application.runtime.step import LaneContext, Superseded
from sro.application.runtime.ui_lane import UiLane
from sro.domain.execution.account import LeaseState
from sro.domain.execution.lanes import Broken, Lane, StepResult, cites_key
from sro.domain.execution.progress import MAIN, Progress, StepMark
from tests.unit.runtime_support import (
    CTX,
    TENANT,
    SteelRun,
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
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write(Lane.UI))
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
    run = await world.saved_run()
    assert Progress.of(run.progress).asking["kind"] == "step"
    assert [(one.of_step, one.verdict, one.verdict_by) for one in run.steps] == [
        (0, "failed", "sight")
    ]
    assert "could not be done" in run.steps[0].reason


async def test_a_retry_after_a_send_never_runs_a_lane_and_settles_by_read_back() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.mark_sending(0)
    world.lanes.api.settles = "done"

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False
    assert (world.lanes.ui.calls, world.lanes.sight.calls) == (0, 0)
    run = await world.saved_run()
    assert [(one.verdict, one.verdict_by) for one in run.steps] == [("held", "ui")]
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
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write(Lane.UI))
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
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write(Lane.UI))
    world.lanes.ui.answers(StepResult("unknown", Lane.UI, "no answer"))

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert world.lanes.api.contexts[-1].reauthed is False
    run = await world.saved_run()
    assert Progress.of(run.progress).marks[0].wrote == "unknown"
    assert [(one.verdict, one.verdict_by) for one in run.steps] == [("unclear", "ui")]
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


async def test_a_stop_is_seen_before_the_next_primitive() -> None:
    step, by_id = save_step(status=201)
    world = await steel_run(steps=[(step, by_id)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    stop = asyncio.Event()
    stop.set()

    async def really_acts(ctx: LaneContext) -> None:
        await UiLane(world.driver).execute(step, {}, ctx)

    world.lanes.ui.on_execute(really_acts)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=stop)

    assert outcome.failed and not outcome.more
    assert (await world.saved_run()).outcome == "aborted"
    assert world.driver.acted == []


async def test_stopped_aborts_a_running_run_and_leaves_a_finished_one_alone() -> None:
    world = await steel_run(steps=[save_step(status=201)])

    await world.run_steps.stopped(CTX, world.run_id)
    run = await world.saved_run()
    assert run.outcome == "aborted"
    run.outcome = "held"
    await world.uow.workflow_runs.save(run)
    await world.run_steps.stopped(CTX, world.run_id)

    assert (await world.saved_run()).outcome == "held"


async def test_a_restarted_worker_finds_the_run_s_tab_by_its_target_id() -> None:
    world = await steel_run(steps=[type_step(), save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    tab = Progress.of((await world.saved_run()).progress).tabs[MAIN]
    opened = dict(world.driver.tabs)

    await world.restarted().acquire(CTX, world.run_id)

    assert Progress.of((await world.saved_run()).progress).tabs[MAIN] == tab
    assert world.driver.tabs == opened


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


def _both_arrive(world: SteelRun, *, write: bool) -> list[int]:
    """Holds each attempt in the UI lane until two are there, the way a retry
    Temporal scheduled overlaps the attempt it gave up on; `sent` counts the
    writes that actually went out."""
    here: list[LaneContext] = []
    both = asyncio.Event()
    sent: list[int] = []

    async def act(ctx: LaneContext) -> None:
        here.append(ctx)
        if len(here) == 2:
            both.set()
        await both.wait()
        if write:
            await ctx.about_to_write(Lane.UI)
            sent.append(1)

    world.lanes.ui.on_execute(act)
    return sent


async def test_two_overlapping_attempts_on_a_one_write_job_send_it_once() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    sent = _both_arrive(world, write=True)
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))

    results = await asyncio.gather(
        world.run_steps.step(CTX, world.run_id, stop=asyncio.Event()),
        world.run_steps.step(CTX, world.run_id, stop=asyncio.Event()),
        return_exceptions=True,
    )

    assert len(sent) == 1
    assert sum(isinstance(one, Superseded) for one in results) == 1
    run = await world.saved_run()
    assert [(one.of_step, one.verdict) for one in run.steps] == [(0, "held")]
    assert Progress.of(run.progress).step == 1


async def test_overlapping_attempts_on_a_two_step_job_never_skip_the_save() -> None:
    world = await steel_run(steps=[type_step(), save_step(status=201)])
    _both_arrive(world, write=False)
    world.lanes.ui.answers(*(StepResult("done", Lane.UI) for _ in range(3)))

    await asyncio.gather(
        world.run_steps.step(CTX, world.run_id, stop=asyncio.Event()),
        world.run_steps.step(CTX, world.run_id, stop=asyncio.Event()),
        return_exceptions=True,
    )
    world.lanes.ui.on_execute(lambda ctx: None)
    last = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert last.more is False
    run = await world.saved_run()
    assert [(one.of_step, one.verdict) for one in run.steps] == [(0, "held"), (1, "held")]
    assert world.lanes.ui.calls == 3


async def test_a_run_that_is_no_longer_running_is_never_acted_on() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    run = await world.saved_run()
    run.outcome = "aborted"
    await world.uow.workflow_runs.save(run)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False
    assert world.lanes.ui.calls == 0
    assert await world.run_steps.acquire(CTX, world.run_id) == ""
    assert Progress.of((await world.saved_run()).progress).tabs == {}


async def test_a_job_with_no_recorded_sign_in_asks_at_prepare_and_says_why() -> None:
    world = await steel_run(steps=[save_step(status=201)], recorded_sign_in=False)

    prepared = await world.run_steps.prepare(CTX, world.run_id)

    assert prepared.asking
    run = await world.saved_run()
    assert Progress.of(run.progress).asking["id"] == prepared.asking
    assert [one.verdict for one in run.steps] == ["failed"]
    assert "no recorded sign-in" in run.steps[0].reason


async def test_a_sign_in_that_needs_a_password_is_asked_at_acquire() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    world.driver.shows_sign_in_until_signed = True

    asking = await world.run_steps.acquire(CTX, world.run_id)

    assert asking
    run = await world.saved_run()
    assert Progress.of(run.progress).asking == {
        "id": asking,
        "kind": "password",
        "text": run.steps[0].reason,
    }
    assert [one.verdict for one in run.steps] == ["failed"]


async def test_a_stop_during_acquire_keeps_the_tab_for_release_and_aborts() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    stop = asyncio.Event()
    stop.set()

    await world.run_steps.acquire(CTX, world.run_id, stop=stop)

    run = await world.saved_run()
    assert run.outcome == "aborted"
    tab = Progress.of(run.progress).tabs[MAIN]
    await world.run_steps.release(CTX, world.run_id)
    assert tab not in world.driver.tabs


async def test_an_acquire_that_cannot_record_its_tab_closes_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)

    async def lost(*args: object, **kwargs: object) -> bool:
        raise ConnectionError("the database went away")

    monkeypatch.setattr(world.uow.workflow_runs, "record_progress", lost)

    with pytest.raises(ConnectionError):
        await world.run_steps.acquire(CTX, world.run_id)

    assert world.driver.tabs == {}


async def test_a_done_step_stays_done_when_teaching_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write(Lane.UI))
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    async def broken(*args: object, **kwargs: object) -> None:
        raise ConnectionError("the database went away")

    monkeypatch.setattr(world.uow.workflows, "mend_lane", broken)

    with pytest.raises(ConnectionError):
        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert Progress.of(run.progress).written(0)
    assert [one.verdict for one in run.steps] == ["held"]


async def test_an_in_doubt_write_is_read_back_as_its_sender_signed_in_afresh() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write(Lane.UI))
    world.lanes.ui.answers(StepResult("unknown", Lane.UI, "no answer", expired=True))
    asked = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    assert asked.asking
    world.lanes.api.settles = "done"

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.lanes.ui.calls == 1
    assert world.lanes.api.contexts[-1].reauthed is True
    run = await world.saved_run()
    assert [(one.verdict, one.verdict_by) for one in run.steps] == [
        ("unclear", "ui"),
        ("held", "ui"),
    ]
    assert Progress.of(run.progress).asking == {}
    assert await world.run_steps.finish(CTX, world.run_id) == "held"


async def test_a_retry_after_a_crash_mid_send_names_the_lane_that_sent() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.mark_sending(0, Lane.SIGHT)
    world.lanes.api.settles = "done"

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert [(one.verdict, one.verdict_by) for one in run.steps] == [("held", "sight")]


async def test_a_lease_the_beat_finds_lost_is_the_lost_page_path() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    lease = Progress.of((await world.saved_run()).progress).lease
    assert await world.uow.browser_sessions.settle(TENANT, lease, state=LeaseState.BROKEN)

    with pytest.raises(PageGone):
        await world.run_steps.beat(CTX, world.run_id)


async def test_a_zombie_attempt_that_fails_a_step_already_held_asks_nothing() -> None:
    world = await steel_run(steps=[type_step(), save_step(status=201)])
    zombie_in, zombie_go = asyncio.Event(), asyncio.Event()
    calls: list[LaneContext] = []

    async def first_one_hangs(ctx: LaneContext) -> None:
        calls.append(ctx)
        if len(calls) == 1:
            zombie_in.set()
            await zombie_go.wait()

    world.lanes.ui.on_execute(first_one_hangs)
    world.lanes.ui.answers(
        StepResult("done", Lane.UI),
        StepResult("failed", Lane.UI, "the zombie lost its page"),
        StepResult("done", Lane.UI),
    )
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, "nor could sight"))
    zombie = asyncio.create_task(world.run_steps.step(CTX, world.run_id, stop=asyncio.Event()))
    await zombie_in.wait()
    assert (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).more

    zombie_go.set()
    with pytest.raises(Superseded):
        await zombie
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    run = await world.saved_run()
    assert [(one.of_step, one.verdict) for one in run.steps] == [(0, "held"), (1, "held")]
    assert Progress.of(run.progress).asking == {}
    assert await world.run_steps.finish(CTX, world.run_id) == "held"
