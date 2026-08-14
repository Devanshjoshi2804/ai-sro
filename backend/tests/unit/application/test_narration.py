"""Narration labels the work. It never decides what the work is."""

from __future__ import annotations

from sro.application.induction.narration import align
from sro.domain.recording.narration import NarrationSegment
from tests import factories as f


def _said(text: str, *, start: int, end: int) -> NarrationSegment:
    return NarrationSegment(starts_at=f.at(start), ends_at=f.at(end), text=text)


def _frames() -> tuple:
    return (f.frame(0), f.frame(1), f.frame(2))  # at 10s, 11s, 12s


async def test_what_was_said_lands_on_the_step_it_was_said_during() -> None:
    placed = align(
        _frames(),
        (
            _said("I am filtering to the LPN we counted", start=10, end=11),
            _said("and this is the quantity from the count sheet", start=11, end=12),
        ),
    )

    assert placed[0].text == "I am filtering to the LPN we counted"
    assert placed[1].text == "and this is the quantity from the count sheet"
    assert 2 not in placed


async def test_the_last_step_keeps_listening_after_the_final_click() -> None:
    """The summing-up arrives after the work and is the best sentence there is."""
    placed = align(_frames(), (_said("that is queued for approval now", start=30, end=34),))

    assert placed[2].text == "that is queued for approval now"


async def test_a_path_the_operator_only_described_becomes_a_question() -> None:
    placed = align(
        _frames(),
        (_said("If the count does not match, I raise a discrepancy instead", start=10, end=11),),
    )

    assert placed[0].branch_hint == "If the count does not match, I raise a discrepancy instead"


async def test_saying_a_supervisor_is_involved_flags_the_step() -> None:
    placed = align(_frames(), (_said("here I check with the supervisor", start=10, end=11),))

    assert placed[0].requires_human is True


async def test_a_silent_demonstration_produces_nothing_rather_than_guesses() -> None:
    assert align(_frames(), ()) == {}
