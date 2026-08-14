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
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    requested_by: Mapped[str] = mapped_column(String(64), nullable=False)
    authorized_by: Mapped[str | None] = mapped_column(String(64))

    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    derived: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_runs_tenant_started", "tenant_id", "started_at"),)


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
