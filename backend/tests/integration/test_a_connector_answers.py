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

from sro.application.ports.tools import ToolsUnavailable
from sro.infrastructure.mcp.client import McpServer, McpToolCaller

TOKEN = "a-token"  # noqa: S105 -- what this stub asks for, not a credential

TOOLS = {
    "tools": [
        {
            "name": "send_message",
            "description": "Send a mail",
            "inputSchema": {"properties": {"to": {"type": "string"}, "body": {"type": "string"}}},
        }
    ]
}


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

    def _reply(self, code: int, body: bytes, kind: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def connector() -> Any:
    _Server.mode = "json"
    _Server.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Server)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    yield McpToolCaller([McpServer(name="mail", url=f"http://{host}:{port}/mcp", token=TOKEN)])
    server.shutdown()
    server.server_close()


async def test_a_connector_says_what_it_offers(connector: McpToolCaller) -> None:
    offered = await connector.list_tools("mail")

    assert [tool.name for tool in offered] == ["send_message"]
    assert set(offered[0].arguments) == {"to", "body"}


async def test_calling_one_sends_the_arguments_and_the_credential(
    connector: McpToolCaller,
) -> None:
    answered = await connector.call("mail", "send_message", {"to": "a@b.test", "body": "hi"})

    assert json.loads(answered.text) == {"status": "sent", "to": "a@b.test", "body": "hi"}
    assert answered.failed is False
    assert _Server.seen[-1]["authorization"] == f"Bearer {TOKEN}"


async def test_an_answer_that_arrives_as_an_event_stream_reads_the_same(
    connector: McpToolCaller,
) -> None:
    _Server.mode = "sse"

    answered = await connector.call("mail", "send_message", {"to": "a@b.test", "body": "hi"})

    assert json.loads(answered.text)["status"] == "sent"


async def test_a_tool_that_refuses_is_an_answer_rather_than_an_exception(
    connector: McpToolCaller,
) -> None:
    """The escalation table treats "it refused" and "there was nothing to ask"
    differently, and both arriving as an exception would collapse them."""
    _Server.mode = "refuses"

    answered = await connector.call("mail", "send_message", {"to": "a@b.test"})

    assert answered.failed is True
    assert "no mailbox" in answered.detail


async def test_a_connector_that_answers_rubbish_is_unavailable_rather_than_a_crash(
    connector: McpToolCaller,
) -> None:
    _Server.mode = "broken"

    with pytest.raises(ToolsUnavailable):
        await connector.call("mail", "send_message", {"to": "a@b.test"})


async def test_a_server_nobody_configured_is_refused_before_a_socket_is_opened(
    connector: McpToolCaller,
) -> None:
    with pytest.raises(ToolsUnavailable, match="no connector called erp"):
        await connector.call("erp", "anything", {})

    assert _Server.seen == []
