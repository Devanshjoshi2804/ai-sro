"""The press, from outside the process: start a run of a mined workflow.

Ported from `start_run` in `new_agent_arch/src/rig/api.py:1021`.

**Why not `/v1/runs`, which is where the rig put this.** `/v1/runs`,
`/v1/runs/{run_id}`, `/v1/runs/{run_id}/stop` and `/v1/runs/{run_id}/values`
already exist on this host and already mean something else: a *skill* run,
`sro.domain.execution.run.Run`, keyed on a `RunId`. The rig's `/v1/runs` means a
*workflow* run, `sro.domain.execution.workflow_run.WorkflowRun`, keyed on a
plain `str`. Two aggregates, two id spaces, one path -- and a router that
served both would have to guess which id space a string belongs to on every
request.

The extension already lives with the collision from the other side: `api.js:178`
calls `/v1/runs/{id}` on the backend's base url and `api.js:192` calls the
byte-identical path on the rig's, told apart by a mirrored `source` field.
Phase 7 deletes the rig and both bases become one host, which is the moment the
collision would have become unresolvable. So: **`/v1/workflow-runs`**, and the
spec's "same paths and bodies so the extension changes only its base URL" is
knowingly not kept here. That is the one deviation and this is where it is
written down.

Not `/v1/workflows/runs` either, which would make a workflow whose id is
literally `runs` a live ambiguity with `/v1/workflows/{workflow_id}`.

*If you are looking for where the rig's `POST /v1/runs` went, this is it.*

Nothing here catches a refusal: `sro.interface.http.errors` maps them once, for
every route -- `AskerUnavailable` to 503, `OverCap` to 429, `Conflict` to 409,
`NotFound` to 404 and `RunRefused` to the rig's own 400.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import StartWorkflowRunRequest, WorkflowRunModel

router = APIRouter(tags=["workflow-runs"])
"""The tenant's credential and nothing else, which is the rig's own gate
(`dependencies=[Depends(authorised)]`) and deliberately NOT `/v1/chat`'s
`TenantOnly`.

Chat refuses a browser proving itself because a browser's secret opens its own
doors and not the tenant's purse. A press is different in the one way that
matters: pressing start is exactly what a browser does. The extension sends
`X-Device-Secret` on every call it makes, and `asking_device` answers a secret
with no `?device_id=` beside it with a 404 -- so `TenantOnly` here would refuse
the one caller this door exists for. Which browser to drive is a body field, as
it is in the rig, and the tenant's browsers are the tenant's to drive.
"""


@router.post("/workflow-runs", status_code=status.HTTP_201_CREATED)
async def start_workflow_run(
    body: StartWorkflowRunRequest, container: ContainerDep, ctx: ContextDep
) -> WorkflowRunModel:
    """Start one run of a mined job, and answer with the row it claimed.

    201 and the whole row, where the rig answered 202 and `{"run_id": ...}`.
    The row exists and is committed by the time this returns -- that is the
    whole point of claiming it here -- so 201 is what happened, and a caller
    that has to poll for what it just created to learn which browser and which
    step it got is a caller that cannot show the operator anything yet.

    Answered as soon as the row exists rather than when the last step lands,
    exactly as `run_skill`'s device path is: this is a run a person sits and
    watches happen in their own browser, and they could not if the id only
    arrived with the result.

    `container.pursuits.spawn`, not a bare `create_task`: a task nobody holds
    is a task the loop may collect mid-gesture, which would leave a browser
    open on a half-filled form. `perform` catches everything and closes the row
    itself -- nobody is awaiting this, so a run left `running` would be swept
    only by `fail_orphans` at the next process start, which is a restart away
    and not a moment away.
    """
    starter = container.start_workflow_run()
    claimed = await starter.execute(
        ctx,
        workflow_id=body.workflow_id,
        device_id=DeviceId(body.device_id),
        values=body.values,
        live=body.live,
        allow_focus=body.allow_focus,
        from_step=body.from_step,
    )
    container.pursuits.spawn(starter.perform(ctx, claimed))
    return WorkflowRunModel.of(claimed)
