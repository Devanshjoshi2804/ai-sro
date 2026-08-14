"""Turn a sentence into a decision. No run starts here."""

from __future__ import annotations

from fastapi import APIRouter

from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import ResolutionModel, ResolveIntentRequest

router = APIRouter(prefix="/intent", tags=["intent"])


@router.post("/resolve")
async def resolve_intent(
    body: ResolveIntentRequest, container: ContainerDep, ctx: ContextDep
) -> ResolutionModel:
    """What was asked for, and whether anything can honestly perform it.

    Deliberately separate from starting a run: an operator confirms a match
    before a write goes out, and that confirmation is what an assisted run
    records as its authorisation.
    """
    resolution = await container.resolve_intent().execute(
        ctx,
        utterance=body.utterance,
        system=body.system,
        parameters=body.parameters,
    )
    return ResolutionModel.of(resolution)
