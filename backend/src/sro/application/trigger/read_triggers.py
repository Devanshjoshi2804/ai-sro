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
        async with self._uow as uow:
            triggers = await uow.triggers.list_for_tenant(ctx.tenant_id)
        return tuple(
            trigger
            for trigger in triggers
            if trigger.kind is TriggerKind.WATCH
            and trigger.enabled
            and trigger.device_id == device_id
        )

    async def arrivals(self, ctx: RequestContext, *, device_id: DeviceId) -> tuple[Trigger, ...]:
        async with self._uow as uow:
            triggers = await uow.triggers.list_for_tenant(ctx.tenant_id)
        return tuple(
            trigger
            for trigger in triggers
            if trigger.kind is TriggerKind.ARRIVAL
            and trigger.enabled
            and trigger.device_id == device_id
        )


class SetTriggerEnabled:
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
            trigger = await uow.triggers.get(ctx.tenant_id, trigger_id)
            if trigger.kind is TriggerKind.SCHEDULE:
                await self._scheduler.unschedule(trigger.id)
            await uow.triggers.remove(ctx.tenant_id, trigger.id)
            await uow.commit()
