"""A task somebody keeps doing.

Derived, and recomputable: an episode is a slice of a day's observation, and a
candidate is a class of episodes that look like the same piece of work. Both
come out of evidence that is kept verbatim, so a better miner is re-run over
what is already stored rather than needing a new week of watching.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from statistics import median

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, CandidateId, PrincipalId, SkillId, TenantId

WORTH_OFFERING = 3
"""How many times something has to have been done before it is proposed.

Twice is a coincidence and the operator knows it; being asked about
coincidences is how a recommendation surface gets ignored. Kept from two so the
count is already there when the third happens.
"""


class CandidateStatus(StrEnum):
    NEW = "new"
    DISMISSED = "dismissed"
    TAUGHT = "taught"


@dataclass(frozen=True, slots=True)
class Episode:
    """One doing of it. Addressed by time rather than by offsets into an upload,
    because a task takes minutes and an upload covers a minute -- the evidence
    for one episode is several batches, and which part of each is a question the
    timestamps already answer."""

    started_at: datetime
    ended_at: datetime
    host: str
    batch_ids: tuple[BatchId, ...]
    gestures: int = 0
    calls: int = 0

    def __post_init__(self) -> None:
        for name, at in (("started_at", self.started_at), ("ended_at", self.ended_at)):
            if at.tzinfo is None:
                raise InvariantViolation(f"{name} must be timezone-aware")
        if self.ended_at < self.started_at:
            raise InvariantViolation("an episode cannot end before it started")

    @property
    def duration_ms(self) -> int:
        return int((self.ended_at - self.started_at).total_seconds() * 1000)


@dataclass(eq=False)
class TaskCandidate:
    """An episode class, and what it would be worth automating.

    A proposal to a person, never something the system acts on. Nothing here
    starts a run; teaching it produces a recording, which goes through induction
    and the promotion ladder like any demonstration somebody gave on purpose.
    """

    id: CandidateId
    tenant_id: TenantId
    principal_id: PrincipalId
    signature: str
    host: str
    title: str
    status: CandidateStatus = CandidateStatus.NEW
    episodes: tuple[Episode, ...] = ()
    skill_id: SkillId | None = None
    dismissed_reason: str | None = None
    named_by_model: bool = False
    """Whether the title is a model's reading of the evidence. It is the only
    part of a candidate anything generated, and it is marked so nobody mistakes
    a sentence for a fact."""

    def __post_init__(self) -> None:
        if not self.signature.strip():
            raise InvariantViolation("a candidate with no signature cannot be recognised again")
        if not self.title.strip():
            raise InvariantViolation("a candidate nobody can read is a candidate nobody acts on")
        self.episodes = tuple(sorted(self.episodes, key=lambda episode: episode.started_at))

    @property
    def times_seen(self) -> int:
        return len(self.episodes)

    @property
    def first_seen(self) -> datetime | None:
        return self.episodes[0].started_at if self.episodes else None

    @property
    def last_seen(self) -> datetime | None:
        return self.episodes[-1].ended_at if self.episodes else None

    @property
    def median_duration_ms(self) -> int:
        """The middle one, not the mean. One episode where somebody went to
        lunch mid-task would otherwise decide what the task costs."""
        if not self.episodes:
            return 0
        return int(median(episode.duration_ms for episode in self.episodes))

    @property
    def worth_offering(self) -> bool:
        return self.status is CandidateStatus.NEW and self.times_seen >= WORTH_OFFERING

    @property
    def minutes_so_far(self) -> float:
        return sum(episode.duration_ms for episode in self.episodes) / 60_000

    def observed(self, episode: Episode) -> bool:
        """Record another doing of it. Answers whether this was new.

        Mining runs again over evidence it has already read, so the same
        episode arriving twice must not become two occurrences -- a count of how
        often something happened is the whole reason a candidate exists.
        """
        if any(known.started_at == episode.started_at for known in self.episodes):
            return False
        self.episodes = tuple(sorted((*self.episodes, episode), key=lambda one: one.started_at))
        return True

    def rename(self, title: str, *, by_model: bool = False) -> None:
        if not title.strip():
            raise InvariantViolation("a candidate nobody can read is a candidate nobody acts on")
        self.title = title
        self.named_by_model = by_model

    def dismiss(self, reason: str) -> None:
        """Not worth automating, said by a person. Kept rather than deleted, so
        the miner does not offer it again next week."""
        if not reason.strip():
            raise InvariantViolation("a dismissal with no reason will be second-guessed")
        self.status = CandidateStatus.DISMISSED
        self.dismissed_reason = reason

    def taught(self, skill_id: SkillId) -> None:
        self.status = CandidateStatus.TAUGHT
        self.skill_id = skill_id
