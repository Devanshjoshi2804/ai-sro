"""Something a person asked for, and what came of it.

Everything this system records, it records as state: a run is a row because a
run was created, an offer because an offer was made. Nothing at all is written
when nothing happens -- and *I pressed it and nothing happened* is the question
a support engineer is actually asked.
"""

from __future__ import annotations

import pytest

from sro.domain.observation.attempts import (
    DONE,
    K_WHY,
    NOTHING,
    REFUSED,
    Attempt,
    as_row,
)


def _attempt(**over: object) -> Attempt:
    base: dict[str, object] = {
        "id": "att_1",
        "tenant": "greyorange",
        "at": "2026-09-20T11:47:53+00:00",
        "asked_for": "press an offer",
        "came_of": DONE,
    }
    return Attempt(**{**base, **over})


def test_an_attempt_must_come_to_something_this_system_recognises() -> None:
    """A vocabulary nobody checks is a column of free text within a month."""
    with pytest.raises(ValueError, match="succeeded"):
        _attempt(came_of="succeeded")


def test_nothing_is_an_outcome() -> None:
    """The one this exists for: the request was accepted, nothing objected, and
    no state changed. A press on an offer that had already expired, an undo
    with nothing to take back. Those were silence."""
    attempt = _attempt(came_of=NOTHING, why="that offer had already expired")

    assert as_row(attempt)["came_of"] == NOTHING
    assert as_row(attempt)["why"] == "that offer had already expired"


def test_a_reason_is_bounded_and_kept_to_one_line() -> None:
    """Bounded in the domain rather than at the column, so a store that forgot
    its own limit cannot be the thing that decides."""
    row = as_row(_attempt(came_of=REFUSED, why="a\nvery " + "long " * 200))

    assert len(str(row["why"])) == K_WHY
    assert "\n" not in str(row["why"])


def test_an_attempt_nobody_made_says_so_rather_than_guessing() -> None:
    """A trigger and a sweep have no person behind them, and somebody reading a
    day wants to know which of the two they are looking at."""
    assert as_row(_attempt())["principal"] == ""
    assert as_row(_attempt(principal="rudy"))["principal"] == "rudy"


def test_what_it_was_about_travels_with_it() -> None:
    row = as_row(_attempt(about={"run": "run_1", "thread": "thr_2"}))

    assert row["about"] == {"run": "run_1", "thread": "thr_2"}


def test_the_row_is_a_copy_and_not_the_attempt_s_own_dictionary() -> None:
    """A caller that mutates what it stored must not rewrite the record."""
    attempt = _attempt(about={"run": "run_1"})
    row = as_row(attempt)

    assert isinstance(row["about"], dict)
    row["about"]["run"] = "somebody_elses_run"

    assert attempt.about == {"run": "run_1"}
