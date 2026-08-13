"""Wire types.

Domain objects never cross the HTTP boundary. These are what the frontend's
generated client is built from, so their shape is a contract; the aggregates
behind them stay free to change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from sro.domain.recording.recording import Recording
from sro.domain.shared.objective import Direction
from sro.domain.skill.skill import Skill, SkillVersion


class ObjectiveKeyModel(BaseModel):
    objective_type: str
    target_system: str
    entity_type: str
    facility: str
    direction: Direction


class StartRecordingRequest(BaseModel):
    objective_key: ObjectiveKeyModel
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
    name: str
    target_system: str
    base_url: str


class ConnectionModel(BaseModel):
    id: str
    name: str
    target_system: str
    base_url: str
    status: str
    authenticated_at: datetime | None
    last_error: str | None


class OpenedConnectionResponse(BaseModel):
    connection_id: str
    live_view_url: str
    browser_session_id: str
    """Handed back when the operator says they have signed in, so the session
    they created is the one that gets kept."""


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


class RecordingSummary(BaseModel):
    id: str
    objective_key: ObjectiveKeyModel
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
            objective_key=ObjectiveKeyModel(
                objective_type=recording.objective_key.objective_type,
                target_system=recording.objective_key.target_system,
                entity_type=recording.objective_key.entity_type,
                facility=recording.objective_key.facility,
                direction=recording.objective_key.direction,
            ),
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


class InduceSkillRequest(BaseModel):
    first_recording_id: str
    second_recording_id: str
    name: str | None = None


class SkillSummary(BaseModel):
    id: str
    name: str
    objective_key: ObjectiveKeyModel
    created_at: datetime
    latest_version: int
    latest_stage: str

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
        )


class ParameterModel(BaseModel):
    name: str
    kind: str
    description: str
    observed_values: list[str]
    source_step_index: int | None


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
    network_plan: NetworkPlanModel | None
    ui_plan: UiPlanModel | None
    assertions: list[AssertionModel]


class SkillVersionModel(BaseModel):
    version: int
    stage: str
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
            induced_at=version.provenance.induced_at,
            induced_by=version.provenance.induced_by.value,
            recording_ids=[r.value for r in version.provenance.recording_ids],
            provenance_note=version.provenance.note,
            steps=[
                StepModel(
                    index=step.index,
                    intent=step.intent,
                    requires_human=step.requires_human,
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


class PromoteRequest(BaseModel):
    version: int
    to: str


class InductionResponse(BaseModel):
    skill_id: str
    version: int
    step_count: int
    input_parameter_count: int
    derived_parameter_count: int
