"""Request-scoped dependencies, starting with who is asking.

Identity used to be two headers with defaults, which meant the tenant boundary
the rest of this codebase is built around could be crossed by typing a
different value. Every use case takes its tenant from ``RequestContext``, so
this is the one file that decides whose data a request can touch -- and now it
decides it from a signature rather than from a claim.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from sro.application.context import RequestContext
from sro.application.ports.auth import CredentialRejected, Unconfigured
from sro.container import Container
from sro.infrastructure.telemetry.whose import attribute


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


async def get_context(
    container: Annotated[Container, Depends(get_container)],
    authorization: Annotated[str | None, Header()] = None,
) -> RequestContext:
    """The caller this credential belongs to, or no request at all.

    The 401 says a credential is needed and nothing else. Which part was wrong
    -- absent, expired, or signed by somebody else -- is only useful to
    somebody working out what to try next.

    `async`, and that is load-bearing: FastAPI runs a SYNC dependency in a
    threadpool, and `run_in_threadpool` gives it a COPY of the context. The
    `attribute` below then set the tenant in the copy, which was thrown away
    when the thread finished -- so every line an HTTP route wrote carried a
    request id and no tenant at all, which is exactly the attribution this
    plane exists for. Verifying a credential is a signature check and blocks
    on nothing, so there was never a thread worth spending on it either.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="this endpoint needs a credential: send `Authorization: Bearer <token>`",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        caller = container.credentials.verify(authorization)
    except Unconfigured as exc:
        # Ours to fix, not theirs, and never a reason to let the request past:
        # a deployment that cannot check credentials must refuse, not shrug.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except CredentialRejected as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="that credential was not accepted",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # From here on, every line this request writes says whose it is. The
    # middleware gave it an id before anything knew who was asking; this is
    # the first moment anything does. Inside the request's own task, so it
    # lasts exactly as long as the request -- see `whose.attribute`.
    attribute(tenant=caller.tenant_id.value, principal=caller.principal_id.value)
    return RequestContext(tenant_id=caller.tenant_id, principal_id=caller.principal_id)


ContainerDep = Annotated[Container, Depends(get_container)]
ContextDep = Annotated[RequestContext, Depends(get_context)]

DeviceSecretDep = Annotated[str, Header(alias="X-Device-Secret")]
"""What a browser proves it is *itself* with, on every device-scoped path.

The credential above says which tenant is asking and can never say which
browser: `/v1/agents/{device_id}/...` is a namespace, not a credential, and one
of those paths fires a run in a live warehouse. Both, always -- drop the
credential and a leaked secret reaches across tenants, drop the secret and a
colleague's extension is any device it can name.

Declared with a default of `""` at every use rather than as required, because a
422 naming a missing header is itself an answer: absent, wrong, and belonging
to somebody else must all be the one 404.
"""


async def about_thread(thread_id: str) -> None:
    """Attribute this request to the conversation it is about.

    A dependency rather than a line in each handler: it is declared once beside
    the route and FastAPI resolves `thread_id` from the path it already
    matched, so a route that has a thread cannot be added without one. Nothing
    is returned -- the attribution is the whole of the effect.
    """
    attribute(thread=thread_id)


AboutThread = Depends(about_thread)
"""Put this in a thread route's `dependencies=[...]`. See `about_thread`."""
