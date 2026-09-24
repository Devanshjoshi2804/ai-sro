"""Skill endpoints: list, read, describe."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from sro.domain.shared.identifiers import SkillId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    ChoiceModel,
    DescribeRequest,
    SkillDetail,
    SkillSummary,
    SkillVersionModel,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/{skill_id}/choices/{parameter}")
async def choices(
    skill_id: str,
    parameter: str,
    container: ContainerDep,
    ctx: ContextDep,
    q: str = "",
    version: int | None = None,
) -> list[ChoiceModel]:
    """What this field's dropdown holds, from the system, now.

    The field was a dropdown when the task was taught, and it stays one: the
    console fills it from the endpoint the screen used rather than asking an
    operator to type back an id. Fetched live on every open, because a list of
    what used to exist is a way of writing to a record that no longer does.
    """
    found = await container.list_choices().execute(
        ctx, skill_id=SkillId(skill_id), parameter=parameter, version=version, like=q
    )
    return [ChoiceModel(value=choice.value, label=choice.label) for choice in found]


@router.get("")
async def list_skills(
    container: ContainerDep,
    ctx: ContextDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SkillSummary]:
    skills = await container.list_skills().execute(ctx, limit=limit, offset=offset)
    return [SkillSummary.of(s) for s in skills]


@router.get("/{skill_id}")
async def get_skill(skill_id: str, container: ContainerDep, ctx: ContextDep) -> SkillDetail:
    skill = await container.get_skill().execute(ctx, skill_id=SkillId(skill_id))
    return SkillDetail.of_skill(skill)


@router.post("/{skill_id}/describe")
async def describe_skill(
    skill_id: str, body: DescribeRequest, container: ContainerDep, ctx: ContextDep
) -> SkillVersionModel:
    """Reword what the skill is for. Changes what finds it, never what it does."""
    version = await container.describe_skill().execute(
        ctx,
        skill_id=SkillId(skill_id),
        version=body.version,
        summary=body.summary,
        when_to_use=body.when_to_use,
    )
    return SkillVersionModel.of(version)
