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
    tenant_id: str = ""
    """Whose pursuit this is. `id` is an unguessable uuid4, but every other
    resource in this system 404s across tenants rather than relying on that,
    and a pursuit is no different -- it drives a browser and writes to a
    thread, both scoped to one tenant."""

    state: PursuitState = PursuitState.WORKING
    gestures: list[str] = field(default_factory=list)
    detail: str = ""
    landed_at: str = ""

    session_id: str = ""
    """The browser it is driving. Kept so the reaper can tell a session
    somebody is using from one that outlived whatever opened it."""

    recording_id: str = ""
    """What it left behind. A pursuit is a demonstration nobody had to give."""

    skill_id: str = ""
    """The skill induced from it, so the same request is answered over the API
    next time instead of by looking at a screen again."""

    @property
    def finished(self) -> bool:
        return self.state is not PursuitState.WORKING


class Pursuits:
    """Every pursuit this process is driving. One per browser, in practice."""

    def __init__(self, keep: int = 50) -> None:
        self._live: dict[str, PursuitProgress] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._keep = keep

    def start(self, pursuit_id: str, goal: str, *, tenant_id: str = "") -> PursuitProgress:
        progress = PursuitProgress(id=pursuit_id, goal=goal, tenant_id=tenant_id)
        self._live[pursuit_id] = progress
        self._forget_old()
        return progress

    def working(self) -> PursuitProgress | None:
        """The pursuit driving a screen right now, if one is.

        There is one browser behind a self-hosted provider, so a second pursuit
        does not get a second screen -- it gets the same one, mid-task, and both
        navigate it out from under each other. Two pursuits produced two runs of
        twelve gestures that each reported the screen would not respond.
        """
        return next(
            (progress for progress in self._live.values() if not progress.finished), None
        )

    def get(self, pursuit_id: str) -> PursuitProgress | None:
        return self._live.get(pursuit_id)

    def sessions(self) -> tuple[str, ...]:
        """Browsers pursuits are driving right now, so nothing releases one."""
        return tuple(
            progress.session_id
            for progress in self._live.values()
            if progress.session_id and not progress.finished
        )

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
