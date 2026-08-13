"""Promotion ladder. See docs/01-architecture.md#promotion-ladder."""

from __future__ import annotations

from enum import StrEnum

from sro.domain.shared.errors import InvariantViolation

_ORDER: tuple[str, ...] = ("recorded", "shadow", "assisted", "autonomous")


class PromotionStage(StrEnum):
    RECORDED = "recorded"
    SHADOW = "shadow"
    ASSISTED = "assisted"
    AUTONOMOUS = "autonomous"

    @property
    def rung(self) -> int:
        return _ORDER.index(self.value)

    def next_stage(self) -> PromotionStage:
        if self is PromotionStage.AUTONOMOUS:
            raise InvariantViolation("autonomous is the top of the ladder")
        return PromotionStage(_ORDER[self.rung + 1])


# Raise only alongside a working executor and its cross-path verification.
# Until then, nothing above SHADOW can honestly be verified.
HIGHEST_PERMITTED_STAGE = PromotionStage.SHADOW


def check_promotion(current: PromotionStage, target: PromotionStage) -> None:
    """Validate a promotion, or explain precisely why it is refused."""
    if target is current:
        raise InvariantViolation(f"skill is already {current}")
    if target.rung < current.rung:
        raise InvariantViolation(
            f"cannot demote {current} to {target} by promotion; "
            "demotion is a separate, monitored action"
        )
    if target.rung > current.rung + 1:
        raise InvariantViolation(
            f"cannot jump {current} to {target}: promotion moves one rung at a time, "
            f"next is {current.next_stage()}"
        )
    if target.rung > HIGHEST_PERMITTED_STAGE.rung:
        raise InvariantViolation(
            f"{target} is not available in this release: there is no executor, so "
            f"nothing above {HIGHEST_PERMITTED_STAGE} can be verified"
        )
