"""Putting a task on a clock.

Everything that can be refused is refused here rather than at three in the
morning: a skill that has never earned a stage that may run, values the skill
declares and nobody supplied, a write with nobody's name on it. A trigger that
exists is a trigger that would work.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.schedule import Scheduler
from sro.application.ports.system import Clock, IdFactory
from sro.domain.execution.run import Medium
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.trigger.trigger import Trigger, TriggerKind
from sro.domain.trigger.watch import Watch


class TriggerRefused(DomainError):
    """This trigger will not be created, and the reason is about the skill or
    the authority rather than about the request being malformed."""

    code = "trigger_refused"


@dataclass(frozen=True, slots=True)
class NewTrigger:
    skill_id: SkillId
    kind: TriggerKind = TriggerKind.SCHEDULE
    cron: str | None = None
    timezone: str = "UTC"
    parameters: dict[str, str] | None = None
    from_message: tuple[str, ...] = ()
    """Parameters a message that fires this may name -- an order number in a
    mail. Everything not listed here is fixed at creation, so a relay cannot
    point a warehouse read at another facility."""

    watch: Watch | None = None
    """What makes a mail one of these, for a trigger the operator's own browser
    evaluates. The names it reads are its `from_message`; there is no second
    list to keep in step."""

    device_id: DeviceId | None = None
    medium: Medium = Medium.NETWORK
    authorized_by: bool = False
    """Whether the caller is standing behind every run this will start. The
    name comes from their credential, never from the request."""

    auto_approve: bool = False
    may_take_focus: bool = False


class CreateTrigger:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory, scheduler: Scheduler) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._scheduler = scheduler

    async def execute(self, ctx: RequestContext, request: NewTrigger) -> Trigger:
        parameters = dict(request.parameters or {})

        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, request.skill_id)
            version = skill.runnable
            if version is None:
                raise TriggerRefused(
                    "this skill has no version that may run yet; it has never been rehearsed"
                )

            # A watch names the values it supplies by where it reads them out
            # of the mail. One list, checked the same way -- a value pointed at
            # a parameter this skill does not have is the same silent typo.
            supplied = request.watch.reads if request.watch else request.from_message

            declared = {parameter.name for parameter in version.parameters}
            if unknown := sorted(set(supplied) - declared):
                # A typo here is silent otherwise: the mail's value is dropped
                # for having the wrong name, and the trigger fires with nothing
                # every time until somebody reads a run.
                raise TriggerRefused(
                    f"this skill has no {', '.join(unknown)} for a message to supply"
                )

            missing = sorted(
                parameter.name
                for parameter in version.inputs
                if parameter.name not in parameters and parameter.name not in supplied
            )
            if missing:
                # A trigger with a value missing fails every single time it
                # fires, and nobody is watching when it does.
                raise TriggerRefused(
                    f"this skill needs {', '.join(missing)}: supply a value, "
                    "or say that a message will"
                )

            writes = version.changes_the_system
            if writes and not request.authorized_by:
                raise TriggerRefused(
                    "this skill changes the system, so a trigger for it must be authorised"
                )
            # A write that fires with nobody there used to be refused outright,
            # because there was nowhere to ask. There is now: the fire becomes
            # a card in `confirmations` and the run starts when somebody
            # answers it, with their name on it. `auto_approve` remains the
            # other honest answer -- a named person saying in advance that this
            # one need not be asked about.

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
                # Before the commit, deliberately. A schedule for a trigger that
                # was never stored fires once, finds nothing, and removes
                # itself; a stored trigger with no schedule is a task somebody
                # believes is covered and is not.
                await self._scheduler.schedule(trigger)

            await uow.triggers.add(trigger)
            await uow.commit()

        return trigger
