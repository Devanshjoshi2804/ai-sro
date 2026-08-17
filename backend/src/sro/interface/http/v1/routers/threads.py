"""Chat. A thread decides; starting a run is a separate, deliberate request."""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, status

from sro.application.intent.pursue import compose
from sro.domain.chat.thread import ThreadId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    PursuedResponse,
    PursueRequest,
    SayRequest,
    ThreadDetail,
    ThreadSummary,
)

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_thread(container: ContainerDep, ctx: ContextDep) -> ThreadDetail:
    return ThreadDetail.of_thread(await container.start_thread().execute(ctx))


@router.get("")
async def list_threads(container: ContainerDep, ctx: ContextDep) -> list[ThreadSummary]:
    threads = await container.read_threads().list(ctx)
    return [ThreadSummary.of(thread) for thread in threads]


@router.get("/{thread_id}")
async def get_thread(thread_id: str, container: ContainerDep, ctx: ContextDep) -> ThreadDetail:
    thread = await container.read_threads().get(ctx, thread_id=ThreadId(thread_id))
    return ThreadDetail.of_thread(thread)


@router.post("/{thread_id}/pursue")
async def pursue(
    thread_id: str, body: PursueRequest, container: ContainerDep, ctx: ContextDep
) -> PursuedResponse:
    """Say go: work a task out on the screen, when nobody has demonstrated it.

    The rung of last resort, and the one with the least behind it -- so it is
    reached only after the operator has read the goal and the values, and said
    to go ahead.
    """
    goal = compose(body.intent, None)
    pursued = await container.pursue_goal().execute(
        ctx,
        goal=replace(goal, start_url=body.start_url or goal.start_url),
        target_system=body.target_system,
        values=body.values,
    )
    return PursuedResponse(
        goal=pursued.goal,
        reached=pursued.reached,
        gestures=list(pursued.gestures),
        landed_at=pursued.landed_at,
        detail=pursued.detail,
    )


@router.post("/{thread_id}/messages")
async def say(
    thread_id: str, body: SayRequest, container: ContainerDep, ctx: ContextDep
) -> ThreadDetail:
    """Say something and get the whole thread back, decision included.

    Nothing is performed here. A matched skill is offered; starting it is the
    operator's next request, and that is what makes their confirmation the
    authorisation an assisted run records.
    """
    thread = await container.converse().execute(
        ctx,
        thread_id=ThreadId(thread_id),
        text=body.text,
        system=body.system,
        parameters=body.parameters,
    )
    return ThreadDetail.of_thread(thread)
