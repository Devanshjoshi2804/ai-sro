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
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import REQUIRED_CLEAN_RUNS, Verdict
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


def test_a_preview_promoting_to_assisted_itself_succeeds() -> None:
    """The cap is `rung > ASSISTED`, not `rung >= ASSISTED` -- reaching
    assisted is the entire point of a preview promotion, not one rung short
    of what it is refused."""
    version = f.skill_version(stage=PromotionStage.SHADOW)

    version.promote(PromotionStage.ASSISTED, f.at(100), f.OPERATOR, from_where="preview")

    assert version.stage is PromotionStage.ASSISTED
    assert version.promoted_from == "preview"


def test_the_cap_is_the_only_thing_refusing_a_version_that_is_actually_ready() -> None:
    """`f.skill_version`'s default step carries no assertion, so
    `not_ready_for_autonomy` refuses every version this file builds for a
    reason that has nothing to do with `from_where` -- proving nothing about
    the cap this test exists to defend. Build one that is genuinely ready
    (checkable, a full clean streak) and show the preview guard is what stops
    it: the same promotion, same evidence, succeeds through the console."""
    step = f.step(assertions=(Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),))
    version = f.skill_version(steps=(step,), stage=PromotionStage.ASSISTED)
    for _ in range(REQUIRED_CLEAN_RUNS):
        version.record_run(Verdict.CLEAN, f.at(30))
    assert version.not_ready_for_autonomy is None, "the version must be genuinely ready first"

    with pytest.raises(InvariantViolation, match="preview"):
        version.promote(PromotionStage.AUTONOMOUS, f.at(100), f.OPERATOR, from_where="preview")

    version.promote(PromotionStage.AUTONOMOUS, f.at(200), f.OPERATOR, from_where="console")
    assert version.stage is PromotionStage.AUTONOMOUS


def test_a_press_does_not_hand_a_failing_version_a_fresh_three_lives() -> None:
    """The counter that demotes is cleared by the person who looked, and a
    press is not that person.

    `promote` zeroes `consecutive_failures` because a console promotion is
    somebody saying they have read the failures and understood them. The
    preview press says something much smaller: this operator read the steps
    and the values of the one run in front of them. If it cleared the count
    too, a version that is wrong every single time would never reach three in
    a row -- every press would walk it back to zero -- and
    `DEMOTE_AFTER_FAILURES`, which ADR 014 leans its entire residual-risk
    argument on, would never fire at all.
    """
    version = f.skill_version(stage=PromotionStage.SHADOW)
    version.record_run(Verdict.FAILED, f.at(10))
    version.record_run(Verdict.FAILED, f.at(20))

    version.promote(PromotionStage.ASSISTED, f.at(100), f.OPERATOR, from_where="preview")

    assert version.track_record.consecutive_failures == 2, (
        "a press cleared the count that demotes, so the third failure never arrives"
    )


def test_a_console_promotion_still_clears_it() -> None:
    """The other half. The clearing was written for the console path and is
    correct there -- a version demoted at three failures would otherwise go
    straight back down on its next run whatever that run did, because
    `should_demote` is a standing condition re-asked after every run."""
    version = f.skill_version(stage=PromotionStage.SHADOW)
    version.record_run(Verdict.FAILED, f.at(10))
    version.record_run(Verdict.FAILED, f.at(20))

    version.promote(PromotionStage.ASSISTED, f.at(100), f.OPERATOR, from_where="console")

    assert version.track_record.consecutive_failures == 0


def test_a_demoted_version_is_refused_a_preview_promotion_outright() -> None:
    """Three wrong runs pulled it back; the operator's next press must not put
    it straight back. What a version demoted for being wrong needs is a person
    in the console with the evidence in front of them -- that is what the
    ladder is for, and a press mid-task is not it.

    The sentence is checked, not only the refusal: this lands in the panel
    beside the button the operator just pressed, so it has to say what went
    wrong in their words rather than name a field.
    """
    version = f.skill_version(stage=PromotionStage.ASSISTED)
    version.demote(PromotionStage.SHADOW, f.at(50), "3 runs failed in a row")

    with pytest.raises(InvariantViolation) as refused:
        version.promote(PromotionStage.ASSISTED, f.at(100), f.OPERATOR, from_where="preview")

    said = str(refused.value)
    assert "went wrong three times in a row" in said
    assert "demotion_reason" not in said, "a field name reached an operator"
    assert version.stage is PromotionStage.SHADOW, "the refusal still moved the version"

    # And the door that is open: somebody who looks may put it back.
    version.promote(PromotionStage.ASSISTED, f.at(200), f.OPERATOR, from_where="console")
    assert version.stage is PromotionStage.ASSISTED
    # False positive: the SHADOW assert above narrowed `version.stage`, and mypy
    # does not invalidate that across `promote`, which mutates it -- so the
    # ASSISTED assert narrows to Never and this passing check looks dead.
    assert version.demotion_reason is None  # type: ignore[unreachable]
