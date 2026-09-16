"""The MCP client against a server that actually speaks the protocol.

The unit tests hold what the executor does with an answer. This holds that we
can get one: a real socket, real JSON-RPC, and the two shapes a streamable-HTTP
server is allowed to reply in. A fake that agreed with our reading of the spec
would agree with it whether or not the reading was right.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from sro.application.ports.tools import NotConnected, ToolsUnavailable
from sro.domain.execution.secrets import secret_key_of
from sro.domain.shared.identifiers import TenantId
from sro.infrastructure.mcp.client import McpServer, McpToolCaller

ACME, OTHER = TenantId("acme"), TenantId("other")

GRANTS = {
    # Built with `secret_key_of` and never spelled by hand. It normalises the
    # field -- `mcp_token` becomes `mcp-token` -- so a key typed out here would
    # pass review and miss every lookup, which is how this test first failed.
    secret_key_of(ACME.value, "mail", "mcp_token"): "acme-grant",
    secret_key_of(OTHER.value, "mail", "mcp_token"): "other-grant",
}


class _Vault:
    """Holds what the console would have written when a tenant connected."""

    def __init__(self, grants: dict[str, str]) -> None:
        self._grants = grants

    async def store(self, key: str, value: str) -> None:
        self._grants[key] = value

    async def get(self, key: str) -> str | None:
        return self._grants.get(key)

    async def delete(self, key: str) -> None:
        self._grants.pop(key, None)


TOOLS = {
    "tools": [
        {
            "name": "send_message",
            "description": "Send a mail",
            "inputSchema": {"properties": {"to": {"type": "string"}, "body": {"type": "string"}}},
        }
    ]
}


SESSION = "a-session-the-server-handed-out"


class _Server(BaseHTTPRequestHandler):
    """Answers as an MCP server does. `mode` decides how."""

    mode = "json"
    seen: list[dict[str, Any]] = []  # noqa: RUF012 -- one server, one test

    def log_message(self, *args: Any) -> None:  # silence the default stderr log
        return

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        request = json.loads(raw)
        _Server.seen.append({**request, "authorization": self.headers.get("Authorization", "")})

        if _Server.mode == "broken":
            self._reply(500, b"not json at all", kind="text/plain")
            return

        if _Server.mode == "session":
            # What a streamable-HTTP server built on the standard SDK does, and
            # what our own /mcp endpoint answered before this was fixed:
            # everything before `initialize` is refused, and everything after
            # it must carry the session it handed back.
            if request["method"] == "initialize":
                body = json.dumps(
                    {"jsonrpc": "2.0", "id": request["id"], "result": {"capabilities": {}}}
                ).encode()
                self._reply(200, body, session=SESSION)
                return
            if self.headers.get("Mcp-Session-Id") != SESSION:
                body = json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {"code": -32600, "message": "Bad Request: Missing session ID"},
                    }
                ).encode()
                self._reply(200, body)
                return
            if request["method"] == "notifications/initialized":
                self._reply(202, b"")
                return

        if request["method"] == "tools/list":
            result: dict[str, Any] = TOOLS
        elif _Server.mode == "refuses":
            result = {"content": [{"type": "text", "text": "no mailbox"}], "isError": True}
        else:
            arguments = request["params"]["arguments"]
            result = {
                "content": [
                    {"type": "image", "data": "ignored"},
                    {"type": "text", "text": json.dumps({"status": "sent", **arguments})},
                ]
            }

        body = json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}).encode()
        if _Server.mode == "sse":
            # The other shape a streamable-HTTP server may answer in, which is
            # the server's choice rather than ours.
            self._reply(200, b"event: message\ndata: " + body + b"\n\n", kind="text/event-stream")
        else:
            self._reply(200, body)

    def _reply(
        self, code: int, body: bytes, kind: str = "application/json", session: str = ""
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        if session:
            self.send_header("Mcp-Session-Id", session)
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def connector() -> Any:
    _Server.mode = "json"
    _Server.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Server)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # The host is the literal this server was bound to. Reading it back off
    # `server_address` types as `str | bytes` -- the AF_UNIX arm -- and a bytes
    # host would silently build `http://b'127.0.0.1':.../mcp`.
    port = server.server_address[1]
    yield McpToolCaller(
        [McpServer(name="mail", url=f"http://127.0.0.1:{port}/mcp")], vault=_Vault(dict(GRANTS))
    )
    server.shutdown()
    server.server_close()


async def test_a_connector_says_what_it_offers(connector: McpToolCaller) -> None:
    offered = await connector.list_tools(ACME, "mail")

    assert [tool.name for tool in offered] == ["send_message"]
    assert set(offered[0].arguments) == {"to", "body"}


async def test_calling_one_sends_the_arguments_and_the_credential(
    connector: McpToolCaller,
) -> None:
    answered = await connector.call(ACME, "mail", "send_message", {"to": "a@b.test", "body": "hi"})

    assert json.loads(answered.text) == {"status": "sent", "to": "a@b.test", "body": "hi"}
    assert answered.failed is False
    assert _Server.seen[-1]["authorization"] == "Bearer acme-grant"


async def test_an_answer_that_arrives_as_an_event_stream_reads_the_same(
    connector: McpToolCaller,
) -> None:
    _Server.mode = "sse"

    answered = await connector.call(ACME, "mail", "send_message", {"to": "a@b.test", "body": "hi"})

    assert json.loads(answered.text)["status"] == "sent"


async def test_a_tool_that_refuses_is_an_answer_rather_than_an_exception(
    connector: McpToolCaller,
) -> None:
    """The escalation table treats "it refused" and "there was nothing to ask"
    differently, and both arriving as an exception would collapse them."""
    _Server.mode = "refuses"

    answered = await connector.call(ACME, "mail", "send_message", {"to": "a@b.test"})

    assert answered.failed is True
    assert "no mailbox" in answered.detail


async def test_a_connector_that_answers_rubbish_is_unavailable_rather_than_a_crash(
    connector: McpToolCaller,
) -> None:
    _Server.mode = "broken"

    with pytest.raises(ToolsUnavailable):
        await connector.call(ACME, "mail", "send_message", {"to": "a@b.test"})


async def test_a_server_nobody_configured_is_refused_before_a_socket_is_opened(
    connector: McpToolCaller,
) -> None:
    with pytest.raises(ToolsUnavailable, match="no connector called erp"):
        await connector.call(ACME, "erp", "anything", {})

    assert _Server.seen == []


async def test_a_connector_that_needs_a_session_is_greeted_first(
    connector: McpToolCaller,
) -> None:
    """Every real MCP server built on the standard SDK needs this, and our own
    /mcp endpoint answered "Bad Request: Missing session ID" to a client that
    went straight to `tools/list`. So the stub above was the only server this
    could ever talk to -- a connector that worked in its own test and nowhere
    a tenant would actually point it.
    """
    _Server.mode = "session"

    offered = await connector.list_tools(ACME, "mail")

    assert [tool.name for tool in offered] == ["send_message"]
    greeted = [request["method"] for request in _Server.seen]
    assert greeted[0] == "initialize", f"it asked before it greeted: {greeted}"
    assert "notifications/initialized" in greeted, greeted
    assert greeted[-1] == "tools/list"


async def test_the_session_is_carried_on_the_call_itself(connector: McpToolCaller) -> None:
    """Not only on the handshake. A server that hands one back expects it on
    everything after, and a send that arrived without it would be refused at
    the one moment the step cannot be retried."""
    _Server.mode = "session"

    result = await connector.call(ACME, "mail", "send_message", {"to": "rudy", "body": "hello"})

    assert not result.failed, result.detail
    assert "sent" in result.text


# -- one tenant's grant, and no other ------------------------------------------


async def test_two_tenants_reach_the_connector_with_their_own_grant(
    connector: McpToolCaller,
) -> None:
    """The property this adapter exists for, and it did not hold until
    2026-09-16: the bearer was one string in deployment config, so every
    tenant's step reached the same connector holding the same person's grant.

    Nothing had noticed because nothing had called it -- MCP was unreachable
    from a mined-workflow run, and the one path that did use it ran on a
    single-tenant deployment. This is the door shut before anything leaned on
    it.
    """
    await connector.call(ACME, "mail", "send_message", {"to": "a@b.test", "body": "hi"})
    assert _Server.seen[-1]["authorization"] == "Bearer acme-grant"

    await connector.call(OTHER, "mail", "send_message", {"to": "c@d.test", "body": "hi"})
    assert _Server.seen[-1]["authorization"] == "Bearer other-grant"


async def test_a_tenant_who_has_not_connected_reaches_nothing_at_all(
    connector: McpToolCaller,
) -> None:
    """Refused before a socket is opened, and refused as `NotConnected` rather
    than a bare `ToolsUnavailable` -- a console can turn the first into "connect
    Gmail", which a person can act on, and cannot act on the second.

    Refusing is the point. The old adapter called with whatever credential the
    deployment held, so a tenant who had connected nothing still reached
    somebody's mailbox.
    """
    before = len(_Server.seen)

    with pytest.raises(NotConnected):
        await connector.call(TenantId("a-third"), "mail", "send_message", {"to": "x@y.test"})

    assert len(_Server.seen) == before, "a request went out for a tenant with no grant"


async def test_a_deployment_with_no_vault_cannot_reach_a_connector_at_all(
    connector: McpToolCaller,
) -> None:
    """Stricter than before on purpose. With no vault there is nowhere for a
    per-tenant grant to live, so there is no way to call as one tenant rather
    than as all of them -- and calling anyway is what this change removed."""
    vaultless = McpToolCaller([McpServer(name="mail", url="http://127.0.0.1:1/mcp")])

    with pytest.raises(NotConnected):
        await vaultless.list_tools(ACME, "mail")
