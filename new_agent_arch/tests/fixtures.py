"""The extension's own committed fixtures, produced by a real browser test.

Parsing these is what proves the rig matches the protocol; a hand-retyped dict
would only prove somebody retyped it consistently.
"""

import json
from pathlib import Path

FIXTURES = (
    Path(__file__).parent.parent.parent / "new-chrome-extension" / "fixtures"
)


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


BATCH = load("batch")
GESTURE_TYPE = load("gesture-type")
GESTURE_CLICK = load("gesture-click")
GESTURE_SECRET = load("gesture-secret")
REQUEST_POST = load("request-post")
REQUEST_FAILED = load("request-failed")
PAGE_NAVIGATED = load("page-navigated")
