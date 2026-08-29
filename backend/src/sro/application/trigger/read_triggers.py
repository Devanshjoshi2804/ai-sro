"""What is on a clock, and switching one off."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.schedule import Scheduler
from sro.domain.shared.identifiers import DeviceId, SkillId, TriggerId
from sro.domain.trigger.trigger import Trigger, TriggerKind


class ReadTriggers:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, skill_id: SkillId | None = None
    ) -> tuple[Trigger, ...]:
        async with self._uow as uow:
            return await uow.triggers.list_for_tenant(ctx.tenant_id, skill_id=skill_id)

    async def one(self, ctx: RequestContext, *, trigger_id: TriggerId) -> Trigger:
        async with self._uow as uow:
            return await uow.triggers.get(ctx.tenant_id, trigger_id)

    async def watches(self, ctx: RequestContext, *, device_id: DeviceId) -> tuple[Trigger, ...]:
        """What this one browser is watching for.

        A watch is evaluated nowhere else -- the browser that already has the
        mailbox open applies the rule locally, and nothing about the mail ever
        leaves it -- so the browser has to be able to ask what its rules are.

        Scoped to the device as well as the tenant, and that is the point: two
        operators in the same tenant have their own mailboxes, and a rule about
        one person's mail handed to another person's browser is that mail being
        read by somebody who was never offered it. Disabled ones are left out
        rather than sent with a flag, because a browser that had to remember to
        check the flag is a browser that one day does not.
        """
        async with self._uow as uow:
            # ponytail: filtered here rather than in SQL -- a tenant has tens of
            # triggers, not thousands. A `device_id` clause on `list_for_tenant`
            # is the move the first time that stops being true.
            triggers = await uow.triggers.list_for_tenant(ctx.tenant_id)
        return tuple(
            trigger
            for trigger in triggers
            if trigger.kind is TriggerKind.WATCH
            and trigger.enabled
            and trigger.device_id == device_id
        )


class SetTriggerEnabled:
    """Pausing a trigger unschedules it rather than letting it fire into a
    check. A schedule that runs every minute to decide it should not have is a
    schedule somebody will find in a bill."""

    def __init__(self, uow: UnitOfWork, scheduler: Scheduler) -> None:
        self._uow = uow
        self._scheduler = scheduler

    async def execute(
        self, ctx: RequestContext, *, trigger_id: TriggerId, enabled: bool, reason: str = ""
    ) -> Trigger:
        async with self._uow as uow:
            trigger = await uow.triggers.get(ctx.tenant_id, trigger_id)
            if enabled:
                trigger.enable()
            else:
                trigger.disable(reason or "switched off by hand")

            if trigger.kind is TriggerKind.SCHEDULE:
                if trigger.enabled:
                    await self._scheduler.schedule(trigger)
                else:
                    await self._scheduler.unschedule(trigger.id)

            await uow.triggers.save(trigger)
            await uow.commit()
        return trigger


class DeleteTrigger:
    def __init__(self, uow: UnitOfWork, scheduler: Scheduler) -> None:
        self._uow = uow
        self._scheduler = scheduler

    async def execute(self, ctx: RequestContext, *, trigger_id: TriggerId) -> None:
        async with self._uow as uow:
            # Read first: deleting a trigger that is not this tenant's must be
            # the same "not found" as one that never existed, and a blind
            # DELETE would answer 200 either way.
            trigger = await uow.triggers.get(ctx.tenant_id, trigger_id)
            # Only a schedule kind was ever registered with the scheduler --
            # the same gate SetTriggerEnabled applies. Without it, deleting a
            # manual or inbound trigger, which never depended on it, could
            # not be done during exactly the outage the rest of this system
            # goes out of its way to tolerate.
            if trigger.kind is TriggerKind.SCHEDULE:
                await self._scheduler.unschedule(trigger.id)
            await uow.triggers.remove(ctx.tenant_id, trigger.id)
            await uow.commit()
