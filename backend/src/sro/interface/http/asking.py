"""Which browser is asking, if a browser is asking at all.

The rig's `caller` read one bearer and answered "the tenant (None) or this
device (its id)", because a device there held a token of its own. The backend
does not work that way and is not being changed to: its credential says which
tenant and can never say which browser, and a browser proves it is itself with
`X-Device-Secret` on top. So the port of `caller` is not a second credential
check -- it is "this request also carried a secret that checks out, so name the
browser it belongs to."

Declared divergence from `new_agent_arch/src/rig/api.py:405-419`: there, a
device bearer WAS a credential and a request could arrive as a device without
the tenant's token. Here both are always required, which is strictly stronger
and is the rule the rest of this codebase already keeps -- `DeviceSecretDep`
and `ReadDevice` say it in the same words. Nothing downstream notices: every
route that cared only wanted the device's id.

Half a pair is a refusal, never a downgrade. A secret with no device named, or
a device named with no secret, is somebody reaching for a browser they cannot
prove they are -- answering that as "the tenant, then" would turn
`?device_id=` into an impersonation parameter, and every device-scoped answer
would be one query string away from any credential in the tenant.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status

from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.deps import ContainerDep, ContextDep, DeviceSecretDep


async def asking_device(
    container: ContainerDep,
    ctx: ContextDep,
    x_device_secret: DeviceSecretDep = "",
    device_id: Annotated[str | None, Query()] = None,
) -> DeviceId | None:
    """The browser this request proves it is, or ``None`` for the tenant.

    The 404 is the same one every device-scoped path gives, in the same words
    `refuse_unless_itself` uses: absent, wrong, revoked and belonging to
    somebody else must not be told apart by a caller probing for which browsers
    exist. Raised as an `HTTPException` rather than let out as the domain's
    `NotFound` only so that the half-pair refusal above -- which never reaches a
    repository -- cannot be told from a lookup that did by the shape of what
    comes back. Both land on the same problem document either way.
    """
    # Blanked, never rewritten. `?device_id=%20` reached `DeviceId(" ")`; an id
    # the domain refuses to build is a 422 telling a caller their query string
    # was interesting, out of the one function whose promise is that nothing
    # here is told apart. So an id that is nothing but space becomes "no
    # browser named". (`?device_id=` never got that far on its own: an empty
    # string is falsy and takes one of the two branches below.)
    #
    # And nothing else. `device_id.strip()` would read the same and quietly
    # rewrite every PADDED id on its way to `DeviceId`, at the one seam whose
    # whole job is which browser was named: ` dev-1` would authenticate as
    # `dev-1`. There is no caller that needs that and no test that wanted it.
    if not (device_id or "").strip():
        device_id = ""
    if not device_id and not x_device_secret:
        return None
    if not device_id or not x_device_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"device {device_id} was not found",
        )
    named = DeviceId(device_id)
    try:
        await container.read_device().execute(ctx, device_id=named, secret=x_device_secret)
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return named


AskingDeviceDep = Annotated[DeviceId | None, Depends(asking_device)]


async def tenant_only(asking: AskingDeviceDep) -> None:
    """The tenant's own credential, not a browser proving itself.

    Ported from `new_agent_arch/src/rig/api.py:423`. Registering and revoking
    browsers, spending model money and reading every browser's day are the
    tenant's: a browser's secret opens its own doors -- ingest, its socket, the
    runner's -- and not the tenant's purse or the other browsers' evidence.

    403 and not 404: the caller is holding a tenant credential that was
    accepted, so this is not an enumeration channel -- unlike the device-scoped
    paths above, where absent, wrong and somebody else's have to be one answer.
    They already know the browser exists; they proved they are it.

    A refusal, not a downgrade to the tenant. Ignoring the secret and serving
    the request as the tenant would make `X-Device-Secret` a header that
    changes nothing, and the first route to read `asking` for anything but this
    would then be reading it from a request that had been let through anyway.
    """
    if asking is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="that is the tenant's to do, not a browser's",
        )


TenantOnly = Depends(tenant_only)
