"""Pursuits in flight, and what they have done so far.

A pursuit is minutes long: twelve gestures, each one a screenshot to a hosted
model and back. Run inside the HTTP request that asked for it, it held the
whole API until it finished -- the console could not poll, could not answer
another question, and could not even report health. That is not a slow
endpoint, it is an outage with a good excuse.

So the request starts it and returns. What it returns is an address to watch,
and the gestures appear there as they happen, because a browser being driven on
somebody's behalf with nothing on screen for two minutes is indistinguishable
from a hang.

Kept in memory on purpose. A pursuit does not survive a restart and should not
pretend to: the browser it was driving does not survive one either, and a
half-finished pursuit resumed against a screen nobody can see is worse than one
that stopped. What survives is what it wrote to the thread when it finished.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)


class PursuitState(StrEnum):
    WORKING = "working"
    REACHED = "reached"
    STOPPED = "stopped"
    """Ran out of budget, was refused, or the screen stopped responding. Not an
    error: a pursuit that stops with a reason is doing its job."""

    FAILED = "failed"


@dataclass
class PursuitProgress:
    id: str
    goal: str
    state: PursuitState = PursuitState.WORKING
    gestures: list[str] = field(default_factory=list)
    detail: str = ""
    landed_at: str = ""

    @property
    def finished(self) -> bool:
        return self.state is not PursuitState.WORKING


class Pursuits:
    """Every pursuit this process is driving. One per browser, in practice."""

    def __init__(self, keep: int = 50) -> None:
        self._live: dict[str, PursuitProgress] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._keep = keep

    def start(self, pursuit_id: str, goal: str) -> PursuitProgress:
        progress = PursuitProgress(id=pursuit_id, goal=goal)
        self._live[pursuit_id] = progress
        self._forget_old()
        return progress

    def get(self, pursuit_id: str) -> PursuitProgress | None:
        return self._live.get(pursuit_id)

    def spawn(self, coroutine: Coroutine[object, object, None]) -> None:
        """Run it detached, and keep a reference so it is not garbage collected.

        A task nobody holds is a task the loop may collect mid-gesture, which
        would leave a browser open on a half-filled form.
        """
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _forget_old(self) -> None:
        finished = [key for key, value in self._live.items() if value.finished]
        for key in finished[: max(0, len(self._live) - self._keep)]:
            del self._live[key]
