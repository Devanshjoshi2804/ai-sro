"""Chat. A thread decides; starting a run is a separate, deliberate request."""

from __future__ import annotations

import uuid
from dataclasses import replace

from fastapi import APIRouter, status

from sro.application.execution.execute_skill import ExecutionRequest
from sro.application.execution.pursuits import PursuitProgress, PursuitState
from sro.application.intent.pursue import compose
from sro.domain.chat.thread import ThreadId
from sro.domain.execution.run import Medium
from sro.domain.shared.errors import Conflict, InvariantViolation, NotFound
from sro.domain.shared.identifiers import SkillId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    PursueRequest,
    PursuitProgressModel,
    RunSkillRequest,
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


@router.post("/{thread_id}/runs", status_code=status.HTTP_201_CREATED)
async def run_from_thread(
    thread_id: str, body: RunSkillRequest, container: ContainerDep, ctx: ContextDep
) -> ThreadDetail:
    """Start a run and write it into the conversation that asked for it.

    The same run as `/v1/skills/{id}/runs`, kept where it belongs: an operator
    who filled in a card and pressed the button has had a conversation, and a
    result that lives only in the browser's memory is gone on the next render.
    """
    if not body.skill_id:
        # Caught here, before any workflow starts: without this, a missing
        # skill_id started a durable run against no skill at all, and the only
        # sign of it was a 404 from the *next* line -- one whose real cause was
        # already off running as an orphaned workflow.
        raise InvariantViolation("a run started from a thread must name a skill_id")
    skill_id = SkillId(body.skill_id)
    # Read before the workflow starts, not after: a skill id that names nothing
    # answered 404 from below while the workflow it had already scheduled went
    # off to fail on its own, out of sight of the request that caused it.
    skill = await container.get_skill().execute(ctx, skill_id=skill_id)
    # Refused here or not at all. This answers before the run begins, so a
    # refusal raised inside the workflow -- a skill at a stage that may not run,
    # a breaker asking for a person -- reached nobody: the request had already
    # answered 201 with the id of a run that was never created, and the console
    # sat on "opening the connection" for a run that had been stopped on
    # purpose.
    await container.start_run().check(
        ctx,
        ExecutionRequest(
            skill_id=skill_id,
            parameters=body.parameters,
            version=body.version,
            medium=Medium(body.medium),
        ),
    )
    # Named before it starts, so the console can watch the steps land instead
    # of holding this request open for as long as the warehouse takes.
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
    # One screen, one pursuit. The provider behind this deployment has a single
    # browser, so a second pursuit does not get a second screen -- it drives the
    # same one, mid-task, and both navigate it out from under each other. Two
    # pursuits then report, separately and truthfully, that the screen would not
    # respond to anything they did.
    if (busy := container.pursuits.working()) is not None:
        raise Conflict(
            f"a pursuit is already working on {busy.goal!r}; there is one browser, "
            "so this would drive the same screen. Wait for it or stop it first"
        )
    pursuit_id = f"pur_{uuid.uuid4().hex}"
    goal = replace(compose(body.intent, None), start_url=body.start_url)
    progress = container.pursuits.start(pursuit_id, goal.intent, tenant_id=ctx.tenant_id.value)

    async def drive() -> None:
        try:
            pursued = await container.pursue_goal().execute(
                ctx,
                goal=goal,
                target_system=body.target_system,
                values=body.values,
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
