import asyncio
from dataclasses import replace

import pytest

from sro.application.context import RequestContext
from sro.application.runtime.step import Held, LaneContext, Superseded, WaitingForAPerson
from sro.domain.execution.account import K_LEASE_TTL, LeaseState
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.skill.tabs import MAIN
from tests.unit.runtime_support import CTX, SteelRun, steel_run

POPUP = "opened_from:main"


async def _started(*tabs: str) -> SteelRun:
    world = await steel_run(tabs=tabs)
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    world.lanes.ui.answers(*(StepResult("done", Lane.UI) for _ in range(len(tabs) + 1)))
    return world


async def _step(world: SteelRun) -> None:
    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())


def _acted_in(world: SteelRun) -> list[str]:
    return [ctx.held.target_id for ctx in world.lanes.ui.contexts if ctx.held is not None]


async def test_a_step_in_a_popup_acts_in_the_tab_its_opener_opened() -> None:
    world = await _started(MAIN, POPUP)
    main = world.progress().tabs[MAIN]
    world.driver.popups[main] = "tab-9"

    await _step(world)
    await _step(world)

    assert _acted_in(world) == [main, "tab-9"]
    progress = world.progress()
    assert progress.tabs == {MAIN: main, POPUP: "tab-9"}
    assert [progress.marks[n].tab for n in (0, 1)] == [MAIN, POPUP]


async def test_a_second_tab_opens_at_the_steps_own_page() -> None:
    world = await _started(MAIN, "tab_2")
    main = world.progress().tabs[MAIN]

    await _step(world)
    await _step(world)

    context = world.lanes.ui.contexts[-1].held
    assert context is not None
    assert ("open_tab", context.session.context_id, world.page_of(1)) in world.driver.calls
    assert _acted_in(world)[-1] not in ("", main)
    assert world.progress().tabs == {MAIN: main, "tab_2": _acted_in(world)[-1]}


async def test_a_popup_that_never_opens_asks_a_person_and_sends_nothing() -> None:
    world = await _started(MAIN, POPUP)

    await _step(world)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert len(world.lanes.ui.contexts) == 1
    assert "never opened" in (await world.saved_run()).steps[-1].reason


async def test_release_closes_every_tab_of_the_run() -> None:
    world = await _started(MAIN, POPUP)
    main = world.progress().tabs[MAIN]
    world.driver.popups[main] = "tab-9"
    await _step(world)
    await _step(world)

    await world.run_steps.release(CTX, world.run_id)

    closed = [call[2] for call in world.driver.calls if call[0] == "close_tab"]
    assert closed == ["tab-9", main]
    assert world.progress().tabs == {}


async def test_a_resumed_run_returns_to_the_steps_own_tab() -> None:
    world = await _started(MAIN, POPUP)
    main = world.progress().tabs[MAIN]
    world.driver.popups[main] = "tab-9"
    await _step(world)
    await _step(world)
    world.rewind(to=1)

    await _step(world)

    assert _acted_in(world)[-1] == "tab-9"
    assert [call[2] for call in world.driver.calls if call[0] == "opened_by"] == [main]


async def test_a_popup_whose_tab_was_lost_is_found_again_from_its_opener() -> None:
    world = await _started(MAIN, POPUP)
    main = world.progress().tabs[MAIN]
    world.driver.popups[main] = "tab-9"
    await _step(world)
    await _step(world)
    del world.driver.tabs["tab-9"], world.driver.owners["tab-9"]
    world.driver.popups[main] = "tab-10"
    world.rewind(to=1)

    await _step(world)

    assert _acted_in(world)[-1] == "tab-10"
    assert world.progress().tabs == {MAIN: main, POPUP: "tab-10"}


async def test_a_new_lease_forgets_the_old_lease_s_tabs() -> None:
    world = await _started(MAIN, POPUP)
    main = world.progress().tabs[MAIN]
    world.driver.popups[main] = "tab-9"
    await _step(world)
    await _step(world)
    lease = world.progress().lease
    world.clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)
    world.rewind(to=0)

    await _step(world)

    progress = world.progress()
    assert progress.lease != lease
    assert set(progress.tabs) == {MAIN}


async def test_a_code_asked_in_a_popup_keeps_both_of_the_run_s_tabs() -> None:
    world = await _started(MAIN, POPUP)
    main = world.progress().tabs[MAIN]
    world.driver.popups[main] = "tab-9"

    def asks_for_a_code(ctx: LaneContext) -> None:
        if ctx.held is not None and ctx.held.target_id == "tab-9":
            waiting = replace(ctx.held.lease, state=LeaseState.WAITING, waits_for="code")
            raise WaitingForAPerson(
                "asks for a one-time code", held=replace(ctx.held, lease=waiting)
            )

    world.lanes.ui.on_execute(asks_for_a_code)
    await _step(world)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert world.progress().tabs == {MAIN: main, POPUP: "tab-9"}


async def test_a_tab_opened_by_an_attempt_another_one_superseded_is_closed() -> None:
    world = await _started(MAIN, "tab_2")
    await _step(world)
    opens = world.broker.open_tab
    opened: list[str] = []

    async def meanwhile_moved_on(ctx: RequestContext, held: Held, url: str) -> Held:
        tab = await opens(ctx, held, url)
        opened.append(tab.target_id)
        await world.mark_sending(0)
        return tab

    world.broker.open_tab = meanwhile_moved_on  # type: ignore[method-assign]

    with pytest.raises(Superseded):
        await _step(world)

    assert opened and opened[0] not in world.driver.tabs
    assert len(world.lanes.ui.contexts) == 1
