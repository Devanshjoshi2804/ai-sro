from __future__ import annotations

from sro.domain.skill.promotion import HIGHEST_PERMITTED_STAGE, PromotionStage
from sro.domain.skill.track_record import REQUIRED_CLEAN_RUNS, TrackRecord, Verdict


def earned_stage(
    *,
    current: PromotionStage,
    record: TrackRecord,
    verdict: Verdict,
    has_verifiable_outcome: bool,
    sends_writes: bool,
    values_are_fixed: bool = False,
) -> PromotionStage | None:
    if current is PromotionStage.RECORDED:
        return _capped(PromotionStage.SHADOW)

    if current is PromotionStage.SHADOW and verdict in {Verdict.WITHHELD, Verdict.CLEAN}:
        if values_are_fixed and sends_writes:
            return None
        return _capped(PromotionStage.ASSISTED)

    if current is PromotionStage.ASSISTED and record.clean_streak >= REQUIRED_CLEAN_RUNS:
        if not has_verifiable_outcome:
            return None
        if not sends_writes:
            return None
        if values_are_fixed:
            return None
        return _capped(PromotionStage.AUTONOMOUS)

    return None


def _capped(target: PromotionStage) -> PromotionStage | None:
    return target if target.rung <= HIGHEST_PERMITTED_STAGE.rung else None
