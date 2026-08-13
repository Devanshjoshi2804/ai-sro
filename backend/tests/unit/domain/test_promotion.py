"""The promotion ladder -- §3.4.

These tests are the governance layer. If they ever get relaxed to make something
convenient pass, that is the moment one clerk's workaround starts running
unattended across every facility.
"""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.promotion import (
    HIGHEST_PERMITTED_STAGE,
    PromotionStage,
    check_promotion,
)
from tests import factories as f


def test_promotion_moves_exactly_one_rung() -> None:
    check_promotion(PromotionStage.RECORDED, PromotionStage.SHADOW)


def test_recorded_cannot_jump_to_autonomous() -> None:
    with pytest.raises(InvariantViolation, match="one rung at a time"):
        check_promotion(PromotionStage.RECORDED, PromotionStage.AUTONOMOUS)


def test_promotion_cannot_go_backwards() -> None:
    # Demotion on a failure spike is a real behaviour, but it is monitored and
    # automatic -- it must not be reachable through the review UI's promote button.
    with pytest.raises(InvariantViolation, match="cannot demote"):
        check_promotion(PromotionStage.SHADOW, PromotionStage.RECORDED)


def test_this_release_refuses_to_go_past_assisted() -> None:
    # ASSISTED is available because an L1 executor exists and checks every step
    # against the demonstration's assertions. AUTONOMOUS additionally claims a
    # result is right when no human looked, which needs one medium's outcome
    # checked against another's -- and nothing here does that yet.
    assert HIGHEST_PERMITTED_STAGE is PromotionStage.ASSISTED

    with pytest.raises(InvariantViolation, match="unattended"):
        check_promotion(PromotionStage.ASSISTED, PromotionStage.AUTONOMOUS)


def test_promotion_records_who_and_when() -> None:
    version = f.skill_version()

    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)

    assert version.stage is PromotionStage.SHADOW
    assert version.promoted_at == f.at(700)
    assert version.promoted_by == f.OPERATOR
