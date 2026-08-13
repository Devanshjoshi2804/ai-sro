"""Skill endpoints: induce from two recordings, review, promote."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.domain.shared.identifiers import RecordingId, SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    InduceSkillRequest,
    InductionResponse,
    PromoteRequest,
    SkillDetail,
    SkillSummary,
    SkillVersionModel,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("/induct", status_code=status.HTTP_201_CREATED)
async def induce_skill(
    body: InduceSkillRequest, container: ContainerDep, ctx: ContextDep
) -> InductionResponse:
    """Two runs to one skill version. Runs synchronously: induction is pure
    computation over sealed recordings and takes milliseconds. The durable path
    through Temporal exists for callers that want a retryable handle."""
    induced = await container.induce_skill().execute(
        ctx,
        first=RecordingId(body.first_recording_id),
        second=RecordingId(body.second_recording_id),
        name=body.name,
    )
    return InductionResponse(
        skill_id=induced.skill_id.value,
        version=induced.version,
        step_count=induced.step_count,
        input_parameter_count=induced.input_parameter_count,
        derived_parameter_count=induced.derived_parameter_count,
    )


@router.get("")
async def list_skills(
    container: ContainerDep,
    ctx: ContextDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SkillSummary]:
    uow = container.unit_of_work()
    async with uow as unit:
        skills = await unit.skills.list_for_tenant(ctx.tenant_id, limit=limit, offset=offset)
    return [SkillSummary.of(s) for s in skills]


@router.get("/{skill_id}")
async def get_skill(skill_id: str, container: ContainerDep, ctx: ContextDep) -> SkillDetail:
    uow = container.unit_of_work()
    async with uow as unit:
        skill = await unit.skills.get(ctx.tenant_id, SkillId(skill_id))
    return SkillDetail.of_skill(skill)


@router.post("/{skill_id}/promote")
async def promote_skill(
    skill_id: str, body: PromoteRequest, container: ContainerDep, ctx: ContextDep
) -> SkillVersionModel:
    version = await container.promote_skill().execute(
        ctx,
        skill_id=SkillId(skill_id),
        version=body.version,
        to=PromotionStage(body.to),
    )
    return SkillVersionModel.of(version)
