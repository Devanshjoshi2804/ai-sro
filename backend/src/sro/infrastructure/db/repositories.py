"""Postgres-backed repositories and the unit of work.

Reads are always filtered by ``tenant_id`` as well as by id. A row belonging to
another tenant is reported as ``NotFound``, which is the same answer as a row
that does not exist -- the difference is not something a caller may learn.
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from sro.application.ports.repositories import (
    BrowserSessionRepository,
    CandidateRepository,
    ConfirmationRepository,
    ConnectionRepository,
    DeviceRepository,
    KnowledgeRepository,
    ModelCallRepository,
    ObservationPolicyRepository,
    ObservationRepository,
    RecordingRepository,
    RunRepository,
    SkillRepository,
    ThreadRepository,
    ToolCallRepository,
    TriggerRepository,
    UnitOfWork,
)
from sro.domain.chat.thread import Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Run, RunId
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import (
    BatchId,
    BrowserSessionId,
    CandidateId,
    ConfirmationId,
    DeviceId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
    TriggerId,
)
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.skill import Skill
from sro.domain.trigger.confirmation import Answer, Confirmation
from sro.domain.trigger.trigger import Trigger
from sro.infrastructure.db.codec import dump_policy, when
from sro.infrastructure.db.evidence import SqlGestureRepository, SqlPoolRepository
from sro.infrastructure.db.mappers import (
    batch_to_row,
    candidate_to_row,
    confirmation_to_row,
    connection_to_row,
    device_to_row,
    knowledge_to_row,
    model_call_to_row,
    objective_columns,
    policy_to_row,
    recording_to_row,
    row_to_batch,
    row_to_candidate,
    row_to_confirmation,
    row_to_connection,
    row_to_device,
    row_to_knowledge,
    row_to_model_call,
    row_to_policy,
    row_to_recording,
    row_to_run,
    row_to_skill,
    row_to_thread,
    row_to_trigger,
    run_to_row,
    skill_to_row,
    thread_to_row,
    trigger_to_row,
    update_candidate_row,
    update_confirmation_row,
    update_connection_row,
    update_device_row,
    update_knowledge_row,
    update_recording_row,
    update_run_row,
    update_skill_row,
    update_thread_row,
    update_trigger_row,
)
from sro.infrastructure.db.models import (
    AgentDeviceRow,
    BrowserSessionRow,
    ConfirmationRow,
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
    ToolCallRow,
    TriggerRow,
)
from sro.infrastructure.db.offers import SqlChatRepository, SqlOfferRepository
from sro.infrastructure.db.spend import SqlSpendRepository
from sro.infrastructure.db.workflow_runs import SqlWorkflowRunRepository
from sro.infrastructure.db.workflows import SqlWorkflowRepository


class SqlRecordingRepository(RecordingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, recording: Recording) -> None:
        self._session.add(recording_to_row(recording))

    async def get(self, tenant_id: TenantId, recording_id: RecordingId) -> Recording:
        return row_to_recording(await self._row(tenant_id, recording_id))

    async def save(self, recording: Recording) -> None:
        row = await self._row(recording.tenant_id, recording.id)
        update_recording_row(row, recording)

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        objective_key: ObjectiveKey | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Recording, ...]:
        query = select(RecordingRow).where(RecordingRow.tenant_id == tenant_id.value)
        if objective_key is not None:
            for column, value in objective_columns(objective_key).items():
                query = query.where(getattr(RecordingRow, column) == value)
        query = query.order_by(RecordingRow.started_at.desc()).limit(limit).offset(offset)

        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_recording(row) for row in rows)

    async def _row(self, tenant_id: TenantId, recording_id: RecordingId) -> RecordingRow:
        query = select(RecordingRow).where(
            RecordingRow.id == recording_id.value,
            RecordingRow.tenant_id == tenant_id.value,
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"recording {recording_id} not found")
        return row

    async def list_capturing(self) -> tuple[Recording, ...]:
        query = select(RecordingRow).where(RecordingRow.status == RecordingStatus.CAPTURING.value)
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_recording(row) for row in rows)


class SqlSkillRepository(SkillRepository):
    """Holds on to the rows it read, for as long as the unit of work lasts.

    SQLAlchemy's identity map is weak, and a repository that loads a row, builds
    an aggregate out of it and drops the row leaves nothing referring to it --
    so the row is collected and the next `save` re-reads it. That re-read is
    what defeated the version check on `skills`: it fetched, and believed, a
    `latest_version` somebody else had committed in between, and then wrote over
    them. Keeping the row is what makes "the version I read" mean anything.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._read: dict[str, SkillRow] = {}

    async def add(self, skill: Skill) -> None:
        self._session.add(self._kept(skill_to_row(skill)))

    async def get(self, tenant_id: TenantId, skill_id: SkillId) -> Skill:
        return row_to_skill(self._kept(await self._row(tenant_id, skill_id)))

    async def save(self, skill: Skill) -> None:
        row = self._read.get(skill.id.value) or await self._row(skill.tenant_id, skill.id)
        update_skill_row(row, skill)

    def _kept(self, row: SkillRow) -> SkillRow:
        self._read[row.id] = row
        return row

    async def find_by_objective(
        self, tenant_id: TenantId, objective_key: ObjectiveKey
    ) -> Skill | None:
        query = select(SkillRow).where(SkillRow.tenant_id == tenant_id.value)
        for column, value in objective_columns(objective_key).items():
            query = query.where(getattr(SkillRow, column) == value)

        row = (await self._session.execute(query)).scalar_one_or_none()
        return row_to_skill(self._kept(row)) if row is not None else None

    async def list_for_tenant(
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Skill, ...]:
        query = (
            select(SkillRow)
            .where(SkillRow.tenant_id == tenant_id.value)
            .order_by(SkillRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_skill(self._kept(row)) for row in rows)

    async def _row(self, tenant_id: TenantId, skill_id: SkillId) -> SkillRow:
        query = select(SkillRow).where(
            SkillRow.id == skill_id.value, SkillRow.tenant_id == tenant_id.value
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"skill {skill_id} not found")
        return row


class SqlConnectionRepository(ConnectionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, connection: Connection) -> None:
        self._session.add(connection_to_row(connection))

    async def get(self, tenant_id: TenantId, connection_id: ConnectionId) -> Connection:
        return row_to_connection(await self._row(tenant_id, connection_id))

    async def save(self, connection: Connection) -> None:
        row = await self._row(connection.tenant_id, connection.id)
        update_connection_row(row, connection)

    async def find_by_system(self, tenant_id: TenantId, target_system: str) -> Connection | None:
        query = select(ConnectionRow).where(
            ConnectionRow.tenant_id == tenant_id.value,
            ConnectionRow.target_system == target_system,
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        return row_to_connection(row) if row is not None else None

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[Connection, ...]:
        query = (
            select(ConnectionRow)
            .where(ConnectionRow.tenant_id == tenant_id.value)
            .order_by(ConnectionRow.created_at.desc())
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_connection(row) for row in rows)

    async def _row(self, tenant_id: TenantId, connection_id: ConnectionId) -> ConnectionRow:
        query = select(ConnectionRow).where(
            ConnectionRow.id == connection_id.value,
            ConnectionRow.tenant_id == tenant_id.value,
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"connection {connection_id} not found")
        return row

    async def list_connected(self) -> tuple[Connection, ...]:
        query = select(ConnectionRow).where(
            ConnectionRow.status == ConnectionStatus.CONNECTED.value
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_connection(row) for row in rows)


class SqlRunRepository(RunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: Run) -> None:
        self._session.add(run_to_row(run))

    async def get(self, tenant_id: TenantId, run_id: RunId) -> Run:
        return row_to_run(await self._row(tenant_id, run_id))

    async def save(self, run: Run) -> None:
        update_run_row(await self._row(run.tenant_id, run.id), run)

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        skill_id: SkillId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Run, ...]:
        query = select(RunRow).where(RunRow.tenant_id == tenant_id.value)
        if skill_id is not None:
            query = query.where(RunRow.skill_id == skill_id.value)
        query = query.order_by(RunRow.started_at.desc()).limit(limit).offset(offset)
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_run(row) for row in rows)

    async def since(self, tenant_id: TenantId, *, since: datetime) -> tuple[Run, ...]:
        query = (
            select(RunRow)
            .where(RunRow.tenant_id == tenant_id.value, RunRow.started_at >= since)
            .order_by(RunRow.started_at)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_run(row) for row in rows)

    async def finished_since(
        self, tenant_id: TenantId, *, target_system: str, since: datetime
    ) -> tuple[Run, ...]:
        query = select(RunRow).where(
            RunRow.tenant_id == tenant_id.value,
            # Keyed by it, or one of the systems it touched on the way. A
            # workflow that fails in its second system is stored under the
            # first, and a breaker that could not see that would be protecting
            # nothing while appearing to.
            or_(
                RunRow.target_system == target_system,
                RunRow.systems.contains([target_system]),
            ),
            RunRow.ended_at.is_not(None),
            RunRow.ended_at >= since,
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_run(row) for row in rows)

    async def _row(self, tenant_id: TenantId, run_id: RunId) -> RunRow:
        query = select(RunRow).where(RunRow.id == run_id.value, RunRow.tenant_id == tenant_id.value)
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"run {run_id} not found")
        return row


_NOT_WORTH_MATCHING = frozenset({"a", "an", "the", "at", "in", "on", "of", "to", "for", "and"})


def _terms(text: str) -> list[str]:
    """Words worth matching. Two characters or fewer match everything."""
    return [
        word
        for word in re.findall(r"[A-Za-z0-9]+", text.lower())
        if len(word) > 2 and word not in _NOT_WORTH_MATCHING
    ]


class SqlKnowledgeRepository(KnowledgeRepository):
    """Structured filters narrow, similarity only orders.

    A nearest-neighbour search across the whole store answers confidently with
    another system's endpoint, so system and kind are `WHERE` clauses and the
    vector is an `ORDER BY`. Superseded rows never come back: they are history,
    not belief.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: KnowledgeEntry) -> None:
        self._session.add(knowledge_to_row(entry))

    async def save(self, entry: KnowledgeEntry) -> None:
        query = select(KnowledgeRow).where(KnowledgeRow.id == str(entry.id))
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"knowledge entry {entry.id} not found")
        update_knowledge_row(row, entry)

    async def current(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str
    ) -> KnowledgeEntry | None:
        query = select(KnowledgeRow).where(
            KnowledgeRow.tenant_id == tenant_id.value,
            KnowledgeRow.system == system,
            KnowledgeRow.kind == kind.value,
            KnowledgeRow.key == key,
            KnowledgeRow.superseded_by.is_(None),
        )
        row = (await self._session.execute(query)).scalars().first()
        return row_to_knowledge(row) if row is not None else None

    async def history(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str, limit: int = 10
    ) -> tuple[KnowledgeEntry, ...]:
        query = (
            select(KnowledgeRow)
            .where(
                KnowledgeRow.tenant_id == tenant_id.value,
                KnowledgeRow.system == system,
                KnowledgeRow.kind == kind.value,
                KnowledgeRow.key == key,
            )
            .order_by(KnowledgeRow.observed_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_knowledge(row) for row in rows)

    async def without_embedding(
        self, tenant_id: TenantId, *, limit: int = 200
    ) -> tuple[KnowledgeEntry, ...]:
        query = (
            select(KnowledgeRow)
            .where(
                KnowledgeRow.tenant_id == tenant_id.value,
                KnowledgeRow.superseded_by.is_(None),
                KnowledgeRow.embedding.is_(None),
            )
            .limit(limit)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_knowledge(row) for row in rows)

    async def search(
        self,
        tenant_id: TenantId,
        *,
        system: str | None = None,
        kinds: tuple[EntryKind, ...] = (),
        terms: str = "",
        embedding: tuple[float, ...] = (),
        min_evidence: EvidenceLevel | None = None,
        limit: int = 20,
    ) -> tuple[KnowledgeEntry, ...]:
        query = select(KnowledgeRow).where(
            KnowledgeRow.tenant_id == tenant_id.value,
            KnowledgeRow.superseded_by.is_(None),
        )
        if system:
            query = query.where(KnowledgeRow.system == system)
        if kinds:
            query = query.where(KnowledgeRow.kind.in_([kind.value for kind in kinds]))
        if min_evidence is not None:
            # In the query, not after it: filtering the page would hide strong
            # claims behind weak ones that happened to sort first.
            query = query.where(
                KnowledgeRow.evidence.in_(
                    [level.value for level in EvidenceLevel if level.rank >= min_evidence.rank]
                )
            )
        if words := _terms(terms):
            # Any word, not the whole phrase. "add a carrier" ILIKE'd whole
            # matches nothing, and a sentence is how the question arrives.
            query = query.where(
                or_(
                    *[
                        clause
                        for word in words
                        for clause in (
                            KnowledgeRow.title.ilike(f"%{word}%"),
                            KnowledgeRow.key.ilike(f"%{word}%"),
                        )
                    ]
                )
            )
        if embedding:
            query = query.where(KnowledgeRow.embedding.is_not(None)).order_by(
                KnowledgeRow.embedding.cosine_distance(list(embedding))
            )
        else:
            # Best evidence first when there is no distance to sort by: a
            # reproduced claim outranks a scraped one for the same question.
            query = query.order_by(KnowledgeRow.observed_at.desc())
        rows = (await self._session.execute(query.limit(limit))).scalars().all()
        return tuple(row_to_knowledge(row) for row in rows)


class SqlThreadRepository(ThreadRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, thread: Thread) -> None:
        self._session.add(thread_to_row(thread))

    async def get(self, tenant_id: TenantId, thread_id: ThreadId) -> Thread:
        return row_to_thread(await self._row(tenant_id, thread_id))

    async def save(self, thread: Thread) -> None:
        update_thread_row(await self._row(thread.tenant_id, thread.id), thread)

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        opened_by: PrincipalId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Thread, ...]:
        query = select(ThreadRow).where(ThreadRow.tenant_id == tenant_id.value)
        if opened_by is not None:
            query = query.where(ThreadRow.opened_by == opened_by.value)
        query = query.order_by(ThreadRow.opened_at.desc()).limit(limit).offset(offset)
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_thread(row) for row in rows)

    async def _row(self, tenant_id: TenantId, thread_id: ThreadId) -> ThreadRow:
        query = select(ThreadRow).where(
            ThreadRow.id == thread_id.value, ThreadRow.tenant_id == tenant_id.value
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"thread {thread_id} not found")
        return row


class SqlModelCallRepository(ModelCallRepository):
    """Append-only. A model call is a fact about what left the deployment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, call: ModelCall) -> None:
        self._session.add(model_call_to_row(call))

    async def list_for_run(self, tenant_id: TenantId, run_id: RunId) -> tuple[ModelCall, ...]:
        query = (
            select(ModelCallRow)
            .where(ModelCallRow.tenant_id == tenant_id.value, ModelCallRow.run_id == run_id.value)
            .order_by(ModelCallRow.started_at)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_model_call(row) for row in rows)


class SqlBrowserSessionRepository(BrowserSessionRepository):
    """Ownership of a browser, and nothing else about it.

    No ``_row(tenant_id, id)`` helper here because nothing fetches one row by
    id: the two-predicate check is ``held_by``, and ``release`` is untenanted on
    purpose -- the sweep and crash recovery are not anybody's request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim(
        self,
        tenant_id: TenantId,
        session_id: BrowserSessionId,
        opened_by: PrincipalId,
        opened_at: datetime,
    ) -> None:
        self._session.add(
            BrowserSessionRow(
                session_id=session_id.value,
                tenant_id=tenant_id.value,
                opened_by=opened_by.value,
                opened_at=opened_at,
            )
        )
        try:
            # Flushed here rather than at commit: the caller is about to hand a
            # browser to somebody, and "who owns this" has to be settled before
            # they get it, not after the request has already done its work.
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"browser session {session_id} is already held") from clash

    async def held_by(self, tenant_id: TenantId) -> tuple[BrowserSessionId, ...]:
        rows = await self._session.execute(
            select(BrowserSessionRow.session_id).where(
                BrowserSessionRow.tenant_id == tenant_id.value
            )
        )
        return tuple(BrowserSessionId(held) for held in rows.scalars())

    async def all_held(self) -> tuple[tuple[BrowserSessionId, datetime], ...]:
        rows = await self._session.execute(
            select(BrowserSessionRow.session_id, BrowserSessionRow.opened_at)
        )
        return tuple((BrowserSessionId(held), opened_at) for held, opened_at in rows)

    async def release(self, session_id: BrowserSessionId) -> None:
        await self._session.execute(
            delete(BrowserSessionRow).where(BrowserSessionRow.session_id == session_id.value)
        )


class SqlDeviceRepository(DeviceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, device: AgentDevice) -> None:
        self._session.add(device_to_row(device))
        try:
            # Flushed here, like the observation batch: two registrations for
            # the same (tenant, principal, label) racing each other must not
            # let the second one 500 instead of finding the first via
            # `registered_as` the way RegisterDevice's own idempotency assumes.
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"a device is already registered as {device.label!r}") from clash

    async def get(self, tenant_id: TenantId, device_id: DeviceId) -> AgentDevice:
        return row_to_device(await self._row(tenant_id, device_id))

    async def save(self, device: AgentDevice) -> None:
        update_device_row(await self._row(device.tenant_id, device.id), device)

    async def registered_as(
        self, tenant_id: TenantId, principal_id: PrincipalId, label: str
    ) -> AgentDevice | None:
        query = select(AgentDeviceRow).where(
            AgentDeviceRow.tenant_id == tenant_id.value,
            AgentDeviceRow.principal_id == principal_id.value,
            AgentDeviceRow.label == label,
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        return None if row is None else row_to_device(row)

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[AgentDevice, ...]:
        query = (
            select(AgentDeviceRow)
            .where(AgentDeviceRow.tenant_id == tenant_id.value)
            .order_by(AgentDeviceRow.last_seen_at.desc())
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_device(row) for row in rows)

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[AgentDevice, ...]:
        # Registered since, or revoked since: the audit is asking who could
        # act and until when, and a browser registered last month and revoked
        # this morning is part of this morning's answer.
        #
        # Tenant-scoped, where the rig's audit select was not: its device query
        # had no `tenant = ?` at all, so one tenant's audit listed every
        # tenant's browsers by id. That is a leak rather than a rule, and it
        # does not travel.
        at = when(since)
        query = (
            select(AgentDeviceRow)
            .where(
                AgentDeviceRow.tenant_id == tenant_id.value,
                or_(AgentDeviceRow.registered_at >= at, AgentDeviceRow.revoked_at >= at),
            )
            # On the id as well, as the audit's other three reads all are:
            # `workflow_runs.since` and `chats.since` on `id DESC`,
            # `offers.since` on `seq DESC`. Two browsers registered in the same
            # instant -- one operator installing on two profiles, a fixture
            # planting a morning -- have no order at all under
            # `registered_at` alone, so the same audit read twice could report
            # them two ways and a reader diffing the two saw a change nobody
            # made.
            .order_by(AgentDeviceRow.registered_at.desc(), AgentDeviceRow.id.desc())
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_device(row) for row in rows)

    async def revoke(self, tenant_id: TenantId, device_id: DeviceId, *, at: str) -> bool:
        # Read then set, rather than a conditional UPDATE: the row is the one
        # `get` in this session already holds, so nothing here can leave a
        # caller reading a browser it has just revoked as still live. `_row`
        # raises `NotFound` for a device this tenant does not have, which is a
        # different answer from "there was nothing live to revoke".
        #
        # Locked, because the read and the set are what the rig did atomically
        # in one `UPDATE ... WHERE revoked_at IS NULL`: without the lock two
        # concurrent revocations both read a live browser, both answer True,
        # and the second overwrites the instant the first recorded -- which is
        # precisely what this promises cannot happen.
        row = await self._row(tenant_id, device_id, lock=True)
        if row.revoked_at is not None:
            # The first revocation stands. A second press must not move the
            # instant the authority ended -- that instant is what an audit of
            # what this browser was allowed to do is read against.
            return False
        # UTC when it said nothing: this is the server's own clock, and a naive
        # local instant beside the aware ones reads as a revocation hours before
        # the browser registered.
        row.revoked_at = when(at)
        return True

    async def restore(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        # Read then set under the same lock as `revoke`, and for the same two
        # reasons: the row is the one this session already holds, so nothing
        # can read a browser it has just restored as still revoked; and two
        # concurrent presses must not both answer True, because the boolean is
        # what the route reports as "this press is what moved it".
        #
        # `revoked_at = NULL` and nothing else. The secret is not reissued --
        # revoking never blanked it, and the extension is still holding the one
        # it was minted with.
        row = await self._row(tenant_id, device_id, lock=True)
        if row.revoked_at is None:
            return False
        row.revoked_at = None
        return True

    async def _row(
        self, tenant_id: TenantId, device_id: DeviceId, *, lock: bool = False
    ) -> AgentDeviceRow:
        query = select(AgentDeviceRow).where(
            AgentDeviceRow.id == device_id.value,
            AgentDeviceRow.tenant_id == tenant_id.value,
        )
        if lock:
            # FOR UPDATE, and only where a caller is about to write what it
            # read. Every other read here is a read.
            query = query.with_for_update()
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"device {device_id} was not found")
        return row


class SqlObservationRepository(ObservationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, batch: ObservationBatch) -> None:
        self._session.add(batch_to_row(batch))
        try:
            # Flushed here rather than at commit: the id is the extension's, and
            # whether this upload is a retry has to be settled before the
            # response says how many events were kept.
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"observation batch {batch.id} is already stored") from clash

    async def get(self, tenant_id: TenantId, batch_id: BatchId) -> ObservationBatch | None:
        query = select(ObservationBatchRow).where(
            ObservationBatchRow.id == batch_id.value,
            ObservationBatchRow.tenant_id == tenant_id.value,
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        return None if row is None else row_to_batch(row)

    async def between(
        self,
        tenant_id: TenantId,
        *,
        since: datetime,
        until: datetime | None = None,
        principal_id: PrincipalId | None = None,
    ) -> tuple[ObservationBatch, ...]:
        # Overlap, not containment: a batch that began before the window and
        # ended inside it holds events the window asked for.
        query = select(ObservationBatchRow).where(
            ObservationBatchRow.tenant_id == tenant_id.value,
            ObservationBatchRow.ended_at >= since,
        )
        if until is not None:
            query = query.where(ObservationBatchRow.started_at <= until)
        if principal_id is not None:
            query = query.where(ObservationBatchRow.principal_id == principal_id.value)
        query = query.order_by(ObservationBatchRow.started_at)
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_batch(row) for row in rows)

    async def for_recording(
        self, tenant_id: TenantId, recording_id: RecordingId
    ) -> tuple[ObservationBatch, ...]:
        query = (
            select(ObservationBatchRow)
            .where(
                ObservationBatchRow.tenant_id == tenant_id.value,
                ObservationBatchRow.recording_id == recording_id.value,
            )
            .order_by(ObservationBatchRow.started_at)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_batch(row) for row in rows)

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]:
        rows = await self._session.execute(
            select(ObservationBatchRow.tenant_id)
            .where(ObservationBatchRow.ended_at >= since)
            .distinct()
        )
        return tuple(TenantId(tenant) for tenant in rows.scalars())

    async def forget(self, tenant_id: TenantId, ids: tuple[BatchId, ...]) -> None:
        if not ids:
            return
        await self._session.execute(
            delete(ObservationBatchRow).where(
                ObservationBatchRow.tenant_id == tenant_id.value,
                ObservationBatchRow.id.in_([batch_id.value for batch_id in ids]),
            )
        )


class SqlCandidateRepository(CandidateRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, candidate: TaskCandidate) -> None:
        self._session.add(candidate_to_row(candidate))
        try:
            # A manual mine-now request can race the scheduled sweep onto the
            # same new (tenant, principal, signature). Flushed here so that
            # collision fails on its own row rather than rolling back every
            # candidate the rest of that mining pass already found.
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"a candidate already exists for {candidate.signature!r}") from clash

    async def get(self, tenant_id: TenantId, candidate_id: CandidateId) -> TaskCandidate:
        return row_to_candidate(await self._row(tenant_id, candidate_id))

    async def save(self, candidate: TaskCandidate) -> None:
        update_candidate_row(await self._row(candidate.tenant_id, candidate.id), candidate)

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        status: CandidateStatus | None = None,
        principal_id: PrincipalId | None = None,
        seen_at_least: int = 0,
        host: str | None = None,
    ) -> tuple[TaskCandidate, ...]:
        query = select(TaskCandidateRow).where(TaskCandidateRow.tenant_id == tenant_id.value)
        if status is not None:
            query = query.where(TaskCandidateRow.status == status.value)
        if principal_id is not None:
            query = query.where(TaskCandidateRow.principal_id == principal_id.value)
        if seen_at_least:
            query = query.where(TaskCandidateRow.times_seen >= seen_at_least)
        if host:
            # Stored lowercased by the segmenter, so the caller's spelling of a
            # hostname does not decide whether their own tasks come back.
            query = query.where(TaskCandidateRow.host == host.lower())
        query = query.order_by(TaskCandidateRow.times_seen.desc())
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_candidate(row) for row in rows)

    async def _row(self, tenant_id: TenantId, candidate_id: CandidateId) -> TaskCandidateRow:
        query = select(TaskCandidateRow).where(
            TaskCandidateRow.id == candidate_id.value,
            TaskCandidateRow.tenant_id == tenant_id.value,
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"candidate {candidate_id} was not found")
        return row


class SqlObservationPolicyRepository(ObservationPolicyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: TenantId) -> ObservationPolicy | None:
        row = await self._session.get(ObservationPolicyRow, tenant_id.value)
        return None if row is None else row_to_policy(row)

    async def save(self, tenant_id: TenantId, policy: ObservationPolicy) -> None:
        row = await self._session.get(ObservationPolicyRow, tenant_id.value)
        if row is None:
            self._session.add(policy_to_row(tenant_id, policy))
            return
        row.version = policy.version
        row.policy = dump_policy(policy)


class SqlConfirmationRepository(ConfirmationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, confirmation: Confirmation) -> None:
        self._session.add(confirmation_to_row(confirmation))

    async def get(self, tenant_id: TenantId, confirmation_id: ConfirmationId) -> Confirmation:
        return row_to_confirmation(await self._row(tenant_id, confirmation_id))

    async def save(self, confirmation: Confirmation) -> None:
        update_confirmation_row(
            await self._row(confirmation.tenant_id, confirmation.id), confirmation
        )

    async def waiting(self, tenant_id: TenantId) -> tuple[Confirmation, ...]:
        rows = (
            await self._session.execute(
                select(ConfirmationRow)
                .where(
                    ConfirmationRow.tenant_id == tenant_id.value,
                    ConfirmationRow.answer == Answer.WAITING.value,
                )
                .order_by(ConfirmationRow.asked_at)
            )
        ).scalars()
        return tuple(row_to_confirmation(row) for row in rows)

    async def _row(self, tenant_id: TenantId, confirmation_id: ConfirmationId) -> ConfirmationRow:
        row = (
            await self._session.execute(
                select(ConfirmationRow).where(
                    ConfirmationRow.id == confirmation_id.value,
                    ConfirmationRow.tenant_id == tenant_id.value,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFound(f"confirmation {confirmation_id} not found")
        return row


class SqlToolCallRepository(ToolCallRepository):
    """The claim is the insert. Two writers racing for one key both try it, the
    primary key refuses one of them, and that refusal is the answer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def remember(self, tenant_id: TenantId, key: str, *, tool: str, at: datetime) -> bool:
        # `ON CONFLICT DO NOTHING` rather than a read followed by a write:
        # between the two of those, the other run inserts.
        claimed = await self._session.execute(
            pg_insert(ToolCallRow)
            .values(
                tenant_id=tenant_id.value,
                idempotency_key=key,
                tool=tool,
                claimed_at=at,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"])
            # What came back rather than how many rows: `rowcount` is the
            # driver's, and asking the statement to return the key it wrote
            # answers the same question in one shape everywhere.
            .returning(ToolCallRow.idempotency_key)
        )
        return claimed.scalar_one_or_none() is not None


class SqlTriggerRepository(TriggerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, trigger: Trigger) -> None:
        self._session.add(trigger_to_row(trigger))

    async def get(self, tenant_id: TenantId, trigger_id: TriggerId) -> Trigger:
        return row_to_trigger(await self._row(tenant_id, trigger_id))

    async def save(self, trigger: Trigger) -> None:
        update_trigger_row(await self._row(trigger.tenant_id, trigger.id), trigger)

    async def remove(self, tenant_id: TenantId, trigger_id: TriggerId) -> None:
        await self._session.execute(
            delete(TriggerRow).where(
                TriggerRow.id == trigger_id.value, TriggerRow.tenant_id == tenant_id.value
            )
        )

    async def list_for_tenant(
        self, tenant_id: TenantId, *, skill_id: SkillId | None = None
    ) -> tuple[Trigger, ...]:
        query = select(TriggerRow).where(TriggerRow.tenant_id == tenant_id.value)
        if skill_id is not None:
            query = query.where(TriggerRow.skill_id == skill_id.value)
        rows = (await self._session.execute(query.order_by(TriggerRow.created_at.desc()))).scalars()
        return tuple(row_to_trigger(row) for row in rows.all())

    async def find(self, trigger_id: TriggerId) -> Trigger | None:
        row = await self._session.get(TriggerRow, trigger_id.value)
        return None if row is None else row_to_trigger(row)

    async def _row(self, tenant_id: TenantId, trigger_id: TriggerId) -> TriggerRow:
        query = select(TriggerRow).where(
            TriggerRow.id == trigger_id.value, TriggerRow.tenant_id == tenant_id.value
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"trigger {trigger_id} was not found")
        return row


class SqlUnitOfWork(UnitOfWork):
    """One session per block. The session opens on entry, not on construction,
    so a unit of work can be built once and used per request."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlUnitOfWork:
        self._session = self._session_factory()
        self.recordings = SqlRecordingRepository(self._session)
        self.skills = SqlSkillRepository(self._session)
        self.connections = SqlConnectionRepository(self._session)
        self.runs = SqlRunRepository(self._session)
        self.knowledge = SqlKnowledgeRepository(self._session)
        self.model_calls = SqlModelCallRepository(self._session)
        self.threads = SqlThreadRepository(self._session)
        self.browser_sessions = SqlBrowserSessionRepository(self._session)
        self.devices = SqlDeviceRepository(self._session)
        self.observations = SqlObservationRepository(self._session)
        self.gestures = SqlGestureRepository(self._session)
        self.workflow_runs = SqlWorkflowRunRepository(self._session)
        self.workflows = SqlWorkflowRepository(self._session)
        self.offers = SqlOfferRepository(self._session)
        self.chats = SqlChatRepository(self._session)
        self.spend = SqlSpendRepository(self._session)
        self.pool = SqlPoolRepository(self._session)
        self.observation_policies = SqlObservationPolicyRepository(self._session)
        self.candidates = SqlCandidateRepository(self._session)
        self.triggers = SqlTriggerRepository(self._session)
        self.tool_calls = SqlToolCallRepository(self._session)
        self.confirmations = SqlConfirmationRepository(self._session)
        return self

    async def __aexit__(self, *exc: object) -> None:
        session = self._require_session()
        try:
            if exc[0] is not None:
                await session.rollback()
        finally:
            await session.close()
            self._session = None

    async def commit(self) -> None:
        try:
            await self._require_session().commit()
        except StaleDataError as clash:
            # Somebody wrote the row between this block reading it and
            # committing, and the write that was about to land was computed
            # from what it read. Reported as a conflict rather than a crash
            # because it is one: the caller decides whether to redo the work
            # against what is there now or to leave it to whoever comes next.
            await self._require_session().rollback()
            raise Conflict(str(clash)) from clash

    async def rollback(self) -> None:
        await self._require_session().rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("SqlUnitOfWork must be used as an async context manager")
        return self._session
