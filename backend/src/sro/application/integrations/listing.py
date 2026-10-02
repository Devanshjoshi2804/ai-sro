from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.integrations.connect import NOT_SET_UP
from sro.application.integrations.end_user import end_user_id
from sro.application.integrations.servers import MCP_SERVER
from sro.application.ports.nango import Nango, NangoUnavailable
from sro.application.ports.vault import CredentialVault
from sro.domain.execution.secrets import connector_key


@dataclass(frozen=True, slots=True)
class IntegrationStatus:
    integration: str
    connected: bool
    connected_at: datetime | None


class ListIntegrations:
    def __init__(
        self, nango: Nango | None, integrations: Sequence[str], vault: CredentialVault
    ) -> None:
        self._nango = nango
        self._integrations = integrations
        self._vault = vault

    async def execute(self, ctx: RequestContext) -> list[IntegrationStatus]:
        if not self._integrations:
            return []
        if self._nango is None:
            raise NangoUnavailable(NOT_SET_UP)
        made: dict[str, datetime] = {}
        for one in await self._nango.connections(end_user_id(ctx)):
            if one.healthy:
                made[one.integration] = max(
                    one.created_at, made.get(one.integration, one.created_at)
                )
        return [
            IntegrationStatus(name, name in made and await self._linked(ctx, name), made.get(name))
            for name in self._integrations
        ]

    async def _linked(self, ctx: RequestContext, integration: str) -> bool:
        # Connected in Nango is not enough: the connector needs this operator's bearer too.
        server = MCP_SERVER.get(integration)
        if server is None:
            return True
        key = connector_key(ctx.tenant_id.value, server, ctx.principal_id.value)
        return await self._vault.get(key) is not None
