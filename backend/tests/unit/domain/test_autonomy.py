"""The rung nobody watches, and what has to be true before it opens."""

from __future__ import annotations

from datetime import timedelta

import pytest

from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.execution.safety import (
    MAX_ITEMS_PER_BATCH,
    MAX_WRITES_PER_WINDOW,
    TRIP_AFTER,
    RunFact,
    assess,
)
from sro.domain.execution.verdict import Verdict, judge
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import REQUIRED_CLEAN_RUNS, TrackRecord
from tests import factories as f


def _run(*outcomes: StepOutcome, stage: PromotionStage = PromotionStage.ASSISTED) -> Run:
    run = Run(
        id=RunId("run-1"),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=stage,
        parameters={},
        requested_by=f.OPERATOR,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
        target_system="blue_yonder",
    )
    for outcome in outcomes:
        run.record(outcome)
    run.finish(f.at(60))
    return run


def _step(**overrides: object) -> StepOutcome:
    defaults: dict[str, object] = {
        "index": 0,
        "medium": Medium.NETWORK,
        "disposition": StepDisposition.PERFORMED,
        "intent": "adjust",
        "status_code": 200,
    }
    return StepOutcome(**{**defaults, **overrides})  # type: ignore[arg-type]


class TestVerdict:
    def test_every_step_at_l1_with_its_assertions_passing_is_clean(self) -> None:
        assert judge(_run(_step())) is Verdict.CLEAN

    def test_a_run_the_browser_had_to_finish_is_degraded_not_clean(self) -> None:
        """It worked, and it also told us the recipe no longer fits."""
        run = _run(_step(medium=Medium.UI, escalated_from=Medium.NETWORK))

        assert judge(run) is Verdict.DEGRADED

    def test_a_shadow_run_neither_advances_nor_resets_anything(self) -> None:
        run = _run(
            _step(disposition=StepDisposition.WITHHELD, status_code=None),
            stage=PromotionStage.SHADOW,
        )

        assert judge(run) is Verdict.WITHHELD
        assert TrackRecord().after(judge(run), f.at(1)) == TrackRecord()


class TestTrackRecord:
    def test_the_streak_is_consecutive_rather_than_cumulative(self) -> None:
        """Nine wins in ten is a skill that does the wrong thing on a Tuesday."""
        record = TrackRecord()
        for _ in range(5):
            record = record.after(Verdict.CLEAN, f.at(1))
        record = record.after(Verdict.DEGRADED, f.at(2))

        assert record.clean_streak == 0
        assert record.clean_runs == 5, "the history is kept; the streak is what counts"

    def test_three_failures_in_a_row_call_for_a_demotion(self) -> None:
        record = TrackRecord()
        for _ in range(3):
            record = record.after(Verdict.FAILED, f.at(1))

        assert record.should_demote

    def test_a_single_success_clears_the_failure_count(self) -> None:
        record = TrackRecord().after(Verdict.FAILED, f.at(1)).after(Verdict.CLEAN, f.at(2))

        assert record.consecutive_failures == 0


class TestEarningAutonomy:
    def _version(self, *, verifiable: bool = True) -> SkillVersion:
        step = f.step(
            assertions=(
                (Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template("200")),)
                if verifiable
                else ()
            )
        )
        version = f.skill_version(steps=(step,))
        version.promote(PromotionStage.SHADOW, f.at(10), f.OPERATOR)
        version.promote(PromotionStage.ASSISTED, f.at(20), f.OPERATOR)
        return version

    def test_a_skill_nothing_can_check_never_runs_unattended(self) -> None:
        """It may run assisted indefinitely. Autonomy is earned by being
        checkable, not by succeeding quietly."""
        version = self._version(verifiable=False)
        for _ in range(REQUIRED_CLEAN_RUNS * 2):
            version.record_run(Verdict.CLEAN, f.at(30))

        with pytest.raises(InvariantViolation, match="cannot be checked"):
            version.promote(PromotionStage.AUTONOMOUS, f.at(40), f.OPERATOR)

    def test_a_clean_streak_is_what_opens_the_last_rung(self) -> None:
        version = self._version()
        for _ in range(REQUIRED_CLEAN_RUNS):
            version.record_run(Verdict.CLEAN, f.at(30))

        version.promote(PromotionStage.AUTONOMOUS, f.at(40), f.OPERATOR)

        assert version.stage is PromotionStage.AUTONOMOUS

    def test_a_run_that_needed_vision_puts_autonomy_back_out_of_reach(self) -> None:
        version = self._version()
        for _ in range(REQUIRED_CLEAN_RUNS):
            version.record_run(Verdict.CLEAN, f.at(30))
        version.record_run(Verdict.DEGRADED, f.at(31))

        with pytest.raises(InvariantViolation, match="clean runs in a row"):
            version.promote(PromotionStage.AUTONOMOUS, f.at(40), f.OPERATOR)

    def test_demotion_is_not_a_promotion_backwards(self) -> None:
        version = self._version()

        version.demote(PromotionStage.SHADOW, f.at(50), "3 runs failed in a row")

        assert version.stage is PromotionStage.SHADOW
        assert version.promoted_by is None, "nobody authorised this; it happened"
        assert version.demotion_reason == "3 runs failed in a row"


class TestSafety:
    def test_a_system_that_keeps_failing_stops_being_asked(self) -> None:
        now = f.at(1000)
        facts = tuple(
            RunFact(finished_at=now - timedelta(minutes=i), failed=True, writes=0)
            for i in range(TRIP_AFTER)
        )

        verdict = assess(facts, now)

        assert not verdict.permitted
        assert "a person should look" in (verdict.reason or "")

    def test_old_failures_do_not_hold_a_recovered_system_closed(self) -> None:
        now = f.at(100_000)
        facts = tuple(
            RunFact(finished_at=now - timedelta(hours=3), failed=True, writes=0)
            for _ in range(TRIP_AFTER * 2)
        )

        assert assess(facts, now).permitted

    def test_an_hour_of_writes_is_bounded(self) -> None:
        now = f.at(1000)
        facts = (
            RunFact(
                finished_at=now - timedelta(minutes=5), failed=False, writes=MAX_WRITES_PER_WINDOW
            ),
        )

        verdict = assess(facts, now)

        assert not verdict.permitted
        assert "limit is" in (verdict.reason or "")

    def test_a_batch_larger_than_a_person_would_confirm_is_refused(self) -> None:
        verdict = assess((), f.at(1), requested_writes=MAX_ITEMS_PER_BATCH + 1)

        assert not verdict.permitted
        assert "without a person deciding" in (verdict.reason or "")
