"""Connecting a mail account in one click, through Nango.

The sign-in happens on the provider's own page inside Nango's Connect UI. Nothing
here accepts a password or a token from the browser, and the Nango secret key never
leaves this process.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import (
    ConnectSessionModel,
    ConnectSessionRequest,
    IntegrationModel,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/connect-session")
async def create_connect_session(
    body: ConnectSessionRequest, container: ContainerDep, ctx: ContextDep
) -> ConnectSessionModel:
    """A short-lived token for Nango's Connect UI, naming this operator as the end user."""
    grant = await container.connect_session().execute(ctx, integration=body.integration)
    return ConnectSessionModel(
        token=grant.token, connect_url=grant.connect_url, api_url=grant.api_url
    )


@router.get("")
async def list_integrations(container: ContainerDep, ctx: ContextDep) -> list[IntegrationModel]:
    """Each configured integration, and whether this operator has connected it."""
    found = await container.list_integrations().execute(ctx)
    return [
        IntegrationModel(
            integration=one.integration, connected=one.connected, connected_at=one.connected_at
        )
        for one in found
    ]
