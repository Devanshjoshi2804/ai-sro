from __future__ import annotations

import contextlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx

from sro.application.ports.tools import (
    NotConnected,
    ToolCaller,
    ToolOffered,
    ToolResult,
    ToolsUnavailable,
)
from sro.application.ports.vault import CredentialVault, VaultUnavailable
from sro.domain.execution.secrets import connector_key
from sro.domain.shared.identifiers import PrincipalId, TenantId

CALL_TIMEOUT = 30.0

PROTOCOL = "2025-06-18"


@dataclass(frozen=True, slots=True)
class McpServer:
    name: str
    url: str


class McpToolCaller(ToolCaller):
    def __init__(
        self, servers: Sequence[McpServer] = (), vault: CredentialVault | None = None
    ) -> None:
        self._servers = {server.name: server for server in servers}
        self._vault = vault

    @property
    def available(self) -> bool:
        return bool(self._servers)

    async def _bearer(self, tenant_id: TenantId, principal_id: PrincipalId, server: str) -> str:
        if self._vault is None:
            raise NotConnected(
                f"{server} needs a per-tenant grant and this deployment has no vault to keep it in"
            )
        key = connector_key(tenant_id.value, server, principal_id.value)
        try:
            kept = await self._vault.get(key)
        except VaultUnavailable as down:
            raise ToolsUnavailable(f"the vault holding {server}'s grant is unreachable") from down
        if kept:
            return kept
        raise NotConnected(f"{principal_id.value} has not connected {server}")

    async def list_tools(
        self, tenant_id: TenantId, principal_id: PrincipalId, server: str
    ) -> tuple[ToolOffered, ...]:
        answer = await self._rpc(tenant_id, principal_id, server, "tools/list", {})
        offered = answer.get("tools")
        if not isinstance(offered, list):
            return ()
        return tuple(
            ToolOffered(
                name=str(tool["name"]),
                description=str(tool.get("description", "")),
                arguments=_argument_names(tool.get("inputSchema")),
            )
            for tool in offered
            if isinstance(tool, dict) and tool.get("name")
        )

    async def call(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        tool: str,
        arguments: Mapping[str, str],
    ) -> ToolResult:
        answer = await self._rpc(
            tenant_id,
            principal_id,
            server,
            "tools/call",
            {"name": tool, "arguments": dict(arguments)},
        )
        return ToolResult(
            text=_text_of(answer),
            failed=bool(answer.get("isError")),
            detail=_text_of(answer) if answer.get("isError") else "",
        )

    async def _rpc(
        self,
        tenant_id: TenantId,
        principal_id: PrincipalId,
        server: str,
        method: str,
        params: dict[str, object],
    ) -> dict[str, object]:
        known = self._servers.get(server)
        if known is None:
            raise ToolsUnavailable(f"no connector called {server} is configured")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        headers["Authorization"] = f"Bearer {await self._bearer(tenant_id, principal_id, server)}"

        try:
            async with httpx.AsyncClient(timeout=CALL_TIMEOUT) as client:
                session = await self._greet(client, known, headers)
                response = await client.post(
                    known.url,
                    headers={**headers, **session},
                    json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                )
        except httpx.HTTPError as unreachable:
            raise ToolsUnavailable(f"{server} did not answer: {unreachable}") from unreachable

        if response.status_code >= 400:
            raise ToolsUnavailable(f"{server} answered {response.status_code}")

        body = _payload(response.text)
        if body is None:
            raise ToolsUnavailable(f"{server} answered something that is not JSON-RPC")
        if "error" in body:
            error = body["error"]
            detail = error.get("message") if isinstance(error, dict) else str(error)
            raise ToolsUnavailable(f"{server} refused: {detail}")
        result = body.get("result")
        return result if isinstance(result, dict) else {}

    async def _greet(
        self, client: httpx.AsyncClient, known: McpServer, headers: Mapping[str, str]
    ) -> dict[str, str]:
        try:
            answer = await client.post(
                known.url,
                headers=dict(headers),
                json={
                    "jsonrpc": "2.0",
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": PROTOCOL,
                        "capabilities": {},
                        "clientInfo": {"name": "ai-sro", "version": "1"},
                    },
                },
            )
        except httpx.HTTPError:
            return {}

        session = answer.headers.get("mcp-session-id", "")
        if not session:
            return {}

        with contextlib.suppress(httpx.HTTPError):
            await client.post(
                known.url,
                headers={**headers, "Mcp-Session-Id": session},
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
        return {"Mcp-Session-Id": session}


def _argument_names(schema: object) -> tuple[str, ...]:
    if not isinstance(schema, dict):
        return ()
    properties = schema.get("properties")
    return tuple(str(name) for name in properties) if isinstance(properties, dict) else ()


def _payload(text: str) -> dict[str, object] | None:
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            loaded = json.loads(stripped)
        except ValueError:
            return None
        return loaded if isinstance(loaded, dict) else None

    for line in stripped.splitlines():
        if line.startswith("data:"):
            try:
                loaded = json.loads(line[len("data:") :].strip())
            except ValueError:
                continue
            if isinstance(loaded, dict):
                return loaded
    return None


def _text_of(result: dict[str, object]) -> str:
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        str(block.get("text", ""))
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )
