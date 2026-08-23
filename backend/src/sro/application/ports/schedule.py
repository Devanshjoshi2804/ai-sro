"""Handing a clock to somebody else.

The system has no timer of its own for this on purpose. A cron loop in a process
fires nothing while the process is down and fires twice when two are up, and
both of those are a warehouse write. What this port asks for is a scheduler that
already answers those questions.
"""

from __future__ import annotations

from typing import Protocol

from sro.domain.shared.identifiers import TriggerId
from sro.domain.trigger.trigger import Trigger


class Scheduler(Protocol):
    async def schedule(self, trigger: Trigger) -> None:
        """Create or replace the schedule for this trigger.

        Idempotent on the trigger's id: the same trigger scheduled twice is one
        schedule, because the alternative is two runs of the same task at the
        same moment against the same records.
        """
        ...

    async def unschedule(self, trigger_id: TriggerId) -> None:
        """Idempotent: a schedule that is already gone is success.

        By id rather than by trigger, because the caller that most needs this is
        a schedule that outlived the trigger it was for -- there is no trigger
        left to pass.
        """
        ...


class SchedulerUnavailable(Exception):
    """No scheduler. Not a ``DomainError``: the trigger was fine.

    Raised rather than storing a trigger that will never fire, which is worse
    than refusing to store it -- somebody would believe the task was covered.
    """
