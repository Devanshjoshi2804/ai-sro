"""Who may say a run came out wrong, and what saying so does.

A run drives one operator's browser and they are the only person who saw what it
produced. Anybody else in the tenant is guessing, and a guess in a track record
is worse than a silence -- it demotes a skill on the strength of somebody's
impression of a screen they were not looking at.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.call_run_wrong import CallRunWrong, NotYours, StillRunning
from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.execution.verdict import apply_verdict
from sro.domain.shared.identifiers import PrincipalId, SkillId
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.track_record import DEMOTE_AFTER_FAILURES
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeUnitOfWork

OPERATOR = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _run(*, requested_by: PrincipalId = f.OPERATOR, run_id: str = "run-1") -> Run:
    # Local, like `test_autonomy.py`'s `_run`: there is no shared `f.run`
    # builder, and the point of this test is the use case, not a new factory.
    return Run(
        id=RunId(run_id),
        tenant_id=f.TENANT,
        skill_id=SkillId("skill-1"),
        skill_version=1,
        stage=PromotionStage.ASSISTED,
        parameters={},
        requested_by=requested_by,
        started_at=f.at(0),
        authorized_by=f.OPERATOR,
        target_system="blue_yonder",
    )


def _step(**overrides: object) -> StepOutcome:
    defaults: dict[str, object] = {
        "index": 0,
        "medium": Medium.NETWORK,
        "disposition": StepDisposition.PERFORMED,
        "intent": "adjust",
        "status_code": 200,
    }
    return StepOutcome(**{**defaults, **overrides})


async def _a_finished_run(uow: FakeUnitOfWork, run_id: str = "run-1") -> Run:
    run = _run(run_id=run_id)
    run.record(_step())
    run.finish(f.at(60))
    async with uow as open_uow:
        await open_uow.runs.add(run)
        await open_uow.commit()
    return run


async def test_saying_it_was_wrong_counts_against_the_skill() -> None:
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    run = await _a_finished_run(uow)
    skill = f.skill()
    async with uow as open_uow:
        await open_uow.skills.add(skill)
        await open_uow.commit()

    await CallRunWrong(uow, clock).execute(
        OPERATOR, run_id=run.id, because="undone by the operator"
    )

    async with uow as open_uow:
        again = await open_uow.runs.get(f.TENANT, run.id)
        assert again.wrong_because == "undone by the operator"

        # The run was otherwise clean -- one step, performed, status 200 -- so
        # without `wrong_because` this would have read as a CLEAN run. It counts
        # as a failure instead, because the ladder cannot see this on its own.
        again_skill = await open_uow.skills.get(f.TENANT, skill.id)
        assert again_skill.version(1).track_record.consecutive_failures == 1


async def test_somebody_else_cannot_call_your_run_wrong() -> None:
    """They did not see it. A guess in the track record is worse than a silence."""
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    run = await _a_finished_run(uow)
    somebody_else = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("nobody"))

    with pytest.raises(NotYours):
        await CallRunWrong(uow, clock).execute(
            somebody_else, run_id=run.id, because="looked wrong to me"
        )


async def test_a_run_still_going_cannot_be_called_wrong_yet() -> None:
    """There is no result to judge. Stopping a run is a different button and it
    already exists."""
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    running = _run()
    async with uow as open_uow:
        await open_uow.runs.add(running)
        await open_uow.commit()

    with pytest.raises(StillRunning, match="still going"):
        await CallRunWrong(uow, clock).execute(
            OPERATOR, run_id=running.id, because="undone by the operator"
        )


async def test_one_run_leaves_one_entry_in_the_record_not_two() -> None:
    """`FinishRun` already judged this run when it ended. Calling it wrong
    revises that answer; it does not add a second run.

    Before this, one run that succeeded and was then called wrong left the
    version claiming two attempts: a clean one and a failed one. `total_runs`
    and `clean_runs` overstated permanently, and -- worse -- `earn` read that
    phantom clean run, so a version one clean run short of a rung could be
    promoted on the strength of a run the operator was in the middle of taking
    back.

    Both halves of the story are performed here, in order, exactly as the two
    use cases perform them: `apply_verdict` once for the run finishing clean,
    then `CallRunWrong` for the operator saying it was not.
    """
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    run = await _a_finished_run(uow)
    skill = f.skill()
    async with uow as open_uow:
        await open_uow.skills.add(skill)
        # What `FinishRun` did when this run ended: one clean run, counted.
        apply_verdict(skill, run, f.at(60))
        await open_uow.skills.save(skill)
        await open_uow.commit()
    assert skill.version(1).track_record.clean_runs == 1

    await CallRunWrong(uow, clock).execute(
        OPERATOR, run_id=run.id, because="undone by the operator"
    )

    record = skill.version(1).track_record
    assert record.total_runs == 1, "one run left two entries in the record"
    assert record.clean_runs == 0, "a run the operator took back is still counted clean"
    assert record.failed_runs == 1
    assert record.consecutive_failures == 1, "the demotion count still has to see it"


async def test_a_skill_that_is_wrong_every_single_time_demotes() -> None:
    """The backstop ADR 014 leans its whole residual-risk argument on, run
    through the sequence that actually happens.

    Not three runs that failed. A run that *succeeded* -- every step clean, the
    system happy -- and made the wrong record, which the operator sees and
    takes back. That is the exact shape the ADR describes: "a preview that
    undersold a write becomes a run the operator can call wrong the moment they
    see what it made; that counts against the streak exactly like any other
    failure, and `DEMOTE_AFTER_FAILURES = 3` pulls the version back below
    ASSISTED on the third one."

    It did not. `FinishRun` records CLEAN the moment the run ends, and
    `after(CLEAN)` zeroes `consecutive_failures`; the operator's answer arrives
    afterwards and can only count up from zero. So the counter oscillated 0 -> 1
    on every run and never once reached three, and a skill that produced the
    wrong record every single time ran assisted forever. Closing the preview
    door in `promote` did not touch this, because this is the same failure
    arriving through `FinishRun`'s door instead.
    """
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    skill = f.skill()
    version = skill.version(1)
    version.promote(PromotionStage.SHADOW, f.at(10), f.OPERATOR, acknowledging_fixed_values=True)
    version.promote(PromotionStage.ASSISTED, f.at(20), f.OPERATOR, acknowledging_fixed_values=True)
    async with uow as open_uow:
        await open_uow.skills.add(skill)
        await open_uow.commit()

    for attempt in range(1, DEMOTE_AFTER_FAILURES + 1):
        run = await _a_finished_run(uow, run_id=f"run-{attempt}")
        async with uow as open_uow:
            # What `FinishRun` does the instant the run ends: nothing has gone
            # wrong that any assertion could see, so this is a clean run.
            apply_verdict(skill, run, f.at(60 * attempt))
            await open_uow.skills.save(skill)
            await open_uow.commit()
        # Zero, correctly: as far as anything can tell at this instant the run
        # worked, and a run that worked resets the count. What must not happen
        # is that zero surviving the operator's answer below -- the count has
        # to come back to where the clean verdict found it and then rise.
        assert version.track_record.consecutive_failures == 0

        # And what the operator does once they look at what it made.
        await CallRunWrong(uow, clock).execute(
            OPERATOR, run_id=run.id, because="it made the wrong record again"
        )
        assert version.track_record.consecutive_failures == attempt, (
            f"wrong run {attempt} did not count as the {attempt}th failure in a row"
        )

    assert version.stage is PromotionStage.SHADOW, (
        "a skill that made the wrong record every single time never demoted"
    )
    assert version.track_record.total_runs == DEMOTE_AFTER_FAILURES
    assert version.track_record.clean_runs == 0
