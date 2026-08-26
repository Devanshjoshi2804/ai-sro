"""A picture of the side panel, for working on how it looks.

The panel is an extension page, so it cannot be opened by URL in an ordinary
browser and cannot be seen without loading the extension. This loads it the way
the tests do, signs it in against whatever is running locally, opens the panel
at the width Chrome gives it, and writes a PNG.

    make panel-shot            # /tmp/panel.png
    make panel-shot at=here    # a tab on `here` first, so the panel has a host
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[2] / "new-chrome-extension"
OUT = Path(os.environ.get("SRO_SHOT", "/tmp/panel.png"))
API = os.environ.get("SRO_API_URL", "http://localhost:8000")
CONSOLE = os.environ.get("SRO_CONSOLE_URL", "http://localhost:3000")
TOKEN = os.environ.get("SRO_TOKEN", "")
BESIDE = os.environ.get("SRO_BESIDE", "")


def main() -> int:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            # A profile of its own each time: storage persists, so a shot of
            # the unconnected state taken in yesterday's profile is a shot of
            # yesterday's sign-in.
            tempfile.mkdtemp(prefix="sro-panel-"),
            headless=False,
            channel="chromium",
            args=[f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}"],
            viewport={"width": 420, "height": 900},
        )
        # The worker starts when something asks it to. A page on the extension's
        # own origin is enough, and its id is the one thing not known yet -- so
        # the worker is waited for, and then woken by opening a tab if it has
        # not started on its own.
        ident = ""
        for attempt in range(40):
            if context.service_workers:
                ident = str(context.service_workers[0].url).split("/")[2]
                break
            if attempt == 8:
                context.new_page().goto("about:blank")
            time.sleep(0.25)
        if not ident:
            # Chrome lists it even when it has not been woken.
            page = context.new_page()
            page.goto("chrome://extensions/")
            found = page.evaluate(
                """() => {
                    const manager = document.querySelector("extensions-manager");
                    const items = manager?.shadowRoot?.querySelectorAll("extensions-item") ?? [];
                    return [...items].map((item) => item.id);
                }"""
            )
            ident = found[0] if found else ""
            page.close()
        if not ident:
            print("the extension's worker never started", file=sys.stderr)
            return 1

        panel = context.new_page()
        panel.goto(f"chrome-extension://{ident}/src/panel/panel.html")
        if TOKEN:
            panel.evaluate(
                """([apiUrl, consoleUrl, token]) => new Promise((resolve) =>
                    chrome.runtime.sendMessage(
                        { kind: "sign-in", apiUrl, consoleUrl, token }, () => resolve(null)))""",
                [API, CONSOLE, TOKEN],
            )
        if BESIDE and os.environ.get("SRO_TEACHING"):
            # A demonstration in progress: the state with the most to show and
            # the most tedious to reach by hand.
            beside = context.new_page()
            beside.goto(BESIDE)
            beside.wait_for_timeout(2500)
            panel.evaluate(
                """(url) => new Promise((resolve) =>
                    chrome.tabs.query({}, (tabs) => {
                        const tab = tabs.find((each) => (each.url || "").startsWith(url));
                        chrome.runtime.sendMessage(
                            { kind: "teach-start", tabId: tab?.id, label: "a demonstration" },
                            () => resolve(null));
                    }))""",
                BESIDE,
            )
            beside.bring_to_front()
            beside.mouse.click(200, 200)
            beside.wait_for_timeout(2500)
        elif BESIDE:
            beside = context.new_page()
            beside.goto(BESIDE)
            beside.wait_for_timeout(1500)
        panel.bring_to_front()
        panel.reload()
        panel.wait_for_timeout(6000)
        panel.screenshot(path=str(OUT), full_page=True)
        print(f"wrote {OUT}")
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
