"""Temporal Schedules: the clock this system does not keep itself.

A cron loop in a process fires nothing while that process is down and twice
while two are up, and both of those are a warehouse write. Temporal already
answers those questions, and the deployment already runs it.

The schedule id is derived from the trigger id, which is what makes creating one
twice idempotent -- the same trigger scheduled again is one schedule, not two
runs of the same task at the same moment against the same records.
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleSpec,
    ScheduleUpdate,
)
from temporalio.service import RPCError, RPCStatusCode

from sro.application.ports.schedule import Scheduler, SchedulerUnavailable
from sro.domain.shared.identifiers import TriggerId
from sro.domain.trigger.trigger import Trigger
from sro.infrastructure.temporal.activities import TriggerRequest
from sro.infrastructure.temporal.queues import DEFAULT_QUEUE
from sro.infrastructure.temporal.workflows import TriggerWorkflow

logger = logging.getLogger(__name__)


def schedule_id(trigger_id: TriggerId) -> str:
    return f"trigger-{trigger_id.value}"


class TemporalScheduler(Scheduler):
    def __init__(self, *, address: str, namespace: str = "default") -> None:
        self._address = address
        self._namespace = namespace
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    async def schedule(self, trigger: Trigger) -> None:
        if trigger.cron is None:
            raise SchedulerUnavailable("this trigger has no cron expression to schedule")
        client = await self._connect()
        spec = ScheduleSpec(cron_expressions=[trigger.cron], time_zone_name=trigger.timezone)
        action = ScheduleActionStartWorkflow(
            TriggerWorkflow.run,
            TriggerRequest(trigger_id=trigger.id.value),
            # Derived, so a firing is traceable to the trigger that caused it
            # without a lookup.
            id=f"fire-{trigger.id.value}",
            task_queue=DEFAULT_QUEUE,
        )
        try:
            await client.create_schedule(
                schedule_id(trigger.id), Schedule(action=action, spec=spec)
            )
        except ScheduleAlreadyRunningError:
            # Idempotent by id: an update replaces the spec rather than adding
            # a second schedule for the same trigger.
            handle = client.get_schedule_handle(schedule_id(trigger.id))
            await handle.update(
                lambda _: ScheduleUpdate(schedule=Schedule(action=action, spec=spec))
            )

    async def unschedule(self, trigger_id: TriggerId) -> None:
        client = await self._connect()
        try:
            await client.get_schedule_handle(schedule_id(trigger_id)).delete()
        except RPCError as failure:
            if failure.status is not RPCStatusCode.NOT_FOUND:
                raise
            # Already gone. Deleting what is not there is the success this port
            # promises, because a failed teardown must be safe to repeat.
            logger.debug("no schedule for trigger %s to remove", trigger_id)

    async def _connect(self) -> Client:
        """Connected on first use, not at boot: a Temporal outage must not stop
        the API from serving reads. Same reason as the durable adapter."""
        async with self._lock:
            if self._client is None:
                try:
                    self._client = await Client.connect(self._address, namespace=self._namespace)
                except RuntimeError as unreachable:
                    raise SchedulerUnavailable(
                        f"no scheduler at {self._address}: {unreachable}"
                    ) from unreachable
            return self._client
