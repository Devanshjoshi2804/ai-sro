from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

import pytest
from temporalio.testing import ActivityEnvironment

from sro.application.context import RequestContext
from sro.application.runtime.run_steps import StepOutcome
from sro.infrastructure.temporal.activities import RunActivities, RunRef

if TYPE_CHECKING:
    from sro.container import Container

K_NEVER_STOPPED_S = 5
REF = RunRef(tenant_id="acme", principal_id="clerk", run_id="run_a")


class _Steps:
    """A step that runs until it is stopped, then says so, as `RunSteps.step`
    does once its lane sees the stop; `beat` raises when `beat_fails`."""

    def __init__(self, *, beat_fails: bool = False) -> None:
        self.started = asyncio.Event()
        self.stopped_cleanly = False
        self.beat_fails = beat_fails
        self.finish = asyncio.Event()

    async def step(self, ctx: RequestContext, run_id: str, *, stop: asyncio.Event) -> StepOutcome:
        self.started.set()
        done = asyncio.create_task(self.finish.wait())
        stopped = asyncio.create_task(stop.wait())
        await asyncio.wait({done, stopped}, return_when=asyncio.FIRST_COMPLETED)
        done.cancel()
        stopped.cancel()
        self.stopped_cleanly = stop.is_set()
        return StepOutcome(more=False, failed=stop.is_set())

    async def beat(self, ctx: RequestContext, run_id: str) -> None:
        if self.beat_fails:
            raise ConnectionError("the database went away for a moment")


class _Container:
    def __init__(self, steps: _Steps) -> None:
        self._steps = steps

    def run_steps(self) -> _Steps:
        return self._steps


def _activities(steps: _Steps) -> RunActivities:
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
    steps = _Steps(beat_fails=True)
    env = ActivityEnvironment()
    running = asyncio.create_task(env.run(_activities(steps).step, REF))
    await steps.started.wait()

    steps.finish.set()

    assert await running == StepOutcome(more=False)
    assert not steps.stopped_cleanly
