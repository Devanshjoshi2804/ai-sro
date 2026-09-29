from __future__ import annotations

import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

SESSION = uuid.uuid4().hex

MAILBOX: list[dict[str, str]] = [
    {
        "id": "msg-1",
        "from": "devansh.j@greyorange.com",
        "to": "warehouse@greyorange.com",
        "subject": "Create a supplier with these details",
        "body": (
            "Create a supplier of name TestYonder2\n"
            "And client name is NEWTEST19\n"
            "RECIVING STTAUS is 008 Bramp-Conv\n"
            "Address of supplier 12900 CAROL COURT FRANKSVILLE 53126"
        ),
    },
    {
        "id": "msg-2",
        "from": "warehouse@greyorange.com",
        "to": "devansh.j@greyorange.com",
        "subject": "Weekly counts",
        "body": "Nothing to action.",
    },
]

SENT: list[dict[str, str]] = []

TOOLS = [
    {
        "name": "search_threads",
        "description": "Find mails whose subject or body contains a phrase.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "get_message",
        "description": "One mail, in full, by id.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "send_message",
        "description": "Send a mail. The least reversible thing here.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "body"],
        },
    },
]


def _call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "search_threads":
        term = str(arguments.get("query", "")).lower()
        found = [
            mail
            for mail in MAILBOX
            if term in mail["subject"].lower() or term in mail["body"].lower()
        ]
        return _text(json.dumps({"messages": found}, indent=1))
    if name == "get_message":
        wanted = str(arguments.get("id", ""))
        mail = next((m for m in MAILBOX if m["id"] == wanted), None)
        if mail is None:
            return {"content": [{"type": "text", "text": f"no mail {wanted}"}], "isError": True}
        return _text(json.dumps(mail, indent=1))
    if name == "send_message":
        SENT.append(dict(arguments))
        print(f"  → sent to {arguments.get('to')}: {arguments.get('subject', '(no subject)')}")
        return _text(json.dumps({"status": "sent", "id": f"sent-{len(SENT)}"}))
    return {"content": [{"type": "text", "text": f"no tool called {name}"}], "isError": True}


def _text(body: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": body}]}


class Connector(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:
        return

    def do_POST(self) -> None:
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        request = json.loads(raw or b"{}")
        method = request.get("method", "")
        print(f"{method}  session={self.headers.get('Mcp-Session-Id', '-')[:8]}")

        if method == "initialize":
            self._reply(
                200,
                self._envelope(
                    request.get("id"),
                    {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "mock-mail", "version": "1"},
                    },
                ),
                session=SESSION,
            )
            return

        if self.headers.get("Mcp-Session-Id") != SESSION:
            self._reply(
                200,
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {"code": -32600, "message": "Bad Request: Missing session ID"},
                    }
                ).encode(),
            )
            return

        if method == "notifications/initialized":
            self._reply(202, b"")
            return
        if method == "tools/list":
            self._reply(200, self._envelope(request.get("id"), {"tools": TOOLS}))
            return
        if method == "tools/call":
            params = request.get("params", {})
            result = _call(params.get("name", ""), params.get("arguments", {}))
            self._reply(200, self._envelope(request.get("id"), result))
            return

        self._reply(
            200,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32601, "message": f"no method {method}"},
                }
            ).encode(),
        )

    def _envelope(self, ident: Any, result: dict[str, Any]) -> bytes:
        return json.dumps({"jsonrpc": "2.0", "id": ident, "result": result}).encode()

    def _reply(self, code: int, body: bytes, session: str = "") -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if session:
            self.send_header("Mcp-Session-Id", session)
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8931
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Connector)
    except OSError as taken:
        print(f"port {port} is already in use ({taken.strerror}).")
        print(f"  what has it:  lsof -ti :{port}")
        print(f"  free it:      lsof -ti :{port} | xargs kill")
        print(f"  or pick another: uv run python {sys.argv[0]} {port + 1}")
        raise SystemExit(1) from taken

    print(f"mail connector on http://localhost:{port}/mcp   session={SESSION[:8]}…")
    print("point the system at it with:")
    print(f'  SRO_MCP_SERVERS="mail=http://localhost:{port}/mcp"')
    print("set in the API's own environment -- a shell variable set beside it")
    print("reaches nothing, because the API reads its settings in its own process.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
