from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.execution.pursuits import Pursuits
from sro.application.execution.workflow_runs import RunRefused, StartWorkflowRun
from sro.application.ports.dispatch import DispatchFailed, RunDispatcher
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.schedule import Scheduler
from sro.application.ports.system import Clock, IdFactory
from sro.domain.execution.run import RunId
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import ConfirmationId, TriggerId
from sro.domain.skill.skill import SkillVersion
from sro.domain.trigger.confirmation import ANSWER_WITHIN, Confirmation
from sro.domain.trigger.trigger import Trigger
from sro.whose import attribute

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Fired:
    trigger_id: TriggerId
    run_id: RunId | None = None
    confirmation_id: ConfirmationId | None = None

    skipped: str | None = None


class FireTrigger:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        durable: DurableExecution,
        *,
        ids: IdFactory,
        dispatcher: RunDispatcher | None = None,
        scheduler: Scheduler | None = None,
        start_run: StartWorkflowRun | None = None,
        pursuits: Pursuits | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._durable = durable
        self._ids = ids
        self._dispatcher = dispatcher
        self._scheduler = scheduler
        self._start_run = start_run
        self._pursuits = pursuits

    async def execute(
        self, trigger_id: TriggerId, *, message: Mapping[str, str] | None = None
    ) -> Fired:
        async with self._uow as uow:
            trigger = await uow.triggers.find(trigger_id)
            if trigger is None:
                await self._forget(trigger_id)
                return Fired(trigger_id, skipped="no such trigger")
            if not trigger.enabled:
                return Fired(trigger_id, skipped=trigger.disabled_reason or "disabled")

            ctx = RequestContext(tenant_id=trigger.tenant_id, principal_id=trigger.created_by)
            attribute(tenant=trigger.tenant_id.value, principal=trigger.created_by.value)
            now = self._clock.now()
            values = trigger.values_from(message or {})

            if trigger.workflow_id is not None:
                return await self._fire_a_job(uow, trigger, ctx=ctx, now=now, values=values)

            assert trigger.skill_id is not None  # noqa: S101 - the invariant Trigger keeps
            skill = await uow.skills.get(ctx.tenant_id, trigger.skill_id)
            version = skill.runnable
            if version is None:
                trigger.disable("the skill has no version that may run")
                await uow.triggers.save(trigger)
                await uow.commit()
                return Fired(trigger_id, skipped=trigger.disabled_reason)

            if version.changes_the_system and not trigger.writes:
                trigger.disable("the skill now changes the system; authorise this trigger again")
                await uow.triggers.save(trigger)
                await uow.commit()
                return Fired(trigger_id, skipped=trigger.disabled_reason)

            if blank := blank_inputs(version, values):
                return Fired(trigger_id, skipped="nothing said " + ", ".join(blank))

            if trigger.requires_confirmation:
                asked = await self._ask_a_person(
                    uow, trigger, now=now, values=values, message=message
                )
                return Fired(trigger_id, confirmation_id=asked.id)

            try:
                run_id = await self._start(ctx, trigger, version=version.version, values=values)
            except DispatchFailed as unreachable:
                logger.info("trigger %s could not reach its browser: %s", trigger_id, unreachable)
                return Fired(trigger_id, skipped=str(unreachable))

            trigger.fired(now, run_id)
            await uow.triggers.save(trigger)
            await uow.commit()

        return Fired(trigger_id, run_id=run_id)

    async def _ask_a_person(
        self,
        uow: UnitOfWork,
        trigger: Trigger,
        *,
        now: datetime,
        values: dict[str, str],
        message: Mapping[str, str] | None,
    ) -> Confirmation:
        for standing in await uow.confirmations.waiting(trigger.tenant_id):
            if (
                standing.trigger_id == trigger.id
                and standing.expires_at > now
                and standing.values == values
                and standing.because == _because(trigger, message)
            ):
                logger.info(
                    "trigger %s fired and %s is still waiting on somebody",
                    trigger.id.value,
                    standing.id.value,
                )
                trigger.fired(now, None)
                await uow.triggers.save(trigger)
                await uow.commit()
                return standing
        asked = Confirmation(
            id=self._ids.new_confirmation_id(),
            tenant_id=trigger.tenant_id,
            trigger_id=trigger.id,
            skill_id=trigger.skill_id,
            workflow_id=trigger.workflow_id,
            asked_at=now,
            expires_at=now + ANSWER_WITHIN,
            values=values,
            because=_because(trigger, message),
        )
        await uow.confirmations.add(asked)
        trigger.fired(now, None)
        await uow.triggers.save(trigger)
        await uow.commit()
        return asked

    async def _fire_a_job(
        self,
        uow: UnitOfWork,
        trigger: Trigger,
        *,
        ctx: RequestContext,
        now: datetime,
        values: dict[str, str],
        message: Mapping[str, str] | None = None,
    ) -> Fired:
        if self._start_run is None and self._dispatcher is None:
            return Fired(trigger.id, skipped="this process cannot start a job")
        if trigger.device_id is None:
            trigger.disable("a job runs in a browser: name a device")
            await uow.triggers.save(trigger)
            await uow.commit()
            return Fired(trigger.id, skipped=trigger.disabled_reason)

        await uow.workflows.get(ctx.tenant_id, str(trigger.workflow_id))

        if trigger.requires_confirmation:
            asked = await self._ask_a_person(uow, trigger, now=now, values=values, message=message)
            return Fired(trigger.id, confirmation_id=asked.id)

        try:
            run_id = await start_job_for(
                ctx,
                trigger,
                values=values,
                start_run=self._start_run,
                pursuits=self._pursuits,
                dispatcher=self._dispatcher,
            )
        except (DispatchFailed, Conflict, RunRefused) as refused:
            logger.info("trigger %s did not start its job: %s", trigger.id, refused)
            return Fired(trigger.id, skipped=str(refused))
        trigger.fired(now, run_id)
        await uow.triggers.save(trigger)
        await uow.commit()
        return Fired(trigger.id, run_id=run_id)

    async def _start(
        self, ctx: RequestContext, trigger: Trigger, *, version: int, values: dict[str, str]
    ) -> RunId:
        return await start_for(
            ctx,
            trigger,
            version=version,
            values=values,
            durable=self._durable,
            ids=self._ids,
            dispatcher=self._dispatcher,
        )

    async def _forget(self, trigger_id: TriggerId) -> None:
        if self._scheduler is None:
            return
        logger.info("removing the schedule for trigger %s, which no longer exists", trigger_id)
        await self._scheduler.unschedule(trigger_id)


async def start_for(
    ctx: RequestContext,
    trigger: Trigger,
    *,
    version: int,
    values: dict[str, str],
    durable: DurableExecution,
    ids: IdFactory,
    dispatcher: RunDispatcher | None,
    authorized_by: str | None = None,
) -> RunId:
    named = authorized_by or (trigger.authorized_by.value if trigger.authorized_by else None)
    if trigger.skill_id is None:
        raise DispatchFailed("this trigger runs a job, not a skill")

    if trigger.device_id is None:
        run_id = ids.new_run_id()
        await durable.execute_skill(
            ctx,
            skill_id=trigger.skill_id,
            parameters=values,
            version=version,
            authorized_by=named,
            medium=trigger.medium.value,
            run_id=run_id,
            wait=False,
        )
        return run_id

    if dispatcher is None:
        raise DispatchFailed("this process cannot reach a browser")
    return await dispatcher.start(
        ctx,
        skill_id=trigger.skill_id,
        parameters=values,
        device_id=trigger.device_id,
        version=version,
        authorized_by=named is not None,
        medium=trigger.medium,
        may_take_focus=trigger.may_take_focus,
    )


async def start_job_for(
    ctx: RequestContext,
    trigger: Trigger,
    *,
    values: Mapping[str, str],
    start_run: StartWorkflowRun | None,
    pursuits: Pursuits | None,
    dispatcher: RunDispatcher | None = None,
    authorized_by: str | None = None,
) -> RunId:
    named = authorized_by or (trigger.authorized_by.value if trigger.authorized_by else None)
    if named is None and trigger.writes:
        raise DispatchFailed("this trigger writes and names nobody who authorised it")
    if trigger.device_id is None:
        raise DispatchFailed("a job runs in a browser: this trigger names none")

    if dispatcher is not None:
        return await dispatcher.start_job(
            ctx,
            workflow_id=str(trigger.workflow_id),
            device_id=trigger.device_id,
            values=values,
            allow_focus=trigger.may_take_focus,
        )
    if start_run is None:
        raise DispatchFailed("this process cannot start a job")

    claimed = await start_run.execute(
        ctx,
        workflow_id=str(trigger.workflow_id),
        device_id=trigger.device_id,
        values=values,
        live=True,
        allow_focus=trigger.may_take_focus,
    )
    performing = start_run.perform(ctx, claimed)
    if pursuits is None:
        await performing
    else:
        pursuits.spawn(performing)
    return RunId(claimed.id)


def blank_inputs(version: SkillVersion, values: Mapping[str, str]) -> list[str]:
    return sorted(p.name for p in version.inputs if not values.get(p.name, "").strip())


def _because(trigger: Trigger, message: Mapping[str, str] | None) -> str:
    said = dict(message or {})
    for name in ("subject", "title", "summary"):
        if said.get(name):
            return said[name][:200]
    article = "an" if trigger.kind.value[0] in "aeiou" else "a"
    return f"{article} {trigger.kind} trigger fired"
