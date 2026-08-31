"""Why a panel press may promote a version, and how far.

`_check_runnable` refuses a RECORDED version because "a recorded skill has not
been reviewed by anybody". After the preview it has been: by the operator, on
the exact steps and the exact values, at the screen it will act on, with a stop
button in front of them. That is a real reading of the rule and not a way around
it -- but a reviewer in the console has to be able to tell it apart from
somebody sitting down with the evidence, and disagree.
"""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f


def test_a_promotion_says_where_its_review_happened() -> None:
    version = f.skill_version(stage=PromotionStage.RECORDED)

    version.promote(PromotionStage.SHADOW, f.at(100), f.OPERATOR, from_where="preview")

    assert version.promoted_from == "preview"
    assert version.promoted_by == f.OPERATOR


def test_a_promotion_from_the_console_says_so_too() -> None:
    """Not a flag that only the new path sets. A blank would mean "old row" and
    "somebody reviewed this properly" at once, which is the kind of field nobody
    can read back."""
    version = f.skill_version(stage=PromotionStage.RECORDED)

    version.promote(PromotionStage.SHADOW, f.at(100), f.OPERATOR, from_where="console")

    assert version.promoted_from == "console"


def test_a_preview_cannot_reach_past_assisted() -> None:
    """The whole argument is that the operator read what it would do. Nobody
    reads what ten future unattended runs will do."""
    version = f.skill_version(stage=PromotionStage.ASSISTED)

    with pytest.raises(InvariantViolation, match="preview"):
        version.promote(PromotionStage.AUTONOMOUS, f.at(100), f.OPERATOR, from_where="preview")
