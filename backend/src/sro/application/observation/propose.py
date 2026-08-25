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
    Join,
    JoinKind,
    TaskCandidate,
)

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
        if not self._interpreter.available:
            # A deployment that may not call a hosted model still mines, still
            # offers candidates, still teaches. It gets duller titles.
            return Proposed()

        async with self._uow as uow:
            candidates = await uow.candidates.list_for_tenant(
                ctx.tenant_id, status=CandidateStatus.NEW
            )

        worth = [candidate for candidate in candidates if candidate.worth_offering]
        named, asked = await self._name(worth)
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
            *_variants(candidates),
            *_workflows(candidates),
        ][:MOST_PAIRS]

        joined = asked = 0
        for kind, first, second in pairs:
            asked += 1
            judgement = await self._interpreter.judge_join(
                kind.value, _describe(first), _describe(second)
            )
            if not judgement.joined or not judgement.because.strip():
                continue
            # On both, because a suggestion visible from only one of two
            # candidates is a suggestion half the people who look will miss.
            first.suggest(Join(other_id=second.id, kind=kind, because=judgement.because))
            second.suggest(Join(other_id=first.id, kind=kind, because=judgement.because))
            async with self._uow as uow:
                await uow.candidates.save(first)
                await uow.candidates.save(second)
                await uow.commit()
            joined += 1
        return joined, asked


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
    """Same operator, different systems, done one after the other more than once.

    An episode breaks on a host change, so this is the shape no candidate can
    have on its own: "check the WMS, then record it in the ERP" is two
    candidates and always will be.
    """
    pairs = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1 :]:
            if first.principal_id != second.principal_id or first.host == second.host:
                continue
            if _followed(first, second) + _followed(second, first) >= TOGETHER_TIMES:
                pairs.append((JoinKind.WORKFLOW, first, second))
    return pairs


def _followed(first: TaskCandidate, second: TaskCandidate) -> int:
    """How often an episode of `second` began just as one of `first` ended."""
    return sum(
        1
        for earlier in first.episodes
        for later in second.episodes
        if timedelta(0) <= later.started_at - earlier.ended_at <= TOGETHER_WITHIN
    )


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
