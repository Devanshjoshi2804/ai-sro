"""What a match offers after somebody demonstrates a working skill again.

A second demonstration lands at RECORDED, which the runner refuses. Matching
always offered `versions[-1]`, so every match after a re-teach answered with a
version that could not run -- the skill that had been working ten minutes
earlier now told the operator it had never been reviewed, and the only way back
was to promote the new one.
"""

from __future__ import annotations

from sro.domain.skill.promotion import PromotionStage
from tests import factories as f


def _skill(*stages: PromotionStage) -> object:
    skill = f.skill(versions=0)
    for index, stage in enumerate(stages, start=1):
        version = f.skill_version(version=index)
        skill.add_version(version)
        current = PromotionStage.RECORDED
        while current is not stage:
            current = current.next_stage()
            version.promote(current, f.at(700), f.OPERATOR)
    return skill


def test_the_version_offered_is_the_newest_one_that_can_run() -> None:
    taught_twice = _skill(PromotionStage.ASSISTED, PromotionStage.RECORDED)

    assert taught_twice.runnable is not None  # type: ignore[attr-defined]
    assert taught_twice.runnable.version == 1  # type: ignore[attr-defined]


def test_the_newest_wins_once_it_has_been_reviewed() -> None:
    promoted = _skill(PromotionStage.ASSISTED, PromotionStage.SHADOW)

    assert promoted.runnable.version == 2  # type: ignore[attr-defined]


def test_a_skill_that_has_only_ever_been_recorded_has_nothing_runnable() -> None:
    """It is still matched -- the caller falls back to the newest -- so the
    operator is told to promote it rather than told it does not exist."""
    fresh = _skill(PromotionStage.RECORDED)

    assert fresh.runnable is None  # type: ignore[attr-defined]
