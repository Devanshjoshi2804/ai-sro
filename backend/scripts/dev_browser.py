"""A browser with the extension loaded, for working on this by hand.

Chrome under an enterprise policy refuses an unpacked extension — the whole
point of the policy — so this uses the Chromium that Playwright already
installed for the browser tests, which no policy governs. Same launch the tests
do, with two differences: it is headed, and the profile lives somewhere durable
so a WMS login and the extension's settings survive a restart.

    make dev-browser

Nothing here is part of the product. It is a way to hold it.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[2] / "new-chrome-extension"
PROFILE = Path.home() / ".sro-dev-browser"
CONSOLE = os.environ.get("SRO_CONSOLE_URL", "http://localhost:3000")
API = os.environ.get("SRO_API_URL", "http://localhost:8000")
TOKEN = os.environ.get("SRO_TOKEN", "")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed here: uv sync --group dev", file=sys.stderr)
        return 1

    PROFILE.mkdir(exist_ok=True)
    print(f"extension  {EXTENSION}")
    print(f"profile    {PROFILE}")
    print("\nThe window stays open until you close it or press ctrl-c here.\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=False,
            channel="chromium",
            viewport=None,
            args=[
                f"--disable-extensions-except={EXTENSION}",
                f"--load-extension={EXTENSION}",
            ],
        )
        # The extension's pages are addressed by an id Chrome assigns at load,
        # and the service worker is where it appears first. It starts a moment
        # after the window does.
        ident = _extension_id(context)
        page = context.pages[0] if context.pages else context.new_page()

        if ident and TOKEN:
            # Signed in rather than typed, and through the message the options
            # form sends rather than by writing storage: registering the device,
            # clearing whatever the last credential left, and starting the
            # command channel all hang off that message. Storage alone would
            # leave a browser that holds a token and is not a device.
            options = context.new_page()
            options.goto(f"chrome-extension://{ident}/src/options/options.html")
            said = options.evaluate(
                """([apiUrl, consoleUrl, token]) => new Promise((resolve) =>
                    chrome.runtime.sendMessage(
                        { kind: "sign-in", apiUrl, consoleUrl, token },
                        (answer) => resolve(answer ?? { error: "no answer" }),
                    ))""",
                [API, CONSOLE, TOKEN],
            )
            options.reload()
            print(f"signed in     {said}")
        elif ident:
            print("no SRO_TOKEN in the environment, so the options page is yours to fill in")

        if ident:
            print(f"extension id  {ident}")
            print(f"options       chrome-extension://{ident}/src/options/options.html")
        page.goto(CONSOLE)
        try:
            page.wait_for_event("close", timeout=0)
        except KeyboardInterrupt:
            pass
        except Exception:
            pass
        finally:
            context.close()
    return 0


def _extension_id(context: object) -> str:
    """The id Chrome gave the unpacked extension, once its worker is up."""
    for _ in range(40):
        workers = context.service_workers  # type: ignore[attr-defined]
        if workers:
            return str(workers[0].url).split("/")[2]
        time.sleep(0.25)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
