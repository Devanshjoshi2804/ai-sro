"""Day-end 6: a connector that is not configured, and one that refuses for want of a grant, both
sent nothing -- they are NotConnected (reconnect), not "the mail may have gone"."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from sro.application.ports.tools import NotConnected, ToolsUnavailable
from sro.domain.execution.secrets import connector_key
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.mcp.client import McpServer, McpToolCaller
from tests.unit.fakes import FakeCredentialVault

ACME, DEV = TenantId("acme"), PrincipalId("dev")


async def _caller(
    monkeypatch: pytest.MonkeyPatch, answer: Callable[[httpx.Request], httpx.Response]
) -> McpToolCaller:
    real = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(answer), **kw)
    )
    vault = FakeCredentialVault()
    await vault.store(connector_key(ACME.value, "outlook", DEV.value), "grant")
    return McpToolCaller([McpServer("outlook", "http://connector.test/mcp")], vault)


async def test_a_server_nothing_configured_is_not_connected() -> None:
    caller = McpToolCaller([McpServer("gmail", "http://connector.test/mcp")], FakeCredentialVault())

    with pytest.raises(NotConnected, match="outlook"):
        await caller.call(ACME, DEV, "outlook", "send_message", {})


async def test_a_connector_that_has_no_grant_for_the_operator_is_not_connected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32001, "message": "no grant for that credential"},
            },
        )

    caller = await _caller(monkeypatch, refuse)

    with pytest.raises(NotConnected, match="reconnect"):
        await caller.call(ACME, DEV, "outlook", "send_message", {})


async def test_any_other_error_the_connector_returns_is_still_only_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32603, "message": "Graph took too long"},
            },
        )

    caller = await _caller(monkeypatch, refuse)

    with pytest.raises(ToolsUnavailable) as raised:
        await caller.call(ACME, DEV, "outlook", "send_message", {})

    assert not isinstance(raised.value, NotConnected)
