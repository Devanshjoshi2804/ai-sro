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


# AUTONOMOUS is reachable now that the things which make it survivable exist:
# a run is classified (domain/execution/verdict.py), a version's clean streak is
# counted rather than asserted, a skill with no assertion anywhere can never
# qualify, three consecutive failures demote automatically, and a circuit
# breaker plus a write budget stop a run before it starts.
#
# Reachable is not the same as easy. `SkillVersion.promote` refuses the last
# rung until the record earns it, so the ceiling is no longer what holds the
# line -- the evidence is.
#
# The difference the ladder actually makes: at SHADOW a write is produced and
# withheld, at ASSISTED it is sent and the run names the human who allowed it,
# at AUTONOMOUS nobody is named because nobody was asked.
HIGHEST_PERMITTED_STAGE = PromotionStage.AUTONOMOUS


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
