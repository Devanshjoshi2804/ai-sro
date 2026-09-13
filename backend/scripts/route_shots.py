"""A picture of every screen, at three widths, for comparing before and after.

There is no visual regression suite and this is not one. It is the smallest
thing that makes a change to 314 inline styles reviewable: shoot every route
before touching anything, shoot them again after, and look at the pairs.

    make shots out=/tmp/before
    …change something…
    make shots out=/tmp/after

A console that breaks quietly breaks in one state on one width, which is
exactly what nobody checks by hand.

Not every difference is a change you made. These shoot live data, so a route
whose rows carry timestamps, counts or a capture still in progress differs
between two runs of this script with nothing edited in between -- Recordings and
Skills both do. The way to tell: shoot twice without changing anything and diff
those, then treat that set as noise.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

CONSOLE = os.environ.get("SRO_CONSOLE_URL", "http://localhost:3000")
TOKEN = os.environ.get("SRO_TOKEN", "")
OUT = Path(os.environ.get("SRO_SHOTS", "/tmp/sro-shots"))

ROUTES = (
    # Bar order, left to right, so a contact sheet reads the way the nav does.
    # `/waiting` was missing here while its page existed, which is the failure
    # this list is for: a route nobody shoots is a route nobody compares.
    "/console",
    "/waiting",
    "/needs",
    "/overview",
    "/jobs",
    "/recordings",
    "/runs",
    "/triggers",
    "/browsers",
    "/audit",
    "/spend",
    "/knowledge",
)

WIDTHS = (1512, 900, 560)
"""Desktop, a narrow laptop, and the width where the bar and the tables stop
fitting -- which is where this product's layout problems have all been."""


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
                # The credential is per origin, so it is planted once and every
                # route after this one is already signed in.
                page.goto(f"{CONSOLE}/console", wait_until="domcontentloaded")
                page.evaluate("(token) => localStorage.setItem('sro.credential', token)", TOKEN)

                for route in ROUTES:
                    page.goto(f"{CONSOLE}{route}", wait_until="networkidle")
                    # A table that is still fetching is a skeleton, and a
                    # skeleton compared against a table is a diff on every row.
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
