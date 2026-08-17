"""Chat. A thread decides; starting a run is a separate, deliberate request."""

from __future__ import annotations

import uuid
from dataclasses import replace

from fastapi import APIRouter, status

from sro.application.execution.pursuits import PursuitProgress, PursuitState
from sro.application.intent.pursue import compose
from sro.domain.chat.thread import ThreadId
from sro.domain.shared.errors import NotFound
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    PursueRequest,
    PursuitProgressModel,
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


@router.post("/{thread_id}/pursue", status_code=status.HTTP_202_ACCEPTED)
async def pursue(
    thread_id: str, body: PursueRequest, container: ContainerDep, ctx: ContextDep
) -> PursuitProgressModel:
    """Say go: work a task out on the screen, when nobody has demonstrated it.

    Accepted rather than performed. A pursuit is twelve gestures long, each one
    a screenshot to a hosted model and back, and running it inside this request
    held the whole API until it finished -- which is not a slow endpoint, it is
    an outage with a good excuse. What comes back is an address to watch.
    """
    pursuit_id = f"pur_{uuid.uuid4().hex}"
    goal = replace(compose(body.intent, None), start_url=body.start_url)
    progress = container.pursuits.start(pursuit_id, goal.intent)

    async def drive() -> None:
        try:
            pursued = await container.pursue_goal().execute(
                ctx,
                goal=goal,
                target_system=body.target_system,
                values=body.values,
                watching=progress.gestures.append,
            )
            progress.state = PursuitState.REACHED if pursued.reached else PursuitState.STOPPED
            progress.detail = pursued.detail
            progress.landed_at = pursued.landed_at
            progress.recording_id = pursued.recording_id
            progress.skill_id = pursued.skill_id
        except Exception as error:
            progress.state = PursuitState.FAILED
            progress.detail = str(error)
        finally:
            # The thread outlives the process; the progress does not. What
            # happened has to end up somewhere an operator can read tomorrow.
            await container.converse().note(
                ctx, thread_id=ThreadId(thread_id), text=_pursuit_note(progress)
            )

    container.pursuits.spawn(drive())
    return PursuitProgressModel.of(progress)


@router.get("/{thread_id}/pursue/{pursuit_id}")
async def pursuit_progress(
    thread_id: str, pursuit_id: str, container: ContainerDep, ctx: ContextDep
) -> PursuitProgressModel:
    """What it has done so far. Polled while the browser is being driven."""
    progress = container.pursuits.get(pursuit_id)
    if progress is None:
        raise NotFound(f"no pursuit {pursuit_id} is being driven by this process")
    return PursuitProgressModel.of(progress)


def _pursuit_note(progress: PursuitProgress) -> str:
    lines = [
        f"Worked on the screen: {progress.goal}",
        f"{progress.state} — {progress.detail}" if progress.detail else str(progress.state),
    ]
    lines.extend(f"· {gesture}" for gesture in progress.gestures)
    if progress.skill_id:
        lines.append(
            f"Kept as a skill ({progress.skill_id}) — the same request runs over the API now."
        )
    elif progress.recording_id:
        lines.append(f"Recorded as {progress.recording_id}.")
    return "\n".join(lines)


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
