from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from typing import Literal

import httpx
from playwright.async_api import async_playwright

PROBE = "https://probe.example"


@dataclass(frozen=True, slots=True)
class Seen:
    second_session_live: bool
    same_cdp_endpoint: bool
    contexts_isolated: bool
    context_survives_disconnect: bool
    other_survives_release: bool


def verdict(seen: Seen) -> Literal["sessions", "contexts", "one-per-container"]:
    if seen.second_session_live and not seen.same_cdp_endpoint and seen.other_survives_release:
        return "sessions"
    if seen.contexts_isolated and seen.context_survives_disconnect:
        return "contexts"
    return "one-per-container"


async def _session(client: httpx.AsyncClient, base: str) -> dict[str, object]:
    made = (await client.post(f"{base}/v1/sessions", json={"timeout": 600_000})).json()
    for _ in range(10):
        body = (await client.get(f"{base}/v1/sessions/{made['id']}")).json()
        if str(body.get("status", "")).lower() == "live":
            return dict(body)
        await asyncio.sleep(0.5)
    return dict(body)


async def _cdp(client: httpx.AsyncClient, cdp: str) -> str:
    version = (await client.get(f"{cdp}/json/version")).json()
    path = httpx.URL(str(version["webSocketDebuggerUrl"])).path
    return f"ws://{httpx.URL(cdp).netloc.decode()}{path}"


async def probe(base: str, cdp: str) -> Seen:
    async with httpx.AsyncClient(timeout=30.0) as client:
        first = await _session(client, base)
        second = await _session(client, base)
        second_live = str(second.get("status", "")).lower() == "live"
        same_endpoint = first.get("websocketUrl") == second.get("websocketUrl")
        endpoint = await _cdp(client, cdp)
        async with async_playwright() as driver:
            browser = await driver.chromium.connect_over_cdp(endpoint)
            one, two = await browser.new_context(), await browser.new_context()
            await one.add_cookies([{"name": "who", "value": "one", "url": PROBE}])
            isolated = not await two.cookies(PROBE)
            raw = await browser.new_browser_cdp_session()
            made = await raw.send("Target.createBrowserContext", {"disposeOnDetach": False})
            target = await raw.send(
                "Target.createTarget",
                {"url": "about:blank", "browserContextId": made["browserContextId"]},
            )
            await browser.close()
            again = await driver.chromium.connect_over_cdp(endpoint)
            raw = await again.new_browser_cdp_session()
            targets = (await raw.send("Target.getTargets"))["targetInfos"]
            survives = any(one["targetId"] == target["targetId"] for one in targets)
            await again.close()
        await client.post(f"{base}/v1/sessions/{first['id']}/release")
        after = (await client.get(f"{base}/v1/sessions/{second['id']}")).json()
        other_alive = str(after.get("status", "")).lower() == "live"
        await client.post(f"{base}/v1/sessions/{second['id']}/release")
    return Seen(second_live, same_endpoint, isolated, survives, other_alive)


def main() -> None:
    seen = asyncio.run(probe(sys.argv[1], sys.argv[2]))
    print(json.dumps({"verdict": verdict(seen), **asdict(seen)}, indent=2))


if __name__ == "__main__":
    main()
