"""A form has thirty fields and no two people fill the same subset.

Two work areas created in Blue Yonder on 2026-08-27, watched passively, are the
evidence behind every rule in this file: same endpoint, same keys, and one of
them leaves Delta Priority empty. Before this, that was "the flows diverged".
"""

from __future__ import annotations

from sro.application.induction import jsonutil


def test_an_empty_value_is_not_a_different_shape() -> None:
    filled = {"workArea": "TWOTEST", "deltaPriority": 1, "distanceThreshold": ""}
    skipped = {"workArea": "THREE TE", "deltaPriority": None, "distanceThreshold": ""}

    assert jsonutil.same_shape(filled, skipped) is True


def test_a_key_one_run_does_not_send_is_still_a_different_shape() -> None:
    """The rule this relaxes exists for a reason. A key present in one body and
    absent from the other is two different requests, not one optional field."""
    with_key = {"workArea": "TWOTEST", "deltaPriority": 1}
    without_key = {"workArea": "THREE TE"}

    assert jsonutil.same_shape(with_key, without_key) is False


def test_two_kinds_of_filled_value_still_disagree() -> None:
    """Relaxing null against anything is the whole change. A number against a
    string is a flow that diverged, and stays one."""
    assert jsonutil.same_shape({"qty": 5}, {"qty": "five"}) is False
