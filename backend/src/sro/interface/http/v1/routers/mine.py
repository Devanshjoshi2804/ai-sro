"""One reading of this tenant's day, asked for on purpose.

Ported from `new_agent_arch/src/rig/api.py:739`. Tenant-only, as it is there:
this is the most expensive call the system makes, and a device token opening
its own doors must not be able to spend the tenant's model budget.

**Not `/v1/candidates/mine`.** That one is the heuristic candidate miner and
makes no model call at all. Two routes, two miners, one verb between them.

Nothing here catches a refusal: `sro.interface.http.errors` maps
`AskerUnavailable` to 503 and `OverCap` to 429 once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import MinePassResponse

router = APIRouter(tags=["mine"], dependencies=[TenantOnly])


@router.post("/mine", status_code=status.HTTP_200_OK)
async def mine_the_day(container: ContainerDep, ctx: ContextDep) -> MinePassResponse:
    """Read this tenant's day and keep what it recognises.

    No body: the tenant comes from the caller and the day comes from the
    container's clock. A body naming either would be a request to mine
    somebody else's evidence, or to mine a day the spend cap was not measured
    against.

    200 rather than 202: the pass is synchronous and the caller is billed for
    it, so answering "accepted" and hanging up would leave nobody holding the
    receipt.
    """
    return MinePassResponse.of(await container.mine_pass().execute(ctx))
