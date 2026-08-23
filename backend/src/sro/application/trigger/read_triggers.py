"""What is on a clock, and switching one off."""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.schedule import Scheduler
from sro.domain.shared.identifiers import SkillId, TriggerId
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
            await self._scheduler.unschedule(trigger.id)
            await uow.triggers.remove(ctx.tenant_id, trigger.id)
            await uow.commit()
