"""Postgres-backed repositories and the unit of work.

Reads are always filtered by ``tenant_id`` as well as by id. A row belonging to
another tenant is reported as ``NotFound``, which is the same answer as a row
that does not exist -- the difference is not something a caller may learn.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.ports.repositories import (
    ConnectionRepository,
    RecordingRepository,
    RunRepository,
    SkillRepository,
    UnitOfWork,
)
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.run import Run, RunId
from sro.domain.recording.recording import Recording
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import RecordingId, SkillId, TenantId
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.skill import Skill
from sro.infrastructure.db.mappers import (
    connection_to_row,
    objective_columns,
    recording_to_row,
    row_to_connection,
    row_to_recording,
    row_to_run,
    row_to_skill,
    run_to_row,
    skill_to_row,
    update_connection_row,
    update_recording_row,
    update_run_row,
    update_skill_row,
)
from sro.infrastructure.db.models import ConnectionRow, RecordingRow, RunRow, SkillRow


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
