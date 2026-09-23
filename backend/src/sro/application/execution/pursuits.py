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

    FAILED = "failed"


@dataclass
class PursuitProgress:
    id: str
    goal: str
    tenant_id: str = ""

    state: PursuitState = PursuitState.WORKING
    gestures: list[str] = field(default_factory=list)
    detail: str = ""
    landed_at: str = ""

    session_id: str = ""

    recording_id: str = ""

    skill_id: str = ""

    @property
    def finished(self) -> bool:
        return self.state is not PursuitState.WORKING


class Pursuits:
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
        return next((progress for progress in self._live.values() if not progress.finished), None)

    def get(self, pursuit_id: str) -> PursuitProgress | None:
        return self._live.get(pursuit_id)

    def sessions(self) -> tuple[str, ...]:
        return tuple(
            progress.session_id
            for progress in self._live.values()
            if progress.session_id and not progress.finished
        )

    def spawn(self, coroutine: Coroutine[object, object, None]) -> None:
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _forget_old(self) -> None:
        finished = [key for key, value in self._live.items() if value.finished]
        for key in finished[: max(0, len(self._live) - self._keep)]:
            del self._live[key]
