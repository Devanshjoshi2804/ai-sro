from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import (
    ColumnElement,
    CursorResult,
    case,
    delete,
    exists,
    literal,
    or_,
    select,
    text,
    update,
)
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
from sro.domain.execution.account import K_LEASE_TTL, LIVE, Account, Lease, LeaseState
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Run, RunId
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.errors import Conflict, InvariantViolation, NotFound
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
from sro.infrastructure.db.attempts import SqlAttemptRepository
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
    WorkflowRow,
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

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        busy: str | None = await self._session.scalar(
            select(RunRow.id)
            .where(
                RunRow.tenant_id == tenant_id.value,
                RunRow.device_id == device_id.value,
                RunRow.ended_at.is_(None),
            )
            .order_by(RunRow.started_at.desc())
            .limit(1)
        )
        return busy

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
    return [
        word
        for word in re.findall(r"[A-Za-z0-9]+", text.lower())
        if len(word) > 2 and word not in _NOT_WORTH_MATCHING
    ]


class SqlKnowledgeRepository(KnowledgeRepository):
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
            query = query.where(
                KnowledgeRow.evidence.in_(
                    [level.value for level in EvidenceLevel if level.rank >= min_evidence.rank]
                )
            )
        matched: Any = None
        if words := _terms(terms):
            hits = [
                or_(
                    KnowledgeRow.title.ilike(f"%{word}%"),
                    KnowledgeRow.key.ilike(f"%{word}%"),
                )
                for word in words
            ]
            query = query.where(or_(*hits))
            matched = sum(
                (case((hit, 1), else_=0) for hit in hits),
                start=literal(0),
            )
        if embedding:
            await self._session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))
            query = query.where(KnowledgeRow.embedding.is_not(None)).order_by(
                *([] if matched is None else [matched.desc()]),
                KnowledgeRow.embedding.cosine_distance(list(embedding)),
            )
        else:
            query = query.order_by(
                *([] if matched is None else [matched.desc()]),
                KnowledgeRow.observed_at.desc(),
            )
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


_LIVE_STATES = tuple(state.value for state in LIVE)


def _lease_of(row: BrowserSessionRow) -> Lease:
    if (
        row.state is None
        or row.origin is None
        or row.username is None
        or row.container_url is None
        or row.steel_session_id is None
        or row.context_id is None
        or row.holder is None
        or row.heartbeat_at is None
        or row.expires_at is None
    ):
        raise InvariantViolation(f"browser session {row.session_id} is not a whole lease")
    return Lease(
        id=row.session_id,
        account=Account(row.tenant_id, row.origin, row.username),
        container_url=row.container_url,
        steel_session_id=row.steel_session_id,
        context_id=row.context_id,
        holder=row.holder,
        heartbeat_at=row.heartbeat_at,
        expires_at=row.expires_at,
        state=LeaseState(row.state),
    )


class SqlBrowserSessionRepository(BrowserSessionRepository):
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
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"browser session {session_id} is already held") from clash

    async def held_by(self, tenant_id: TenantId) -> tuple[BrowserSessionId, ...]:
        rows = await self._session.execute(
            select(BrowserSessionRow.session_id).where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.state.is_(None),
            )
        )
        return tuple(BrowserSessionId(held) for held in rows.scalars())

    async def all_held(self) -> tuple[tuple[BrowserSessionId, datetime], ...]:
        rows = await self._session.execute(
            select(BrowserSessionRow.session_id, BrowserSessionRow.opened_at).where(
                BrowserSessionRow.state.is_(None)
            )
        )
        return tuple((BrowserSessionId(held), opened_at) for held, opened_at in rows)

    async def release(self, session_id: BrowserSessionId) -> None:
        await self._session.execute(
            delete(BrowserSessionRow).where(BrowserSessionRow.session_id == session_id.value)
        )

    async def lease(self, tenant_id: TenantId, lease: Lease) -> Lease:
        await self._session.execute(
            pg_insert(BrowserSessionRow)
            .values(
                session_id=lease.id,
                tenant_id=tenant_id.value,
                opened_at=lease.heartbeat_at,
                account_key=lease.account.key,
                origin=lease.account.origin,
                username=lease.account.username,
                container_url=lease.container_url,
                steel_session_id=lease.steel_session_id,
                context_id=lease.context_id,
                holder=lease.holder,
                heartbeat_at=lease.heartbeat_at,
                expires_at=lease.expires_at,
                state=lease.state.value,
            )
            .on_conflict_do_nothing(
                index_elements=["tenant_id", "account_key"],
                index_where=BrowserSessionRow.state.in_(_LIVE_STATES),
            )
        )
        current = await self.current_lease(tenant_id, lease.account)
        if current is None:
            raise Conflict(f"lease {lease.id} lost the race for its account and was settled")
        return current

    async def current_lease(self, tenant_id: TenantId, account: Account) -> Lease | None:
        row = await self._session.scalar(
            select(BrowserSessionRow).where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.account_key == account.key,
                BrowserSessionRow.state.in_(_LIVE_STATES),
            )
        )
        return None if row is None else _lease_of(row)

    async def get_lease(self, tenant_id: TenantId, lease_id: str) -> Lease | None:
        row = await self._session.get(BrowserSessionRow, lease_id)
        if row is None or row.tenant_id != tenant_id.value or row.state is None:
            return None
        return _lease_of(row)

    async def settle(self, tenant_id: TenantId, lease_id: str, *, state: LeaseState) -> bool:
        if state is LeaseState.EXPIRED:
            raise ValueError("settle cannot move a lease to expired; use expire")
        result = await self._session.execute(
            update(BrowserSessionRow)
            .where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.session_id == lease_id,
                BrowserSessionRow.state.in_(_LIVE_STATES),
            )
            .values(state=state.value)
        )
        return cast(CursorResult[Any], result).rowcount > 0

    async def expire(self, tenant_id: TenantId, lease_id: str, *, now: datetime) -> bool:
        result = await self._session.execute(
            update(BrowserSessionRow)
            .where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.session_id == lease_id,
                BrowserSessionRow.state.in_(_LIVE_STATES),
                BrowserSessionRow.expires_at <= now,
            )
            .values(state=LeaseState.EXPIRED.value)
        )
        return cast(CursorResult[Any], result).rowcount > 0

    async def beat(
        self, tenant_id: TenantId, lease_id: str, *, now: datetime, holder: str | None = None
    ) -> bool:
        values: dict[str, object] = {"heartbeat_at": now, "expires_at": now + K_LEASE_TTL}
        if holder is not None:
            values["holder"] = holder
        result = await self._session.execute(
            update(BrowserSessionRow)
            .where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.session_id == lease_id,
                BrowserSessionRow.state.in_(_LIVE_STATES),
            )
            .values(**values)
        )
        return cast(CursorResult[Any], result).rowcount > 0

    async def expired(self, *, now: datetime) -> tuple[Lease, ...]:
        rows = await self._session.scalars(
            select(BrowserSessionRow).where(
                BrowserSessionRow.state.in_(_LIVE_STATES), BrowserSessionRow.expires_at <= now
            )
        )
        return tuple(_lease_of(row) for row in rows)

    async def busy_containers(self, tenant_id: TenantId, *, now: datetime) -> tuple[str, ...]:
        rows = await self._session.scalars(
            select(BrowserSessionRow.container_url).where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.state.in_(_LIVE_STATES),
                BrowserSessionRow.expires_at > now,
            )
        )
        return tuple(str(url) for url in rows)

    async def leased_sessions(self) -> frozenset[str]:
        rows = await self._session.scalars(
            select(BrowserSessionRow.steel_session_id).where(
                BrowserSessionRow.state.in_(_LIVE_STATES)
            )
        )
        return frozenset(str(one) for one in rows if one)


class SqlDeviceRepository(DeviceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, device: AgentDevice) -> None:
        self._session.add(device_to_row(device))
        try:
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
        at = when(since)
        query = (
            select(AgentDeviceRow)
            .where(
                AgentDeviceRow.tenant_id == tenant_id.value,
                or_(AgentDeviceRow.registered_at >= at, AgentDeviceRow.revoked_at >= at),
            )
            .order_by(AgentDeviceRow.registered_at.desc(), AgentDeviceRow.id.desc())
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(row_to_device(row) for row in rows)

    async def revoke(self, tenant_id: TenantId, device_id: DeviceId, *, at: str) -> bool:
        row = await self._row(tenant_id, device_id, lock=True)
        if row.revoked_at is not None:
            return False
        row.revoked_at = when(at)
        return True

    async def restore(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
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

    async def received_before(
        self, tenant_id: TenantId, cutoff: datetime
    ) -> tuple[ObservationBatch, ...]:
        query = (
            select(ObservationBatchRow)
            .where(
                ObservationBatchRow.tenant_id == tenant_id.value,
                ObservationBatchRow.received_at <= cutoff,
            )
            .order_by(ObservationBatchRow.received_at)
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

    async def tenants_waiting(self) -> tuple[TenantId, ...]:
        rows = await self._session.execute(
            select(ConfirmationRow.tenant_id)
            .where(ConfirmationRow.answer == Answer.WAITING.value)
            .distinct()
        )
        return tuple(TenantId(tenant) for tenant in rows.scalars())

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
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def remember(
        self,
        tenant_id: TenantId,
        key: str,
        *,
        tool: str,
        at: datetime,
        stale_after: timedelta | None = None,
    ) -> bool:
        insert = pg_insert(ToolCallRow).values(
            tenant_id=tenant_id.value,
            idempotency_key=key,
            tool=tool,
            claimed_at=at,
        )
        claimed = await self._session.execute(
            (
                insert.on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"])
                if stale_after is None
                else insert.on_conflict_do_update(
                    index_elements=["tenant_id", "idempotency_key"],
                    set_={"claimed_at": at, "tool": tool},
                    where=ToolCallRow.claimed_at < at - stale_after,
                )
            ).returning(ToolCallRow.idempotency_key)
        )
        return claimed.scalar_one_or_none() is not None

    async def forget(self, tenant_id: TenantId, key: str) -> None:
        await self._session.execute(
            delete(ToolCallRow).where(
                ToolCallRow.tenant_id == tenant_id.value,
                ToolCallRow.idempotency_key == key,
            )
        )


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
        query = select(TriggerRow).where(TriggerRow.tenant_id == tenant_id.value, _job_live())
        if skill_id is not None:
            query = query.where(TriggerRow.skill_id == skill_id.value)
        rows = (await self._session.execute(query.order_by(TriggerRow.created_at.desc()))).scalars()
        return tuple(row_to_trigger(row) for row in rows.all())

    async def find(self, trigger_id: TriggerId) -> Trigger | None:
        query = select(TriggerRow).where(TriggerRow.id == trigger_id.value, _job_live())
        row = (await self._session.execute(query)).scalar_one_or_none()
        return None if row is None else row_to_trigger(row)

    async def _row(self, tenant_id: TenantId, trigger_id: TriggerId) -> TriggerRow:
        query = select(TriggerRow).where(
            TriggerRow.id == trigger_id.value, TriggerRow.tenant_id == tenant_id.value
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        if row is None:
            raise NotFound(f"trigger {trigger_id} was not found")
        return row


def _job_live() -> ColumnElement[bool]:
    return ~exists().where(
        WorkflowRow.tenant_id == TriggerRow.tenant_id,
        WorkflowRow.id == TriggerRow.workflow_id,
        WorkflowRow.retired_at.is_not(None),
    )


class SqlUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._depth = 0

    async def __aenter__(self) -> SqlUnitOfWork:
        self._depth += 1
        if self._session is not None:
            return self
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
        self.attempts = SqlAttemptRepository(self._session)
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
        self._depth -= 1
        if exc[0] is not None:
            await session.rollback()
        if self._depth > 0:
            return
        try:
            await session.close()
        finally:
            self._session = None

    async def commit(self) -> None:
        try:
            await self._require_session().commit()
        except StaleDataError as clash:
            await self._require_session().rollback()
            raise Conflict(str(clash)) from clash

    async def rollback(self) -> None:
        await self._require_session().rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("SqlUnitOfWork must be used as an async context manager")
        return self._session
