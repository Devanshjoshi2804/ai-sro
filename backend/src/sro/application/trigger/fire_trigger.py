"""A clock asking for a task to be done.

Nobody is watching, which is what every check here is about. The trigger's
standing authorisation is what a write goes out on; the skill is re-read rather
than trusted, because it may have been re-induced into something that changes a
system since the day somebody put it on a schedule.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.dispatch import DispatchFailed, RunDispatcher
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.schedule import Scheduler
from sro.application.ports.system import Clock, IdFactory
from sro.domain.execution.run import RunId
from sro.domain.shared.identifiers import ConfirmationId, TriggerId
from sro.domain.skill.skill import SkillVersion
from sro.domain.trigger.confirmation import ANSWER_WITHIN, Confirmation
from sro.domain.trigger.trigger import Trigger

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Fired:
    trigger_id: TriggerId
    run_id: RunId | None = None
    confirmation_id: ConfirmationId | None = None
    """Set where nothing was started because somebody has to say yes first.

    Beside ``run_id`` rather than instead of it, and neither is a failure: a
    fire that became a card is the trigger working exactly as its author asked
    it to."""

    skipped: str | None = None
    """Why nothing was started. Not an error: a disabled trigger and a skill
    that has stopped being runnable are both ordinary, and a scheduler that
    treated them as failures would retry them all night."""


class FireTrigger:
    """The only thing a schedule calls.

    Takes no ``RequestContext``: there is no request and no caller. The tenant
    and the principal come off the trigger, which is why the repository's
    ``find`` is the one tenant-blind read in the system.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        durable: DurableExecution,
        *,
        ids: IdFactory,
        dispatcher: RunDispatcher | None = None,
        scheduler: Scheduler | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._durable = durable
        self._ids = ids
        self._dispatcher = dispatcher
        self._scheduler = scheduler

    async def execute(
        self, trigger_id: TriggerId, *, message: Mapping[str, str] | None = None
    ) -> Fired:
        """Fire it.

        `message` is what a mail relay or a watching browser said. Only the
        names this trigger declared it would take are read from it; everything
        else it runs with is what it was created with.
        """
        async with self._uow as uow:
            trigger = await uow.triggers.find(trigger_id)
            if trigger is None:
                # A schedule that outlived its trigger. It removes itself rather
                # than firing into nothing every hour until somebody notices.
                await self._forget(trigger_id)
                return Fired(trigger_id, skipped="no such trigger")
            if not trigger.enabled:
                return Fired(trigger_id, skipped=trigger.disabled_reason or "disabled")

            ctx = RequestContext(tenant_id=trigger.tenant_id, principal_id=trigger.created_by)
            skill = await uow.skills.get(ctx.tenant_id, trigger.skill_id)
            version = skill.runnable
            if version is None:
                trigger.disable("the skill has no version that may run")
                await uow.triggers.save(trigger)
                await uow.commit()
                return Fired(trigger_id, skipped=trigger.disabled_reason)

            if version.changes_the_system and not trigger.writes:
                # The skill was re-induced into something that writes. The
                # authorisation on this trigger was given for a task that did
                # not, and it does not carry over.
                trigger.disable("the skill now changes the system; authorise this trigger again")
                await uow.triggers.save(trigger)
                await uow.commit()
                return Fired(trigger_id, skipped=trigger.disabled_reason)

            now = self._clock.now()
            values = trigger.values_from(message or {})
            if blank := blank_inputs(version, values):
                # A mail that matched the rule but named no order. Every relay
                # sends some of these -- an autoreply, a thread with the number
                # only in an attachment -- and each one would otherwise be a
                # run that starts, asks the warehouse for nothing, and fails.
                # Skipped here, where the reason is still legible.
                return Fired(trigger_id, skipped="nothing said " + ", ".join(blank))

            if trigger.requires_confirmation:
                # Nobody is here. The fire becomes a card instead of a run, and
                # the values on it are frozen now rather than re-read when
                # somebody answers -- what they approve has to be what is
                # written in front of them, and a trigger edited in between
                # would turn a yes to one thing into a yes to another.
                asked = Confirmation(
                    id=self._ids.new_confirmation_id(),
                    tenant_id=trigger.tenant_id,
                    trigger_id=trigger.id,
                    skill_id=trigger.skill_id,
                    asked_at=now,
                    expires_at=now + ANSWER_WITHIN,
                    values=values,
                    because=_because(trigger, message),
                )
                await uow.confirmations.add(asked)
                trigger.fired(now, None)
                await uow.triggers.save(trigger)
                await uow.commit()
                return Fired(trigger_id, confirmation_id=asked.id)

            try:
                run_id = await self._start(ctx, trigger, version=version.version, values=values)
            except DispatchFailed as unreachable:
                # A laptop that is closed. Ordinary, and not a reason to stop
                # the trigger: it will be open again before the next one.
                logger.info("trigger %s could not reach its browser: %s", trigger_id, unreachable)
                return Fired(trigger_id, skipped=str(unreachable))

            trigger.fired(now, run_id)
            await uow.triggers.save(trigger)
            await uow.commit()

        return Fired(trigger_id, run_id=run_id)

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
    """Start the run a trigger asks for, at the rung it asks for.

    Module-level because two callers need it and they must not disagree. A fire
    starts a run here; a confirmation somebody approved starts one too, and the
    second used to call `execute_skill` directly -- which quietly dropped the
    trigger's `device_id` and drove a browser this deployment owns instead of
    the operator's own. The run then failed to attach to a CDP endpoint nobody
    was listening on, and the card had already been marked approved.

    ``authorized_by`` overrides the trigger's, because an approved card runs
    under the name of whoever pressed the button rather than whoever made the
    trigger.
    """
    named = authorized_by or (trigger.authorized_by.value if trigger.authorized_by else None)

    if trigger.device_id is None:
        # Named before it starts, the same reason the console does this --
        # `wait=False` alone is not fire-and-forget: the durable adapter's
        # fast path only takes it once a run id is already there to
        # return, and without one every fire blocked a worker activity
        # slot for the run's full duration regardless of the flag.
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

    # The channel to that browser is held by whichever process the extension
    # connected to, and this is not that process.
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
        # Whether this fire may move the operator's tab. A schedule that runs
        # at 3am has no business taking a screen, and a trigger the operator
        # set up to watch may.
        may_take_focus=trigger.may_take_focus,
    )


def blank_inputs(version: SkillVersion, values: Mapping[str, str]) -> list[str]:
    """The values this skill needs that nothing supplied.

    Public because the offer a watch turns into has to say the same thing
    before the press rather than after it: a card that starts a run which then
    fails teaches nobody. One definition, so the sentence on the card and the
    reason for the skip cannot come to disagree.

    A parameter present but empty counts: a relay's template renders
    `{{order}}` to nothing at all when the mail did not hold one, and an empty
    string reaches a run as a value rather than as an absence.

    Optional ones do not. A demonstration proved the record is created without
    that field, and `execute_skill` sends the absent form it actually sent, so
    a mail that named no Delta Priority is not a mail that named nothing --
    it is one doing what the operator who skipped that box did.
    """
    return sorted(p.name for p in version.inputs if not values.get(p.name, "").strip())


def _because(trigger: Trigger, message: Mapping[str, str] | None) -> str:
    """The one sentence somebody reads before deciding.

    A subject where a mail carried one, because that is what the person
    approving actually recognises. Otherwise what kind of trigger this was --
    which is thin, and thin is better than a sentence this code invented about
    a message it did not read.
    """
    said = dict(message or {})
    for name in ("subject", "title", "summary"):
        if said.get(name):
            return said[name][:200]
    return f"a {trigger.kind} trigger fired"
