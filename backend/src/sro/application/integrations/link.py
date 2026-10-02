from __future__ import annotations

from collections.abc import Sequence

from pydantic import SecretStr

from sro.application.context import RequestContext
from sro.application.integrations.connect import NOT_SET_UP
from sro.application.integrations.end_user import end_user_id
from sro.application.integrations.listing import IntegrationStatus
from sro.application.integrations.servers import MCP_SERVER
from sro.application.ports.nango import Nango, NangoUnavailable
from sro.application.ports.vault import CredentialVault
from sro.domain.execution.connector_bearer import sign_bearer
from sro.domain.execution.secrets import connector_key
from sro.domain.shared.errors import Conflict

NO_KEY = "Linking a mail account is not set up on this server yet"


class LinkIntegration:
    """Makes a Nango connection usable by its MCP connector: keeps the signed bearer."""

    def __init__(
        self,
        nango: Nango | None,
        integrations: Sequence[str],
        vault: CredentialVault,
        signing_key: SecretStr | None,
    ) -> None:
        self._nango = nango
        self._integrations = integrations
        self._vault = vault
        self._key = signing_key

    async def execute(self, ctx: RequestContext, *, integration: str) -> IntegrationStatus:
        server = MCP_SERVER.get(integration)
        if integration not in self._integrations or server is None:
            raise Conflict(f"{integration!r} is not an integration this server can link")
        if self._nango is None:
            raise NangoUnavailable(NOT_SET_UP)
        if self._key is None:
            raise NangoUnavailable(NO_KEY)
        who = end_user_id(ctx)
        healthy = [
            one
            for one in await self._nango.connections(who)
            if one.integration == integration and one.healthy
        ]
        if not healthy:
            raise Conflict(f"Connect {server.capitalize()} first")
        bearer = sign_bearer(
            self._key.get_secret_value(), server, ctx.tenant_id.value, ctx.principal_id.value
        )
        await self._vault.store(
            connector_key(ctx.tenant_id.value, server, ctx.principal_id.value), bearer
        )
        return IntegrationStatus(integration, True, max(one.created_at for one in healthy))
