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
    # The operator's own browser, when the demonstration happened there. A
    # recording has one or the other, never both.
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
    """Bumped by every write to this row, and by nothing else.

    Every version of a skill lives in one JSONB document, so two writers that
    both read it, changed their own copy and saved overwrote each other -- a
    demonstration, a repair or a promotion gone, with a green log to show for
    it.

    `latest_version` used to be the counter, on the grounds that it already
    existed and already counted. It only moves when a version is *appended*,
    though, and that left everything else racing: two reviewers promoting two
    different versions of one skill both rewrite the whole list, so the second
    silently undoes the first. The comment here used to call that correct, on
    the grounds that a stage is one field -- but it is not one field that gets
    written, it is the document all the versions are in.
    """

    __mapper_args__ = {  # noqa: RUF012 -- SQLAlchemy reads this, nothing mutates it
        # The UPDATE carries `WHERE revision = <what was read>`, so a write
        # onto a skill somebody else has touched fails instead of landing, and
        # `UnitOfWork.commit` turns that into a `Conflict` for the caller to
        # answer.
        "version_id_col": revision,
    }

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
    # False for every run that already exists, which is what they were: nothing
    # could take an operator's screen before there was a browser to take it in.
    may_take_focus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_system: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # Every system the run touched, for the breaker of a system it wrote into
    # without being keyed by. Empty for the ordinary single-system run, which is
    # every run there has ever been.
    systems: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    # What each loop's body is being run with, one entry per thing in the list
    # the system returned. Empty for a skill without loops, which is most.
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
    # Null means nobody said anything, which is the ordinary case and is not a
    # verdict. Set only by the one person who saw what this run made.
    wrong_because: Mapped[str | None] = mapped_column(Text)
    # Empty for a console run, a batch, a trigger -- everything that did not
    # begin with somebody typing a sentence. The one store for it; see
    # ``Run.intent``.
    intent: Mapped[str] = mapped_column(Text, nullable=False, default="")

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

    secret: Mapped[str | None] = mapped_column(String(64))
    """What this browser proves it is itself with. Nullable only for a device
    registered before it existed; that one is refused until its extension
    re-registers, which is idempotent on the label."""

    grants: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    """Hosts this operator said may be watched after all, each with an expiry.
    A list rather than a table: they are read only with the device, only ever
    all at once, and there are a handful at a time."""

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
    # Null for passive capture, which is all of it until somebody is asked to
    # demonstrate something.
    recording_id: Mapped[str | None] = mapped_column(String(64), index=True)

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
    # Which of those values whatever fires this may supply instead. A column
    # rather than a key inside `parameters`, because these two are read in
    # opposite directions: one is what the trigger knows, the other is what it
    # is allowed to be told.
    from_message: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    # What makes a mail one of these, for a trigger the operator's browser
    # evaluates. Terms and locators only: a term names a header and carries the
    # operator's own phrase, a value carries a place to read and no text, so
    # there is no field here a mail body would fit in.
    watch: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

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
    inbound_token: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        Index("ix_triggers_tenant_created", "tenant_id", "created_at"),
        Index("ix_triggers_tenant_skill", "tenant_id", "skill_id"),
    )


class TaskCandidateRow(Base):
    """A task somebody keeps doing, and how often.

    Episodes are one document: they are read whole, by the person deciding
    whether to teach it, and nothing queries a candidate by one of them.
    """

    __tablename__ = "task_candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # The clustering key, and the reason the table has a unique index rather
    # than a primary key that means anything: mining runs again over evidence
    # it has read, and the same task must find its own row.
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    host: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    # The page the first doing began on, host and path, no query. What a panel
    # recognises when somebody lands there. Empty where no gesture carried a
    # URL, which is every candidate mined before this column existed.
    starts_on: Mapped[str] = mapped_column(Text, nullable=False, default="")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    named_by_model: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # How many doings had been seen when learning was last tried on this, so an
    # unattended sweep does not retry the same evidence every quarter hour.
    learned_from: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # And which induction rules made that attempt, so a candidate refused under
    # rules that have since been fixed comes back without waiting for a doing.
    learned_under: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    skill_id: Mapped[str | None] = mapped_column(String(64))
    dismissed_reason: Mapped[str | None] = mapped_column(Text)
    # When this was offered to the operator, so a quarter-hourly sweep does not
    # say the same sentence into their thread again.
    offered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    episodes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    # Suggestions about this candidate -- read whole beside it, never queried,
    # and never acted on by anything but a person.
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
    """One key, claimed before a connector was called with it.

    A row rather than a JSONB list on something: two runs claiming the same key
    at once is exactly the race this exists to lose, and a primary key is the
    only thing that loses it reliably.
    """

    __tablename__ = "tool_calls"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), primary_key=True)

    tool: Mapped[str] = mapped_column(String(200), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConfirmationRow(Base):
    """A fire waiting for somebody to say yes, and what they said."""

    __tablename__ = "confirmations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_id: Mapped[str] = mapped_column(String(64), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(64), nullable=False)

    asked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    values: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    because: Mapped[str] = mapped_column(Text, nullable=False, default="")

    answer: Mapped[str] = mapped_column(String(16), nullable=False, default="waiting")
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_by: Mapped[str | None] = mapped_column(String(64))
    run_id: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (
        # What the console asks for: this tenant's, oldest first, waiting ones.
        Index("ix_confirmations_tenant_answer", "tenant_id", "answer", "asked_at"),
    )
