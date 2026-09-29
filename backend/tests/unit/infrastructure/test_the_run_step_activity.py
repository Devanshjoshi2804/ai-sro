from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest
from temporalio.activity import ActivityCancellationDetails
from temporalio.testing import ActivityEnvironment

from sro.application.context import RequestContext
from sro.application.ports.page import PageGone
from sro.application.runtime.run_steps import RunSteps, StepOutcome
from sro.application.runtime.step import LaneContext
from sro.domain.execution.lanes import Lane
from sro.infrastructure.temporal.activities import RunActivities, RunRef
from tests.unit.runtime_support import CTX, save_step, steel_run

if TYPE_CHECKING:
    from sro.container import Container

K_NEVER_STOPPED_S = 5
REF = RunRef(tenant_id="acme", principal_id="clerk", run_id="run_a", budget_s=600.0)
TIMED_OUT = ActivityCancellationDetails(timed_out=True)


class _Steps:
    """A step that runs until it is stopped, then says so, as `RunSteps.step`
    does once its lane sees the stop; `beat` raises `beat_raises` when set."""

    def __init__(self, *, beat_raises: Exception | None = None) -> None:
        self.started = asyncio.Event()
        self.stopped_cleanly = False
        self.cancelled = False
        self.beat_raises = beat_raises
        self.finish = asyncio.Event()

    async def step(self, ctx: RequestContext, run_id: str, *, stop: asyncio.Event) -> StepOutcome:
        self.started.set()
        done = asyncio.create_task(self.finish.wait())
        stopped = asyncio.create_task(stop.wait())
        try:
            await asyncio.wait({done, stopped}, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        finally:
            done.cancel()
            stopped.cancel()
        self.stopped_cleanly = stop.is_set()
        return StepOutcome(more=False, failed=stop.is_set())

    async def beat(self, ctx: RequestContext, run_id: str) -> None:
        if self.beat_raises is not None:
            await self.started.wait()
            raise self.beat_raises


class _Container:
    def __init__(self, steps: _Steps | RunSteps) -> None:
        self._steps = steps

    def run_steps(self) -> _Steps | RunSteps:
        return self._steps


def _activities(steps: _Steps | RunSteps) -> RunActivities:
    return RunActivities(cast("Container", _Container(steps)))


async def test_a_cancelled_step_is_stopped_and_waited_for_before_the_cancel_goes_on() -> None:
    steps = _Steps()
    env = ActivityEnvironment()
    running = asyncio.create_task(env.run(_activities(steps).step, REF))
    await steps.started.wait()

    env.cancel()

    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(K_NEVER_STOPPED_S):
            await running
    assert steps.stopped_cleanly


async def test_a_beat_that_fails_never_abandons_the_step() -> None:
    steps = _Steps(beat_raises=ConnectionError("the database went away for a moment"))
    env = ActivityEnvironment()
    running = asyncio.create_task(env.run(_activities(steps).step, REF))
    await steps.started.wait()

    steps.finish.set()

    assert await running == StepOutcome(more=False)
    assert not steps.stopped_cleanly


async def test_a_timed_out_attempt_is_cancelled_not_stopped() -> None:
    steps = _Steps()
    env = ActivityEnvironment()
    running = asyncio.create_task(env.run(_activities(steps).step, REF))
    await steps.started.wait()

    env.cancel(TIMED_OUT)

    with pytest.raises(asyncio.CancelledError):
        await running
    assert steps.cancelled
    assert not steps.stopped_cleanly


async def test_a_lease_lost_under_a_step_cancels_it_and_says_the_page_is_gone() -> None:
    steps = _Steps(beat_raises=PageGone("lease lst_1 is no longer live"))

    with pytest.raises(PageGone):
        await ActivityEnvironment().run(_activities(steps).step, REF)

    assert steps.cancelled


async def test_a_heartbeat_timeout_then_a_retry_sends_once_and_never_aborts() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    in_flight = asyncio.Event()

    async def sends_and_hangs(ctx: LaneContext) -> None:
        await ctx.about_to_write(Lane.UI)
        in_flight.set()
        await asyncio.Event().wait()

    world.lanes.ui.on_execute(sends_and_hangs)
    env = ActivityEnvironment()
    first = asyncio.create_task(env.run(_activities(world.run_steps).step, REF))
    await in_flight.wait()
    env.cancel(TIMED_OUT)
    with pytest.raises(asyncio.CancelledError):
        await first
    world.lanes.api.settles = "done"

    again = await ActivityEnvironment().run(_activities(world.run_steps).step, REF)

    assert again == StepOutcome(more=False)
    assert world.lanes.ui.calls == 1
    run = await world.saved_run()
    assert run.outcome == "running"
    assert [one.verdict for one in run.steps] == ["held"]
    assert await world.run_steps.finish(CTX, world.run_id) == "held"
