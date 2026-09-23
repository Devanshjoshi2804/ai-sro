"""Runs of mined workflows: start one, list them, read one, stop one, approve one.

Ported from `start_run`, `runs` and `read_run` in
`new_agent_arch/src/rig/api.py:1021`, `:1152` and `:1217`.

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

*If you are looking for where the rig's `/v1/runs` went, all three are here.*

Nothing here catches a refusal: `sro.interface.http.errors` maps them once, for
every route -- `AskerUnavailable` to 503, `OverCap` to 429, `Conflict` to 409,
`NotFound` to 404 and `RunRefused` to the rig's own 400.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from sro.application.chat.from_the_mail import SERVER
from sro.domain.observation.attempts import DONE, NOTHING
from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.asking import AskingDeviceDep
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    StartWorkflowRunRequest,
    WorkflowRunModel,
    WorkflowStepApprovedModel,
)

router = APIRouter(tags=["workflow-runs"])
"""The tenant's credential and nothing else, which is the rig's own gate
(`dependencies=[Depends(authorised)]`) and deliberately NOT `/v1/chat`'s
`TenantOnly`.

Chat refuses a browser proving itself because a browser's secret opens its own
doors and not the tenant's purse. A press is different in the one way that
matters: pressing start is exactly what a browser does, and so is reading back
what it started. The extension sends `X-Device-Secret` on every call it makes,
and `asking_device` answers a secret with no `?device_id=` beside it with a 404
-- so `TenantOnly` here would refuse the one caller these doors exist for, on
every one of them. Which browser to drive is a body field, as it is in the rig,
and the tenant's browsers are the tenant's to drive.

`approve` is the one door here that reads a browser, and it reads it with
`asking_device` rather than as a gate. It is the only one that lets a withheld
warehouse write out, and a caller that names a browser answers for the run that
browser is driving and no other. The tenant's credential alone still taps: a
supervisor's console has no extension, and `?awaiting=true` exists so anybody
may answer a parked run.

**Phase 5 hand-off, and it is not the 404 an earlier note here claimed.**
`api.js`'s `rigApprove` (`api.js:333-341`) sends `rigHeaders()`, which is
documented as "none of the backend's headers" and omits `X-Device-Secret`
(`api.js:250-257`) -- and it sends no `?device_id=` either. Pointed at this
door unchanged it therefore resolves `asking = None` and gets a **silent 200
with a NULL approver and the 403 never evaluated**: a write let out by nobody,
recorded as let out by nobody, on the door whose entire job is recording who
let it out. That is worse than a 404, because nothing goes red.

The `?device_id=` in `shapes()` is not the precedent to copy either: it is
sent with `rigHeaders()` too, so it is half a pair and `asking_device` answers
it with a 404. **Phase 5 must send BOTH** -- `?device_id=` in the query and
`X-Device-Secret` in the headers.

**Corrected 2026-09-10.** This paragraph used to end "which is what `call()`
plus an explicit query parameter already does for `/v1/offers`". It did not.
`reportOffer` was a raw `fetch` to the *rig* with `rigHeaders()`, sending
neither the secret nor `?device_id=` -- one of the broken calls, not a working
precedent, and the pattern existed nowhere in `api.js`. Phase 5 built it:
`rigApprove` and `reportOffer` are both one `call()` with an explicit
`?device_id=` now, `rigHeaders()` is deleted, and the header rule lives in
`call()` alone -- which is the whole reason a second place to put headers was
what broke this door. Line cites are dropped rather than re-pinned; every one
in this file had drifted by a hunk or more.
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
        items=body.items,
        live=body.live,
        allow_focus=body.allow_focus,
        watched=body.watched,
        from_step=body.from_step,
        matched=body.matched,
        conversation=(SERVER, body.mail_thread),
        undoes_run=body.undoes_run,
    )
    container.pursuits.spawn(starter.perform(ctx, claimed))
    await container.record_attempt().execute(
        ctx,
        asked_for="take back a run" if body.undoes_run else "press a job",
        came_of=DONE,
        about={
            "run": claimed.id,
            "workflow": body.workflow_id,
            "device": body.device_id,
        },
    )
    return WorkflowRunModel.of(claimed)


@router.get("/workflow-runs")
async def list_workflow_runs(
    container: ContainerDep,
    ctx: ContextDep,
    workflow_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
    awaiting: Annotated[bool, Query()] = False,
) -> list[WorkflowRunModel]:
    """The most recent runs, newest first, as one row each.

    Ported from `runs` in `new_agent_arch/src/rig/api.py:1152`, and this keeps
    its order: newest first, capped. That is deliberately not
    `WorkflowRunRepository.for_workflow`'s ascending order -- that one is the
    evidence order `proofs` reads, and its docstring used to cite the rig for
    it, which is exactly backwards. A person opening a list wants what happened
    last at the top.

    **The rows are whole, where the rig sent one line each with the full record
    a `GET` away.** `WorkflowRunModel` is what the press already answers with,
    and a panel that has to make a second request per row to show a parked step
    is a panel that makes twenty.

    That is also how the divergence this plan settles reaches the wire. The rig
    reported the deepest parked step of each run, in an `awaiting` field of its
    own; this reports every parked step, `ord` ascending, in `steps` -- the
    ones with `verdict == "awaiting"`. **Plan 4b's ruling**, written here and on
    `WorkflowRunRepository.awaiting`: anyone may answer a parked run, and a
    queue that hides all but the deepest step hides work from the person who
    could clear it.

    `limit` is validated rather than clamped, which is the one other deviation.
    The rig did `max(1, min(limit, 200))`; a caller that asks for 5000 and
    silently gets 200 cannot tell a cap from a truncated answer, and FastAPI
    says this once, in the place the generated client reads.
    """
    runs = await container.list_workflow_runs().execute(
        ctx, workflow_id=workflow_id, limit=limit, awaiting=awaiting
    )
    return [WorkflowRunModel.of(run) for run in runs]


@router.get("/workflow-runs/{run_id}")
async def get_workflow_run(
    run_id: str, container: ContainerDep, ctx: ContextDep
) -> WorkflowRunModel:
    """One run of a mined job, whole.

    Ported from `read_run` in `new_agent_arch/src/rig/api.py:1217`.

    A run of another tenant is a 404 and never a 403: a 403 confirms the id
    exists, run ids are unguessable, and the answer to "is this yours" must not
    differ from the answer to "does this exist". The repository answers `None`
    for both, `GetWorkflowRun` raises `NotFound`, and `errors` maps it once.
    """
    reader = container.get_workflow_run()
    run = await reader.execute(ctx, run_id=run_id)
    return WorkflowRunModel.of(run, await reader.undo_for(ctx, run))


@router.post("/workflow-runs/{run_id}/abort", status_code=status.HTTP_202_ACCEPTED)
async def abort_workflow_run(
    run_id: str, container: ContainerDep, ctx: ContextDep
) -> WorkflowRunModel:
    """Ask a run of a mined job to stop.

    Ported from `abort_run` in `new_agent_arch/src/rig/api.py:1237`, and it
    closes phase 4a's carried item 1: nothing outside this process could reach
    a parked run to stop it.

    202 rather than 200, as `/v1/runs/{id}/stop` next door is: it takes effect
    at the next step, because a gesture already sent cannot be recalled from a
    warehouse and a stop that ended the run mid-command would report a write as
    not having happened when it had. The row answered with therefore still says
    `running` -- the task driving the browser closes it, and it is the only
    thing that knows how the step it was in the middle of ended.

    **No body**, where the rig's took one naming the browser. The row already
    says which browser is driving it, and a `device_id` in the body is a second
    answer to that question which can disagree with the first. A bare POST is
    also what a tap is: a route that 422s one is a Stop-shaped button that
    sometimes does nothing.

    A run of another tenant is a 404 and never a 403, for `get_workflow_run`'s
    reason. A run that is not `running`, or one naming no browser, is the 409
    `CannotStop` already carries -- it subclasses `Conflict`, so `errors` maps
    it through the MRO walk without a table entry of its own.
    """
    stopped = await container.abort_workflow_run().execute(ctx, run_id=run_id)
    await container.record_attempt().execute(
        ctx, asked_for="stop a run", came_of=DONE, about={"run": run_id}
    )
    return WorkflowRunModel.of(stopped)


@router.post("/workflow-runs/{run_id}/approve")
async def approve_workflow_step(
    run_id: str, container: ContainerDep, ctx: ContextDep, asking: AskingDeviceDep
) -> WorkflowStepApprovedModel:
    """A person saw the write the panel showed and said go.

    Ported from `approve_run` in `new_agent_arch/src/rig/api.py:1270`, and it
    is the precondition on anything ever being pressed live: until this
    existed, a run that parked on a person waited out its five minutes and
    failed however hard anybody tapped. Not `POST /v1/confirmations/{id}/
    approve` next door, which approves a *confirmation*, keyed on the
    confirmation and not on the run.

    **No body**, exactly as `abort` above has none, and one reason further. A
    bare POST is what a tap is and a route that 422s one is a Stop-shaped
    button that sometimes does nothing; and the browser that tapped is the one
    that proved itself, so a `device_id` in a body would be a name nobody
    checked written into the row an audit reads first. That is the ruling
    `StartWorkflowRunRequest` already made about `started_by`. The rig had to
    rank a token's own device above the body's claim; here there is no claim to
    rank it against.

    **`asking` is why this door alone reads a browser.** `AbortWorkflowRun`
    needs none -- it stops the run whoever asks -- but this one lets a
    warehouse write out, and a caller that names a browser answers for the run
    that browser is driving and no other. So a tap FROM a browser must send
    `?device_id=` and `X-Device-Secret` together, as `/v1/shapes` and
    `/v1/offers` require; half a pair is `asking_device`'s usual 404. The
    tenant's own credential with neither names no browser and may answer a
    parked run, as anyone may -- that is a supervisor's console, which has no
    extension of its own. See the module docstring for what that check is and
    is not, and for what phase 5 has to change to reach it.

    200 and not 202: unlike the stop next door, this has already happened by
    the time it answers. The row naming who let the write out is committed, and
    the wait is released.

    `resumed` says whether there was a wait to release. False means the
    authorisation is recorded and the run will not move, because the process
    holding it is gone or its five minutes ran out -- the case an operator hit
    for real, tapping Approve on a login step and watching nothing happen. Not
    a refusal, because the tap did authorise the write; a panel that reads it
    can say the true thing instead of "approved" and silence.

    A run of another tenant is a 404 and never a 403, for `get_workflow_run`'s
    reason. A run with nothing parked on a person is a 409 `Conflict`, and a
    browser reaching for a run it is not driving is `NotDrivingThisRun`, a 403.
    """
    order, first, resumed = await container.approve_workflow_step().execute(
        ctx, run_id=run_id, asking=asking
    )
    await container.record_attempt().execute(
        ctx,
        asked_for="approve a step",
        came_of=DONE if resumed else NOTHING,
        why="" if resumed else "that step had already been let out",
        about={"run": run_id, "device": asking.value if asking else ""},
    )
    return WorkflowStepApprovedModel(order=order, first=first, resumed=resumed)
