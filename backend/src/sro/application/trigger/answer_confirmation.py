"""Somebody answering a fire that was waiting for them.

The run starts here rather than when the trigger went off, and it starts with
the name of whoever pressed the button. That is the whole point of the queue:
an unattended write happens because a person said so, minutes or hours later,
and the record says which person.

Nothing in this file starts anything on its own. `Sweep` marks the ones nobody
answered as expired, and expiring runs nothing -- a write that happened because
everybody was on holiday is the failure the ladder exists to prevent.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.ports.dispatch import RunDispatcher
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.trigger.fire_trigger import start_for
from sro.domain.execution.run import RunId
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import ConfirmationId
from sro.domain.trigger.confirmation import Answer, Confirmation


@dataclass(frozen=True, slots=True)
class Answered:
    confirmation_id: ConfirmationId
    answer: Answer
    run_id: RunId | None = None


class AnswerConfirmation:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        ids: IdFactory,
        durable: DurableExecution,
        dispatcher: RunDispatcher | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._durable = durable
        self._dispatcher = dispatcher

    async def approve(self, ctx: RequestContext, *, confirmation_id: ConfirmationId) -> Answered:
        """Yes: run it, with this person's name on the run.

        The values are the ones frozen when it was asked. Re-reading the
        trigger here would let a change made in between turn a yes to one thing
        into a yes to another, and the person who pressed the button would
        carry the name on it.
        """
        now = self._clock.now()
        async with self._uow as uow:
            waiting = await uow.confirmations.get(ctx.tenant_id, confirmation_id)
            _refuse_unless_still_askable(waiting, now)

            trigger = await uow.triggers.get(ctx.tenant_id, waiting.trigger_id)
            if not trigger.enabled:
                # Switched off between the fire and the answer. Approving it
                # now would run a task somebody has since decided to stop.
                raise InvariantViolation(
                    f"this trigger was disabled after it fired: "
                    f"{trigger.disabled_reason or 'no reason given'}"
                )

            skill = await uow.skills.get(ctx.tenant_id, waiting.skill_id)
            version = skill.runnable
            if version is None:
                raise InvariantViolation("this skill has no version that may run")

            # The same start a fire uses, rather than a second one beside it.
            # This called `execute_skill` directly and quietly dropped the
            # trigger's `device_id`, so a card for a task bound to the
            # operator's own browser drove a browser this deployment owns --
            # and failed to attach to a CDP endpoint nobody was listening on,
            # with the card already marked approved. Found by pressing the
            # button.
            #
            # `authorized_by` is the person who answered, not the person who
            # made the trigger: an unattended write happens because somebody
            # said so, and this is the somebody.
            run_id = await start_for(
                ctx,
                trigger,
                version=version.version,
                values=dict(waiting.values),
                durable=self._durable,
                ids=self._ids,
                dispatcher=self._dispatcher,
                authorized_by=ctx.principal_id.value,
            )
            waiting.approve(ctx.principal_id, now, run_id)
            trigger.fired(now, run_id)
            await uow.confirmations.save(waiting)
            await uow.triggers.save(trigger)
            await uow.commit()

        return Answered(confirmation_id, Answer.APPROVED, run_id)

    async def decline(
        self, ctx: RequestContext, *, confirmation_id: ConfirmationId, note: str = ""
    ) -> Answered:
        """No. Kept rather than deleted: a card somebody turned down is the
        clearest evidence there is about a trigger that should not exist."""
        now = self._clock.now()
        async with self._uow as uow:
            waiting = await uow.confirmations.get(ctx.tenant_id, confirmation_id)
            _refuse_unless_still_askable(waiting, now)
            waiting.decline(ctx.principal_id, now, note)
            await uow.confirmations.save(waiting)
            await uow.commit()
        return Answered(confirmation_id, Answer.DECLINED)


class ReadConfirmations:
    """What is waiting, oldest first."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> tuple[Confirmation, ...]:
        async with self._uow as uow:
            return await uow.confirmations.waiting(ctx.tenant_id)


class ExpireConfirmations:
    """Mark the ones nobody answered, so a screen can say so.

    `Confirmation.waiting_at` already refuses a late answer on read, so this
    changes nothing about what may run -- it is what turns "not answered yet"
    into "nobody looked", which is a different thing to read a month later and
    the only one worth changing how a team works over.
    """

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, ctx: RequestContext) -> int:
        now = self._clock.now()
        expired = 0
        async with self._uow as uow:
            for waiting in await uow.confirmations.waiting(ctx.tenant_id):
                if now >= waiting.expires_at:
                    waiting.expire(now)
                    await uow.confirmations.save(waiting)
                    expired += 1
            await uow.commit()
        return expired


def _refuse_unless_still_askable(waiting: Confirmation, now: datetime) -> None:
    """The domain object holds both rules; this is where they are asked.

    Kept as a call rather than inlined twice, because approve and decline have
    to refuse for the same reasons -- a decline recorded against something that
    already ran would read as somebody having stopped it.
    """
    if not waiting.waiting_at(now):
        if waiting.answer is not Answer.WAITING:
            raise InvariantViolation(f"this was already {waiting.answer}")
        raise InvariantViolation(
            "this expired without an answer; nothing was run and nothing can be now"
        )
