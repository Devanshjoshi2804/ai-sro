"""Chat. A thread decides; starting a run is a separate, deliberate request."""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.domain.chat.thread import ThreadId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import SayRequest, ThreadDetail, ThreadSummary

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
