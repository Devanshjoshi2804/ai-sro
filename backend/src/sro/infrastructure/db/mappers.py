"""Rows to aggregates and back.

Kept apart from the repositories so the shape of persistence is readable in one
place, and apart from the domain so the domain never learns it is stored.
"""

from __future__ import annotations

from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.identifiers import (
    BrowserSessionId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
)
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill
from sro.infrastructure.db.codec import (
    dump_artifacts,
    dump_frames,
    dump_versions,
    load_artifacts,
    load_frames,
    load_versions,
)
from sro.infrastructure.db.models import RecordingRow, SkillRow


def objective_columns(key: ObjectiveKey) -> dict[str, str]:
    return {
        "objective_type": key.objective_type,
        "target_system": key.target_system,
        "entity_type": key.entity_type,
        "facility": key.facility,
        "direction": key.direction.value,
    }


def _objective(row: RecordingRow | SkillRow) -> ObjectiveKey:
    return ObjectiveKey(
        objective_type=row.objective_type,
        target_system=row.target_system,
        entity_type=row.entity_type,
        facility=row.facility,
        direction=Direction(row.direction),
    )


def recording_to_row(recording: Recording) -> RecordingRow:
    row = RecordingRow(id=recording.id.value)
    update_recording_row(row, recording)
    return row


def update_recording_row(row: RecordingRow, recording: Recording) -> None:
    row.tenant_id = recording.tenant_id.value
    for column, value in objective_columns(recording.objective_key).items():
        setattr(row, column, value)
    row.demonstrator = recording.demonstrator.value
    row.label = recording.label
    row.status = recording.status.value
    row.browser_session_id = (
        recording.browser_session_id.value if recording.browser_session_id else None
    )
    row.started_at = recording.started_at
    row.ended_at = recording.ended_at
    row.abandon_reason = recording.abandon_reason
    row.frames = dump_frames(recording.frames)
    row.artifacts = dump_artifacts(recording.artifacts)


def row_to_recording(row: RecordingRow) -> Recording:
    recording = Recording(
        id=RecordingId(row.id),
        tenant_id=TenantId(row.tenant_id),
        objective_key=_objective(row),
        demonstrator=PrincipalId(row.demonstrator),
        started_at=row.started_at,
        browser_session_id=(
            BrowserSessionId(row.browser_session_id) if row.browser_session_id else None
        ),
        label=row.label,
        status=RecordingStatus(row.status),
        ended_at=row.ended_at,
        abandon_reason=row.abandon_reason,
    )
    # Frames and artifacts are replayed through the private lists rather than
    # ``append_frame``: a sealed recording rejects appends, and rehydration is
    # not a state transition.
    recording._frames.extend(load_frames(row.frames))
    recording._artifacts.extend(load_artifacts(row.artifacts))
    return recording


def skill_to_row(skill: Skill) -> SkillRow:
    row = SkillRow(id=skill.id.value)
    update_skill_row(row, skill)
    return row


def update_skill_row(row: SkillRow, skill: Skill) -> None:
    row.tenant_id = skill.tenant_id.value
    for column, value in objective_columns(skill.objective_key).items():
        setattr(row, column, value)
    row.name = skill.name
    row.created_at = skill.created_at
    row.versions = dump_versions(skill.versions)
    # Denormalised so listing skills does not mean parsing every version.
    row.latest_version = skill.versions[-1].version if skill.versions else 0
    row.latest_stage = (
        skill.versions[-1].stage.value if skill.versions else PromotionStage.RECORDED.value
    )


def row_to_skill(row: SkillRow) -> Skill:
    skill = Skill(
        id=SkillId(row.id),
        tenant_id=TenantId(row.tenant_id),
        objective_key=_objective(row),
        name=row.name,
        created_at=row.created_at,
    )
    skill._versions.extend(load_versions(row.versions))
    return skill
