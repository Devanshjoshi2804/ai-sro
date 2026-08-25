"""What can be read off two examples of one value being reformatted.

The line is the same one the whole diff stands on: a rule is worth having when
the evidence forces it and worth refusing when it does not. Everything this
cannot explain stays a question for an operator, which is the safe failure.
"""

from __future__ import annotations

import pytest

from sro.application.induction.transform import discover
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.transform import Transform


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("42", "LPN-42"),  # the shape a cross-system workflow is made of
        ("42", "LPN-00042"),  # padded on the way
        ("ab12", "AB12"),  # a system that shouts
        ("AB12", "ab12"),
        (" 42 ", "42"),  # a value read off a screen with its whitespace
        ("42", "42/DC01"),  # followed by the site it belongs to
        ("wave-9", "REF:wave-9:OPEN"),  # both ends
    ],
)
def test_a_reformatting_two_runs_agree_on_is_read_exactly(source: str, target: str) -> None:
    found = discover(source, target)

    assert found is not None, f"{source!r} to {target!r} was not explained"
    assert found.apply(source) == target


@pytest.mark.parametrize(
    ("source", "target"),
    [
        ("42", "42"),  # nothing was done; the diff already knows this case
        ("7", "LPN-7"),  # one character carried into a longer string is luck
        ("42", "24"),  # rearranged, which this deliberately cannot express
        ("42", "LPN-43"),  # not this value at all
        ("042", "1042"),  # a digit run that continues past it is a coincidence
        ("abc", ""),
        # The reverse of padding, which nothing has asked for yet: the next
        # operation to add, on the day a real system wants `00042` unpadded.
        ("00042", "42"),
    ],
)
def test_what_cannot_be_shown_is_refused(source: str, target: str) -> None:
    assert discover(source, target) is None


def test_a_value_that_appears_as_it_is_gets_the_shorter_story() -> None:
    """`42` inside `LPN-42` is a prefix, never "padded to two then prefixed":
    a rule that claims more than it must is a rule that breaks on the next run
    for a reason nobody can see."""
    found = discover("42", "LPN-42")

    assert found is not None
    assert found.ops == (("prefix", "LPN-"),)


def test_padding_is_only_claimed_where_padding_is_what_happened() -> None:
    found = discover("42", "LPN-00042")

    assert found is not None
    assert found.ops == (("pad", "5", "0"), ("prefix", "LPN-"))
    assert found.said_plainly() == "padded to 5 with '0', then prefixed with 'LPN-'"


def test_an_operation_nobody_defined_is_refused_rather_than_ignored() -> None:
    # Read back out of a stored skill document written by a later version of
    # this code. Ignoring it would apply *some* of a transformation and send
    # the result to a warehouse.
    with pytest.raises(InvariantViolation, match="unknown transformation"):
        Transform(ops=(("reverse",),))

    with pytest.raises(InvariantViolation, match="takes 1 arguments"):
        Transform(ops=(("prefix",),))
