from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[2] / "new-chrome-extension"
API = os.environ.get("SRO_API_URL", "http://localhost:8000")
CONSOLE = os.environ.get("SRO_CONSOLE_URL", "http://localhost:3000")
TOKEN = os.environ.get("SRO_TOKEN", "")

DEADLINE_S = 20.0
MAX_BUSY_WAIT = 0.5


def call(path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(  # noqa: S310
        f"{API}{path}",
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as answer:  # noqa: S310
            return json.loads(answer.read())
    except urllib.error.HTTPError as refused:
        problem = refused.read().decode()
        raise SystemExit(f"{path} answered {refused.code}: {problem}") from None


def held_in_stream(run_id: str, seconds: float = 6.0) -> dict | None:
    request = urllib.request.Request(  # noqa: S310
        f"{API}/v1/runs/{run_id}/stream", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    deadline = time.time() + seconds
    with urllib.request.urlopen(request, timeout=seconds) as stream:  # noqa: S310
        buffer = ""
        while time.time() < deadline:
            chunk = stream.readline().decode()
            if not chunk:
                break
            buffer += chunk
            if not buffer.endswith("\n\n") and "\n\n" not in buffer:
                continue
            for event in buffer.split("\n\n"):
                lines = event.splitlines()
                name = next((x[7:] for x in lines if x.startswith("event: ")), None)
                data = next((x[6:] for x in lines if x.startswith("data: ")), None)
                if name == "waiting" and data:
                    return json.loads(data)
            buffer = ""
    return None


def main() -> int:
    if not TOKEN:
        print("SRO_TOKEN is required; run this through `make verify-held`", file=sys.stderr)
        return 1

    from playwright.sync_api import sync_playwright

    with sync_playwright() as play:
        context = play.chromium.launch_persistent_context(
            tempfile.mkdtemp(prefix="sro-held-"),
            headless=False,
            channel="chromium",
            args=[f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}"],
            viewport={"width": 1280, "height": 900},
        )
        try:
            ident = ""
            for attempt in range(40):
                if context.service_workers:
                    ident = str(context.service_workers[0].url).split("/")[2]
                    break
                if attempt == 8:
                    context.new_page().goto("about:blank")
                time.sleep(0.25)
            if not ident:
                print("the extension's worker never started", file=sys.stderr)
                return 1
            print(f"1/6  extension loaded            {ident[:16]}…")

            panel = context.new_page()
            panel.goto(f"chrome-extension://{ident}/src/panel/panel.html")
            panel.evaluate(
                """([apiUrl, consoleUrl, token]) => new Promise((resolve) =>
                    chrome.runtime.sendMessage(
                        { kind: "sign-in", apiUrl, consoleUrl, token }, () => resolve(null)))""",
                [API, CONSOLE, TOKEN],
            )

            device, channel = "", ""
            for _ in range(60):
                state = panel.evaluate(
                    """() => new Promise((resolve) =>
                        chrome.runtime.sendMessage({ kind: "status" }, resolve))"""
                )
                device, channel = state.get("deviceId") or "", state.get("channel") or ""
                if device and channel == "open":
                    break
                time.sleep(0.5)
            if not device or channel != "open":
                print(f"the channel never opened (device={device!r} channel={channel!r})")
                return 1
            print(f"2/6  device registered, channel open   {device[:16]}…")

            work = context.new_page()
            work.goto(f"{CONSOLE}/overview")
            work.wait_for_timeout(1500)
            watched = panel.evaluate(
                """() => new Promise((resolve) =>
                    chrome.tabs.query({}, (tabs) => {
                      const tab = tabs.find((t) => t.url && t.url.includes("/overview"));
                      if (!tab) return resolve(false);
                      chrome.runtime.sendMessage(
                        { kind: "watch-tab", tabId: tab.id, url: tab.url }, () => resolve(true));
                    }))"""
            )
            print(f"3/6  tab watched                 {watched}")

            work.bring_to_front()
            for _ in range(6):
                work.mouse.click(600, 400)
                work.keyboard.type("x")
                time.sleep(0.15)
            print("4/6  a real gesture in the watched tab")

            skill, given = skill_to_run()
            run = call(
                f"/v1/skills/{skill}/runs",
                {
                    "parameters": given,
                    "medium": "ui",
                    "device_id": device,
                    "may_take_focus": False,
                },
            )
            print(f"5/6  run started, answered while running   {run['id'][:20]}… {run['status']}")

            waiting = held_in_stream(run["id"])
            if waiting is None:
                print("6/6  NO `waiting` event -- the chain is broken here", file=sys.stderr)
                return 1
            held = waiting.get("held_ms")
            if not held or held <= 0:
                print(f"6/6  a `waiting` event that says nothing: {waiting}", file=sys.stderr)
                return 1
            ceiling = DEADLINE_S * MAX_BUSY_WAIT * 1000
            if held > ceiling:
                print(
                    f"6/6  held_ms={held} is over the {ceiling:.0f} the backend honours",
                    file=sys.stderr,
                )
                return 1
            print(f"6/6  console told it is held     held_ms={held} (ceiling {ceiling:.0f})")
            return 0
        finally:
            context.close()


def skill_to_run() -> tuple[str, dict[str, str]]:
    for skill in call("/v1/skills"):
        if skill.get("latest_stage") != "shadow":
            continue
        detail = call(f"/v1/skills/{skill['id']}")
        version = detail["versions"][-1]
        given = {
            parameter["name"]: "sro-verify"
            for parameter in version.get("parameters", [])
            if parameter.get("kind") == "input"
        }
        return str(skill["id"]), given
    raise SystemExit("this tenant has no shadow skill to run harmlessly")


if __name__ == "__main__":
    raise SystemExit(main())
