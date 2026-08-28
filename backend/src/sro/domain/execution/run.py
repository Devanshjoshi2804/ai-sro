"""One attempt to perform a skill against a live system.

A run is the audit record. It exists before the first call is made and it is
written to after every step, so a run that dies mid-flight still says exactly
which calls were sent and which were not -- the question anybody asks first
after an automated system touches a warehouse.
"""

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
    UI = "ui"
    VISION = "vision"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StepDisposition(StrEnum):
    PERFORMED = "performed"
    """The call was sent and the system answered."""

    WITHHELD = "withheld"
    """A mutation the stage does not permit. Recorded in full, never sent --
    this is what a shadow run is for: proving what would happen."""

    SKIPPED = "skipped"
    """Nothing to do at this rung: the step has no network plan."""

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
    """Present for every mutating step, sent or withheld. Identifies the attempt
    so a retry can tell "already done" from "never started"."""

    request_body: str | None = None
    """The body a write produced -- withheld, sent, or failed on the wire.

    A step that records only the method and the URL hides every decision
    induction made: which field became a parameter, what an optional one
    nobody supplied falls back to, whether a value landed in the right key.
    Withheld, that body exists nowhere else. Sent, "POST -> 201" says a record
    was created in a live warehouse and nothing about what is in it, and the
    review this system's safety rests on cannot be done. Failed, it is the only
    thing left to debug with, and the failure that says "the call may have
    arrived" is exactly when somebody needs to know what would have arrived.

    Writes only. A read's body is not what anybody reviews, and the UI medium
    has no body at all."""

    assertion_failures: tuple[str, ...] = ()

    escalated_from: Medium | None = None
    """Set when a slower medium finished what a faster one could not. The run
    says which rung actually did the work, because a step that quietly needs the
    browser every time is a skill drifting from the system it was taught on."""

    escalation_reason: str | None = None

    plan_step: int | None = None
    """Which step of the version this was, when that is not ``index``.

    ``index`` is the position in the run's log, and for a skill without loops
    the two are the same number -- which is every skill taught before loops
    existed. A loop's body runs once per thing in a list, so the same step of
    the plan appears at several positions, and the run has to be able to say
    which one it was."""

    iteration: int = 0
    """Which time round the loop this was. Zero for everything else."""

    matched_by: str | None = None
    """Which locator strategy found the control, for a UI step. A step that only
    ever matches on the last fallback is about to break."""

    detail: str | None = None
    """Why it was withheld, skipped or failed. Never carries a response body."""

    found_rows: int | None = None
    """How many records this response carried. Kept because a run that reports
    `GET … -> 200` has answered nothing: the number was in the response and was
    being thrown away."""

    found_total: int | None = None
    """How many exist, where the system said so beside the page.

    Distinct from ``found_rows`` because they disagree, and the disagreement is
    the whole point: 50 rows came back out of 330,140, and answering "how many
    suppliers are there" with 50 is a confident wrong number."""

    found_partial: bool = False
    """A page came back and nothing said how long the whole thing is. Then there
    is no count to report, and reporting one anyway is the failure this system
    exists to avoid."""

    found: tuple[dict[str, str], ...] = ()
    found_values: tuple[tuple[str, tuple[str, ...]], ...] = ()
    """A few values each column holds, as pairs so this survives being stored.

    What the next question can be asked about: a column with three values is a
    filter somebody may want, and one nobody has to invent."""

    found_columns: tuple[str, ...] = ()
    """The columns of the result, in the order they should be shown. Carried
    because `jsonb` sorts an object's keys by length, so a row cannot be trusted
    to remember its own field order."""

    found_labels: tuple[str, ...] = ()
    """Each record as one readable line. Kept as text because `jsonb` sorts an
    object's keys by length, so the field ranking does not survive being
    stored."""
    """Enough of the first records to recognise them. Bounded deliberately --
    this is an answer, not a copy of the customer's database."""

    @property
    def ok(self) -> bool:
        return self.disposition is not StepDisposition.FAILED and not self.assertion_failures

    @property
    def step_index(self) -> int:
        """The version step this outcome belongs to."""
        return self.plan_step if self.plan_step is not None else self.index


@dataclass(eq=False)
class Run:
    """The aggregate. Steps are appended; nothing is ever rewritten."""

    id: RunId
    tenant_id: TenantId
    skill_id: SkillId
    skill_version: int
    stage: PromotionStage
    """The stage the skill was at when this ran. Copied, not referenced: a later
    promotion must not change the record of what was permitted at the time."""

    parameters: Mapping[str, str]
    requested_by: PrincipalId
    started_at: datetime

    medium: Medium = Medium.NETWORK
    """The rung this run performs the task at. Recorded on the run rather than
    inferred from the steps, because "we ran this in a browser" is the first
    thing anybody asks about a run that behaved oddly."""

    device_id: DeviceId | None = None
    """The operator's own browser, when this run is performed there rather than
    in one the deployment owns.

    Recorded rather than resolved at each step: which browser a write went
    through is the first question about a run that touched the wrong record,
    and a device chosen fresh per step could answer it differently each time."""

    may_take_focus: bool = False
    """Whether this run is allowed to bring a tab to the front of the
    operator's browser.

    The trigger's decision, carried on the run because a run outlives the
    request that started it: a task somebody asked for and is watching may move
    their tab, and one a cron or a mail relay started at 3am may not. Default
    no -- a run that has not been told it may take somebody's screen has not
    been given permission to."""

    iterations: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    """What each loop's body is to be run with, one entry per thing in the list.

    Written the moment the step that produces the list answers, because that is
    when the count exists at all -- and stored on the run rather than recomputed,
    so a run that resumes after a restart does the same iterations it started
    rather than whatever the system says now."""

    systems: tuple[str, ...] = ()
    """Every system this run touched, when that is more than one.

    `target_system` alone is where the work lands, and it is what a run is keyed
    by. For a workflow that also writes into a second system, being keyed by the
    first means the second's circuit breaker never sees the failure -- so the
    breaker is asked about all of them and, because of this, can be answered by
    all of them. Half a breaker protects nothing and reads as though it does.
    """

    target_system: str = ""
    """Which system this run wrote to.

    Copied from the skill rather than joined: the circuit breaker asks "how has
    this system behaved lately", and a join through a skill that has since been
    re-induced would answer a different question.
    """

    authorized_by: PrincipalId | None = None
    """Who authorised writes for this run. Required above shadow; a run that
    changed a warehouse names the human who allowed it."""

    derived: dict[str, str] = field(default_factory=dict)
    """Values read out of one step's response for a later step to use.

    Kept on the run rather than in memory because a run survives the process:
    the step that needs the item number may execute in a different worker from
    the step that read it. It is also the honest audit answer to "what value did
    it actually send", which the parameters alone cannot give."""

    may_change_the_system: bool = True
    """Whether the skill being run sends anything but reads.

    Authorisation is for changing a system. A read-only skill demanded a named
    human and told them it "performs real writes" while fetching a list -- untrue,
    and the kind of prompt that teaches people to click past prompts."""

    status: RunStatus = RunStatus.RUNNING
    steps: list[StepOutcome] = field(default_factory=list)
    ended_at: datetime | None = None
    failure: str | None = None

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
        """Mutating steps that actually went out. What the blast radius counts."""
        return sum(
            1
            for step in self.steps
            if step.disposition is StepDisposition.PERFORMED and step.idempotency_key is not None
        )

    @property
    def performs_writes(self) -> bool:
        """Whether this run's stage permits a mutation to leave the process.

        Shadow is the rehearsal rung: every read is real, every write is
        recorded and withheld. That is the whole difference between the two.
        """
        return self.stage.rung > PromotionStage.SHADOW.rung

    @property
    def values(self) -> dict[str, str]:
        """Everything a template may reference: what was asked for, plus what
        the system has said so far."""
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
        """None where the list has not arrived yet, which is every moment
        before the step that produces it has answered."""
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
        """End a run that could not continue, as opposed to one that ran and
        failed its checks. Both are FAILED; only this one has a reason that is
        not about assertions."""
        self._require_running()
        self._require_after_start(at)
        if not reason.strip():
            raise InvariantViolation("a failed run must say why")
        self.status = RunStatus.FAILED
        self.failure = reason
        self.ended_at = at

    def _require_running(self) -> None:
        if self.status is not RunStatus.RUNNING:
            raise InvariantViolation(f"run is {self.status} and cannot be added to")

    def _require_after_start(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise InvariantViolation("timestamps must be timezone-aware")
        if at < self.started_at:
            raise InvariantViolation("a run cannot end before it started")
