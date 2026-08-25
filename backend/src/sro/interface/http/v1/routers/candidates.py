"""Tasks the system noticed, and what an operator does about them."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.domain.observation.candidate import WORTH_OFFERING
from sro.domain.shared.identifiers import CandidateId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    DismissCandidateRequest,
    MinedModel,
    TaskCandidateModel,
    TaughtModel,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("")
async def list_candidates(
    container: ContainerDep,
    ctx: ContextDep,
    seen_at_least: Annotated[int, Query(ge=0, le=100)] = WORTH_OFFERING,
    mine_only: Annotated[bool, Query()] = False,
    host: Annotated[str | None, Query(max_length=200)] = None,
) -> list[TaskCandidateModel]:
    """Most often done first.

    The default floor is three: twice is a coincidence and the operator knows
    it, and being asked about coincidences is how a recommendation surface
    starts getting ignored.

    `host` narrows to one system, which is what the extension's side panel asks
    of the tab it is docked beside: "tasks you keep doing *here*" is a different
    question, and one that cannot be answered by filtering a page of results
    that was already cut off somewhere else.
    """
    candidates = await container.read_candidates().execute(
        ctx, seen_at_least=seen_at_least, mine_only=mine_only, host=host
    )
    return [TaskCandidateModel.of(candidate) for candidate in candidates]


@router.post("/mine", status_code=status.HTTP_202_ACCEPTED)
async def mine_now(
    container: ContainerDep,
    ctx: ContextDep,
    hours: Annotated[int, Query(ge=1, le=720)] = 24,
) -> MinedModel:
    """Look at the last few hours now, rather than waiting for the sweep.

    The sweep in the worker is what runs in a deployment; this exists because
    somebody building an extension should not have to wait a quarter of an hour
    to see whether what they captured turns into anything. Idempotent, like the
    sweep: an episode already recorded is not counted twice.
    """
    mined = await container.mine_observations().execute(
        ctx, since=datetime.now(UTC) - timedelta(hours=hours)
    )
    return MinedModel(
        episodes=mined.episodes,
        candidates_seen=mined.candidates_seen,
        candidates_new=mined.candidates_new,
        occurrences_new=mined.occurrences_new,
    )


@router.get("/{candidate_id}")
async def get_candidate(
    candidate_id: str, container: ContainerDep, ctx: ContextDep
) -> TaskCandidateModel:
    candidate = await container.read_candidates().one(ctx, candidate_id=CandidateId(candidate_id))
    return TaskCandidateModel.of(candidate)


@router.post("/{candidate_id}/teach", status_code=status.HTTP_202_ACCEPTED)
async def teach_candidate(
    candidate_id: str, container: ContainerDep, ctx: ContextDep
) -> TaughtModel:
    """Learn it from what was already watched, rather than asking again.

    When the evidence will not induce, this says so and asks for one deliberate
    repetition -- which is a normal part of the flow, not a failure.
    """
    taught = await container.teach_candidate().execute(ctx, candidate_id=CandidateId(candidate_id))
    return TaughtModel(
        candidate_id=taught.candidate_id.value,
        recording_id=taught.recording_id.value if taught.recording_id else None,
        skill_id=taught.skill_id.value if taught.skill_id else None,
        needs_demonstration=taught.needs_demonstration,
        because=taught.because,
    )


@router.post("/{candidate_id}/dismiss")
async def dismiss_candidate(
    candidate_id: str,
    body: DismissCandidateRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> TaskCandidateModel:
    """Kept rather than deleted, so it is not offered again next week as if it
    were new."""
    candidate = await container.dismiss_candidate().execute(
        ctx, candidate_id=CandidateId(candidate_id), reason=body.reason
    )
    return TaskCandidateModel.of(candidate)
