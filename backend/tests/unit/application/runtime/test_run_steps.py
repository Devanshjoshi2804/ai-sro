import asyncio
from dataclasses import replace

import pytest

from sro.application.context import RequestContext
from sro.application.ports.locks import AccountBusy
from sro.application.ports.page import PageGone
from sro.application.runtime.step import LaneContext, Superseded
from sro.application.runtime.ui_lane import UiLane
from sro.domain.execution.account import Account, LeaseState
from sro.domain.execution.lanes import Broken, Lane, StepResult, Verdict, cites_key
from sro.domain.execution.progress import Progress, StepMark
from sro.domain.execution.takeover import OPERATOR, Takeover, Took, take_over
from sro.domain.skill.tabs import MAIN
from tests.unit.runtime_support import (
    CTX,
    NOW,
    TENANT,
    WORKFLOW,
    SteelRun,
    mail_send_step,
    operator_did,
    posted,
    save_step,
    steel_run,
    two_saves,
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
    assert await world.uow.workflows.broken_for(
        TENANT, job.id, {step.order: cites_key(step)}, now=NOW
    ) == (Broken(0, Lane.UI, "f"),)
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
    other = await steel_run(steps=[save_step(status=201)])

    await world.run_steps.stopped(CTX, world.run_id)
    assert await other.run_steps.finish(CTX, other.run_id) == "failed"
    await other.run_steps.stopped(CTX, other.run_id)

    assert (await world.saved_run()).outcome == "aborted"
    assert (await other.saved_run()).outcome == "failed"


async def test_a_prepare_that_asks_after_a_stop_never_reopens_the_run() -> None:
    world = await steel_run(steps=[save_step(status=201)], recorded_sign_in=False)
    asks = world.broker.account_for

    async def stopped_meanwhile(ctx: RequestContext, url: str) -> Account:
        await world.restarted().stopped(CTX, world.run_id)
        return await asks(ctx, url)

    world.broker.account_for = stopped_meanwhile  # type: ignore[method-assign,assignment]

    prepared = await world.run_steps.prepare(CTX, world.run_id)

    assert prepared.asking
    run = await world.saved_run()
    assert (run.outcome, run.finished_at) == ("aborted", None)


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
        "step": "0",
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


async def test_an_optional_value_nobody_gave_skips_its_step() -> None:
    world = await steel_run(steps=[type_step(), save_step(status=201)])
    await world.uow.workflow_runs.save(replace(await world.saved_run(), values={}))
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    first = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    second = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert (first.more, second.more) == (True, False)
    assert world.lanes.ui.calls == 1
    run = await world.saved_run()
    assert [(one.of_step, one.verdict) for one in run.steps] == [(0, "skipped"), (1, "held")]
    assert "Customer Type" in run.steps[0].reason
    assert await world.run_steps.finish(CTX, world.run_id) == "held"


async def test_a_required_value_nobody_gave_is_asked_for_never_guessed() -> None:
    step, by_id = type_step()
    job = replace(
        WORKFLOW,
        steps=[replace(step, order=0)],
        parameters=[{"name": "Customer Type", "required": True}],
    )
    world = await steel_run(steps=[(step, by_id)], job=job, values={})

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert world.lanes.ui.calls == 0
    progress = Progress.of((await world.saved_run()).progress)
    assert progress.asking["kind"] == "value"
    assert "Customer Type" in progress.asking["text"]


FORM = "https://wms.example/app/customer-types/new"


async def test_a_taken_over_run_skips_the_operator_s_save_and_replays_only_what_leads_on() -> None:
    world = await steel_run(
        steps=two_saves(FORM), progress=Takeover(replay_from=2, done=(1,)).progress()
    )
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))

    while (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).more:
        pass

    run = await world.saved_run()
    assert world.lanes.ui.calls == 2
    assert [one.of_step for one in run.steps] == [2, 3]
    assert Progress.of(run.progress).marks[1].lane == OPERATOR


async def test_a_write_the_operator_made_is_passed_over_as_theirs() -> None:
    world = await steel_run(
        steps=[save_step(status=201)], progress=Takeover(replay_from=0, done=(0,)).progress()
    )

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False and world.lanes.ui.calls == 0
    assert (await world.saved_run()).steps[-1].verdict_by == OPERATOR


async def test_an_operator_s_write_in_doubt_is_read_back_never_sent_again() -> None:
    world = await steel_run(
        steps=[save_step(status=201)], progress=Takeover(replay_from=0, in_doubt=(0,)).progress()
    )
    world.lanes.api.settles = "done"

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False and world.lanes.api.read_backs == 1
    assert world.lanes.ui.calls == 0
    assert Progress.of((await world.saved_run()).progress).written(0)


async def test_a_takeover_opens_steel_on_the_page_of_its_first_replayed_step() -> None:
    world = await steel_run(
        steps=two_saves(FORM), progress=Takeover(replay_from=2, done=(1,)).progress()
    )

    await world.run_steps.prepare(CTX, world.run_id)

    assert Progress.of((await world.saved_run()).progress).start_url == FORM


async def test_a_save_past_a_stale_offer_is_read_back_or_asked_about_never_sent() -> None:
    """An open offer made at k=2, then the operator's own Save -- in the same tab
    or in a popup -- then the press: the run never sends that save again."""
    cases: tuple[tuple[int, Verdict | None], ...] = ((7, None), (8, None), (7, "done"))
    for tab, reads_back in cases:
        steps = two_saves()
        job = replace(
            WORKFLOW,
            steps=[replace(step, order=n) for n, (step, _) in enumerate(steps)],
            parameters=[
                {"name": "First", "seen_values": ["A1", "A2"]},
                {"name": "Second", "seen_values": ["B1", "B2"]},
            ],
        )
        by_id = {one: seen for _, cited in steps for one, seen in cited.items()}
        world = await steel_run(steps=steps)
        await operator_did(world.uow, device="dev-1", tab=7, at=95.0, calls=[])
        await operator_did(
            world.uow, device="dev-1", tab=tab, at=100.0, calls=[posted("GT1", 100.0)]
        )
        seen = await world.uow.gestures.gestures_for(TENANT, stream_id="dev-1")
        took = take_over(
            job,
            by_id,
            matched=1,
            took=Took(7, 90.0, 95.0, 100.0),
            seen=seen,
            values={"First": "GT1", "Second": "GT2"},
        )
        await world.uow.workflow_runs.record_progress(
            TENANT, world.run_id, took.progress().as_json()
        )
        world.lanes.ui.answers(StepResult("done", Lane.UI))
        world.lanes.api.settles = reads_back

        await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
        second = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

        assert world.lanes.ui.calls == 1, tab
        assert world.lanes.api.read_backs == 1, tab
        progress = Progress.of((await world.saved_run()).progress)
        if reads_back is None:
            assert second.asking and progress.asking["kind"] == "step"
        else:
            assert progress.written(1) and progress.step == 2


async def _operator_answered(status: int) -> SteelRun:
    """A Steel run that takes over after the operator's own first save, which the
    system answered `status`."""
    steps = two_saves()
    job = replace(
        WORKFLOW,
        steps=[replace(step, order=n) for n, (step, _) in enumerate(steps)],
        parameters=[
            {"name": "First", "seen_values": ["A1", "A2"]},
            {"name": "Second", "seen_values": ["B1", "B2"]},
        ],
    )
    by_id = {one: seen for _, cited in steps for one, seen in cited.items()}
    world = await steel_run(steps=steps)
    await operator_did(
        world.uow, device="dev-1", tab=7, at=100.0, calls=[posted("GT1", 100.0, status)]
    )
    seen = await world.uow.gestures.gestures_for(TENANT, stream_id="dev-1")
    took = take_over(
        job,
        by_id,
        matched=2,
        took=Took(7, 90.0, 100.0, 100.0),
        seen=seen,
        values={"First": "GT1", "Second": "GT2"},
    )
    await world.uow.workflow_runs.record_progress(TENANT, world.run_id, took.progress().as_json())
    return world


async def test_an_operator_save_answered_409_is_read_back_or_asked_never_sent_again() -> None:
    world = await _operator_answered(409)
    world.lanes.ui.answers(StepResult("done", Lane.UI))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    asked = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.lanes.ui.calls == 1 and world.lanes.api.read_backs == 1
    assert asked.asking


async def test_an_operator_save_answered_422_is_made_by_the_run() -> None:
    world = await _operator_answered(422)
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert world.lanes.ui.calls == 2 and world.lanes.api.read_backs == 0
    assert Progress.of((await world.saved_run()).progress).step == 2
