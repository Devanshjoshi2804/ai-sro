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


# ASSISTED because an L1 executor now exists and every step it performs is
# checked against the assertions the demonstration established. AUTONOMOUS stays
# closed: it additionally requires the cross-path check (an L2 or L3 result
# verified against what L1 would have produced), which arrives with those rungs.
#
# The difference the ladder actually makes: at SHADOW a write is produced and
# withheld, at ASSISTED it is sent and the run names the human who allowed it.
HIGHEST_PERMITTED_STAGE = PromotionStage.ASSISTED


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
            f"{target} is not available in this release: a result is verified against "
            "its own assertions, and nothing yet checks one medium's result against "
            f"another's, so nothing above {HIGHEST_PERMITTED_STAGE} can be trusted "
            "to run unattended"
        )
