"""Turning "you keep doing this" into a demonstration.

The evidence for an episode is already stored, verbatim, so teaching a candidate
does not ask the operator to do the task again -- it reads back what they did the
last time and hands it to the same induction a deliberate demonstration goes
through. Everything after this line is code that already existed.

Sometimes it is not enough. Passive capture sees no accessibility tree and only
the response bodies the page itself could see, so a task whose evidence will not
induce comes back asking for one deliberate repetition rather than producing a
skill nobody can trust.
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from sro.application.capture.assemble import assemble_frames
from sro.application.capture.decode import (
    epoch_to_datetime,
    to_captured_request,
    to_input_action,
)
from sro.application.capture.events import CaptureEvent, InputEvent, RequestEvent
from sro.application.capture.identity import derive_objective_key
from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.induction.understand import UnderstandRecording
from sro.application.ports.blob import BlobStore
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.observation.candidate import CandidateStatus, Episode, TaskCandidate
from sro.domain.recording.recording import Recording
from sro.domain.shared.errors import DomainError
from sro.domain.shared.identifiers import CandidateId, RecordingId, SkillId


class NothingToTeach(DomainError):
    """The evidence for this candidate is gone or was never enough -- or the
    decision about it was already made, by this same request racing itself
    or by whoever clicked before this click landed."""

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
    ) -> None:
        self._uow = uow
        self._blobs = blobs
        self._clock = clock
        self._ids = ids
        self._understand = understand

    async def execute(self, ctx: RequestContext, *, candidate_id: CandidateId) -> Taught:
        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)

        if candidate.status is not CandidateStatus.NEW:
            # Checked before gathering evidence and running induction, not
            # only at the domain object's own guard at the end of this: a
            # stale tab's retried teach, or a second operator's click after
            # the first's, should not cost a full induction pass just to be
            # refused by it.
            raise NothingToTeach(f"this candidate is already {candidate.status}")

        episode = _best(candidate)
        if episode is None:
            raise NothingToTeach("this candidate has no episode to learn from")

        events = await self._evidence(ctx, episode)
        assembled = assemble_frames(list(events))
        if not assembled.frames:
            return Taught(
                candidate_id=candidate_id,
                recording_id=None,
                needs_demonstration=True,
                because="the evidence for this has aged out or was never enough to replay",
            )

        recording = Recording(
            id=self._ids.new_recording_id(),
            tenant_id=ctx.tenant_id,
            # Whose work it was, not who pressed the button. A skill's
            # provenance should name the person who actually did the task.
            demonstrator=candidate.principal_id,
            started_at=episode.started_at,
            label=candidate.title,
        )
        for frame in assembled.frames:
            recording.append_frame(frame)

        objective = derive_objective_key(recording.frames, system=candidate.host)
        if objective is None:
            return Taught(
                candidate_id=candidate_id,
                recording_id=None,
                needs_demonstration=True,
                because="nothing in this looks like a task that changed something",
            )
        recording.name_objective(objective)
        recording.seal(self._clock.now())

        async with self._uow as uow:
            await uow.recordings.add(recording)
            await uow.commit()

        try:
            understood = await self._understand.execute(
                ctx, recording_id=recording.id, name=candidate.title
            )
        except InductionFailed as thin:
            # The recording is kept: it is evidence either way, and the
            # deliberate repetition this asks for will be diffed against it.
            return Taught(
                candidate_id=candidate_id,
                recording_id=recording.id,
                needs_demonstration=True,
                because=str(thin),
            )

        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
            candidate.taught(understood.skill_id)
            await uow.candidates.save(candidate)
            await uow.commit()

        return Taught(
            candidate_id=candidate_id,
            recording_id=recording.id,
            skill_id=understood.skill_id,
        )

    async def _evidence(self, ctx: RequestContext, episode: Episode) -> Iterator[CaptureEvent]:
        """The events of one episode, read back out of the evidence plane.

        Addressed by time rather than by offsets: an episode spans several
        uploads and part of each, and the timestamps already say which part.
        """
        events: list[CaptureEvent] = []
        async with self._uow as uow:
            for batch_id in episode.batch_ids:
                batch = await uow.observations.get(ctx.tenant_id, batch_id)
                if batch is None:
                    continue
                try:
                    payload = await self._blobs.read(batch.uri)
                except (KeyError, OSError):
                    continue
                events.extend(_within(payload, episode))
        return iter(events)


class DismissCandidate:
    """Kept rather than deleted, so the miner does not offer it again next week
    as if it were new."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, ctx: RequestContext, *, candidate_id: CandidateId, reason: str
    ) -> TaskCandidate:
        async with self._uow as uow:
            candidate = await uow.candidates.get(ctx.tenant_id, candidate_id)
            candidate.dismiss(reason)
            await uow.candidates.save(candidate)
            await uow.commit()
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


def _best(candidate: TaskCandidate) -> Episode | None:
    """The most recent one. The screens move, and the freshest doing of a task
    is the one most likely to still find its controls."""
    return candidate.episodes[-1] if candidate.episodes else None


def _within(payload: bytes, episode: Episode) -> Sequence[CaptureEvent]:
    kept: list[CaptureEvent] = []
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, Mapping):
            continue
        capture = _capture(event, episode)
        if capture is not None:
            kept.append(capture)
    return kept


def _capture(event: Mapping[str, object], episode: Episode) -> CaptureEvent | None:
    kind = event.get("kind")
    if kind == "gesture":
        gesture = event.get("gesture")
        if not isinstance(gesture, Mapping):
            return None
        at = _at(gesture.get("at"))
        if at is None or not _inside(at, episode):
            return None
        return InputEvent(at=at, action=to_input_action(dict(gesture)))

    if kind == "request":
        request = event.get("request")
        if not isinstance(request, Mapping):
            return None
        at = _at(request.get("started_at"))
        if at is None or not _inside(at, episode):
            return None
        try:
            return RequestEvent(request=to_captured_request(dict(request)))
        except ValueError:
            # An exchange this deployment's domain will not accept. Skipped
            # rather than failing the teach: one malformed call out of forty is
            # not a reason to make somebody do the task again.
            return None
    return None


def _inside(at: datetime, episode: Episode) -> bool:
    return episode.started_at <= at <= episode.ended_at


def _at(raw: object) -> datetime | None:
    """The recorder's float seconds, or the ISO string everything else uses.
    Same two rules segmentation applies, because it read the same lines --
    including that an offset-less string is malformed, not naive: comparing
    it against `episode.started_at` in `_inside()` below would raise rather
    than answer, and this candidate's evidence would 500 instead of asking
    for one more demonstration the way thin evidence otherwise always does.
    """
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return epoch_to_datetime(float(raw))
    if isinstance(raw, str):
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else None
    return None
