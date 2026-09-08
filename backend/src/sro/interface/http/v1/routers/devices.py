"""Who may act in this tenant, and taking it away or giving it back.

Ported from `new_agent_arch/src/rig/api.py:988-1019`. Tenant-only, all three:
a browser's secret opens its own doors and never the other browsers'.

`restore` has no rig ancestor. It exists because this port made revocation
enforce -- the rig's `issue` un-revoked as a side effect of handing out a fresh
token, and backend registration is idempotent and returns the same secret, so
nothing here undid a revoke until this route did.

Divergence from the rig's `GET /v1/devices`, declared: there, a device token
got a reduced answer (the online list and nothing more). Here it gets a 403.
The reduced answer was the rig's way of not enumerating siblings to a browser;
this codebase already gives a browser its own doors elsewhere, and a list that
means two different things depending on who asked is a shape a generated client
cannot type.

The path segment is `{device}` and not `{device_id}`, which is not cosmetic:
`tenant_only` reaches `asking_device`, which reads `?device_id=` to learn which
browser is proving itself. Two different browsers can be named on one of these
requests -- the subject in the path, the asker in the query -- and FastAPI
refuses to let one name mean both. The URL an operator types is unchanged.

`NotFound` is not caught. `sro.interface.http.errors` maps it to 404 for every
route at once, and a router that caught it here would be the one place the
answer could quietly drift into something else.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.asking import TenantOnly
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import RevocationResponse, RosterResponse

router = APIRouter(tags=["devices"], dependencies=[TenantOnly])


@router.get("/devices")
async def roster(container: ContainerDep, ctx: ContextDep) -> RosterResponse:
    """Every browser this tenant registered, most recently seen first, with
    whether each is connected and when its authority ended if it has."""
    return RosterResponse.of(await container.read_roster().execute(ctx))


@router.post("/devices/{device}/revoke")
async def revoke(device: str, container: ContainerDep, ctx: ContextDep) -> RevocationResponse:
    """`moved` is false for a browser that was already revoked.

    Not a 404 and not an error: the first revocation's instant is what an audit
    is read against, and a second press must not move it. The 404 is for a
    browser this tenant does not have, which is a different answer.
    """
    moved = await container.revoke_device().execute(ctx, device_id=DeviceId(device))
    return RevocationResponse(device_id=device, moved=moved)


@router.post("/devices/{device}/restore")
async def restore(device: str, container: ContainerDep, ctx: ContextDep) -> RevocationResponse:
    """`moved` is false for a browser that was never revoked -- the same
    idempotence the revoke has, for the same reason: an administrator pressing
    twice has not made a mistake worth an error page.

    No socket is opened. The extension dials on its own next heartbeat.
    """
    moved = await container.restore_device().execute(ctx, device_id=DeviceId(device))
    return RevocationResponse(device_id=device, moved=moved)
