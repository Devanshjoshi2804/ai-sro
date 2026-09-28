"""D10: a run left `running` after its workflow ended is closed, honestly, once.

Every run here is started the way production starts one -- `StartWorkflowRun`
claims the row and `start_on_steel` hands it to the durable side -- and driven
by the real `RunSteps` over a real `SessionBroker` on fakes. What the sweep is
asked to prove: a stuck row is closed with its reason and lets go of its tab
and its parked lease; a finished run, a run still open in Temporal and a run
whose real `finish` landed first are left alone; and two sweeps close one row
once.
"""

from __future__ import annotations

import asyncio

from sro.application.execution.approvals import Approvals
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.stops import Stops
from sro.application.execution.stuck_runs import CloseStuckRuns
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.domain.execution.account import LeaseState
from sro.domain.execution.progress import K_BUDGET_MARGIN_S, Progress
from sro.domain.execution.waiting import STUCK
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.identifiers import DeviceId
from sro.domain.skill.signing_in import PageSignals
from sro.domain.skill.tabs import MAIN
from tests.unit.fakes import FakeAsker, FakeChannel, FakeDurableExecution, FakeIdFactory
from tests.unit.runtime_support import APP, CTX, TENANT, SteelRun, save_step, steel_run

PAST_ITS_TIME = 120 + K_BUDGET_MARGIN_S
"""Seconds from the start of a one-step run to its end: `run_budget`'s floor
for a job whose evidence spans no time, plus the durable side's margin."""


def _starter(world: SteelRun, *, steel: bool = True) -> StartWorkflowRun:
    return StartWorkflowRun(
        world.uow,
        channel=FakeChannel(),
        asker=FakeAsker(),
        clock=world.clock,
        cap_usd=5.0,
        stops=Stops(),
        approvals=Approvals(),
        one_time_secrets=OneTimeSecrets(),
        durable=world.durable,
        steel_tenants=frozenset({TENANT.value}) if steel else frozenset(),
    )


async def _started(world: SteelRun) -> WorkflowRun:
    job = await world.job()
    starter = _starter(world)
    run = await starter.execute(
        CTX,
        workflow_id=job.id,
        device_id=None,
        values=(await world.saved_run()).values,
        live=True,
        allow_focus=False,
    )
    assert await starter.start_on_steel(CTX, run)
    await world.run_steps.prepare(CTX, run.id)
    await world.run_steps.acquire(CTX, run.id)
    return run


async def _world(*, asks_for_a_code: bool = False) -> tuple[SteelRun, WorkflowRun]:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.finish(CTX, world.run_id)
    if asks_for_a_code:
        await world.vault.store(world.account.vault_key("password"), "pw")
        world.driver.signals_for_every_tab = PageSignals(
            APP, autocomplete=frozenset({"one-time-code"})
        )
    run = await _started(world)
    if asks_for_a_code:
        await world.run_steps.release(CTX, run.id)
    return world, run


def _sweep(world: SteelRun, durable: FakeDurableExecution | None = None) -> CloseStuckRuns:
    return CloseStuckRuns(
        world.uow,
        durable=durable or world.durable,
        release=world.run_steps.release,
        clock=world.clock,
        ids=FakeIdFactory(),
    )


async def _saved(world: SteelRun, run_id: str) -> WorkflowRun:
    return await world.saved_run(run_id)


async def test_a_run_whose_workflow_timed_out_is_closed_with_its_reason_and_lets_its_tab_go() -> (
    None
):
    world, run = await _world()
    tab = Progress.of((await _saved(world, run.id)).progress).tabs[MAIN]
    assert tab in world.driver.tabs
    world.durable.ended.add(run.id)
    world.clock.advance(30)

    assert await _sweep(world).execute() == (run.id,)

    closed = await _saved(world, run.id)
    assert closed.outcome == "failed"
    assert closed.finished_at is not None
    assert closed.steps[-1].reason == STUCK
    assert (closed.steps[-1].verdict, closed.steps[-1].verdict_by) == ("failed", "none")
    assert tab not in world.driver.tabs, "the run's tab was closed"
    assert Progress.of(closed.progress).tabs == {}
    said = [one for one in await world.thread_says() if one["decision"].get("run_id") == run.id]
    assert [one["text"] for one in said] == [
        f"{(await world.job()).title} did not finish: {STUCK}."
    ]


async def test_a_run_parked_on_a_code_has_its_lease_released_when_its_workflow_is_gone() -> None:
    world, run = await _world(asks_for_a_code=True)
    waiting = Progress.of((await _saved(world, run.id)).progress)
    assert waiting.asking["kind"] == "code"
    assert world.uow.browser_sessions.leases[waiting.lease].state is LeaseState.WAITING
    world.durable.ended.add(run.id)

    assert await _sweep(world).execute() == (run.id,)

    lease = world.uow.browser_sessions.leases[waiting.lease]
    assert lease.state is LeaseState.EXPIRED
    assert waiting.tabs[MAIN] not in world.driver.tabs


async def test_a_run_past_its_time_that_temporal_never_heard_of_is_closed_by_the_clock() -> None:
    world, run = await _world()
    never = FakeDurableExecution()

    world.clock.advance(PAST_ITS_TIME - 1)
    assert await _sweep(world, never).execute() == ()
    world.clock.advance(1)
    assert await _sweep(world, never).execute() == (run.id,)

    assert (await _saved(world, run.id)).outcome == "failed"


async def test_a_run_still_open_in_temporal_is_left_alone_however_late() -> None:
    world, run = await _world()
    world.clock.advance(PAST_ITS_TIME * 10)

    assert await _sweep(world).execute() == ()
    assert (await _saved(world, run.id)).outcome == "running"


async def test_a_run_that_finished_normally_is_untouched() -> None:
    world, run = await _world()
    held = await world.run_steps.finish(CTX, run.id)
    before = await _saved(world, run.id)
    world.durable.ended.add(run.id)
    world.clock.advance(PAST_ITS_TIME)

    assert await _sweep(world).execute() == ()

    assert await _saved(world, run.id) == before
    assert before.outcome == held


async def test_a_run_waiting_on_a_question_is_not_closed_by_the_clock() -> None:
    world, run = await _world(asks_for_a_code=True)
    assert Progress.of((await _saved(world, run.id)).progress).asking.get("id")
    world.clock.advance(PAST_ITS_TIME * 10)

    assert await _sweep(world, FakeDurableExecution()).execute() == ()
    assert (await _saved(world, run.id)).outcome == "running"


async def test_the_real_finish_wins_a_race_and_the_sweep_does_nothing() -> None:
    world, run = await _world()
    world.durable.ended.add(run.id)
    sweep = _sweep(world)
    finished: list[str] = []

    real = world.uow.workflow_runs.close_stuck

    async def finish_lands_first(*args: object, **kwargs: object) -> bool:
        finished.append(await world.run_steps.finish(CTX, run.id))
        return await real(*args, **kwargs)

    world.uow.workflow_runs.close_stuck = finish_lands_first  # type: ignore[method-assign]
    assert await sweep.execute() == ()

    kept = await _saved(world, run.id)
    assert kept.outcome == finished[0]
    assert all(one.reason != STUCK for one in kept.steps)
    assert not [one for one in await world.thread_says() if one["text"].endswith(f"{STUCK}.")]


async def test_two_sweeps_at_once_close_the_row_once() -> None:
    world, run = await _world()
    world.durable.ended.add(run.id)
    real = world.uow.workflow_runs.running

    async def both_read_it_running() -> tuple[WorkflowRun, ...]:
        found = await real()
        await asyncio.sleep(0)
        return found

    world.uow.workflow_runs.running = both_read_it_running  # type: ignore[method-assign]

    first, second = await asyncio.gather(_sweep(world).execute(), _sweep(world).execute())

    assert sorted((*first, *second)) == [run.id]
    said = [one for one in await world.thread_says() if one["decision"].get("run_id") == run.id]
    assert len(said) == 1


async def test_an_extension_run_past_its_time_is_closed_without_asking_temporal() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.finish(CTX, world.run_id)
    job = await world.job()
    run = await _starter(world, steel=False).execute(
        CTX,
        workflow_id=job.id,
        device_id=DeviceId("dev-1"),
        values=(await world.saved_run()).values,
        live=True,
        allow_focus=False,
    )
    assert run.executor == "extension"
    world.clock.advance(PAST_ITS_TIME)

    assert await _sweep(world).execute() == (run.id,)
    assert (await _saved(world, run.id)).outcome == "failed"
