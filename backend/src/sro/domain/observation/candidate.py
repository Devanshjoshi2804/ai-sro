from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from statistics import median

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import BatchId, CandidateId, PrincipalId, SkillId, TenantId

K_GESTURES_IN_A_DOING = 2

WORTH_OFFERING = 3


class CandidateStatus(StrEnum):
    NEW = "new"
    DISMISSED = "dismissed"
    TAUGHT = "taught"


@dataclass(frozen=True, slots=True)
class Episode:
    started_at: datetime
    ended_at: datetime
    host: str
    batch_ids: tuple[BatchId, ...]
    gestures: int = 0
    calls: int = 0
    touched_from: datetime | None = None
    touched_until: datetime | None = None

    starts_on: str = ""

    def __post_init__(self) -> None:
        for name, at in (("started_at", self.started_at), ("ended_at", self.ended_at)):
            if at.tzinfo is None:
                raise InvariantViolation(f"{name} must be timezone-aware")
        if self.ended_at < self.started_at:
            raise InvariantViolation("an episode cannot end before it started")

    @property
    def duration_ms(self) -> int:
        return int((self.ended_at - self.started_at).total_seconds() * 1000)


class JoinKind(StrEnum):
    VARIANT = "variant"

    WORKFLOW = "workflow"


class JoinAnswer(StrEnum):
    SAME = "same"

    DIFFERENT = "different"


@dataclass(frozen=True, slots=True)
class Join:
    other_id: CandidateId
    kind: JoinKind
    because: str
    by_model: bool = True

    answered: JoinAnswer | None = None
    answered_by: PrincipalId | None = None

    def __post_init__(self) -> None:
        if not self.because.strip():
            raise InvariantViolation("a join nobody can explain will not be believed")
        if (self.answered is None) != (self.answered_by is None):
            raise InvariantViolation("an answered join names who answered it")

    @property
    def is_answered(self) -> bool:
        return self.answered is not None


@dataclass(eq=False)
class TaskCandidate:
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
    joins: tuple[Join, ...] = ()

    named_by_model: bool = False

    starts_on: str = ""

    offered_at: datetime | None = None

    learned_from: int = 0

    learned_under: int = 0

    def __post_init__(self) -> None:
        if not self.signature.strip():
            raise InvariantViolation("a candidate with no signature cannot be recognised again")
        if not self.title.strip():
            raise InvariantViolation("a candidate nobody can read is a candidate nobody acts on")
        self.episodes = tuple(sorted(self.episodes, key=lambda episode: episode.started_at))

    @property
    def times_seen(self) -> int:
        return len(self.episodes)

    def worth_learning_again(self, induction_version: int) -> bool:
        return self.times_seen > self.learned_from or induction_version > self.learned_under

    def learning_tried(self, induction_version: int) -> None:
        self.learned_from = self.times_seen
        self.learned_under = induction_version

    @property
    def first_seen(self) -> datetime | None:
        return self.episodes[0].started_at if self.episodes else None

    @property
    def last_seen(self) -> datetime | None:
        return self.episodes[-1].ended_at if self.episodes else None

    @property
    def median_duration_ms(self) -> int:
        if not self.episodes:
            return 0
        return int(median(episode.duration_ms for episode in self.episodes))

    @property
    def status_is_new(self) -> bool:
        return self.status is CandidateStatus.NEW

    @property
    def worth_offering(self) -> bool:
        return (
            self.status is CandidateStatus.NEW
            and self.times_seen >= WORTH_OFFERING
            and self.typical_doing >= K_GESTURES_IN_A_DOING
        )

    @property
    def typical_doing(self) -> float:
        return median(episode.gestures for episode in self.episodes) if self.episodes else 0

    @property
    def minutes_so_far(self) -> float:
        return sum(episode.duration_ms for episode in self.episodes) / 60_000

    def observed(self, episode: Episode) -> bool:
        if any(known.started_at == episode.started_at for known in self.episodes):
            return False
        self.episodes = tuple(sorted((*self.episodes, episode), key=lambda one: one.started_at))
        return True

    def rename(self, title: str, *, by_model: bool = False) -> None:
        if not title.strip():
            raise InvariantViolation("a candidate nobody can read is a candidate nobody acts on")
        self.title = title
        self.named_by_model = by_model

    def suggest(self, join: Join) -> bool:
        if join.other_id == self.id:
            raise InvariantViolation("a candidate cannot be a variant of itself")
        already = self.join_with(join.other_id, join.kind)
        if already is not None and already.is_answered:
            return False
        if already == join:
            return False
        self.joins = (*(known for known in self.joins if known is not already), join)
        return True

    def join_with(self, other_id: CandidateId, kind: JoinKind) -> Join | None:
        return next(
            (known for known in self.joins if known.other_id == other_id and known.kind is kind),
            None,
        )

    def answer(
        self, other_id: CandidateId, kind: JoinKind, answer: JoinAnswer, by: PrincipalId
    ) -> Join:
        known = self.join_with(other_id, kind)
        if known is None:
            raise InvariantViolation("nothing suggested these two were one thing")
        answered = replace(known, answered=answer, answered_by=by)
        self.joins = tuple(answered if one is known else one for one in self.joins)
        return answered

    def dismiss(self, reason: str) -> None:
        self._require_new("dismissed")
        if not reason.strip():
            raise InvariantViolation("a dismissal with no reason will be second-guessed")
        self.status = CandidateStatus.DISMISSED
        self.dismissed_reason = reason

    def taught(self, skill_id: SkillId) -> None:
        self._require_new("taught")
        self.status = CandidateStatus.TAUGHT
        self.skill_id = skill_id

    def _require_new(self, verb: str) -> None:
        if self.status is not CandidateStatus.NEW:
            raise InvariantViolation(f"a {self.status} candidate cannot be {verb}")
