"""A first demonstration contains looking around. That is not the task.

Demanding two runs of identical length made an operator's hesitation part of
the skill: the transport-mode task was refused because run 1 clicked the
Description field twice and run 2 clicked it once, while both runs' writes were
byte-identical 201s.
"""

from __future__ import annotations

from typing import Any

import pytest

from sro.application.induction.diff import align, parameterise
from sro.application.induction.errors import InductionFailed
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from tests import factories as f

CREATE = "https://wms.test/data/WM/wm/transportModes"


def _frame(index: int, kind: ActionKind, name: str, **overrides: Any) -> ActionFrame:
    return f.frame(
        index=index,
        action=InputAction(
            kind=kind,
            target=f.fingerprint(accessible_name=name, css_path=f"#{name}"),
            value=overrides.pop("value", None),
        ),
        **overrides,
    )


def _click(index: int, name: str, **overrides: Any) -> ActionFrame:
    return _frame(index, ActionKind.CLICK, name, **overrides)


def _type(index: int, name: str, value: str) -> ActionFrame:
    return _frame(index, ActionKind.TYPE, name, value=value, requests=())


def _write(index: int, name: str, url: str = CREATE) -> ActionFrame:
    return _click(index, name, requests=(f.request(method="POST", url=url, status=201),))


def test_a_field_clicked_twice_in_one_run_still_pairs() -> None:
    run_a = (
        _click(0, "Add", requests=()),
        _click(1, "Description", requests=()),
        _click(2, "Description", requests=()),  # the hesitation
        _type(3, "Description", "first"),
        _write(4, "Save"),
    )
    run_b = (
        _click(0, "Add", requests=()),
        _click(1, "Description", requests=()),
        _type(2, "Description", "second"),
        _write(3, "Save"),
    )

    pairs = align(run_a, run_b)

    assert len(pairs) == 4
    # And the value that actually varied is still found, at its paired index.
    varied = parameterise(run_a, run_b).parameters
    assert any("first" in p.observed_values for p in varied), (
        "the typed value is what the pair was for"
    )


def test_an_extra_write_is_never_quietly_dropped() -> None:
    """The line between forgiving exploration and inventing a task.

    A step that changed the system is evidence. If only one run has it, the two
    runs did different things, and no alignment may paper over that.
    """
    run_a = (_click(0, "Add", requests=()), _write(1, "Save"), _write(2, "Delete", f"{CREATE}/1"))
    run_b = (_click(0, "Add", requests=()), _write(1, "Save"))

    with pytest.raises(InductionFailed, match="did something the other did not"):
        align(run_a, run_b)


def test_a_typed_value_only_one_run_entered_is_a_disagreement_too() -> None:
    run_a = (_click(0, "Add", requests=()), _type(1, "Reference", "R1"), _write(2, "Save"))
    run_b = (_click(0, "Add", requests=()), _write(1, "Save"))

    with pytest.raises(InductionFailed):
        align(run_a, run_b)


def test_runs_with_nothing_in_common_are_refused() -> None:
    with pytest.raises(InductionFailed, match="share no steps"):
        align((_click(0, "Add", requests=()),), (_click(0, "Cancel", requests=()),))


def test_a_cache_buster_is_not_a_parameter() -> None:
    """Ext JS stamps every request with the clock. That is not an input.

    Two of the four parameters on the first real task taught were `_dc`, so the
    skill asked its operator for a number meaning "now".
    """
    stamped = "https://wms.test/data/WM/wm/policies?siteId=SG&_dc="
    run_a = (
        _click(0, "Add", requests=(f.request(method="GET", url=f"{stamped}1786949388027"),)),
        _type(1, "Transport Mode", "SROTES1"),
        _write(2, "Save"),
    )
    run_b = (
        _click(0, "Add", requests=(f.request(method="GET", url=f"{stamped}1786949500647"),)),
        _type(1, "Transport Mode", "NEWSROTES2"),
        _write(2, "Save"),
    )

    names = [p.name for p in parameterise(run_a, run_b).parameters]

    assert not any("dc" in name for name in names), names
    assert any("SROTES1" in p.observed_values for p in parameterise(run_a, run_b).parameters)


def test_a_read_only_one_run_made_is_not_a_divergence() -> None:
    """The browser cached it. That is a fact about the browser, not the task.

    The transport-mode pair was refused because run 2 fetched an address list
    run 1 already had -- while the write, a PUT to the same address, was
    identical in both. The operator was told to record the whole thing again to
    no purpose.
    """
    run_a = (_click(0, "Add", requests=()), _click(1, "Row", requests=()), _write(2, "Save"))
    run_b = (
        _click(0, "Add", requests=()),
        _click(
            1, "Row", requests=(f.request(method="GET", url=f"{CREATE}/addresses", status=200),)
        ),
        _write(2, "Save"),
    )

    assert len(align(run_a, run_b)) == 3
    parameterise(run_a, run_b)  # does not raise


def test_a_write_only_one_run_made_is_still_a_divergence() -> None:
    """The line stays where it was: a call that changed something is evidence,
    and one run having it means the two runs did different things."""
    run_a = (_click(0, "Add", requests=()), _click(1, "Row", requests=()), _write(2, "Save"))
    run_b = (
        _click(0, "Add", requests=()),
        _write(1, "Row", f"{CREATE}/extra"),
        _write(2, "Save"),
    )

    with pytest.raises(InductionFailed, match="changed the system"):
        parameterise(run_a, run_b)
