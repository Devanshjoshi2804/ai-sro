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
from sro.domain.trigger.watch import QUESTION, Watch


class TriggerRefused(DomainError):
    """This trigger will not be created, and the reason is about the skill or
    the authority rather than about the request being malformed."""

    code = "trigger_refused"


@dataclass(frozen=True, slots=True)
class NewTrigger:
    skill_id: SkillId | None = None
    workflow_id: str | None = None
    """What this will run. Exactly one, refused below rather than by an
    `InvariantViolation` from `Trigger` -- a caller naming both deserves a
    sentence about it, not a 500."""

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

    asks: bool = False
    """This watch asks a question rather than running anything. No skill and no
    job, because there is nothing to name: the mail carries a question and the
    answer is somewhere in the systems the operator works in."""


class CreateTrigger:
    def __init__(self, uow: UnitOfWork, clock: Clock, ids: IdFactory, scheduler: Scheduler) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._scheduler = scheduler

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

        assert request.skill_id is not None  # noqa: S101 - checked directly above
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

    async def _for_a_question(self, ctx: RequestContext, request: NewTrigger) -> Trigger:
        """A watch that asks rather than runs.

        The checks a job trigger makes are all about the thing it runs, and
        there is nothing here to check them against: no version to have earned
        a stage, no parameters to be missing, no write to authorise. What is
        left is what this kind can get wrong -- being asked of a browser that
        is not there, or being given no question to ask -- and the second is
        `Trigger`'s own invariant, checked here so a caller reads a sentence
        rather than a 500.
        """
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
            # Neither, and both for the same reason: a read writes nothing, so
            # there is no write to authorise and no card to ask anybody for.
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
        """A trigger on a mined job.

        The checks are the ones this moment knows and a later one cannot. The
        job exists and is proven -- an offer is never made for an unproven one,
        so a schedule must not be the way round that. It runs in a browser,
        because a workflow is a recording of somebody's own window and there is
        no headless path for one. And every parameter it declares has a value,
        from the trigger or from whatever fires it: `StartWorkflowRun` refuses
        a job with one left blank, which for a schedule means failing at 3am
        every night instead of being refused once, now, in front of a person.

        `writes` is True for a job and is not computed from its steps. It is a
        standing authority to drive somebody's browser through a recording of
        real work, and the honest reading of that is "this changes things" --
        so it needs a name behind it. What decides whether the write actually
        goes out unattended is not this flag at all: it is `earned`, three live
        runs whose every write a state belt verified, checked per run.
        """
        async with self._uow as uow:
            workflow = await uow.workflows.get(ctx.tenant_id, str(request.workflow_id))
            if workflow.unproven:
                raise TriggerRefused("this job is not proven yet: " + "; ".join(workflow.unproven))
            if request.kind is TriggerKind.WATCH:
                # The browser evaluates a watch and offers what it matched, and
                # that path (`/v1/agents/{id}/watches/{trigger}/matched`) reads
                # a skill's inputs to say what the mail did not name. Refused
                # rather than half-built: a watch that fired into a job nothing
                # could describe would be a card with no sentence on it.
                raise TriggerRefused("a job cannot be watched for yet: schedule it instead")
            if request.device_id is None:
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
            if missing := sorted(
                name for name in declared if name not in parameters and name not in supplied
            ):
                # Every declared parameter is required: `StartWorkflowRun`
                # refuses a press that leaves one blank, because the planner
                # would otherwise fall back to the value the RECORDING happened
                # to contain and do the job with somebody else's client code.
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
                # Before the commit, for the reason the skill path gives: a
                # schedule for a trigger that was never stored fires once and
                # removes itself, and a stored trigger with no schedule is a
                # task somebody believes is covered and is not.
                await self._scheduler.schedule(trigger)
            await uow.triggers.add(trigger)
            await uow.commit()
        return trigger
