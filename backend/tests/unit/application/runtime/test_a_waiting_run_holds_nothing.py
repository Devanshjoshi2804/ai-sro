"""L1: a run waiting on a person, for anything but a one-time code, holds no
lease, no park and no tab; anyone else on its account gets a page at once, and
the run, once answered, takes a lease the way a new run does.

Every run here is driven through the real `RunSteps` over a real
`SessionBroker` on fakes, and the other holder asks the same broker."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from temporalio.testing import ActivityEnvironment

from sro.domain.execution.account import LeaseState
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.execution.progress import Progress
from sro.domain.skill.signing_in import PageSignals
from sro.domain.skill.tabs import MAIN
from sro.infrastructure.temporal.activities import RunActivities, RunRef
from tests.unit.runtime_support import APP, CTX, SteelRun, save_step, steel_run

if TYPE_CHECKING:
    from sro.application.runtime.run_steps import RunSteps
    from sro.application.runtime.step import Held
    from sro.container import Container

K_PROMPTLY_S = 2.0
HOURS = 3 * 3600


async def _probe(world: SteelRun) -> Held:
    return await asyncio.wait_for(
        world.broker.acquire(CTX, world.account, APP, holder="probe"), K_PROMPTLY_S
    )


async def _asked_a_password_mid_step() -> tuple[SteelRun, str]:
    """The session ends under a step, and signing back in finds no password."""
    world = await steel_run(steps=[save_step(status=201)])
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    world.driver.expire_session()
    world.lanes.ui.answers(StepResult("failed", Lane.UI, "signed out", expired=True))

    asked = (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking

    assert Progress.of((await world.saved_run()).progress).asking["kind"] == "password"
    return world, asked


async def test_a_run_asking_for_a_password_leaves_the_account_to_the_next_holder() -> None:
    world, _ = await _asked_a_password_mid_step()
    parked = Progress.of((await world.saved_run()).progress).lease
    assert world.uow.browser_sessions.leases[parked].state is LeaseState.WAITING

    await world.run_steps.release(CTX, world.run_id)
    await world.vault.store(world.account.vault_key("password"), "pw")
    held = await _probe(world)

    assert held.target_id in world.driver.tabs
    assert world.uow.browser_sessions.leases[parked].state is LeaseState.EXPIRED
    assert (Progress.of((await world.saved_run()).progress).lease, world.driver.tabs) == (
        "",
        {held.target_id: world.driver.tabs[held.target_id]},
    )


async def test_a_code_park_the_run_no_longer_waits_on_is_ended_when_it_asks_otherwise() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.vault.store(world.account.vault_key("password"), "pw")
    await world.run_steps.prepare(CTX, world.run_id)
    world.driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))
    code = await world.run_steps.acquire(CTX, world.run_id)
    await world.run_steps.release(CTX, world.run_id)
    parked = Progress.of((await world.saved_run()).progress).lease
    await world.answer(code)
    world.driver.signals_for_every_tab = PageSignals(APP, password=True)
    assert await world.run_steps.acquire(CTX, world.run_id)
    assert Progress.of((await world.saved_run()).progress).asking["kind"] == "password"

    await world.run_steps.release(CTX, world.run_id)
    world.driver.signals_for_every_tab = PageSignals(APP)
    held = await _probe(world)

    assert held.target_id in world.driver.tabs
    assert world.uow.browser_sessions.leases[parked].state is LeaseState.EXPIRED


async def test_a_run_asking_about_a_failed_step_keeps_no_lease_or_tab() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    assert (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking

    await world.run_steps.release(CTX, world.run_id)
    held = await _probe(world)

    waiting = Progress.of((await world.saved_run()).progress)
    assert (waiting.lease, waiting.tabs) == ("", {})
    assert list(world.driver.tabs) == [held.target_id]


class _Container:
    def __init__(self, steps: RunSteps) -> None:
        self._steps = steps

    def run_steps(self) -> RunSteps:
        return self._steps


async def test_an_answered_run_takes_a_fresh_lease_and_carries_on_after_hours_of_waiting() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    first = Progress.of((await world.saved_run()).progress).lease
    asked = (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking
    await world.run_steps.release(CTX, world.run_id)
    world.clock.advance(HOURS)
    await _probe(world)
    assert world.uow.browser_sessions.leases[first].state is LeaseState.EXPIRED

    await world.answer(asked)
    activities = RunActivities(cast("Container", _Container(world.run_steps)))
    ref = RunRef(tenant_id="acme", principal_id="clerk", run_id=world.run_id, budget_s=600.0)
    world.lanes.ui.answers(StepResult("done", Lane.UI))
    assert await ActivityEnvironment().run(activities.acquire, ref) == ""
    outcome = await ActivityEnvironment().run(activities.step, ref)

    resumed = Progress.of((await world.saved_run()).progress)
    assert resumed.lease not in ("", first)
    assert world.uow.browser_sessions.leases[resumed.lease].state is LeaseState.READY
    assert resumed.tabs[MAIN] in world.driver.tabs
    assert (outcome.more, outcome.asking, resumed.step) == (False, "", 1)


async def test_a_second_release_of_a_waiting_run_changes_nothing() -> None:
    world, _ = await _asked_a_password_mid_step()
    parked = Progress.of((await world.saved_run()).progress).lease
    await world.run_steps.release(CTX, world.run_id)
    once = (await world.saved_run()).progress

    await world.run_steps.release(CTX, world.run_id)

    assert (await world.saved_run()).progress == once
    assert Progress.of(once).lease == ""
    assert world.uow.browser_sessions.leases[parked].state is LeaseState.EXPIRED


async def test_a_park_whose_release_never_ran_is_ended_by_the_password_answer() -> None:
    world, asked = await _asked_a_password_mid_step()
    parked = Progress.of((await world.saved_run()).progress).lease
    await world.vault.store(world.account.vault_key("password"), "pw")

    await world.answer(asked)

    assert world.uow.browser_sessions.leases[parked].state is LeaseState.EXPIRED
    assert await world.run_steps.acquire(CTX, world.run_id) == ""
    assert Progress.of((await world.saved_run()).progress).lease != parked


async def test_a_waiting_run_leaves_a_sibling_s_tab_and_their_shared_lease_alone() -> None:
    world = await steel_run(steps=[save_step(status=201)])
    await world.another_run("run_b")
    for run_id in (world.run_id, "run_b"):
        await world.run_steps.prepare(CTX, run_id)
        await world.run_steps.acquire(CTX, run_id)
    sibling = Progress.of((await world.saved_run("run_b")).progress)
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))
    assert (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).asking

    await world.run_steps.release(CTX, world.run_id)

    assert list(world.driver.tabs) == [sibling.tabs[MAIN]]
    assert world.uow.browser_sessions.leases[sibling.lease].state is LeaseState.READY
