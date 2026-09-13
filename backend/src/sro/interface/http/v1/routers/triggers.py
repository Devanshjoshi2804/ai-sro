"""Putting a task on a clock, and taking it off one."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.application.trigger.create_trigger import NewTrigger
from sro.domain.shared.identifiers import DeviceId, SkillId, TriggerId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    ChangeTriggerRequest,
    FiredModel,
    NewTriggerRequest,
    TriggerModel,
)

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_trigger(
    body: NewTriggerRequest, container: ContainerDep, ctx: ContextDep
) -> TriggerModel:
    """Everything refusable is refused now rather than at three in the morning.

    A skill that has never been rehearsed, a value nobody supplied, a write with
    nobody's name behind it: all of them answer here, to the person who can do
    something about it, weeks before the first firing.

    `skill_id` or `workflow_id`, never both. The second is a job the rig mined,
    which until now could be started by a person accepting an offer in their
    own browser and by nothing else.
    """
    trigger = await container.create_trigger().execute(
        ctx,
        NewTrigger(
            skill_id=SkillId(body.skill_id) if body.skill_id else None,
            workflow_id=body.workflow_id,
            kind=body.kind,
            cron=body.cron,
            timezone=body.timezone,
            parameters=body.parameters,
            from_message=tuple(body.from_message),
            watch=body.watch.to_domain() if body.watch else None,
            device_id=DeviceId(body.device_id) if body.device_id else None,
            medium=body.medium,
            authorized_by=body.authorized_by,
            auto_approve=body.auto_approve,
            may_take_focus=body.may_take_focus,
        ),
    )
    return TriggerModel.of(trigger)


@router.get("")
async def list_triggers(
    container: ContainerDep,
    ctx: ContextDep,
    skill_id: Annotated[str | None, Query()] = None,
) -> list[TriggerModel]:
    triggers = await container.read_triggers().execute(
        ctx, skill_id=SkillId(skill_id) if skill_id else None
    )
    return [TriggerModel.of(trigger) for trigger in triggers]


@router.get("/{trigger_id}")
async def get_trigger(trigger_id: str, container: ContainerDep, ctx: ContextDep) -> TriggerModel:
    trigger = await container.read_triggers().one(ctx, trigger_id=TriggerId(trigger_id))
    return TriggerModel.of(trigger)


@router.patch("/{trigger_id}")
async def change_trigger(
    trigger_id: str, body: ChangeTriggerRequest, container: ContainerDep, ctx: ContextDep
) -> TriggerModel:
    """Pausing removes the schedule rather than letting it fire into a check."""
    trigger = await container.set_trigger_enabled().execute(
        ctx, trigger_id=TriggerId(trigger_id), enabled=body.enabled, reason=body.reason
    )
    return TriggerModel.of(trigger)


@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trigger(trigger_id: str, container: ContainerDep, ctx: ContextDep) -> None:
    await container.delete_trigger().execute(ctx, trigger_id=TriggerId(trigger_id))


@router.post("/{trigger_id}/fire", status_code=status.HTTP_202_ACCEPTED)
async def fire_trigger(trigger_id: str, container: ContainerDep, ctx: ContextDep) -> FiredModel:
    """Do it now, with the trigger's own values and its own authorisation.

    The read first is the ownership check: firing takes no context, because a
    schedule has no caller, so the tenant has to be proved here instead.
    """
    trigger = await container.read_triggers().one(ctx, trigger_id=TriggerId(trigger_id))
    fired = await container.fire_trigger().execute(trigger.id)
    return FiredModel(
        trigger_id=fired.trigger_id.value,
        run_id=fired.run_id.value if fired.run_id else None,
        confirmation_id=fired.confirmation_id.value if fired.confirmation_id else None,
        skipped=fired.skipped,
    )
