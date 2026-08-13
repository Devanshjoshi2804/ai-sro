"""Request-scoped dependencies.

Identity is a stub in v0: the tenant and principal arrive as headers. The rest
of the codebase already takes them from ``RequestContext``, so replacing this
with a real identity provider touches this file only.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request

from sro.application.context import RequestContext
from sro.container import Container
from sro.domain.shared.identifiers import PrincipalId, TenantId


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_context(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")] = "dev",
    x_principal_id: Annotated[str, Header(alias="X-Principal-Id")] = "dev-operator",
) -> RequestContext:
    return RequestContext(
        tenant_id=TenantId(x_tenant_id),
        principal_id=PrincipalId(x_principal_id),
    )


ContainerDep = Annotated[Container, Depends(get_container)]
ContextDep = Annotated[RequestContext, Depends(get_context)]
