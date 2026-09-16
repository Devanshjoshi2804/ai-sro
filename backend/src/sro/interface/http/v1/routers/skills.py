"""Skill endpoints: induce from two recordings, review, promote."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.application.ports.tools import ToolsUnavailable
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import RecordingId, SkillId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    AssertRequest,
    ChoiceModel,
    DemonstrationModel,
    DescribeRequest,
    InduceSkillRequest,
    InductionResponse,
    MapStepRequest,
    PromoteRequest,
    SkillDetail,
    SkillSummary,
    SkillVersionModel,
    ToolOfferedModel,
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


@router.get("/{skill_id}/doings")
async def get_doings(
    skill_id: str, container: ContainerDep, ctx: ContextDep, version: int | None = None
) -> list[DemonstrationModel]:
    """Every demonstration this version was learned from, and what each one filled in.

    The version stores the values of the two doings it diffed; the rest are
    read back out of their own recorded traffic here. A skill demonstrated ten
    times has ten of these, and a reviewer asked why a field is optional can
    see the doing that left it out.
    """
    doings = await container.read_doings().execute(ctx, skill_id=SkillId(skill_id), version=version)
    return [
        DemonstrationModel(
            recording_id=str(doing.recording_id),
            started_at=doing.started_at,
            demonstrator=str(doing.demonstrator),
            frames=doing.frames,
            diffed=doing.diffed,
            values=doing.values,
        )
        for doing in doings
    ]


@router.get("/tools/{server}")
async def offered_tools(
    server: str, container: ContainerDep, ctx: ContextDep
) -> list[ToolOfferedModel]:
    """What this connector says it has, now.

    Asked by the screen that maps a step onto one, so somebody is choosing from
    what the server actually offers rather than typing a name and finding out
    the first time the skill fires.
    """
    tools = container.tools
    if not tools.available:
        raise NotFound("no connector is configured")
    try:
        offered = await tools.list_tools(ctx.tenant_id, server)
    except ToolsUnavailable as gone:
        raise NotFound(str(gone)) from gone
    return [
        ToolOfferedModel(
            name=tool.name, description=tool.description, arguments=list(tool.arguments)
        )
        for tool in offered
    ]


@router.post("/{skill_id}/steps/tool", status_code=status.HTTP_201_CREATED)
async def map_step_to_tool(
    skill_id: str, body: MapStepRequest, container: ContainerDep, ctx: ContextDep
) -> SkillDetail:
    """Somebody saying: this click is that tool.

    The one part of a skill nobody demonstrates, so it is a decision with a
    name on it. A new version, at the bottom of the ladder -- the step now goes
    through a door nobody has watched it go through, and the streak that would
    let it run unattended has to be earned against the connector rather than
    inherited from the clicks it replaced.
    """
    await container.map_step_to_tool().execute(
        ctx,
        skill_id=SkillId(skill_id),
        version=body.version,
        step_index=body.step_index,
        server=body.server,
        tool=body.tool,
        arguments=body.arguments,
        writes=body.writes,
    )
    skill = await container.get_skill().execute(ctx, skill_id=SkillId(skill_id))
    return SkillDetail.of_skill(skill)


@router.post("/{skill_id}/steps/assertion", status_code=status.HTTP_201_CREATED)
async def add_assertion(
    skill_id: str, body: AssertRequest, container: ContainerDep, ctx: ContextDep
) -> SkillDetail:
    """Somebody saying what counts as this step having worked.

    Post-conditions normally come out of the recordings -- two demonstrations
    answering the same status, or agreeing on a field. A step performed through
    a connector has no such thing behind it, so the only post-condition it can
    have is one a person writes, and a write that proves nothing about its
    result keeps the whole version off the top of the ladder.

    Only ever adds. A check induction derived is what two demonstrations
    agreed on, and an opinion that could delete a measurement is not a
    tightening.
    """
    await container.add_assertion().execute(
        ctx,
        skill_id=SkillId(skill_id),
        version=body.version,
        step_index=body.step_index,
        kind=body.kind,
        expected=body.expected,
        pointer=body.pointer,
    )
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
