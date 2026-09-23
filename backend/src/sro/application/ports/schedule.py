from __future__ import annotations

from typing import Protocol

from sro.domain.shared.identifiers import TriggerId
from sro.domain.trigger.trigger import Trigger


class Scheduler(Protocol):
    async def schedule(self, trigger: Trigger) -> None: ...

    async def unschedule(self, trigger_id: TriggerId) -> None: ...


class SchedulerUnavailable(Exception):
    code = "no_scheduler"
