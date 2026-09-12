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

Pass --approve and it also presses Approve, **as itself**. That is the one
check `approver_is_the_driver` exists for and the one thing nothing in this
repository had ever exercised: every approval ever recorded here was tapped
with the tenant's bare credential, naming no browser, which is the
supervisor's-console path and skips the check entirely. A stub holding a
socket already holds the two things a real panel proves itself with -- the
`device_id` in the URL it dialled and the `X-Device-Secret` it dialled with --
so it can send the pair, and the row it leaves names a browser.

What it still is not: a Chrome. The panel's own `rigApprove` is not exercised
by this, and a warehouse that can show its own write back is what a `held`
outcome needs. This closes the backend half of steps 8 and 9, not the browser
half.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from urllib.parse import urlsplit

import httpx
import websockets

APPROVE_EVERY_S = 1.0
"""How often the approver asks whether anything is parked on a person.

A poll and not a push, because there is no channel for this: the command
socket carries commands TO a browser, and a parked run sends nothing down it
-- `run_workflow` is sitting on an `asyncio.Event` and the panel a real
operator uses polls too. One second against `K_APPROVAL_WAIT_S`, so a run
parks and is answered well inside its own patience."""

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


def _device_of(url: str) -> str:
    """The browser this socket is, read off the URL it dialled.

    `/v1/agents/<device_id>/commands`. Taken from the URL rather than asked
    for as a flag because these are the same id by construction: a stub that
    could be told a different one is a stub that can approve for a browser it
    is not -- which is the exact thing the check under test refuses, and a
    test rig must not be able to fake the thing it is proving.
    """
    parts = [p for p in urlsplit(url).path.split("/") if p]
    if len(parts) < 3 or parts[0] != "v1" or parts[1] != "agents":
        raise SystemExit(f"not a commands URL: {url}")
    return parts[2]


async def approve_as_this_browser(url: str, token: str, secret: str) -> None:
    """Press Approve on this browser's own parked runs, as this browser.

    Both halves of the pair or neither: `?device_id=` in the query and
    `X-Device-Secret` in the header. Half of it is `asking_device`'s 404, and
    NEITHER is the console path -- a silent 200 recording an approval by
    nobody, on the door whose whole job is recording who let the write out.

    Only this browser's runs are tapped, and the filter is here rather than
    left to the 403. The queue is the tenant's: `?awaiting=true` answers with
    every parked run of every browser, deliberately, so that a supervisor can
    clear any of them. A stub that tapped all of them would be answering for
    windows it is not driving, get `NotDrivingThisRun` for its trouble, and
    bury the one answer that matters in 403s.
    """
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
                # The API restarting under a stub that outlives it is the
                # ordinary case, not an error worth dying of: a poller that
                # exits on the first refused connection takes the socket with
                # it and the run it was going to answer parks out its wait.
                print(f"!! could not read the queue: {problem}")
                continue

            for run in runs if isinstance(runs, list) else []:
                run_id = str(run.get("id"))
                if run.get("device_id") != device or run_id in answered:
                    continue
                # Recorded before the call, not after. A tap that reaches the
                # backend and then fails to answer -- a dropped socket, a
                # timeout -- has still let the write out, and a retry would
                # tap a second time on a run that parked again for a different
                # reason.
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
    parser.add_argument(
        "--approve",
        action="store_true",
        help="also press Approve on this browser's own parked runs, as this browser",
    )
    args = parser.parse_args()
    asyncio.run(_both(args))
    return 0


async def _both(args: argparse.Namespace) -> None:
    """The socket, and optionally the approver beside it.

    The socket is the one that decides when this process is done: a stub whose
    command channel closed has stopped being a browser, and an approver still
    polling for a browser that is gone would answer for a run nothing is
    driving. So the poller is cancelled with it rather than waited on.
    """
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
