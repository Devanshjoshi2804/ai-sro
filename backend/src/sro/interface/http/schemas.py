"""Wire types.

Domain objects never cross the HTTP boundary. These are what the frontend's
generated client is built from, so their shape is a contract; the aggregates
behind them stay free to change.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sro.application.analytics.summary import Summary
from sro.application.capture.devices import DeviceLine
from sro.application.execution.pursuits import PursuitProgress
from sro.application.execution.reversal import Reversal
from sro.application.intent.match import Candidate
from sro.application.intent.resolve import Resolution
from sro.domain.chat.thread import Thread
from sro.domain.execution.run import Medium, Run, StepOutcome
from sro.domain.observation.batch import CaptureMode, RejectedEvent
from sro.domain.observation.candidate import (
    Episode,
    Join,
    JoinAnswer,
    JoinKind,
    TaskCandidate,
)
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.recording import Recording
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.assertion import AssertionKind
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill, SkillVersion
from sro.domain.skill.template import Template
from sro.domain.skill.track_record import (
    DEMOTE_AFTER_FAILURES,
    REQUIRED_CLEAN_RUNS,
)
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

    device_id: str | None = None
    """Demonstrated through the extension, in the operator's own Chrome.

    Different from `attach_to` in the direction the evidence flows: an attached
    browser is driven by this deployment over CDP, and a device uploads what it
    saw afterwards, as teaching-mode observation batches. Nothing is opened,
    nothing is signed in, and there is no live view — the operator is already
    looking at the only screen involved."""


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


class DemonstrationModel(BaseModel):
    """One demonstration behind a version, and what it put in each field.

    ``values`` holds a name only where this doing answers for it: a null is
    "sent holding nothing", which is the evidence behind an optional field,
    and a name absent from the mapping is a field this doing does not answer
    for at all. The two are different facts and the screen shows them
    differently.
    """

    recording_id: str
    started_at: datetime
    demonstrator: str
    frames: int
    diffed: bool
    values: dict[str, str | None]


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


class ToolOfferedModel(BaseModel):
    name: str
    description: str
    arguments: list[str]


class ConfirmationModel(BaseModel):
    """A fire waiting for somebody to say yes."""

    id: str
    trigger_id: str
    skill_id: str
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
            skill_id=confirmation.skill_id.value,
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


class AssertRequest(BaseModel):
    version: int
    step_index: int
    kind: AssertionKind
    expected: str
    pointer: str | None = None


class MapStepRequest(BaseModel):
    version: int
    step_index: int
    server: str
    tool: str
    arguments: dict[str, str] = {}
    writes: bool = False
    """Whether calling this changes something outside this system. Said by the
    person mapping it, because nothing else can: MCP declares no such thing,
    and a tool named `send_message` is a name rather than a promise."""


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
    # The two thresholds the streak is measured against, sent rather than left
    # for a reader to know. A console drawing "7 of 10" from a 10 it hardcoded
    # would go on saying 10 the day `REQUIRED_CLEAN_RUNS` moved, and the bar
    # would disagree with the rule that actually refuses the promotion.
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


class PromoteRequest(BaseModel):
    """A person, in the console, choosing to move a version up a rung.

    Carries no `from_where`: this endpoint is answered by `PromoteSkill`, which
    always tells the version it was `"console"`. A press on the panel's preview
    promotes through a different call, because it is a different review -- see
    ADR 014 -- and this request never stands in for it."""

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

    items: list[dict[str, str]] = []
    """Values the parser read out of the sentence for the matched skill, one
    set per thing to do -- "these six SKUs" is six. Sent so a caller that asks
    in a sentence rather than a form can actually use what typing the sentence
    was for; without this a matched skill whose parameters the sentence
    supplied was refused at the press for values nobody was ever asked to
    give twice."""

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
            items=[dict(item) for item in resolution.items],
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

    run_id: str | None = None
    """Set when this was typed at a run that is happening, rather than asked of
    the system. Such a sentence is kept beside that run and resolved against
    nothing: putting "use the north yard address" through intent matching finds
    some other skill and offers to run it."""


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
    capture_snapshots: bool = False
    snapshot_max_per_minute: int = 20
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
            capture_snapshots=policy.capture_snapshots,
            snapshot_max_per_minute=policy.snapshot_max_per_minute,
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


class ObservationBatchRequest(BaseModel):
    batch_id: str = Field(max_length=64)
    """Minted by the extension so a retried upload is recognised as the one it
    already sent."""

    device_id: str = Field(max_length=64)
    started_at: datetime
    ended_at: datetime
    mode: CaptureMode = CaptureMode.PASSIVE

    recording_id: str | None = Field(default=None, max_length=64)
    """The demonstration this batch belongs to. Set when, and only when, the
    mode is `teaching`."""

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


class NewTriggerRequest(BaseModel):
    skill_id: str
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


class ChangeTriggerRequest(BaseModel):
    enabled: bool
    reason: str = ""
    """Why it was switched off. A trigger nobody remembers disabling gets
    switched back on."""


class TriggerModel(BaseModel):
    id: str
    skill_id: str
    kind: str
    cron: str | None
    timezone: str
    parameters: dict[str, str]
    from_message: list[str]
    watch: WatchModel | None
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
            skill_id=trigger.skill_id.value,
            kind=trigger.kind.value,
            cron=trigger.cron,
            timezone=trigger.timezone,
            parameters=dict(trigger.parameters),
            from_message=list(trigger.from_message),
            watch=None if trigger.watch is None else WatchModel.of(trigger.watch),
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
    skill_id: str
    values: dict[str, str]
    missing: list[str]


class EpisodeModel(BaseModel):
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    gestures: int
    calls: int

    @classmethod
    def of(cls, episode: Episode) -> EpisodeModel:
        return cls(
            started_at=episode.started_at,
            ended_at=episode.ended_at,
            duration_ms=episode.duration_ms,
            gestures=episode.gestures,
            calls=episode.calls,
        )


class JoinModel(BaseModel):
    """A suggestion that this candidate and another are one piece of work.

    `variant` is the same task done two ways; `workflow` is two halves of one
    task in two systems. Suggestions, with the reason attached: nothing merges
    on them, and `by_model` says who is doing the suggesting.
    """

    other_id: str
    kind: str
    because: str
    by_model: bool

    answered: str | None = None
    """`same` or `different`, once somebody has looked. Absent means it is
    still a question, and a screen should be asking it rather than stating it."""

    answered_by: str | None = None

    @classmethod
    def of(cls, join: Join) -> JoinModel:
        return cls(
            other_id=join.other_id.value,
            kind=join.kind.value,
            because=join.because,
            by_model=join.by_model,
            answered=join.answered.value if join.answered else None,
            answered_by=join.answered_by.value if join.answered_by else None,
        )


class AnswerJoinRequest(BaseModel):
    """What a person says two candidates are to each other."""

    other_id: str
    kind: JoinKind
    answer: JoinAnswer


class TaskCandidateModel(BaseModel):
    """A task somebody keeps doing, offered rather than acted on."""

    id: str
    title: str
    host: str
    signature: str
    """The calls it makes, in order, with the identifiers taken out. On the wire
    because it is the whole argument that two doings are the same task, and an
    operator who disagrees should be able to see why."""

    status: str
    times_seen: int
    median_duration_ms: int
    minutes_so_far: float
    first_seen: datetime | None
    last_seen: datetime | None
    skill_id: str | None
    dismissed_reason: str | None
    named_by_model: bool
    """Whether the title is a model's sentence rather than one derived from the
    calls. On the wire so a screen can say so: a name is not a fact."""

    offered_at: datetime | None
    """When this was said out loud in the operator's conversation, if it has
    been. On the wire so the panel's list can stop drawing what the thread is
    already showing: an offer belongs in one place, and two surfaces carrying
    the same two buttons is how they come to disagree about whether it was
    answered."""

    starts_on: str = ""
    """Host and path of the page this task begins on, no query string.

    On the wire so the extension can recognise that page the moment the operator
    lands on it, against the candidate list it already holds -- without asking
    the server on every navigation what the tab in front of somebody is for.
    """

    joins: list[JoinModel]
    episodes: list[EpisodeModel]

    @classmethod
    def of(cls, candidate: TaskCandidate) -> TaskCandidateModel:
        return cls(
            id=candidate.id.value,
            title=candidate.title,
            host=candidate.host,
            starts_on=candidate.starts_on,
            signature=candidate.signature,
            status=candidate.status.value,
            times_seen=candidate.times_seen,
            median_duration_ms=candidate.median_duration_ms,
            minutes_so_far=round(candidate.minutes_so_far, 1),
            first_seen=candidate.first_seen,
            last_seen=candidate.last_seen,
            skill_id=candidate.skill_id.value if candidate.skill_id else None,
            dismissed_reason=candidate.dismissed_reason,
            named_by_model=candidate.named_by_model,
            offered_at=candidate.offered_at,
            joins=[JoinModel.of(join) for join in candidate.joins],
            episodes=[EpisodeModel.of(episode) for episode in candidate.episodes],
        )


class ReviseRunRequest(BaseModel):
    """What the operator changed while the run was going.

    Names the skill declares and nothing else -- a name outside them reaches no
    step, and the run refuses it rather than recording a decision with no
    effect.
    """

    values: dict[str, str] = Field(min_length=1)


class DismissCandidateRequest(BaseModel):
    reason: str


class TaughtModel(BaseModel):
    candidate_id: str
    recording_id: str | None
    skill_id: str | None
    needs_demonstration: bool
    because: str | None
    """Why one more doing of it is needed. Passive capture sees no accessibility
    tree and only the response bodies the page could see, so some tasks cannot
    be induced from it -- and being told which, and why, is better than a skill
    nobody can trust."""


class TeachTogetherRequest(BaseModel):
    """The other half of a job a person has said is one job."""

    other_id: str


class TaughtTogetherModel(BaseModel):
    """One skill out of two candidates. Both ids, because both were spent."""

    first_id: str
    second_id: str
    recording_ids: list[str]
    skill_id: str | None
    needs_demonstration: bool
    because: str | None


class MinedModel(BaseModel):
    episodes: int
    candidates_seen: int
    candidates_new: int
    occurrences_new: int


class WatchingModel(BaseModel):
    devices: int
    batches: int
    events: int
    hours: float


class NoticingModel(BaseModel):
    tasks: int
    worth_offering: int
    taught: int
    dismissed: int
    by_kind: dict[str, int]


class DoingModel(BaseModel):
    runs: int
    clean: int
    degraded: int
    failed: int
    withheld: int
    unreachable: int
    writes_sent: int
    minutes_saved: float


class TaskLineModel(BaseModel):
    id: str
    title: str
    host: str
    kind: str
    status: str
    times_seen: int
    median_seconds: float
    minutes_spent: float
    skill_id: str | None
    runs: int
    minutes_saved: float


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
