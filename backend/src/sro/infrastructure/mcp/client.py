"""Calling somebody else's MCP tools from a skill's own step.

The other half of `server.py`. That one hands this system's skills to another
agent; this one lets a step be performed by calling a connector the tenant
configured -- which is what makes a mail step a call rather than a click, and a
click is the one thing that can never be clean.

Configured rather than discovered. A server is named in settings with its URL;
nothing here goes looking for connectors, because a system that found one and
used it would be making the tenant's integration decisions for them.

**The URL is deployment config and the credential never is.** Settings used to
carry `name=url#token`, one bearer for the whole deployment, and every tenant's
step went out holding it -- so a skill run for any tenant reached the same
connector and the same person's Google grant. The token now comes from the
vault under `tenant/server/mcp_token`, per tenant, and a tenant with no grant
gets `NotConnected` rather than somebody else's mailbox. The `#token` form is
gone rather than deprecated: left in, it is a working shared-credential path
that nothing would stop a deployment using.
"""

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
"""Long enough for a mail to be sent, short enough that a hung connector is a
failed step rather than a run nobody can finish."""

PROTOCOL = "2025-06-18"
"""The version this client says it speaks when it opens a session.

Named rather than inlined because it is the one thing in the handshake a server
may refuse over, and a refusal that names a version is one somebody can act on.
"""


@dataclass(frozen=True, slots=True)
class McpServer:
    """Where a connector is. Deliberately no credential on it -- see the module
    docstring: a bearer here is a bearer every tenant shares."""

    name: str
    url: str


class McpToolCaller(ToolCaller):
    """Streamable-HTTP MCP, spoken directly.

    The SDK's client wants to own a connection and a session for the life of a
    conversation; a step is one call and then nothing, sometimes hours before
    the next. Two JSON-RPC requests over `httpx` is the whole of what that
    needs, and it fails in ways this code can report rather than in the SDK's.
    """

    def __init__(
        self, servers: Sequence[McpServer] = (), vault: CredentialVault | None = None
    ) -> None:
        self._servers = {server.name: server for server in servers}
        self._vault = vault

    @property
    def available(self) -> bool:
        return bool(self._servers)

    async def _bearer(self, tenant_id: TenantId, principal_id: PrincipalId, server: str) -> str:
        """This OPERATOR's grant for this connector, or a refusal naming both.

        The whole security property of this adapter. `secret_key_of` is the
        vault's own `tenant/system/field` shape rather than a second spelling,
        so a connector's grant sits beside the passwords a step types and is
        revoked the same way.

        A deployment with no vault configured cannot hold a per-tenant grant,
        so it gets the refusal too. That is stricter than before -- it used to
        call with no credential at all -- and it is the point: a connector
        reached without a tenant's grant is a connector reached on somebody
        else's behalf.
        """
        if self._vault is None:
            raise NotConnected(
                f"{server} needs a per-tenant grant and this deployment has no vault to keep it in"
            )
        # `connector_key` on both sides, never a hand-spelled key. It hashes
        # the principal in, because `_as_key` collapses punctuation and
        # `devansh.j` and `devansh_j` would otherwise be one key -- which is
        # one operator reading another's mail.
        key = connector_key(tenant_id.value, server, principal_id.value)
        try:
            kept = await self._vault.get(key)
        except VaultUnavailable as down:
            # A different fact from "not connected", and the caller tells them
            # apart: one is a console saying "connect Gmail", the other is a
            # deployment problem no operator can act on.
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
        # `isError` is the tool saying no, which is an answer. Reported as a
        # failed result rather than raised, because the escalation table treats
        # "it refused" and "there was nothing to ask" differently and both
        # arriving as an exception would collapse them.
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
        """Open a session, and the header that carries it.

        A streamable-HTTP MCP server built on the standard SDK answers anything
        before `initialize` with "Bad Request: Missing session ID", so a client
        that went straight to `tools/list` could talk to a permissive stub and
        to nothing else. This one greets first, then sends the session id back
        on the call itself.

        `{}` where the server needs no session: a server that does not answer
        with `Mcp-Session-Id` is one that never asked for it, and a call
        carrying an invented header would be worse than one carrying none.

        A failed greeting is not raised here. The call that follows fails on
        its own and says why in its own words -- reporting the handshake
        instead would name the wrong request.
        """
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

        # The spec's third step. A server may hold `tools/list` until it
        # arrives, and one that does not is unbothered by receiving it.
        with contextlib.suppress(httpx.HTTPError):
            await client.post(
                known.url,
                headers={**headers, "Mcp-Session-Id": session},
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
        return {"Mcp-Session-Id": session}


def _argument_names(schema: object) -> tuple[str, ...]:
    """What this tool takes, for a person choosing what to map onto it.

    Read from the schema rather than required to be there: a server that
    declares no properties still offers the tool, and a mapping screen that
    hid it would be hiding a working connector over a missing description.
    """
    if not isinstance(schema, dict):
        return ()
    properties = schema.get("properties")
    return tuple(str(name) for name in properties) if isinstance(properties, dict) else ()


def _payload(text: str) -> dict[str, object] | None:
    """The JSON-RPC envelope, whether it arrived as JSON or as one SSE event.

    Streamable HTTP may answer either, and which one is the server's choice
    rather than ours.
    """
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
    """What the tool said, as the text an assertion is checked against.

    MCP answers with a list of content blocks. The text ones are joined and the
    rest are left out: an assertion reads a document, and an image in the
    middle of one is not part of the document.
    """
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        str(block.get("text", ""))
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )
