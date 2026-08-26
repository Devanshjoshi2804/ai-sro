"""A browser that isn't.

Holds the command channel open and answers whatever is sent down it, so the
backend half can be exercised before the extension's own client exists -- and
afterwards, when the question is whether a failure is ours or Chrome's.

    make token tenant=acme principal=you
    curl -s -X POST localhost:8000/v1/agents/register \
      -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      -d '{"label":"stub"}'
    uv run python scripts/stub_device.py ws://localhost:8000/v1/agents/<device>/commands $TOKEN

Every answer is a success, on purpose: what this proves is the path, not the
page. Pass --refuse to have it answer `control_not_found` instead, which is how
the escalation policy is exercised without a browser.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import websockets

ANSWERS: dict[str, dict[str, Any]] = {
    "ui.perform": {"performed": True, "matched_by": "component", "candidates": 1},
    "ui.perform_at": {"performed": True, "candidates": 1},
    "ui.url": {"url": "https://wms.example/orders"},
    "http.send": {
        "status": 200,
        "headers": {"content-type": "application/json"},
        "body": '{"ok": true}',
    },
}


async def serve(url: str, token: str, *, refuse: bool) -> None:
    async with websockets.connect(url, subprotocols=["bearer", token]) as socket:  # type: ignore[arg-type]
        print("connected; waiting for commands")
        async for raw in socket:
            command = json.loads(raw)
            kind = str(command.get("kind"))
            print(f"<- {kind} {json.dumps(command.get('payload'))[:120]}")

            if refuse and kind.startswith("ui."):
                answer: dict[str, Any] = {
                    "ok": False,
                    "error": {"kind": "control_not_found", "detail": "the stub refuses"},
                }
            elif kind in ANSWERS:
                answer = {"ok": True, "result": ANSWERS[kind]}
            else:
                answer = {"ok": False, "error": {"kind": "unsupported", "detail": kind}}

            await socket.send(json.dumps({"command_id": command["command_id"], **answer}))


def main() -> int:
    parser = argparse.ArgumentParser(description="Answer commands as if it were a browser.")
    parser.add_argument("url", help="ws://localhost:8000/v1/agents/<device_id>/commands")
    parser.add_argument("token")
    parser.add_argument("--refuse", action="store_true", help="answer control_not_found")
    args = parser.parse_args()
    asyncio.run(serve(args.url, args.token, refuse=args.refuse))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
