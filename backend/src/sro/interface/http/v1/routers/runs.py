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
from sro.application.execution.reversal import reversal_for
from sro.container import Container
from sro.domain.execution.run import Medium, Run, RunId, RunStatus
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    BatchItemModel,
    BatchRequest,
    BatchResultModel,
    CalledWrongRequest,
    ReviseRunRequest,
    RunFromPreviewRequest,
    RunModel,
    RunSkillRequest,
)
from sro.interface.http.v1.routers.authorising import authorising

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])

_LIBRARY_PAGE = 200
"""Same number, same reasoning as `_LIBRARY_PAGE` in
`sro.application.intent.resolve`: a tenant's library is dozens, not millions,
so one page holds it. It has to hold it *here* particularly -- a skill that
would undo this run sitting on a page this fetch never asks for is not
"no undo exists", it is an undo the operator cannot tell from one that
doesn't, on the one button whose entire value is being reliable. Same
ponytail note applies: query it once fetching a page stops being enough."""


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


@router.post("/skills/{skill_id}/runs/from-preview", status_code=status.HTTP_201_CREATED)
async def run_from_preview(
    skill_id: str, body: RunFromPreviewRequest, container: ContainerDep, ctx: ContextDep
) -> RunModel:
    """The press. Promotes a version that has never been reviewed anywhere else,
    then runs it. See ADR 014 and `RunFromPreview`.

    Always in the operator's own browser: the preview this promotes on showed
    them the tab the run is about to act in, and a run started anywhere else
    would not be the run they read. Pinned, too, to the version the client says
    it previewed: refused outright where the skill has been taught again since,
    because what the operator read has to be what runs and neither the newer
    version nor the older one is that. That makes this always `run_skill`'s
    device path, followed exactly rather than reinvented: answered as soon as
    the row exists, with the rest driven in the background, because this is a
    run a person is watching happen on their own screen and could not if the
    id only arrived with the result -- `/runs/{id}/stream` would have nothing
    to subscribe to and `/runs/{id}/stop` nothing left to stop.
    """
    started = await container.run_from_preview().begin(
        ctx,
        skill_id=SkillId(skill_id),
        parameters=body.parameters,
        device_id=DeviceId(body.device_id),
        intent=body.intent,
        previewed=body.version,
    )
    container.pursuits.spawn(_perform(container, ctx, started))
    return RunModel.of(started)


@router.post("/runs/{run_id}/stop", status_code=status.HTTP_202_ACCEPTED)
async def stop_run(run_id: str, container: ContainerDep, ctx: ContextDep) -> RunModel:
    """Ask a run in your own browser to stop.

    Accepted rather than done: it takes effect at the next step, because a
    gesture already sent cannot be recalled from a warehouse and a stop that
    ended the run mid-command would report a write as not having happened when
    it had. So this can wait as long as the current step's deadline, and the
    console says so rather than showing a button that appears to do nothing.

    Refused for a run this process is not performing. Answering "stopping" for
    a durable run the worker will finish anyway would be the one thing a stop
    control must never do.
    """
    return RunModel.of(await container.stop_run().execute(ctx, run_id=RunId(run_id)))


@router.post("/runs/{run_id}/wrong", status_code=status.HTTP_202_ACCEPTED)
async def called_wrong(
    run_id: str, body: CalledWrongRequest, container: ContainerDep, ctx: ContextDep
) -> RunModel:
    """The person this ran for says the result was wrong.

    Reached by pressing "undo that" or "it's wrong, I'll fix it" -- things they
    wanted anyway, which is why the answer can be trusted. It counts against the
    skill exactly as a crash does, because the question the ladder is asking is
    "does this still work", and a run that made the wrong record did not.
    """
    run = await container.call_run_wrong().execute(ctx, run_id=RunId(run_id), because=body.because)
    return RunModel.of(run)


@router.post("/runs/{run_id}/values", status_code=status.HTTP_202_ACCEPTED)
async def revise_run(
    run_id: str, body: ReviseRunRequest, container: ContainerDep, ctx: ContextDep
) -> RunModel:
    """Change what the steps still to come will run with.

    Reached from the panel, where a run is drawn a row per step and a step that
    has not been sent yet still shows a way to argue with it. Steps already
    performed keep what they sent; the next one is a fresh read of the run, so
    it renders from what is saved here.

    Accepted rather than OK: the run goes on being performed elsewhere, and
    what this returns is the run as it stands, not the effect of the change.
    """
    run = await container.revise_run().execute(ctx, run_id=RunId(run_id), values=body.values)
    return RunModel.of(run)


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
    reversal = None
    if run.status is RunStatus.SUCCEEDED:
        skills = await container.list_skills().execute(ctx, limit=_LIBRARY_PAGE)
        reversal = reversal_for(run, skills)
    return RunModel.of(run, reversal=reversal)


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
