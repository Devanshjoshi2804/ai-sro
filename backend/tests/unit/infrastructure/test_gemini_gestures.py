"""The model answers with a function call, and that is data crossing a boundary.

The computer-use model refuses a plain JSON schema outright (400: "This model
requires the use of the Computer Use tool"), so what comes back is a named call
from its own predefined set. These are the rules for turning one into a gesture.
"""

from __future__ import annotations

from typing import Any

from sro.application.ports.vision import Screen
from sro.domain.recording.events import ActionKind
from sro.infrastructure.gemini.computer_use import _gesture

SCREEN = Screen(image=b"png", mime_type="image/png", width=1280, height=800)
ALLOWED = (ActionKind.CLICK, ActionKind.SCROLL, ActionKind.HOVER)


def _call(name: str, **args: Any) -> Any:
    return _gesture(name, args, "because the button is there", SCREEN, ALLOWED)


def test_a_normalised_coordinate_becomes_a_pixel_on_this_screen() -> None:
    """The model answers in 0-1000, which is a different pixel on every
    viewport, so it is converted at the boundary rather than carried inwards."""
    gesture = _call("click_at", x=500, y=250)

    assert (gesture.x, gesture.y) == (640, 200)


def test_a_function_this_driver_cannot_perform_is_refused_not_approximated() -> None:
    gesture = _call("drag_and_drop", x=1, y=2)

    assert gesture.refusal is not None
    assert "drag_and_drop" in gesture.refusal


def test_a_gesture_outside_what_the_step_allows_is_refused() -> None:
    gesture = _gesture("type_text_at", {"x": 1, "y": 2, "text": "48"}, "", SCREEN, ALLOWED)

    assert gesture.refusal is not None, "a step demonstrated as a click stays a click"


def test_typed_text_is_carried_from_whichever_argument_holds_it() -> None:
    gesture = _gesture(
        "type_text_at", {"x": 1, "y": 2, "text": "48"}, "", SCREEN, (ActionKind.TYPE,)
    )

    assert gesture.value == "48"


def test_the_model_reasoning_is_kept_with_the_gesture() -> None:
    assert _call("click_at", x=1, y=2).reasoning == "because the button is there"


def test_a_call_with_no_coordinates_yields_none_rather_than_a_guess() -> None:
    gesture = _call("click_at")

    assert gesture.x is None and gesture.y is None
