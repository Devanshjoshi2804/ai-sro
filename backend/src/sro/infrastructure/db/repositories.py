"""Postgres-backed repositories and the unit of work.

Reads are always filtered by ``tenant_id`` as well as by id. A row belonging to
another tenant is reported as ``NotFound``, which is the same answer as a row
that does not exist -- the difference is not something a caller may learn.
"""

from __future__ import annotations

import re

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.ports.repositories import (
    ConnectionRepository,
    KnowledgeRepository,
    ModelCallRepository,
    RecordingRepository,
    RunRepository,
    SkillRepository,
    ThreadRepository,
    UnitOfWork,
)
from sro.domain.chat.thread import Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Run, RunId
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.recording.recording import Recording
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import RecordingId, SkillId, TenantId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.skill import Skill
from sro.infrastructure.db.mappers import (
    connection_to_row,
    knowledge_to_row,
    model_call_to_row,
    objective_columns,
    recording_to_row,
    row_to_connection,
    row_to_knowledge,
    row_to_model_call,
    row_to_recording,
    row_to_run,
    row_to_skill,
    row_to_thread,
    run_to_row,
    skill_to_row,
    thread_to_row,
    update_connection_row,
    update_knowledge_row,
    update_recording_row,
    update_run_row,
    update_skill_row,
    update_thread_row,
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


class SqlSkillRepository(SkillRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, skill: Skill) -> None:
        self._session.add(skill_to_row(skill))

    async def get(self, tenant_id: TenantId, skill_id: SkillId) -> Skill:
        return row_to_skill(await self._row(tenant_id, skill_id))

    async def save(self, skill: Skill) -> None:
        row = await self._row(skill.tenant_id, skill.id)
        update_skill_row(row, skill)

    async def find_by_objective(
        self, tenant_id: TenantId, objective_key: ObjectiveKey
    ) -> Skill | None:
        query = select(SkillRow).where(SkillRow.tenant_id == tenant_id.value)
        for column, value in objective_columns(objective_key).items():
            query = query.where(getattr(SkillRow, column) == value)

        row = (await self._session.execute(query)).scalar_one_or_none()
        return row_to_skill(row) if row is not None else None

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
        return tuple(row_to_skill(row) for row in rows)

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
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Thread, ...]:
        query = (
            select(ThreadRow)
            .where(ThreadRow.tenant_id == tenant_id.value)
            .order_by(ThreadRow.opened_at.desc())
            .limit(limit)
            .offset(offset)
        )
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
        await self._require_session().commit()

    async def rollback(self) -> None:
        await self._require_session().rollback()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("SqlUnitOfWork must be used as an async context manager")
        return self._session
