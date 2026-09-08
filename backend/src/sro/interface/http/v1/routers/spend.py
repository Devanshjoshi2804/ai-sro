"""What the tenant's day of model calls has cost, and the cap it is spending against.

Ported from `new_agent_arch/src/rig/api.py:663`. Tenant-only, as it is there:
what a tenant is spending on models is the tenant's to read, and a browser's
secret opens its own doors and not the tenant's purse.

Narrowed from the rig, deliberately. There, `/v1/spend` answered twenty-two
fields -- token counts, per-table roll-ups, gestures read, an average per
reading. Three are ported: the day's dollars, the day's unpriced calls and the
cap. They are the three the cap is judged on -- `over_cap` reads the first two
and is given the third -- so this is the one endpoint that can answer "am I
about to be cut off" without the console doing arithmetic the application layer
already does. The rest were a debugging surface over the rig's own tables,
several of which do not exist under those names here, and each one would be a
second place the day's bill is computed.

`unpriced` is reported and never folded into the total. Two commits on main --
`789d069` and `11782b4` -- exist because a call that never returned was being
recorded as a free one, and a day summed on `cost_usd` alone reads as free
while it spends: a model name the price table never knew about bills $0.0000
with `unpriced` set. A route that answered only a number would throw that away
at the last step, on the last screen anybody looks at.

Which day is being asked about comes off the container's clock and never off
one read here -- `Container.read_spend` supplies it -- and the cap off
`settings`, never a literal: a route that answered the shipped default would
be wrong on every deployment that configured its own.

Nothing here catches a domain error: `sro.interface.http.errors` maps them
once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import SpendResponse

router = APIRouter(tags=["spend"], dependencies=[TenantOnly])


@router.get("/spend")
async def spend(container: ContainerDep, ctx: ContextDep) -> SpendResponse:
    """This tenant's bill since midnight UTC, with what could not be priced."""
    return SpendResponse.of(
        await container.read_spend(ctx), cap_usd=container.settings.daily_usd_cap
    )
