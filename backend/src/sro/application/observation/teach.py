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
from sro.application.observation.shots import ShotRef, pictures
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
"""How many doings of a task one teach reads.

Well above the two that are diffed and the handful `worth_offering` asks for,
and far below the number a daily task accumulates. Every doing past this is
read for one thing -- whether a field was left empty -- and the tenth is
unlikely to be the first to say so.
"""


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
            # Checked before gathering evidence and running induction, not
            # only at the domain object's own guard at the end of this: a
            # stale tab's retried teach, or a second operator's click after
            # the first's, should not cost a full induction pass just to be
            # refused by it.
            raise NothingToTeach(f"this candidate is already {candidate.status}")

        # Freshest first: the screens move, and the most recent doings of a
        # task are the ones most likely to still find their controls. That is
        # the rule for the two that get *diffed*, and all of them are built:
        # whether a field may be left out is a fact about the whole history of
        # a task rather than about the last two times somebody did it, and the
        # doing that proves the warehouse takes Absolute Priority empty may be
        # the first of three.
        # Bounded, and the bound is said out loud. A task somebody does every
        # morning has fifty sightings by the end of the month, and reading them
        # all is fifty blob passes and fifty stored recordings for one teach --
        # to answer a question the freshest handful has already answered.
        #
        # Dropped from the far end, so the two that get diffed are never among
        # the losses. What a dropped doing could still have said is that some
        # field may be left out, and not hearing it leaves that field required:
        # a skill that asks for one value too many, which is the direction to
        # be wrong in.
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
            # The recordings are kept: they are evidence either way, and the
            # deliberate repetition this asks for will be diffed against them.
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
        """Close the loop on an offer, where there was one.

        Only where the offer was actually made: a candidate taught from the
        console was never asked about, and answering a question nobody put
        would start a conversation to say something into it.

        After the candidate is saved, never with it. If the message fails the
        skill is still taught and the offer merely looks unanswered; the other
        order would record an answer to something that did not happen.
        """
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
        """A skill from what was watched, by the strongest instrument available.

        The two freshest doings are diffed against each other: what differs
        between them is a parameter, proved, and no model is asked. The older
        doings are handed over too -- for the fields somebody left empty, and
        for the steps they made, which is how a task done four different ways
        comes out as one task rather than as whatever two of them shared. One
        doing has nothing to diff, so its narrative -- what varies, what each
        step was for -- is a model reading the same evidence, and every part of
        it is marked as read rather than proven.

        The difference matters most to exactly the task this exists for. A
        creation seen once yields a skill that would re-create the same record
        by name; seen twice, the name is a parameter somebody can fill in.
        """
        if self._induce is not None and len(recordings) > 1:
            return await self._induce_from_a_pair(ctx, candidate, recordings)
        understood = await self._understand.execute(
            ctx, recording_id=recordings[0].id, name=candidate.title
        )
        return understood.skill_id

    async def _induce_from_a_pair(
        self, ctx: RequestContext, candidate: TaskCandidate, recordings: Sequence[Recording]
    ) -> SkillId:
        """Induce from the first pair that really is two runs of one task.

        The two freshest used to be the only pair tried, and one odd doing
        among them sank the whole candidate. A real case: four doings of
        "create a work area", of which the second freshest was a two-frame stub
        where somebody typed one field. Three of the six pairs aligned
        perfectly; induction picked the one that did not, and the operator was
        asked to demonstrate a task the system had watched four times.

        So a refusal is no longer the end of it. Freshness is still the
        preference -- the screens move, and the most recent doings are the ones
        most likely to still find their controls -- but it stops being a single
        point of failure. Pairs are tried nearest-to-freshest first, and the
        rest of the history goes along as `others` whichever pair wins, so a
        field somebody left empty and a step most doings make are still read
        from every doing.

        Bounded on purpose. Ten doings are forty-five pairs, and a candidate
        that cannot align in a handful of tries is telling us something --
        that these are not doings of one task -- rather than waiting to be
        brute-forced into agreement.

        Where every pair refuses, the freshest pair's refusal is the one
        raised: it is the two runs the operator most likely has in mind, so it
        is the explanation that will make sense to them.
        """
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
                    # The rest of the history. Read for whether some doing left
                    # a field empty, and -- since ADR 015 -- for the steps they
                    # made: a step most doings contain is part of the task even
                    # when the pair happens not to share it, and a rare one
                    # that types a field somebody supplied is a branch rather
                    # than a fumble.
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
        """One doing of the task, read back out of the evidence plane as a
        recording. `None` where that doing cannot be replayed at all -- its
        batches have aged out, or nothing in it changed anything."""
        read = await self._evidence(ctx, episode)
        assembled = assemble_frames(read.events)
        if not assembled.frames:
            return None

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
            return None
        recording.name_objective(objective)
        # The pictures of the very gestures these frames describe. Attached
        # before the seal, because a sealed recording is evidence nobody may
        # add to afterwards.
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
    """One skill from two candidates. Both ids, because both were spent."""

    first_id: CandidateId
    second_id: CandidateId
    recording_ids: tuple[RecordingId, ...] = ()
    skill_id: SkillId | None = None
    needs_demonstration: bool = False
    because: str | None = None


class TeachWorkflow:
    """Two candidates a person has said are one job, taught as one skill.

    Segmentation runs each host on its own stream, so an episode is always one
    host's -- which makes "check the WMS, then record it in the ERP" two
    candidates and always will. What makes it teachable is that
    the operator did both halves together more than once: each of those
    occurrences is one demonstration of the whole job, and two of them are the
    pair induction wants. The two candidates are never diffed against each
    other -- that would compare the WMS half with the ERP half and call the
    difference a parameter.
    """

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
                # Named, because "already taught" with no skill to go and look
                # at reads as a bug, and the person is one click from what they
                # were trying to make.
                raise NothingToTeach(f"{candidate.title} is already a skill ({candidate.skill_id})")
            if candidate.status is not CandidateStatus.NEW:
                raise NothingToTeach(f"this candidate is already {candidate.status}")

        if _said_different(first, second) or _said_different(second, first):
            raise NothingToTeach("somebody has already said these two are different work")

        # Every doing, both ways round -- not the larger direction. The miner
        # counts both ways before it decides the pair is worth suggesting, and
        # an operator flipping between two tabs will not flip the same way
        # twice: taking the larger of one each way induces from a single
        # recording while two doings sit in the evidence.
        #
        # Sorted back into order after the concatenation, so `reversed` below
        # is still freshest first. `spent` is what stops a pair that somehow
        # qualified in both directions from becoming two recordings of one
        # doing.
        #
        # Where the two halves each write, the two directions name different
        # objectives and induction refuses them by name. That is the honest
        # answer: it is what the operator did, and it is better than diffing
        # one recording against itself.
        pairs = sorted(
            occurrences(first, second) + occurrences(second, first),
            key=lambda pair: pair[0].started_at,
        )

        # Freshest first: the screens move, and the most recent doing is the one
        # most likely to still find its controls.
        #
        # No episode twice. One doing of the WMS half followed by two doings of
        # the ERP half is two adjacent pairs and one occurrence: handing both to
        # induction would diff a recording against itself on one side, so every
        # value the operator typed in the WMS half would be proved constant by
        # evidence that is literally the same bytes.
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
                # Every doing of the two halves together, not the freshest
                # two: the steps of a chained task are decided by the same
                # counts as any other, and stopping at two is the intersection
                # ADR 015 exists to stop taking.
                others=tuple(recording.id for recording in recordings[2:]),
            )
        except InductionFailed as thin:
            # Kept, as a single teach keeps its recording: two halves that will
            # not induce are still the evidence a deliberate demonstration gets
            # diffed against.
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
        """One occurrence of the whole job, as one recording.

        Each episode read on its own, so nothing between two halves that
        followed one another is ever read: that gap is where the operator
        answered an email.

        It is not one window across both, but it is not two watertight halves
        either, and this is the known trade rather than a surprise. The events
        are concatenated and `assemble_frames` folds them by time alone, so
        where the two halves *overlap* -- an operator flipping tabs, which is
        the shape this whole path exists for -- the other tab's traffic
        attaches to whichever frame is open. A mail poll lands on the warehouse
        click.

        Bounded: `diff.align` and `binding` both filter on `is_mutation`, so
        the pair still aligns and still induces the right steps. Not free:
        `understand`, `capabilities`, `_collections_read` and
        `_response_leaves` all read a frame's requests as they are, so a mail
        response's JSON can be offered as a binding source for a warehouse
        step. `is_background_traffic` does not catch it either -- a mail poll
        matches none of its markers, which is the failure its own docstring
        names.

        Deliberately left: fixing it means folding per host, and the frame
        boundaries that produces are a bigger question than the one this
        branch answers.
        """
        read = await self._evidence(ctx, earlier)
        late = await self._evidence(ctx, later)
        # Snapshotted before the two are joined, because `extend` folds the
        # second half into the first and the naming half may be either of them.
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

        # Named from one half, and always the same half.
        #
        # No `system=`, because the candidate's host would name whichever half
        # the operator opened. But the frames of the whole recording will not do
        # either: `derive_objective_key` takes the LAST write, and
        # `assemble_frames` folds by time, so the half the operator happened to
        # finish with names the job. Somebody who closes waves and then records
        # the receipt gets `close`; the week they had the ERP open already and
        # did it the other way round gets `create` -- two names for one job, and
        # `_check_pairable` then refuses its own pair by name.
        #
        # An operator flipping between two tabs does not flip the same way
        # twice, and interleaving made that ordinary rather than odd.
        #
        # So the naming half is chosen by host, which is the one thing about
        # these two that neither the operator nor the caller can vary: not the
        # order they were done in, and not the order somebody named them when
        # asking for the merge. Alphabetical is arbitrary and says so -- what
        # matters is that a job spanning two systems is named by one of them by
        # a rule that cannot depend on how anybody did it or asked for it.
        #
        # Falls back to the whole recording where that half asked the server
        # nothing: a half that made no call cannot name anything, and a doing
        # that names nothing is dropped a line below rather than kept unnamed.
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
        """What to call the merged skill.

        The model's, because neither half's title describes the job: "Update
        adjust on wms" and "Create receipts on erp" are two sentences about one
        piece of work. Nothing about identity rests on it -- the objective key
        is already decided by then.
        """
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
"""How many pairs to try before believing the refusal.

Six is every pair among the four freshest doings. Ten doings are forty-five
pairs, and a candidate that cannot find two runs of one task in six tries is
saying these are not doings of one task -- which is a real answer, and the one
`needs_demonstration` exists to give.
"""


def _pairs(count: int) -> Iterator[tuple[int, int]]:
    """Every pair of doings, freshest first, nearest first.

    `recordings` is ordered freshest-first, so (0,1) is the pair that used to be
    the only one tried and stays the first. After that, `near + far` ascending
    prefers pairs that are both recent and adjacent: two doings from this
    morning are likelier to be two runs of one task than this morning and last
    Tuesday, because the screens move.
    """
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
    """Kept rather than deleted, so the miner does not offer it again next week
    as if it were new."""

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

        # Said only where it was asked, and only where there is a clock and ids
        # to say it with -- a deployment without them dismisses exactly as it
        # did before rather than failing over a sentence.
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
    """One episode, read back out of the evidence plane.

    Addressed by time rather than by offsets: an episode spans several uploads
    and part of each, and the timestamps already say which part.
    """

    events: list[CaptureEvent]
    shots: dict[int, ShotRef]
    """Where each gesture's picture would be, keyed by ``id()`` of the event
    it belongs to. Identity, because `assemble_frames` hands back the very
    objects it was given and two gestures can share a timestamp."""

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
    """This episode's slice of one batch, each gesture carrying where its
    picture would be.

    The ordinal counts every gesture line in the batch, including the ones
    this episode does not want and the ones `_capture` cannot read -- because
    that is what the recorder counted when it numbered the pictures
    (`upload.js`, ``framesOf``). Counting only the surviving gestures would
    slide every later picture onto the wrong one.
    """
    kept: list[tuple[CaptureEvent, ShotRef | None]] = []
    ordinal = -1
    for line in payload.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, Mapping):
            continue
        gesture = event.get("kind") == "gesture"
        if gesture:
            ordinal += 1
        capture = _capture(event, episode)
        if capture is not None:
            kept.append((capture, ShotRef(batch_id, ordinal) if gesture else None))
    return kept


def _capture(event: Mapping[str, object], episode: Episode) -> CaptureEvent | None:
    kind = event.get("kind")
    if kind == "gesture":
        gesture = event.get("gesture")
        if not isinstance(gesture, Mapping):
            return None
        at = _at(gesture.get("at"))
        # The same field segmentation bucketed this gesture by (`segment._observed`
        # reads `gesture.url`, not the top-level `page_url` this event also
        # carries for `InputEvent.page_url`) -- using a different one here would
        # let this guard disagree with the partition that already decided which
        # episode this gesture belongs to.
        if at is None or not _inside(at, _host(str(gesture.get("url") or "")), episode):
            return None
        return InputEvent(
            at=at,
            action=to_input_action(dict(gesture)),
            # The tab's URL, not the frame's. A gesture inside a portal that
            # hosts its screens in an iframe reports the frame's src, and a run
            # told to open that would load the frame's document on its own,
            # outside the shell that gives it its session. What has to be
            # reproduced is the address an operator would type.
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
            # An exchange this deployment's domain will not accept. Skipped
            # rather than failing the teach: one malformed call out of forty is
            # not a reason to make somebody do the task again.
            return None

    if kind == "snapshot":
        # Read here as well as on the demonstration path, because this is where
        # a task the operator never deliberately taught becomes a skill -- which
        # is the way this product is meant to work. Passing over the trees here
        # meant a mined skill got the weaker locator ladder however many trees
        # had been captured for it: a css path of framework ids assigned in
        # render order, different on the next page load.
        snapshot = event.get("snapshot")
        taken_at = event.get("taken_at")
        if not isinstance(snapshot, Mapping):
            return None
        at = _at(taken_at)
        # By time alone -- see `_when`'s docstring. A snapshot's `url` is the
        # tab's, not the frame's whose host the episode carries.
        if at is None or not _when(at, episode):
            return None
        try:
            graph = to_ax_graph(dict(snapshot), url=str(event.get("url") or ""), taken_at=at)
        except (KeyError, TypeError, ValueError):
            return None
        return None if graph is None else SnapshotEvent(snapshot=graph)
    return None


def _inside(at: datetime, host: str, episode: Episode) -> bool:
    """Whether this event belongs to this episode.

    Time and host, not time alone. Episodes on two hosts genuinely overlap now
    that `segment` runs each host on its own stream -- an operator flipping
    between a mailbox and the warehouse system produces exactly that -- and a
    window is no longer enough to say which piece of work an event was part of.

    Load-bearing, not a guard against a future: one batch with a mail episode
    over 0-11s and a warehouse episode over 5-6s is the whole case. With the
    host check the mail half holds its two mail calls; revert it to time alone
    and the same half also holds `wms.example/api/suppliers`, and the induced
    skill does the warehouse work twice. Anyone deleting this as dead code
    reintroduces exactly that.

    No fallback for an event with no URL: an empty host is only ever right for
    a `host=""` episode, and segmentation never mines one -- `_segment` drops
    any run with no calls, and a stream of URL-less events has none. Letting
    `""` slide into a real episode would readmit exactly the contamination
    this guard exists to stop.
    """
    return host == episode.host and _when(at, episode)


def _when(at: datetime, episode: Episode) -> bool:
    """Whether this event's time falls in this episode's window.

    Host-blind, on purpose: a snapshot uses this instead of `_inside`.
    Segmentation has no snapshot branch -- an episode's window is drawn from
    its gestures and calls alone -- so a snapshot's host was never part of
    what defined an episode, and applying a host rule to it now would invent a
    constraint the partition never had. A snapshot's own `url` is the tab's,
    read by `service-worker.js`'s `takeTreeSoon`, while the episode's host
    comes from the gesture's frame URL -- the two disagree exactly for the
    cross-host iframe portal `_capture`'s gesture branch already documents,
    and host-checking the snapshot there would silently drop it.
    """
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


def _text(value: object) -> str | None:
    """A string field of the payload, or nothing. The blob is whatever the
    browser uploaded, so a shape nobody expected is an absence rather than a
    crash halfway through assembling a demonstration."""
    return value if isinstance(value, str) and value.strip() else None
