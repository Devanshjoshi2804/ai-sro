from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from sro.domain.shared.identifiers import PrincipalId, TenantId


@dataclass(frozen=True, slots=True)
class ToolOffered:
    name: str
    description: str = ""
    arguments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ToolResult:
    text: str
    failed: bool = False
    detail: str = ""


class ToolsUnavailable(Exception):
    code = "tools_unavailable"


class NotConnected(ToolsUnavailable):
    code = "not_connected"


class ToolCaller(Protocol):
    @property
    def available(self) -> bool: ...

    async def list_tools(
        self, tenant_id: TenantId, principal_id: PrincipalId, server: str
    ) -> Sequence[ToolOffered]: ...

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult: ...
