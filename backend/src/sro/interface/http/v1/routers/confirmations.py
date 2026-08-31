"""Fires waiting for somebody to say yes.

A manual trigger needs none of this -- the click that fires it is the
confirmation. A schedule and an inbound message both go off with nobody there,
and until this existed a write on one of those could not be created at all.

Nothing here starts a run because time passed. Approving one does, with the
name of whoever approved it on the run; declining records that somebody said
no; and an item nobody answered expires, which runs nothing.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.domain.shared.identifiers import ConfirmationId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import AnsweredModel, ConfirmationModel, DeclineRequest

router = APIRouter(prefix="/confirmations", tags=["confirmations"])


@router.get("")
async def list_confirmations(container: ContainerDep, ctx: ContextDep) -> list[ConfirmationModel]:
    """What is waiting, oldest first.

    The skill's name comes along because the card is read by somebody deciding,
    and an id is not something anybody decides about.
    """
    waiting = await container.read_confirmations().execute(ctx)
    named: list[ConfirmationModel] = []
    for confirmation in waiting:
        skill = await container.get_skill().execute(ctx, skill_id=confirmation.skill_id)
        named.append(ConfirmationModel.of(confirmation, skill_name=skill.name))
    return named


@router.post("/{confirmation_id}/approve")
async def approve(confirmation_id: str, container: ContainerDep, ctx: ContextDep) -> AnsweredModel:
    """Yes -- and the run starts here, with this person's name on it.

    Not the name of whoever created the trigger. An unattended write happens
    because somebody said so, and this is the somebody.
    """
    answered = await container.answer_confirmation().approve(
        ctx, confirmation_id=ConfirmationId(confirmation_id)
    )
    return AnsweredModel(
        confirmation_id=answered.confirmation_id.value,
        answer=answered.answer.value,
        run_id=answered.run_id.value if answered.run_id else None,
    )


@router.post("/{confirmation_id}/decline")
async def decline(
    confirmation_id: str,
    body: DeclineRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> AnsweredModel:
    """No. Kept rather than deleted: a card somebody turned down is the
    clearest evidence there is about a trigger that should not exist."""
    answered = await container.answer_confirmation().decline(
        ctx, confirmation_id=ConfirmationId(confirmation_id), note=body.note
    )
    return AnsweredModel(
        confirmation_id=answered.confirmation_id.value, answer=answered.answer.value
    )
