"""Run a skill, and read what happened.

The caller waits, but the work is durable underneath: a run is a workflow with
one activity per step, so a process that dies halfway resumes at the next step
rather than starting a second attempt at a warehouse it has already changed.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.domain.execution.run import Medium, RunId
from sro.domain.shared.identifiers import SkillId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    BatchItemModel,
    BatchRequest,
    BatchResultModel,
    RunModel,
    RunSkillRequest,
)

router = APIRouter(tags=["runs"])


@router.post("/skills/{skill_id}/runs", status_code=status.HTTP_201_CREATED)
async def run_skill(
    skill_id: str, body: RunSkillRequest, container: ContainerDep, ctx: ContextDep
) -> RunModel:
    """Perform the skill at L1.

    What the stage means here: `shadow` sends every read and withholds every
    write, producing the exact request it would have sent. Above shadow the
    writes go out, and the request must name the human who authorised that.
    """
    run_id = await container.durable.execute_skill(
        ctx,
        skill_id=SkillId(skill_id),
        parameters=body.parameters,
        version=body.version,
        authorized_by=body.authorized_by,
        medium=body.medium,
    )
    return RunModel.of(await container.get_run().execute(ctx, run_id=run_id))


@router.post("/skills/{skill_id}/batch", status_code=status.HTTP_201_CREATED)
async def run_batch(
    skill_id: str, body: BatchRequest, container: ContainerDep, ctx: ContextDep
) -> BatchResultModel:
    """Do the same taught task to several things.

    N runs, each with its own idempotency keys, audit record and verification —
    so one item failing says nothing about the others, and the failure names
    which item it was. A safety limit stops the batch rather than the item.
    """
    result = await container.run_batch().execute(
        ctx,
        skill_id=SkillId(skill_id),
        items=tuple(body.items),
        authorized_by=body.authorized_by,
        version=body.version,
        medium=Medium(body.medium),
    )
    return BatchResultModel(
        items=[
            BatchItemModel(
                parameters=item.parameters,
                run_id=item.run.id.value if item.run else None,
                status=(
                    "refused"
                    if item.refused
                    else (item.run.status.value if item.run else "unknown")
                ),
                detail=item.refused or (item.run.failure if item.run else None),
            )
            for item in result.items
        ],
        performed=result.performed,
        stopped_early=result.stopped_early,
    )


@router.get("/runs")
async def list_runs(
    container: ContainerDep,
    ctx: ContextDep,
    skill_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RunModel]:
    runs = await container.list_runs().execute(
        ctx,
        skill_id=SkillId(skill_id) if skill_id else None,
        limit=limit,
        offset=offset,
    )
    return [RunModel.of(run) for run in runs]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, container: ContainerDep, ctx: ContextDep) -> RunModel:
    run = await container.get_run().execute(ctx, run_id=RunId(run_id))
    return RunModel.of(run)
