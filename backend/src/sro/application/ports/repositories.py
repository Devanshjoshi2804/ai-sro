"""Persistence ports.

``tenant_id`` is the first parameter everywhere and never defaulted, so scoping
is checked by mypy rather than by review. Missing entities raise ``NotFound``
instead of returning ``None``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sro.domain.chat.thread import Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Run, RunId
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import (
    BrowserSessionId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
)
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.skill import Skill


class RecordingRepository(Protocol):
    async def add(self, recording: Recording) -> None: ...

    async def get(self, tenant_id: TenantId, recording_id: RecordingId) -> Recording: ...

    async def save(self, recording: Recording) -> None: ...

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        objective_key: ObjectiveKey | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Recording, ...]:
        """Newest first. Filtering by objective is how the UI offers run pairing."""
        ...

    async def list_capturing(self) -> tuple[Recording, ...]:
        """Recordings open right now, across tenants.

        Crosses the tenant boundary for one reason: the browser reaper has to
        know which sessions somebody is demonstrating in before it releases
        any, and nobody is making that request. It returns recordings, never
        their contents.
        """
        ...


class SkillRepository(Protocol):
    async def add(self, skill: Skill) -> None: ...

    async def get(self, tenant_id: TenantId, skill_id: SkillId) -> Skill: ...

    async def save(self, skill: Skill) -> None: ...

    async def find_by_objective(
        self, tenant_id: TenantId, objective_key: ObjectiveKey
    ) -> Skill | None:
        """``None`` is meaningful here: the caller creates the skill instead."""
        ...

    async def list_for_tenant(
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Skill, ...]: ...


class ConnectionRepository(Protocol):
    async def add(self, connection: Connection) -> None: ...

    async def get(self, tenant_id: TenantId, connection_id: ConnectionId) -> Connection: ...

    async def save(self, connection: Connection) -> None: ...

    async def find_by_system(self, tenant_id: TenantId, target_system: str) -> Connection | None:
        """``None`` is meaningful: the caller offers to connect one instead."""
        ...

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[Connection, ...]: ...

    async def list_connected(self) -> tuple[Connection, ...]:
        """Every connected system, across tenants.

        The one query in this codebase that deliberately crosses the tenant
        boundary, and the only caller is the keeper that signs sessions back in
        before they expire: nobody is making the request, so there is no tenant
        to scope it to. It returns connections, never anybody's data.
        """
        ...


class RunRepository(Protocol):
    async def add(self, run: Run) -> None: ...

    async def get(self, tenant_id: TenantId, run_id: RunId) -> Run: ...

    async def save(self, run: Run) -> None:
        """Overwrite the record of a run in progress.

        A run is append-only in the domain, so this only ever grows the step
        log; the repository rewrites the row because a run is one document.
        """
        ...

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        skill_id: SkillId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Run, ...]:
        """Newest first."""
        ...

    async def finished_since(
        self, tenant_id: TenantId, *, target_system: str, since: datetime
    ) -> tuple[Run, ...]:
        """Runs against one system that have ended. What the breaker reads."""
        ...


class KnowledgeRepository(Protocol):
    async def add(self, entry: KnowledgeEntry) -> None: ...

    async def current(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str
    ) -> KnowledgeEntry | None:
        """The claim believed right now for this key, if there is one."""
        ...

    async def save(self, entry: KnowledgeEntry) -> None: ...

    async def without_embedding(
        self, tenant_id: TenantId, *, limit: int = 200
    ) -> tuple[KnowledgeEntry, ...]:
        """Current entries with no vector, for a deployment that turned
        embeddings on after it had already stored things."""
        ...

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
        """Superseded entries are never returned: they are history, not belief.

        Structured filters narrow first and similarity only orders what is left
        -- ``docs/09-agentic-standards.md``, because a nearest neighbour across
        the whole store answers confidently with the wrong system's endpoint.
        """
        ...


class ThreadRepository(Protocol):
    async def add(self, thread: Thread) -> None: ...

    async def get(self, tenant_id: TenantId, thread_id: ThreadId) -> Thread: ...

    async def save(self, thread: Thread) -> None: ...

    async def list_for_tenant(
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Thread, ...]:
        """Most recently opened first."""
        ...


class ModelCallRepository(Protocol):
    async def add(self, call: ModelCall) -> None: ...

    async def list_for_run(self, tenant_id: TenantId, run_id: RunId) -> tuple[ModelCall, ...]:
        """Every call a run made, oldest first. The run's egress record."""
        ...


class BrowserSessionRepository(Protocol):
    """Who a browser belongs to.

    The only durable answer to that question. The API and the Temporal worker
    each open and close browsers in their own process, so an in-memory map is
    one process's opinion about a resource both of them touch.
    """

    async def claim(
        self,
        tenant_id: TenantId,
        session_id: BrowserSessionId,
        opened_by: PrincipalId,
        opened_at: datetime,
    ) -> None:
        """Record the owner.

        Raises ``Conflict`` when somebody already holds this id, which means the
        provider handed one browser to two callers. Serving it to the second is
        the bug this record exists to prevent, so it fails rather than transfers.
        """
        ...

    async def held_by(self, tenant_id: TenantId) -> tuple[BrowserSessionId, ...]:
        """Every session this tenant has claimed, live or not.

        Liveness belongs to the provider; the caller intersects the two.
        """
        ...

    async def all_held(self) -> tuple[tuple[BrowserSessionId, datetime], ...]:
        """Every claim in the deployment, and when it was made.

        Crosses the tenant boundary for the same reason ``list_capturing`` does:
        the browser sweep has to know which sessions are spoken for, and nobody
        is making that request. Ids and timestamps, never a tenant.
        """
        ...

    async def release(self, session_id: BrowserSessionId) -> None:
        """Forget the claim. Idempotent, and deliberately not tenant-scoped:
        crash recovery and the sweep are not anybody's request."""
        ...


class UnitOfWork(Protocol):
    """Transaction boundary. Leaving the block without ``commit`` rolls back."""

    recordings: RecordingRepository
    skills: SkillRepository
    connections: ConnectionRepository
    runs: RunRepository
    knowledge: KnowledgeRepository
    model_calls: ModelCallRepository
    threads: ThreadRepository
    browser_sessions: BrowserSessionRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
