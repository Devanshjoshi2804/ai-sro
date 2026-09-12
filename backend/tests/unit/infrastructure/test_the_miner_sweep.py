"""The pre-rig observation sweep, and the switch that leaves it to a call.

`worker.mine_lately` is the only caller of `MineObservations`, and it does not
stop at noticing: it runs `LearnWhatRepeats` straight after, which teaches every
candidate seen `WORTH_OFFERING` times with nobody asked. So whether this loop
runs is whether a deployment learns things unattended, and it deserves a test
rather than a default nobody reads.

No Temporal and no container of the real kind: `mine_lately` takes the interval
as an argument and reaches the rest through the container it is handed, so a
stub that raises if it is touched is the whole fixture.
"""

from __future__ import annotations

import asyncio
from typing import NoReturn

import pytest

from sro.config import Settings
from sro.infrastructure.temporal.worker import mine_lately


class _Untouchable:
    """A container that fails the test if the sweep asks it for anything."""

    def __getattr__(self, name: str) -> NoReturn:
        raise AssertionError(f"the sweep is off and still reached for {name}()")


async def test_a_sweep_of_zero_seconds_returns_instead_of_looping() -> None:
    """Off means the coroutine finishes, not that it sleeps forever.

    A guard written as `while True: if every_seconds <= 0: continue` would spin,
    and one that slept first would hold a task the worker can never cancel
    cleanly. `mine_lately` is started with `asyncio.create_task`, so returning
    is what lets the task complete.
    """
    await asyncio.wait_for(mine_lately(_Untouchable(), 0.0, 24), timeout=1.0)


@pytest.mark.parametrize("interval", [0.0, -1.0])
async def test_nothing_is_mined_and_nothing_is_taught_while_it_is_off(
    interval: float,
) -> None:
    """Neither half runs. The learning half is the one that matters: it teaches
    without asking, and four of the nine skills it has taught across both real
    tenants are Gmail's `POST sync/u/*/i/s` or this console's own
    `POST */candidates/*/teach`.

    A negative interval is off too, and not a very fast sweep -- `asyncio.sleep`
    treats a negative delay as zero, so the naive guard would have mined in a
    tight loop.
    """
    await asyncio.wait_for(mine_lately(_Untouchable(), interval, 24), timeout=1.0)


def test_the_shipped_default_leaves_the_pre_rig_miner_off() -> None:
    """The decision, pinned where a diff has to argue with it.

    `mining_pass.mine` is the path this deployment runs on; `MineObservations`
    is the one it migrated away from. Turning the sweep back on is a deliberate
    edit, and the phase 7 precondition in
    `docs/new-agent-doc-arc/two-miners-one-day.md` wants a deliberate pass
    anyway -- both miners over one shared day, which a background loop has
    never given it.
    """
    assert Settings(_env_file=None).mining_sweep_seconds == 0.0


async def test_a_positive_interval_still_sweeps() -> None:
    """The switch is a switch, not a deletion.

    Asserted by watching the sweep reach for the container it is handed.
    `mine_lately` swallows whatever the sweep raises and carries on to the next
    interval, so the loop is ended by the timeout rather than by the error --
    what is being asserted is that it got as far as asking at all.
    """
    asked: list[str] = []

    class _Noted:
        def __getattr__(self, name: str) -> object:
            asked.append(name)
            raise RuntimeError("far enough")

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(mine_lately(_Noted(), 0.001, 24), timeout=0.25)

    assert "mine_everything" in asked, f"the sweep never mined; it asked for {asked}"
