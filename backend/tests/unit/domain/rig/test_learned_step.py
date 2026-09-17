"""What a run keeps about a step, and what it does not."""

from __future__ import annotations

from sro.domain.execution.learned_step import learned_from


def test_a_control_a_picture_found_becomes_a_locator() -> None:
    """The expensive rung's answer, made cheap.

    Measured on the deployment, 2026-09-17: the rung that looks at a picture
    worked out three times in one afternoon that the control is called
    "Customer Types", and the job knew no more at the end of it than at the
    start.
    """
    learned = learned_from(
        2, "sight", {"performed": True, "control": {"tag": "span", "name": "Customer Types"}}
    )

    assert learned is not None
    assert (learned.strategy, learned.query) == ("text", "Customer Types")
    assert learned.found_by == "sight"


def test_the_page_s_own_name_for_it_wins_over_the_words_on_it() -> None:
    """An itemId is what the application calls the control; the words are what
    this release happens to show. A name survives a translation and an id
    survives a rewording, and a warehouse system does both."""
    learned = learned_from(
        2, "sight", {"control": {"tag": "span", "name": "Customer Types", "item_id": "tabItem-9"}}
    )

    assert learned is not None
    assert (learned.strategy, learned.query) == ("component", "tabItem-9")


def test_the_locator_that_matched_is_kept_as_it_was() -> None:
    learned = learned_from(
        3, "css_path", {"matched": {"strategy": "css_path", "query": "span#save-1067"}}
    )

    assert learned is not None
    assert (learned.strategy, learned.query) == ("css_path", "span#save-1067")


def test_nothing_is_kept_where_the_job_was_already_right() -> None:
    """`component` and `test_id` are the job's own recorded identity. Writing
    those down is the job telling itself what it already says."""
    assert learned_from(1, "component", {"control": {"name": "Save"}}) is None
    assert learned_from(1, "test_id", {"control": {"name": "Save"}}) is None


def test_nothing_is_kept_from_a_reply_that_named_nothing() -> None:
    """A run cannot pass on what it did not learn."""
    assert learned_from(1, "sight", {"performed": True}) is None
    assert learned_from(1, "sight", None) is None
    assert learned_from(1, None, {"control": {"name": "Save"}}) is None
    assert learned_from(1, "sight", {"control": {"name": "   "}}) is None
