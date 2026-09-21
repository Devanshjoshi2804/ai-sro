"""The question a stopped run asks, in the words of what went wrong.

Two different things bring a run to a stop with a value it needs, and they want
two different questions.

A value nobody could find is "I could not find X". A value that would not fit
is a different problem entirely: the person HAS a value, they sent it, and the
box will not take it. Asking that one the first way gets the same value back --
nothing has told them their description is twice the length the field holds,
because the browser truncated it in silence, which is the whole reason the
limit had to be discovered at all.
"""

from __future__ import annotations

from sro.application.execution.workflow_runs import _asking


def test_a_value_nobody_could_find_is_asked_for_plainly() -> None:
    said = _asking(["Customer Type"], "Create a Customer Type", {})

    assert said.startswith("I could not find Customer Type for Create a Customer Type.")


def test_a_value_that_will_not_fit_says_what_the_box_holds() -> None:
    said = _asking(["Description"], "Create a Customer Type", {"Description": 28})

    assert "holds 28 characters" in said, said
    # NOT "I could not find" -- it was found, and it was too long.
    assert "could not find Description" not in said, said


def test_one_of_each_says_both_and_confuses_neither() -> None:
    said = _asking(
        ["Description", "Customer Type"],
        "Create a Customer Type",
        {"Description": 28},
    )

    assert "Description holds 28 characters" in said, said
    assert "could not find Customer Type" in said, said
