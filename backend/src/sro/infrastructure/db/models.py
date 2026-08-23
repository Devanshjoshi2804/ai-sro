"""SQLAlchemy tables.

Every table carries ``tenant_id`` and every index leads with it, so a query that
forgets the tenant is also a query that misses its index.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RecordingRow(Base):
    __tablename__ = "recordings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Nullable while capturing: the evidence names the task at seal.
    objective_type: Mapped[str | None] = mapped_column(String(64))
    target_system: Mapped[str | None] = mapped_column(String(64))
    entity_type: Mapped[str | None] = mapped_column(String(64))
    facility: Mapped[str | None] = mapped_column(String(64))
    direction: Mapped[str | None] = mapped_column(String(16))

    demonstrator: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    browser_session_id: Mapped[str | None] = mapped_column(String(128))

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

    __table_args__ = (
        # One skill per objective per tenant: induction adds a version rather
        # than a second skill, which is what makes provenance a chain.
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
        # One connection per system per tenant: a second would mean two sessions
        # racing each other into the same WMS.
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
    # Nullable: almost every run is performed in a browser the deployment owns,
    # and this names the operator's own when it is not.
    device_id: Mapped[str | None] = mapped_column(String(64))
    target_system: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    requested_by: Mapped[str] = mapped_column(String(64), nullable=False)
    authorized_by: Mapped[str | None] = mapped_column(String(64))

    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    derived: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_runs_tenant_started", "tenant_id", "started_at"),
        # The breaker's question: how has this system behaved lately.
        Index("ix_runs_system_ended", "tenant_id", "target_system", "ended_at"),
    )


EMBEDDING_DIMENSIONS = 768
"""Fixed by the column. Changing the embedding model means re-embedding the
store, not mixing two geometries in one index."""


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

    # Superseded rows are kept: "we used to believe this" is the only way to
    # explain an incident afterwards.
    superseded_by: Mapped[str | None] = mapped_column(String(64))

    embedding: Mapped[Any] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)

    __table_args__ = (
        # Retrieval filters on all four before it ever measures a distance.
        Index(
            "ix_knowledge_current",
            "tenant_id",
            "system",
            "kind",
            "key",
            postgresql_where=text("superseded_by IS NULL"),
        ),
        Index("ix_knowledge_tenant_kind", "tenant_id", "kind"),
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

    # One document: a thread is read whole and never queried by message.
    messages: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (Index("ix_threads_tenant_opened", "tenant_id", "opened_at"),)


class BrowserSessionRow(Base):
    """Which tenant a browser session belongs to.

    No status column: the provider is the only truth about what is still live,
    and this row answers one question -- whose. The primary key on the
    provider's own id is the security property. A second claim means one browser
    was handed to two callers, and that has to fail rather than transfer.
    """

    __tablename__ = "browser_sessions"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_by: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_browser_sessions_tenant", "tenant_id"),)


class AgentDeviceRow(Base):
    """One installed extension in one browser profile.

    Unique on (tenant, principal, label) so a reinstall re-registers as the
    device it was. An administrator reading this table is answering "whose
    browsers are being observed", and one operator appearing four times is not
    an answer.
    """

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
    """One upload. The events are one object in the blob store, not a column.

    A day of passive capture is millions of events, none of them fetched by id.
    They are read whole, over a window, by a miner. In a column the row that
    says "this arrived" would cost as much to read as the evidence it points at.
    """

    __tablename__ = "observation_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    uri: Mapped[str] = mapped_column(Text, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    byte_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Kept with the batch rather than logged: a rejection is a bug in a specific
    # version of the extension, and it has to be findable next to the upload it
    # came from.
    rejected: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_observation_batches_tenant_started", "tenant_id", "started_at"),
        Index("ix_observation_batches_principal", "tenant_id", "principal_id", "started_at"),
    )


class ObservationPolicyRow(Base):
    """What one tenant agreed to have observed. Absent means nothing."""

    __tablename__ = "observation_policies"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)


class TriggerRow(Base):
    """What starts a run when nobody typed a sentence."""

    __tablename__ = "triggers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)

    cron: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    device_id: Mapped[str | None] = mapped_column(String(64))
    medium: Mapped[str] = mapped_column(String(16), nullable=False, default="network")

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Not nullable by accident: a trigger for a skill that writes cannot exist
    # without one, and the entity refuses to be built otherwise.
    authorized_by: Mapped[str | None] = mapped_column(String(64))
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    may_take_focus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_id: Mapped[str | None] = mapped_column(String(64))
    disabled_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_triggers_tenant_created", "tenant_id", "created_at"),
        Index("ix_triggers_tenant_skill", "tenant_id", "skill_id"),
    )
