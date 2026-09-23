from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import PrincipalId, RecordingId, SkillId, TenantId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.assertion import Assertion
from sro.domain.skill.earned import earned_stage
from sro.domain.skill.loop import Loop
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import NetworkPlan, ToolPlan, UiPlan
from sro.domain.skill.promotion import PromotionStage, check_promotion
from sro.domain.skill.track_record import TrackRecord, Verdict, why_not_autonomous


@dataclass(frozen=True, slots=True)
class SkillStep:
    index: int
    intent: str
    network_plan: NetworkPlan | None = None
    ui_plan: UiPlan | None = None
    tool_plan: ToolPlan | None = None
    assertions: tuple[Assertion, ...] = ()
    requires_human: bool = False

    narration: str = ""

    branch_hint: str | None = None

    seen_in: int = 0
    of_doings: int = 0

    when: str | None = None

    def __post_init__(self) -> None:
        if self.index < 0:
            raise InvariantViolation("SkillStep.index must be non-negative")
        if not self.intent.strip():
            raise InvariantViolation("SkillStep requires an intent")
        if self.network_plan is None and self.ui_plan is None and self.tool_plan is None:
            raise InvariantViolation(
                f"step {self.index} has no network plan, UI plan or tool plan; "
                "there is no way to perform it"
            )

    @property
    def placeholders(self) -> frozenset[str]:
        names: set[str] = set()
        if self.network_plan is not None:
            names |= self.network_plan.placeholders
        if self.ui_plan is not None:
            names |= self.ui_plan.placeholders
        if self.tool_plan is not None:
            names |= self.tool_plan.placeholders
        for assertion in self.assertions:
            names |= assertion.expected.placeholders
        return frozenset(names)


@dataclass(frozen=True, slots=True)
class Provenance:
    recording_ids: tuple[RecordingId, ...]

    induced_at: datetime
    induced_by: PrincipalId

    note: str = ""

    repaired_from: str | None = None

    aligned_recording_ids: tuple[RecordingId, ...] = ()

    def __post_init__(self) -> None:
        if not self.recording_ids:
            raise InvariantViolation("a skill version must cite the recordings it came from")
        if self.induced_at.tzinfo is None:
            raise InvariantViolation("Provenance.induced_at must be timezone-aware")
        if not set(self.aligned_recording_ids) <= set(self.recording_ids):
            raise InvariantViolation(
                "Provenance.aligned_recording_ids must be a subset of recording_ids -- a "
                "recording cannot have shaped the steps without being cited as a source at all"
            )


@dataclass(eq=False)
class SkillVersion:
    version: int
    steps: tuple[SkillStep, ...]
    parameters: tuple[Parameter, ...]
    provenance: Provenance
    stage: PromotionStage = PromotionStage.RECORDED
    promoted_at: datetime | None = None
    promoted_by: PrincipalId | None = None

    promoted_from: str = ""

    track_record: TrackRecord = field(default_factory=TrackRecord)

    summary: str = ""

    demotion_reason: str | None = None

    starts_on: str | None = None

    systems: tuple[str, ...] = ()

    loops: tuple[Loop, ...] = ()

    when_to_use: str = ""

    def __post_init__(self) -> None:
        if self.version < 1:
            raise InvariantViolation("version numbers start at 1")
        if not self.steps:
            raise InvariantViolation("a skill version needs at least one step")
        self._check_step_indices()
        self._check_parameters_declared()
        self._check_derived_ordering()
        self._check_loops()

    @property
    def inputs(self) -> tuple[Parameter, ...]:
        return tuple(p for p in self.parameters if p.kind is ParameterKind.INPUT and not p.optional)

    def describe(self, *, summary: str, when_to_use: str) -> None:
        if not summary.strip():
            raise InvariantViolation("a skill nobody can describe is a skill nobody will find")
        self.summary = summary.strip()
        self.when_to_use = when_to_use.strip()

    @property
    def crosses_systems(self) -> bool:
        return len(self.systems) > 1

    @property
    def changes_the_system(self) -> bool:
        return any(_writes(step) for step in self.steps)

    @property
    def from_one_demonstration(self) -> bool:
        return len(self.provenance.recording_ids) == 1

    @property
    def needs_a_person(self) -> bool:
        return any(step.network_plan is None and step.tool_plan is None for step in self.steps)

    @property
    def unchecked_writes(self) -> tuple[int, ...]:
        return tuple(step.index for step in self.steps if _writes(step) and not step.assertions)

    @property
    def not_ready_for_autonomy(self) -> str | None:
        return why_not_autonomous(
            self.track_record,
            verifiable=self.verifiable,
            needs_a_person=self.needs_a_person,
            unchecked_writes=(
                "step " + ", ".join(str(index) for index in self.unchecked_writes)
                if self.unchecked_writes
                else "no step"
            ),
        )

    @property
    def verifiable(self) -> bool:
        return any(step.assertions for step in self.steps) and not self.unchecked_writes

    def record_run(
        self, verdict: Verdict, at: datetime, *, revising: Verdict | None = None
    ) -> None:
        self.track_record = (
            self.track_record.after(verdict, at)
            if revising is None
            else self.track_record.instead_of(revising, verdict, at)
        )

    def earn(self, verdict: Verdict, at: datetime) -> PromotionStage | None:
        target = earned_stage(
            current=self.stage,
            record=self.track_record,
            verdict=verdict,
            has_verifiable_outcome=self.verifiable,
            sends_writes=self.changes_the_system,
            values_are_fixed=self.from_one_demonstration,
        )
        if target is None:
            return None
        self.stage = target
        self.promoted_at = at
        self.promoted_by = None
        self.promoted_from = "earned"
        self.demotion_reason = None
        return target

    def demote(self, to: PromotionStage, at: datetime, why: str) -> None:
        if to.rung >= self.stage.rung:
            raise InvariantViolation(f"{to} is not below {self.stage}")
        self.stage = to
        self.promoted_at = at
        self.promoted_by = None
        self.promoted_from = ""
        self.demotion_reason = why

    def promote(
        self,
        to: PromotionStage,
        at: datetime,
        by: PrincipalId,
        *,
        acknowledging_fixed_values: bool = False,
        from_where: str = "",
    ) -> None:
        check_promotion(self.stage, to)
        if from_where == "preview" and to.rung > PromotionStage.ASSISTED.rung:
            raise InvariantViolation(
                "a preview promotes no further than assisted; "
                f"{to} is earned by clean runs, not by a press"
            )
        if from_where == "preview" and self.demotion_reason:
            raise InvariantViolation(
                "this task went wrong three times in a row, so it was pulled back and stopped "
                "running. Somebody needs to look at what it did before it runs again -- ask "
                "whoever looks after these tasks to check it in the console"
            )
        if (
            to.rung > PromotionStage.SHADOW.rung
            and self.from_one_demonstration
            and self.changes_the_system
            and not acknowledging_fixed_values
        ):
            raise InvariantViolation(
                "this version came from one demonstration, so every value it sends is fixed "
                "as demonstrated -- running it assisted repeats that exact write. Teach it a "
                "second time to turn those values into parameters, or promote it again saying "
                "you have read what it sends"
            )
        if to is PromotionStage.AUTONOMOUS and (refusal := self.not_ready_for_autonomy):
            raise InvariantViolation(f"not ready to run unattended: {refusal}")
        if at.tzinfo is None:
            raise InvariantViolation("promotion timestamp must be timezone-aware")
        self.stage = to
        self.promoted_at = at
        self.promoted_by = by
        self.promoted_from = from_where
        if from_where != "preview":
            self.track_record = replace(self.track_record, consecutive_failures=0)
            self.demotion_reason = None

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
            named = step.placeholders | ({step.when} if step.when else frozenset())
            missing = named - declared
            if missing:
                raise InvariantViolation(
                    f"step {step.index} references undeclared parameters: "
                    f"{', '.join(sorted(missing))}"
                )

    def _check_loops(self) -> None:
        covered: set[int] = set()
        declared = {parameter.name for parameter in self.parameters}
        for loop in self.loops:
            if loop.last_step >= len(self.steps):
                raise InvariantViolation(
                    f"a loop covers steps {loop.first_step}-{loop.last_step}, "
                    f"and this version has {len(self.steps)}"
                )
            body = set(loop.body)
            if body & covered:
                raise InvariantViolation("loops may not overlap")
            covered |= body
            unknown = sorted({binding.parameter for binding in loop.binds} - declared)
            if unknown:
                raise InvariantViolation(
                    f"a loop binds undeclared parameters: {', '.join(unknown)}"
                )

    def loop_at(self, step_index: int) -> Loop | None:
        return next((loop for loop in self.loops if loop.covers(step_index)), None)

    def loop_from(self, step_index: int) -> Loop | None:
        return next((loop for loop in self.loops if loop.over_step_index == step_index), None)

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

    @property
    def runnable(self) -> SkillVersion | None:
        for version in reversed(self._versions):
            if version.stage is not PromotionStage.RECORDED:
                return version
        return None

    def version(self, number: int) -> SkillVersion:
        for candidate in self._versions:
            if candidate.version == number:
                return candidate
        raise InvariantViolation(f"skill {self.id} has no version {number}")

    def next_version_number(self) -> int:
        return len(self._versions) + 1

    def add_version(self, version: SkillVersion) -> None:
        expected = self.next_version_number()
        if version.version != expected:
            raise InvariantViolation(
                f"versions are append-only and sequential: expected v{expected}, "
                f"got v{version.version}"
            )
        if version.stage is not PromotionStage.RECORDED:
            raise InvariantViolation("a new version always starts at RECORDED")
        self._versions.append(version)


def _writes(step: SkillStep) -> bool:
    if step.network_plan is not None and step.network_plan.is_mutation:
        return True
    return step.tool_plan is not None and step.tool_plan.writes
