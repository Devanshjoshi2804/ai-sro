"""The rung nobody watches, and what has to be true before it opens."""

from __future__ import annotations

from datetime import timedelta

import pytest

from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.execution.safety import (
    FAILURE_WINDOW,
    MAX_ITEMS_PER_BATCH,
    MAX_WRITES_PER_WINDOW,
    TRIP_AFTER,
    WRITE_WINDOW,
    BreakerState,
    RunFact,
    assess,
)
from sro.domain.execution.verdict import Verdict, apply_verdict, judge
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import (
    DEMOTE_AFTER_FAILURES,
    REQUIRED_CLEAN_RUNS,
    TrackRecord,
)
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
    return StepOutcome(**{**defaults, **overrides})


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

    def test_a_run_that_never_reached_the_system_is_not_a_failed_run(self) -> None:
        """The operator's browser had no tab open on it. That is a fact about
        the browser, and the skill was never asked anything."""
        run = _run(
            _step(
                disposition=StepDisposition.FAILED,
                status_code=None,
                detail="no tab is open on https://wms.example/data/WM/wm/workAreas",
                unreachable=True,
            )
        )

        assert judge(run) is Verdict.UNREACHABLE

    def test_a_system_that_answered_wrong_is_still_a_failed_run(self) -> None:
        """It answered. What it answered is exactly what a track record is for."""
        run = _run(_step(status_code=500, assertion_failures=("expected status 200, got 500",)))

        assert judge(run) is Verdict.FAILED

    def test_one_step_that_did_reach_it_makes_the_whole_run_evidence_again(self) -> None:
        """Otherwise a genuine failure hides behind a laptop that closed later."""
        run = _run(
            _step(index=0, assertion_failures=("/data/ok is 'false'",)),
            _step(index=1, disposition=StepDisposition.FAILED, unreachable=True),
        )

        assert judge(run) is Verdict.FAILED

    def test_a_run_where_every_step_was_withheld_is_withheld(self) -> None:
        """The subset is inclusive, and this is what says so.

        A shadow run withholds every step, so the set of dispositions IS
        `{WITHHELD}` rather than a proper subset of anything -- with `<` the
        commonest shadow run of all falls through to the loop below and is
        judged CLEAN, which would let a rehearsal that sent nothing count as
        evidence the skill still works."""
        run = _run(
            _step(index=0, disposition=StepDisposition.WITHHELD, status_code=None),
            _step(index=1, disposition=StepDisposition.WITHHELD, status_code=None),
            stage=PromotionStage.SHADOW,
        )

        assert judge(run) is Verdict.WITHHELD

    def test_a_step_taught_as_a_gesture_is_degraded_even_though_nothing_escalated(self) -> None:
        """`or`, not `and`: either half alone is enough.

        A step performed in the browser has not shown that the recorded CALL
        still works, whether it got there by escalating or by having been
        taught that way in the first place. Read as `and`, a skill taught
        entirely at the interface would count every run as clean and climb the
        ladder on evidence it never produced."""
        run = _run(_step(medium=Medium.UI, escalated_from=None))

        assert judge(run) is Verdict.DEGRADED


class TestApplyVerdict:
    """The one function that turns a finished run into a rung.

    Every use case that finishes a run's story calls this, and until these
    tests existed nothing asserted that it moved the ladder at all: a sweep on
    2026-09-13 replaced both of `earn`'s arguments with None and the suite
    stayed green, which means a version could have stopped climbing entirely
    without a failing test.
    """

    def test_a_clean_run_climbs_the_rung_the_record_has_earned(self) -> None:
        skill = f.skill()
        assert skill.version(1).stage is PromotionStage.RECORDED

        verdict = apply_verdict(skill, _run(_step()), f.at(600))

        # Re-read rather than held: a name bound before the call narrows to the
        # rung it was on, and every assertion after it reads as unreachable.
        version = skill.version(1)
        assert verdict is Verdict.CLEAN
        assert version.stage is PromotionStage.SHADOW
        # The time the run finished, not whenever somebody looked.
        assert version.promoted_at == f.at(600)
        assert version.promoted_from == "earned", (
            "a streak did this, not a person -- blank would be indistinguishable "
            "from a version nobody has ever looked at"
        )
        assert version.promoted_by is None

    def test_the_bottom_rung_is_where_demotion_stops(self) -> None:
        """A shadow version sends nothing, so there is nothing to pull it back
        from -- and a `demote` called here would overwrite the reason on a
        version that has done nothing wrong except fail while rehearsing."""
        skill = f.skill()
        version = skill.version(1)
        version.promote(PromotionStage.SHADOW, f.at(10), f.OPERATOR)

        for attempt in range(DEMOTE_AFTER_FAILURES):
            failed = _run(_step(status_code=500, assertion_failures=("expected 200",)))
            apply_verdict(skill, failed, f.at(100 + attempt))

        assert version.track_record.should_demote
        assert version.stage is PromotionStage.SHADOW
        assert version.demotion_reason is None

    def test_a_version_above_it_is_pulled_back_at_the_moment_it_failed(self) -> None:
        skill = f.skill()
        version = skill.version(1)
        version.promote(PromotionStage.SHADOW, f.at(10), f.OPERATOR)
        version.promote(PromotionStage.ASSISTED, f.at(20), f.OPERATOR)

        for attempt in range(DEMOTE_AFTER_FAILURES):
            failed = _run(_step(status_code=500, assertion_failures=("expected 200",)))
            apply_verdict(skill, failed, f.at(100 + attempt))

        assert version.stage is PromotionStage.SHADOW
        assert version.demotion_reason == f"{DEMOTE_AFTER_FAILURES} runs failed in a row"
        # `demote` stamps `promoted_at` with when it happened -- the run that
        # pulled it back, not a wall clock somebody read later.
        assert version.promoted_at == f.at(100 + DEMOTE_AFTER_FAILURES - 1)
        assert version.promoted_by is None


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

    def test_a_closed_browser_never_demotes_a_skill(self) -> None:
        """The live case this exists for: two work areas created, then three
        runs where the operator had no tab open on the system. Under the old
        rule the third one demoted a skill that had never done anything wrong."""
        record = TrackRecord()
        for _ in range(2):
            record = record.after(Verdict.CLEAN, f.at(1))
        for _ in range(DEMOTE_AFTER_FAILURES):
            record = record.after(Verdict.UNREACHABLE, f.at(2))

        assert record.consecutive_failures == 0
        assert not record.should_demote
        assert record.clean_streak == 2, "a browser that was closed is not the skill drifting"
        assert record.total_runs == 5, "the attempts happened and the record says so"
        assert record.unreachable_runs == 3, "in their own column, neither win nor fault"

    def test_a_run_that_did_reach_the_system_still_counts_towards_demotion(self) -> None:
        record = TrackRecord()
        for _ in range(DEMOTE_AFTER_FAILURES):
            record = record.after(Verdict.UNREACHABLE, f.at(1))
            record = record.after(Verdict.FAILED, f.at(2))

        assert record.should_demote, "an unreachable run between them interrupts nothing"


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
        assert verdict.state is BreakerState.OPEN
        assert "without a person deciding" in (verdict.reason or "")

    # Every limit below is a boundary, and a boundary nothing stands on is a
    # number that can move by one without any test noticing. A mutation sweep
    # over this module on 2026-09-13 read 60.6%, and every survivor was one of
    # these: `>` for `>=` on both caps, `<=` for `<` on both windows, and the
    # OPEN state itself, which no test looked at because `permitted` is False
    # for any state that is not CLOSED.

    def test_a_batch_of_exactly_the_limit_is_still_somebody_doing_their_job(self) -> None:
        # "Bigger than this is a migration" -- so this size is not one.
        assert assess((), f.at(1), requested_writes=MAX_ITEMS_PER_BATCH).permitted

    def test_one_failure_short_of_the_trip_still_permits_a_run(self) -> None:
        now = f.at(1000)
        facts = tuple(
            RunFact(finished_at=now - timedelta(minutes=i), failed=True, writes=0)
            for i in range(TRIP_AFTER - 1)
        )

        assert assess(facts, now).permitted

    def test_a_failure_exactly_as_old_as_the_window_still_counts(self) -> None:
        """The window is inclusive, and this is the only test that says so.

        It matters more than the second it describes: with `<` the third
        failure ages out at the instant the breaker would have tripped, so a
        system failing steadily every five minutes never trips at all."""
        now = f.at(100_000)
        facts = tuple(
            RunFact(finished_at=now - FAILURE_WINDOW, failed=True, writes=0)
            for _ in range(TRIP_AFTER)
        )

        verdict = assess(facts, now)

        assert not verdict.permitted
        assert verdict.state is BreakerState.OPEN

    def test_a_failure_one_second_past_the_window_does_not(self) -> None:
        now = f.at(100_000)
        facts = tuple(
            RunFact(finished_at=now - FAILURE_WINDOW - timedelta(seconds=1), failed=True, writes=0)
            for _ in range(TRIP_AFTER)
        )

        assert assess(facts, now).permitted

    def test_a_run_that_did_not_fail_never_counts_towards_the_trip(self) -> None:
        now = f.at(1000)
        facts = tuple(
            RunFact(finished_at=now - timedelta(minutes=i), failed=False, writes=0)
            for i in range(TRIP_AFTER * 3)
        )

        assert assess(facts, now).permitted

    def test_the_hour_of_writes_is_inclusive_at_its_edge(self) -> None:
        now = f.at(100_000)
        facts = (
            RunFact(finished_at=now - WRITE_WINDOW, failed=False, writes=MAX_WRITES_PER_WINDOW),
        )

        assert not assess(facts, now).permitted

    def test_a_write_older_than_the_hour_is_no_longer_spent(self) -> None:
        now = f.at(100_000)
        facts = (
            RunFact(
                finished_at=now - WRITE_WINDOW - timedelta(seconds=1),
                failed=False,
                writes=MAX_WRITES_PER_WINDOW,
            ),
        )

        assert assess(facts, now).permitted

    def test_the_write_this_run_wants_is_counted_against_the_hour_with_the_rest(self) -> None:
        """One under the cap plus this run's own write is exactly the cap, and
        exactly the cap is allowed. One more is not.

        The default `requested_writes=1` is the assumption the whole limit
        rests on -- a run asks to write once unless it says otherwise -- and
        without this pair nothing would notice it changing."""
        now = f.at(1000)
        nearly = (
            RunFact(
                finished_at=now - timedelta(minutes=5),
                failed=False,
                writes=MAX_WRITES_PER_WINDOW - 1,
            ),
        )

        assert assess(nearly, now).permitted
        assert not assess(nearly, now, requested_writes=2).permitted
