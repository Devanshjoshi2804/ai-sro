"""A gesture that changes nothing has to be told to the thing that made it.

The first live pursuit clicked within a few pixels of the same point eight
times and stopped only when the budget ran out. It was handed its own past
coordinates and no outcome at all, so nothing distinguished a click that opened
a form from a click on the page background.
"""

from __future__ import annotations

from sro.application.execution.pursue_goal import _STUCK


def test_giving_up_takes_fewer_tries_than_the_budget() -> None:
    """Otherwise "stuck" and "still working" are the same thing to watch.

    A model that has not moved the screen in three gestures is not about to,
    and spending the rest of the budget proves it slowly while a browser sits
    open on somebody's warehouse.
    """
    from sro.application.execution.pursue_goal import GESTURE_BUDGET

    assert _STUCK < GESTURE_BUDGET
