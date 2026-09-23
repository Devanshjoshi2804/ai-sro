"""Watching a run happen, rather than waiting for it to be over.

A twelve-second run used to be a spinner: the request stayed open until the
last step, and everything the operator might have wanted to see -- the read
that answered, the write that was withheld, the step that failed and why --
arrived at once or not at all.

The run row already grows a step at a time, because each step is committed as
it completes. So this watches that row and sends what is new. No queue, no
broker, no second copy of the truth: the thing being streamed is the same
record the run is stored in, which is also why a reconnecting browser catches
up instead of missing what it slept through.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from sro.application.context import RequestContext
from sro.container import Container
from sro.domain.execution.run import RunId, RunStatus
from sro.domain.shared.errors import NotFound
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import RunModel

router = APIRouter(prefix="/runs", tags=["runs"])

LOOK_EVERY = 0.4
"""How often the row is re-read. Fast enough that a step appears as it lands,
slow enough that a run nobody is watching costs nothing."""

GIVE_UP_AFTER = 15 * 60
"""A run still going after this is not going to finish while somebody watches."""

WAIT_FOR_THE_ROW = 3.0
"""How long a run may take to appear before this gives up on it.

The workflow starts the row a moment after the caller is told the id, so a
short wait is right. Waiting indefinitely is not: a run id belonging to another
tenant is a row this caller will never see, and the stream sat open for fifteen
minutes rather than saying so."""


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, container: ContainerDep, ctx: ContextDep) -> StreamingResponse:
    """Server-sent events: one per step as it completes, then the finished run.

    Events are `step`, `waiting` and `done`. A client that arrives late gets
    every step so far immediately, because what is sent is derived from the row
    rather than from what happened to be published while it was connected.

    `waiting` is the exception: it is a fact about right now rather than about
    the row, and it is sent only when it changes. A client that arrives during a
    pause is told about it on the next tick.
    """
    return StreamingResponse(
        _events(container, ctx, RunId(run_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _events(container: Container, ctx: RequestContext, run_id: RunId) -> AsyncIterator[str]:
    sent = 0
    waited = 0.0
    looked_for = 0.0
    held: bool | None = None
    while waited < GIVE_UP_AFTER:
        try:
            run = await container.get_run().execute(ctx, run_id=run_id)
        except NotFound:
            looked_for += LOOK_EVERY
            if looked_for > WAIT_FOR_THE_ROW:
                yield _event(
                    "gone",
                    {"id": run_id.value, "detail": "no run with that id belongs to you"},
                )
                return
            await asyncio.sleep(LOOK_EVERY)
            waited += LOOK_EVERY
            continue

        model = RunModel.of(run)
        for step in model.steps[sent:]:
            yield _event("step", step.model_dump(mode="json"))
        sent = len(model.steps)

        if run.status is not RunStatus.RUNNING:
            yield _event("done", model.model_dump(mode="json"))
            return

        if run.device_id is not None:
            seconds = await container.agents().held_for(ctx.tenant_id, run.device_id)
            if (seconds is not None) != held:
                held = seconds is not None
                yield _event(
                    "waiting",
                    {
                        "index": len(model.steps),
                        "held_ms": None if seconds is None else round(seconds * 1000),
                    },
                )

        await asyncio.sleep(LOOK_EVERY)
        waited += LOOK_EVERY

    yield _event("done", {"id": run_id.value, "status": "running", "steps": []})


def _event(name: str, payload: dict[str, object]) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, default=str)}\n\n"
