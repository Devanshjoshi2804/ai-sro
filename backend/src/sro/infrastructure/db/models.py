"""SQLAlchemy tables.

Every table carries ``tenant_id`` and every index leads with it, so a query that
forgets the tenant is also a query that misses its index.

The exception is a table reached only through its parent. ``workflow_run_steps``
and ``approvals`` are keyed on a run id and carry no tenant of their own: the
run carries it, nothing reaches either table without going through the run, and
a second copy of the tenant on a child row is one more thing that can disagree.
"""

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
    # Values the operator changed while this was running: [name, value, when],
    # in the order they changed them. A document because nothing queries one --
    # they are read beside the run, by somebody asking who decided what it used.
    revisions: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

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

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """When this browser's authority was taken away. Nullable and never
    cleared: a column rather than a deleted row because a revoked device is
    still the answer to "whose browsers were being observed, and until when"."""

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
    skill_id: Mapped[str | None] = mapped_column(String(64))
    workflow_id: Mapped[str | None] = mapped_column(String(64))
    """What this runs: a taught skill or a mined job, and exactly one of them.
    Both nullable in the column and neither optional in the domain -- `Trigger`
    refuses a row that names two or none, and a CHECK constraint here would be
    the same rule written twice in two languages."""
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    asks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """Whether this watch asks a question rather than running anything. The
    third branch of the rule above -- a skill, a job, or a question and
    neither of them -- and the reason there is no CHECK constraint for it."""

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
    # And the other rule a browser holds: the page whose arrival starts this.
    # Beside the watch rather than inside it -- a watch carries terms about a
    # mail, an arrival carries one page, and there is nowhere in either for
    # the other's content.
    arrival: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

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
    skill_id: Mapped[str | None] = mapped_column(String(64))
    workflow_id: Mapped[str | None] = mapped_column(String(64))
    """What the card is asking about. Exactly one, as on `TriggerRow`."""

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


class GestureBatchRow(Base):
    """One upload from a browser, and what became of it.

    ``batch_id`` is minted by the extension and is the primary key, which is
    what makes ingest idempotent: an upload retried after its answer was lost
    is refused rather than stored twice. The second copy would double every
    gesture in it and be mined as a second doing of the same job.
    """

    __tablename__ = "gesture_batches"

    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)

    started_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    ended_at: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    """The device's own clock for the window this batch covers, against
    ``received_at``'s server clock, and kept exactly as it was sent. The
    protocol requires both and the rig discarded both -- the same silent loss
    as a dropped screenshot reference, except these two carry something
    nothing else does."""

    recording_id: Mapped[str | None] = mapped_column(String(64))
    """Which teaching recording this batch belongs to. ``mode`` says a batch
    was a demonstration; without this, nothing says WHICH, and the extension
    refuses to mix two recordings into one batch precisely so that this is
    answerable."""

    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class GestureRow(Base):
    """One thing an operator did, with the calls and page marks around it."""

    __tablename__ = "gestures"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    """Every reader filters on it: the mining pass, the pool, the reading loop
    and the routes."""

    stream_id: Mapped[str] = mapped_column(String(64), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False)

    at: Mapped[float] = mapped_column(Float, nullable=False)
    """Unix seconds as a float -- recorder.js's own format, and what every
    ordering in the rig is on. Not a timestamp: converting it would make two
    formats for one number and a reading loop that sorts differently from the
    browser that recorded it."""

    url: Mapped[str | None] = mapped_column(Text)
    system: Mapped[str | None] = mapped_column(Text)  # scheme+host, derived at ingest
    tab_id: Mapped[int | None] = mapped_column(Integer)
    frame_url: Mapped[str | None] = mapped_column(Text)

    page_url: Mapped[str | None] = mapped_column(Text)
    """The TAB's url, which is not the frame's. A gesture inside a portal that
    hosts its screens in an iframe reports the frame's src in ``url``, and a
    run told to open that would load the frame's document outside the shell
    that gives it its session. This is the address an operator would type."""

    gesture: Mapped[Any] = mapped_column(JSONB, nullable=False)
    requests: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    page_events: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_gestures_tenant_at", "tenant_id", "at"),
        Index("ix_gestures_stream", "tenant_id", "stream_id", "at"),
    )


class IntentRow(Base):
    """What one model call read out of one gesture, and what it cost.

    One row per gesture, replaced rather than appended to: a second reading of
    the same evidence supersedes the first. A row with no usable ``act`` is
    still a row -- the model was asked, it answered, and it was billed, so the
    reading is visible rather than both billed and hidden.
    """

    __tablename__ = "intents"

    gesture_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    act: Mapped[str | None] = mapped_column(Text)
    object_: Mapped[str | None] = mapped_column("object", Text)
    system: Mapped[str | None] = mapped_column(Text)
    page: Mapped[str | None] = mapped_column(Text)
    values_seen: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    continues: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(Text)
    why: Mapped[str | None] = mapped_column(Text)

    model: Mapped[str | None] = mapped_column(Text)
    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Inside ``out_tokens``, not beside it: thinking is billed at the output
    rate and ``out_tokens`` is what the bill is computed from. Kept as its own
    column because on Flash it is ~84% of billed output, and a reader with one
    number cannot tell a long answer from a long silence."""

    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """A call that cost nothing and a call whose cost could not be established
    are the same row without this, and a bill summed over them is understated
    without saying so."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    error: Mapped[str | None] = mapped_column(Text)
    """Why it read nothing, when it read nothing for a reason the API gave. An
    honest empty answer and a refused call are the same row without this."""

    __table_args__ = (
        # The spend sum reads it: everything this tenant was billed for over a
        # window, and a cap that cannot ask that question is not a cap.
        Index("ix_intents_tenant_created", "tenant_id", "created_at"),
    )


class OrphanRequestRow(Base):
    """A recorded call no gesture claimed, kept against the batch it came in.

    Keyed on (batch, request) so a replayed batch re-offers its orphans without
    doubling them: the same call twice is not a second call.
    """

    __tablename__ = "orphan_requests"

    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)


class OrphanPageRow(Base):
    """A page event no gesture claimed.

    A surrogate id rather than a natural key, deliberately: two distinct page
    events can share a batch, an instant and a payload, and keying on those
    would silently drop the second. ``gesture_batches.batch_id`` already makes
    re-ingesting a batch a no-op, so there is nothing here to deduplicate.
    """

    __tablename__ = "orphan_pages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    at: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)


class PoolRow(Base):
    """Evidence a mining pass did not place, waiting to be shown again.

    Keyed by tenant rather than by stream. That is the whole mechanism by which
    one operator's Blue Yonder half meets another operator's SAP half.
    """

    __tablename__ = "mining_pool"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gesture_id: Mapped[str] = mapped_column(String(64), primary_key=True)

    age: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Two clocks, because they measure opposite things and one counter cannot
    be both. ``age`` counts readings this entry was SHOWN and not cited, and
    runs out at ``K_POOL_AGE``. ``waited`` counts passes it was PASSED OVER,
    and drives priority so the day rotates. Using age for both made an entry
    that had been read six times outrank one never seen at all."""

    retired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    """Why it retired, empty while it is still live. Evidence that leaves the
    prompt without a record is the failure this architecture exists to avoid."""

    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowRunRow(Base):
    """One run of a mined workflow: what it was performed with, and how it ended.

    ``workflow_runs`` rather than ``runs`` because ``runs`` is taken -- by the
    backend's own ``RunRow``, which is a different concept and predates this.

    Written whole after every step so the panel can poll it, and its steps are
    replaced rather than appended for the same reason.
    """

    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)

    values_: Mapped[Any] = mapped_column(
        # Quoted by hand: SQLAlchemy does not hold `values` to be reserved and
        # would emit it bare, which Postgres happens to accept in a column
        # definition and does not in every position a query can put it.
        quoted_name("values", True),
        JSONB,
        nullable=False,
        default=dict,
    )
    """What this run is performed with. The press is the only source of them:
    nothing a chat door understood is carried across on its own."""

    items: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    """What this run was asked to do the repeated block for: one set of values
    per thing on the list. Empty for every run of a job that does one thing
    once, which is most of them, and for every run made before repeats
    existed."""

    started_by: Mapped[str] = mapped_column(Text, nullable=False, default="")
    live: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_focus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """A real timestamp, where the rig kept text. The record still carries ISO
    strings, so this converts on the way in and out -- but a run whose clock is
    a string sorts a naive instant beside an offset-bearing one and neither is
    wrong, and ``started_at`` is what both indexes below order on."""

    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="running")

    from_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """How many steps the operator did before the offer was made. Stored so a
    re-press of this run can be checked against what the first press asked
    for -- without it the row cannot say whether a second press is the same
    job or a different one."""

    withheld: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    """The writes a dry run produced and did not send, in full. This is what a
    person reads before pressing through to live."""

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """A run that cost nothing and a run whose cost could not be established
    are the same row without this."""

    __table_args__ = (
        Index("ix_workflow_runs_tenant_workflow", "tenant_id", "workflow_id", "started_at"),
        # The busy check: whether this browser already has a run in flight.
        # One browser, one hand -- two runs driving the same window interleave
        # their clicks into a form neither of them can then read back.
        Index("ix_workflow_runs_tenant_device", "tenant_id", "device_id", "outcome"),
        # And the rule the index above can only report on. Reading "is this
        # browser busy" and then claiming it is two statements with awaits
        # between them, so two presses on one event loop both read free and
        # both claim -- demonstrated against real Postgres, two rows and one
        # browser. Migration 0039 named this index as what a second worker
        # would need; it turns out one worker needs it too, because async does
        # not give one request at a time.
        Index(
            "uq_workflow_runs_one_running_per_device",
            "tenant_id",
            "device_id",
            unique=True,
            postgresql_where=text("outcome = 'running'"),
        ),
    )


class WorkflowRunStepRow(Base):
    """One step of a run: what was planned, what was sent, and what it earned.

    No tenant of its own and no foreign key, as in the rig: a step is reached
    only through its run, which carries the tenant, and the run's save deletes
    and reinserts this whole set every time.
    """

    __tablename__ = "workflow_run_steps"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)

    says: Mapped[str] = mapped_column(Text, nullable=False, default="")

    made: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    """What the warehouse called the record this step created, where it made
    one. `{}` for every step that created nothing, which is most of them."""

    of_step: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    """Which step of the JOB this row is. `ord` is where in the RUN it happened,
    and the two are the same number until a job repeats its middle."""

    item: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Which thing on the list it was done for, or NULL for a step done once."""

    planned_by: Mapped[str | None] = mapped_column(Text)
    sent: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    """The command envelope's kind and payload, NULL for a step that sent
    nothing. ``none_as_null`` because JSONB otherwise stores ``None`` as the
    JSON scalar ``null``, which is not SQL NULL: ``sent IS NULL`` would be false
    and every reader that asks whether a step sent anything would be told yes.
    The rig wrote SQL NULL, and its readers test for it."""

    result: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    """What the extension answered, NULL when it never did -- the same reason."""

    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    verdict_by: Mapped[str] = mapped_column(String(24), nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    matched_by: Mapped[str | None] = mapped_column(Text)
    stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    before_url: Mapped[str | None] = mapped_column(Text)
    after_url: Mapped[str | None] = mapped_column(Text)

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ApprovalRow(Base):
    """An approval a person gave: which step of which run, when, and from where.

    The first tap wins; a second on the same step is not a second
    authorisation. That is the whole reason for the composite key -- a write
    rescued to the second rung parks at the same step and takes a second tap.

    Not deleted and rewritten with the run: the run record says a write went
    out, and this says a person let it.
    """

    __tablename__ = "approvals"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(64))
    """The browser whose panel the tap came from, when the panel named one. A
    bare POST is a tap, so this is nullable."""


class WorkflowRow(Base):
    """A workflow a mining pass found: what it says, and the shape it is known by.

    No cost of its own. One pass makes exactly one model call and proposes
    every workflow in it, so a workflow names the pass that found it rather
    than carrying a copy of the bill -- three workflows out of one $0.04 call
    summed to $0.12 when they each carried it, an overstatement that grew with
    how well the pass did.
    """

    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)

    pass_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    """Empty for a workflow saved outside a pass, which today is only a test."""

    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    narrative: Mapped[str] = mapped_column(Text, nullable=False, default="")
    systems: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    parameters: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)

    shape_key: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    """What identity resolution compares a new proposal against. Rewritten in
    place by ``rekey`` when the rule that makes a key changes, because keys
    mined before the change no longer match keys mined after and a job already
    held could then be proposed again as a new one."""

    repeat: Mapped[Any] = mapped_column(JSONB, nullable=True)
    """The steps this job does once per thing on a list, as `{first_step,
    last_step}`, or NULL for a job that does one thing once -- which is most of
    them and every job mined before repeats existed. JSONB rather than two
    integer columns because the pair is one fact and a row with one of them set
    is a row that means nothing."""

    same_as: Mapped[str | None] = mapped_column(String(64))
    """The model's opinion about whether this is one it has proposed before. It
    is recorded and it decides nothing: a model re-judging its own earlier
    verdict disagrees with itself at roughly 90%."""

    unproven: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_workflows_tenant_created", "tenant_id", "created_at"),)


class WorkflowStepRow(Base):
    """One step of a workflow, and the gestures that prove it.

    No tenant of its own and no foreign key, as in the rig: a step is reached
    only through its workflow, which carries the tenant, and the workflow's
    save deletes and reinserts this whole set every time.

    ``cites`` is the reason the mining prompt selects rather than generates:
    free-generated workflow JSON hallucinated up to 21% of steps, and forced to
    select from real evidence that fell below 7.5%. An uncited step is rejected.
    """

    __tablename__ = "workflow_steps"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)

    says: Mapped[str] = mapped_column(Text, nullable=False, default="")
    system: Mapped[str | None] = mapped_column(Text)
    cites: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)
    parameters: Mapped[Any] = mapped_column(JSONB, nullable=False, default=list)


class WorkflowStaleRow(Base):
    """A step whose control was only found by the weakest rung of the locator
    ladder. The run succeeded; the step is about to break.

    One row per step, so a workflow run daily reports the same weak step once
    rather than daily. Kept apart from the workflow itself because that is what
    a mining pass writes and this is what a run learned -- rewriting the
    workflow from here would race a re-mine and lose one of the two.
    """

    __tablename__ = "workflow_stale"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)
    matched_by: Mapped[str | None] = mapped_column(Text)
    noticed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkflowEffectRow(Base):
    """One write a live run made and the verifier then saw hold by STATE -- a
    status the server answered, or a read that showed the record.

    Never by a picture: a model reading a screenshot is not evidence anything
    was written. Three runs whose every write is in here is what buys a job the
    right to write unasked, and one failed write empties it for that workflow.
    """

    __tablename__ = "workflow_effects"

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ord: Mapped[int] = mapped_column(Integer, primary_key=True)
    verified_by: Mapped[str] = mapped_column(String(24), nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MiningPassRow(Base):
    """One reading of one tenant's day, and what it cost.

    ``mining_passes`` rather than the rig's ``passes``: the shorter word says
    nothing about what kind of pass it is in a schema this size.

    Written whether the pass found anything or not -- including when it was
    refused, which is the only record left of a call that cost money and
    returned nothing.
    """

    __tablename__ = "mining_passes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Inside out_tokens, not beside them."""

    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    proposed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    kept: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    learned_parameters: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """What the pass LEARNT, beside what it kept. See `MiningPass`."""
    coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    skew: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lopsided: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    window_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    left_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """How much evidence this pass was shown, and how much the budget dropped.
    What the scheduled sweep reads to tell a tenant with more to say from one
    whose window already held everything. See `MiningPass`."""

    error: Mapped[str | None] = mapped_column(Text)
    """Why it found nothing, when it found nothing for a reason the API gave.
    An honest zero and a refused call are the same row without this."""

    __table_args__ = (Index("ix_mining_passes_tenant_started", "tenant_id", "started_at"),)


class OfferRow(Base):
    """One offer the extension made from a recognised prefix, and its fate.

    The labelled record of whether recognition was right: the share of
    ``diverged`` in a job's newest offers is what moves its threshold, and a run
    of refusals from one browser is what rests it there.

    ``seq`` is the rig's ``rowid`` tiebreak made explicit. The extension sends
    the browser's own clock, several offers can carry the same second, and the
    newest three of them decide whether a job is rested -- so "newest" has to
    mean arrival order once ``at`` ties, and Postgres promises no order at all
    without a column to say so.
    """

    __tablename__ = "offers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)

    k: Mapped[int] = mapped_column(Integer, nullable=False)
    """How many gestures of the tail matched when it was offered. Zero is an
    arrival nudge -- "you have been here before", nothing typed -- which is
    neither kind of evidence and is filtered out of the counsel window."""

    fate: Mapped[str] = mapped_column(String(16), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_offers_tenant_workflow", "tenant_id", "workflow_id", "at"),)


class ChatRow(Base):
    """One sentence the chat door read, and what the reading cost.

    The sentence is not here and there is no column for it: it is an operator's
    words about their warehouse, and the row exists for the cap and the spend
    line, neither of which needs them.
    """

    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    workflow_id: Mapped[str | None] = mapped_column(String(64))
    """The job the sentence turned out to be about, when it was about one."""

    in_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    out_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thought_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """Inside out_tokens, not beside them."""

    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unpriced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """A reading that cost nothing and a reading nobody could price are the
    same row without this, and the day's bill is understated silently."""

    error: Mapped[str | None] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_chats_tenant_at", "tenant_id", "at"),)
