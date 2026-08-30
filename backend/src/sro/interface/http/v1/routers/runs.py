"""Run a skill, and read what happened.

The caller waits, but the work is durable underneath: a run is a workflow with
one activity per step, so a process that dies halfway resumes at the next step
rather than starting a second attempt at a warehouse it has already changed.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecutionRequest
from sro.container import Container
from sro.domain.execution.run import Medium, Run, RunId
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    BatchItemModel,
    BatchRequest,
    BatchResultModel,
    RunModel,
    RunSkillRequest,
)
from sro.interface.http.v1.routers.authorising import authorising

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


@router.post("/skills/{skill_id}/runs", status_code=status.HTTP_201_CREATED)
async def run_skill(
    skill_id: str, body: RunSkillRequest, container: ContainerDep, ctx: ContextDep
) -> RunModel:
    """Perform the skill at L1.

    What the stage means here: `shadow` sends every read and withholds every
    write, producing the exact request it would have sent. Above shadow the
    writes go out, and somebody is on the record for that.

    Who, is the authenticated caller -- never a name in the body. A request
    that says who authorised it is a signature nobody checked, and the audit
    trail on a warehouse write is worth more than that.
    """
    request = ExecutionRequest(
        skill_id=SkillId(skill_id),
        parameters=body.parameters,
        version=body.version,
        authorized_by=authorising(body.authorized_by, ctx),
        medium=Medium(body.medium),
        device_id=DeviceId(body.device_id) if body.device_id else None,
        may_take_focus=body.may_take_focus,
    )

    if request.device_id is not None:
        # Performed here rather than handed to the worker, because the browser
        # this run needs is a laptop. Durability across a restart would mean
        # resuming into a Chrome that may be closed, on a page that has moved,
        # halfway through a task -- and a step that has already been recorded as
        # sent must never be sent again to find out.
        #
        # Answered as soon as the row exists, though, rather than when the last
        # step lands. A run in somebody's own browser is the one a person sits
        # and watches, and they could not: the id arrived with the result, so
        # `/runs/{id}/stream` had nothing to subscribe to until there was
        # nothing left to see.
        started = await container.execute_skill().begin(ctx, request)
        container.pursuits.spawn(_perform(container, ctx, started))
        return RunModel.of(started)

    run_id = await container.durable.execute_skill(
        ctx,
        skill_id=SkillId(skill_id),
        parameters=body.parameters,
        version=body.version,
        authorized_by=authorising(body.authorized_by, ctx),
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
        authorized_by=authorising(body.authorized_by, ctx),
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


async def _perform(container: Container, ctx: RequestContext, run: Run) -> None:
    """Drive a run whose caller has already been answered.

    Nobody is awaiting this, so nobody would see it raise. A `DomainError` mid-
    run would leave the row saying `running` for as long as the process lived,
    and the console watching it would count the seconds forever. Whatever goes
    wrong, the run is ended saying so.
    """
    try:
        await container.execute_skill().resume(ctx, run)
    except Exception as error:
        logger.exception("a run in an operator's browser could not be finished")
        try:
            await container.finish_run().execute(ctx, run_id=run.id, stopped=str(error))
        except Exception:
            logger.exception("and its row could not be closed either")
