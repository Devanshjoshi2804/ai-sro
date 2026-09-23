"""The jobs this tenant has, and the evidence underneath one of them.

Ported from `new_agent_arch/src/rig/api.py:812` and `:904`. Two routes with
two different doors, which is the whole of this module:

`GET /v1/workflows` is authorised -- a browser holding its own secret may ask,
as it may ask `/v1/shapes` beside it. It is the menu of jobs that browser
could be offered, and prose about a job is not a fact about anybody's day.

`GET /v1/workflows/{id}/evidence` is tenant-only. What a workflow cites is
every browser's gestures: what somebody typed, where they clicked, the calls
their page made. Two browsers sharing a workflow is the normal case -- that is
what a mined job IS -- so serving the evidence to a browser's secret would
hand one operator another's afternoon through a job they happen to have in
common. One is a menu; the other is somebody's day.

The dependency is on the evidence route and not on the router, unlike
`audit.py` and `spend.py` next door, because these two routes disagree about
it. That is how the rig declares it too -- per route, at the decorator -- and
a second router in this module to hold one dependency would put the two
halves of one door in two objects `app.py` has to remember to keep together.

`?device_id=` with `X-Device-Secret` is validated on the listing even though
the listing does not vary by browser. `asking_device` is what refuses a
bogus id or a half pair, and `/v1/shapes` -- the sibling this module compares
itself to -- refuses both. A query parameter checked on one route and silently
ignored on the next door along is a caller told its browser was accepted when
nothing looked; the listing serves the tenant's menu either way, so the only
thing dropping the dependency bought was that inconsistency. The pair is
refused at the evidence route instead by `tenant_only`, with a 403 rather than
a 404: the caller is holding a tenant credential that was accepted, so this is
not an enumeration channel.

Nothing here catches a domain error: `sro.interface.http.errors` maps them
once, for every route. A workflow this tenant does not have is the
repository's `NotFound` and reaches a caller as a 404 -- never as an empty
list, which would tell them their bridge is fine and their job is empty.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.application.skill.retire_workflow import RetireWorkflow
from sro.interface.http.asking import AskingDeviceDep, TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    EvidenceResponse,
    LearnedChangesResponse,
    WorkflowsResponse,
)

router = APIRouter(tags=["workflows"])


@router.get("/workflows")
async def workflows(
    container: ContainerDep, ctx: ContextDep, asking: AskingDeviceDep
) -> WorkflowsResponse:
    """Every workflow this tenant has mined, with what has become of each.

    `asking` is not read: the menu is the tenant's and does not vary by
    browser. It is here to be refused -- a `?device_id=` this tenant does not
    have, or one named without its secret, is a 404 here exactly as it is at
    `/v1/shapes`. See the module docstring.
    """
    del asking
    return WorkflowsResponse.of(await container.read_workflows().execute(ctx))


@router.post(
    "/workflows/{workflow_id}/retire",
    dependencies=[TenantOnly],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def retire_workflow(container: ContainerDep, ctx: ContextDep, workflow_id: str) -> None:
    """Retire a job: it stops being offered, listed or run, for good.

    The row and its citations stay. Deleting it would hand its gestures back
    to the miner, which would read them into a fresh copy of the job the
    operator just dropped -- so a retired job's evidence stays placed, and the
    job stays retired.

    A job this tenant does not have, or has already retired, is a 404.
    Tenant-only: which jobs a deployment keeps is not a browser's decision.
    """
    await RetireWorkflow(container.unit_of_work(), container.clock).execute(
        ctx, workflow_id=workflow_id
    )


@router.get("/workflows/{workflow_id}/taught", dependencies=[TenantOnly])
async def what_the_job_taught_itself(
    container: ContainerDep, ctx: ContextDep, workflow_id: str
) -> LearnedChangesResponse:
    """What this job has changed its mind about, newest first.

    A job rewrites its own behaviour: a locator the recorded one could not find
    is replaced by the one a run did, and a box's limit is written down the
    first time a value would not fit. Every one of those is stored as the
    CURRENT answer, one row per step, the last winning -- which is right for
    the run asking what to try first, and leaves a job drifting with nothing
    anybody can read.

    This is the reviewable half. Not an approval gate: what a run found is
    already what the next run will try, and holding that behind a person would
    mean a job that healed itself on Friday waits until Monday to say so. What
    it is for is somebody being able to ask "why is this step looking for a css
    path" and get an answer with a run id in it.

    Tenant-only, like the evidence beside it. A locator is a fact about the
    inside of somebody's warehouse system.
    """
    return LearnedChangesResponse.of(
        await container.read_what_a_job_taught().execute(ctx, workflow_id=workflow_id)
    )


@router.get("/workflows/{workflow_id}/evidence", dependencies=[TenantOnly])
async def workflow_evidence(
    container: ContainerDep, ctx: ContextDep, workflow_id: str
) -> EvidenceResponse:
    """Everything one workflow cites, for the bridge that replays it.

    The evidence first, so an unknown workflow is the one 404 it always was
    rather than whichever of the two reads happens to be asked first.
    """
    evidence = await container.read_evidence().execute(ctx, workflow_id=workflow_id)
    return EvidenceResponse.of(
        evidence, shots=await container.read_shots().execute(ctx, workflow_id=workflow_id)
    )
