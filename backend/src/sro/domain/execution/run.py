from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import (
    DeviceId,
    Identifier,
    PrincipalId,
    SkillId,
    TenantId,
)
from sro.domain.skill.promotion import PromotionStage


class RunId(Identifier): ...


class Medium(StrEnum):
    """Which rung of the ladder performed a step."""

    NETWORK = "network"

    TOOL = "tool"

    UI = "ui"
    VISION = "vision"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StepDisposition(StrEnum):
    PERFORMED = "performed"

    WITHHELD = "withheld"

    SKIPPED = "skipped"

    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StepOutcome:
    index: int
    medium: Medium
    disposition: StepDisposition
    intent: str

    method: str | None = None
    url: str | None = None
    status_code: int | None = None
    idempotency_key: str | None = None

    request_body: str | None = None

    assertion_failures: tuple[str, ...] = ()

    unchecked: tuple[str, ...] = ()

    escalated_from: Medium | None = None

    escalation_reason: str | None = None

    plan_step: int | None = None

    iteration: int = 0

    matched_by: str | None = None

    detail: str | None = None

    unreachable: bool = False

    found_rows: int | None = None

    found_total: int | None = None

    found_partial: bool = False

    found: tuple[dict[str, str], ...] = ()
    found_values: tuple[tuple[str, tuple[str, ...]], ...] = ()

    found_columns: tuple[str, ...] = ()

    found_labels: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.disposition is not StepDisposition.FAILED and not self.assertion_failures

    @property
    def step_index(self) -> int:
        return self.plan_step if self.plan_step is not None else self.index


@dataclass(eq=False)
class Run:
    id: RunId
    tenant_id: TenantId
    skill_id: SkillId
    skill_version: int
    stage: PromotionStage

    parameters: Mapping[str, str]
    requested_by: PrincipalId
    started_at: datetime

    medium: Medium = Medium.NETWORK

    device_id: DeviceId | None = None

    may_take_focus: bool = False

    iterations: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    systems: tuple[str, ...] = ()

    target_system: str = ""

    authorized_by: PrincipalId | None = None

    derived: dict[str, str] = field(default_factory=dict)

    may_change_the_system: bool = True

    status: RunStatus = RunStatus.RUNNING
    steps: list[StepOutcome] = field(default_factory=list)
    ended_at: datetime | None = None
    failure: str | None = None

    revisions: tuple[tuple[str, str, datetime], ...] = ()

    wrong_because: str | None = None

    intent: str = ""

    def __post_init__(self) -> None:
        if self.skill_version < 1:
            raise InvariantViolation("version numbers start at 1")
        if self.started_at.tzinfo is None:
            raise InvariantViolation("Run.started_at must be timezone-aware")
        if (
            self.may_change_the_system
            and self.stage.rung > PromotionStage.SHADOW.rung
            and self.authorized_by is None
        ):
            raise InvariantViolation(
                f"a {self.stage} run performs real writes and must name the human who authorised it"
            )
        self.parameters = MappingProxyType(dict(self.parameters))

    @property
    def writes_sent(self) -> int:
        return sum(
            1
            for step in self.steps
            if step.disposition is StepDisposition.PERFORMED and step.idempotency_key is not None
        )

    @property
    def performs_writes(self) -> bool:
        return self.stage.rung > PromotionStage.SHADOW.rung

    @property
    def values(self) -> dict[str, str]:
        return {**self.parameters, **self.derived}

    def learn(self, name: str, value: str) -> None:
        if name in self.derived and self.derived[name] != value:
            raise InvariantViolation(
                f"{name} was already read as {self.derived[name]!r}; a derived value "
                "is read once, and a second answer means the run is not repeatable"
            )
        self.derived[name] = value

    def will_iterate(self, loop_at: int, bindings: list[dict[str, str]]) -> None:
        self.iterations[str(loop_at)] = bindings

    def iterations_of(self, loop_at: int) -> list[dict[str, str]] | None:
        return self.iterations.get(str(loop_at))

    def record(self, outcome: StepOutcome) -> None:
        self._require_running()
        if outcome.index != len(self.steps):
            raise InvariantViolation(
                f"step {outcome.index} recorded out of order; a run is an ordered log"
            )
        self.steps.append(outcome)

    def finish(self, at: datetime) -> None:
        self._require_running()
        self._require_after_start(at)
        failures = [s for s in self.steps if not s.ok]
        self.status = RunStatus.FAILED if failures else RunStatus.SUCCEEDED
        if failures:
            self.failure = f"{len(failures)} step(s) did not satisfy their post-conditions"
        self.ended_at = at

    def fail(self, at: datetime, reason: str) -> None:
        self._require_running()
        self._require_after_start(at)
        if not reason.strip():
            raise InvariantViolation("a failed run must say why")
        self.status = RunStatus.FAILED
        self.failure = reason
        self.ended_at = at

    def called_wrong(self, because: str) -> None:
        if self.status is RunStatus.RUNNING:
            raise InvariantViolation(
                "a run still running has made nothing yet for anyone to call wrong"
            )
        if self.wrong_because is not None:
            raise InvariantViolation(f"this run was already called wrong: {self.wrong_because!r}")
        if not because.strip():
            raise InvariantViolation("a run called wrong says why, even if only 'undone'")
        self.wrong_because = because

    def _require_running(self) -> None:
        if self.status is not RunStatus.RUNNING:
            raise InvariantViolation(f"run is {self.status} and cannot be added to")

    def _require_after_start(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("timestamps must be timezone-aware")
        if at < self.started_at:
            raise InvariantViolation("a run cannot end before it started")
