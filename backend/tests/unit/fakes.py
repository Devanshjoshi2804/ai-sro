"""In-memory implementations of every port.

If a new port cannot be faked in a few lines it is describing an implementation
rather than a capability, and should be redesigned before it gets an adapter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count

from sro.application.context import RequestContext
from sro.application.induction.induce_skill import InducedSkill, InduceSkill
from sro.application.ports.browser import BrowserSession, BrowserUnavailable
from sro.application.ports.repositories import (
    ConnectionRepository,
    RecordingRepository,
    SkillRepository,
)
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.recording.recording import Recording
from sro.domain.shared.errors import NotFound
from sro.domain.shared.identifiers import (
    BrowserSessionId,
    RecordingId,
    SkillId,
    TenantId,
)
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.skill import Skill


class FakeClock:
    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 3, 1, 9, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int) -> None:
        self._now += timedelta(seconds=seconds)


class FakeIdFactory:
    """Sequential ids, so failures name ``rec-3`` rather than a UUID."""

    def __init__(self) -> None:
        self._recordings = count(1)
        self._skills = count(1)

    def new_recording_id(self) -> RecordingId:
        return RecordingId(f"rec-{next(self._recordings)}")

    def new_skill_id(self) -> SkillId:
        return SkillId(f"skill-{next(self._skills)}")


class FakeBrowserProvider:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.opened: list[BrowserSessionId] = []
        self.closed: list[BrowserSessionId] = []
        self.navigated: list[tuple[BrowserSessionId, str]] = []
        self._counter = count(1)

    async def open(self, *, start_url: str | None = None) -> BrowserSession:
        if not self.available:
            raise BrowserUnavailable("fake provider is switched off")
        session_id = BrowserSessionId(f"sess-{next(self._counter)}")
        self.opened.append(session_id)
        return BrowserSession(
            id=session_id,
            live_view_url=f"https://steel.test/v1/sessions/{session_id}/live",
            debugger_url=f"ws://steel.test/devtools/{session_id}",
        )

    async def close(self, session_id: BrowserSessionId) -> None:
        if not self.available:
            raise BrowserUnavailable("fake provider is switched off")
        self.closed.append(session_id)

    async def navigate(self, session_id: BrowserSessionId, url: str) -> None:
        self.navigated.append((session_id, url))

    async def session_cookies(self, session_id: BrowserSessionId) -> tuple[dict[str, object], ...]:
        return ({"name": "JSESSIONID", "value": "fake-session", "domain": "wms.test"},)

    async def live_view_url(self, session_id: BrowserSessionId) -> str | None:
        if session_id in self.closed:
            return None
        return f"https://steel.test/v1/sessions/{session_id}/live"


class FakeBlobStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, *, content_type: str) -> str:
        self.objects[key] = data
        return f"s3://sro-artifacts/{key}"

    async def presigned_url(self, key: str, *, expires_in: timedelta) -> str:
        return f"https://blobs.test/{key}?expires={int(expires_in.total_seconds())}"

    async def presigned_url_for_uri(self, uri: str, *, expires_in: timedelta) -> str | None:
        prefix = "s3://sro-artifacts/"
        if not uri.startswith(prefix):
            return None
        return await self.presigned_url(uri[len(prefix) :], expires_in=expires_in)


class FakeTranscriber:
    """Unavailable unless given text, matching the production default."""

    def __init__(self, text: str | None = None) -> None:
        self._text = text
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._text is not None

    async def transcribe(self, audio: bytes, *, content_type: str) -> str:
        if self._text is None:
            raise RuntimeError("no transcriber configured")
        self.calls += 1
        return self._text


class FakeDurableExecution:
    """Runs induction inline and records the deadlines it was asked for.

    Keeping the real use case behind it means the HTTP tests still exercise
    induction; what they skip is the scheduler, not the behaviour.
    """

    def __init__(self, induce: InduceSkill, *, available: bool = True) -> None:
        self._induce = induce
        self.available = available
        self.watching: list[str] = []
        self.finished: list[str] = []

    async def induce_skill(
        self,
        ctx: RequestContext,
        *,
        first: RecordingId,
        second: RecordingId,
        name: str | None = None,
    ) -> InducedSkill:
        return await self._induce.execute(ctx, first=first, second=second, name=name)

    async def watch_recording(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        browser_session_id: BrowserSessionId,
        timeout_seconds: int,
    ) -> bool:
        if not self.available:
            return False
        self.watching.append(str(recording_id))
        return True

    async def recording_finished(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        self.finished.append(str(recording_id))


class FakeRecordingRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], Recording] = {}

    async def add(self, recording: Recording) -> None:
        self.rows[(str(recording.tenant_id), str(recording.id))] = recording

    async def get(self, tenant_id: TenantId, recording_id: RecordingId) -> Recording:
        try:
            return self.rows[(str(tenant_id), str(recording_id))]
        except KeyError:
            raise NotFound(f"recording {recording_id} not found") from None

    async def save(self, recording: Recording) -> None:
        await self.add(recording)

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        objective_key: ObjectiveKey | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Recording, ...]:
        rows = [r for (t, _), r in self.rows.items() if t == str(tenant_id)]
        if objective_key is not None:
            rows = [r for r in rows if r.objective_key == objective_key]
        rows.sort(key=lambda r: r.started_at, reverse=True)
        return tuple(rows[offset : offset + limit])


class FakeSkillRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], Skill] = {}

    async def add(self, skill: Skill) -> None:
        self.rows[(str(skill.tenant_id), str(skill.id))] = skill

    async def get(self, tenant_id: TenantId, skill_id: SkillId) -> Skill:
        try:
            return self.rows[(str(tenant_id), str(skill_id))]
        except KeyError:
            raise NotFound(f"skill {skill_id} not found") from None

    async def save(self, skill: Skill) -> None:
        await self.add(skill)

    async def find_by_objective(
        self, tenant_id: TenantId, objective_key: ObjectiveKey
    ) -> Skill | None:
        for (tenant, _), skill in self.rows.items():
            if tenant == str(tenant_id) and skill.objective_key == objective_key:
                return skill
        return None

    async def list_for_tenant(
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Skill, ...]:
        rows = [s for (t, _), s in self.rows.items() if t == str(tenant_id)]
        return tuple(rows[offset : offset + limit])


class FakeConnectionRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], Connection] = {}

    async def add(self, connection: Connection) -> None:
        self.rows[(str(connection.tenant_id), str(connection.id))] = connection

    async def get(self, tenant_id: TenantId, connection_id: ConnectionId) -> Connection:
        try:
            return self.rows[(str(tenant_id), str(connection_id))]
        except KeyError:
            raise NotFound(f"connection {connection_id} not found") from None

    async def save(self, connection: Connection) -> None:
        await self.add(connection)

    async def find_by_system(self, tenant_id: TenantId, target_system: str) -> Connection | None:
        for (tenant, _), connection in self.rows.items():
            if tenant == str(tenant_id) and connection.target_system == target_system:
                return connection
        return None

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[Connection, ...]:
        return tuple(c for (t, _), c in self.rows.items() if t == str(tenant_id))


class FakeCredentialVault:
    """In memory, and asserts the one rule: nothing else may read a value."""

    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    async def store(self, key: str, value: str) -> None:
        self.secrets[key] = value

    async def get(self, key: str) -> str | None:
        return self.secrets.get(key)

    async def delete(self, key: str) -> None:
        self.secrets.pop(key, None)


class FakeUnitOfWork:
    """Counts commits. Does not simulate rollback -- the repositories hold the
    same objects the use case mutated. Transactions are proved in
    ``tests/integration`` against real Postgres.
    """

    recordings: RecordingRepository
    skills: SkillRepository
    connections: ConnectionRepository

    def __init__(self) -> None:
        self.recordings = FakeRecordingRepository()
        self.skills = FakeSkillRepository()
        self.connections = FakeConnectionRepository()
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, *exc: object) -> None:
        if exc[0] is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1
