from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class NangoConnection:
    connection_id: str
    integration: str
    created_at: datetime
    healthy: bool = True
    end_user_id: str = ""  # the tag Nango holds, so a caller can check whose it is


class Nango(Protocol):
    async def create_connect_session(
        self, end_user_id: str, display_name: str, organization_id: str, integrations: Sequence[str]
    ) -> str: ...

    async def connections(self, end_user_id: str) -> list[NangoConnection]: ...

    async def integrations(self) -> set[str]:
        """The unique keys of the integrations set up in Nango."""
        ...


class NangoUnavailable(Exception):
    code = "connections_unavailable"


class NangoIntegrationMissing(Exception):
    """Nango has no such integration: retrying never helps, an admin must add it."""
