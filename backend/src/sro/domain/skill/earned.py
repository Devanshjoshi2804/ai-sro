"""What a version's record entitles it to, without anybody clicking anything.

The ladder was always meant to be earned rather than granted -- but earning it
still required a person to notice and press a button, which is a chore nobody
has time for and which makes the stage a fact about somebody's afternoon rather
than about the skill.

So the record decides. Each rung asks one question, and the answers get harder
in the order that matters:

- **Rehearsing** costs nothing to allow: nothing is sent. A taught skill that
  can build a request is entitled to build one.
- **Running with a confirmation** needs proof the request is real -- that it was
  built, sent, and answered the way the demonstration was answered. The person
  is still there; what they are spared is the paperwork of saying so twice.
- **Running alone** is the only rung where nobody is watching, so it is the only
  one that asks for a streak, and it asks for a long one.

Nothing here promotes past what a human allowed for the tenant, and nothing here
demotes: demotion is its own decision, made on failures, and it is deliberately
faster than this.
"""

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
    """The rung this record has earned, or None to leave it where it is.

    One rung at a time, on purpose: a skill that has only ever rehearsed has not
    shown it can run, and the evidence for each rung is the previous rung's
    runs.
    """
    if current is PromotionStage.RECORDED:
        # Nothing is sent at the next rung. Withholding a request the operator
        # cannot see is not caution, it is just a skill nobody can review.
        return _capped(PromotionStage.SHADOW)

    if current is PromotionStage.SHADOW and verdict in {Verdict.WITHHELD, Verdict.CLEAN}:
        if values_are_fixed and sends_writes:
            # Induced from one demonstration, so every value it sends is the one
            # that run happened to carry. A rehearsal proves the request can be
            # built; it cannot prove that sending that exact request again is
            # what anybody wants. A person says that, or it stays here -- and
            # this is the path where nobody is asked, so the refusal has to live
            # here too rather than only on the promotion by hand.
            return None
        # The request was built and, where it was a read, answered as the
        # demonstration was answered. That is the whole claim of this rung.
        return _capped(PromotionStage.ASSISTED)

    if current is PromotionStage.ASSISTED and record.clean_streak >= REQUIRED_CLEAN_RUNS:
        if not has_verifiable_outcome:
            # A skill that cannot check its own result may be run by a person
            # who can. It may not be run by nobody.
            return None
        if not sends_writes:
            # A read-only skill has nothing to be autonomous about; leaving it
            # where a human confirms costs nothing and means one less thing
            # running unattended.
            return None
        if values_are_fixed:
            # The same refusal as the rung below, and it has to be repeated
            # here: this branch was reached without re-checking, so a skill
            # induced from one demonstration -- every value the one the
            # demonstration happened to carry -- ran ten clean assisted runs and
            # arrived at nobody being asked at all. Ten confirmations of the
            # same fixed request are not evidence that anybody wants it sent
            # unattended; they are the same confirmation ten times.
            return None
        return _capped(PromotionStage.AUTONOMOUS)

    return None


def _capped(target: PromotionStage) -> PromotionStage | None:
    """Never past the ceiling a deployment set for itself."""
    return target if target.rung <= HIGHEST_PERMITTED_STAGE.rung else None
