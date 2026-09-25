from __future__ import annotations

import secrets
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.schedule import Scheduler
from sro.application.ports.system import Clock, IdFactory
from sro.domain.execution.run import Medium
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.trigger.arrival import Arrival
from sro.domain.trigger.trigger import Trigger, TriggerKind
from sro.domain.trigger.watch import QUESTION, Watch


class TriggerRefused(DomainError):
    code = "trigger_refused"


@dataclass(frozen=True, slots=True)
class NewTrigger:
    skill_id: SkillId | None = None
    workflow_id: str | None = None

    kind: TriggerKind = TriggerKind.SCHEDULE
    cron: str | None = None
    timezone: str = "UTC"
    parameters: dict[str, str] | None = None
    from_message: tuple[str, ...] = ()

    watch: Watch | None = None

    arrival: Arrival | None = None

    device_id: DeviceId | None = None
    medium: Medium = Medium.NETWORK
    authorized_by: bool = False

    auto_approve: bool = False
    may_take_focus: bool = False

    asks: bool = False


class CreateTrigger:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        ids: IdFactory,
        scheduler: Scheduler,
        can_gather: bool = False,
        start_run: StartWorkflowRun | None = None,
    ) -> None:
        self._uow = uow
        self._start_run = start_run
        self._clock = clock
        self._ids = ids
        self._scheduler = scheduler
        self._can_gather = can_gather

    async def execute(self, ctx: RequestContext, request: NewTrigger) -> Trigger:
        parameters = dict(request.parameters or {})
        named = [name for name in (request.skill_id, request.workflow_id) if name]
        if request.asks:
            return await self._for_a_question(ctx, request)
        if len(named) != 1:
            raise TriggerRefused(
                "a trigger runs one thing: name a skill or a job, not "
                + ("both" if named else "neither")
            )

        if request.workflow_id is not None:
            return await self._for_a_job(ctx, request, parameters=parameters)

        if request.kind is TriggerKind.ARRIVAL:
            raise TriggerRefused("only a mined job can be started by arriving somewhere")

        assert request.skill_id is not None  # noqa: S101 - checked directly above
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, request.skill_id)
            version = skill.runnable
            if version is None:
                raise TriggerRefused(
                    "this skill has no version that may run yet; it has never been rehearsed"
                )

            supplied = request.watch.reads if request.watch else request.from_message

            declared = {parameter.name for parameter in version.parameters}
            if unknown := sorted(set(supplied) - declared):
                raise TriggerRefused(
                    f"this skill has no {', '.join(unknown)} for a message to supply"
                )

            missing = sorted(
                parameter.name
                for parameter in version.inputs
                if parameter.name not in parameters and parameter.name not in supplied
            )
            if missing:
                raise TriggerRefused(
                    f"this skill needs {', '.join(missing)}: supply a value, "
                    "or say that a message will"
                )

            writes = version.changes_the_system
            if writes and not request.authorized_by:
                raise TriggerRefused(
                    "this skill changes the system, so a trigger for it must be authorised"
                )

            trigger = Trigger(
                id=self._ids.new_trigger_id(),
                tenant_id=ctx.tenant_id,
                skill_id=skill.id,
                kind=request.kind,
                created_by=ctx.principal_id,
                created_at=self._clock.now(),
                parameters=parameters,
                from_message=request.from_message,
                watch=request.watch,
                cron=request.cron,
                timezone=request.timezone,
                device_id=request.device_id,
                medium=request.medium,
                writes=writes,
                authorized_by=ctx.principal_id if request.authorized_by else None,
                requires_confirmation=writes and not request.auto_approve,
                may_take_focus=request.may_take_focus,
                inbound_token=(
                    secrets.token_urlsafe(32) if request.kind is TriggerKind.INBOUND else None
                ),
            )

            if trigger.is_scheduled:
                await self._scheduler.schedule(trigger)

            await uow.triggers.add(trigger)
            await uow.commit()

        return trigger

    async def _for_a_question(self, ctx: RequestContext, request: NewTrigger) -> Trigger:
        if request.skill_id or request.workflow_id:
            raise TriggerRefused("a trigger that asks a question runs nothing: name neither")
        if request.kind is not TriggerKind.WATCH:
            raise TriggerRefused("only a watch asks a question: it is read out of a mail")
        if request.watch is None or not any(
            value.name == QUESTION for value in request.watch.values
        ):
            raise TriggerRefused(
                f"a watch that asks needs a {QUESTION!r} value: where in the mail the question is"
            )

        trigger = Trigger(
            id=self._ids.new_trigger_id(),
            tenant_id=ctx.tenant_id,
            kind=TriggerKind.WATCH,
            asks=True,
            created_by=ctx.principal_id,
            created_at=self._clock.now(),
            watch=request.watch,
            device_id=request.device_id,
            medium=request.medium,
            writes=False,
            requires_confirmation=False,
            may_take_focus=request.may_take_focus,
        )
        async with self._uow as uow:
            await uow.triggers.add(trigger)
            await uow.commit()
        return trigger

    async def _for_a_job(
        self, ctx: RequestContext, request: NewTrigger, *, parameters: dict[str, str]
    ) -> Trigger:
        async with self._uow as uow:
            workflow = await uow.workflows.get(ctx.tenant_id, str(request.workflow_id))
            if request.kind is TriggerKind.ARRIVAL and request.arrival is None:
                raise TriggerRefused("an arrival trigger needs the page it fires on")
            on_steel = self._start_run is not None and self._start_run.runs_on_steel(ctx)
            seen_in_a_browser = request.kind in (TriggerKind.ARRIVAL, TriggerKind.WATCH)
            if request.device_id is None and (seen_in_a_browser or not on_steel):
                raise TriggerRefused("a job runs in a browser: name a device")
            if not request.authorized_by:
                raise TriggerRefused(
                    "a job drives a real browser through real work, so a trigger for one "
                    "must be authorised"
                )

            declared = {
                str(parameter["name"]) for parameter in workflow.parameters if parameter.get("name")
            }
            supplied = request.watch.reads if request.watch else request.from_message
            if unknown := sorted(set(supplied) - declared):
                raise TriggerRefused(
                    f"this job has no {', '.join(unknown)} for a message to supply"
                )
            if (
                missing := sorted(
                    name for name in declared if name not in parameters and name not in supplied
                )
            ) and not self._can_gather:
                raise TriggerRefused(
                    f"this job needs {', '.join(missing)}: supply a value, "
                    "or say that a message will"
                )

            trigger = Trigger(
                id=self._ids.new_trigger_id(),
                tenant_id=ctx.tenant_id,
                workflow_id=workflow.id,
                kind=request.kind,
                created_by=ctx.principal_id,
                created_at=self._clock.now(),
                parameters=parameters,
                from_message=request.from_message,
                arrival=request.arrival,
                watch=request.watch,
                cron=request.cron,
                timezone=request.timezone,
                device_id=request.device_id,
                medium=request.medium,
                writes=True,
                authorized_by=ctx.principal_id,
                requires_confirmation=not request.auto_approve,
                may_take_focus=request.may_take_focus,
                inbound_token=(
                    secrets.token_urlsafe(32) if request.kind is TriggerKind.INBOUND else None
                ),
            )
            if trigger.is_scheduled:
                await self._scheduler.schedule(trigger)
            await uow.triggers.add(trigger)
            await uow.commit()
        return trigger
