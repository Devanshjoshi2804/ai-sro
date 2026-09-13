"""Tasks the system noticed, and what an operator does about them."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.domain.observation.candidate import WORTH_OFFERING
from sro.domain.shared.identifiers import CandidateId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    AnswerJoinRequest,
    DismissCandidateRequest,
    TaskCandidateModel,
    TaughtModel,
    TaughtTogetherModel,
    TeachTogetherRequest,
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


@router.post("/{candidate_id}/teach-together", status_code=status.HTTP_202_ACCEPTED)
async def teach_together(
    candidate_id: str,
    body: TeachTogetherRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> TaughtTogetherModel:
    """One skill from the two candidates a person has said are one job.

    Each time the operator did both halves in a row is one demonstration of the
    whole thing, and two of those are what the induction diffs -- never the two
    candidates against each other, which would compare the WMS half with the ERP
    half and call the difference a parameter.
    """
    taught = await container.teach_workflow().execute(
        ctx,
        first_id=CandidateId(candidate_id),
        second_id=CandidateId(body.other_id),
    )
    return TaughtTogetherModel(
        first_id=taught.first_id.value,
        second_id=taught.second_id.value,
        recording_ids=[recording.value for recording in taught.recording_ids],
        skill_id=taught.skill_id.value if taught.skill_id else None,
        needs_demonstration=taught.needs_demonstration,
        because=taught.because,
    )


@router.post("/{candidate_id}/joins")
async def answer_join(
    candidate_id: str,
    body: AnswerJoinRequest,
    container: ContainerDep,
    ctx: ContextDep,
) -> TaskCandidateModel:
    """Say what two candidates are to each other.

    The line `docs/15-observation-to-tasks.md` draws: a model may notice that
    two look like one piece of work and say why, and a person decides whether
    they are. Answering `same` about a variant dismisses the other as a
    duplicate of this one, naming it -- kept rather than deleted, so the miner
    does not offer it again next week as though it were new.
    """
    answered = await container.answer_join().execute(
        ctx,
        candidate_id=CandidateId(candidate_id),
        other_id=CandidateId(body.other_id),
        kind=body.kind,
        answer=body.answer,
    )
    return TaskCandidateModel.of(answered)


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
