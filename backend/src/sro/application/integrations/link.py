from __future__ import annotations

from collections.abc import Sequence

from pydantic import SecretStr

from sro.application.context import RequestContext
from sro.application.integrations.connect import NOT_SET_UP
from sro.application.integrations.end_user import end_user_id
from sro.application.integrations.listing import IntegrationStatus
from sro.application.integrations.servers import MCP_SERVER, not_set_up
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
        if integration not in self._integrations:
            raise Conflict(f"{integration!r} is not an integration this server can link")
        if self._nango is None:
            raise NangoUnavailable(NOT_SET_UP)
        server = MCP_SERVER.get(integration)
        if server is not None and self._key is None:
            raise NangoUnavailable(NO_KEY)
        if integration not in await self._nango.integrations():
            raise Conflict(not_set_up(integration))
        healthy = [
            one
            for one in await self._nango.connections(end_user_id(ctx))
            if one.integration == integration and one.healthy
        ]
        if not healthy:
            raise Conflict(f"Connect {(server or integration).capitalize()} first")
        if server is not None and self._key is not None:  # no connector: nothing to link
            bearer = sign_bearer(
                self._key.get_secret_value(), server, ctx.tenant_id.value, ctx.principal_id.value
            )
            await self._vault.store(
                connector_key(ctx.tenant_id.value, server, ctx.principal_id.value), bearer
            )
        return IntegrationStatus(integration, True, True, max(one.created_at for one in healthy))
