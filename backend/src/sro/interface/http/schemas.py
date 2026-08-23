"""Wire types.

Domain objects never cross the HTTP boundary. These are what the frontend's
generated client is built from, so their shape is a contract; the aggregates
behind them stay free to change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sro.application.execution.pursuits import PursuitProgress
from sro.application.intent.match import Candidate
from sro.application.intent.resolve import Resolution
from sro.domain.chat.thread import Thread
from sro.domain.execution.run import Run, StepOutcome
from sro.domain.observation.batch import CaptureMode, RejectedEvent
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.recording import Recording
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillVersion
from sro.domain.skill.track_record import why_not_autonomous


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


class StartRecordingRequest(BaseModel):
    objective_key: ObjectiveKeyModel | None = None
    """Absent for a first demonstration: the evidence names the task at seal.
    Present for the second run of a pair, so both carry the same key."""

    start_url: str | None = None
    label: str | None = None

    attach_to: str | None = None
    """CDP endpoint of a browser the operator already has open.

    When set, no hosted session is created and capture attaches to that browser
    instead — the operator demonstrates in their own window."""


class StartRecordingResponse(BaseModel):
    recording_id: str
    live_view_url: str


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


class MediaModel(BaseModel):
    kind: str
    url: str
    content_type: str
    size_bytes: int
    duration_ms: int | None
    frame_index: int | None


class LiveViewResponse(BaseModel):
    live_view_url: str | None


class FinishRecordingRequest(BaseModel):
    abandon_reason: str | None = Field(
        default=None,
        description="Present means abandon; absent means seal.",
    )

    objective_key: ObjectiveKeyModel | None = Field(
        default=None,
        description=(
            "Only for a demonstration whose evidence cannot name it, or the "
            "second run of a pair. Otherwise the task names itself."
        ),
    )


class RecordingSummary(BaseModel):
    id: str
    objective_key: ObjectiveKeyModel | None
    label: str | None
    status: str
    demonstrator: str
    started_at: datetime
    ended_at: datetime | None
    frame_count: int
    has_narration: bool

    @classmethod
    def of(cls, recording: Recording) -> RecordingSummary:
        return cls(
            id=recording.id.value,
            objective_key=ObjectiveKeyModel.of(recording.objective_key),
            label=recording.label,
            status=recording.status.value,
            demonstrator=recording.demonstrator.value,
            started_at=recording.started_at,
            ended_at=recording.ended_at,
            frame_count=len(recording.frames),
            has_narration=recording.has_narration,
        )


class FrameSummary(BaseModel):
    """Enough to render the timeline. The full frame is fetched per frame."""

    index: int
    occurred_at: datetime
    action_kind: str
    target: str | None
    request_count: int
    primary_request: str | None
    primary_status: int | None
    error_count: int

    applied: bool
    """The action caused a mutating call the system accepted.

    How a teaching session knows the task actually happened rather than asking
    the operator to say so. It means something was applied, not that the task is
    finished -- a task can apply several things.
    """


class RecordingDetail(RecordingSummary):
    frames: list[FrameSummary]
    artifacts: list[ArtifactModel]

    @classmethod
    def of_recording(cls, recording: Recording) -> RecordingDetail:
        summary = RecordingSummary.of(recording)
        return cls(
            **summary.model_dump(),
            frames=[
                FrameSummary(
                    index=frame.index,
                    occurred_at=frame.occurred_at,
                    action_kind=frame.action.kind.value,
                    target=frame.action.target.describe() if frame.action.target else None,
                    request_count=len(frame.requests),
                    primary_request=(
                        f"{frame.primary_request.method} {frame.primary_request.url}"
                        if frame.primary_request
                        else None
                    ),
                    primary_status=(
                        frame.primary_request.status if frame.primary_request else None
                    ),
                    applied=(
                        frame.primary_request is not None
                        and frame.primary_request.is_mutation
                        and frame.primary_request.succeeded
                    ),
                    error_count=len(frame.errors),
                )
                for frame in recording.frames
            ],
            artifacts=[ArtifactModel.of(a) for a in recording.artifacts],
        )


class ArtifactModel(BaseModel):
    kind: str
    uri: str
    content_type: str
    size_bytes: int
    frame_index: int | None
    label: str | None

    @classmethod
    def of(cls, artifact: Any) -> ArtifactModel:
        return cls(
            kind=artifact.kind.value,
            uri=artifact.uri,
            content_type=artifact.content_type,
            size_bytes=artifact.size_bytes,
            frame_index=artifact.frame_index,
            label=artifact.label,
        )


class UnderstandRequest(BaseModel):
    recording_id: str
    name: str | None = None


class UnderstoodResponse(BaseModel):
    skill_id: str
    version: int
    step_count: int
    proposed_parameter_count: int
    caveat: str
    """What the reading could not account for. Kept, because "I did not
    understand step 4" is the most useful thing it can say."""


class InduceSkillRequest(BaseModel):
    first_recording_id: str
    second_recording_id: str | None = None
    """Absent when the operator asked for a skill from one demonstration. What
    that costs is on the skill itself: with nothing to diff against, every value
    stays exactly as it was demonstrated and the skill takes no parameters."""
    name: str | None = None


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


class AssertionModel(BaseModel):
    kind: str
    expected: str
    pointer: str | None


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


class StepModel(BaseModel):
    index: int
    intent: str
    requires_human: bool
    narration: str
    branch_hint: str | None
    network_plan: NetworkPlanModel | None
    ui_plan: UiPlanModel | None
    assertions: list[AssertionModel]


class TrackRecordModel(BaseModel):
    clean_streak: int
    consecutive_failures: int
    clean_runs: int
    degraded_runs: int
    failed_runs: int


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
    induced_at: datetime
    induced_by: str
    recording_ids: list[str]
    provenance_note: str
    steps: list[StepModel]
    parameters: list[ParameterModel]

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
            ),
            ready_for_autonomy=why_not_autonomous(
                version.track_record, verifiable=version.verifiable
            ),
            demotion_reason=version.demotion_reason,
            induced_at=version.provenance.induced_at,
            induced_by=version.provenance.induced_by.value,
            recording_ids=[r.value for r in version.provenance.recording_ids],
            provenance_note=version.provenance.note,
            steps=[
                StepModel(
                    index=step.index,
                    intent=step.intent,
                    requires_human=step.requires_human,
                    narration=step.narration,
                    branch_hint=step.branch_hint,
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
                    assertions=[
                        AssertionModel(
                            kind=a.kind.value, expected=str(a.expected), pointer=a.pointer
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


class PromoteRequest(BaseModel):
    version: int
    to: PromotionStage
    """The rung to move to, checked here rather than in the router: coercing an
    unknown name inside the handler raised a bare ValueError, so asking to
    promote something to "wizard" answered 500 — an internal fault for a typo."""

    acknowledging_fixed_values: bool = False
    """Yes, I have read what this sends and I mean it.

    Only consulted for a version induced from one demonstration that writes:
    with nothing to diff against, every value it sends is the one that run
    happened to carry, and above shadow it is sent for real."""


class DescribeRequest(BaseModel):
    version: int
    summary: str
    when_to_use: str = ""


class InductionResponse(BaseModel):
    skill_id: str
    version: int
    step_count: int
    input_parameter_count: int
    derived_parameter_count: int


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

    authorized_by: str | None = None
    """Required above shadow. The human who allowed this run to write."""


class StepOutcomeModel(BaseModel):
    index: int
    medium: str
    disposition: str
    intent: str
    method: str | None
    url: str | None
    status_code: int | None
    idempotency_key: str | None
    assertion_failures: list[str]
    escalated_from: str | None
    escalation_reason: str | None
    matched_by: str | None
    detail: str | None

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
            assertion_failures=list(step.assertion_failures),
            escalated_from=step.escalated_from.value if step.escalated_from else None,
            escalation_reason=step.escalation_reason,
            matched_by=step.matched_by,
            detail=step.detail,
            found_rows=step.found_rows,
            found_total=step.found_total,
            found_partial=step.found_partial,
            found=[dict(row) for row in step.found],
            found_columns=list(step.found_columns),
            found_values={key: list(values) for key, values in step.found_values},
            found_labels=list(step.found_labels),
        )


class RunModel(BaseModel):
    id: str
    skill_id: str
    skill_version: int
    stage: str
    medium: str
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
    steps: list[StepOutcomeModel]

    @classmethod
    def of(cls, run: Run) -> RunModel:
        return cls(
            id=run.id.value,
            skill_id=run.skill_id.value,
            skill_version=run.skill_version,
            stage=run.stage.value,
            medium=run.medium.value,
            status=run.status.value,
            parameters=dict(run.parameters),
            derived=dict(run.derived),
            requested_by=run.requested_by.value,
            authorized_by=run.authorized_by.value if run.authorized_by else None,
            started_at=run.started_at,
            ended_at=run.ended_at,
            failure=run.failure,
            steps=[StepOutcomeModel.of(step) for step in run.steps],
        )


class SessionHeadersRequest(BaseModel):
    facility: str
    headers: dict[str, str]
    """Header name to value. Values go straight to the vault."""


class SessionHeadersResponse(BaseModel):
    stored: list[str]
    """Key names only. A credential is never echoed back."""


class ResolveIntentRequest(BaseModel):
    utterance: str
    system: str | None = None
    parameters: dict[str, str] = Field(default_factory=dict)


class CandidateModel(BaseModel):
    skill_id: str
    name: str
    version: int
    stage: str
    summary: str
    score: int
    why: list[str]
    unexplained: list[str]


class ProposedStepModel(BaseModel):
    what: str
    detail: str
    source: str
    evidence: str


class ProposalModel(BaseModel):
    steps: list[ProposedStepModel]
    sources: list[str]
    caveat: str


class ResolutionModel(BaseModel):
    """What the system decided a sentence asked for.

    `matched` absent with `choices` present means two skills were too close to
    separate; `proposal` present means nothing was taught and this is what the
    knowledge base says. Neither is a run.
    """

    utterance: str
    matched: CandidateModel | None
    choices: list[CandidateModel]
    missing_parameters: list[str]
    runnable: bool
    confident: bool
    question: str | None
    why: list[str]
    proposal: ProposalModel | None

    @classmethod
    def of(cls, resolution: Resolution) -> ResolutionModel:
        return cls(
            utterance=resolution.utterance,
            matched=_candidate(resolution.matched),
            choices=[model for c in resolution.choices if (model := _candidate(c))],
            missing_parameters=list(resolution.missing_parameters),
            runnable=resolution.runnable,
            confident=resolution.confident,
            question=resolution.question,
            why=list(resolution.why),
            proposal=(
                ProposalModel(
                    steps=[
                        ProposedStepModel(
                            what=step.what,
                            detail=step.detail,
                            source=step.source,
                            evidence=step.evidence.value,
                        )
                        for step in resolution.proposal.steps
                    ],
                    sources=list(resolution.proposal.sources),
                    caveat=resolution.proposal.caveat,
                )
                if resolution.proposal is not None
                else None
            ),
        )


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
    404 was read as a RecordingDetail with every field missing.
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
    policy: ObservationPolicyModel
    policy_version: int


class HeartbeatRequest(BaseModel):
    queued_events: int = 0
    queued_bytes: int = 0
    policy_version: int | None = None
    """What the device holds. The policy comes back only when this is behind."""


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

    @classmethod
    def of(cls, device: AgentDevice) -> DeviceModel:
        return cls(
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


class ObservationBatchRequest(BaseModel):
    batch_id: str = Field(max_length=64)
    """Minted by the extension so a retried upload is recognised as the one it
    already sent."""

    device_id: str = Field(max_length=64)
    started_at: datetime
    ended_at: datetime
    mode: CaptureMode = CaptureMode.PASSIVE
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


class ObservationArtifactResponse(BaseModel):
    uri: str
    size_bytes: int


class ForgottenResponse(BaseModel):
    batches: int
    events: int
