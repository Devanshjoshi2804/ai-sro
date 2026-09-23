from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Identity,
    Index,
    Integer,
    String,
    Text,
    quoted_name,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RecordingRow(Base):
    __tablename__ = "recordings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    objective_type: Mapped[str | None] = mapped_column(String(64))
    target_system: Mapped[str | None] = mapped_column(String(64))
    entity_type: Mapped[str | None] = mapped_column(String(64))
    facility: Mapped[str | None] = mapped_column(String(64))
    direction: Mapped[str | None] = mapped_column(String(16))

    demonstrator: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    browser_session_id: Mapped[str | None] = mapped_column(String(128))
    device_id: Mapped[str | None] = mapped_column(String(64))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abandon_reason: Mapped[str | None] = mapped_column(Text)

    frames: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    artifacts: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    narration: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_recordings_tenant_started", "tenant_id", "started_at"),
        Index(
            "ix_recordings_tenant_objective",
            "tenant_id",
            "objective_type",
            "target_system",
            "entity_type",
            "facility",
            "direction",
        ),
    )


class SkillRow(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    objective_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_system: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    facility: Mapped[str] = mapped_column(String(64), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)

    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    latest_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_stage: Mapped[str] = mapped_column(String(16), nullable=False, default="recorded")
    versions: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __mapper_args__ = {  # noqa: RUF012 -- SQLAlchemy reads this, nothing mutates it
        "version_id_col": revision,
    }

    __table_args__ = (
        Index(
            "uq_skills_tenant_objective",
            "tenant_id",
            "objective_type",
            "target_system",
            "entity_type",
            "facility",
            "direction",
            unique=True,
        ),
    )


class ConnectionRow(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    target_system: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    authenticated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    failures_acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[str | None] = mapped_column(String(255))
    acknowledgement_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("uq_connections_tenant_system", "tenant_id", "target_system", unique=True),
    )


class RunRow(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_version: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(16), nullable=False)
    medium: Mapped[str] = mapped_column(String(16), nullable=False, default="network")
    device_id: Mapped[str | None] = mapped_column(String(64))
    may_take_focus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_system: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    systems: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    iterations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    requested_by: Mapped[str] = mapped_column(String(64), nullable=False)
    authorized_by: Mapped[str | None] = mapped_column(String(64))

    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    derived: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure: Mapped[str | None] = mapped_column(Text)
    wrong_because: Mapped[str | None] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(Text, nullable=False, default="")
    revisions: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_runs_tenant_started", "tenant_id", "started_at"),
        Index("ix_runs_system_ended", "tenant_id", "target_system", "ended_at"),
        Index(
            "uq_runs_one_running_per_device",
            "tenant_id",
            "device_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )


EMBEDDING_DIMENSIONS = 768


class KnowledgeRow(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    system: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    superseded_by: Mapped[str | None] = mapped_column(String(64))

    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)

    __table_args__ = (
        Index(
            "ix_knowledge_current",
            "tenant_id",
            "system",
            "kind",
            "key",
            postgresql_where=text("superseded_by IS NULL"),
        ),
        Index("ix_knowledge_tenant_kind", "tenant_id", "kind"),
        Index(
            "ix_knowledge_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_where=text("superseded_by IS NULL"),
        ),
    )


class ModelCallRow(Base):
    __tablename__ = "model_calls"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    destination: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    redacted_fields: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    failed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (Index("ix_model_calls_run", "tenant_id", "run_id", "started_at"),)


class ThreadRow(Base):
    __tablename__ = "threads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_by: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    messages: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (Index("ix_threads_tenant_opened", "tenant_id", "opened_at"),)


class BrowserSessionRow(Base):
    __tablename__ = "browser_sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_by: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_browser_sessions_tenant", "tenant_id"),)


class AgentDeviceRow(Base):
    __tablename__ = "agent_devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    extension_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paused_by: Mapped[str | None] = mapped_column(String(64))

    queued_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queued_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    secret: Mapped[str | None] = mapped_column(String(64))

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    grants: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    __table_args__ = (
        Index("ix_agent_devices_tenant_seen", "tenant_id", "last_seen_at"),
        Index(
            "uq_agent_devices_tenant_principal_label",
            "tenant_id",
            "principal_id",
            "label",
            unique=True,
        ),
    )


class ObservationBatchRow(Base):
    __tablename__ = "observation_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    recording_id: Mapped[str | None] = mapped_column(String(64), index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    uri: Mapped[str] = mapped_column(Text, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rejected: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_observation_batches_tenant_started", "tenant_id", "started_at"),
        Index("ix_observation_batches_principal", "tenant_id", "principal_id", "started_at"),
    )


class ObservationPolicyRow(Base):
    __tablename__ = "observation_policies"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)


class TriggerRow(Base):
    __tablename__ = "triggers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str | None] = mapped_column(String(64))
    workflow_id: Mapped[str | None] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    asks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    cron: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    from_message: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    watch: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    arrival: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    device_id: Mapped[str | None] = mapped_column(String(64))
    medium: Mapped[str] = mapped_column(String(16), nullable=False, default="network")

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    authorized_by: Mapped[str | None] = mapped_column(String(64))
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    may_take_focus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_id: Mapped[str | None] = mapped_column(String(64))
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    inbound_token: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_triggers_tenant_created", "tenant_id", "created_at"),
        Index("ix_triggers_tenant_skill", "tenant_id", "skill_id"),
    )


class TaskCandidateRow(Base):
    __tablename__ = "task_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False)

    signature: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    starts_on: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    named_by_model: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    learned_from: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    learned_under: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    skill_id: Mapped[str | None] = mapped_column(String(64))
    dismissed_reason: Mapped[str | None] = mapped_column(Text)
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    episodes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    joins: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    times_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_task_candidates_tenant_seen", "tenant_id", "times_seen"),
        Index(
            "uq_task_candidates_signature",
            "tenant_id",
            "principal_id",
            "signature",
            unique=True,
        ),
    )


class ToolCallRow(Base):
    __tablename__ = "tool_calls"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), primary_key=True)

    tool: Mapped[str] = mapped_column(String(200), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConfirmationRow(Base):
    __tablename__ = "confirmations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str | None] = mapped_column(String(64))
    workflow_id: Mapped[str | None] = mapped_column(String(64))

    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    values: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    because: Mapped[str] = mapped_column(Text, nullable=False, default="")

    answer: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_by: Mapped[str | None] = mapped_column(String(64))
    run_id: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (Index("ix_confirmations_tenant_answer", "tenant_id", "answer", "asked_at"),)


class GestureBatchRow(Base):
    __tablename__ = "gesture_batches"

    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)

    started_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    ended_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    recording_id: Mapped[str | None] = mapped_column(String(64))

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class GestureRow(Base):
    __tablename__ = "gestures"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    stream_id: Mapped[str] = mapped_column(String(64), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False)

    at: Mapped[float] = mapped_column(Float, nullable=False)

    url: Mapped[str | None] = mapped_column(Text)
    system: Mapped[str | None] = mapped_column(Text)
    tab_id: Mapped[int | None] = mapped_column(Integer)
    frame_url: Mapped[str | None] = mapped_column(Text)

    page_url: Mapped[str | None] = mapped_column(Text)

    gesture: Mapped[Any] = mapped_column(JSONB, nullable=False)
    requests: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    page_events: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_gestures_tenant_at", "tenant_id", "at"),
        Index("ix_gestures_stream", "tenant_id", "stream_id", "at"),
    )


class IntentRow(Base):
    __tablename__ = "intents"

    gesture_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    act: Mapped[str | None] = mapped_column(Text)
    object_: Mapped[str | None] = mapped_column("object", Text)
    page: Mapped[str | None] = mapped_column(Text)
    values_seen: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    continues: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(Text)
    why: Mapped[str | None] = mapped_column(Text)

    model: Mapped[str | None] = mapped_column(Text)
    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_intents_tenant_created", "tenant_id", "created_at"),)


class OrphanRequestRow(Base):
    __tablename__ = "orphan_requests"

    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)


class OrphanPageRow(Base):
    __tablename__ = "orphan_pages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    at: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)


class PoolRow(Base):
    __tablename__ = "mining_pool"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gesture_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    age: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    retired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowRunRow(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)

    values_: Mapped[Any] = mapped_column(
        quoted_name("values", True),
        JSONB,
        nullable=False,
        default=dict,
    )

    items: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")

    started_by: Mapped[str] = mapped_column(Text, nullable=False, default="")
    live: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_focus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="running")

    from_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    withheld: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    watched: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    doing: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    gathered: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    needs: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    unasked: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    undoes_run: Mapped[str | None] = mapped_column(String(64))

    asked_the_asker: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    awaiting: Mapped[Any] = mapped_column(JSONB, nullable=True)

    wrong_because: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_workflow_runs_tenant_workflow", "tenant_id", "workflow_id", "started_at"),
        Index("ix_workflow_runs_undoes", "undoes_run"),
        Index("ix_workflow_runs_tenant_device", "tenant_id", "device_id", "outcome"),
        Index(
            "uq_workflow_runs_one_running_per_device",
            "tenant_id",
            "device_id",
            unique=True,
            postgresql_where=text("outcome = 'running'"),
        ),
        Index(
            "ix_workflow_runs_awaiting",
            "tenant_id",
            text("(awaiting ->> 'server')"),
            text("(awaiting ->> 'thread')"),
            postgresql_where=text("awaiting IS NOT NULL"),
        ),
    )


class WorkflowRunStepRow(Base):
    __tablename__ = "workflow_run_steps"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)

    says: Mapped[str] = mapped_column(Text, nullable=False, default="")

    made: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    of_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    item: Mapped[int | None] = mapped_column(Integer, nullable=True)

    planned_by: Mapped[str | None] = mapped_column(Text)
    sent: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)

    result: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)

    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    verdict_by: Mapped[str] = mapped_column(String(24), nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    matched_by: Mapped[str | None] = mapped_column(Text)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    before_url: Mapped[str | None] = mapped_column(Text)
    after_url: Mapped[str | None] = mapped_column(Text)

    notes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ApprovalRow(Base):
    __tablename__ = "approvals"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(64))


class WorkflowRow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    pass_id: Mapped[str] = mapped_column(Text, nullable=False, default="")

    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    narrative: Mapped[str] = mapped_column(Text, nullable=False, default="")
    systems: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    parameters: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    shape_key: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    repeat: Mapped[Any] = mapped_column(JSONB, nullable=True)

    signs_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    same_as: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_workflows_tenant_created", "tenant_id", "created_at"),)


class WorkflowStepRow(Base):
    __tablename__ = "workflow_steps"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)

    says: Mapped[str] = mapped_column(Text, nullable=False, default="")
    system: Mapped[str | None] = mapped_column(Text)
    cites: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    parameters: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    uses: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)


class WorkflowStaleRow(Base):
    __tablename__ = "workflow_stale"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)
    matched_by: Mapped[str | None] = mapped_column(Text)
    noticed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowLearnedRow(Base):
    __tablename__ = "workflow_learned"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    found_by: Mapped[str] = mapped_column(Text, nullable=False)
    holds: Mapped[int | None] = mapped_column(Integer)
    learned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowLearnedHistoryRow(Base):
    __tablename__ = "workflow_learned_history"
    __table_args__ = (Index("ix_workflow_learned_history_job", "workflow_id", "at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ord: Mapped[int] = mapped_column(Integer, nullable=False)
    about: Mapped[str] = mapped_column(Text, nullable=False)

    was: Mapped[str] = mapped_column(Text, nullable=False, default="")
    now: Mapped[str] = mapped_column(Text, nullable=False, default="")

    by_run: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    found_by: Mapped[str] = mapped_column(Text, nullable=False, default="")

    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LearnedWriteRow(Base):
    __tablename__ = "learned_writes"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    method: Mapped[str] = mapped_column(String(16), primary_key=True)
    path_pattern: Mapped[str] = mapped_column(Text, primary_key=True)

    origin: Mapped[str] = mapped_column(Text, nullable=False, default="")
    proved_by_run: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    verified_by: Mapped[str] = mapped_column(String(16), nullable=False)

    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowEffectRow(Base):
    __tablename__ = "workflow_effects"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)
    verified_by: Mapped[str] = mapped_column(String(24), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MiningPassRow(Base):
    __tablename__ = "mining_passes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    proposed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kept: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    learned_parameters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    skew: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lopsided: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    window_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    left_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unplaced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_mining_passes_tenant_started", "tenant_id", "started_at"),)


class AttemptRow(Base):
    __tablename__ = "attempts"
    __table_args__ = (Index("ix_attempts_tenant_at", "tenant_id", "at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    principal: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    asked_for: Mapped[str] = mapped_column(Text, nullable=False)
    came_of: Mapped[str] = mapped_column(String(16), nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False, default="")
    about: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)


class OfferRow(Base):
    __tablename__ = "offers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)

    k: Mapped[int] = mapped_column(Integer, nullable=False)

    fate: Mapped[str] = mapped_column(String(16), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_offers_tenant_workflow", "tenant_id", "workflow_id", "at"),)


class ChatRow(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str | None] = mapped_column(String(64))

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    error: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_chats_tenant_at", "tenant_id", "at"),)
