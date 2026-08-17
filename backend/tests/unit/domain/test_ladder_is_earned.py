"""The ladder climbs itself, and stops where the evidence stops.

Promoting by hand made a version's stage a fact about somebody's afternoon.
Nobody has time to notice that a skill has earned the next rung, and a stage
nobody has time to grant is a stage that stays wrong.

What must not follow from that is a skill wandering up to unattended on its own
enthusiasm, so most of these are about where it stops.
"""

from __future__ import annotations

from sro.domain.skill.earned import earned_stage
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.track_record import REQUIRED_CLEAN_RUNS, TrackRecord, Verdict


def _record(clean: int) -> TrackRecord:
    return TrackRecord(clean_streak=clean, clean_runs=clean)


def _earned(current: PromotionStage, **overrides: object) -> PromotionStage | None:
    options: dict[str, object] = {
        "record": _record(0),
        "verdict": Verdict.CLEAN,
        "has_verifiable_outcome": True,
        "sends_writes": True,
    }
    options.update(overrides)
    return earned_stage(current=current, **options)  # type: ignore[arg-type]


def test_a_taught_skill_may_rehearse_immediately() -> None:
    """Nothing is sent at this rung, so there is nothing to be careful about.

    Withholding a request the operator cannot see is not caution; it is a skill
    nobody can review.
    """
    assert _earned(PromotionStage.RECORDED, verdict=Verdict.WITHHELD) is PromotionStage.SHADOW


def test_a_rehearsal_that_built_its_request_earns_a_confirmed_run() -> None:
    assert _earned(PromotionStage.SHADOW, verdict=Verdict.WITHHELD) is PromotionStage.ASSISTED


def test_one_good_run_is_not_a_licence_to_run_unattended() -> None:
    assert _earned(PromotionStage.ASSISTED, record=_record(1)) is None
    assert _earned(PromotionStage.ASSISTED, record=_record(REQUIRED_CLEAN_RUNS - 1)) is None


def test_a_long_clean_streak_earns_running_alone() -> None:
    assert (
        _earned(PromotionStage.ASSISTED, record=_record(REQUIRED_CLEAN_RUNS))
        is PromotionStage.AUTONOMOUS
    )


def test_a_skill_that_cannot_check_its_own_result_never_runs_alone() -> None:
    """It may be run by a person who can check it. It may not be run by nobody."""
    assert (
        _earned(
            PromotionStage.ASSISTED,
            record=_record(REQUIRED_CLEAN_RUNS * 2),
            has_verifiable_outcome=False,
        )
        is None
    )


def test_a_read_only_skill_has_nothing_to_be_autonomous_about() -> None:
    """Leaving it where a human confirms costs nothing, and means one less
    thing running unattended for no gain."""
    assert (
        _earned(PromotionStage.ASSISTED, record=_record(REQUIRED_CLEAN_RUNS), sends_writes=False)
        is None
    )


def test_a_failing_run_earns_nothing() -> None:
    assert _earned(PromotionStage.SHADOW, verdict=Verdict.FAILED) is None


def test_the_top_of_the_ladder_stays_the_top() -> None:
    assert _earned(PromotionStage.AUTONOMOUS, record=_record(REQUIRED_CLEAN_RUNS * 3)) is None
