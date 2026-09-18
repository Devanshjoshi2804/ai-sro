"""What a run keeps about a step, and what it does not."""

from __future__ import annotations

from sro.domain.execution.learned_step import (
    LearnedStep,
    learned_from,
    limits_for,
    too_long,
)
from sro.domain.skill.workflow import Step


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


def test_a_limit_learnt_about_a_step_is_readable_by_the_name_it_was_typed_into() -> None:
    """A limit is learnt about a STEP, because a step is what typed into the
    box. Everything that wants to use it ahead of time -- the question asked of
    somebody whose value was too long, the card asked before the press -- knows
    a parameter's name and not which step fills it."""
    steps = [
        Step(order=0, says="open the screen", system=None, cites=["g"]),
        Step(
            order=1,
            says="type the description",
            system=None,
            cites=["g"],
            parameters=["Customer Type Description"],
        ),
    ]
    learned = (
        LearnedStep(0, "text", "Customer Types", "sight"),
        LearnedStep(1, "component", "textfield-1", "sight", holds=28),
    )

    assert limits_for(steps, learned) == {"Customer Type Description": 28}


def test_a_name_typed_at_two_steps_is_held_to_the_smaller_box() -> None:
    """A value that fits the first box and not the second still stops the job,
    and a card that promised otherwise lied to the person who pressed."""
    steps = [
        Step(order=0, says="type it here", system=None, cites=["g"], parameters=["Description"]),
        Step(order=1, says="and here", system=None, cites=["g"], parameters=["Description"]),
    ]
    learned = (
        LearnedStep(0, "component", "a", "sight", holds=40),
        LearnedStep(1, "component", "b", "sight", holds=28),
    )

    assert limits_for(steps, learned) == {"Description": 28}
    assert limits_for(list(reversed(steps)), learned) == {"Description": 28}


def test_a_step_nothing_was_learnt_about_declares_no_limit() -> None:
    """Which is every step that does not type, and every typing step whose
    value has always fitted -- so most of them. A limit exists only where some
    run has hit one, and inventing one from silence would refuse values that
    are perfectly fine."""
    steps = [Step(order=0, says="type it", system=None, cites=["g"], parameters=["Description"])]

    assert limits_for(steps, ()) == {}
    assert limits_for(steps, (LearnedStep(0, "text", "Description", "sight"),)) == {}


def test_only_the_values_that_will_not_fit_come_back_and_they_carry_the_number() -> None:
    """The limit and not a flag: "this will not fit" sends somebody back with a
    value that does not fit either, and they have no way to know why -- the
    browser truncates in silence and says nothing at all."""
    limits = {"Description": 28, "Code": 10}
    values = {
        "Description": "leaning new SRO type 044 for the north dock",
        "Code": "GU9",
        "Something Else": "x" * 90,
    }

    assert too_long(values, limits) == {"Description": 28}
    # The boundary is what the box KEEPS, so exactly that many fits.
    assert too_long({"Code": "0123456789"}, limits) == {}
    assert too_long({"Code": "01234567890"}, limits) == {"Code": 10}
