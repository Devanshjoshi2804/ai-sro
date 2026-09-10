"""The carryover pool: what the next pass will be offered first, and what it will not.

Ported from `new_agent_arch/src/rig/api.py:794`. Its docstring is the reason
the door exists: `retired` is the record `pool.py` says must exist -- evidence
that stopped being privileged, when it entered and under which cap it aged out
-- and nothing over the wire could read it. A pass whose window quietly stopped
carrying yesterday's tail looked exactly like one that had nothing left to
carry.

Worth opening now rather than in a later phase because it is the only way to
check the pool-rotation measurement from outside a script: ten simulated passes
put pass 1 at 81% coverage and pass 2 at 96%, with nineteen gestures never
shown -- all of them claimed. Those numbers came from a simulation. This is
where a real deployment's are read from.

Two lists and never one, which is `PoolRepository`'s own rule: a retired entry
is not a deleted one, so the live entries and the retired ones are two reads
and an entry is retired exactly when it has a `reason`.

Read-only, and deliberately: `age` is the pass's to call, once per pass. A door
that aged what it looked at would retire evidence for being read about.

Broadened from the rig on one point, and it is the same divergence
`asking.py` declares. There `authorised` meant the tenant's bearer and a device
held a token of its own; here the credential IS the tenant's, and a browser
proves it is itself with `X-Device-Secret` on top. So this router takes the
credential and nothing else rather than `TenantOnly` -- the extension sends
that header on every request it makes, and a tenant-only door would answer it
404 for naming no browser rather than serving a read that is the tenant's
either way. Nothing here is per browser: the pool is keyed by tenant, which is
the whole mechanism by which one operator's Blue Yonder half meets another
operator's SAP half.

Nothing here catches a domain error: `sro.interface.http.errors` maps them
once, for every route.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import PoolResponse

router = APIRouter(tags=["pool"])


@router.get("/pool")
async def pool(container: ContainerDep, ctx: ContextDep) -> PoolResponse:
    """This tenant's live entries, oldest first, and what has retired."""
    return PoolResponse.of(await container.read_pool().execute(ctx))
