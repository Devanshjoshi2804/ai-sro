"""A task somebody keeps doing.

Derived, and recomputable: an episode is a slice of a day's observation, and a
candidate is a class of episodes that look like the same piece of work. Both
come out of evidence that is kept verbatim, so a better miner is re-run over
what is already stored rather than needing a new week of watching.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
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


class JoinKind(StrEnum):
    VARIANT = "variant"
    """The same piece of work done two ways -- an extra page, a different
    order. Two candidates because the signature is compared for equality, which
    is the property that keeps identity stable."""

    WORKFLOW = "workflow"
    """Two halves of one piece of work, in two systems. An episode breaks on a
    host change, so this is a shape no single candidate can ever have."""


class JoinAnswer(StrEnum):
    SAME = "same"
    """A person looked and said yes. For a variant that means one of the two is
    a duplicate; for a workflow it means the pair is one job done in two
    systems, which no single candidate can represent."""

    DIFFERENT = "different"
    """A person looked and said no. Kept rather than deleted, for the same
    reason a dismissed candidate is kept: a question somebody has already
    answered must not be asked again next week as though it were new."""


@dataclass(frozen=True, slots=True)
class Join:
    """A suggestion that this candidate and another are one thing, and what a
    person said about it.

    Until somebody answers, it is a suggestion and nothing acts on it -- a
    suggestion the system acted on would be a task identity a model decided
    after all. The answer is what turns it into a fact, and it names who said
    so, because "these two are the same task" is a claim about somebody's work.
    """

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
    joins: tuple[Join, ...] = ()
    """What this candidate might be part of. See `Join`."""

    named_by_model: bool = False
    """Whether the title is a model's reading of the evidence. It is the only
    part of a candidate anything generated, and it is marked so nobody mistakes
    a sentence for a fact."""

    learned_from: int = 0
    """How many doings had been seen the last time learning was tried on this.

    Unattended learning runs on a sweep, and a candidate whose evidence will
    not induce would otherwise be tried again every quarter of an hour, leaving
    two sealed recordings behind each time. Trying again is only worth it when
    there is something new to try it on."""

    learned_under: int = 0
    """Which version of the induction rules made that attempt.

    The other half of "something new": rules change too. A candidate refused
    under rules that have since been fixed would otherwise sit refused
    forever, silently, while the code that could learn it is already merged.
    Zero means the attempt predates anyone counting."""

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
        """Whether a fresh attempt would see anything the last one did not.

        Two ways it might: a doing arrived that the last attempt never read, or
        induction has learned to read what it already had. The version is given
        rather than known here, because which rules are current is not
        something a task somebody keeps doing has any business knowing.
        """
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
        """The middle one, not the mean. One episode where somebody went to
        lunch mid-task would otherwise decide what the task costs."""
        if not self.episodes:
            return 0
        return int(median(episode.duration_ms for episode in self.episodes))

    @property
    def status_is_new(self) -> bool:
        """Whether anything may still be decided about it. `dismiss` and
        `taught` both refuse otherwise, and a second answer to one join should
        not raise because the first already dismissed the duplicate."""
        return self.status is CandidateStatus.NEW

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

    def suggest(self, join: Join) -> bool:
        """Record a suggestion about this candidate. Answers whether it was new.

        Replaces an earlier suggestion about the same pair rather than
        accumulating: the question was asked again because the evidence grew,
        and two answers to one question on a screen is a screen nobody trusts.

        A pair somebody has already answered is left exactly as it is. Nothing
        a model notices next week overrules a person who looked at these two
        candidates and said what they were.
        """
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
        """Somebody looked at the pair and said what it is.

        Answerable only where something was suggested: an answer to a question
        nobody asked has no evidence attached to it, and the reason a person
        was shown these two together is half of what makes the answer readable
        later.
        """
        known = self.join_with(other_id, kind)
        if known is None:
            raise InvariantViolation("nothing suggested these two were one thing")
        answered = replace(known, answered=answer, answered_by=by)
        self.joins = tuple(answered if one is known else one for one in self.joins)
        return answered

    def dismiss(self, reason: str) -> None:
        """Not worth automating, said by a person. Kept rather than deleted, so
        the miner does not offer it again next week."""
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
        """Both transitions are one-way and terminal. Without this, a stale
        tab's retried teach after a dismissal -- or a second operator's click
        after the first's -- silently overwrites the decision already made:
        a rejected task becomes a skill, or an existing skill's id is replaced
        and every trigger still pointing at it is orphaned."""
        if self.status is not CandidateStatus.NEW:
            raise InvariantViolation(f"a {self.status} candidate cannot be {verb}")
