"""Skill aggregate. See docs/06-glossary.md#skill."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId, RecordingId, SkillId, TenantId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.assertion import Assertion
from sro.domain.skill.earned import earned_stage
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import NetworkPlan, UiPlan
from sro.domain.skill.promotion import PromotionStage, check_promotion
from sro.domain.skill.track_record import TrackRecord, Verdict, why_not_autonomous


@dataclass(frozen=True, slots=True)
class SkillStep:
    index: int
    intent: str
    network_plan: NetworkPlan | None = None
    ui_plan: UiPlan | None = None
    assertions: tuple[Assertion, ...] = ()
    requires_human: bool = False

    narration: str = ""
    """What the operator said while doing this step.

    Kept apart from ``intent`` on purpose: intent is derived from what was
    observed and is the same on every replay, narration is a transcript and is
    a model's reading of a microphone. One field holding either would make them
    indistinguishable at review, which is where the difference matters most."""

    branch_hint: str | None = None
    """A path the operator described but did not demonstrate. A question for a
    reviewer -- never executed, because nothing was recorded doing it."""

    def __post_init__(self) -> None:
        if self.index < 0:
            raise InvariantViolation("SkillStep.index must be non-negative")
        if not self.intent.strip():
            raise InvariantViolation("SkillStep requires an intent")
        if self.network_plan is None and self.ui_plan is None:
            raise InvariantViolation(
                f"step {self.index} has neither a network plan nor a UI plan; "
                "there is no way to perform it"
            )

    @property
    def placeholders(self) -> frozenset[str]:
        names: set[str] = set()
        if self.network_plan is not None:
            names |= self.network_plan.placeholders
        if self.ui_plan is not None:
            names |= self.ui_plan.placeholders
        for assertion in self.assertions:
            names |= assertion.expected.placeholders
        return frozenset(names)


@dataclass(frozen=True, slots=True)
class Provenance:
    """Which demonstrations a version came from. Never optional."""

    recording_ids: tuple[RecordingId, ...]
    induced_at: datetime
    induced_by: PrincipalId
    note: str = ""

    def __post_init__(self) -> None:
        if not self.recording_ids:
            raise InvariantViolation("a skill version must cite the recordings it came from")
        if self.induced_at.tzinfo is None:
            raise InvariantViolation("Provenance.induced_at must be timezone-aware")


@dataclass(eq=False)
class SkillVersion:
    """One revision. Steps and parameters are fixed; only the stage moves."""

    version: int
    steps: tuple[SkillStep, ...]
    parameters: tuple[Parameter, ...]
    provenance: Provenance
    stage: PromotionStage = PromotionStage.RECORDED
    promoted_at: datetime | None = None
    promoted_by: PrincipalId | None = None

    track_record: TrackRecord = field(default_factory=TrackRecord)
    """What this version has actually done. Autonomy is earned from this, never
    granted by a click."""

    summary: str = ""
    """What this version does, in a sentence."""

    demotion_reason: str | None = None
    """Why this version was pulled back down, when it was."""

    when_to_use: str = ""
    """When to reach for it.

    Together with ``summary`` this is what an operator's request is matched
    against, so it is editable: a skill described in words nobody searches with
    is a skill nobody finds. Editing it changes what is found, never what runs.
    """

    def __post_init__(self) -> None:
        if self.version < 1:
            raise InvariantViolation("version numbers start at 1")
        if not self.steps:
            raise InvariantViolation("a skill version needs at least one step")
        self._check_step_indices()
        self._check_parameters_declared()
        self._check_derived_ordering()

    @property
    def inputs(self) -> tuple[Parameter, ...]:
        return tuple(p for p in self.parameters if p.kind is ParameterKind.INPUT)

    @property
    def needs_human_step(self) -> bool:
        return any(step.requires_human for step in self.steps)

    def describe(self, *, summary: str, when_to_use: str) -> None:
        """Reword what this version is for. A label, never a behaviour."""
        if not summary.strip():
            raise InvariantViolation("a skill nobody can describe is a skill nobody will find")
        self.summary = summary.strip()
        self.when_to_use = when_to_use.strip()

    @property
    def verifiable(self) -> bool:
        """Whether a run of this can be checked at all.

        A skill with no assertion anywhere produces runs that only ever prove a
        request was sent. That may run assisted forever; it may never run
        unattended.
        """
        return any(step.assertions for step in self.steps)

    def record_run(self, verdict: Verdict, at: datetime) -> None:
        self.track_record = self.track_record.after(verdict, at)

    def earn(self, verdict: Verdict, at: datetime) -> PromotionStage | None:
        """Move up if the record now says so. Returns the rung, or None.

        Promotion by hand made a version's stage a fact about somebody's
        afternoon rather than about the skill: the ladder was always meant to be
        earned, and waiting for a click is not evidence. Nobody is named as the
        promoter because nobody was asked -- the runs were.
        """
        target = earned_stage(
            current=self.stage,
            record=self.track_record,
            verdict=verdict,
            has_verifiable_outcome=self.verifiable,
            sends_writes=any(
                step.network_plan is not None
                and step.network_plan.method.upper() not in {"GET", "HEAD", "OPTIONS"}
                for step in self.steps
            ),
        )
        if target is None:
            return None
        self.stage = target
        self.promoted_at = at
        self.promoted_by = None
        self.demotion_reason = None
        return target

    def demote(self, to: PromotionStage, at: datetime, why: str) -> None:
        """Pull a version back down. Not a promotion in reverse: this happens
        automatically, without a human, which is exactly why it is a separate
        method with a reason attached."""
        if to.rung >= self.stage.rung:
            raise InvariantViolation(f"{to} is not below {self.stage}")
        self.stage = to
        self.promoted_at = at
        self.promoted_by = None
        self.demotion_reason = why

    def promote(self, to: PromotionStage, at: datetime, by: PrincipalId) -> None:
        check_promotion(self.stage, to)
        if to is PromotionStage.AUTONOMOUS and (
            refusal := why_not_autonomous(self.track_record, verifiable=self.verifiable)
        ):
            raise InvariantViolation(f"not ready to run unattended: {refusal}")
        if at.tzinfo is None:
            raise InvariantViolation("promotion timestamp must be timezone-aware")
        self.stage = to
        self.promoted_at = at
        self.promoted_by = by

    def _check_step_indices(self) -> None:
        indices = [step.index for step in self.steps]
        if indices != list(range(len(self.steps))):
            raise InvariantViolation(f"step indices must be 0..n-1, got {indices}")

    def _check_parameters_declared(self) -> None:
        names = [p.name for p in self.parameters]
        if len(names) != len(set(names)):
            raise InvariantViolation("parameter names must be unique within a version")

        declared = set(names)
        for step in self.steps:
            missing = step.placeholders - declared
            if missing:
                raise InvariantViolation(
                    f"step {step.index} references undeclared parameters: "
                    f"{', '.join(sorted(missing))}"
                )

    def _check_derived_ordering(self) -> None:
        for param in self.parameters:
            source = param.source_step_index
            if param.kind is not ParameterKind.DERIVED or source is None:
                continue
            if source >= len(self.steps):
                raise InvariantViolation(
                    f"derived parameter {param.name!r} names step {source}, which does not exist"
                )
            first_use = next((s.index for s in self.steps if param.name in s.placeholders), None)
            if first_use is not None and first_use <= source:
                raise InvariantViolation(
                    f"derived parameter {param.name!r} is used at step {first_use} "
                    f"but only produced at step {source}"
                )


@dataclass(eq=False)
class Skill:
    id: SkillId
    tenant_id: TenantId
    objective_key: ObjectiveKey
    name: str
    created_at: datetime
    _versions: list[SkillVersion] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvariantViolation("Skill requires a name")
        if self.created_at.tzinfo is None:
            raise InvariantViolation("Skill.created_at must be timezone-aware")

    @property
    def versions(self) -> tuple[SkillVersion, ...]:
        return tuple(self._versions)

    @property
    def latest(self) -> SkillVersion:
        if not self._versions:
            raise InvariantViolation(f"skill {self.id} has no versions")
        return self._versions[-1]

    def version(self, number: int) -> SkillVersion:
        for candidate in self._versions:
            if candidate.version == number:
                return candidate
        raise InvariantViolation(f"skill {self.id} has no version {number}")

    def next_version_number(self) -> int:
        return len(self._versions) + 1

    def add_version(self, version: SkillVersion) -> None:
        """Append. Existing versions are never mutated by a re-induction."""
        expected = self.next_version_number()
        if version.version != expected:
            raise InvariantViolation(
                f"versions are append-only and sequential: expected v{expected}, "
                f"got v{version.version}"
            )
        if version.stage is not PromotionStage.RECORDED:
            raise InvariantViolation("a new version always starts at RECORDED")
        self._versions.append(version)
