"""Rows to aggregates and back.

Kept apart from the repositories so the shape of persistence is readable in one
place, and apart from the domain so the domain never learns it is stored.
"""

from __future__ import annotations

from typing import Any

from sro.domain.chat.thread import Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import (
    Medium,
    Run,
    RunId,
    RunStatus,
    StepDisposition,
    StepOutcome,
)
from sro.domain.knowledge.entry import (
    EntryKind,
    EvidenceLevel,
    KnowledgeEntry,
    KnowledgeId,
)
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
    dump_messages,
    dump_narration,
    dump_versions,
    load_artifacts,
    load_frames,
    load_messages,
    load_narration,
    load_versions,
)
from sro.infrastructure.db.models import (
    ConnectionRow,
    KnowledgeRow,
    ModelCallRow,
    RecordingRow,
    RunRow,
    SkillRow,
    ThreadRow,
)

_OBJECTIVE_COLUMNS = ("objective_type", "target_system", "entity_type", "facility", "direction")


def objective_columns(key: ObjectiveKey) -> dict[str, str]:
    return {
        "objective_type": key.objective_type,
        "target_system": key.target_system,
        "entity_type": key.entity_type,
        "facility": key.facility,
        "direction": key.direction.value,
    }


def _objective_or_none(row: RecordingRow) -> ObjectiveKey | None:
    if row.objective_type is None:
        return None
    return ObjectiveKey(
        objective_type=row.objective_type,
        target_system=row.target_system or "",
        entity_type=row.entity_type or "",
        facility=row.facility or "",
        direction=Direction(row.direction or Direction.INTERNAL),
    )


def _objective(row: SkillRow) -> ObjectiveKey:
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
    columns = (
        objective_columns(recording.objective_key)
        if recording.objective_key is not None
        else dict.fromkeys(_OBJECTIVE_COLUMNS)
    )
    for column, value in columns.items():
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
    row.narration = dump_narration(recording.narration)


def row_to_recording(row: RecordingRow) -> Recording:
    recording = Recording(
        id=RecordingId(row.id),
        tenant_id=TenantId(row.tenant_id),
        objective_key=_objective_or_none(row),
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
    recording._narration.extend(load_narration(row.narration))
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


def connection_to_row(connection: Connection) -> ConnectionRow:
    row = ConnectionRow(id=connection.id.value)
    update_connection_row(row, connection)
    return row


def update_connection_row(row: ConnectionRow, connection: Connection) -> None:
    row.tenant_id = connection.tenant_id.value
    row.name = connection.name
    row.target_system = connection.target_system
    row.base_url = connection.base_url
    row.status = connection.status.value
    row.created_at = connection.created_at
    row.authenticated_at = connection.authenticated_at
    row.last_error = connection.last_error
    row.failures_acknowledged_at = connection.failures_acknowledged_at
    row.acknowledged_by = connection.acknowledged_by
    row.acknowledgement_reason = connection.acknowledgement_reason


def row_to_connection(row: ConnectionRow) -> Connection:
    return Connection(
        id=ConnectionId(row.id),
        tenant_id=TenantId(row.tenant_id),
        name=row.name,
        target_system=row.target_system,
        base_url=row.base_url,
        created_at=row.created_at,
        status=ConnectionStatus(row.status),
        authenticated_at=row.authenticated_at,
        last_error=row.last_error,
        failures_acknowledged_at=row.failures_acknowledged_at,
        acknowledged_by=row.acknowledged_by,
        acknowledgement_reason=row.acknowledgement_reason,
    )


def run_to_row(run: Run) -> RunRow:
    row = RunRow(id=run.id.value)
    update_run_row(row, run)
    return row


def update_run_row(row: RunRow, run: Run) -> None:
    row.tenant_id = run.tenant_id.value
    row.skill_id = run.skill_id.value
    row.skill_version = run.skill_version
    row.stage = run.stage.value
    row.medium = run.medium.value
    row.target_system = run.target_system
    row.status = run.status.value
    row.requested_by = run.requested_by.value
    row.authorized_by = run.authorized_by.value if run.authorized_by else None
    row.parameters = dict(run.parameters)
    row.derived = dict(run.derived)
    row.steps = [_step_to_json(step) for step in run.steps]
    row.started_at = run.started_at
    row.ended_at = run.ended_at
    row.failure = run.failure


def row_to_run(row: RunRow) -> Run:
    run = Run(
        id=RunId(row.id),
        tenant_id=TenantId(row.tenant_id),
        skill_id=SkillId(row.skill_id),
        skill_version=row.skill_version,
        stage=PromotionStage(row.stage),
        medium=Medium(row.medium),
        target_system=row.target_system or "",
        parameters=dict(row.parameters),
        requested_by=PrincipalId(row.requested_by),
        started_at=row.started_at,
        authorized_by=PrincipalId(row.authorized_by) if row.authorized_by else None,
        derived=dict(row.derived),
        # A stored run was validated when it was created; rehydration must not
        # re-litigate that. A read-only assisted run has no authoriser by
        # design, and re-checking would make it unreadable ever afterwards.
        may_change_the_system=False,
    )
    run.status = RunStatus(row.status)
    run.steps = [_step_from_json(step) for step in row.steps]
    run.ended_at = row.ended_at
    run.failure = row.failure
    return run


def _step_to_json(step: StepOutcome) -> dict[str, Any]:
    return {
        "index": step.index,
        "medium": step.medium.value,
        "disposition": step.disposition.value,
        "intent": step.intent,
        "method": step.method,
        "url": step.url,
        "status_code": step.status_code,
        "idempotency_key": step.idempotency_key,
        "assertion_failures": list(step.assertion_failures),
        "escalated_from": step.escalated_from.value if step.escalated_from else None,
        "escalation_reason": step.escalation_reason,
        "matched_by": step.matched_by,
        "detail": step.detail,
        "found_rows": step.found_rows,
        "found": [dict(row) for row in step.found],
    }


def _step_from_json(data: dict[str, Any]) -> StepOutcome:
    return StepOutcome(
        index=data["index"],
        medium=Medium(data["medium"]),
        disposition=StepDisposition(data["disposition"]),
        intent=data["intent"],
        method=data.get("method"),
        url=data.get("url"),
        status_code=data.get("status_code"),
        idempotency_key=data.get("idempotency_key"),
        assertion_failures=tuple(data.get("assertion_failures") or ()),
        escalated_from=(Medium(data["escalated_from"]) if data.get("escalated_from") else None),
        escalation_reason=data.get("escalation_reason"),
        matched_by=data.get("matched_by"),
        detail=data.get("detail"),
        found_rows=data.get("found_rows"),
        found=tuple(dict(row) for row in (data.get("found") or ())),
    )


def knowledge_to_row(entry: KnowledgeEntry) -> KnowledgeRow:
    row = KnowledgeRow(id=str(entry.id))
    update_knowledge_row(row, entry)
    return row


def update_knowledge_row(row: KnowledgeRow, entry: KnowledgeEntry) -> None:
    row.tenant_id = entry.tenant_id.value
    row.system = entry.system
    row.kind = entry.kind.value
    row.key = entry.key
    row.title = entry.title
    row.body = dict(entry.body)
    row.source = entry.source
    row.evidence = entry.evidence.value
    row.observed_at = entry.observed_at
    row.superseded_by = str(entry.superseded_by) if entry.superseded_by else None
    row.embedding = list(entry.embedding) if entry.embedding else None


def row_to_knowledge(row: KnowledgeRow) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=KnowledgeId(row.id),
        tenant_id=TenantId(row.tenant_id),
        system=row.system,
        kind=EntryKind(row.kind),
        key=row.key,
        title=row.title,
        body=dict(row.body or {}),
        source=row.source,
        evidence=EvidenceLevel(row.evidence),
        observed_at=row.observed_at,
        superseded_by=KnowledgeId(row.superseded_by) if row.superseded_by else None,
        embedding=tuple(row.embedding) if row.embedding is not None else (),
    )


def model_call_to_row(call: ModelCall) -> ModelCallRow:
    return ModelCallRow(
        id=call.id,
        tenant_id=call.tenant_id.value,
        run_id=call.run_id.value,
        step_index=call.step_index,
        purpose=call.purpose,
        destination=call.destination,
        model=call.model,
        started_at=call.started_at,
        duration_ms=call.duration_ms,
        sent_bytes=call.sent_bytes,
        image_sent=call.image_sent,
        redacted_fields=list(call.redacted_fields),
        outcome=call.outcome,
        failed=call.failed,
    )


def row_to_model_call(row: ModelCallRow) -> ModelCall:
    return ModelCall(
        id=row.id,
        tenant_id=TenantId(row.tenant_id),
        run_id=RunId(row.run_id),
        step_index=row.step_index,
        purpose=row.purpose,
        destination=row.destination,
        model=row.model,
        started_at=row.started_at,
        duration_ms=row.duration_ms,
        sent_bytes=row.sent_bytes,
        image_sent=row.image_sent,
        redacted_fields=tuple(row.redacted_fields or ()),
        outcome=row.outcome,
        failed=row.failed,
    )


def thread_to_row(thread: Thread) -> ThreadRow:
    row = ThreadRow(id=thread.id.value)
    update_thread_row(row, thread)
    return row


def update_thread_row(row: ThreadRow, thread: Thread) -> None:
    row.tenant_id = thread.tenant_id.value
    row.opened_by = thread.opened_by.value
    row.opened_at = thread.opened_at
    row.messages = dump_messages(thread.messages)


def row_to_thread(row: ThreadRow) -> Thread:
    thread = Thread(
        id=ThreadId(row.id),
        tenant_id=TenantId(row.tenant_id),
        opened_by=PrincipalId(row.opened_by),
        opened_at=row.opened_at,
    )
    thread._messages.extend(load_messages(row.messages))
    return thread
