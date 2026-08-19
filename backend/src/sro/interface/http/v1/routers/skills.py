"""Skill endpoints: induce from two recordings, review, promote."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.domain.shared.identifiers import RecordingId, SkillId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    ChoiceModel,
    DescribeRequest,
    InduceSkillRequest,
    InductionResponse,
    PromoteRequest,
    SkillDetail,
    SkillSummary,
    SkillVersionModel,
    UnderstandRequest,
    UnderstoodResponse,
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


@router.post("/induct", status_code=status.HTTP_201_CREATED)
async def induce_skill(
    body: InduceSkillRequest, container: ContainerDep, ctx: ContextDep
) -> InductionResponse:
    """Two runs to one skill version.

    Runs through Temporal rather than in the request: a failed induction keeps a
    history worth reading, and a retry starts from the sealed recordings rather
    than from a browser session nobody can reproduce. The caller still waits --
    induction takes milliseconds -- but the work is not lost if this process is.
    """
    induced = await container.durable.induce_skill(
        ctx,
        first=RecordingId(body.first_recording_id),
        second=RecordingId(body.second_recording_id) if body.second_recording_id else None,
        name=body.name,
    )
    return InductionResponse(
        skill_id=induced.skill_id.value,
        version=induced.version,
        step_count=induced.step_count,
        input_parameter_count=induced.input_parameter_count,
        derived_parameter_count=induced.derived_parameter_count,
    )


@router.post("/understand", status_code=status.HTTP_201_CREATED)
async def understand_recording(
    body: UnderstandRequest, container: ContainerDep, ctx: ContextDep
) -> UnderstoodResponse:
    """One demonstration to a skill.

    The two-run diff proves which values vary; this reads a single run instead,
    and says so: the calls are evidence, the description and the parameters are
    a model's reading of them, and every parameter it proposes is checked
    against a literal in the captured payloads before it survives.
    """
    understood = await container.understand_recording().execute(
        ctx, recording_id=RecordingId(body.recording_id), name=body.name
    )
    return UnderstoodResponse(
        skill_id=understood.skill_id.value,
        version=understood.version,
        step_count=understood.step_count,
        proposed_parameter_count=understood.proposed_parameter_count,
        caveat=understood.caveat,
    )


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


@router.post("/{skill_id}/promote")
async def promote_skill(
    skill_id: str, body: PromoteRequest, container: ContainerDep, ctx: ContextDep
) -> SkillVersionModel:
    version = await container.promote_skill().execute(
        ctx,
        skill_id=SkillId(skill_id),
        version=body.version,
        to=body.to,
        acknowledging_fixed_values=body.acknowledging_fixed_values,
    )
    return SkillVersionModel.of(version)
