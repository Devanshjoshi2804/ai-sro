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
from sro.domain.observation.batch import CaptureMode, ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.identifiers import (
    BatchId,
    BrowserSessionId,
    CandidateId,
    DeviceId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
    TriggerId,
)
from sro.domain.shared.objective import Direction, ObjectiveKey
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import Skill
from sro.domain.trigger.trigger import Trigger, TriggerKind
from sro.infrastructure.db.codec import (
    dump_artifacts,
    dump_episodes,
    dump_frames,
    dump_joins,
    dump_messages,
    dump_narration,
    dump_policy,
    dump_rejected,
    dump_versions,
    load_artifacts,
    load_episodes,
    load_frames,
    load_joins,
    load_messages,
    load_narration,
    load_policy,
    load_rejected,
    load_versions,
)
from sro.infrastructure.db.models import (
    AgentDeviceRow,
    ConnectionRow,
    KnowledgeRow,
    ModelCallRow,
    ObservationBatchRow,
    ObservationPolicyRow,
    RecordingRow,
    RunRow,
    SkillRow,
    TaskCandidateRow,
    ThreadRow,
    TriggerRow,
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
    row.device_id = recording.device_id.value if recording.device_id else None
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
        device_id=DeviceId(row.device_id) if row.device_id else None,
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
    row.device_id = run.device_id.value if run.device_id else None
    row.may_take_focus = run.may_take_focus
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
        device_id=DeviceId(row.device_id) if row.device_id else None,
        may_take_focus=bool(row.may_take_focus),
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
        "found_total": step.found_total,
        "found_partial": step.found_partial,
        "found": [dict(row) for row in step.found],
        "found_columns": list(step.found_columns),
        "found_values": [[key, list(values)] for key, values in step.found_values],
        "found_labels": list(step.found_labels),
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
        found_total=data.get("found_total"),
        found_partial=bool(data.get("found_partial")),
        found=tuple(dict(row) for row in (data.get("found") or ())),
        found_columns=tuple(data.get("found_columns") or ()),
        found_values=tuple(
            (str(key), tuple(str(value) for value in values))
            for key, values in (data.get("found_values") or [])
        ),
        found_labels=tuple(data.get("found_labels") or ()),
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


def device_to_row(device: AgentDevice) -> AgentDeviceRow:
    row = AgentDeviceRow(id=device.id.value)
    update_device_row(row, device)
    return row


def update_device_row(row: AgentDeviceRow, device: AgentDevice) -> None:
    row.tenant_id = device.tenant_id.value
    row.principal_id = device.principal_id.value
    row.label = device.label
    row.extension_version = device.extension_version
    row.registered_at = device.registered_at
    row.last_seen_at = device.last_seen_at
    row.paused = device.paused
    row.paused_by = device.paused_by
    row.queued_events = device.queued_events
    row.queued_bytes = device.queued_bytes
    row.uploads = device.uploads


def row_to_device(row: AgentDeviceRow) -> AgentDevice:
    return AgentDevice(
        id=DeviceId(row.id),
        tenant_id=TenantId(row.tenant_id),
        principal_id=PrincipalId(row.principal_id),
        label=row.label,
        extension_version=row.extension_version,
        registered_at=row.registered_at,
        last_seen_at=row.last_seen_at,
        paused=row.paused,
        paused_by=row.paused_by,
        queued_events=row.queued_events,
        queued_bytes=row.queued_bytes,
        uploads=row.uploads,
    )


def batch_to_row(batch: ObservationBatch) -> ObservationBatchRow:
    return ObservationBatchRow(
        id=batch.id.value,
        tenant_id=batch.tenant_id.value,
        device_id=batch.device_id.value,
        principal_id=batch.principal_id.value,
        mode=batch.mode.value,
        recording_id=batch.recording_id.value if batch.recording_id else None,
        started_at=batch.started_at,
        ended_at=batch.ended_at,
        received_at=batch.received_at,
        uri=batch.uri,
        event_count=batch.event_count,
        byte_count=batch.byte_count,
        rejected=dump_rejected(batch.rejected),
    )


def row_to_batch(row: ObservationBatchRow) -> ObservationBatch:
    return ObservationBatch(
        id=BatchId(row.id),
        tenant_id=TenantId(row.tenant_id),
        device_id=DeviceId(row.device_id),
        principal_id=PrincipalId(row.principal_id),
        mode=CaptureMode(row.mode),
        recording_id=RecordingId(row.recording_id) if row.recording_id else None,
        started_at=row.started_at,
        ended_at=row.ended_at,
        received_at=row.received_at,
        uri=row.uri,
        event_count=row.event_count,
        byte_count=row.byte_count,
        rejected=load_rejected(row.rejected),
    )


def policy_to_row(tenant_id: TenantId, policy: ObservationPolicy) -> ObservationPolicyRow:
    return ObservationPolicyRow(
        tenant_id=tenant_id.value, version=policy.version, policy=dump_policy(policy)
    )


def row_to_policy(row: ObservationPolicyRow) -> ObservationPolicy:
    return load_policy(row.policy)


def trigger_to_row(trigger: Trigger) -> TriggerRow:
    row = TriggerRow(id=trigger.id.value)
    update_trigger_row(row, trigger)
    return row


def update_trigger_row(row: TriggerRow, trigger: Trigger) -> None:
    row.tenant_id = trigger.tenant_id.value
    row.skill_id = trigger.skill_id.value
    row.kind = trigger.kind.value
    row.cron = trigger.cron
    row.timezone = trigger.timezone
    row.parameters = dict(trigger.parameters)
    row.device_id = trigger.device_id.value if trigger.device_id else None
    row.medium = trigger.medium.value
    row.enabled = trigger.enabled
    row.writes = trigger.writes
    row.authorized_by = trigger.authorized_by.value if trigger.authorized_by else None
    row.requires_confirmation = trigger.requires_confirmation
    row.may_take_focus = trigger.may_take_focus
    row.created_by = trigger.created_by.value
    row.created_at = trigger.created_at
    row.last_fired_at = trigger.last_fired_at
    row.last_run_id = trigger.last_run_id.value if trigger.last_run_id else None
    row.disabled_reason = trigger.disabled_reason
    row.inbound_token = trigger.inbound_token


def row_to_trigger(row: TriggerRow) -> Trigger:
    return Trigger(
        id=TriggerId(row.id),
        tenant_id=TenantId(row.tenant_id),
        skill_id=SkillId(row.skill_id),
        kind=TriggerKind(row.kind),
        created_by=PrincipalId(row.created_by),
        created_at=row.created_at,
        parameters=dict(row.parameters),
        cron=row.cron,
        timezone=row.timezone,
        device_id=DeviceId(row.device_id) if row.device_id else None,
        medium=Medium(row.medium),
        enabled=row.enabled,
        writes=row.writes,
        authorized_by=PrincipalId(row.authorized_by) if row.authorized_by else None,
        requires_confirmation=row.requires_confirmation,
        may_take_focus=row.may_take_focus,
        last_fired_at=row.last_fired_at,
        last_run_id=RunId(row.last_run_id) if row.last_run_id else None,
        disabled_reason=row.disabled_reason,
        inbound_token=row.inbound_token,
    )


def candidate_to_row(candidate: TaskCandidate) -> TaskCandidateRow:
    row = TaskCandidateRow(id=candidate.id.value)
    update_candidate_row(row, candidate)
    return row


def update_candidate_row(row: TaskCandidateRow, candidate: TaskCandidate) -> None:
    row.tenant_id = candidate.tenant_id.value
    row.principal_id = candidate.principal_id.value
    row.signature = candidate.signature
    row.host = candidate.host
    row.title = candidate.title
    row.named_by_model = candidate.named_by_model
    row.status = candidate.status.value
    row.skill_id = candidate.skill_id.value if candidate.skill_id else None
    row.dismissed_reason = candidate.dismissed_reason
    row.episodes = dump_episodes(candidate.episodes)
    row.joins = dump_joins(candidate.joins)
    # Lifted out of the document so "offer me what happened most often" is an
    # index rather than a scan of every candidate's episodes.
    row.times_seen = candidate.times_seen
    row.first_seen = candidate.first_seen
    row.last_seen = candidate.last_seen


def row_to_candidate(row: TaskCandidateRow) -> TaskCandidate:
    return TaskCandidate(
        id=CandidateId(row.id),
        tenant_id=TenantId(row.tenant_id),
        principal_id=PrincipalId(row.principal_id),
        signature=row.signature,
        host=row.host,
        title=row.title,
        status=CandidateStatus(row.status),
        episodes=load_episodes(row.episodes),
        skill_id=SkillId(row.skill_id) if row.skill_id else None,
        dismissed_reason=row.dismissed_reason,
        joins=load_joins(row.joins),
        named_by_model=row.named_by_model,
    )
