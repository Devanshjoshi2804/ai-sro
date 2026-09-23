from __future__ import annotations

import os
import sys
from pathlib import Path

CONSOLE = os.environ.get("SRO_CONSOLE_URL", "http://localhost:3000")
TOKEN = os.environ.get("SRO_TOKEN", "")
OUT = Path(os.environ.get("SRO_SHOTS", "/tmp/sro-shots"))

ROUTES = (
    "/console",
    "/knowledge",
    "/triggers",
    "/overview",
)

WIDTHS = (1512, 900, 560)


def main() -> int:
    if not TOKEN:
        print("SRO_TOKEN is required; run this through `make shots`", file=sys.stderr)
        return 1

    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    taken = 0

    with sync_playwright() as play:
        browser = play.chromium.launch(channel="chromium")
        try:
            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 1000})
                page = context.new_page()
                page.goto(f"{CONSOLE}/console", wait_until="domcontentloaded")
                page.evaluate("(token) => localStorage.setItem('sro.credential', token)", TOKEN)

                for route in ROUTES:
                    page.goto(f"{CONSOLE}{route}", wait_until="networkidle")
                    page.wait_for_timeout(1200)
                    name = route.strip("/").replace("/", "-") or "root"
                    page.screenshot(path=OUT / f"{name}-{width}.png", full_page=True)
                    taken += 1
                context.close()
        finally:
            browser.close()

    print(f"wrote {taken} shots to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
