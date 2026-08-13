"""A scroll between a click and its responses must not steal them.

Recorded twice against Blue Yonder, the same search fired several reads. In one
run a scroll landed in the middle of them, opened a frame of its own, and took
the tail of the search with it -- so the two runs attributed the same calls to
different steps and induction refused the pair.
"""

from __future__ import annotations

from sro.application.capture.assemble import assemble_frames
from sro.application.capture.events import InputEvent, RequestEvent
from sro.domain.recording.events import ActionKind, InputAction
from tests import factories as f


def test_a_scroll_mid_flight_leaves_the_calls_with_the_click() -> None:
    click = InputEvent(at=f.at(10), action=f.frame().action)
    first = RequestEvent(request=f.request(request_id="first", started_at=f.at(11)))
    scroll = InputEvent(at=f.at(12), action=InputAction(kind=ActionKind.SCROLL))
    second = RequestEvent(request=f.request(request_id="second", started_at=f.at(13)))

    result = assemble_frames([click, first, scroll, second])

    assert len(result.frames) == 1, "a scroll is not a step"
    assert [r.request_id for r in result.frames[0].requests] == ["first", "second"]
