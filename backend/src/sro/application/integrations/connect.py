from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.integrations.end_user import end_user_id
from sro.application.ports.nango import Nango, NangoUnavailable
from sro.domain.shared.errors import Conflict

NOT_SET_UP = "Connections are not set up on this server yet"


@dataclass(frozen=True, slots=True)
class ConnectGrant:
    token: str
    connect_url: str
    api_url: str


class ConnectSession:
    def __init__(
        self,
        nango: Nango | None,
        integrations: Sequence[str],
        connect_url: str,
        api_url: str,
    ) -> None:
        self._nango = nango
        self._integrations = integrations
        self._connect_url = connect_url
        self._api_url = api_url

    async def execute(self, ctx: RequestContext, *, integration: str) -> ConnectGrant:
        if integration not in self._integrations:
            raise Conflict(f"{integration!r} is not an integration this server offers")
        if self._nango is None:
            raise NangoUnavailable(NOT_SET_UP)
        token = await self._nango.create_connect_session(
            end_user_id(ctx), ctx.principal_id.value, ctx.tenant_id.value, [integration]
        )
        return ConnectGrant(token, self._connect_url, self._api_url)
