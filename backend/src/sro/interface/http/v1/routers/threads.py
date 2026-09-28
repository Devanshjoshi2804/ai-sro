"""Chat. A thread decides; starting a run is a separate, deliberate request."""

from __future__ import annotations

import uuid
from dataclasses import replace

from fastapi import APIRouter, status

from sro.application.execution.execute_skill import ExecutionRequest
from sro.application.execution.pursue_goal import Unauthorised
from sro.application.execution.pursuits import PursuitProgress, PursuitState
from sro.application.intent.pursue import compose
from sro.domain.chat.thread import ThreadId
from sro.domain.execution.run import Medium, RunId
from sro.domain.observation.attempts import DONE, NOTHING
from sro.domain.shared.errors import Conflict, InvariantViolation, NotFound
from sro.domain.shared.identifiers import SkillId
from sro.interface.http.deps import AboutThread, ContainerDep, ContextDep
from sro.interface.http.schemas import (
    PursueRequest,
    PursuitProgressModel,
    RunSkillRequest,
    SayRequest,
    ThreadDetail,
    ThreadSummary,
)
from sro.interface.http.v1.routers.authorising import authorising

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_thread(container: ContainerDep, ctx: ContextDep) -> ThreadDetail:
    return ThreadDetail.of_thread(await container.start_thread().execute(ctx))


@router.get("")
async def list_threads(container: ContainerDep, ctx: ContextDep) -> list[ThreadSummary]:
    threads = await container.read_threads().list(ctx)
    return [ThreadSummary.of(thread) for thread in threads]


@router.get("/current")
async def current_thread(container: ContainerDep, ctx: ContextDep) -> ThreadDetail:
    """The conversation this operator is in, made if they are not in one yet.

    The panel needs "the thread", not a list to guess from -- one continuous
    conversation per operator, across every tab they have open, not one per
    host.

    Declared before `/{thread_id}` in this file: FastAPI matches routes in
    declaration order, and below that one, `current` is read as a thread id
    and answers 404 instead of resolving here.

    `ReadThreads.current` only reads; when this operator has nothing running,
    starting one is `StartThread`'s job -- done here, once, rather than taught
    to a reader as a second way for a thread to come into being.
    """
    thread = await container.read_threads().current(ctx)
    if thread is None:
        thread = await container.start_thread().execute(ctx)
    return ThreadDetail.of_thread(thread)


@router.post(
    "/{thread_id}/runs",
    status_code=status.HTTP_201_CREATED,
    dependencies=[AboutThread],
)
async def run_from_thread(
    thread_id: str, body: RunSkillRequest, container: ContainerDep, ctx: ContextDep
) -> ThreadDetail:
    """Start a run and write it into the conversation that asked for it.

    The same run as `/v1/skills/{id}/runs`, kept where it belongs: an operator
    who filled in a card and pressed the button has had a conversation, and a
    result that lives only in the browser's memory is gone on the next render.

    409 when the caller did not open the thread, checked before any run
    starts: a run written into somebody else's thread stands over their offer.
    """
    if not body.skill_id:
        raise InvariantViolation("a run started from a thread must name a skill_id")
    await container.converse().may_start(ctx, thread_id=ThreadId(thread_id))
    skill_id = SkillId(body.skill_id)
    skill = await container.get_skill().execute(ctx, skill_id=skill_id)
    await container.start_run().check(
        ctx,
        ExecutionRequest(
            skill_id=skill_id,
            parameters=body.parameters,
            version=body.version,
            medium=Medium(body.medium),
        ),
    )
    run_id = container.ids.new_run_id()
    await container.durable.execute_skill(
        ctx,
        skill_id=skill_id,
        parameters=body.parameters,
        version=body.version,
        authorized_by=ctx.principal_id.value if body.authorized_by else None,
        medium=body.medium,
        run_id=run_id,
        wait=False,
    )
    thread = await container.converse().started(
        ctx, thread_id=ThreadId(thread_id), run_id=run_id, skill=skill
    )
    return ThreadDetail.of_thread(thread)


@router.get("/{thread_id}", dependencies=[AboutThread])
async def get_thread(thread_id: str, container: ContainerDep, ctx: ContextDep) -> ThreadDetail:
    thread = await container.read_threads().get(ctx, thread_id=ThreadId(thread_id))
    return ThreadDetail.of_thread(thread)


@router.post(
    "/{thread_id}/pursue",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[AboutThread],
)
async def pursue(
    thread_id: str, body: PursueRequest, container: ContainerDep, ctx: ContextDep
) -> PursuitProgressModel:
    """Say go: work a task out on the screen, when nobody has demonstrated it.

    Accepted rather than performed. A pursuit is twelve gestures long, each one
    a screenshot to a hosted model and back, and running it inside this request
    held the whole API until it finished -- which is not a slow endpoint, it is
    an outage with a good excuse. What comes back is an address to watch.

    409 when the caller did not open the thread, checked before anything is
    driven: the pursuit's note is written into this thread when it ends.
    """
    await container.converse().may_start(ctx, thread_id=ThreadId(thread_id))
    if (busy := container.pursuits.working()) is not None:
        raise Conflict(
            f"a pursuit is already working on {busy.goal!r}; there is one browser, "
            "so this would drive the same screen. Wait for it or stop it first"
        )
    pursuit_id = f"pur_{uuid.uuid4().hex}"
    goal = replace(compose(body.intent, None), start_url=body.start_url)
    if goal.changes_the_system and not body.authorized_by:
        raise Unauthorised(
            "this would change the warehouse. Confirm it first: a pursuit has no "
            "demonstration behind it, so your say-so is the only thing between a "
            "model's reading of a screen and a real write"
        )
    progress = container.pursuits.start(pursuit_id, goal.intent, tenant_id=ctx.tenant_id.value)

    async def drive() -> None:
        try:
            pursued = await container.pursue_goal().execute(
                ctx,
                goal=goal,
                target_system=body.target_system,
                values=body.values,
                authorized_by=authorising(body.authorized_by, ctx),
                watching=progress.gestures.append,
                using=lambda session_id: setattr(progress, "session_id", session_id),
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
            await container.converse().note(
                ctx, thread_id=ThreadId(thread_id), text=_pursuit_note(progress)
            )

    container.pursuits.spawn(drive())
    return PursuitProgressModel.of(progress)


@router.get("/{thread_id}/pursue/{pursuit_id}", dependencies=[AboutThread])
async def pursuit_progress(
    thread_id: str, pursuit_id: str, container: ContainerDep, ctx: ContextDep
) -> PursuitProgressModel:
    """What it has done so far. Polled while the browser is being driven."""
    progress = container.pursuits.get(pursuit_id)
    if progress is None or progress.tenant_id != ctx.tenant_id.value:
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


@router.post("/{thread_id}/messages", dependencies=[AboutThread])
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
        run_id=RunId(body.run_id) if body.run_id else None,
        answering=body.answering,
    )
    last = thread.messages[-1] if thread.messages else None
    decided = str((last.decision or {}).get("kind") or "") if last else ""
    await container.record_attempt().execute(
        ctx,
        asked_for="say something in a conversation",
        came_of=DONE if decided else NOTHING,
        why="" if decided else "nothing was made of what was said",
        about={"thread": thread_id, "run": body.run_id or ""},
    )
    return ThreadDetail.of_thread(thread)
