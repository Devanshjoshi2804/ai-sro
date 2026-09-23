from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from sro.application.chat.converse import StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.ports.interpretation import WorkflowInterpreter
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.chat.thread import Message, Said, Speaker
from sro.domain.observation.candidate import (
    CandidateStatus,
    Episode,
    Join,
    JoinAnswer,
    JoinKind,
    TaskCandidate,
)
from sro.domain.shared.identifiers import CandidateId, TenantId

logger = logging.getLogger(__name__)

MOST_PAIRS = 20

TOGETHER_WITHIN = timedelta(minutes=5)

TOGETHER_TIMES = 2

ENOUGH_OVERLAP = 0.6

MOST_DOINGS = 8

Readings = dict[tuple[str, str], list[str]]


@dataclass(frozen=True, slots=True)
class Proposed:
    named: int = 0
    joined: int = 0
    offered: int = 0
    asked: int = 0


class ProposeAboutCandidates:
    def __init__(
        self,
        uow: UnitOfWork,
        interpreter: WorkflowInterpreter,
        clock: Clock | None = None,
        ids: IdFactory | None = None,
    ) -> None:
        self._uow = uow
        self._interpreter = interpreter
        self._clock = clock
        self._ids = ids

    async def execute(self, ctx: RequestContext) -> Proposed:
        async with self._uow as uow:
            candidates = await uow.candidates.list_for_tenant(
                ctx.tenant_id, status=CandidateStatus.NEW
            )
            said = await _already_read(uow, ctx.tenant_id)

        worth = [candidate for candidate in candidates if candidate.worth_offering]
        named, asked = await self._name(worth, said) if self._interpreter.available else (0, 0)
        joined, asked_again = await self._join(worth, said)
        offered = await self._offer(ctx, candidates)
        return Proposed(named=named, joined=joined, offered=offered, asked=asked + asked_again)

    async def _name(self, candidates: list[TaskCandidate], said: Readings) -> tuple[int, int]:
        named = asked = 0
        for candidate in candidates:
            if candidate.named_by_model:
                continue
            asked += 1
            answer = await self._interpreter.name_task(_describe(candidate, said))
            title = answer.title.strip()
            if not title:
                continue
            candidate.rename(title, by_model=True)
            async with self._uow as uow:
                await uow.candidates.save(candidate)
                await uow.commit()
            named += 1
        return named, asked

    async def _join(self, candidates: list[TaskCandidate], said: Readings) -> tuple[int, int]:
        pairs = [
            (kind, first, second)
            for kind, first, second in (*_variants(candidates), *_workflows(candidates))
            if not _settled(first, second, kind)
        ][:MOST_PAIRS]

        joined = asked = 0
        for kind, first, second in pairs:
            if self._interpreter.available:
                asked += 1
                judgement = await self._interpreter.judge_join(
                    kind.value, _describe(first, said), _describe(second, said)
                )
                if not judgement.joined or not judgement.because.strip():
                    continue
                because, by_model = judgement.because, True
            else:
                because, by_model = _plainly(kind, first, second), False
            first.suggest(Join(other_id=second.id, kind=kind, because=because, by_model=by_model))
            second.suggest(Join(other_id=first.id, kind=kind, because=because, by_model=by_model))
            async with self._uow as uow:
                await uow.candidates.save(first)
                await uow.candidates.save(second)
                await uow.commit()
            joined += 1
        return joined, asked

    async def _offer(self, ctx: RequestContext, candidates: Sequence[TaskCandidate]) -> int:
        if self._clock is None or self._ids is None:
            return 0
        read, start = ReadThreads(self._uow), StartThread(self._uow, self._clock, self._ids)
        offered = 0
        for candidate in candidates:
            if not candidate.worth_offering or candidate.offered_at is not None:
                continue
            owner = RequestContext(ctx.tenant_id, candidate.principal_id)
            found = await read.current(owner) or await start.execute(owner)
            async with self._uow as uow:
                thread = await uow.threads.get(owner.tenant_id, found.id)
                said_at = self._clock.now()
                thread.say(
                    Message(
                        id=self._ids.new_message_id(),
                        speaker=Speaker.SYSTEM,
                        text=_offered(candidate),
                        said_at=said_at,
                        decision={
                            "kind": Said.OFFER,
                            "candidate_id": candidate.id.value,
                            "times": candidate.times_seen,
                            "seconds_each": _seconds(candidate),
                            "host": candidate.host,
                            "title": candidate.title,
                            "named_by_model": candidate.named_by_model,
                            "signature": candidate.signature,
                        },
                    )
                )
                candidate.offered_at = said_at
                await uow.threads.save(thread)
                await uow.candidates.save(candidate)
                await uow.commit()
            offered += 1
        return offered


class AnswerJoin:
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
    pairs = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1 :]:
            if first.principal_id != second.principal_id or first.host != second.host:
                continue
            if _overlap(first.signature, second.signature) < ENOUGH_OVERLAP:
                continue
            if first.signature == second.signature:
                continue
            pairs.append((JoinKind.VARIANT, first, second))
    return pairs


def _workflows(
    candidates: list[TaskCandidate],
) -> list[tuple[JoinKind, TaskCandidate, TaskCandidate]]:
    pairs = []
    for index, first in enumerate(candidates):
        for second in candidates[index + 1 :]:
            if first.principal_id != second.principal_id or first.host == second.host:
                continue
            if _followed(first, second) + _followed(second, first) >= TOGETHER_TIMES:
                pairs.append((JoinKind.WORKFLOW, first, second))
    return pairs


def _settled(first: TaskCandidate, second: TaskCandidate, kind: JoinKind) -> bool:
    return any(
        (candidate.join_with(other.id, kind) or _UNANSWERED).is_answered
        for candidate, other in ((first, second), (second, first))
    )


_UNANSWERED = Join(other_id=CandidateId("none"), kind=JoinKind.VARIANT, because="not asked")


def occurrences(first: TaskCandidate, second: TaskCandidate) -> list[tuple[Episode, Episode]]:
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
        return False
    return (
        later.touched_from - earlier.touched_until <= TOGETHER_WITHIN
        and earlier.touched_from - later.touched_until <= TOGETHER_WITHIN
    )


def _followed(first: TaskCandidate, second: TaskCandidate) -> int:
    return len(occurrences(first, second))


def _plainly(kind: JoinKind, first: TaskCandidate, second: TaskCandidate) -> str:
    if kind is JoinKind.WORKFLOW:
        forwards, backwards = occurrences(first, second), occurrences(second, first)
        pairs = forwards + backwards
        times = len(pairs)
        order = (first, second) if len(forwards) >= len(backwards) else (second, first)
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
    one, two = set(first.split(" → ")), set(second.split(" → "))
    if not one or not two:
        return 0.0
    return len(one & two) / min(len(one), len(two))


def _describe(candidate: TaskCandidate, said: Readings | None = None) -> str:
    doings = _doings(candidate, said or {})
    return "\n".join(
        (
            f"system: {candidate.host}",
            f"done {candidate.times_seen} times, "
            f"about {candidate.median_duration_ms // 1000}s each",
            f"currently called: {candidate.title}",
            "steps:",
            *(f"  {step}" for step in candidate.signature.split(" → ")),
            *(("what was done, as read at capture:",) if doings else ()),
            *(f"  {doing}" for doing in doings),
        )
    )


def _doings(candidate: TaskCandidate, said: Readings) -> list[str]:
    found: list[str] = []
    for episode in candidate.episodes:
        for batch_id in episode.batch_ids:
            for one in said.get((batch_id.value, candidate.host), ()):
                if one not in found:
                    found.append(one)
    if len(found) <= MOST_DOINGS:
        return found
    step = len(found) / MOST_DOINGS
    return [found[int(index * step)] for index in range(MOST_DOINGS)]


async def _already_read(uow: UnitOfWork, tenant_id: TenantId) -> Readings:
    intents = {intent.gesture_id: intent for intent in await uow.gestures.intents_for(tenant_id)}
    found: Readings = {}
    for gesture in await uow.gestures.gestures_for(tenant_id):
        intent = intents.get(gesture.id)
        if intent is None or not intent.act:
            continue
        host = urlsplit(gesture.system or gesture.url or "").hostname or ""
        reading = intent.act if not intent.object else f"{intent.act} — {intent.object}"
        found.setdefault((gesture.batch_id, host), []).append(reading)
    return found


def _offered(candidate: TaskCandidate) -> str:
    said = _seconds(candidate)
    times = f"{candidate.times_seen} times"
    if candidate.named_by_model and candidate.title:
        return (
            f"{candidate.title} — you've done this {times}, about {said}s each. "
            "Want me to do the next one?"
        )
    what = _noun(candidate)
    if not what:
        return f"You've done this {times} here — about {said}s each."
    return f"You've created {candidate.times_seen} {_plural(what)} here — about {said}s each."


def _seconds(candidate: TaskCandidate) -> int:
    return round(candidate.median_duration_ms / 1000)


def _noun(candidate: TaskCandidate) -> str:
    path = ([*candidate.signature.split(" "), ""])[1]
    word = next((part for part in reversed(path.split("/")) if part and part != "*"), "")
    return re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", word).lower()


def _plural(word: str) -> str:
    return word if word.endswith("s") else f"{word}s"
