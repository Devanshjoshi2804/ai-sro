from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.context import RequestContext
from sro.application.integrations.connect import NOT_SET_UP
from sro.application.integrations.end_user import end_user_id
from sro.application.ports.nango import Nango, NangoUnavailable


@dataclass(frozen=True, slots=True)
class IntegrationStatus:
    integration: str
    connected: bool
    connected_at: datetime | None


class ListIntegrations:
    def __init__(self, nango: Nango | None, integrations: Sequence[str]) -> None:
        self._nango = nango
        self._integrations = integrations

    async def execute(self, ctx: RequestContext) -> list[IntegrationStatus]:
        if not self._integrations:
            return []
        if self._nango is None:
            raise NangoUnavailable(NOT_SET_UP)
        made = {
            c.integration: c.created_at for c in await self._nango.connections(end_user_id(ctx))
        }
        return [
            IntegrationStatus(name, name in made, made.get(name)) for name in self._integrations
        ]
