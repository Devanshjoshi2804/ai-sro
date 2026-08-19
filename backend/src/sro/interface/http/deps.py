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


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_context(
    container: Annotated[Container, Depends(get_container)],
    authorization: Annotated[str | None, Header()] = None,
) -> RequestContext:
    """The caller this credential belongs to, or no request at all.

    The 401 says a credential is needed and nothing else. Which part was wrong
    -- absent, expired, or signed by somebody else -- is only useful to
    somebody working out what to try next.
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

    return RequestContext(tenant_id=caller.tenant_id, principal_id=caller.principal_id)


ContainerDep = Annotated[Container, Depends(get_container)]
ContextDep = Annotated[RequestContext, Depends(get_context)]
