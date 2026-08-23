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
import json
import re
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
        if self.path == "/v1/agents/policy":
            return self._send(200, policy())
        if self.path == "/v1/agents":
            return self._send(200, list(STATE["devices"].values()))  # type: ignore[union-attr]
        return self._send(404, self._problem(404, "no such thing"))

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorised():
            return self._send(401, self._problem(401, "that credential was not accepted"))

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
    )

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Contract)
    print(f"the contract, mocked, on http://127.0.0.1:{args.port}")  # noqa: T201
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
