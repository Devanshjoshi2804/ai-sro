"""What the extension matches a live tail against.

Ported from `new_agent_arch/src/rig/api.py:1533`. Arithmetic on the way out
and arithmetic on the way in: no model is on this path, which is why it can be
asked on every page an operator opens.

The asking browser is named by its secret and never by the query string --
`asking_device` refuses a mismatch rather than resolving it -- because the rest
a workflow earns is per browser: a job somebody refused three times comes back
quiet for them and for nobody else, and a browser that could name another's id
could read that.

Not `tenant_only`, unlike the devices door next to it: a browser asking for its
own list is the whole point of this route, and the tenant asking without naming
one is answered too -- with no browser named there is nobody to rest, so the
list comes back with every job offerable.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.interface.http.asking import AskingDeviceDep
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import ShapesResponse

router = APIRouter(tags=["shapes"])


@router.get("/shapes")
async def shapes(
    container: ContainerDep,
    ctx: ContextDep,
    asking: AskingDeviceDep,
) -> ShapesResponse:
    """Every proven workflow of this tenant, as the extension needs it."""
    served = await container.serve_shapes().execute(ctx, device_id=asking)
    return ShapesResponse(
        shapes=[shape.as_json() for shape in served],
        can_find=container.can_gather,
        takes_over=container.start_workflow_run().runs_on_steel(ctx),
    )
