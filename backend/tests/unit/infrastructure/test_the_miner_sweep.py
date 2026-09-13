"""The miner's sweep, and the switch that decides it.

`worker.mine_the_rig_lately` calls `MineLately`, whose output is a `workflows`
row that `validate` has already refused nine ways, that no browser is offered
until it is proven, and whose first run is always dry. Until it existed,
`mine_pass` had one caller in `src/` and it was a door -- every mining result
this project had measured came from a person running a script.

There were two sweeps here, and the other one is why this file argues about a
default at all: `mine_lately` ran `MineObservations` and then `LearnWhatRepeats`
straight after, teaching every candidate seen `WORTH_OFFERING` times with
nobody asked. Four of the nine skills it taught across both real tenants are
not work. It shipped off, and phase 7 deleted it (2026-09-14) once both miners
had been measured over one store: it found nothing the model path missed.

No Temporal and no container of the real kind: the loop takes its interval as
an argument and reaches the rest through the container it is handed, so a stub
that raises if it is touched is the whole fixture.
"""

from __future__ import annotations

import asyncio
from typing import NoReturn

import pytest

from sro.config import Settings
from sro.infrastructure.temporal.worker import mine_the_rig_lately


class _Untouchable:
    """A container that fails the test if the sweep asks it for anything."""

    def __getattr__(self, name: str) -> NoReturn:
        raise AssertionError(f"the sweep is off and still reached for {name}()")


async def test_the_rig_sweep_of_zero_seconds_returns_instead_of_looping() -> None:
    """The same switch, on the other miner. Off means the coroutine finishes:
    `mine_the_rig_lately` is started with `asyncio.create_task`, so returning
    is what lets the worker's task complete on shutdown."""
    await asyncio.wait_for(mine_the_rig_lately(_Untouchable(), 0.0), timeout=1.0)


def test_the_shipped_default_leaves_the_rig_miner_on() -> None:
    """The decision, pinned where a diff has to argue with it.

    The opposite default from `mining_sweep_seconds`, and the two are not
    variants of one setting. That one teaches what it notices with nobody asked
    and four of the nine skills it taught across both real tenants are not
    work. This one writes a `workflows` row that `validate` has already refused
    nine ways, that no browser is offered until it is proven, and whose first
    run is always dry.

    A system whose promise is that it watches the work, notices the repetition
    and offers the job back cannot wait for somebody to press a button.
    """
    assert Settings(_env_file=None).rig_sweep_seconds == 3600.0


async def test_the_rig_sweep_sleeps_before_it_mines() -> None:
    """A worker restarting in a crash loop would otherwise fire the most
    expensive call in the system on every start. Asserted by watching it NOT
    reach for the container inside an interval it has not yet slept."""
    asked: list[str] = []

    class _Noted:
        def __getattr__(self, name: str) -> object:
            asked.append(name)
            raise RuntimeError("far enough")

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(mine_the_rig_lately(_Noted(), 30.0), timeout=0.25)

    assert asked == [], f"it mined before its first interval: {asked}"


async def test_a_positive_rig_interval_mines() -> None:
    """The switch is a switch, not a deletion. `mine_the_rig_lately` swallows
    whatever the sweep raises and carries on to the next interval, so the loop
    is ended by the timeout rather than by the error -- what is asserted is
    that it got as far as asking at all."""
    asked: list[str] = []

    class _Noted:
        def __getattr__(self, name: str) -> object:
            asked.append(name)
            raise RuntimeError("far enough")

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(mine_the_rig_lately(_Noted(), 0.001), timeout=0.25)

    assert "mine_lately" in asked, f"the rig sweep never mined; it asked for {asked}"
