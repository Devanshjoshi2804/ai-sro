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

`?device_id=` with `X-Device-Secret` still reaches the listing and names the
browser; nothing there reads it. It is refused at the evidence route by
`tenant_only`, with a 403 rather than a 404: the caller is holding a tenant
credential that was accepted, so this is not an enumeration channel.

Nothing here catches a domain error: `sro.interface.http.errors` maps them
once, for every route. A workflow this tenant does not have is the
repository's `NotFound` and reaches a caller as a 404 -- never as an empty
list, which would tell them their bridge is fine and their job is empty.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import EvidenceResponse, WorkflowsResponse

router = APIRouter(tags=["workflows"])


@router.get("/workflows")
async def workflows(container: ContainerDep, ctx: ContextDep) -> WorkflowsResponse:
    """Every workflow this tenant has mined, with what has become of each."""
    return WorkflowsResponse.of(await container.read_workflows().execute(ctx))


@router.get("/workflows/{workflow_id}/evidence", dependencies=[TenantOnly])
async def workflow_evidence(
    container: ContainerDep, ctx: ContextDep, workflow_id: str
) -> EvidenceResponse:
    """Everything one workflow cites, for the bridge that replays it."""
    return EvidenceResponse.of(
        await container.read_evidence().execute(ctx, workflow_id=workflow_id)
    )
