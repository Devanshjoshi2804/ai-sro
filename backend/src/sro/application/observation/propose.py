"""What a model may say about a task the miner found.

Three things, and they are all *about* candidates rather than part of them:
a sentence a person would recognise, a suggestion that two candidates are one
task done two ways, and a suggestion that two are halves of one workflow across
systems.

None of it touches identity. A candidate is `(principal, signature)` compared
for equality, because mining re-runs and induction pairs on exact keys -- and a
model that answers slightly differently on a second pass would produce a second
candidate whose demonstrations can never pair. See `docs/15-observation-to-tasks.md`.

Every model call here is behind a deterministic filter that has already decided
the question is worth asking. A day's candidates crossed with each other is a
lot of pairs, and most of them are obviously unrelated to a `for` loop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from sro.application.context import RequestContext
from sro.application.ports.interpretation import WorkflowInterpreter
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.candidate import (
    CandidateStatus,
    Episode,
    Join,
    JoinAnswer,
    JoinKind,
    TaskCandidate,
)
from sro.domain.shared.identifiers import CandidateId

logger = logging.getLogger(__name__)

MOST_PAIRS = 20
"""How many pairs one sweep will ask about. A ceiling rather than a budget: the
answer is a sentence on a screen, and nobody's model bill should scale with how
many tabs somebody had open."""

TOGETHER_WITHIN = timedelta(minutes=5)
"""How close two episodes in different systems have to be to look like halves of
one piece of work."""

TOGETHER_TIMES = 2
"""And how often. Once is two things happening to be done in a row."""

ENOUGH_OVERLAP = 0.6
"""How much of the smaller signature has to appear in the larger before two
candidates in one system are worth asking about."""


@dataclass(frozen=True, slots=True)
class Proposed:
    named: int = 0
    joined: int = 0
    asked: int = 0
    """Model calls made. Reported because this is the one part of the pipeline
    that costs money per candidate."""


class ProposeAboutCandidates:
    """The three model slots, run over one tenant's candidates."""

    def __init__(self, uow: UnitOfWork, interpreter: WorkflowInterpreter) -> None:
        self._uow = uow
        self._interpreter = interpreter

    async def execute(self, ctx: RequestContext) -> Proposed:
        async with self._uow as uow:
            candidates = await uow.candidates.list_for_tenant(
                ctx.tenant_id, status=CandidateStatus.NEW
            )

        worth = [candidate for candidate in candidates if candidate.worth_offering]
        # A deployment that may not call a hosted model still mines, still
        # offers candidates, still teaches. It gets duller titles -- and duller
        # reasons, but it still gets the suggestions: which two candidates go
        # together is decided by adjacency in the evidence, and only the
        # sentence about it was ever the model's.
        named, asked = await self._name(worth) if self._interpreter.available else (0, 0)
        joined, asked_again = await self._join(worth)
        return Proposed(named=named, joined=joined, asked=asked + asked_again)

    async def _name(self, candidates: list[TaskCandidate]) -> tuple[int, int]:
        """Slot 1: the sentence on the front.

        Only for candidates nothing has named yet. A title a person edited is
        theirs, and a title a model already wrote is not worth paying for
        twice.
        """
        named = asked = 0
        for candidate in candidates:
            if candidate.named_by_model:
                continue
            asked += 1
            answer = await self._interpreter.name_task(_describe(candidate))
            title = answer.title.strip()
            if not title:
                # The model was told to say nothing rather than guess. The
                # derived title stands, which is dull and correct. Stripped
                # here rather than trusting the adapter to have done it: a
                # blank title would fail the candidate's own invariant, deep
                # inside a sweep, over a sentence nobody needed.
                continue
            candidate.rename(title, by_model=True)
            async with self._uow as uow:
                await uow.candidates.save(candidate)
                await uow.commit()
            named += 1
        return named, asked

    async def _join(self, candidates: list[TaskCandidate]) -> tuple[int, int]:
        """Slots 2 and 3: what this candidate might be part of."""
        pairs = [
            (kind, first, second)
            for kind, first, second in (*_variants(candidates), *_workflows(candidates))
            # A pair somebody has already looked at is not a question any more.
            # Asking the model again would spend a call to re-suggest what a
            # person answered, and `suggest` would refuse to store it anyway.
            if not _settled(first, second, kind)
        ][:MOST_PAIRS]

        joined = asked = 0
        for kind, first, second in pairs:
            if self._interpreter.available:
                asked += 1
                judgement = await self._interpreter.judge_join(
                    kind.value, _describe(first), _describe(second)
                )
                if not judgement.joined or not judgement.because.strip():
                    continue
                because, by_model = judgement.because, True
            else:
                # What the evidence says, in the plainest words there are. The
                # model reads a pair better than a rule does and is why this
                # asks it where it can -- but a suggestion nobody can make
                # without one is a feature that exists only for deployments
                # that pay for a model, and the pairing was never the model's
                # decision to make.
                because, by_model = _plainly(kind, first, second), False
            # On both, because a suggestion visible from only one of two
            # candidates is a suggestion half the people who look will miss.
            first.suggest(Join(other_id=second.id, kind=kind, because=because, by_model=by_model))
            second.suggest(Join(other_id=first.id, kind=kind, because=because, by_model=by_model))
            async with self._uow as uow:
                await uow.candidates.save(first)
                await uow.candidates.save(second)
                await uow.commit()
            joined += 1
        return joined, asked


class AnswerJoin:
    """A person saying what two candidates are to each other.

    This is the line `docs/15` draws. A model may notice that two candidates
    look like one piece of work and say why; it may not decide that they are,
    because a candidate's identity is what makes mining re-runnable and pairing
    exact. So the suggestion waits until somebody looks.

    Answering `same` about a variant does the one thing that follows from it:
    the other candidate is dismissed as a duplicate of this one, naming it. Not
    deleted -- a dismissed candidate is kept precisely so the miner does not
    offer it again next week as though it were new -- and not merged, because
    merging two signatures would mean inventing a third that neither was.

    Answering `same` about a workflow records exactly that and nothing more.
    Two candidates in two systems being one job is a shape nothing here can
    represent yet, and a fact recorded honestly is worth more than a merge that
    would have to be undone.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        candidate_id: CandidateId,
        other_id: CandidateId,
        kind: JoinKind,
        answer: JoinAnswer,
    ) -> TaskCandidate:
        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
            other = await uow.candidates.get(ctx.tenant_id, other_id)

            candidate.answer(other_id, kind, answer, ctx.principal_id)
            # On both, because the pair is the thing being answered and a
            # screen showing one of them must not still be asking.
            if other.join_with(candidate_id, kind) is not None:
                other.answer(candidate_id, kind, answer, ctx.principal_id)

            if answer is JoinAnswer.SAME and kind is JoinKind.VARIANT and other.status_is_new:
                other.dismiss(f"the same task as {candidate.title}, done another way")

            await uow.candidates.save(candidate)
            await uow.candidates.save(other)
            await uow.commit()
        return candidate


def _variants(
    candidates: list[TaskCandidate],
) -> list[tuple[JoinKind, TaskCandidate, TaskCandidate]]:
    """Same operator, same system, nearly the same steps.

    The filter is a plain overlap of call shapes: the same task done with one
    extra page shares most of its signature, and two unrelated tasks on one
    system share the screen they both start from and little else.
    """
    pairs = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1 :]:
            if first.principal_id != second.principal_id or first.host != second.host:
                continue
            if _overlap(first.signature, second.signature) < ENOUGH_OVERLAP:
                continue
            if first.signature == second.signature:
                continue  # the same candidate; the miner would not have made two
            pairs.append((JoinKind.VARIANT, first, second))
    return pairs


def _workflows(
    candidates: list[TaskCandidate],
) -> list[tuple[JoinKind, TaskCandidate, TaskCandidate]]:
    """Same operator, different systems, done together more than once.

    Together in either shape `occurrences` counts: one after the other, or both
    tabs open and worked in at once.

    Segmentation runs each host on its own stream, so an episode is always one
    host's -- which makes this the shape no candidate can have on its own:
    "check the WMS, then record it in the ERP" is two candidates and always
    will be.
    """
    pairs = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1 :]:
            if first.principal_id != second.principal_id or first.host == second.host:
                continue
            if _followed(first, second) + _followed(second, first) >= TOGETHER_TIMES:
                pairs.append((JoinKind.WORKFLOW, first, second))
    return pairs


def _settled(first: TaskCandidate, second: TaskCandidate, kind: JoinKind) -> bool:
    """Whether a person has already said what this pair is."""
    return any(
        (candidate.join_with(other.id, kind) or _UNANSWERED).is_answered
        for candidate, other in ((first, second), (second, first))
    )


_UNANSWERED = Join(other_id=CandidateId("none"), kind=JoinKind.VARIANT, because="not asked")


def occurrences(first: TaskCandidate, second: TaskCandidate) -> list[tuple[Episode, Episode]]:
    """Each time an episode of `second` belongs with one of `first`.

    Two shapes, because a person does a job across two systems in two ways.
    They finish in the mail and move to the warehouse -- sequential, which is
    what this counted before. Or they keep both open and go back and forth,
    which produces episodes that overlap and which this counted as nothing at
    all, so the join built for exactly that shape was never proposed.

    The pairs themselves, because teaching the two candidates as one skill needs
    the halves that actually belong together: two doings a fortnight apart are
    two doings, and reading one window across both would sweep up whatever the
    operator did in between.

    Oldest first, which is how episodes are stored; the caller takes from the
    end when it wants the freshest.
    """
    return [
        (earlier, later)
        for earlier in first.episodes
        for later in second.episodes
        if _together(earlier, later)
    ]


def _together(earlier: Episode, later: Episode) -> bool:
    gap = later.started_at - earlier.ended_at
    if timedelta(0) <= gap <= TOGETHER_WITHIN:
        return True
    return _interleaved(earlier, later)


def _interleaved(earlier: Episode, later: Episode) -> bool:
    """Overlapping in time, and touched by a person in the same stretch.

    Overlap alone would pair a mailbox somebody left open with whatever else
    they did that hour: the tab was there, the client polled, and none of it
    was work. So the windows compared are the ones an episode records for when
    somebody actually had their hands on it.

    Directional -- only the episode that started first may be the earlier half.
    `_workflows` counts both directions against `TOGETHER_TIMES`, so a
    symmetric rule would let one interleaved pair reach the threshold alone.

    Ordered on `(started_at, ended_at, host)` rather than on `started_at`
    alone, because both timestamps come from event data and two tabs starting
    in the same second is not exotic. That is a total order for two episodes of
    two candidates -- their hosts differ, which is what makes them a workflow
    at all -- so exactly one direction of any pair qualifies, ties included.
    """
    if (earlier.started_at, earlier.ended_at, earlier.host) >= (
        later.started_at,
        later.ended_at,
        later.host,
    ):
        return False
    if not (later.started_at < earlier.ended_at):
        return False
    if (
        earlier.touched_from is None
        or earlier.touched_until is None
        or later.touched_from is None
        or later.touched_until is None
    ):
        # Mined before an episode recorded this. It keeps the meaning it had.
        return False
    return (
        later.touched_from - earlier.touched_until <= TOGETHER_WITHIN
        and earlier.touched_from - later.touched_until <= TOGETHER_WITHIN
    )


def _followed(first: TaskCandidate, second: TaskCandidate) -> int:
    """How often an episode of `second` belongs with one of `first` -- either
    beginning just as it ended, or overlapping it with somebody's hands in both."""
    return len(occurrences(first, second))


def _plainly(kind: JoinKind, first: TaskCandidate, second: TaskCandidate) -> str:
    """The reason, when nothing was asked to write one.

    Says what was counted, so a person can weigh it: a suggestion whose reason
    is "the system thinks so" is one nobody can answer.
    """
    if kind is JoinKind.WORKFLOW:
        # Both directions, because both are what `_workflows` counted: an
        # operator flipping tabs will not flip the same way twice, so a pair
        # that qualified once each way is proposed on 1 + 1 -- and reporting
        # the larger direction alone says "1 times" for something that
        # happened twice.
        forwards, backwards = occurrences(first, second), occurrences(second, first)
        pairs = forwards + backwards
        times = len(pairs)
        # The order named is the one it more often went in. With one doing each
        # way there is no such order, and the sentence for that case does not
        # claim one: it says both tabs were open at once.
        order = (first, second) if len(forwards) >= len(backwards) else (second, first)
        # Which shape it was, because "one after the other" is simply false about
        # somebody who kept both tabs open, and a reason a person cannot weigh is
        # a reason nobody answers.
        at_once = sum(1 for earlier, later in pairs if _interleaved(earlier, later))
        if at_once == times:
            return f"worked in both at once {times} times -- {order[0].host} and {order[1].host}"
        if at_once:
            return (
                f"done together {times} times -- {order[0].host} and {order[1].host}, "
                f"{at_once} of them with both open at once"
            )
        return f"done one after the other {times} times -- {order[0].host}, then {order[1].host}"
    steps = len(set(first.signature.split(" → ")) & set(second.signature.split(" → ")))
    return f"{steps} of their steps are the same call"


def _overlap(first: str, second: str) -> float:
    """How much of the smaller signature the larger one contains, by step."""
    one, two = set(first.split(" → ")), set(second.split(" → "))
    if not one or not two:
        return 0.0
    return len(one & two) / min(len(one), len(two))


def _describe(candidate: TaskCandidate) -> str:
    """What the model is shown about a candidate.

    Its shape and its cost, and nothing else: no bodies, no responses, no
    payloads. Naming a task needs the steps and the system, and everything else
    would be egress bought for nothing.
    """
    return "\n".join(
        (
            f"system: {candidate.host}",
            f"done {candidate.times_seen} times, "
            f"about {candidate.median_duration_ms // 1000}s each",
            f"currently called: {candidate.title}",
            "steps:",
            *(f"  {step}" for step in candidate.signature.split(" → ")),
        )
    )
