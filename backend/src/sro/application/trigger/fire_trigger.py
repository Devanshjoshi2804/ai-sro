"""A clock asking for a task to be done.

Nobody is watching, which is what every check here is about. The trigger's
standing authorisation is what a write goes out on; what it runs is re-read
rather than trusted, because a skill may have been re-induced into something
that changes a system since the day somebody put it on a schedule.

Two things a trigger can run, and the difference is where the safety lives. A
SKILL is checked here: `runnable`, `changes_the_system`, `blank_inputs`. A
mined JOB is checked by the run itself -- `run_workflow` is dry until somebody
presses through to live, a live write parks for a person until the job has
`earned` the right by `K_EARNED_RUNS` state-verified runs, and every step is
verified before the next one starts. So the workflow path here is plumbing
rather than a second ladder: what it must not do is invent a weaker one.
"""

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
        start_run: StartWorkflowRun | None = None,
        pursuits: Pursuits | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._durable = durable
        self._ids = ids
        self._dispatcher = dispatcher
        self._scheduler = scheduler
        # `None` in a process that cannot drive a browser, the same shape
        # `dispatcher` already has: a worker with no channel to an extension
        # skips the fire rather than failing to construct.
        self._start_run = start_run
        self._pursuits = pursuits

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
                # The skill was re-induced into something that writes. The
                # authorisation on this trigger was given for a task that did
                # not, and it does not carry over.
                trigger.disable("the skill now changes the system; authorise this trigger again")
                await uow.triggers.save(trigger)
                await uow.commit()
                return Fired(trigger_id, skipped=trigger.disabled_reason)

            if blank := blank_inputs(version, values):
                # A mail that matched the rule but named no order. Every relay
                # sends some of these -- an autoreply, a thread with the number
                # only in an attachment -- and each one would otherwise be a
                # run that starts, asks the warehouse for nothing, and fails.
                # Skipped here, where the reason is still legible.
                return Fired(trigger_id, skipped="nothing said " + ", ".join(blank))

            if trigger.requires_confirmation:
                # Nobody is here.
                asked = await self._ask_a_person(
                    uow, trigger, now=now, values=values, message=message
                )
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

    async def _ask_a_person(
        self,
        uow: UnitOfWork,
        trigger: Trigger,
        *,
        now: datetime,
        values: dict[str, str],
        message: Mapping[str, str] | None,
    ) -> Confirmation:
        """The fire becomes a card instead of a run.

        The values are frozen now rather than re-read when somebody answers:
        what they approve has to be what is written in front of them, and a
        trigger edited in between would turn a yes to one thing into a yes to
        another.

        One helper for both kinds. The card names whichever of the two the
        trigger names, and every other field is the same question -- a second
        copy of this, per kind, is two cards that drift.
        """
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
        """A mined job, started in the operator's own browser.

        Almost nothing is checked here, and that is the point. `run_workflow`
        is dry until somebody presses through to live; a live write parks for a
        person until the job has EARNED the right by `K_EARNED_RUNS` runs whose
        every write a state belt verified; each step is verified before the
        next is sent; and `StartWorkflowRun` itself refuses a job with a
        declared parameter left blank, a job whose evidence has gone, and a
        browser already driving something else. Repeating any of that here
        would be a second ladder that can disagree with the first.

        What IS checked here is what only this call site knows: that the job
        still exists, and that it is one a browser may be offered at all.

        A job runs in a browser or nowhere. There is no headless path for one:
        a workflow is a recording of somebody's own window, and `device_id` is
        how the run reaches it.
        """
        if self._start_run is None and self._dispatcher is None:
            return Fired(trigger.id, skipped="this process cannot start a job")
        if trigger.device_id is None:
            # Refused at creation too. Belt and braces, because a row written
            # before that check existed is still a row.
            trigger.disable("a job runs in a browser: name a device")
            await uow.triggers.save(trigger)
            await uow.commit()
            return Fired(trigger.id, skipped=trigger.disabled_reason)

        workflow = await uow.workflows.get(ctx.tenant_id, str(trigger.workflow_id))
        if workflow.unproven:
            # Mined and not yet trusted. An offer is never made for one, so a
            # schedule must not be the way round that.
            return Fired(
                trigger.id, skipped="this job is not proven: " + "; ".join(workflow.unproven)
            )

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
            # A closed laptop is a `Conflict` out of `StartWorkflowRun`, not a
            # `DispatchFailed`: the job path has no dispatcher, it presses the
            # same door the console does. Raised out of here it would reach the
            # scheduler as a failed activity and be retried all night, which is
            # what the skill path's catch has always existed to prevent -- and
            # a browser being closed is the most ordinary thing there is.
            #
            # `RunRefused` too, and deliberately not a disable: a job whose
            # cited evidence has aged out is refused today and proven again by
            # the next pass that reads those gestures back.
            logger.info("trigger %s did not start its job: %s", trigger.id, refused)
            return Fired(trigger.id, skipped=str(refused))
        # The run is already committed, on its own unit of work, and this is a
        # second transaction. A failure in between leaves a run started and a
        # trigger that does not know it fired, so the next tick fires again;
        # two concurrent ticks both read the pre-`fired` row and both start.
        #
        # Left as two on purpose. Both outcomes are already caught downstream
        # and caught better than a claim here would catch them: the partial
        # unique index on running runs refuses a second run for the same
        # browser, and `tool_calls.remember` refuses the same job's same write
        # with the same values inside half an hour. A claim taken before the
        # start would have to be released on every refusal path above --
        # a closed laptop, an aged-out job -- and a released claim that missed
        # one of them is an arrival trigger that silently drops the mail it
        # was fired for.
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
    if trigger.skill_id is None:
        # `Trigger` names one or the other, and this is the skill half. A job
        # goes to `start_job_for` above, which is not this function's business
        # to reach into -- `FireTrigger` routes on the same field.
        raise DispatchFailed("this trigger runs a job, not a skill")

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
    """Start the mined job a trigger asks for, in the browser it names.

    Module-level for `start_for`'s reason, which is the one that matters most
    here: two callers need this -- a fire, and a card somebody approved -- and
    the second one calling `StartWorkflowRun` itself is how the skill path
    once dropped the trigger's `device_id` and drove the wrong browser.

    Live, always. A dry run of a scheduled job sends nothing and verifies
    nothing; it is a trigger that appears to work. What keeps it safe is not
    dryness, it is the ladder underneath: a live write parks for a person
    until the job has EARNED the right, and `earned` is three runs whose every
    write a state belt saw.

    `allow_focus` is the trigger's own `may_take_focus`, which defaults to off:
    a schedule that fires at 3am has no business taking somebody's screen.

    Claimed and then spawned, exactly as `POST /v1/workflow-runs` does. A fire
    that awaited the whole run would hold a worker's activity slot for its full
    duration -- the same failure `start_for` records above -- and a run nobody
    holds a reference to is one the loop may collect mid-gesture.

    **A dispatcher wins where there is one**, which is `start_for`'s rule and
    exists for the same reason: the socket to that Chrome is held by whichever
    process the extension connected to, and the scheduler's worker is not that
    one. Started in-process there, `StartWorkflowRun` looks for the browser in
    its own empty register and every scheduled job is skipped forever with
    "not connected". `start_run` remains the path for a deployment with no
    dispatcher at all.
    """
    # The name is on the record already: `WorkflowRun.started_by` is the
    # context's principal, which for a fire is the trigger's author and for an
    # approved card is whoever pressed it.
    named = authorized_by or (trigger.authorized_by.value if trigger.authorized_by else None)
    if named is None and trigger.writes:
        # `Trigger` refuses this at creation. A row written before that check
        # existed is still a row, and this is the last place to notice.
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
        # Nothing to hold the task, so it is awaited rather than dropped: a
        # coroutine created and discarded is a run that never happens, and
        # "the trigger fired" would be a lie told with a run id.
        await performing
    else:
        pursuits.spawn(performing)
    return RunId(claimed.id)


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
    # "an arrival trigger fired", not "a arrival trigger fired". The sentence
    # is read by the person deciding whether to let a write out, and one that
    # cannot manage its own article reads as a system that is guessing.
    article = "an" if trigger.kind.value[0] in "aeiou" else "a"
    return f"{article} {trigger.kind} trigger fired"
