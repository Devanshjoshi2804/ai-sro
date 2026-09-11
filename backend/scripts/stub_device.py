"""A browser that isn't.

Holds the command channel open and answers whatever is sent down it, so the
backend half can be exercised before the extension's own client exists -- and
afterwards, when the question is whether a failure is ours or Chrome's.

    make token tenant=acme principal=you
    curl -s -X POST localhost:8000/v1/agents/register \
      -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      -d '{"label":"stub"}'
    uv run python scripts/stub_device.py \
      ws://localhost:8000/v1/agents/<device>/commands $TOKEN $DEVICE_SECRET

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

WAS = "https://wms.example/orders"
"""Where this browser that isn't is standing.

`ui.url` used to answer a constant, and a constant is a browser that never goes
anywhere: the runner navigates, asks where it is, is told the old page, and
calls the step failed with *the browser is currently on the wrong page*. It
never got past step 1 of a job whose first step is in the mail. So `navigate`
moves this, and `ui.url` reads it -- the least a stub can do and still be a
place.
"""

ANSWERS: dict[str, dict[str, Any]] = {
    "ui.perform": {"performed": True, "matched_by": "component", "candidates": 1},
    "ui.perform_at": {"performed": True, "candidates": 1},
    # The runner's other leaf. A step whose plan is `navigate` got
    # `unsupported: navigate` from here and failed the whole run at step 1,
    # because this map was written before `plan_step` learnt to move the tab
    # itself. `commands.js:511` is what a real browser answers.
    "navigate": {"navigated": True},
    "http.send": {
        "status": 200,
        "headers": {"content-type": "application/json"},
        "body": '{"ok": true}',
    },
}


async def serve(url: str, token: str, secret: str, *, refuse: bool) -> None:
    global WAS
    # Three protocols, not two. The socket stopped taking a tenant bearer alone
    # when `commands` began reading `protocols[2]` as the device secret: a valid
    # credential is not ownership, and a socket that let one stand in for the
    # other would hand any of a tenant's tokens the command channel of any of
    # its browsers. Called with two, the handshake is refused with a 403 that
    # says nothing -- deliberately, so a wrong secret and an absent device
    # close the same way.
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
                # Refused, not faked. `look()` reads a refusal as "no picture"
                # and plans from the url and the digest, which is exactly the
                # degraded path a real browser takes when the page to be driven
                # is not the visible one. A fabricated PNG would instead send
                # the model a picture of nothing and invite it to click in it.
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
    args = parser.parse_args()
    asyncio.run(serve(args.url, args.token, args.secret, refuse=args.refuse))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
