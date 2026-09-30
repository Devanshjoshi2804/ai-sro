"""Wire types.

Domain objects never cross the HTTP boundary. These are what the frontend's
generated client is built from, so their shape is a contract; the aggregates
behind them stay free to change.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Any, Literal
from urllib.parse import quote

from pydantic import BaseModel, Field, StrictInt, StringConstraints

from sro.application.analytics.audit import Audit, AuditedRun
from sro.application.analytics.summary import Summary
from sro.application.capture.devices import DeviceLine
from sro.application.chat.from_the_mail import LookedInTheMail
from sro.application.chat.understand import Understood
from sro.application.execution.effects import can_try_again
from sro.application.execution.mail_job import K_BODY
from sro.application.execution.pursuits import PursuitProgress
from sro.application.execution.reversal import Reversal
from sro.application.intent.match import Candidate
from sro.application.lookup.answer import as_seen
from sro.application.lookup.plan_lookups import Planned
from sro.application.lookup.run_lookups import Answers, Looked
from sro.application.observation.read_shots import PlayableShot
from sro.application.runtime.answer_run import WriteVerdict
from sro.application.skill.read_workflows import CitedEvidence, KnownWorkflow
from sro.domain.chat.reading import ChatReading
from sro.domain.chat.thread import Thread
from sro.domain.execution.account import K_USERNAME_MAX_LEN
from sro.domain.execution.belts import K_EARNED_RUNS
from sro.domain.execution.run import Medium, Run, StepOutcome
from sro.domain.execution.waiting import standing_question
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.lookup.plan import Asked, Lookup
from sro.domain.observation.attempts import Attempt
from sro.domain.observation.batch import CaptureMode, RejectedEvent
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.shared.prices import DaySpend
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.offers import Offer
from sro.domain.skill.skill import Skill, SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import (
    DEMOTE_AFTER_FAILURES,
    REQUIRED_CLEAN_RUNS,
)
from sro.domain.trigger.arrival import Arrival
from sro.domain.trigger.confirmation import Confirmation
from sro.domain.trigger.trigger import Trigger, TriggerKind
from sro.domain.trigger.watch import MAX_TERM, Term, TermField, ValueAt, Watch


class ObjectiveKeyModel(BaseModel):
    objective_type: str
    target_system: str
    entity_type: str
    facility: str
    direction: Direction

    @classmethod
    def of(cls, key: ObjectiveKey | None) -> ObjectiveKeyModel | None:
        if key is None:
            return None
        return cls(
            objective_type=key.objective_type,
            target_system=key.target_system,
            entity_type=key.entity_type,
            facility=key.facility,
            direction=key.direction,
        )

    def to_domain(self) -> ObjectiveKey:
        return ObjectiveKey(
            objective_type=self.objective_type,
            target_system=self.target_system,
            entity_type=self.entity_type,
            facility=self.facility,
            direction=self.direction,
        )


class ConnectSystemRequest(BaseModel):
    """An address, and nothing anybody has to think of a word for.

    A name and a system key are things the URL already knows. Asking for them
    made connecting a form to fill in rather than a link to paste, and got two
    people naming one system two ways.
    """

    base_url: str
    name: str | None = None
    target_system: str | None = None


class ConnectionModel(BaseModel):
    id: str
    name: str
    target_system: str
    base_url: str
    status: str
    authenticated_at: datetime | None
    last_error: str | None


class CredentialsRequest(BaseModel):
    """Entered once, by a human, and never read back out.

    There is no matching response model on purpose: an endpoint that returned a
    password would put it in every proxy log between here and the caller.
    """

    username: str
    password: str


class SignedInResponse(BaseModel):
    target_system: str
    landed_at: str
    steps: list[str]
    """What the driver did, in order, with no values -- enough to debug a login
    that stalled without recording what was typed."""


class PursueRequest(BaseModel):
    """What the operator confirmed before anything is driven."""

    intent: str
    target_system: str
    values: dict[str, str] = {}
    """The values they gave for the fields the screen needs. Given rather than
    guessed: a model asked to work out a code on screen will invent one."""

    start_url: str | None = None

    authorized_by: str | None = None
    """Set when the operator confirmed a pursuit that would change something.
    Their say-so, not their name: the name comes from the credential, so a
    request cannot put somebody else on the record for a warehouse write."""


class PursuitProgressModel(BaseModel):
    id: str
    goal: str
    state: str
    """working | reached | stopped | failed. `reached` is what the model
    claimed, never what the system verified: a pursuit has no demonstration to
    assert against."""

    gestures: list[str]
    detail: str
    landed_at: str

    session_id: str = ""
    """The browser it is driving, so the console can offer a window onto it.
    Watching the thing happen is what turns a two-minute wait into progress."""

    recording_id: str = ""
    skill_id: str = ""
    """What it left behind, and what was induced from it."""

    @classmethod
    def of(cls, progress: PursuitProgress) -> PursuitProgressModel:
        return cls(
            id=progress.id,
            goal=progress.goal,
            state=progress.state.value,
            gestures=list(progress.gestures),
            detail=progress.detail,
            landed_at=progress.landed_at,
            session_id=progress.session_id,
            recording_id=progress.recording_id,
            skill_id=progress.skill_id,
        )


class OpenQuestionModel(BaseModel):
    system: str
    key: str
    question: str
    options: list[str]
    because: list[str]

    @classmethod
    def of(cls, entry: object) -> OpenQuestionModel:
        body = getattr(entry, "body", {}) or {}
        return cls(
            system=str(getattr(entry, "system", "")),
            key=str(getattr(entry, "key", "")),
            question=str(body.get("question") or getattr(entry, "title", "")),
            options=[str(option) for option in (body.get("options") or [])],
            because=[str(reason) for reason in (body.get("because") or [])],
        )


class AnswerQuestionRequest(BaseModel):
    system: str
    key: str
    chosen: str


class TokenEstablishedResponse(BaseModel):
    target_system: str
    held: bool
    """That one exists, never what it is. A token that reached a response body
    would be in every proxy log between here and the caller."""


class ResumeRequest(BaseModel):
    reason: str
    """Why it is safe to carry on. Kept, because a breaker anybody can clear
    anonymously is a breaker that stops meaning anything."""


class SessionCheckModel(BaseModel):
    connection_id: str
    target_system: str
    health: str
    """signed_in | signed_out | never_connected | unreachable. Unreachable is
    not a bad session: signing in again would not fix an outage."""

    detail: str


class OpenedConnectionResponse(BaseModel):
    connection_id: str
    live_view_url: str
    browser_session_id: str
    """Handed back when the operator says they have signed in, so the session
    they created is the one that gets kept."""

    target_system: str
    name: str
    """What was derived from the address, so the console can show what it
    decided rather than making somebody type it."""


class SkillSummary(BaseModel):
    id: str
    name: str
    objective_key: ObjectiveKeyModel
    created_at: datetime
    latest_version: int
    latest_stage: str
    summary: str
    """What the latest version does. Carried on the list because this is what a
    request is matched against, and a list that hides it hides the skill."""

    systems: list[str]
    """Every system the latest version touches. More than one means it runs only
    in a browser signed in to all of them, which a screen offering to put it on
    a clock has to know before it offers."""

    @classmethod
    def of(cls, skill: Skill) -> SkillSummary:
        latest = skill.versions[-1] if skill.versions else None
        return cls(
            id=skill.id.value,
            name=skill.name,
            objective_key=ObjectiveKeyModel(
                objective_type=skill.objective_key.objective_type,
                target_system=skill.objective_key.target_system,
                entity_type=skill.objective_key.entity_type,
                facility=skill.objective_key.facility,
                direction=skill.objective_key.direction,
            ),
            created_at=skill.created_at,
            latest_version=latest.version if latest else 0,
            latest_stage=latest.stage.value if latest else "recorded",
            summary=latest.summary if latest else "",
            systems=list(latest.systems) if latest else [],
        )


class OptionsModel(BaseModel):
    """Where a field's values come from. Its presence is what makes the console
    draw a dropdown instead of a text box."""

    label: list[str]
    value: str
    searchable: bool


class ParameterModel(BaseModel):
    name: str
    kind: str
    description: str
    observed_values: list[str]
    source_step_index: int | None
    options: OptionsModel | None = None

    optional: bool = False
    """Some demonstration left this field out and the write still worked."""

    absent_as: str | None = None
    """What the skipping demonstration sent instead -- the JSON that stands for
    "nobody filled this in". The answer to "why is this optional", and the
    reason it is on the wire: a reviewer asked that has to be shown the doing
    that proves it, not told to trust a flag."""

    evidence: str = "proven"
    """Whether two demonstrations disagreed here, or a model read one and
    guessed. Shown, because a proposed parameter is confirmed by whoever runs
    the skill and a proven one is not."""


class GrantRequest(BaseModel):
    host: str
    seconds: int = 0
    """How long to watch it for. Zero means as long as a grant may last; the
    server caps whatever is asked for, so a browser cannot ask for forever."""


class GrantModel(BaseModel):
    host: str
    granted_by: str
    granted_at: datetime
    expires_at: datetime


class GrantsResponse(BaseModel):
    """What this browser may watch beyond the tenant's default, now.

    The whole live list rather than the one just changed: the panel draws from
    it, and a screen that showed only the last answer would go stale the first
    time a grant expired underneath it.
    """

    grants: list[GrantModel]

    @classmethod
    def of(cls, device: AgentDevice) -> GrantsResponse:
        return cls(
            grants=[
                GrantModel(
                    host=grant.host,
                    granted_by=str(grant.granted_by),
                    granted_at=grant.granted_at,
                    expires_at=grant.expires_at,
                )
                for grant in device.grants
            ]
        )


class AssertionModel(BaseModel):
    kind: str
    expected: str
    pointer: str | None
    written_by: str | None = None
    """Who decided this counts as success, where a person did. ``None`` means
    induction derived it from the recordings -- two demonstrations agreeing,
    which is evidence rather than an opinion."""


class NetworkPlanModel(BaseModel):
    method: str
    url: str
    headers: dict[str, str]
    body: str | None
    expected_status: int | None
    replayable: bool
    unreplayable_reason: str | None
    required_credentials: list[str]


class UiPlanModel(BaseModel):
    action: str
    target: str | None
    target_path: str | None
    value: str | None
    wait_for: str | None


class ConfirmationModel(BaseModel):
    """A fire waiting for somebody to say yes."""

    id: str
    trigger_id: str
    skill_id: str | None = None
    workflow_id: str | None = None
    """What the card asks about, and exactly one of them carries it. See
    `Confirmation`."""
    skill_name: str
    asked_at: datetime
    expires_at: datetime
    values: dict[str, str]
    because: str
    answer: str

    @classmethod
    def of(cls, confirmation: Confirmation, *, skill_name: str = "") -> ConfirmationModel:
        return cls(
            id=confirmation.id.value,
            trigger_id=confirmation.trigger_id.value,
            skill_id=confirmation.skill_id.value if confirmation.skill_id else None,
            workflow_id=confirmation.workflow_id,
            skill_name=skill_name,
            asked_at=confirmation.asked_at,
            expires_at=confirmation.expires_at,
            values=dict(confirmation.values),
            because=confirmation.because,
            answer=confirmation.answer.value,
        )


class DeclineRequest(BaseModel):
    note: str = ""


class AnsweredModel(BaseModel):
    confirmation_id: str
    answer: str
    run_id: str | None = None


class ToolPlanModel(BaseModel):
    server: str
    tool: str
    arguments: dict[str, str]
    writes: bool


class StepModel(BaseModel):
    index: int
    intent: str
    requires_human: bool
    narration: str
    branch_hint: str | None
    when: str | None
    network_plan: NetworkPlanModel | None
    ui_plan: UiPlanModel | None
    tool_plan: ToolPlanModel | None = None
    assertions: list[AssertionModel]


class TrackRecordModel(BaseModel):
    clean_streak: int
    consecutive_failures: int
    clean_runs: int
    degraded_runs: int
    failed_runs: int
    unreachable_runs: int
    clean_runs_needed: int = REQUIRED_CLEAN_RUNS
    failures_before_demotion: int = DEMOTE_AFTER_FAILURES


class LoopModel(BaseModel):
    """A block of steps done once for each thing an earlier step's answer listed."""

    over_step_index: int
    over_pointer: str
    first_step: int
    last_step: int
    binds: dict[str, str]
    says: str
    """The band's label, in the words a reviewer reads: "once for each line
    step 0 found"."""


class SkillVersionModel(BaseModel):
    version: int
    stage: str
    summary: str
    when_to_use: str
    track_record: TrackRecordModel
    ready_for_autonomy: str | None
    """``None`` when it is ready; otherwise the reason it is not. A gate that
    says no without saying why is a gate people work around."""

    demotion_reason: str | None

    promoted_from: str
    """Where the review that put this version at its current stage happened.
    See `SkillVersion.promoted_from` for the full vocabulary; the two that
    matter on this screen are `"console"` -- somebody reading the evidence
    here -- and `"preview"` -- an operator reading the panel's preview and
    pressing once. A reviewer needs both spelled out to tell the two apart
    and disagree with either -- see ADR 014. Blank means nobody has promoted
    this version by a click of any kind; `"earned"` and `"repair"` mean a
    process moved it, with nobody to disagree with."""

    induced_at: datetime
    induced_by: str
    recording_ids: list[str]
    aligned_recording_ids: list[str]
    """The subset of `recording_ids` that actually shaped the steps, as
    opposed to the ones read only for what they proved a parameter could be.
    See `Provenance.aligned_recording_ids`. Carried on the wire as fact, not
    yet rendered anywhere -- where and how a reviewer should read it is a
    screen decision this field does not make for them."""

    repaired_from: str | None
    """The run whose evidence produced this version, where nobody demonstrated
    it. Named here because "did a person write this or did the system" is the
    first question about a version that changed itself, and prose in the note is
    not something a reviewer can filter a list by."""

    provenance_note: str
    steps: list[StepModel]
    parameters: list[ParameterModel]

    loops: list[LoopModel]
    """The blocks this version does once per thing in a list. Empty for most
    skills, and the review screen draws a band around the steps of each."""

    systems: list[str]
    """Every system this version touches.

    More than one means a workflow: it runs in a browser signed in to all of
    them, so a caller that cannot name a device cannot run it at all. Said here
    because otherwise no screen can tell one from an ordinary skill until the
    backend refuses the run."""

    starts_on: str | None
    """The page the run opens before it does anything -- see
    `SkillVersion.starts_on`.

    On the wire because the panel's preview names it, and ADR 014's argument
    depends on that: the closed list of what an operator reads before pressing
    is the step intents, the resolved value of each parameter, and the tab the
    run will act in. The run genuinely navigates there
    (`ExecuteSkill` passes it to the driver), so a preview that left it out was
    describing a run in the operator's current tab and performing one somewhere
    else. `None` where the demonstrations began on different screens, which is
    the evidence saying the screen is not part of the task."""

    @classmethod
    def of(cls, version: SkillVersion) -> SkillVersionModel:
        return cls(
            version=version.version,
            stage=version.stage.value,
            summary=version.summary,
            when_to_use=version.when_to_use,
            track_record=TrackRecordModel(
                clean_streak=version.track_record.clean_streak,
                consecutive_failures=version.track_record.consecutive_failures,
                clean_runs=version.track_record.clean_runs,
                degraded_runs=version.track_record.degraded_runs,
                failed_runs=version.track_record.failed_runs,
                unreachable_runs=version.track_record.unreachable_runs,
            ),
            ready_for_autonomy=version.not_ready_for_autonomy,
            demotion_reason=version.demotion_reason,
            promoted_from=version.promoted_from,
            induced_at=version.provenance.induced_at,
            induced_by=version.provenance.induced_by.value,
            recording_ids=[r.value for r in version.provenance.recording_ids],
            aligned_recording_ids=[r.value for r in version.provenance.aligned_recording_ids],
            repaired_from=version.provenance.repaired_from,
            provenance_note=version.provenance.note,
            loops=[
                LoopModel(
                    over_step_index=loop.over_step_index,
                    over_pointer=loop.over_pointer,
                    first_step=loop.first_step,
                    last_step=loop.last_step,
                    binds={binding.parameter: binding.pointer for binding in loop.binds},
                    says=loop.describe(),
                )
                for loop in version.loops
            ],
            systems=list(version.systems),
            starts_on=version.starts_on,
            steps=[
                StepModel(
                    index=step.index,
                    intent=step.intent,
                    requires_human=step.requires_human,
                    narration=step.narration,
                    branch_hint=step.branch_hint,
                    when=step.when,
                    network_plan=(
                        NetworkPlanModel(
                            method=step.network_plan.method,
                            url=str(step.network_plan.url),
                            headers={
                                header.name: (
                                    str(header.value)
                                    if header.value is not None
                                    else f"<{_header_source(header)}>"
                                )
                                for header in step.network_plan.headers
                            },
                            body=(str(step.network_plan.body) if step.network_plan.body else None),
                            expected_status=step.network_plan.expected_status,
                            replayable=step.network_plan.replayable,
                            unreplayable_reason=step.network_plan.unreplayable_reason,
                            required_credentials=sorted(step.network_plan.required_credentials),
                        )
                        if step.network_plan
                        else None
                    ),
                    ui_plan=(
                        UiPlanModel(
                            action=step.ui_plan.action.value,
                            target=(
                                step.ui_plan.target.describe() if step.ui_plan.target else None
                            ),
                            target_path=step.ui_plan.target_path,
                            value=str(step.ui_plan.value) if step.ui_plan.value else None,
                            wait_for=(
                                step.ui_plan.wait_for.describe() if step.ui_plan.wait_for else None
                            ),
                        )
                        if step.ui_plan
                        else None
                    ),
                    tool_plan=(
                        ToolPlanModel(
                            server=step.tool_plan.server,
                            tool=step.tool_plan.tool,
                            arguments={
                                name: str(value) for name, value in step.tool_plan.arguments
                            },
                            writes=step.tool_plan.writes,
                        )
                        if step.tool_plan
                        else None
                    ),
                    assertions=[
                        AssertionModel(
                            kind=a.kind.value,
                            expected=str(a.expected),
                            pointer=a.pointer,
                            written_by=str(a.written_by) if a.written_by else None,
                        )
                        for a in step.assertions
                    ],
                )
                for step in version.steps
            ],
            parameters=[
                ParameterModel(
                    name=p.name,
                    kind=p.kind.value,
                    description=p.description,
                    observed_values=list(p.observed_values),
                    options=(
                        OptionsModel(
                            label=list(p.options.label),
                            value=p.options.value,
                            searchable=p.options.search is not None,
                        )
                        if p.options is not None
                        else None
                    ),
                    source_step_index=p.source_step_index,
                    optional=p.optional,
                    absent_as=p.absent_as,
                    evidence=p.evidence.value,
                )
                for p in version.parameters
            ],
        )


def _header_source(header: Any) -> str:
    """What a reviewer needs to know: where the value will come from."""
    if header.credential_ref:
        return str(header.credential_ref)
    if header.managed:
        return "set by the client"
    return "minted per run"


class SkillDetail(SkillSummary):
    versions: list[SkillVersionModel]

    @classmethod
    def of_skill(cls, skill: Skill) -> SkillDetail:
        return cls(
            **SkillSummary.of(skill).model_dump(),
            versions=[SkillVersionModel.of(v) for v in skill.versions],
        )


class OpenBrowserModel(BaseModel):
    """A browser this deployment is driving right now."""

    session_id: str
    live_view_url: str | None


class ChoiceModel(BaseModel):
    """One row of a field's dropdown: what runs, and what a person reads."""

    value: str
    label: str


class DescribeRequest(BaseModel):
    version: int
    summary: str
    when_to_use: str = ""


class BatchRequest(BaseModel):
    items: list[dict[str, str]] = Field(min_length=1)
    """One parameter set per thing to do. The operator confirmed this table;
    that confirmation is what each assisted run records as its authorisation.
    An empty table confirms nothing, so it is refused rather than answered
    with a 201 and zero runs."""

    authorized_by: str | None = None
    version: int | None = None
    medium: str = "network"


class BatchItemModel(BaseModel):
    parameters: dict[str, str]
    run_id: str | None
    status: str
    """`refused` when a limit or a missing value stopped it before anything was
    sent — distinct from a run that went out and failed."""

    detail: str | None


class BatchResultModel(BaseModel):
    items: list[BatchItemModel]
    performed: int
    stopped_early: str | None


class RunSkillRequest(BaseModel):
    skill_id: str | None = None
    """Only used when a run is started from inside a thread, where the skill is
    named in the body rather than in the path."""

    parameters: dict[str, str]
    version: int | None = None

    medium: str = "network"
    """`network` replays the calls; `ui` performs the task in a browser."""

    device_id: str | None = None
    """Perform it in this browser -- the operator's own, through the extension --
    rather than in one the deployment owns.

    The call then goes out of a page they are already signed in to, which is how
    a skill runs against a system this deployment holds no credentials for. It
    also means the run cannot outlive the laptop, so it is performed here rather
    than handed to a worker that would retry it into a browser that has gone."""

    may_take_focus: bool = False
    """Whether this run may bring a tab to the front of that browser.

    False unless the caller says otherwise, because the caller is the only one
    who knows whether a person is watching. A console starting a run somebody
    just asked for can say yes; anything firing on a clock says nothing and
    gets no."""

    authorized_by: str | None = None
    """Required above shadow. The human who allowed this run to write."""


class RunFromPreviewRequest(BaseModel):
    """The press. No `authorized_by` field: reading the preview and pressing
    `Do it` is the confirmation, not a second box to tick on top of it."""

    parameters: dict[str, str]

    device_id: str
    """The operator's own browser -- always, not optionally, because the
    preview this promotes on showed them the tab the run is about to act in
    (ADR 014), and a run that then acted somewhere else would not be the run
    they read."""

    intent: str = ""
    """The sentence the operator typed. Carried onto `Run.intent` unchanged --
    see that field for why there is no second place it is kept."""

    version: int
    """The version number the panel actually previewed.

    Required, and not defaulted to "the latest": ADR 014's whole argument is
    that what was on the screen when the operator pressed `Do it` is, line for
    line, what the run is about to do, and a press that could not name which
    version it read cannot make that claim. The backend refuses this run
    outright if the skill has moved on since -- it neither falls forward to a
    version nobody read nor back to one somebody has since replaced."""


class StepOutcomeModel(BaseModel):
    index: int
    medium: str
    disposition: str
    intent: str
    method: str | None
    url: str | None
    status_code: int | None
    idempotency_key: str | None
    request_body: str | None = None
    """The body a write produced: what a withheld step would have sent, or what
    a performed one did send. Writes only -- a read's body is not reviewed."""

    assertion_failures: list[str]
    escalated_from: str | None
    escalation_reason: str | None
    matched_by: str | None
    detail: str | None

    plan_step: int = 0
    """Which step of the version this was. The same number as `index` unless
    the skill has a loop, whose body occupies several positions in the log."""

    iteration: int = 0
    """Which time round the loop, for a screen that says "line 2 of 3"."""

    found_rows: int | None = None
    found_total: int | None = None
    """How many exist, where the system said. `found_rows` is what this page
    carried, and the two are not the same question."""

    found_partial: bool = False
    """How many records a read returned — the answer, when the question was a
    question. A step that reports only a status code has answered nothing."""

    found: list[dict[str, str]] = []
    found_columns: list[str] = []
    found_values: dict[str, list[str]] = {}
    """A few values each column holds. What the next question can be about."""
    """The result's columns, in the order to show them."""

    found_labels: list[str] = []
    """Each record as one readable line, ranked before storage."""

    @classmethod
    def of(cls, step: StepOutcome) -> StepOutcomeModel:
        return cls(
            index=step.index,
            medium=step.medium.value,
            disposition=step.disposition.value,
            intent=step.intent,
            method=step.method,
            url=step.url,
            status_code=step.status_code,
            idempotency_key=step.idempotency_key,
            request_body=step.request_body,
            assertion_failures=list(step.assertion_failures),
            escalated_from=step.escalated_from.value if step.escalated_from else None,
            escalation_reason=step.escalation_reason,
            matched_by=step.matched_by,
            plan_step=step.step_index,
            iteration=step.iteration,
            detail=step.detail,
            found_rows=step.found_rows,
            found_total=step.found_total,
            found_partial=step.found_partial,
            found=[dict(row) for row in step.found],
            found_columns=list(step.found_columns),
            found_values={key: list(values) for key, values in step.found_values},
            found_labels=list(step.found_labels),
        )


class CalledWrongRequest(BaseModel):
    because: str = Field(min_length=1, max_length=500)
    """Why it was wrong. "undone by the operator" where they pressed undo, or
    what they typed. Kept because "I took it back" and "the priority was wrong"
    are different things to read a month later."""


class ReversalModel(BaseModel):
    """What would take back what this run made, where anything would."""

    skill_id: str

    version: int
    """The version the undo was found on and validated against. Sent back
    unchanged on the press, so the run that reverses is the one that was
    offered -- see `RunFromPreviewRequest.version`."""

    removes: str
    """What the delete step says it does, in the demonstration's own words.
    Shown beside the identifying values below, before `Undo that` is pressed:
    one press is the design, and one press that never named what it was about
    to delete is not."""

    parameters: dict[str, str]

    @classmethod
    def of(cls, reversal: Reversal) -> ReversalModel:
        return cls(
            skill_id=reversal.skill_id.value,
            version=reversal.version,
            removes=reversal.removes,
            parameters=reversal.parameters,
        )


class RunModel(BaseModel):
    id: str
    skill_id: str
    skill_version: int
    stage: str
    medium: str
    device_id: str | None = None
    status: str
    parameters: dict[str, str]
    derived: dict[str, str]
    """Values read out of the system as the run went. The audit answer to "what
    did it actually send", which the parameters alone cannot give."""

    requested_by: str
    authorized_by: str | None
    started_at: datetime
    ended_at: datetime | None
    failure: str | None
    wrong_because: str | None = None
    """Set once the person this ran for says the result was wrong. Null is the
    ordinary case and is not a verdict; nothing is asked after a run."""

    intent: str = ""
    """The sentence the operator typed to ask for this run. Empty for a console
    run, a batch, or a trigger firing on its own -- nobody typed one."""

    reversal: ReversalModel | None = None
    """What would undo this run, where the panel found three facts that say
    one does: a write, a runnable skill that deletes that same shape, and the
    identifier it needs, already read back. Null is not "no", it is "not
    computed here" -- only the single-run read fills it in, because it needs
    the tenant's skill library and the list of runs must not pay for that on
    every row."""

    steps: list[StepOutcomeModel]

    @classmethod
    def of(cls, run: Run, *, reversal: Reversal | None = None) -> RunModel:
        return cls(
            id=run.id.value,
            skill_id=run.skill_id.value,
            skill_version=run.skill_version,
            stage=run.stage.value,
            medium=run.medium.value,
            device_id=run.device_id.value if run.device_id else None,
            status=run.status.value,
            parameters=dict(run.parameters),
            derived=dict(run.derived),
            requested_by=run.requested_by.value,
            authorized_by=run.authorized_by.value if run.authorized_by else None,
            started_at=run.started_at,
            ended_at=run.ended_at,
            failure=run.failure,
            wrong_because=run.wrong_because,
            intent=run.intent,
            reversal=ReversalModel.of(reversal) if reversal is not None else None,
            steps=[StepOutcomeModel.of(step) for step in run.steps],
        )


class SessionHeadersRequest(BaseModel):
    facility: str
    headers: dict[str, str]
    """Header name to value. Values go straight to the vault."""


class SessionHeadersResponse(BaseModel):
    stored: list[str]
    """Key names only. A credential is never echoed back."""


class CandidateModel(BaseModel):
    skill_id: str
    name: str
    version: int
    stage: str
    summary: str
    score: int
    why: list[str]
    unexplained: list[str]


def _candidate(candidate: Candidate | None) -> CandidateModel | None:
    if candidate is None:
        return None
    return CandidateModel(
        skill_id=candidate.skill.id.value,
        name=candidate.skill.name,
        version=candidate.version.version,
        stage=candidate.version.stage.value,
        summary=candidate.version.summary,
        score=candidate.score,
        why=list(candidate.why),
        unexplained=list(candidate.unexplained),
    )


class SayRequest(BaseModel):
    text: str
    system: str | None = None
    parameters: dict[str, str] = Field(default_factory=dict)

    run_id: str | None = None
    """Set when this was typed at a run that is happening, rather than asked of
    the system. Such a sentence is kept beside that run and resolved against
    nothing: putting "use the north yard address" through intent matching finds
    some other skill and offers to run it."""

    answering: str | None = None
    """The id of the question this answers, when it was pressed under one. The
    answer acts on that question's offer and no other; a question that is no
    longer open is answered with a refusal, never with another offer."""


class MessageModel(BaseModel):
    id: str
    speaker: str
    text: str
    said_at: datetime
    decision: dict[str, Any]
    """What the system worked out, beside what it said. An auditor reads this
    rather than the prose."""


class ThreadSummary(BaseModel):
    id: str
    title: str
    opened_by: str
    opened_at: datetime
    message_count: int

    @classmethod
    def of(cls, thread: Thread) -> ThreadSummary:
        return cls(
            id=thread.id.value,
            title=thread.title,
            opened_by=thread.opened_by.value,
            opened_at=thread.opened_at,
            message_count=len(thread.messages),
        )


class ThreadDetail(ThreadSummary):
    messages: list[MessageModel]

    @classmethod
    def of_thread(cls, thread: Thread) -> ThreadDetail:
        return cls(
            **ThreadSummary.of(thread).model_dump(),
            messages=[
                MessageModel(
                    id=message.id.value,
                    speaker=message.speaker.value,
                    text=message.text,
                    said_at=message.said_at,
                    decision=dict(message.decision),
                )
                for message in thread.messages
            ],
        )


class TaughtSkillModel(BaseModel):
    skill_id: str
    name: str
    system: str
    facility: str
    version: int
    stage: str
    taught_by: str
    taught_at: str
    clean_streak: int
    proposed_parameters: int


class KnowledgeSummaryModel(BaseModel):
    """What this organisation knows, and how it got there."""

    system_counts: dict[str, int]
    kind_counts: dict[str, int]
    evidence_counts: dict[str, int]
    learned_from_runs: int
    """Claims proved by this tenant's own runs rather than scraped. The number
    that says the system is learning rather than merely loaded."""

    superseded: int
    skills: list[TaughtSkillModel]


class KnowledgeEntryModel(BaseModel):
    id: str
    system: str
    kind: str
    key: str
    title: str
    source: str
    evidence: str
    observed_at: datetime
    body: dict[str, Any]


class ProblemModel(BaseModel):
    """An RFC 9457 problem document, as `errors.py` writes them.

    Declared so the generated client knows the shape. It did not: every failure
    reached the browser as whatever the success model said it should be, and a
    404 was read as a SkillDetail with every field missing.
    """

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None


def _problem(description: str) -> dict[str, Any]:
    """Declared with the media type it is really sent as. RFC 9457 says
    ``application/problem+json``, and a client generated against
    ``application/json`` does not know these documents exist."""
    return {
        "description": description,
        "content": {"application/problem+json": {"schema": ProblemModel.model_json_schema()}},
    }


PROBLEMS: dict[int | str, dict[str, Any]] = {
    401: _problem("No credential, or one this deployment rejects."),
    404: _problem("No such thing, or not yours."),
    409: _problem("The system's state says no, not the request."),
    422: _problem("The request cannot be processed as asked."),
    503: _problem("Something this depends on is unavailable."),
}
"""What every v1 operation may answer with besides its own model.

Declared once for the whole surface rather than per route. Slightly generous --
a POST that creates a thread will not 404 -- and that is the right trade against
the alternative these replaced, which was declaring none of them anywhere.
"""

TOO_LARGE: dict[int | str, dict[str, Any]] = {
    413: _problem("The request is larger than this door accepts."),
}
"""Declared per route rather than added to ``PROBLEMS``.

Two doors have a size belt on them -- the observation batch and the artifact
upload -- and every other operation in v1 has none. Putting 413 in the shared
table would promise it on forty doors that cannot answer it, which is a lie a
generated client would carry.
"""


class ObservationPolicyModel(BaseModel):
    """What the extension is allowed to do. Read on registration, and again only
    when the version it holds falls behind."""

    version: int
    capture_enabled: bool
    exclude_hosts: list[str]
    include_hosts: list[str]
    capture_screenshots: bool
    screenshot_max_per_minute: int
    capture_response_bodies: bool
    max_body_bytes: int
    daily_budget_bytes: int
    retention_days: int

    @classmethod
    def of(cls, policy: ObservationPolicy) -> ObservationPolicyModel:
        return cls(
            version=policy.version,
            capture_enabled=policy.capture_enabled,
            exclude_hosts=list(policy.exclude_hosts),
            include_hosts=list(policy.include_hosts),
            capture_screenshots=policy.capture_screenshots,
            screenshot_max_per_minute=policy.screenshot_max_per_minute,
            capture_response_bodies=policy.capture_response_bodies,
            max_body_bytes=policy.max_body_bytes,
            daily_budget_bytes=policy.daily_budget_bytes,
            retention_days=policy.retention_days,
        )


class RegisterDeviceRequest(BaseModel):
    label: str = Field(max_length=200)
    """Human-readable, and the idempotency key: the same operator registering
    the same label twice is the same device."""

    extension_version: str = Field(default="", max_length=32)


class RegisteredDeviceResponse(BaseModel):
    device_id: str
    device_secret: str
    """What this browser presents on every device-scoped call after this one.

    Said here and nowhere else: it is not on `DeviceModel`, so the screen that
    lists whose browsers are observed cannot hand one browser another's. Said
    on every registration rather than only the first, because registration is
    idempotent on (tenant, principal, label) and a reinstall that could not get
    its secret back would be a device somebody had to delete by hand.
    """

    policy: ObservationPolicyModel
    policy_version: int


K_SAID_LINES = 50
"""How many lines one beat may carry. A beat a minute and fifty lines is more
than a busy browser produces; a browser that produces more is one whose loudest
lines are the ones worth having."""

K_SAID_CHARS = 300
"""How long one of them may be."""


class HeartbeatRequest(BaseModel):
    queued_events: int = 0
    queued_bytes: int = 0
    policy_version: int | None = None
    """What the device holds. The policy comes back only when this is behind."""

    said: list[str] = Field(default_factory=list, max_length=K_SAID_LINES)
    """What the browser decided since the last beat, in its own words.

    The extension had no way to say anything. `run_workflow` narrates every
    rung it climbs and the deployment's log reads like a transcript; the
    browser half of the same run was a black box, and the only place its
    reasoning existed was a service worker console nobody can reach remotely
    -- not from a server, not from another machine, and not by the person
    debugging at two in the morning who has already been asked twice.

    Measured over 2026-09-17: four consecutive faults were found from the
    backend log within one run each, and the one fault that lived in the
    extension took four runs and was still not found.

    Lines, not events: this is for reading, and a schema would make it a
    protocol nobody can add a sentence to. Bounded hard on both counts because
    a browser is not a trusted writer -- a loop in the extension must not be
    able to fill a disk.
    """


class HeartbeatResponse(BaseModel):
    policy_version: int
    policy: ObservationPolicyModel | None
    pause: bool
    """The administrator's switch. Distinct from the operator's own pause, which
    lives in the browser and is theirs to hold."""


class DeviceModel(BaseModel):
    """Whose browser is being observed, and whether we are hearing from it."""

    id: str
    principal_id: str
    label: str
    extension_version: str
    registered_at: datetime
    last_seen_at: datetime
    paused: bool
    queued_events: int
    queued_bytes: int
    uploads: int
    online: bool
    """A command channel open right now, and never true of a revoked browser.

    The question this list is actually read to answer. It is not on
    `AgentDevice` because it is not a fact about a row -- it is a fact about a
    wire, which only `AgentDrivers` knows.
    """

    @classmethod
    def of(cls, device: AgentDevice, *, online: bool) -> DeviceModel:
        return cls(
            online=online,
            id=device.id.value,
            principal_id=device.principal_id.value,
            label=device.label,
            extension_version=device.extension_version,
            registered_at=device.registered_at,
            last_seen_at=device.last_seen_at,
            paused=device.paused,
            queued_events=device.queued_events,
            queued_bytes=device.queued_bytes,
            uploads=device.uploads,
        )


class DeviceLineModel(BaseModel):
    """One browser on the roster: who registered it, when its authority ended
    if it did, and whether it is connected right now.

    `revoked_at` is why a revoked browser stays on this list rather than
    disappearing from it. This is the list read before cutting one off and
    after, and a revocation that erased its own subject would leave an
    administrator unable to confirm the thing they just did.

    A string, not a `datetime`, because that is what `AgentDevice.revoked_at`
    is -- the instant is written by whoever revoked and read back verbatim, and
    re-parsing it here would invent a timezone the row did not record.
    """

    device_id: str
    principal_id: str
    label: str
    registered_at: datetime
    last_seen_at: datetime
    revoked_at: str | None
    online: bool

    @classmethod
    def of(cls, line: DeviceLine) -> DeviceLineModel:
        return cls(
            device_id=line.device.id.value,
            principal_id=line.device.principal_id.value,
            label=line.device.label,
            registered_at=line.device.registered_at,
            last_seen_at=line.device.last_seen_at,
            revoked_at=line.device.revoked_at,
            online=line.online,
        )


class RosterResponse(BaseModel):
    devices: list[DeviceLineModel]

    @classmethod
    def of(cls, roster: tuple[DeviceLine, ...]) -> RosterResponse:
        return cls(devices=[DeviceLineModel.of(line) for line in roster])


class RevocationResponse(BaseModel):
    """`moved` rather than `revoked`: this one answer serves both presses, and
    what it says is whether *this* press changed the row -- not what state the
    browser is now in, which the roster answers."""

    device_id: str
    moved: bool


class ShapesResponse(BaseModel):
    shapes: list[dict[str, object]]
    """The rig answered `{"shapes": [...]}` and the extension reads that key.

    An object rather than a bare list so a later field -- a server clock, a
    next-poll hint -- does not have to break the extension to be added.

    `dict[str, object]` and not a model per field: a `Shape` is the extension's
    matching input, `as_json` is `asdict` over it, and a second declaration of
    the same fields here is the copy that goes stale the first time the domain
    gains one.
    """

    can_find: bool = False
    """Whether a run of one of these can go and find a value nobody typed.

    Here, on the response rather than on each shape, because it is a fact about
    the DEPLOYMENT and not about a job: the same mailbox and the same model
    serve every one of them.

    The browser needs it to draw an offer honestly. A card built from a
    sentence already says "I will look in your mail for the rest" -- that
    answer came back from the chat door, which knows. A card built from a
    PREFIX MATCH is built in the browser out of shapes, and without this it
    demanded every missing value and left its own button disabled: the same
    job, offered two ways, disagreeing about whether it needs you to type."""

    takes_over: bool = False
    """Whether a press of one of these starts a server (Steel) run, which takes
    the job over from where the operator got to and reads what they already
    did from this browser's uploads.

    A fact about the tenant's rollout, not about a job. The browser needs it to
    know whether a press is worth waiting on its own uploads for: a run the
    browser drives itself reads no evidence, and a Steel run that cannot see a
    save still in the queue has to ask about it rather than know."""


class RecordOfferRequest(BaseModel):
    """What a browser showed, and what became of it.

    No `device_id`. The rig read one out of this body; here the browser is the
    one that proved itself with `X-Device-Secret`, for `/v1/shapes`' reason
    next door -- a job's rest is per browser, so a body that could name
    another browser could spend that browser's rest, or earn it.

    `k` is `StrictInt`, which is the whole of why this is not a plain `int`:
    `True` IS an `int` in Python and pydantic coerces it, so `{"k": true}`
    would be stored as a tail that matched one gesture -- because the language
    says so, and not because any browser matched anything. The rig hit exactly
    this on `from_step`. `ge=0` for the rest of it: k is how many gestures
    matched, and no tail matches a negative number of them.

    `at` is the browser's own reading of when it showed the offer, parsed here
    rather than in the application layer so that a clock nobody can read is a
    422 naming the field rather than a 500 out of `datetime.fromisoformat`.
    Optional: absent, the row carries the server's instant.
    """

    workflow_id: str
    fate: str
    k: StrictInt = Field(ge=0)
    run_id: str | None = None
    at: datetime | None = None


class OfferRecordedResponse(BaseModel):
    offer_id: str
    """The rig answered `{"offer_id": ...}` and the extension reads that key.

    The id and not the row: everything else in it is either what the caller
    just sent or the clamp on their own clock, and `/v1/audit` serves the
    stored offer whole to the one caller -- the tenant -- who reads offers
    back.
    """


class AuditStepModel(BaseModel):
    """One step of a run as the audit reads it, with the approval that let it out.

    `sent` is the *kind* of command that was planned and never its payload.
    Ported from the rig's `sent.get("kind")`, and kept for a reason of its own:
    the payload is a warehouse's own data -- an order number, a client's name --
    and this list is read on a console screen by whoever holds a tenant
    credential. What an audit has to answer is that a click on Save went out at
    09:11, and the run's own row is where the rest lives.

    `order` and not the rig's `ord`, which was its column name: the field is
    `RunStep.order` here and a wire name that disagrees with the domain is the
    kind of thing that gets read back into the wrong one.

    The approval is folded onto its step although `AuditedRun` keeps approvals
    beside the run. That separation is about the record -- a `RunStep` the
    runner saves back must not be able to carry somebody's approval in it --
    and nothing saves a wire model back.
    """

    order: int
    """Where in the RUN this row sits, unique within it. The same number as
    `of_step` for a job that does one thing once, which is most of them."""

    of_step: int
    item: int | None
    """Which step of the JOB, and which thing on the list it was done for --
    null for a step done once. What a panel says "item 3 of 5" from."""

    says: str
    verdict: str
    verdict_by: str
    reason: str
    sent: str | None
    matched_by: str | None
    stale: bool
    approved_at: str | None
    approved_by: str | None

    @classmethod
    def of(cls, step: RunStep, approval: tuple[str, str | None] | None) -> AuditStepModel:
        at, by = approval or (None, None)
        kind = (step.sent or {}).get("kind")
        return cls(
            order=step.order,
            of_step=step.of_step,
            item=step.item,
            says=step.says,
            verdict=step.verdict,
            verdict_by=step.verdict_by,
            reason=step.reason,
            sent=None if kind is None else str(kind),
            matched_by=step.matched_by,
            stale=step.stale,
            approved_at=at,
            approved_by=by,
        )


class AuditedRunModel(BaseModel):
    """One run, its steps' verdicts, and what each of them cost."""

    id: str
    workflow_id: str
    device_id: str
    started_by: str
    live: bool
    started_at: str
    finished_at: str | None
    outcome: str
    cost_usd: float
    unpriced: bool
    """True where a call returned without a bill. A run whose cost is 0.0 and
    whose `unpriced` is true did not cost nothing; nobody could say."""

    steps: list[AuditStepModel]

    @classmethod
    def of(cls, audited: AuditedRun) -> AuditedRunModel:
        approved = {order: (at, device_id) for order, at, device_id in audited.approvals}
        run = audited.run
        return cls(
            id=run.id,
            workflow_id=run.workflow_id,
            device_id=run.device_id,
            started_by=run.started_by,
            live=run.live,
            started_at=run.started_at,
            finished_at=run.finished_at,
            outcome=run.outcome,
            cost_usd=run.cost_usd,
            unpriced=run.unpriced,
            steps=[AuditStepModel.of(step, approved.get(step.order)) for step in run.steps],
        )


class AuditOfferModel(BaseModel):
    id: str
    workflow_id: str
    device_id: str
    k: int
    fate: str
    run_id: str | None
    at: str

    @classmethod
    def of(cls, offer: Offer) -> AuditOfferModel:
        return cls(
            id=offer.id,
            workflow_id=offer.workflow_id,
            device_id=offer.device_id,
            k=offer.k,
            fate=offer.fate,
            run_id=offer.run_id,
            at=offer.at,
        )


class AuditDeviceModel(BaseModel):
    """Which browser could act, and from when to when.

    `registered_at` where the rig said `issued_at`: there a device held a token
    of its own and the row was that token's, here the browser registers once and
    is handed a secret, so registration IS the moment its authority began.

    No `online`: what `DeviceLineModel` next door reports is a socket held right
    now, which is a fact about this second and not about the window asked for.
    """

    device_id: str
    registered_at: datetime
    revoked_at: str | None

    @classmethod
    def of(cls, device: AgentDevice) -> AuditDeviceModel:
        return cls(
            device_id=device.id.value,
            registered_at=device.registered_at,
            revoked_at=device.revoked_at,
        )


class AuditChatModel(BaseModel):
    """The chat door, used: when, for which job, at what cost.

    The sentence is not here because it was never kept -- it is an operator's
    words about their warehouse, and the record exists for the bill.
    """

    id: str
    workflow_id: str | None
    cost_usd: float
    unpriced: bool
    error: str | None
    at: str

    @classmethod
    def of(cls, reading: ChatReading) -> AuditChatModel:
        return cls(
            id=reading.id,
            workflow_id=reading.workflow_id,
            cost_usd=reading.cost_usd,
            unpriced=reading.unpriced,
            error=reading.error,
            at=reading.at,
        )


class AuditAttemptModel(BaseModel):
    """Something somebody asked for, and what came of it.

    The four models beside this one are state that already existed; this one is
    the press that started nothing, which had no row anywhere until it did.
    """

    id: str
    at: str
    asked_for: str
    came_of: str
    principal: str
    why: str
    about: dict[str, str]

    @classmethod
    def of(cls, attempt: Attempt) -> AuditAttemptModel:
        return cls(
            id=attempt.id,
            at=attempt.at,
            asked_for=attempt.asked_for,
            came_of=attempt.came_of,
            principal=attempt.principal,
            why=attempt.why,
            about=dict(attempt.about),
        )


class AuditResponse(BaseModel):
    since: str
    """The bound the four reads actually used, normalised to UTC.

    Not the caller's query echoed back. A caller that passed a naive time is
    told, here, what that was taken to mean; a route that echoed the query
    would name a window it had not read, and the two look identical to anyone
    who passed an offset already.
    """

    runs: list[AuditedRunModel]
    offers: list[AuditOfferModel]
    devices: list[AuditDeviceModel]
    chats: list[AuditChatModel]
    attempts: list[AuditAttemptModel] = Field(default_factory=list)
    """Newest first, and defaulted: a console written against the other four
    goes on working."""

    @classmethod
    def of(cls, audit: Audit) -> AuditResponse:
        return cls(
            since=audit.since,
            runs=[AuditedRunModel.of(run) for run in audit.runs],
            offers=[AuditOfferModel.of(offer) for offer in audit.offers],
            devices=[AuditDeviceModel.of(device) for device in audit.devices],
            chats=[AuditChatModel.of(chat) for chat in audit.chats],
            attempts=[AuditAttemptModel.of(one) for one in audit.attempts],
        )


class SpendResponse(BaseModel):
    """What the day has cost, whether that figure can be trusted, and the cap.

    Three numbers rather than one. `cost_usd` alone cannot tell an
    honestly-cheap morning from one whose bills were never priced, and a
    number with no cap beside it cannot answer "am I about to be cut off",
    which is the question this door is opened for.
    """

    cost_usd: float
    """Since midnight UTC, over all four tables a model call bills to,
    rounded where the rig rounded it."""

    unpriced: int
    """How many of today's calls could not be priced -- a count, as the rig
    answered it and as `DaySpend.blind` carries it, not a flag.

    Reported beside the total and never folded into it: a model name the price
    table never knew about records $0.0000 with `unpriced` set, so a day
    summed on `cost_usd` alone reads as free while it spends. The count and
    not a boolean because the 429 the cap raises quotes it, and a console that
    could only say "something" cannot say what to go and look for.
    """

    cap_usd: float
    """What this deployment configured, not what the code shipped with."""

    @classmethod
    def of(cls, day: DaySpend, *, cap_usd: float) -> SpendResponse:
        return cls(cost_usd=round(day.cost_usd, 6), unpriced=day.blind, cap_usd=cap_usd)


class WorkflowHistoryModel(BaseModel):
    """What has become of one job: how often it ran, how often it held, whether
    its page is moving under it, and whether its writes go unasked now.

    Four fields where the rig answered seven. `last`, the offer fates and the
    counsel derived from them are served already -- by `/v1/audit` and
    `/v1/shapes` -- and a second door onto a field is a second place it is
    computed. `sro.application.skill.read_workflows` carries the whole of that
    reasoning.
    """

    total: int
    held: int
    stale: int
    """Steps a run last matched through a weak locator. This route is the only
    reader `mark_stale` has."""

    earned: bool
    """Whether this job may write without asking a person first. Never derived
    from `held` beside it: a hundred held runs with nothing in the register
    have earned nothing."""

    proven: int
    """Runs counted toward `earned`, out of `needed`: the side panel draws the
    job's way to writing on its own as "2 of 3"."""

    needed: int


class WorkflowStepModel(BaseModel):
    """One mined step: what it says, and the evidence that proves it.

    `order` and not the rig's `ord`, which was its column name -- as
    `AuditStepModel` above does, and for the same reason.
    """

    order: int
    says: str
    system: str | None
    cites: list[str]
    parameters: list[str]
    tab: str
    """The tab of the run it acts in: `main`, `opened_from:<role>` for a tab
    a click opened, or `tab_2`, ... for another tab the operator opened."""


class ReasonModel(BaseModel):
    """One reason a job cannot run: what is missing, and at which step (None for the job)."""

    code: str
    step: int | None
    detail: str


class WorkflowModel(BaseModel):
    id: str
    title: str
    narrative: str
    systems: list[str]
    pass_id: str
    """The pass that found it, rather than a per-workflow price. One model call
    proposes every workflow in a pass, so a copy of its cost on each of them
    sums to the bill times the number of jobs found."""

    parameters: list[dict[str, Any]]
    """What the pass could not place. It exists nowhere else a reader can
    reach, and it is the field a route emitting its siblings is likeliest to
    drop."""

    steps: list[WorkflowStepModel]
    runs: WorkflowHistoryModel
    runnable: bool
    """Whether the compile check passes. Only a runnable job is offered to a request."""

    reasons: list[ReasonModel]
    """Why it cannot run, empty when it can."""

    offered: bool
    """Whether the chat would offer it: a real job, not a chore, a mail-only
    doing or a fragment, and the one copy of its title (`real_jobs`). The
    panel lists only these; the console reads every job."""

    warnings: list[ReasonModel]
    """What a reader should know although the job runs: values fixed at
    recording (`fixed_values`), every lane failing lately (`every_lane_broken`)."""

    @classmethod
    def of(cls, known: KnownWorkflow) -> WorkflowModel:
        workflow = known.workflow
        return cls(
            id=workflow.id,
            title=workflow.title,
            narrative=workflow.narrative,
            systems=list(workflow.systems),
            pass_id=workflow.pass_id,
            parameters=[dict(entry) for entry in workflow.parameters],
            steps=[
                WorkflowStepModel(
                    order=step.order,
                    says=step.says,
                    system=step.system,
                    cites=list(step.cites),
                    parameters=list(step.parameters),
                    tab=step.role,
                )
                for step in sorted(workflow.steps, key=lambda step: step.order)
            ],
            runs=WorkflowHistoryModel(
                total=known.total,
                held=known.held,
                stale=known.stale,
                earned=known.earned,
                proven=known.proven,
                needed=K_EARNED_RUNS,
            ),
            runnable=known.compiled.runnable,
            reasons=[
                ReasonModel(code=one.code, step=one.step, detail=one.detail)
                for one in known.compiled.reasons
            ],
            offered=known.offered,
            warnings=[
                ReasonModel(code=one.code, step=one.step, detail=one.detail)
                for one in known.compiled.warnings
            ],
        )


class WorkflowsResponse(BaseModel):
    workflows: list[WorkflowModel]
    """An object rather than a bare list, as `ShapesResponse` is: a later field
    -- a server clock, a next-page cursor -- should not have to break every
    reader to be added."""

    @classmethod
    def of(cls, known: tuple[KnownWorkflow, ...]) -> WorkflowsResponse:
        return cls(workflows=[WorkflowModel.of(one) for one in known])


class ShotModel(BaseModel):
    """One picture of one gesture, addressed for a browser to fetch.

    The URL is minted per request and expires with `PLAYBACK_TTL`, as a
    recording's playback links do: a link to a picture of somebody's screen
    that outlives the page it was drawn on is a copy nobody is tracking.
    """

    url: str
    content_type: str


class EvidenceResponse(BaseModel):
    """Everything a workflow cites, in the shape a runner's bridge consumes.

    Three maps and not one. `gestures` is the extension's own wire shape --
    what a runner's bridge reads a replayable plan out of -- and a
    gesture on the wire never carried its calls, so folding them in would give
    the bridge a shape neither side speaks. `requests` is keyed by gesture id
    beside it, as the rig served it and as the two are stored.

    `dict[str, Any]` per gesture and not a model per field, for
    `ShapesResponse`'s reason: the domain's dataclass is the declaration, and a
    second copy of its fields here goes stale the first time it gains one.
    """

    gestures: dict[str, dict[str, Any]]
    requests: dict[str, list[dict[str, Any]]]
    recordings: list[str]
    """The distinct capture streams those gestures arrived on, oldest first.
    The one input a caller would otherwise have to reach into a column for:
    `Provenance` needs it, and getting it wrong there mis-states whether a
    skill's values were ever diffed."""

    missing: list[str]
    """Cited gesture ids the store no longer holds, in cited order.

    The rig served this and the port dropped it. A bridge skips a citation
    with no gesture, so a caller building a runnable job out
    of this body gets one silently missing a step -- and is entitled to know
    before it runs it. Normally empty: the proposal that became this workflow
    was refused if it cited evidence that did not exist, so a non-empty
    `missing` means the store moved after the job was kept."""

    shots: dict[str, ShotModel] = {}
    """What the screen looked like, keyed by gesture id.

    A gesture nobody photographed has no entry rather than a null one: the
    recorder's per-minute cap, a background tab, a batch the server filtered.
    A key carrying nothing would have the console draw a broken picture where
    there was never one to draw."""

    @classmethod
    def of(
        cls, evidence: CitedEvidence, *, shots: Mapping[str, PlayableShot] | None = None
    ) -> EvidenceResponse:
        served: dict[str, dict[str, Any]] = {}
        calls: dict[str, list[dict[str, Any]]] = {}
        for gesture in evidence.gestures:
            whole = asdict(gesture)
            calls[gesture.id] = whole.pop("requests")
            whole.pop("tenant")
            served[gesture.id] = whole
        return cls(
            gestures=served,
            requests=calls,
            recordings=list(evidence.recordings),
            missing=list(evidence.missing),
            shots={
                gesture_id: ShotModel(url=shot.url, content_type=shot.content_type)
                for gesture_id, shot in (shots or {}).items()
            },
        )


class ObservationBatchRequest(BaseModel):
    batch_id: str = Field(max_length=64)
    """Minted by the extension so a retried upload is recognised as the one it
    already sent."""

    device_id: str = Field(max_length=64)
    started_at: datetime
    ended_at: datetime
    mode: Literal[CaptureMode.PASSIVE] = CaptureMode.PASSIVE
    """The only value this door accepts. `CaptureMode.TEACHING` still exists
    for reading rows a deployment received before the device-teaching path
    was removed -- see its own note -- but no wire input may carry it."""

    events: list[dict[str, Any]]
    """Screened, not parsed, and stored verbatim. The shapes are in
    docs/14-extension-protocol.md; what the domain refuses comes back in
    ``problems`` rather than being dropped in silence."""


class RejectedEventModel(BaseModel):
    index: int
    reason: str

    @classmethod
    def of(cls, rejected: RejectedEvent) -> RejectedEventModel:
        return cls(index=rejected.index, reason=rejected.reason)


class ObservationAcceptedResponse(BaseModel):
    batch_id: str
    accepted: int
    rejected: int
    problems: list[RejectedEventModel]
    stored_at: str | None
    already_had_it: bool
    snapshots_ignored: int = 0
    """Snapshots stored and read by nothing. The rig's own 202 carries this
    key (`new_agent_arch/src/rig/api.py:534`) and for the same reason the
    rejections are here: a browser shipping evidence nothing reads should learn
    it from the answer."""


class ObservationArtifactResponse(BaseModel):
    uri: str
    size_bytes: int


class ForgottenResponse(BaseModel):
    batches: int
    events: int
    artifacts: int = 0


class LocatorModel(BaseModel):
    """Where a control is, in the four fields the extension already speaks.

    Not a new shape: this is exactly what a step handed down the command
    channel carries, so the side that resolves it needs no second parser.
    ``query`` is a plain string here and a template underneath -- a locator may
    name the very record a run is about.
    """

    strategy: LocatorStrategy
    query: str
    within: str | None = None
    """Component query the match must sit inside. The same screen is often
    loaded several times over and only one instance is visible."""

    visible_only: bool = True

    def to_domain(self) -> ControlLocator:
        return ControlLocator(
            strategy=self.strategy,
            query=Template(self.query),
            within=self.within,
            visible_only=self.visible_only,
        )

    @classmethod
    def of(cls, locator: ControlLocator) -> LocatorModel:
        return cls(
            strategy=locator.strategy,
            query=locator.query.raw,
            within=locator.within,
            visible_only=locator.visible_only,
        )


class TermModel(BaseModel):
    """A header, and the operator's own text to find in it.

    Both halves, always. A matcher that knew only which header to look at would
    match every mail that has one, which is all of them.
    """

    field: TermField
    contains: str = Field(max_length=MAX_TERM)
    """Capped for the reason the domain caps it: a paragraph in a term is a
    pasted mail body whatever field it claims to be."""


class ValueAtModel(BaseModel):
    """A parameter, and where in a matching mail to read it.

    A location and nothing else. The order number is different in every mail,
    so there is nothing to compare against and nothing to store.
    """

    name: str
    where: LocatorModel


class WatchModel(BaseModel):
    """What makes a mail one of these, and where to read the values out of it."""

    host: str
    terms: list[TermModel]
    values: list[ValueAtModel] = Field(default_factory=list)

    sender_at: LocatorModel | None = None
    subject_at: LocatorModel | None = None
    """Where the two headers are, on the client this operator uses. Marked in
    the same act as the values and carried in the same four fields, because
    where a sender is on a page is not derivable -- and a browser that had to
    guess a selector would work on one mail client this quarter."""

    def to_domain(self) -> Watch:
        return Watch(
            host=self.host,
            terms=tuple(Term(field=term.field, contains=term.contains) for term in self.terms),
            values=tuple(
                ValueAt(name=value.name, where=value.where.to_domain()) for value in self.values
            ),
            sender_at=self.sender_at.to_domain() if self.sender_at else None,
            subject_at=self.subject_at.to_domain() if self.subject_at else None,
        )

    @classmethod
    def of(cls, watch: Watch) -> WatchModel:
        return cls(
            host=watch.host,
            terms=[TermModel(field=term.field, contains=term.contains) for term in watch.terms],
            values=[
                ValueAtModel(name=value.name, where=LocatorModel.of(value.where))
                for value in watch.values
            ],
            sender_at=None if watch.sender_at is None else LocatorModel.of(watch.sender_at),
            subject_at=None if watch.subject_at is None else LocatorModel.of(watch.subject_at),
        )


class SecretHeldModel(BaseModel):
    """What was held for one run, and when it is forgotten.

    The key and never the value, exactly as `SecretStoredModel` beside it: a
    door that answered with a password would be one a proxy log keeps.
    """

    key: str
    until: float
    """Epoch seconds. After this the value is gone and the step refuses with
    the key it wanted, which is what an operator who never gave one sees."""


class NewSecretRequest(BaseModel):
    """One value to keep for a run to type, and where it belongs.

    No tenant field: it comes from the credential. A body that named one would
    be a caller choosing whose vault to write into.
    """

    system: str
    """The host this signs into, with or without a scheme. Kept per system and
    not per page: an operator signs in once for a host, and a key per url is
    one they would have to store again the first time the sign-in page carried
    a different query."""

    field: str
    """The control's own name, usually `password`. A step that refused says the
    whole key it looked for, so this is readable off the panel rather than
    guessed at."""

    value: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    """Written to the vault and nowhere else: never answered with, never
    logged, never in the evidence plane. See `v1/routers/secrets`."""

    username: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1, max_length=K_USERNAME_MAX_LEN),
        ]
        | None
    ) = None
    """The account this value signs in as. Given, it is kept for that account
    alone, so two operators, or two systems behind one identity provider,
    never share one. Blank or whitespace-only is refused rather than silently
    dropped."""


class NewSecretOnceRequest(NewSecretRequest):
    """`NewSecretRequest`, plus the run this password was given for.

    `PUT /v1/secrets` has no run: what it stores outlives every run that will
    ever read it. What `POST /v1/secrets/once` holds does not -- it is handed
    to one run and refused to every other, so the run has to be named here
    rather than guessed at the moment a step asks for it.
    """

    run_id: str


class SecretStoredModel(BaseModel):
    """What was stored, named by its key and never by its value."""

    key: str


class NewTriggerRequest(BaseModel):
    skill_id: str | None = None
    workflow_id: str | None = None
    """Name one. `CreateTrigger` refuses two and refuses none, which is the
    same rule `Trigger` keeps -- said here as a refusal a caller can read
    rather than as a 500."""

    kind: TriggerKind = TriggerKind.SCHEDULE
    cron: str | None = None
    """Five fields, in the scheduler's own dialect. `0 7 * * 1-5` is every
    weekday at seven."""

    timezone: str = "UTC"
    """The warehouse's, not the server's. A report due at seven local time runs
    at seven local time in March and in November."""

    parameters: dict[str, str] = Field(default_factory=dict)
    from_message: list[str] = Field(default_factory=list)
    """Which of the skill's parameters whatever fires this may name -- the order
    number in a mail. Inbound only, and everything left out of it stays the
    value the trigger was created with, so a relay cannot redirect a read at a
    facility nobody authorised."""

    watch: WatchModel | None = None
    """What makes a mail one of these, for a trigger the operator's own browser
    evaluates. A watch names the values it supplies by where it reads them, so
    `from_message` stays empty for one: there is no second list."""

    arrival: ArrivalModel | None = None
    """The page whose arrival starts the job, for `kind: "arrival"`. What an
    operator makes by standing on the page an offer is about and saying "do
    this here"."""

    device_id: str | None = None
    """Run it in this operator's browser. Such a run happens only while that
    browser is connected, which is a property of a laptop rather than a fault."""

    medium: Medium = Medium.NETWORK
    authorized_by: bool = False
    """Whether the caller stands behind every run this will start. Required for
    a skill that changes the system, and the name comes from the credential."""

    auto_approve: bool = False
    """Send the writes without asking, every time it fires. A per-trigger
    decision by a named person -- never a default, and never global."""

    may_take_focus: bool = False

    asks: bool = False
    """This watch asks a question rather than running anything: name no skill
    and no job, and mark where in the mail the question is with a value called
    `question`. What comes back is an answer in the panel, never a run."""


class ChangeTriggerRequest(BaseModel):
    enabled: bool
    reason: str = ""
    """Why it was switched off. A trigger nobody remembers disabling gets
    switched back on."""


class ArrivalModel(BaseModel):
    """The page whose arrival starts the job: `host/path`, and nothing else."""

    page: str

    def to_domain(self) -> Arrival:
        return Arrival(page=self.page)

    @classmethod
    def of(cls, arrival: Arrival) -> ArrivalModel:
        return cls(page=arrival.page)


class TriggerModel(BaseModel):
    id: str
    skill_id: str | None = None
    workflow_id: str | None = None
    """What this trigger runs: a taught skill or a mined job, never both and
    never neither. See `Trigger`."""
    kind: str
    asks: bool = False
    """This watch asks a question rather than running anything: the browser
    reads the question out of the mail, looks it up across the systems, and
    shows the answer. The third case of "what does this trigger run" -- a
    skill, a job, or neither because it is a question."""

    cron: str | None
    timezone: str
    parameters: dict[str, str]
    from_message: list[str]
    watch: WatchModel | None
    arrival: ArrivalModel | None = None
    """The page this fires on, for an arrival trigger. The browser reads it and
    evaluates it there: the question is where its operator is standing."""

    device_id: str | None
    medium: str
    enabled: bool
    writes: bool
    authorized_by: str | None
    requires_confirmation: bool
    may_take_focus: bool
    created_by: str
    created_at: datetime
    last_fired_at: datetime | None
    last_run_id: str | None
    disabled_reason: str | None
    inbound_token: str | None
    """What an inbound trigger's mail relay or chat webhook presents back. Only
    ever readable by whoever can already read the trigger -- the same tenant
    boundary that protects everything else here."""

    @classmethod
    def of(cls, trigger: Trigger) -> TriggerModel:
        return cls(
            id=trigger.id.value,
            skill_id=trigger.skill_id.value if trigger.skill_id else None,
            workflow_id=trigger.workflow_id,
            kind=trigger.kind.value,
            asks=trigger.asks,
            cron=trigger.cron,
            timezone=trigger.timezone,
            parameters=dict(trigger.parameters),
            from_message=list(trigger.from_message),
            watch=None if trigger.watch is None else WatchModel.of(trigger.watch),
            arrival=None if trigger.arrival is None else ArrivalModel.of(trigger.arrival),
            device_id=trigger.device_id.value if trigger.device_id else None,
            medium=trigger.medium.value,
            enabled=trigger.enabled,
            writes=trigger.writes,
            authorized_by=trigger.authorized_by.value if trigger.authorized_by else None,
            requires_confirmation=trigger.requires_confirmation,
            may_take_focus=trigger.may_take_focus,
            created_by=trigger.created_by.value,
            created_at=trigger.created_at,
            last_fired_at=trigger.last_fired_at,
            last_run_id=trigger.last_run_id.value if trigger.last_run_id else None,
            disabled_reason=trigger.disabled_reason,
            inbound_token=trigger.inbound_token,
        )


class FiredModel(BaseModel):
    trigger_id: str
    run_id: str | None
    skipped: str | None

    confirmation_id: str | None = None
    """Set where the fire became a card somebody has to answer.

    Without it a relay reading this response cannot tell "a person will decide
    about this" from "nothing happened at all": both answered with a null run
    and no reason to skip, which is the one shape that means neither.
    """


class WatchMatchModel(BaseModel):
    """The offer a recognised mail turns into. Not a run: nothing has started.

    `values` is what the task would run with -- the watch's own parameters with
    the mail's on top, after the trigger dropped every name it never declared.
    There is no field here for why it matched, because the browser that asked
    is the one that decided, and a reason travelling back would be mail content
    that had to have crossed to be echoed.

    `missing` is what the skill needs that this mail did not say. The same rule
    the fire itself applies, asked before the press instead of after it: an
    offer whose values are short of a required one is a card that says so,
    rather than a button that starts a run which is skipped a moment later for
    a reason nobody sees.
    """

    trigger_id: str
    skill_id: str | None = None
    workflow_id: str | None = None
    """One of the two, because a watch may name a skill or a mined job and the
    press goes to a different door for each."""

    title: str = ""
    """What the thing is called, so a card can say what matched without a
    second call to look the name up."""

    values: dict[str, str]
    missing: list[str]
    can_find: bool = False
    """Whether a missing value stops the press. A deployment that can read the
    operator's mailbox answers one by going and looking, so the card offers the
    run and says what it will look for; one that cannot keeps the old rule and
    says what it needs."""


class WatchingModel(BaseModel):
    devices: int
    batches: int
    events: int
    hours: float


class NoticingModel(BaseModel):
    tasks: int
    by_kind: dict[str, int]


class DoingModel(BaseModel):
    """The mined jobs' runs started in the window.

    `outcomes` counts each run by the outcome it ended with (`held`,
    `stopped`, `refused`, `aborted`, `failed`, or `running` while it still
    is). `rehearsed` is the held runs that were dry and sent nothing.
    """

    runs: int
    rehearsed: int
    outcomes: dict[str, int]


class TaskLineModel(BaseModel):
    id: str
    title: str
    host: str
    kind: str
    steps: int


class SummaryModel(BaseModel):
    """Everything on the overview, derived from rows somebody can open."""

    since: datetime
    watching: WatchingModel
    noticing: NoticingModel
    doing: DoingModel
    tasks: list[TaskLineModel]

    @classmethod
    def of(cls, summary: Summary) -> SummaryModel:
        return cls(
            since=summary.since,
            watching=WatchingModel(**asdict(summary.watching)),
            noticing=NoticingModel(**asdict(summary.noticing)),
            doing=DoingModel(**asdict(summary.doing)),
            tasks=[TaskLineModel(**asdict(line)) for line in summary.tasks],
        )


class LookupRequest(BaseModel):
    """A question, and whether to go and answer it.

    The same two bounds a sentence to `POST /v1/ask` carries and for the same
    reason: this door spends a model call, so the one part of the prompt a
    caller controls is bounded at both ends before anything is asked.
    """

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

    system: str | None = None
    """Narrows the retrieval to one system's knowledge. Absent means all of
    them, which is the point of the door."""

    execute: bool = True
    """False plans and stops. The plan is readable before anything leaves the
    building, and keeping that separable is what lets a person look at where a
    question is about to be asked."""


class LookupModel(BaseModel):
    """One place the answer might be, and why this deployment thinks so."""

    system: str
    how: str
    target: str
    params: dict[str, str]
    why: str
    cites: list[str]

    @classmethod
    def of(cls, lookup: Lookup) -> LookupModel:
        return cls(
            system=lookup.system,
            how=lookup.how,
            target=lookup.target,
            params=dict(lookup.params),
            why=lookup.why,
            cites=list(lookup.cites),
        )


class AskedModel(BaseModel):
    """The question this deployment will not answer by guessing."""

    key: str
    question: str
    options: list[str]
    because: list[str]

    @classmethod
    def of(cls, asked: Asked) -> AskedModel:
        return cls(
            key=asked.key,
            question=asked.question,
            options=list(asked.options),
            because=list(asked.because),
        )


class LookedModel(BaseModel):
    """What one lookup came back with, or why it did not."""

    system: str
    how: str
    target: str
    url: str
    ok: bool
    detail: str
    status: int | None = None
    body: str | None = None
    """The raw body, and only for an answer that is NOT records: a page of
    HTML, one scalar, a screen. Records cross as `read`, because every surface
    that was handed a body parsed it for itself and each of them guessed."""

    read: dict[str, object] | None = None
    """The records, READ -- see `application.lookup.answer.as_seen`. The count the
    system itself stated, the columns that carry a value ranked with code,
    name and description first, the records projected onto them, and the
    sentence that says it in a line."""

    truncated: bool = False
    """The picture a screen lookup takes is deliberately NOT here. It is
    hundreds of kilobytes of base64 per screen, and nothing on this side of the
    wire can read it -- what a picture MEANS is a model's question, and the
    seam that asks one is not this door. `width`, `height` and the page's text
    digest come back instead, which is enough to say the screen came up."""

    seen: dict[str, object] = Field(default_factory=dict)

    @classmethod
    def of(cls, looked: Looked, question: str = "") -> LookedModel:
        """`question` so the answer can answer it. A lookup comes back with a
        collection and the question was usually about one thing in it; which
        records it NAMED is decided in `application.lookup.naming`, once, rather
        than by each surface that draws one."""
        seen = as_seen(
            system=looked.lookup.system,
            target=looked.lookup.target,
            ok=looked.ok,
            detail=looked.detail,
            answer=looked.answer,
            read=looked.read,
            question=question,
        )
        answer = dict(looked.answer)
        return cls(
            system=looked.lookup.system,
            how=looked.lookup.how,
            target=looked.lookup.target,
            url=looked.url,
            ok=looked.ok,
            detail=looked.detail,
            status=seen["status"],
            body=seen["body"],
            read=seen["read"],
            truncated=bool(seen["truncated"]),
            seen={
                name: value
                for name, value in answer.items()
                if name in ("width", "height", "text_digest", "url", "navigated", "duration_ms")
            },
        )


class LookupResponse(BaseModel):
    """Where one question's answer lives, and what came back from there.

    The plan and the answers are both here because a reader needs both: a
    lookup that failed is only readable beside the reason it was planned. The
    bill is here for `ChatResponse`'s reason -- a reading that cost money and
    named nothing is indistinguishable from a question about nothing without
    it.
    """

    question: str
    why: str
    refused: str | None
    asks: AskedModel | None
    lookups: list[LookupModel]
    answers: list[LookedModel]

    error: str | None
    in_tokens: int
    out_tokens: int
    thought_tokens: int
    cost_usd: float
    unpriced: bool

    @classmethod
    def of(cls, planned: Planned, answers: Answers | None = None) -> LookupResponse:
        bill = planned.answer
        return cls(
            question=planned.plan.question,
            why=planned.plan.why,
            refused=planned.refused,
            asks=AskedModel.of(planned.plan.asks) if planned.plan.asks else None,
            lookups=[LookupModel.of(one) for one in planned.plan.lookups],
            answers=[
                LookedModel.of(one, planned.plan.question)
                for one in (answers.looked if answers else ())
            ],
            error=bill.error if bill else None,
            in_tokens=bill.in_tokens if bill else 0,
            out_tokens=bill.out_tokens if bill else 0,
            thought_tokens=bill.thought_tokens if bill else 0,
            cost_usd=bill.cost_usd if bill else 0.0,
            unpriced=bill.unpriced if bill else False,
        )


class ChatResponse(BaseModel):
    """Which job one sentence turned out to be, and what reading it cost.

    An offer, never a start. The form renders `workflow_id` with `values`
    filled in and `missing` asked for; pressing start is a different door.

    The sentence is not echoed back, and that is deliberate rather than
    incidental: `ChatReading` has no column for an operator's words about their
    own warehouse, and a response model carrying them would put them into every
    proxy log and browser history the answer passes through, which is exactly
    what having no column was for.

    The bill is here and it is not in the rig, which answered the three fields
    above and dropped what it had just spent. A reading that cost money and
    named no job is indistinguishable from a sentence about nothing without
    `error` beside it -- and a day summed on `cost_usd` alone reads as free
    while it spends, which is what `unpriced` says.
    """

    workflow_id: str | None
    values: dict[str, str]
    items: list[dict[str, str]]
    """One set of values per thing the operator named, where they named several
    -- "add these three equipment types" is one job done three times. Empty for
    one thing, which is most sentences."""

    missing: list[str]
    """Sorted, out of `understand`: `declared` is a set, and a form whose
    fields reorder between two identical sentences is a form nothing can
    screenshot."""

    error: str | None
    """What the model said went wrong, when something did. A reading that
    failed and a sentence naming no job are the same body without it."""

    in_tokens: int
    out_tokens: int
    thought_tokens: int
    """Inside `out_tokens`, not beside them. Added to them, a reader reports a
    number no invoice will match."""

    cost_usd: float
    """Unrounded, as `MinePassResponse` leaves it: rounding for display is the
    reader's job, and a bill rounded on the way out cannot be summed against
    the `chats` row it came from."""

    unpriced: bool

    cannot_run: list[str]
    """Why the job named cannot run yet, one line per reason; empty when it can.
    A job that cannot run is still named, so the answer is "it cannot, because",
    never "no such job"."""

    @classmethod
    def of(cls, got: Understood) -> ChatResponse:
        return cls(
            workflow_id=got.workflow_id,
            values=dict(got.values),
            items=[dict(item) for item in got.items],
            missing=list(got.missing),
            error=got.answer.error,
            in_tokens=got.answer.in_tokens,
            out_tokens=got.answer.out_tokens,
            thought_tokens=got.answer.thought_tokens,
            cost_usd=got.answer.cost_usd,
            unpriced=got.answer.unpriced,
            cannot_run=list(got.cannot_run),
        )


class AskRequest(BaseModel):
    """What somebody said, with no claim about which kind of thing it is."""

    said: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

    execute: bool = True
    """Carried through to the lookup half. A job never starts from here
    whatever this says -- what comes back is an offer, and the press is a
    different door."""


class AskResponse(BaseModel):
    """Which of the two worlds the sentence turned out to belong to.

    `kind` is answered even when the half it chose found nothing, because
    "which door did this go through" is the question a caller debugging a
    surprising answer actually has.
    """

    kind: str
    """`job` or `lookup`."""

    job: ChatResponse | None = None
    lookup: LookupResponse | None = None


class AnswerRunRequest(BaseModel):
    """The operator's answer to the question a Steel run is waiting on.

    `question_id` is the one the run is asking now (`decision.question_id` on
    the `run_asks` message in the operator's thread); any other id, or an
    answer when nothing is asked, is a 409. The first answer to a question is
    the one kept: a different second answer is a 409, the same one again is
    accepted.

    `value` is given only for a question that asks for a value; for any other
    it must be empty, or the answer is a 409. A password is stored with
    `PUT /v1/secrets`, a one-time code is typed on the page, and a step is
    answered by its `verdict`, so no secret or free text ever rides along.

    A field question (`asks: "field"`, about a value the job has no field
    for) carries the value's `name` and its `choices` on the `run_asks`
    message: the form's fields (each choice names exactly one), a dropdown's
    options, or -- after a fill that failed -- the field itself, to try it
    again. It is answered with one of `choices`, or an empty `value` to leave
    the value out; anything else is a 409.

    A recipient question (`asks: "recipient"`) is a mail job whose draft named
    somebody neither in the conversation nor an address the job was shown
    sending to; its text quotes the draft's address, which came from a model
    reading untrusted mail. It is answered with the address(es) to send to --
    only by the operator who started the run, and only with addresses that
    read cleanly (anything else is a 409). The answer is kept on the job, so
    its next run writes to that address without asking. On a mail job drafted
    for a press (not on Steel) the run waits `stopped`, holding no browser, and
    this answer redrafts it.

    A mail-body question (`asks: "mail_body"`, "What should the mail say?") is
    a mail job whose mail could not be written: the model wrote no body,
    failed, or put in a value nobody gave. It is answered with the words the
    mail should say (up to 2000 characters; every other answer takes 500), only
    by the operator who started the run; an empty answer is a 409. The words
    are the operator's own, trusted: the mail is written again with them. On a
    mail job drafted for a press the refused draft is shown in the question,
    and `yes` uses exactly that draft, checked again, its recipients still
    ones the mail may go to; either way it is shown again as a draft and
    nothing is sent until its Send is pressed. On Steel the mail is written
    again and sent as the step's write.
    """

    question_id: str
    value: str = Field(default="", max_length=K_BODY)
    verdict: WriteVerdict = ""
    """The operator's word on a step the run asked about. `done`: it was done,
    so the step is settled and never tried again. `not_done`: it was not, so
    the run tries it again. Required when the step is a write the run sent
    and nothing confirmed (a 409 without it, and the question stands); never
    given for any question but a step's."""


class TookOverModel(BaseModel):
    """The operator's own doing a Steel run takes over: the browser tab it
    happened in and the recorder times of the first and last gesture the
    match used.

    The server reads the operator's uploaded gestures from that tab in that
    span, and a write counts as theirs only when its own call is among them
    and confirmed it. Anything the uploads cannot prove is left in doubt and
    settled by a read-back or a question, never sent again.

    Whose uploads is proven, not claimed: the press carries the browser's own
    `X-Device-Secret` for the `device_id` it names, and that browser must be
    the pressing operator's. Otherwise it is the 404 an unknown browser gets."""

    tab_id: StrictInt = Field(ge=0)
    since: float = Field(ge=0)
    through: float = Field(ge=0)
    newest: float = Field(ge=0)
    """The recorder time of the newest gesture this browser recorded before the
    press, on any tab. The press is refused until the server has received it:
    work still uploading -- a save in a popup, say -- is otherwise invisible,
    and a Steel run would make that save a second time."""


class StartWorkflowRunRequest(BaseModel):
    """The press: which job, in which browser, with what, live or dry.

    Every divergence from the rig's body at `api.py:1021`, and why:

    * **No `started_by`.** The rig read it out of the body and defaulted it to
      `"form"`. Here it is the authenticated caller: a request that says who
      authorised it is a signature nobody checked, and the audit trail on a
      warehouse write is worth more than that.
    * **No `tenant`.** It never was in the body; the rig had one tenant per
      process. Here it comes off the credential, as it does on every door.
    * **`device_id` stays in the body**, unlike `/v1/offers`, which dropped it
      because a browser proves itself with `X-Device-Secret`. An offer is
      evidence *about* the browser that showed it, so a browser it merely named
      would be a shift nobody worked. A press *names the browser that pressed*
      -- which a Steel tenant's run never drives: `StartWorkflowRun` picks the
      executor by tenant, and the device only records who pressed.

    `live` defaults to false and `allow_focus` to true, both the rig's: a
    missing `live` is not a caller who forgot, it is the default this system
    promises, and a run that may not take focus cannot reach a control the page
    only renders when focused.

    Two checks are here rather than in `StartWorkflowRun`, and both are facts
    about the wire rather than about the job:

    * `values` as `dict[str, str]`. Coerced values, not checked ones, would
      turn `{"clientCode": {...}}` into the string `"{...}"` and type it into
      somebody's form. Pydantic refuses a nested object for a `str` already, so
      an `isinstance` loop next door would be a second answer to a question the
      wire type has answered. Trimming and dropping the blanks is *not* here:
      that decides what the run is performed with, and it lives beside the
      refusal that reads the job's declared parameters.
    * `from_step` as `StrictInt`. `True` is an `int` in Python, so
      `{"from_step": true}` would pass every range check and start a two-step
      job at its second step -- the operator's first step recorded
      `done_by_operator` and never sent, on a job nobody started. Outside
      strict mode pydantic coerces `true` to `1` before anything downstream can
      tell them apart, so this is the only layer where the guard can be made.
      The range itself needs the job's step count and is checked where the job
      is read.
    """

    workflow_id: str
    device_id: str | None = None
    """The browser to drive. Absent for a tenant whose runs start on Steel,
    where no browser of anybody's is driven; for every other tenant a press
    without one is refused as not connected, by the same check that refuses
    a browser that went away."""
    values: dict[str, str] = Field(default_factory=dict)
    items: list[dict[str, str]] = Field(default_factory=list)
    """The things this job is to be done for, where the operator named several
    -- three equipment types in one mail. Typed as `values` is and for the same
    reason: a coerced value would type `{...}` into somebody's form. Empty is
    one thing, which is most presses, and a job with no repeat is handed none
    of them whatever arrives here."""

    undoes_run: str = ""
    """The run this one takes back, where a press on a result card started it.

    The first place two jobs in this system are one piece of work. What it buys
    is that the two can be put side by side, and that a second press can be
    refused: an undo pressed twice is a second delete addressed to a record the
    first one removed. Empty for every press that is not an undo."""

    mail_thread: str = ""
    """The mail conversation this request came out of, where it came out of one.

    An id and nothing anybody wrote. What it buys is an address: a run that
    comes up short can be found again by a reply to that mail, because the
    person who knows the missing value is usually whoever sent the request and
    they are not the one with this panel open. Empty for every press that was
    not a mail offer, which is most of them."""

    offer: str = Field(default="", max_length=128)
    """The offer this press answers: a conversation message, a mail's key, or
    the panel's own card.

    A run records it under a unique index, so a second start of the same offer
    -- a second panel, a typed yes beside a press -- is answered 200 with the
    run the first one started, never a second live write. Empty for a press
    that answers no offer."""

    live: bool = False
    allow_focus: bool = True

    watched: bool = False
    """Whether somebody is standing in front of this run.

    A press in an open panel sends `true` and gets the job done in front of
    them -- the fields fill, the button is pressed. Anything that presses
    without a person there leaves it false and the run replays the call, which
    is faster, deterministic and invisible. Defaults to false because the
    callers that do not say are the ones nobody is watching: a trigger, a
    schedule, a script."""
    from_step: StrictInt = 0
    matched: StrictInt | None = Field(default=None, ge=0)
    """How many shape entries the browser's tail matched, when a browser is
    what pressed.

    A shape entry is one cited GESTURE and `from_step` is a step, and those are
    not the same number: this deployment's `Create a Customer Type` is 19
    entries over 6 steps. `recognise.match` answers in entries and the panel
    used to send that straight in as `from_step`, so every step under it was
    recorded done-by-the-operator and never performed -- and over the step
    count the press was refused outright.

    A separate field rather than a changed meaning, because the console's
    `from_step` really is a step: somebody reading a run and resuming it names
    one. Two callers, two honest numbers. Given both, this one wins, because
    only a browser sends it and only a browser knows what it matched."""
    took_over: TookOverModel | None = None
    """The span of the operator's own gestures `matched` counted, when a
    browser pressed to hand a job it had started to a Steel run. Absent, a
    Steel run is never started part way through."""


class WorkflowRunStepModel(BaseModel):
    """One step of a mined-workflow run, as the panel reads it.

    `sent` and `result` in full, where `AuditStepModel` next door reduces
    `sent` to its kind. The two are read by different people about different
    things: the audit is every run of the tenant on a console screen, and this
    is the one run an operator is watching in their own browser -- the write a
    dry run withheld is the thing they are being asked to approve, and a kind
    with no payload is not something anybody can say yes to.

    `sent` is what was planned and not proof that it went out. A step parked on
    a person carries the command a tap would release, and `verdict ==
    "awaiting"` is what tells the two apart.
    """

    order: int
    """Where in the RUN this row sits, unique within it. The same number as
    `of_step` for a job that does one thing once, which is most of them."""

    of_step: int
    item: int | None
    """Which step of the JOB, and which thing on the list it was done for --
    null for a step done once. What the panel says "item 3 of 5" from."""

    made: dict[str, str]
    """What the warehouse called the record this step created, where it made
    one. `{}` for every step that created nothing, which is most of them -- and
    what a person needs in order to go and look at what a run made."""

    says: str
    verdict: str
    verdict_by: str
    reason: str
    planned_by: str | None
    sent: dict[str, Any] | None
    result: dict[str, Any] | None
    matched_by: str | None
    stale: bool
    before_url: str | None
    after_url: str | None
    in_tokens: int
    out_tokens: int
    thought_tokens: int
    """Inside `out_tokens`, not beside them. Added to them, a reader reports a
    number no invoice will match."""

    cost_usd: float
    unpriced: bool

    notes: list[str] = []
    """What is already known about the values this step writes -- today, a
    value the field dictionary says will not fit. Shown beside the write a
    person is asked to approve, because a column that keeps four characters of
    six still answers 201 and nothing else in the run can tell."""

    @classmethod
    def of(cls, step: RunStep) -> WorkflowRunStepModel:
        return cls(**asdict(step))


class RunMailModel(BaseModel):
    """The mail a run came from: who sent it, what it was called, when it
    arrived and where to open it. Never its body -- the subject is as much of
    the mail as leaves the mailbox.

    A run a person started in answer to a mail's question knows only the
    conversation, so everything but `thread` and `link` may be empty."""

    subject: str = ""
    sender: str = ""
    arrived: str = ""
    """ISO 8601, from the mail's own Date header; empty where it had none."""

    thread: str = ""
    link: str = ""
    """The conversation in Gmail, for the card's "open the mail"."""

    @classmethod
    def of(cls, mail: Mapping[str, str]) -> RunMailModel:
        thread = mail.get("thread", "")
        return cls(
            subject=mail.get("subject", ""),
            sender=mail.get("sender", ""),
            arrived=mail.get("arrived", ""),
            thread=thread,
            link=f"https://mail.google.com/mail/#all/{quote(thread)}" if thread else "",
        )


class WorkflowRunModel(BaseModel):
    """One run of a mined workflow, whole.

    The backend's own field names, deliberately. The extension's `rigRun()`
    maps `outcome` onto a panel `status` and `{order, says, verdict}` onto
    `{index, outcome}`.

    **Corrected 2026-09-10.** This said phase 5 would delete that mapping layer
    against this docstring, on the reasoning that rig-shaped aliases mean two
    vocabularies forever. Phase 5 kept it, deliberately, and the reasoning was
    the thing that was wrong: `{status, index}` are not rig-shaped aliases, they
    are the *skill* run's own names -- `RunModel.status` and
    `StepOutcomeModel.index`, both in this same module. The extension's
    `run-card.js` draws both kinds of run from that one shape, telling them
    apart only by `source`. Deleting the map means teaching the run card a
    second vocabulary, so the map is what keeps there being one. It moves when
    the card does, and not before.

    Not `RunModel`, which is `sro.domain.execution.run.Run` -- a skill run, keyed
    on a `RunId`. Two aggregates, two id spaces; see the router's docstring for
    why the path differs too.

    `from_step` is on the wire because it is a request input the row carries: a
    re-press that moves it finishes a different job under this run's id, and a
    caller that cannot read back what it claimed cannot re-press correctly.

    `unpriced` beside `cost_usd` because a run whose cost is 0.0 and whose
    `unpriced` is true did not cost nothing; nobody could say.
    """

    id: str
    tenant: str
    workflow_id: str
    device_id: str
    values: dict[str, str]
    items: list[dict[str, str]]
    """The things this run was asked to do the repeated block for. Empty for a
    job that does one thing once."""

    started_by: str
    live: bool
    allow_focus: bool
    started_at: str
    finished_at: str | None
    outcome: str
    from_step: int
    steps: list[WorkflowRunStepModel]
    withheld: list[dict[str, Any]]
    """The writes a dry run produced and did not send, in full. This is what a
    person reads before pressing through to live."""

    in_tokens: int
    out_tokens: int
    thought_tokens: int
    cost_usd: float
    unpriced: bool

    watched: bool = False
    """Whether this run is being done in front of somebody: the fields filling
    and the button pressed, rather than the call replayed."""

    doing: str = ""
    """What this run is doing when it has no step to show for it -- reading a
    mailbox for the values nobody typed. Empty the rest of the time, which is
    almost always."""

    gathered: dict[str, dict[str, str]] = {}
    needs: list[str] = []
    unasked: list[str] = []
    """Names the request asked for that this job declares no parameter for.
    Names and never values; see `WorkflowRun.unasked`."""
    """What it could not find a value for. The panel takes the conversation
    from here: the question is already in the operator's thread."""
    """Parameter -> where its value was read, for values nobody typed.

    On the wire because the card showing a write a person is asked to approve
    has to say where its values came from: a value read out of a mailbox is
    only as good as the message it came from. Empty for a run whose values a
    person typed."""

    wrong_because: str | None = None
    """What the operator said was wrong with what this run made, where anybody
    has said anything.

    On the wire because the card that reports a run is the same card that has
    to stop offering to report it twice, and because a run that says `held` on
    every step and carries this is the one shape a reviewer most needs to be
    able to find. Null on every run nobody has reported."""

    undo: str | None = None
    """The job of this tenant's that takes back what this run made, where one
    exists: a job whose own evidence shows somebody deleting the records this
    one creates.

    An id, still, and never a start: what presses it is a person. Null on a run
    still going, on one that made nothing, on a tenant that has never deleted
    one of these in front of the recorder, and on a run whose record this
    cannot name -- see `undoes_by`."""

    undoes_by: dict[str, str] | None = None
    """Which record that job would address, as the warehouse named it.

    The mapping `undo` said it lacked, and the evidence arrived with `made_by`:
    a step that created something records what the warehouse called it. One
    record named one way or nothing -- a run that made two would need two
    deletes, and an undo that takes back half of what a run did is worse than
    none, because somebody presses it, sees the card go quiet, and believes the
    warehouse is back where it started."""

    try_again: bool = False
    """Whether this run can be started again with one press.

    A run stops for reasons that have nothing to do with the job: the session
    expired, a tab was closed, the browser could not be reached. Until now that
    was a dead end -- the offer that started it is spent, so the request sat
    there until somebody noticed and sent the mail again. Measured on the
    deployment 2026-09-19: a run stopped on a sign-in page and the card offered
    a person nothing but OK.

    True only where **nothing this run did may have landed**. Every step that
    wrote either never left the browser or was refused by the warehouse --
    `effects.may_have_landed`, the same reading that decides whether a failed
    write costs a job its autonomy. A second press after a write that might be
    in the warehouse is how you get two records, and no button is better than
    that.

    False on a run that held: there is nothing to try again."""

    undoes_run: str | None = None
    """The run this one takes back, where it is an undo of one.

    The other end of `undo`, and on the wire for the same reason it is in the
    row: the delete and the thing it deletes are one piece of work, and a
    failed undo has to be readable as *run_abc is still out there* rather than
    as a job that failed on its own. Null on every run that is not an undo."""

    live_view_url: str | None = None
    """Where to watch a Steel run's own tab, view-only, while it holds a live
    browser. Null otherwise, and on every list row: only the one-run read asks
    Steel. The viewer's address and the tab, never a CDP url."""

    offer: str | None = None
    """The offer this run is the one run of -- `mail:<message id>` for a
    mail's. The panel ends any card still offering it, so a mail that already
    ran is shown as its run and never offered again."""

    mail: RunMailModel | None = None
    """The mail this run came from, on the list rows as well as the one-run
    read: the panel's Home draws a card per mail-started run from the list it
    polls. Null for every run no mail started."""

    asking: str = ""
    """The question a running run is parked on, while nobody has answered it;
    empty otherwise. A run waiting on a person is not running: the mail card
    said "Running..." over PJ26's parked save (QA, 2026-09-30), and this is
    how it says "Needs you" instead."""

    @classmethod
    def of(
        cls,
        run: WorkflowRun,
        undo: tuple[str, str, str] | None = None,
        live_view_url: str | None = None,
    ) -> WorkflowRunModel:
        return cls(
            id=run.id,
            tenant=run.tenant,
            workflow_id=run.workflow_id,
            device_id=run.device_id,
            values=dict(run.values),
            items=[dict(item) for item in run.items],
            started_by=run.started_by,
            live=run.live,
            allow_focus=run.allow_focus,
            started_at=run.started_at,
            finished_at=run.finished_at,
            outcome=run.outcome,
            from_step=run.from_step,
            steps=[WorkflowRunStepModel.of(step) for step in run.steps],
            withheld=[dict(one) for one in run.withheld],
            in_tokens=run.in_tokens,
            out_tokens=run.out_tokens,
            thought_tokens=run.thought_tokens,
            cost_usd=run.cost_usd,
            unpriced=run.unpriced,
            watched=run.watched,
            doing=run.doing,
            gathered={k: dict(v) for k, v in run.gathered.items()},
            needs=list(run.needs),
            unasked=list(run.unasked),
            wrong_because=run.wrong_because,
            undo=undo[0] if undo else None,
            undoes_by={undo[1]: undo[2]} if undo else None,
            undoes_run=run.undoes_run,
            try_again=can_try_again(run),
            live_view_url=live_view_url or None,
            offer=run.offer,
            mail=RunMailModel.of(run.mail) if run.mail else None,
            asking=standing_question(run),
        )


class WorkflowStepApprovedModel(BaseModel):
    """What one tap on the panel's approve button let out.

    Two fields, and neither is a constant. The rig answered `{"approved": true,
    "ord": ord}`; `approved` was a literal on every answer this route ever
    gives -- a refusal is a problem document -- so it is not here.

    `order` rather than the store's `ord`, because `WorkflowRunStepModel.order`
    is what a panel already reads a step's number from and one wire vocabulary
    is enough.
    """

    order: int
    """Which step this tap authorised: the DEEPEST one parked on a person, which
    is where a run is waiting. Not the shallowest, and deliberately not the
    order `GET /v1/workflow-runs?awaiting=true` lists -- that answers what is
    waiting, across every step and every browser, and this answers what one tap
    let out."""

    first: bool
    """Whether THIS tap was the one that authorised the step.

    False means somebody had already approved it and theirs is the name in the
    audit: a write rescued to the second rung parks at the same step and takes
    a second tap, and the first authorisation stands. The tap is not refused --
    the run really is parked again -- and this is how a panel can say so."""

    resumed: bool
    """Whether a process was actually holding this run when the tap landed.

    False is the case this field exists for: the authorisation is recorded and
    the run does not move, because the task that was waiting on it is gone --
    the process restarted, or the five-minute wait had already run out. It
    happened in a real session: an operator tapped Approve, got a 200, and the
    browser sat on the same login screen until they gave up.

    Not a refusal. The row naming who let the write out is committed either
    way, and answering 409 would be claiming the authorisation did not happen.
    What this says is narrower and truer: nobody was listening."""


class MailOfferModel(BaseModel):
    """One mail, and the job it turned out to ask for.

    The message id and never the words. A caller that wants to check the
    reading opens the mail in their own mailbox, where it already is -- an
    excerpt echoed back here would be mail content crossing a boundary to say
    something the id already says.
    """

    message: str
    workflow_id: str
    title: str
    values: dict[str, str]
    missing: list[str]
    offer: str = ""
    """The offer's own name, which a start of it sends back: the mail door's
    start and the question it asks carry the same one, so a card pressed in the
    panel and a yes in the thread answer to one run."""

    subject: str = ""
    """What the request was called, so a conversation about it can say which.

    A deliberate exception to the rule above, and `Offered.subject` argues it:
    with four requests for one job open at once, the subject is the only thing
    that tells them apart in a thread that is no longer beside the card."""

    thread: str = ""
    """The mail conversation this request arrived in.

    An id and not a word of anybody's mail, like `message` beside it. It is
    sent back when the job is started, so a run that comes up short can be
    found again by a reply -- the person who knows the missing value is usually
    whoever sent the request, and they do not have this panel open."""

    too_long: dict[str, int] = {}
    """Values this job's own boxes will not hold, and what they hold instead.

    Sent so the card can ask before the press rather than after it. The run
    refuses a value that will not fit, and it can only refuse once it is
    standing in front of the box -- by which time somebody has pressed and is
    watching a form half-fill. The limit was learnt by an earlier run and is
    known now, so the panel says it now.

    Empty for every job no run has hit a limit on, which is most of them."""

    offers: list[list[str]] = []
    """Fields this job can also fill that the page does not ask for, each with
    what it was last time.

    On the card, because a mail that supplied everything required produces no
    question and there is nowhere else to say it. The question path offers
    these when a run comes up short; a request short of nothing never reaches
    it, so on the path an operator who works from their mailbox actually uses,
    an optional field could never be set at all.

    Pairs as two-item lists, because JSON has no tuples and the panel reads
    them positionally."""

    unasked: list[str] = []
    """What the request asked for that this job has no parameter for.

    Sent so the card can say it BEFORE the press. A job's parameters are what
    two doings proved vary and a form has far more fields than that, so `code
    GV3, description X, Department Inbound` is a reasonable request answered by
    a record with no Department in it. The run says so afterwards; after the
    press is after the record."""

    started: bool = False
    """A run is already going for this one, so there is nothing to offer.

    The operator pressed Yes on the request; that press is what sent the mail
    asking for what was missing, and the reply filled the one blank the press
    could not. A card beside the run that answer started is the panel offering
    to do what it is doing.

    Sent rather than inferred from an empty `missing`: plenty of offers arrive
    with nothing missing and every one of them is a card. What makes this one
    different is that somebody already said yes to it."""

    sent_to: list[str] = []
    """Who the operator sent this request to, when the operator sent it to
    somebody else.

    Such a mail is a job the operator asked another person to do, so it never
    starts by itself: the card names who it went to and asks whether this
    system should do it instead. Empty for every mail somebody else sent, and
    for one the operator addressed to themselves."""

    asked: bool = False
    """Already asked in the operator's conversation, as a question the panel
    draws with its own answers. A browser draws no card for it: one mail, one
    question, whichever look read it."""


class AskAboutOfferRequest(BaseModel):
    """An offer the operator pressed that cannot simply be started.

    Sent by the panel instead of drawing boxes on the card. What comes of it is
    a question in their own conversation, which is where every other question
    this system asks already lives.
    """

    workflow_id: str
    title: str = ""
    values: dict[str, str] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)
    items: list[dict[str, str]] = Field(default_factory=list)
    mail_thread: str = ""
    """The mail conversation this offer was read out of.

    Sent back so the run an answer starts answers to it, exactly as one the
    press starts does. See `Pending.mail_thread`."""

    about: str = ""
    """What the request this offer came from was called.

    So the conversation can name it. A question that says only "Customer Type
    takes 4 characters" is a sentence with no subject, and there may be four
    like it in the thread."""

    limits: dict[str, int] = Field(default_factory=dict)
    """What the box behind each name holds, where the offer was told.

    Sent back rather than looked up again: the offer that reached the browser
    carried these, and a second lookup could answer differently -- a run that
    learned a limit in between would change the question under somebody who is
    already reading it."""

    watched: bool = True

    offer: str = ""
    """The offer's own name, where it has one -- a mail's, or the question a
    reply already asked. The question this asks carries it, so its answer and
    any other start of the same offer land on one run."""


class AskAboutOfferResponse(BaseModel):
    """What was asked, so the panel can say something happened.

    Empty `asked` means the offer needed nothing after all and the caller
    should start it -- a 200 with nothing to say, rather than an error on the
    ordinary path.
    """

    asked: str


class SendTheDraftRequest(BaseModel):
    """A drafted mail the operator has read and is authorising.

    An id and never the words. What goes out is re-read from the thread the
    draft was shown in, so what is sent and what was read cannot be two
    different things -- a body accepted here would put every guarantee about a
    person having seen what they authorised on a browser being honest."""

    thread_id: str
    message_id: str


class SentTheDraftResponse(BaseModel):
    """Who it went to, or `""` where nothing was sent.

    Empty is an ordinary answer and not an error: a draft already sent, one
    nobody can find, a run since asked about another way. None of those is a
    500, and none of them means try again."""

    sent_to: str


class FromTheMailResponse(BaseModel):
    """What one look through the mailbox came to.

    `read` and `offered` are different numbers on purpose: a look that read six
    mails and offered none is working correctly, and a caller told only
    "offered: []" cannot tell that from a mailbox nothing was reached in.
    """

    offered: list[MailOfferModel]
    read: int
    why: str

    @classmethod
    def of(cls, looked: LookedInTheMail) -> FromTheMailResponse:
        return cls(
            offered=[
                MailOfferModel(
                    message=one.message,
                    offer=one.named,
                    workflow_id=one.workflow_id,
                    title=one.title,
                    values=dict(one.values),
                    missing=list(one.missing),
                    subject=one.subject,
                    thread=one.thread,
                    too_long=dict(one.too_long),
                    offers=[[name, was] for name, was in one.offers],
                    unasked=list(one.unasked),
                    started=one.started,
                    sent_to=list(one.sent_to),
                    asked=one.asked,
                )
                for one in looked.offered
            ],
            read=looked.read,
            why=looked.why,
        )
