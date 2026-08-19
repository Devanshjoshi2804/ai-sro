"""Clicking Save once can change the system twice.

The supplier screen's Save sent a POST that created the supplier and a PUT that
set its address. Everything downstream read only the frame's "primary" call, so
the induced skill replayed the address and never created the supplier -- a task
that looks right in review and does half the work.
"""

from __future__ import annotations

from typing import Any

import pytest

from sro.application.induction.diff import align, unfold
from sro.application.induction.errors import InductionFailed
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from tests import factories as f

SUPPLIERS = "https://wms.test/data/WM/wm/suppliers"
ADDRESS = "https://wms.test/data/WM/wm/addresses/A1"


def _save(index: int, *requests: Any) -> ActionFrame:
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=tuple(requests),
    )


def _both(index: int) -> ActionFrame:
    return _save(
        index,
        f.request(method="POST", url=SUPPLIERS, status=201),
        f.request(method="PUT", url=ADDRESS, status=200),
    )


def test_one_gesture_that_wrote_twice_becomes_two_steps() -> None:
    pairs = align((_both(0),), (_both(0),))

    assert [pair[0].primary_request.method for pair in pairs] == ["POST", "PUT"]  # type: ignore[union-attr]


def test_the_calls_pair_with_their_own_kind_across_runs() -> None:
    """Not the create against the update: the pairing is what the diff reads."""
    pairs = align((_both(0),), (_both(0),))

    for frame_a, frame_b in pairs:
        assert frame_a.primary_request.method == frame_b.primary_request.method  # type: ignore[union-attr]


def test_a_gesture_that_wrote_differently_in_each_run_is_refused() -> None:
    one_run = (_save(0, f.request(method="POST", url=SUPPLIERS, status=201)),)

    with pytest.raises(InductionFailed, match="not two runs of one task"):
        align((_both(0),), one_run)


def test_a_single_run_unfolds_the_same_way() -> None:
    assert [frame.primary_request.method for frame in unfold((_both(0),))] == ["POST", "PUT"]  # type: ignore[union-attr]
