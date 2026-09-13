"""A task done often enough becomes a skill with nobody pressing anything.

The operator this is for is doing their job, not watching a panel. Everything
needed was already true -- the evidence is stored verbatim, teaching reads it
back rather than asking for the task again -- so what is added here is the
press, and nothing else. What comes out is a skill at the bottom of the ladder:
recorded, never rehearsed, never run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.induction.version import INDUCTION_VERSION
from sro.application.observation.learn import LearnWhatRepeats
from sro.domain.observation.candidate import (
    WORTH_OFFERING,
    CandidateStatus,
    Episode,
    TaskCandidate,
)
from sro.domain.shared.identifiers import BatchId, CandidateId, SkillId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
START = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
LEARNED = SkillId("skl-1")


@dataclass
class _Teaches:
    """Teaching, stood in for. What it does with the evidence is proved in
    `test_teaching_what_was_watched.py`; what matters here is which candidates
    it is asked about at all."""

    asked: list[CandidateId]
    skill_id: SkillId | None = LEARNED
    because: str | None = None
    blows_up: bool = False

    async def execute(self, ctx: RequestContext, *, candidate_id: CandidateId) -> object:
        self.asked.append(candidate_id)
        if self.blows_up:
            raise InductionFailed("the evidence for this will not align")

        @dataclass(frozen=True)
        class _Taught:
            candidate_id: CandidateId
            recording_id: None = None
            skill_id: SkillId | None = None
            needs_demonstration: bool = False
            because: str | None = None

        return _Taught(
            candidate_id=candidate_id,
            skill_id=self.skill_id,
            needs_demonstration=self.skill_id is None,
            because=self.because,
        )


def _candidate(
    number: int, *, times_seen: int, status: CandidateStatus = CandidateStatus.NEW
) -> TaskCandidate:
    episodes = tuple(
        Episode(
            started_at=START + timedelta(hours=doing),
            ended_at=START + timedelta(hours=doing, seconds=30),
            host="wms.acme.test",
            batch_ids=(BatchId(f"bat-{doing}"),),
            gestures=2,
            calls=2,
        )
        for doing in range(times_seen)
    )
    return TaskCandidate(
        id=CandidateId(f"cnd-{number}"),
        tenant_id=f.TENANT,
        principal_id=f.OPERATOR,
        signature=f"POST api/suppliers/{number}",
        host="wms.acme.test",
        title=f"Create suppliers {number} on wms.acme.test",
        status=status,
        episodes=episodes,
    )


async def _learner(*candidates: TaskCandidate) -> tuple[LearnWhatRepeats, _Teaches, FakeUnitOfWork]:
    uow = FakeUnitOfWork()
    for candidate in candidates:
        await uow.candidates.add(candidate)
    teaches = _Teaches(asked=[])
    return LearnWhatRepeats(uow, teaches), teaches, uow


async def test_a_task_done_often_enough_is_learned_with_nobody_asking() -> None:
    often = _candidate(1, times_seen=WORTH_OFFERING)
    learner, teaches, _ = await _learner(often)

    learned = await learner.execute(CTX)

    assert teaches.asked == [often.id]
    assert learned.skills == [LEARNED]


async def test_a_coincidence_is_left_alone() -> None:
    """Twice is a coincidence and the operator knows it. Learning from one
    would fill the console with skills nobody wants and teach people to ignore
    the whole surface."""
    learner, teaches, _ = await _learner(_candidate(1, times_seen=WORTH_OFFERING - 1))

    learned = await learner.execute(CTX)

    assert teaches.asked == []
    assert learned.skills == []


async def test_something_somebody_already_said_no_to_is_not_learned_anyway() -> None:
    """The one thing automatic learning must never do: overrule a person. A
    dismissed candidate stays dismissed however often it happens."""
    dismissed = _candidate(1, times_seen=WORTH_OFFERING * 2, status=CandidateStatus.DISMISSED)
    learner, teaches, _ = await _learner(dismissed)

    await learner.execute(CTX)

    assert teaches.asked == []


async def test_evidence_that_will_not_induce_waits_for_a_person() -> None:
    """It stays `new`, which is exactly what puts it in front of an operator as
    "teach me this once" -- rather than being marked done with no skill behind
    it."""
    waiting = _candidate(1, times_seen=WORTH_OFFERING)
    learner, teaches, uow = await _learner(waiting)
    teaches.skill_id = None
    teaches.because = "no two doings of this align"

    learned = await learner.execute(CTX)

    assert learned.skills == []
    assert learned.still_waiting == [f"{waiting.title}: no two doings of this align"]
    assert uow.candidates.rows[waiting.id.value].status is CandidateStatus.NEW


async def test_one_candidate_that_breaks_does_not_stop_the_rest() -> None:
    """This runs on a sweep with nobody watching. A pass that dies on the first
    bad candidate stops learning anything at all, quietly, for weeks."""
    first = _candidate(1, times_seen=WORTH_OFFERING)
    second = _candidate(2, times_seen=WORTH_OFFERING)
    learner, teaches, _ = await _learner(first, second)

    class _BlowsUpOnce(_Teaches):
        async def execute(self, ctx: RequestContext, *, candidate_id: CandidateId) -> object:
            if candidate_id == first.id:
                self.asked.append(candidate_id)
                raise InductionFailed("this one's evidence is broken")
            return await super().execute(ctx, candidate_id=candidate_id)

    learner._teach = _BlowsUpOnce(asked=teaches.asked)  # type: ignore[assignment]

    learned = await learner.execute(CTX)

    assert teaches.asked == [first.id, second.id]
    assert learned.skills == [LEARNED]


async def test_evidence_already_refused_is_not_tried_again_every_sweep() -> None:
    """The sweep comes round every quarter of an hour.

    An attempt on evidence that already refused refuses again and leaves two
    more sealed recordings behind it -- ninety-six pairs a day, for one
    candidate whose two doings happen to differ.
    """
    waiting = _candidate(1, times_seen=WORTH_OFFERING)
    learner, teaches, _ = await _learner(waiting)
    teaches.skill_id = None
    teaches.because = "no two doings of this align"

    await learner.execute(CTX)
    await learner.execute(CTX)

    assert teaches.asked == [waiting.id], "the same evidence was tried twice"


async def test_a_further_doing_is_worth_another_attempt() -> None:
    """And the pair that would induce is usually the next two, so waiting
    forever is not an option either."""
    waiting = _candidate(1, times_seen=WORTH_OFFERING)
    learner, teaches, uow = await _learner(waiting)
    teaches.skill_id = None

    await learner.execute(CTX)
    stored = uow.candidates.rows[waiting.id.value]
    stored.observed(
        Episode(
            started_at=START + timedelta(days=1),
            ended_at=START + timedelta(days=1, seconds=30),
            host="wms.acme.test",
            batch_ids=(BatchId("bat-later"),),
            gestures=2,
            calls=2,
        )
    )
    teaches.skill_id = LEARNED

    learned = await learner.execute(CTX)

    assert teaches.asked == [waiting.id, waiting.id]
    assert learned.skills == [LEARNED]


async def test_evidence_refused_under_older_rules_is_tried_again() -> None:
    """The other half of "something new to try it on": the rules change too.

    This candidate was refused, no further doing ever came, and induction was
    fixed in between. Without the version stamp it sits refused forever while
    the code that would learn it is already merged -- which is exactly what
    happened, and had to be undone by hand.
    """
    refused = _candidate(1, times_seen=WORTH_OFFERING)
    refused.learned_from = refused.times_seen
    refused.learned_under = INDUCTION_VERSION - 1
    learner, teaches, uow = await _learner(refused)

    learned = await learner.execute(CTX)

    assert teaches.asked == [refused.id]
    assert learned.skills == [LEARNED]
    assert uow.candidates.rows[refused.id.value].learned_under == INDUCTION_VERSION
