from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import httpx
import websockets

APPROVE_EVERY_S = 1.0

WAS = "https://wms.example/orders"

ANSWERS: dict[str, dict[str, Any]] = {
    "ui.perform": {"performed": True, "matched_by": "component", "candidates": 1},
    "ui.perform_at": {"performed": True, "candidates": 1},
    "navigate": {"navigated": True},
    "http.send": {
        "status": 200,
        "headers": {"content-type": "application/json"},
        "body": '{"ok": true}',
    },
}


def _device_of(url: str) -> str:
    parts = [p for p in urlsplit(url).path.split("/") if p]
    if len(parts) < 3 or parts[0] != "v1" or parts[1] != "agents":
        raise SystemExit(f"not a commands URL: {url}")
    return parts[2]


async def approve_as_this_browser(url: str, token: str, secret: str) -> None:
    base = urlsplit(url)
    root = f"{'https' if base.scheme == 'wss' else 'http'}://{base.netloc}"
    device = _device_of(url)
    headers = {"Authorization": f"Bearer {token}", "X-Device-Secret": secret}
    answered: set[str] = set()

    async with httpx.AsyncClient(base_url=root, headers=headers, timeout=10.0) as http:
        while True:
            await asyncio.sleep(APPROVE_EVERY_S)
            try:
                waiting = await http.get("/v1/workflow-runs", params={"awaiting": "true"})
                waiting.raise_for_status()
                runs = waiting.json()
            except (httpx.HTTPError, ValueError) as problem:
                print(f"!! could not read the queue: {problem}")
                continue

            for run in runs if isinstance(runs, list) else []:
                run_id = str(run.get("id"))
                if run.get("device_id") != device or run_id in answered:
                    continue
                answered.add(run_id)
                tap = await http.post(
                    f"/v1/workflow-runs/{run_id}/approve", params={"device_id": device}
                )
                if tap.status_code == 200:
                    said = tap.json()
                    print(f"-> approved {run_id} step {said['order']} (first: {said['first']})")
                else:
                    print(f"!! approve {run_id} answered {tap.status_code}: {tap.text[:200]}")


async def serve(url: str, token: str, secret: str, *, refuse: bool) -> None:
    global WAS
    async with websockets.connect(url, subprotocols=["bearer", token, secret]) as socket:  # type: ignore[arg-type]
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
            elif kind == "navigate":
                WAS = str((command.get("payload") or {}).get("url") or WAS)
                answer = {"ok": True, "result": {"navigated": True}}
            elif kind == "ui.url":
                answer = {"ok": True, "result": {"url": WAS}}
            elif kind == "screenshot":
                answer = {
                    "ok": False,
                    "error": {
                        "kind": "focus_not_permitted",
                        "detail": "a stub has no screen to photograph",
                    },
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
    parser.add_argument("secret", help="the device_secret register returned; the socket checks it")
    parser.add_argument("--refuse", action="store_true", help="answer control_not_found")
    parser.add_argument(
        "--approve",
        action="store_true",
        help="also press Approve on this browser's own parked runs, as this browser",
    )
    args = parser.parse_args()
    asyncio.run(_both(args))
    return 0


async def _both(args: argparse.Namespace) -> None:
    socket = asyncio.create_task(serve(args.url, args.token, args.secret, refuse=args.refuse))
    if not args.approve:
        await socket
        return
    print(f"approving as {_device_of(args.url)}")
    approver = asyncio.create_task(approve_as_this_browser(args.url, args.token, args.secret))
    try:
        await socket
    finally:
        approver.cancel()


if __name__ == "__main__":
    raise SystemExit(main())
