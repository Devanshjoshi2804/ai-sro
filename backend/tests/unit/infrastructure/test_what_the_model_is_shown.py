"""The screen handed to the vision rung, in the coordinates it answers in.

Every gesture the model proposes is a number between 0 and 1000 that the caller
multiplies by the size reported here. Both of these were wrong at once, and
between them the rung could not hit anything: it aimed correctly at a menu and
clicked the empty space beneath it, twelve times, then reported that the screen
would not respond.
"""

from __future__ import annotations

from sro.infrastructure.steel.ui_driver import _TEXT_DIGEST


def test_the_digest_script_is_javascript_and_not_a_python_escape() -> None:
    """Without the `r` prefix Python turned the `\\n` in the final join into a
    real newline, JavaScript received an unterminated string, and every call
    raised SyntaxError into an `except` that answered with an empty digest --
    so the rung that prefers exact control names over pixels had been running
    on pixels alone since it was written."""
    assert "\\n" in _TEXT_DIGEST, "the newline must reach JavaScript as an escape"
    assert "\n');" not in _TEXT_DIGEST, "a real newline here is an unterminated JS string"


def test_controls_are_described_in_the_page_s_own_space() -> None:
    """The screenshot is of the page. A control inside an iframe that starts 90
    pixels down was described as though the iframe were the screen."""
    assert "page.dx" in _TEXT_DIGEST and "page.dy" in _TEXT_DIGEST
    assert "window.innerWidth" not in _TEXT_DIGEST, "the frame's own size is the wrong ruler"
