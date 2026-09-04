"""The extension's own committed fixtures, produced by a real browser test.

Parsing these is what proves the rig matches the protocol; a hand-retyped dict
would only prove somebody retyped it consistently.
"""

import json
from pathlib import Path


def repo_root() -> Path:
    """The checkout, found by looking up rather than by counting `.parent`.

    A fixed count is right from `new_agent_arch/tests/` and wrong from
    anywhere else, and a mutation run copies this whole suite into
    `new_agent_arch/mutants/tests/` -- one directory deeper, so every fixture
    load failed and every test in the file errored out rather than being
    reported as a surviving mutant.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "new-chrome-extension").is_dir():
            return parent
    raise RuntimeError(f"no checkout above {__file__}")


FIXTURES = repo_root() / "new-chrome-extension" / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


BATCH = load("batch")
GESTURE_TYPE = load("gesture-type")
GESTURE_CLICK = load("gesture-click")
GESTURE_SECRET = load("gesture-secret")
REQUEST_POST = load("request-post")
REQUEST_FAILED = load("request-failed")
PAGE_NAVIGATED = load("page-navigated")
SNAPSHOT = load("snapshot")
