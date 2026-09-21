"""What counts as a job changing its mind, and what is only a run agreeing.

The rule this pins is the one that keeps the history readable: a confirmation
is not a change. A job that ran four hundred times and found the same control
every time has taught nothing, and four hundred rows saying so bury the four
that matter.
"""

from __future__ import annotations

from sro.domain.execution.learned_step import HOLDS, LOCATOR, LearnedStep, changed_by


def _step(strategy: str = "component", query: str = "tabItem", **over: object) -> LearnedStep:
    fields: dict[str, object] = {
        "ord": 2,
        "strategy": strategy,
        "query": query,
        "found_by": "evidence",
    }
    fields.update(over)
    return LearnedStep(**fields)


def test_a_run_that_found_what_the_last_one_found_taught_nothing() -> None:
    assert changed_by(_step(), _step()) == ()


def test_the_same_locator_found_another_way_is_still_the_same_locator() -> None:
    """The rung is recorded beside a change rather than folded into it. The
    same query found twice is the same answer however it was found the second
    time, and a row per rung would say a job had drifted when nothing moved."""
    assert changed_by(_step(found_by="evidence"), _step(found_by="sight")) == ()


def test_a_locator_that_moved_is_kept_with_both_halves_of_it() -> None:
    (change,) = changed_by(_step("component", "tabItem"), _step("css_path", "#a > b"))

    assert change.about == LOCATOR
    assert change.was == "component=tabItem"
    assert change.now == "css_path=#a > b"


def test_the_first_thing_a_job_ever_learned_is_worth_keeping() -> None:
    """`was` empty and `now` set is a job learning something it never knew --
    the row somebody reads to find out where a locator nobody demonstrated came
    from."""
    (change,) = changed_by(None, _step())

    assert change.was == ""
    assert change.now == "component=tabItem"


def test_a_limit_a_run_measured_is_its_own_change() -> None:
    """Both halves in one pass, because a run can change both at once: the rung
    that found a control by picture also measured what its box would hold."""
    changes = changed_by(_step(holds=60), _step("css_path", "#a", holds=4))

    assert {one.about for one in changes} == {LOCATOR, HOLDS}
    (limit,) = [one for one in changes if one.about == HOLDS]
    assert (limit.was, limit.now) == ("60", "4")


def test_a_limit_measured_for_the_first_time_says_it_was_nothing() -> None:
    (limit,) = changed_by(_step(), _step(holds=4))

    assert limit.about == HOLDS
    assert (limit.was, limit.now) == ("", "4")


def test_which_run_taught_it_rides_along() -> None:
    """Somebody reading a surprising locator goes and looks at the run that
    found it, the rung that produced it, and the screen it was standing on."""
    (change,) = changed_by(None, _step(found_by="sight"), by_run="run_9")

    assert (change.by_run, change.found_by) == ("run_9", "sight")
