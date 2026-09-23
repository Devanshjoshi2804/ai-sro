from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.execution.pursuits import Pursuits
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.ports.dispatch import RunDispatcher
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.trigger.fire_trigger import start_for, start_job_for
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
        start_run: StartWorkflowRun | None = None,
        pursuits: Pursuits | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids
        self._durable = durable
        self._dispatcher = dispatcher
        self._start_run = start_run
        self._pursuits = pursuits

    async def approve(self, ctx: RequestContext, *, confirmation_id: ConfirmationId) -> Answered:
        now = self._clock.now()
        async with self._uow as uow:
            waiting = await uow.confirmations.get(ctx.tenant_id, confirmation_id)
            _refuse_unless_still_askable(waiting, now)

            trigger = await uow.triggers.get(ctx.tenant_id, waiting.trigger_id)
            if not trigger.enabled:
                raise InvariantViolation(
                    f"this trigger was disabled after it fired: "
                    f"{trigger.disabled_reason or 'no reason given'}"
                )

            if waiting.workflow_id is not None:
                if self._start_run is None and self._dispatcher is None:
                    raise InvariantViolation("this process cannot start a job")
                run_id = await start_job_for(
                    ctx,
                    trigger,
                    values=dict(waiting.values),
                    start_run=self._start_run,
                    pursuits=self._pursuits,
                    dispatcher=self._dispatcher,
                    authorized_by=ctx.principal_id.value,
                )
                waiting.approve(ctx.principal_id, now, run_id)
                trigger.fired(now, run_id)
                await uow.confirmations.save(waiting)
                await uow.triggers.save(trigger)
                await uow.commit()
                return Answered(confirmation_id, Answer.APPROVED, run_id)

            assert waiting.skill_id is not None  # noqa: S101 - the invariant Confirmation keeps
            skill = await uow.skills.get(ctx.tenant_id, waiting.skill_id)
            version = skill.runnable
            if version is None:
                raise InvariantViolation("this skill has no version that may run")

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
        now = self._clock.now()
        async with self._uow as uow:
            waiting = await uow.confirmations.get(ctx.tenant_id, confirmation_id)
            _refuse_unless_still_askable(waiting, now)
            waiting.decline(ctx.principal_id, now, note)
            await uow.confirmations.save(waiting)
            await uow.commit()
        return Answered(confirmation_id, Answer.DECLINED)


class ReadConfirmations:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> tuple[Confirmation, ...]:
        async with self._uow as uow:
            return await uow.confirmations.waiting(ctx.tenant_id)


class ExpireConfirmations:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self) -> dict[str, int]:
        now = self._clock.now()
        expired: dict[str, int] = {}
        async with self._uow as uow:
            for tenant_id in await uow.confirmations.tenants_waiting():
                for waiting in await uow.confirmations.waiting(tenant_id):
                    if now >= waiting.expires_at:
                        waiting.expire(now)
                        await uow.confirmations.save(waiting)
                        expired[tenant_id.value] = expired.get(tenant_id.value, 0) + 1
            await uow.commit()
        return expired


def _refuse_unless_still_askable(waiting: Confirmation, now: datetime) -> None:
    if not waiting.waiting_at(now):
        if waiting.answer is not Answer.WAITING:
            raise InvariantViolation(f"this was already {waiting.answer}")
        raise InvariantViolation(
            "this expired without an answer; nothing was run and nothing can be now"
        )
