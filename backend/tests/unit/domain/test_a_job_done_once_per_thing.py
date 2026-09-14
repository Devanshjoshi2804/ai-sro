"""What a repeat is, and what it refuses to be.

"Add these three equipment types" is one job. The list is a person's -- a mail
the browser matched, a sentence typed into the panel -- so the count is a
human's rather than a guess, and getting the block wrong costs three wrong
records instead of forty.
"""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.repeats import Repeat


def test_the_body_is_the_steps_it_covers() -> None:
    body = Repeat(first_step=2, last_step=5)

    assert [order for order in range(8) if body.covers(order)] == [2, 3, 4, 5]
    assert body.steps == 4


def test_one_step_can_be_the_whole_body() -> None:
    assert Repeat(first_step=3, last_step=3).steps == 1


def test_a_block_that_ends_before_it_begins_is_refused() -> None:
    with pytest.raises(InvariantViolation, match="ends before it begins"):
        Repeat(first_step=4, last_step=2)


def test_a_block_that_starts_where_no_step_is_refused() -> None:
    with pytest.raises(InvariantViolation, match="starts at a step that exists"):
        Repeat(first_step=-1, last_step=2)
