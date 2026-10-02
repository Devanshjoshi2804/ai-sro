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


class NangoUnavailable(Exception):
    code = "connections_unavailable"
