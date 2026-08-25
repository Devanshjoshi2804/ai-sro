#!/usr/bin/env python3
"""The frozen contract, with canned answers. Standard library only.

The extension is built against this so it never waits for the backend. When the
real endpoints land, change the backend URL in the options page and nothing else
should have to move -- and if something does, one of us broke the contract.

    python3 mock-server/server.py            # :8000
    python3 mock-server/server.py --port 8010 --disabled --exclude payroll.acme.com

See ../../docs/14-extension-protocol.md.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import struct
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

STATE: dict[str, object] = {}


def policy() -> dict[str, object]:
    return {
        "version": STATE["policy_version"],
        "capture_enabled": STATE["enabled"],
        "exclude_hosts": STATE["exclude"],
        "include_hosts": STATE["include"],
        "capture_screenshots": True,
        "screenshot_max_per_minute": 20,
        "capture_response_bodies": True,
        "max_body_bytes": 262144,
        "daily_budget_bytes": 524288000,
        "retention_days": 30,
    }


class Contract(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's spelling
        self._send(204, None)

    def do_GET(self) -> None:  # noqa: N802
        if "websocket" in self.headers.get("Upgrade", "").lower():
            return self._channel()
        if self.path == "/v1/agents/policy":
            return self._send(200, policy())
        if self.path == "/v1/agents":
            return self._send(200, list(STATE["devices"].values()))  # type: ignore[union-attr]
        return self._send(404, self._problem(404, "no such thing"))

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorised():
            return self._send(401, self._problem(401, "that credential was not accepted"))

        if self.path == "/v1/observations/artifacts":
            # multipart, so it is not read as JSON. The bytes are counted and
            # dropped: what the extension needs back is the key the real
            # backend would have written.
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length)
            stored = STATE["artifacts"]
            stored.append(len(raw))  # type: ignore[union-attr]
            self.log_message("artifact, %d bytes", len(raw))
            return self._send(
                201,
                {"uri": f"s3://mock/artifact-{len(stored)}.png", "size_bytes": len(raw)},  # type: ignore[arg-type]
            )

        body = self._body()

        if self.path == "/v1/agents/register":
            label = str(body.get("label", "a browser"))
            device_id = STATE["labels"].setdefault(label, f"dev_{uuid.uuid4().hex}")  # type: ignore[union-attr]
            STATE["devices"][device_id] = {  # type: ignore[index]
                "id": device_id,
                "label": label,
                "extension_version": body.get("extension_version", ""),
            }
            return self._send(
                201,
                {"device_id": device_id, "policy": policy(), "policy_version": policy()["version"]},
            )

        if re.fullmatch(r"/v1/agents/[^/]+/heartbeat", self.path):
            held = body.get("policy_version")
            behind = held is None or held != policy()["version"]
            return self._send(
                200,
                {
                    "policy_version": policy()["version"],
                    "policy": policy() if behind else None,
                    "pause": STATE["pause"],
                },
            )

        if self.path == "/v1/observations":
            events = body.get("events", [])
            STATE["batches"].append(body.get("batch_id"))  # type: ignore[union-attr]
            self.log_message("batch %s, %d events", body.get("batch_id"), len(events))
            return self._send(
                202,
                {
                    "batch_id": body.get("batch_id"),
                    "accepted": len(events),
                    "rejected": 0,
                    "problems": [],
                    "stored_at": f"s3://mock/{body.get('batch_id')}.ndjson",
                    "already_had_it": False,
                },
            )

        return self._send(404, self._problem(404, "no such thing"))

    def _channel(self) -> None:
        """Hold the command channel open and say what comes up it.

        No commands go down it: this is the contract's shape, not a scheduler.
        What it is for is the half the extension owns -- that it dials, that it
        authenticates in the subprotocol, and that its keepalive keeps arriving,
        which is what stops Chrome evicting the worker and taking the socket.
        """
        offered = [p.strip() for p in self.headers.get("Sec-WebSocket-Protocol", "").split(",")]
        digest = hashlib.sha1(  # noqa: S324 - the handshake is specified as SHA-1
            (self.headers["Sec-WebSocket-Key"] + _WS_GUID).encode()
        ).digest()
        self.send_response(101)
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", base64.b64encode(digest).decode())
        if offered:
            self.send_header("Sec-WebSocket-Protocol", offered[0])
        self.end_headers()
        self.wfile.flush()
        self.log_message("a browser opened the command channel")

        while True:
            header = self.rfile.read(2)
            if len(header) < 2 or (header[0] & 0x0F) == 8:
                self.log_message("the command channel closed")
                return
            size = header[1] & 0x7F
            if size == 126:
                size = struct.unpack(">H", self.rfile.read(2))[0]
            elif size == 127:
                size = struct.unpack(">Q", self.rfile.read(8))[0]
            mask = self.rfile.read(4) if header[1] & 0x80 else b""
            payload = bytearray(self.rfile.read(size))
            for index in range(len(payload)):
                if mask:
                    payload[index] ^= mask[index % 4]
            if (header[0] & 0x0F) == 1:
                self.log_message("channel: %s", bytes(payload).decode("utf-8", "replace")[:200])

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._authorised():
            return self._send(401, self._problem(401, "that credential was not accepted"))
        return self._send(200, {"batches": 0, "events": 0})

    # -- plumbing ------------------------------------------------------------

    def _authorised(self) -> bool:
        return self.headers.get("Authorization", "").startswith("Bearer ") and len(
            self.headers.get("Authorization", "")
        ) > len("Bearer ")

    def _body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            parsed = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _problem(self, status: int, detail: str) -> dict[str, object]:
        return {
            "type": f"https://ai-sro.dev/problems/{status}",
            "title": "Problem",
            "status": status,
            "detail": detail,
            "instance": self.path,
        }

    def _send(self, status: int, payload: object) -> None:
        raw = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        # The extension's origin is chrome-extension://<id>, which changes per
        # unpacked load, so the mock allows everything. The real backend names
        # the origin in SRO_CORS_ORIGINS.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--disabled", action="store_true", help="answer with capture switched off")
    parser.add_argument("--pause", action="store_true", help="answer heartbeats with pause=true")
    parser.add_argument("--exclude", nargs="*", default=["mail.google.com"])
    parser.add_argument("--only", nargs="*", default=[])
    args = parser.parse_args()

    STATE.update(
        policy_version=1,
        enabled=not args.disabled,
        exclude=list(args.exclude),
        include=list(args.only),
        pause=args.pause,
        devices={},
        labels={},
        batches=[],
        artifacts=[],
    )

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Contract)
    print(f"the contract, mocked, on http://127.0.0.1:{args.port}")  # noqa: T201
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
