"""What a model is allowed to say about a task the miner found.

Three things, all of them *about* a candidate rather than part of one: a
sentence a person would recognise, and two kinds of suggestion that two
candidates are one piece of work. See `docs/15-observation-to-tasks.md`.

The line these tests defend is identity. `(principal, signature)` is what makes
two doings the same task, and it is compared for equality — because mining
re-runs and induction pairs on exact keys, so a model that answered slightly
differently on a second pass would produce a second candidate whose
demonstrations can never pair with the first's. Everything below checks that a
model can write on a candidate without ever reaching that.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sro.application.context import RequestContext
from sro.application.observation.propose import (
    MOST_PAIRS,
    AnswerJoin,
    ProposeAboutCandidates,
)
from sro.application.ports.interpretation import Judgement, Reading, TaskName
from sro.domain.observation.candidate import (
    CandidateStatus,
    Episode,
    JoinAnswer,
    JoinKind,
    TaskCandidate,
)
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, CandidateId, PrincipalId
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
NINE = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)

ADJUST = "PUT wm/inventory/adjust → GET wm/inventory/*"
ADJUST_WITH_A_DETOUR = "GET wm/inventory/* → PUT wm/inventory/adjust → GET wm/inventory/*"
RECEIVE = "POST erp/receipts → GET erp/receipts/*"


class FakeInterpreter:
    """Says what it is told to, and writes down what it was asked."""

    def __init__(
        self,
        *,
        name: TaskName | None = None,
        judgement: Judgement | None = None,
        available: bool = True,
    ) -> None:
        self._name = name or TaskName()
        self._judgement = judgement or Judgement()
        self._available = available
        self.named: list[str] = []
        self.judged: list[tuple[str, str, str]] = []

    @property
    def available(self) -> bool:
        return self._available

    async def read(self, evidence: str) -> Reading:
        raise AssertionError("naming a candidate must not read a demonstration")

    async def name_task(self, evidence: str) -> TaskName:
        self.named.append(evidence)
        return self._name

    async def judge_join(self, kind: str, first: str, second: str) -> Judgement:
        self.judged.append((kind, first, second))
        return self._judgement


def _candidate(
    ident: str,
    *,
    signature: str = ADJUST,
    host: str = "wms.acme.test",
    title: str = "Update adjust on wms.acme.test",
    principal: PrincipalId | None = None,
    at: tuple[datetime, ...] = (NINE,),
    named_by_model: bool = False,
) -> TaskCandidate:
    return TaskCandidate(
        id=CandidateId(ident),
        tenant_id=f.TENANT,
        principal_id=principal or f.OPERATOR,
        signature=signature,
        host=host,
        title=title,
        named_by_model=named_by_model,
        episodes=tuple(
            Episode(
                started_at=started,
                ended_at=started + timedelta(minutes=2),
                host=host,
                batch_ids=(BatchId("bat-1"),),
                gestures=2,
                calls=2,
            )
            for started in at
        ),
    )


async def _world(*candidates: TaskCandidate) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    for candidate in candidates:
        await uow.candidates.add(candidate)
    return uow


def _thrice(start: datetime = NINE) -> tuple[datetime, ...]:
    """Enough doings to be worth offering at all."""
    return tuple(start + timedelta(days=day) for day in range(3))


# -- slot 1: the sentence on the front ---------------------------------------


async def test_a_model_renames_a_candidate_and_cannot_touch_what_it_is() -> None:
    """The derived title is honest and unreadable. This is the one thing a
    model is unambiguously better at — and it is cosmetic by construction."""
    candidate = _candidate("cnd-1", at=_thrice())
    uow = await _world(candidate)
    interpreter = FakeInterpreter(name=TaskName(title="Adjust an LPN after a short ship"))

    proposed = await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    stored = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    assert proposed.named == 1
    assert stored.title == "Adjust an LPN after a short ship"
    assert stored.named_by_model is True, "a sentence was stored as though it were a fact"
    assert stored.signature == ADJUST, "the model reached the thing that decides identity"
    assert stored.host == "wms.acme.test"


async def test_a_model_with_nothing_to_say_leaves_the_derived_title_alone() -> None:
    """It is told to answer with nothing rather than guess: a wrong name on a
    list is worse than a dull one, because somebody teaches it believing it."""
    uow = await _world(_candidate("cnd-1", at=_thrice()))
    interpreter = FakeInterpreter(name=TaskName(title="  "))

    proposed = await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    stored = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    assert proposed.named == 0
    assert stored.title == "Update adjust on wms.acme.test"
    assert stored.named_by_model is False


async def test_a_candidate_already_named_is_not_paid_for_twice() -> None:
    uow = await _world(_candidate("cnd-1", at=_thrice(), named_by_model=True))
    interpreter = FakeInterpreter(name=TaskName(title="something else"))

    proposed = await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert interpreter.named == []
    assert proposed.asked == 0


async def test_a_candidate_nobody_would_be_offered_is_not_named() -> None:
    """Below the threshold it is a coincidence, not a task, and naming every
    coincidence is how a model bill scales with how many tabs somebody had."""
    uow = await _world(_candidate("cnd-1", at=(NINE,)))

    interpreter = FakeInterpreter(name=TaskName(title="never asked"))
    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert interpreter.named == []


async def test_no_interpreter_means_no_proposals_and_no_failure() -> None:
    """A deployment that may not call a hosted model still mines, still offers
    candidates, still teaches. It gets duller titles."""
    uow = await _world(_candidate("cnd-1", at=_thrice()))
    interpreter = FakeInterpreter(available=False)

    proposed = await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert proposed == type(proposed)()
    assert interpreter.named == []


async def test_the_model_is_shown_the_shape_of_the_task_and_no_payloads() -> None:
    """Naming needs the steps and the system. Bodies and responses would be
    egress bought for nothing."""
    uow = await _world(_candidate("cnd-1", at=_thrice()))
    interpreter = FakeInterpreter(name=TaskName(title="Adjust an LPN"))

    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    shown = interpreter.named[0]
    assert "wms.acme.test" in shown
    assert "PUT wm/inventory/adjust" in shown
    assert "done 3 times" in shown


# -- slots 2 and 3: what this candidate might be part of ---------------------


async def test_two_ways_of_doing_one_task_are_suggested_to_be_one() -> None:
    """Same operator, same system, nearly the same steps. Both carry the
    suggestion, because one visible from only one of two candidates is one half
    the people who look will miss."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice(), named_by_model=True),
        _candidate("cnd-2", signature=ADJUST_WITH_A_DETOUR, at=_thrice(), named_by_model=True),
    )
    interpreter = FakeInterpreter(
        judgement=Judgement(joined=True, because="the second checks the count first")
    )

    proposed = await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert proposed.joined == 1
    assert [kind for kind, _, _ in interpreter.judged] == ["variant"]
    first = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    second = await uow.candidates.get(f.TENANT, CandidateId("cnd-2"))
    assert [join.other_id.value for join in first.joins] == ["cnd-2"]
    assert [join.other_id.value for join in second.joins] == ["cnd-1"]
    assert first.joins[0].kind is JoinKind.VARIANT
    assert first.joins[0].because == "the second checks the count first"
    assert first.joins[0].by_model is True


async def test_nothing_is_merged_by_a_suggestion() -> None:
    """The suggestion is a sentence on a screen. Acting on it is a person's
    decision, because a suggestion the system acted on is a task identity a
    model decided after all."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice(), named_by_model=True),
        _candidate("cnd-2", signature=ADJUST_WITH_A_DETOUR, at=_thrice(), named_by_model=True),
    )
    interpreter = FakeInterpreter(judgement=Judgement(joined=True, because="one task"))

    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    both = await uow.candidates.list_for_tenant(f.TENANT)
    assert len(both) == 2, "a suggestion merged two candidates"
    assert {candidate.signature for candidate in both} == {ADJUST, ADJUST_WITH_A_DETOUR}


async def test_two_unrelated_tasks_in_one_system_are_never_asked_about() -> None:
    """The filter is what keeps this affordable: a day's candidates crossed
    with each other is a lot of pairs, and most are obviously unrelated."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice(), named_by_model=True),
        _candidate("cnd-2", signature="GET wm/labels/*", at=_thrice(), named_by_model=True),
    )
    interpreter = FakeInterpreter(judgement=Judgement(joined=True, because="anything"))

    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert interpreter.judged == []


async def test_a_task_that_spans_two_systems_is_suggested_as_one_workflow() -> None:
    """The shape no candidate can have on its own: an episode breaks on a host
    change, so 'check the WMS, then record it in the ERP' is two candidates and
    always will be."""
    wms = _thrice()
    erp = tuple(started + timedelta(minutes=3) for started in wms)
    uow = await _world(
        _candidate("cnd-1", at=wms, named_by_model=True),
        _candidate("cnd-2", signature=RECEIVE, host="erp.acme.test", at=erp, named_by_model=True),
    )
    interpreter = FakeInterpreter(
        judgement=Judgement(joined=True, because="the receipt records the adjustment")
    )

    proposed = await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert proposed.joined == 1
    assert [kind for kind, _, _ in interpreter.judged] == ["workflow"]
    first = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    assert first.joins[0].kind is JoinKind.WORKFLOW


async def test_doing_two_things_in_a_row_once_is_not_a_workflow() -> None:
    """Once is two things that happened to be done in a row."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice(), named_by_model=True),
        _candidate(
            "cnd-2",
            signature=RECEIVE,
            host="erp.acme.test",
            at=(NINE + timedelta(minutes=3), NINE + timedelta(days=9), NINE + timedelta(days=10)),
            named_by_model=True,
        ),
    )
    interpreter = FakeInterpreter(judgement=Judgement(joined=True, because="anything"))

    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert interpreter.judged == []


async def test_two_operators_doing_similar_work_are_not_joined() -> None:
    """A candidate is per person. Joining across people would say two people's
    work is one task, which is a different claim and nobody made it."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice(), named_by_model=True),
        _candidate(
            "cnd-2",
            signature=ADJUST_WITH_A_DETOUR,
            principal=PrincipalId("someone-else"),
            at=_thrice(),
            named_by_model=True,
        ),
    )
    interpreter = FakeInterpreter(judgement=Judgement(joined=True, because="anything"))

    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert interpreter.judged == []


async def test_a_join_nobody_can_explain_is_not_stored() -> None:
    """ "Yes" with no reason is not a suggestion, it is an assertion — and this
    one is shown to a person who has to decide whether to believe it."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice(), named_by_model=True),
        _candidate("cnd-2", signature=ADJUST_WITH_A_DETOUR, at=_thrice(), named_by_model=True),
    )
    interpreter = FakeInterpreter(judgement=Judgement(joined=True, because="   "))

    proposed = await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert proposed.joined == 0
    first = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    assert first.joins == ()


async def test_asking_again_replaces_the_answer_rather_than_stacking_it() -> None:
    """The question is asked again because the evidence grew. Two answers to
    one question on a screen is a screen nobody trusts."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice(), named_by_model=True),
        _candidate("cnd-2", signature=ADJUST_WITH_A_DETOUR, at=_thrice(), named_by_model=True),
    )
    await ProposeAboutCandidates(
        uow, FakeInterpreter(judgement=Judgement(joined=True, because="first answer"))
    ).execute(CTX)
    await ProposeAboutCandidates(
        uow, FakeInterpreter(judgement=Judgement(joined=True, because="a better answer"))
    ).execute(CTX)

    first = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    assert len(first.joins) == 1
    assert first.joins[0].because == "a better answer"


async def test_a_sweep_will_not_ask_about_more_pairs_than_it_is_allowed() -> None:
    """A ceiling rather than a budget: nobody's model bill should scale with
    how many tabs somebody had open."""
    many = [
        _candidate(
            f"cnd-{index}",
            signature=f"{ADJUST} → GET wm/extra/{index}",
            at=_thrice(),
            named_by_model=True,
        )
        for index in range(12)
    ]
    uow = await _world(*many)
    interpreter = FakeInterpreter(judgement=Judgement(joined=False))

    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert len(interpreter.judged) == MOST_PAIRS


# -- and what a person says back ---------------------------------------------


async def _suggested(kind: JoinKind = JoinKind.VARIANT) -> FakeUnitOfWork:
    """Two candidates the model has already joined."""
    first = _candidate("cnd-1", at=_thrice(), named_by_model=True)
    second = _candidate(
        "cnd-2",
        signature=ADJUST_WITH_A_DETOUR if kind is JoinKind.VARIANT else RECEIVE,
        host="wms.acme.test" if kind is JoinKind.VARIANT else "erp.acme.test",
        at=_thrice() if kind is JoinKind.VARIANT else _thrice(NINE + timedelta(minutes=3)),
        named_by_model=True,
    )
    uow = await _world(first, second)
    await ProposeAboutCandidates(
        uow, FakeInterpreter(judgement=Judgement(joined=True, because="one task"))
    ).execute(CTX)
    return uow


async def test_saying_two_are_the_same_dismisses_one_as_a_duplicate() -> None:
    """The one consequence that follows from `same`, and the reason the answer
    is a person's: a duplicate that stays on the list is a task somebody teaches
    twice."""
    uow = await _suggested()

    kept = await AnswerJoin(uow).execute(
        CTX,
        candidate_id=CandidateId("cnd-1"),
        other_id=CandidateId("cnd-2"),
        kind=JoinKind.VARIANT,
        answer=JoinAnswer.SAME,
    )

    duplicate = await uow.candidates.get(f.TENANT, CandidateId("cnd-2"))
    assert kept.status is CandidateStatus.NEW, "the candidate somebody kept was dismissed"
    assert duplicate.status is CandidateStatus.DISMISSED
    assert kept.title in (duplicate.dismissed_reason or ""), (
        "the duplicate does not say what it was a duplicate of"
    )
    # Kept, never deleted: the miner must not offer it again next week as if it
    # were new.
    assert duplicate.times_seen == 3


async def test_the_answer_is_recorded_on_both_and_names_who_gave_it() -> None:
    uow = await _suggested()

    await AnswerJoin(uow).execute(
        CTX,
        candidate_id=CandidateId("cnd-1"),
        other_id=CandidateId("cnd-2"),
        kind=JoinKind.VARIANT,
        answer=JoinAnswer.DIFFERENT,
    )

    for ident, other in (("cnd-1", "cnd-2"), ("cnd-2", "cnd-1")):
        candidate = await uow.candidates.get(f.TENANT, CandidateId(ident))
        join = candidate.join_with(CandidateId(other), JoinKind.VARIANT)
        assert join is not None and join.answered is JoinAnswer.DIFFERENT, (
            f"{ident} is still asking a question somebody answered"
        )
        assert join.answered_by == f.OPERATOR


async def test_saying_no_leaves_both_candidates_alone() -> None:
    uow = await _suggested()

    await AnswerJoin(uow).execute(
        CTX,
        candidate_id=CandidateId("cnd-1"),
        other_id=CandidateId("cnd-2"),
        kind=JoinKind.VARIANT,
        answer=JoinAnswer.DIFFERENT,
    )

    both = await uow.candidates.list_for_tenant(f.TENANT)
    assert [candidate.status for candidate in both] == [CandidateStatus.NEW] * 2


async def test_a_workflow_answered_yes_is_recorded_and_nothing_else() -> None:
    """Two candidates in two systems being one job is a shape nothing here can
    represent yet. A fact recorded honestly beats a merge that would have to be
    undone."""
    uow = await _suggested(JoinKind.WORKFLOW)

    await AnswerJoin(uow).execute(
        CTX,
        candidate_id=CandidateId("cnd-1"),
        other_id=CandidateId("cnd-2"),
        kind=JoinKind.WORKFLOW,
        answer=JoinAnswer.SAME,
    )

    both = await uow.candidates.list_for_tenant(f.TENANT)
    assert [candidate.status for candidate in both] == [CandidateStatus.NEW] * 2


async def test_the_next_sweep_does_not_ask_what_somebody_already_answered() -> None:
    """The whole reason the answer is recorded rather than acted on and
    forgotten. Re-suggesting is not only a wasted model call: it puts a
    question back on a screen that a person has already taken off it."""
    uow = await _suggested()
    await AnswerJoin(uow).execute(
        CTX,
        candidate_id=CandidateId("cnd-1"),
        other_id=CandidateId("cnd-2"),
        kind=JoinKind.VARIANT,
        answer=JoinAnswer.DIFFERENT,
    )

    interpreter = FakeInterpreter(judgement=Judgement(joined=True, because="asked again"))
    await ProposeAboutCandidates(uow, interpreter).execute(CTX)

    assert interpreter.judged == []
    candidate = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    join = candidate.join_with(CandidateId("cnd-2"), JoinKind.VARIANT)
    assert join is not None and join.because == "one task", (
        "a model overwrote the suggestion a person had answered"
    )


async def test_answering_something_nobody_suggested_is_refused() -> None:
    """An answer with no suggestion behind it has no evidence attached, and the
    reason the pair was shown together is half of what makes the answer
    readable a month later."""
    uow = await _world(
        _candidate("cnd-1", at=_thrice()),
        _candidate("cnd-2", signature=RECEIVE, at=_thrice()),
    )

    with pytest.raises(InvariantViolation, match="nothing suggested"):
        await AnswerJoin(uow).execute(
            CTX,
            candidate_id=CandidateId("cnd-1"),
            other_id=CandidateId("cnd-2"),
            kind=JoinKind.VARIANT,
            answer=JoinAnswer.SAME,
        )
