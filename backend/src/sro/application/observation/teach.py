from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.capture.assemble import AssemblyResult, assemble_frames
from sro.application.capture.decode import (
    epoch_to_datetime,
    to_ax_graph,
    to_captured_request,
    to_input_action,
)
from sro.application.capture.events import (
    CaptureEvent,
    InputEvent,
    RequestEvent,
    SnapshotEvent,
)
from sro.application.capture.identity import derive_objective_key
from sro.application.chat.announce import SayWhatHappened
from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.induction.induce_skill import InduceSkill
from sro.application.induction.understand import UnderstandRecording
from sro.application.observation.evidence import once_each
from sro.application.observation.propose import occurrences
from sro.application.observation.segment import _host
from sro.application.observation.shots import ShotRef, numbered, pictures
from sro.application.ports.blob import BlobStore
from sro.application.ports.interpretation import WorkflowInterpreter
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import (
    CandidateStatus,
    Episode,
    JoinAnswer,
    JoinKind,
    TaskCandidate,
)
from sro.domain.recording.recording import Recording
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import BatchId, CandidateId, RecordingId, SkillId

logger = logging.getLogger(__name__)

MOST_DOINGS = 10


class NothingToTeach(DomainError):
    code = "nothing_to_teach"


@dataclass(frozen=True, slots=True)
class Taught:
    candidate_id: CandidateId
    recording_id: RecordingId | None
    skill_id: SkillId | None = None
    needs_demonstration: bool = False
    because: str | None = None


class TeachCandidate:
    def __init__(
        self,
        uow: UnitOfWork,
        blobs: BlobStore,
        clock: Clock,
        ids: IdFactory,
        understand: UnderstandRecording,
        induce: InduceSkill | None = None,
    ) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock
        self._ids = ids
        self._understand = understand
        self._induce = induce

    async def execute(self, ctx: RequestContext, *, candidate_id: CandidateId) -> Taught:
        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)

        if candidate.status is not CandidateStatus.NEW:
            raise NothingToTeach(f"this candidate is already {candidate.status}")

        history = list(reversed(candidate.episodes))
        if len(history) > MOST_DOINGS:
            logger.info(
                "teaching %s from the %d most recent of %d doings",
                candidate_id,
                MOST_DOINGS,
                len(history),
            )
            history = history[:MOST_DOINGS]

        recordings: list[Recording] = []
        for episode in history:
            recording = await self._demonstration(ctx, candidate, episode)
            if recording is not None:
                recordings.append(recording)

        if not recordings:
            return Taught(
                candidate_id=candidate_id,
                recording_id=None,
                needs_demonstration=True,
                because="the evidence for this has aged out or was never enough to replay",
            )

        async with self._uow as uow:
            for recording in recordings:
                await uow.recordings.add(recording)
            await uow.commit()

        recording = recordings[0]
        try:
            skill_id = await self._learn(ctx, candidate, recordings)
        except InductionFailed as thin:
            return Taught(
                candidate_id=candidate_id,
                recording_id=recording.id,
                needs_demonstration=True,
                because=str(thin),
            )

        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
            candidate.taught(skill_id)
            await uow.candidates.save(candidate)
            await uow.commit()

        await self._say_yes_was_answered(ctx, candidate)
        return Taught(candidate_id=candidate_id, recording_id=recording.id, skill_id=skill_id)

    async def _say_yes_was_answered(self, ctx: RequestContext, candidate: TaskCandidate) -> None:
        if candidate.offered_at is None:
            return
        await SayWhatHappened(self._uow, self._clock, self._ids).execute(
            ctx,
            for_operator=candidate.principal_id,
            text=f"{candidate.title} — you asked for this one, so I learned it.",
            decision={
                "kind": "answered",
                "candidate_id": candidate.id.value,
                "answer": "asked",
            },
        )

    async def _learn(
        self, ctx: RequestContext, candidate: TaskCandidate, recordings: Sequence[Recording]
    ) -> SkillId:
        if self._induce is not None and len(recordings) > 1:
            return await self._induce_from_a_pair(ctx, candidate, recordings)
        understood = await self._understand.execute(
            ctx, recording_id=recordings[0].id, name=candidate.title
        )
        return understood.skill_id

    async def _induce_from_a_pair(
        self, ctx: RequestContext, candidate: TaskCandidate, recordings: Sequence[Recording]
    ) -> SkillId:
        first_refusal: InductionFailed | None = None
        for attempt, (near, far) in enumerate(_pairs(len(recordings))):
            if attempt >= MOST_PAIRS:
                break
            try:
                induced = await self._induce.execute(  # type: ignore[union-attr]
                    ctx,
                    first=recordings[near].id,
                    second=recordings[far].id,
                    name=candidate.title,
                    others=tuple(
                        recording.id
                        for index, recording in enumerate(recordings)
                        if index not in (near, far)
                    ),
                )
            except InductionFailed as refused:
                if first_refusal is None:
                    first_refusal = refused
                logger.info(
                    "%s: doings %d and %d are not two runs of one task (%s)",
                    candidate.id,
                    near,
                    far,
                    refused,
                )
                continue
            return induced.skill_id
        raise first_refusal if first_refusal else InductionFailed("no pair of doings to diff")

    async def _demonstration(
        self, ctx: RequestContext, candidate: TaskCandidate, episode: Episode
    ) -> Recording | None:
        read = await self._evidence(ctx, episode)
        assembled = assemble_frames(read.events)
        if not assembled.frames:
            return None

        recording = Recording(
            id=self._ids.new_recording_id(),
            tenant_id=ctx.tenant_id,
            demonstrator=candidate.principal_id,
            started_at=episode.started_at,
            label=candidate.title,
        )
        for frame in assembled.frames:
            recording.append_frame(frame)

        objective = derive_objective_key(recording.frames, system=candidate.host)
        if objective is None:
            return None
        recording.name_objective(objective)
        for artifact in await pictures(
            self._blobs,
            batches=read.batches,
            sources=assembled.sources,
            refs=read.shots,
            now=self._clock.now(),
        ):
            recording.attach_artifact(artifact)
        recording.seal(self._clock.now())
        return recording

    async def _evidence(self, ctx: RequestContext, episode: Episode) -> _Evidence:
        return await _read_episode(self._uow, self._blobs, ctx, episode)


@dataclass(frozen=True, slots=True)
class TaughtTogether:
    first_id: CandidateId
    second_id: CandidateId
    recording_ids: tuple[RecordingId, ...] = ()
    skill_id: SkillId | None = None
    needs_demonstration: bool = False
    because: str | None = None


class TeachWorkflow:
    def __init__(
        self,
        uow: UnitOfWork,
        blobs: BlobStore,
        clock: Clock,
        ids: IdFactory,
        induce: InduceSkill,
        interpreter: WorkflowInterpreter | None = None,
    ) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock
        self._ids = ids
        self._induce = induce
        self._interpreter = interpreter

    async def execute(
        self, ctx: RequestContext, *, first_id: CandidateId, second_id: CandidateId
    ) -> TaughtTogether:
        async with self._uow as uow:
            first = await uow.candidates.get(ctx.tenant_id, first_id)
            second = await uow.candidates.get(ctx.tenant_id, second_id)

        for candidate in (first, second):
            if candidate.status is CandidateStatus.TAUGHT:
                raise NothingToTeach(f"{candidate.title} is already a skill ({candidate.skill_id})")
            if candidate.status is not CandidateStatus.NEW:
                raise NothingToTeach(f"this candidate is already {candidate.status}")

        if _said_different(first, second) or _said_different(second, first):
            raise NothingToTeach("somebody has already said these two are different work")

        pairs = sorted(
            occurrences(first, second) + occurrences(second, first),
            key=lambda pair: pair[0].started_at,
        )

        recordings: list[Recording] = []
        spent: set[Episode] = set()
        for earlier, later in reversed(pairs):
            if earlier in spent or later in spent:
                continue
            spent.update((earlier, later))
            recording = await self._demonstration(ctx, first, second, earlier, later)
            if recording is not None:
                recordings.append(recording)
            if len(recordings) == MOST_DOINGS:
                break

        if not recordings:
            return TaughtTogether(
                first_id=first_id,
                second_id=second_id,
                needs_demonstration=True,
                because="the evidence for the two halves together has aged out "
                "or was never enough to replay",
            )

        async with self._uow as uow:
            for recording in recordings:
                await uow.recordings.add(recording)
            await uow.commit()

        name = await self._name(first, second)
        try:
            induced = await self._induce.execute(
                ctx,
                first=recordings[0].id,
                second=recordings[1].id if len(recordings) > 1 else None,
                name=name,
                others=tuple(recording.id for recording in recordings[2:]),
            )
        except InductionFailed as thin:
            return TaughtTogether(
                first_id=first_id,
                second_id=second_id,
                recording_ids=tuple(recording.id for recording in recordings),
                needs_demonstration=True,
                because=str(thin),
            )

        async with self._uow as uow:
            for candidate_id in (first_id, second_id):
                candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
                candidate.taught(induced.skill_id)
                await uow.candidates.save(candidate)
            await uow.commit()

        return TaughtTogether(
            first_id=first_id,
            second_id=second_id,
            recording_ids=tuple(recording.id for recording in recordings),
            skill_id=induced.skill_id,
        )

    async def _demonstration(
        self,
        ctx: RequestContext,
        first: TaskCandidate,
        second: TaskCandidate,
        earlier: Episode,
        later: Episode,
    ) -> Recording | None:
        read = await self._evidence(ctx, earlier)
        late = await self._evidence(ctx, later)
        naming = list((read if earlier.host <= later.host else late).events)
        read.extend(late)
        assembled = assemble_frames(read.events)
        if not assembled.frames:
            return None

        recording = Recording(
            id=self._ids.new_recording_id(),
            tenant_id=ctx.tenant_id,
            demonstrator=first.principal_id,
            started_at=earlier.started_at,
            label=f"{first.title} and then {second.title}",
        )
        for frame in assembled.frames:
            recording.append_frame(frame)

        objective = derive_objective_key(assemble_frames(naming).frames) or derive_objective_key(
            recording.frames
        )
        if objective is None:
            return None
        recording.name_objective(objective)
        await self._illustrate(recording, read, assembled)
        recording.seal(self._clock.now())
        return recording

    async def _illustrate(
        self, recording: Recording, read: _Evidence, assembled: AssemblyResult
    ) -> None:
        for artifact in await pictures(
            self._blobs,
            batches=read.batches,
            sources=assembled.sources,
            refs=read.shots,
            now=self._clock.now(),
        ):
            recording.attach_artifact(artifact)

    async def _name(self, first: TaskCandidate, second: TaskCandidate) -> str:
        plain = f"{first.title} and then {second.title}"
        if self._interpreter is None or not self._interpreter.available:
            return plain
        answer = await self._interpreter.name_task(
            f"one job done across two systems, in this order:\n"
            f"first, on {first.host}: {first.title}\n"
            f"  steps: {first.signature}\n"
            f"then, on {second.host}: {second.title}\n"
            f"  steps: {second.signature}"
        )
        return answer.title.strip() or plain

    async def _evidence(self, ctx: RequestContext, episode: Episode) -> _Evidence:
        return await _read_episode(self._uow, self._blobs, ctx, episode)


MOST_PAIRS = 6


def _pairs(count: int) -> Iterator[tuple[int, int]]:
    return iter(
        sorted(
            ((near, far) for near in range(count) for far in range(near + 1, count)),
            key=lambda pair: (pair[0] + pair[1], pair[0]),
        )
    )


def _said_different(candidate: TaskCandidate, other: TaskCandidate) -> bool:
    join = candidate.join_with(other.id, JoinKind.WORKFLOW)
    return join is not None and join.answered is JoinAnswer.DIFFERENT


class DismissCandidate:
    def __init__(
        self, uow: UnitOfWork, clock: Clock | None = None, ids: IdFactory | None = None
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._ids = ids

    async def execute(
        self, ctx: RequestContext, *, candidate_id: CandidateId, reason: str
    ) -> TaskCandidate:
        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
            candidate.dismiss(reason)
            await uow.candidates.save(candidate)
            await uow.commit()

        if candidate.offered_at is not None and self._clock and self._ids:
            await SayWhatHappened(self._uow, self._clock, self._ids).execute(
                ctx,
                for_operator=candidate.principal_id,
                text=f"{candidate.title} — you said no to this one.",
                decision={
                    "kind": "answered",
                    "candidate_id": candidate.id.value,
                    "answer": "dismissed",
                },
            )
        return candidate


class ReadCandidates:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        seen_at_least: int = 0,
        mine_only: bool = False,
        host: str | None = None,
    ) -> tuple[TaskCandidate, ...]:
        async with self._uow as uow:
            return await uow.candidates.list_for_tenant(
                ctx.tenant_id,
                seen_at_least=seen_at_least,
                principal_id=ctx.principal_id if mine_only else None,
                host=host,
            )

    async def one(self, ctx: RequestContext, *, candidate_id: CandidateId) -> TaskCandidate:
        async with self._uow as uow:
            return await uow.candidates.get(ctx.tenant_id, candidate_id)


@dataclass(frozen=True, slots=True)
class _Evidence:
    events: list[CaptureEvent]
    shots: dict[int, ShotRef]

    batches: list[ObservationBatch]

    def extend(self, other: _Evidence) -> None:
        self.events.extend(other.events)
        self.shots.update(other.shots)
        self.batches.extend(other.batches)


async def _read_episode(
    uow: UnitOfWork, blobs: BlobStore, ctx: RequestContext, episode: Episode
) -> _Evidence:
    read = _Evidence(events=[], shots={}, batches=[])
    async with uow as work:
        for batch_id in episode.batch_ids:
            batch = await work.observations.get(ctx.tenant_id, batch_id)
            if batch is None:
                continue
            try:
                payload = once_each(await blobs.read(batch.uri))
            except (KeyError, OSError):
                continue
            read.batches.append(batch)
            for event, ref in _within(payload, episode, batch_id):
                read.events.append(event)
                if ref is not None:
                    read.shots[id(event)] = ref
    return read


def _within(
    payload: bytes, episode: Episode, batch_id: BatchId
) -> list[tuple[CaptureEvent, ShotRef | None]]:
    kept: list[tuple[CaptureEvent, ShotRef | None]] = []
    for ordinal, event in numbered(payload):
        capture = _capture(event, episode)
        if capture is not None:
            kept.append((capture, None if ordinal is None else ShotRef(batch_id, ordinal)))
    return kept


def _capture(event: Mapping[str, object], episode: Episode) -> CaptureEvent | None:
    kind = event.get("kind")
    if kind == "gesture":
        gesture = event.get("gesture")
        if not isinstance(gesture, Mapping):
            return None
        at = _at(gesture.get("at"))
        if at is None or not _inside(at, _host(str(gesture.get("url") or "")), episode):
            return None
        return InputEvent(
            at=at,
            action=to_input_action(dict(gesture)),
            page_url=_text(event.get("page_url")),
        )

    if kind == "request":
        request = event.get("request")
        if not isinstance(request, Mapping):
            return None
        at = _at(request.get("started_at"))
        if at is None or not _inside(at, _host(str(request.get("url") or "")), episode):
            return None
        try:
            return RequestEvent(request=to_captured_request(dict(request)))
        except ValueError:
            return None

    if kind == "snapshot":
        snapshot = event.get("snapshot")
        taken_at = event.get("taken_at")
        if not isinstance(snapshot, Mapping):
            return None
        at = _at(taken_at)
        if at is None or not _when(at, episode):
            return None
        try:
            graph = to_ax_graph(dict(snapshot), url=str(event.get("url") or ""), taken_at=at)
        except (KeyError, TypeError, ValueError):
            return None
        return None if graph is None else SnapshotEvent(snapshot=graph)
    return None


def _inside(at: datetime, host: str, episode: Episode) -> bool:
    return host == episode.host and _when(at, episode)


def _when(at: datetime, episode: Episode) -> bool:
    return episode.started_at <= at <= episode.ended_at


def _at(raw: object) -> datetime | None:
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return epoch_to_datetime(float(raw))
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else None
    return None


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
