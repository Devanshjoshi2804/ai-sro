"""The model's answer is data crossing a trust boundary."""

from __future__ import annotations

import json

from sro.application.ports.vision import Screen
from sro.domain.recording.events import ActionKind
from sro.infrastructure.gemini.computer_use import _gesture

SCREEN = Screen(image=b"png", mime_type="image/png", width=1280, height=800)
ALLOWED = (ActionKind.CLICK, ActionKind.SCROLL, ActionKind.HOVER)


def _answer(**fields: object) -> str:
    return json.dumps(fields)


def test_a_normalised_coordinate_becomes_a_pixel_on_this_screen() -> None:
    """0-1000 means a different point on every viewport, so it is converted at
    the boundary rather than carried inwards."""
    gesture = _gesture(_answer(action="click_at", x=500, y=250, reasoning="here"), SCREEN, ALLOWED)

    assert (gesture.x, gesture.y) == (640, 200)


def test_an_action_this_driver_cannot_perform_is_refused_not_approximated() -> None:
    gesture = _gesture(_answer(action="drag_and_drop", reasoning="move it"), SCREEN, ALLOWED)

    assert gesture.refusal is not None
    assert "drag_and_drop" in gesture.refusal


def test_an_action_outside_what_the_step_allows_is_refused() -> None:
    answer = _answer(action="navigate", value="http://x", reasoning="go")
    gesture = _gesture(answer, SCREEN, ALLOWED)

    assert gesture.refusal is not None, "a demonstrated click cannot become a navigation"


def test_an_answer_that_is_not_a_gesture_is_a_refusal() -> None:
    assert _gesture("not json at all", SCREEN, ALLOWED).refusal is not None
    assert _gesture(None, SCREEN, ALLOWED).refusal is not None


def test_the_model_declining_is_carried_through_verbatim() -> None:
    gesture = _gesture(
        _answer(action="click_at", refusal="the screen is not the one described", reasoning=""),
        SCREEN,
        ALLOWED,
    )

    assert gesture.refusal == "the screen is not the one described"


def test_done_is_carried_as_a_claim_with_its_reasoning() -> None:
    gesture = _gesture(
        _answer(action="click_at", done=True, reasoning="the quantity already reads 48"),
        SCREEN,
        ALLOWED,
    )

    assert gesture.done and "already reads 48" in gesture.reasoning
