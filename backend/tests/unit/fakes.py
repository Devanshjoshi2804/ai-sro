"""In-memory implementations of every port.

If a new port cannot be faked in a few lines it is describing an implementation
rather than a capability, and should be redesigned before it gets an adapter.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Mapping
from datetime import UTC, datetime, timedelta
from itertools import count
from types import MappingProxyType

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.induction.induce_skill import InducedSkill, InduceSkill
from sro.application.ports.agent import AgentDrivers
from sro.application.ports.blob import BlobStore
from sro.application.ports.browser import BrowserProvider, BrowserSession, BrowserUnavailable
from sro.application.ports.dispatch import DispatchFailed, RunDispatcher
from sro.application.ports.embedding import Embedder
from sro.application.ports.http import (
    HttpCaller,
    HttpResponse,
    MalformedRequest,
    TargetUnreachable,
)
from sro.application.ports.intent import Extraction, Reading
from sro.application.ports.repositories import (
    BrowserSessionRepository,
    CandidateRepository,
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
    TriggerRepository,
    UnitOfWork,
)
from sro.application.ports.schedule import Scheduler, SchedulerUnavailable
from sro.application.ports.sign_in import SignInDriver, SignInFailed, SignInResult
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.transcription import TranscribedSegment, Transcriber
from sro.application.ports.ui import ResolvedLocator, UiDriver, UiOutcome, UiUnavailable
from sro.application.ports.vault import CredentialVault
from sro.application.ports.vision import (
    ProposedGesture,
    Screen,
    VisionDriver,
    VisionUnavailable,
)
from sro.domain.chat.thread import MessageId, Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Medium, Run, RunId
from sro.domain.knowledge.entry import (
    EntryKind,
    EvidenceLevel,
    KnowledgeEntry,
    KnowledgeId,
)
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.recording.events import ActionKind
from sro.domain.recording.recording import Recording, RecordingStatus
from sro.domain.shared.errors import Conflict, NotFound
from sro.domain.shared.identifiers import (
    BatchId,
    BrowserSessionId,
    CandidateId,
    DeviceId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
    TriggerId,
)
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.locator import LocatorStrategy
from sro.domain.skill.skill import Skill
from sro.domain.trigger.trigger import Trigger


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
        self._runs = count(1)
        self._knowledge = count(1)
        self._threads = count(1)
        self._messages = count(1)
        self._devices = count(1)
        self._triggers = count(1)
        self._candidates = count(1)

    def new_recording_id(self) -> RecordingId:
        return RecordingId(f"rec-{next(self._recordings)}")

    def new_skill_id(self) -> SkillId:
        return SkillId(f"skill-{next(self._skills)}")

    def new_run_id(self) -> RunId:
        return RunId(f"run-{next(self._runs)}")

    def new_knowledge_id(self) -> KnowledgeId:
        return KnowledgeId(f"kb-{next(self._knowledge)}")

    def new_thread_id(self) -> ThreadId:
        return ThreadId(f"thr-{next(self._threads)}")

    def new_message_id(self) -> MessageId:
        return MessageId(f"msg-{next(self._messages)}")

    def new_device_id(self) -> DeviceId:
        return DeviceId(f"dev-{next(self._devices)}")

    def new_trigger_id(self) -> TriggerId:
        return TriggerId(f"trg-{next(self._triggers)}")

    def new_candidate_id(self) -> CandidateId:
        return CandidateId(f"cnd-{next(self._candidates)}")


class FakeSignInDriver:
    """Types what it is given, and remembers only that it was asked."""

    def __init__(
        self, *, lands_at: str = "https://wms.example.com/portal", fails: str = ""
    ) -> None:
        self.lands_at = lands_at
        self.fails = fails
        self.calls = 0
        self.chose: tuple[str, ...] = ()

    async def sign_in(
        self,
        *,
        debugger_url: str,
        url: str,
        username: str,
        password: str,
        choose: tuple[str, ...] = (),
        timeout_s: float = 90.0,
    ) -> SignInResult:
        self.calls += 1
        self.chose = choose
        if self.fails:
            raise SignInFailed(self.fails)
        return SignInResult(landed_at=self.lands_at, steps=("entered the username",))


class FakeBrowserProvider:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.opened: list[BrowserSessionId] = []
        self.closed: list[BrowserSessionId] = []
        self.navigated: list[tuple[BrowserSessionId, str]] = []
        self.cookies: tuple[dict[str, object], ...] = (
            {"name": "JSESSIONID", "value": "fake-session", "domain": "wms.test"},
        )
        self.headers: dict[str, str] = {}
        self.restored: list[dict[str, object]] = []
        self.emptied: list[BrowserSessionId] = []
        self.screen: tuple[bytes, ...] = (b"\xff\xd8\xff-one", b"\xff\xd8\xff-two")
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
        return self.cookies

    async def session_headers(self, session_id: BrowserSessionId, url: str) -> dict[str, str]:
        return dict(self.headers)

    async def forget_everything(self, session_id: BrowserSessionId) -> None:
        self.cookies = ()
        self.emptied.append(session_id)

    async def restore(self, session_id: BrowserSessionId, cookies: list[dict[str, object]]) -> None:
        self.restored = list(cookies)

    async def live_sessions(self) -> tuple[BrowserSessionId, ...]:
        return tuple(s for s in self.opened if s not in self.closed)

    async def debugger_url(self, session_id: BrowserSessionId) -> str:
        return f"ws://steel.test/devtools/{session_id}"

    async def frames(self, session_id: BrowserSessionId) -> AsyncIterator[bytes]:
        for frame in self.screen:
            yield frame

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

    async def read(self, uri: str) -> bytes:
        prefix = "s3://sro-artifacts/"
        if not uri.startswith(prefix):
            raise KeyError(f"{uri} is not in this store")
        return self.objects[uri[len(prefix) :]]

    async def forget(self, uri: str) -> None:
        prefix = "s3://sro-artifacts/"
        if uri.startswith(prefix):
            self.objects.pop(uri[len(prefix) :], None)

    async def forget_prefix(self, prefix: str) -> int:
        doomed = [key for key in self.objects if key.startswith(prefix)]
        for key in doomed:
            del self.objects[key]
        return len(doomed)


class FakeTranscriber:
    """Unavailable unless given text, matching the production default."""

    def __init__(self, text: str | None = None) -> None:
        self._text = text
        self.calls = 0

    @property
    def available(self) -> bool:
        return self._text is not None

    async def transcribe(
        self, audio: bytes, *, content_type: str
    ) -> tuple[TranscribedSegment, ...]:
        if self._text is None:
            raise RuntimeError("no transcriber configured")
        self.calls += 1
        # One segment covering the whole clip. This answered a bare string while
        # the port answers timed segments, so every caller was exercised against
        # a shape production never produces.
        return (TranscribedSegment(start_ms=0, end_ms=1000, text=self._text),)


class FakeDurableExecution:
    """Runs induction inline and records the deadlines it was asked for.

    Keeping the real use case behind it means the HTTP tests still exercise
    induction; what they skip is the scheduler, not the behaviour.
    """

    def __init__(
        self,
        induce: InduceSkill | None = None,
        *,
        execute: ExecuteSkill | None = None,
        available: bool = True,
    ) -> None:
        self._induce = induce
        self._execute = execute
        self.available = available
        self.watching: list[str] = []
        self.finished: list[str] = []
        self.started: list[str] = []
        self.with_values: list[dict[str, str]] = []
        """One entry per `execute_skill` call, the parameters it was actually
        given -- so a test can prove what a trigger fired with, not only that
        it fired."""

        self.waited: list[bool] = []
        """One entry per `execute_skill` call, the `wait` it was actually
        given -- so a test can prove a caller asked not to be blocked, not
        just that a run id came back."""

    async def induce_skill(
        self,
        ctx: RequestContext,
        *,
        first: RecordingId,
        second: RecordingId | None = None,
        name: str | None = None,
    ) -> InducedSkill:
        if self._induce is None:
            raise NotImplementedError("this fake was not given induction")
        return await self._induce.execute(ctx, first=first, second=second, name=name)

    async def execute_skill(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        version: int | None = None,
        authorized_by: str | None = None,
        medium: str = "network",
        run_id: RunId | None = None,
        wait: bool = True,
    ) -> RunId:
        self.started.append(str(skill_id))
        self.with_values.append(dict(parameters))
        self.waited.append(wait)
        if self._execute is None:
            # A caller that only needs to know a run was started -- a trigger,
            # say -- rather than what it did.
            return run_id or RunId(f"run-started-{len(self.started)}")
        run = await self._execute.execute(
            ctx,
            ExecutionRequest(
                skill_id=skill_id,
                parameters=dict(parameters),
                version=version,
                authorized_by=authorized_by,
                medium=Medium(medium),
                run_id=run_id,
            ),
        )
        return run.id

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

    async def list_capturing(self) -> tuple[Recording, ...]:
        """Across tenants, like the port: the browser reaper asks this before it
        releases anything, and nobody is making that request."""
        return tuple(r for r in self.rows.values() if r.status is RecordingStatus.CAPTURING)

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

    async def list_connected(self) -> tuple[Connection, ...]:
        return tuple(c for c in self.rows.values() if c.status is ConnectionStatus.CONNECTED)


class FakeRunRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], Run] = {}

    async def add(self, run: Run) -> None:
        self.rows[(str(run.tenant_id), str(run.id))] = run

    async def get(self, tenant_id: TenantId, run_id: RunId) -> Run:
        try:
            return self.rows[(str(tenant_id), str(run_id))]
        except KeyError:
            raise NotFound(f"run {run_id} not found") from None

    async def save(self, run: Run) -> None:
        await self.add(run)

    async def since(self, tenant_id: TenantId, *, since: datetime) -> tuple[Run, ...]:
        return tuple(
            run
            for run in self.rows.values()
            if run.tenant_id == tenant_id and run.started_at >= since
        )

    async def finished_since(
        self, tenant_id: TenantId, *, target_system: str, since: datetime
    ) -> tuple[Run, ...]:
        return tuple(
            run
            for run in self.rows.values()
            if run.tenant_id == tenant_id
            # Mirrors the SQL exactly, including the second clause: this fake is
            # what reproduces the breaker's behaviour in every unit test.
            and (run.target_system == target_system or target_system in run.systems)
            and run.ended_at is not None
            and run.ended_at >= since
        )

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        skill_id: SkillId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Run, ...]:
        runs = [r for (t, _), r in self.rows.items() if t == str(tenant_id)]
        if skill_id is not None:
            runs = [r for r in runs if r.skill_id == skill_id]
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return tuple(runs[offset : offset + limit])


class FakeHttpCaller:
    """Answers from a queue keyed by URL substring, and records what was sent.

    Sending is the thing under test in an executor, so every call is kept: a
    test asserts on the header a request carried, not only on what came back.
    """

    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []
        self.responses: list[HttpResponse] = []
        self.unreachable = False
        self.malformed = False
        """The request could not be built at all -- what a real client raises
        for a URL that is not a URL. Distinct from ``unreachable`` because only
        one of the two is the skill's own fault."""

    def answer(
        self, status_code: int = 200, text: str = "{}", headers: dict[str, str] | None = None
    ) -> None:
        self.responses.append(
            HttpResponse(status_code=status_code, headers=headers or {}, text=text)
        )

    async def send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] = MappingProxyType({}),
        body: str | None = None,
        timeout_s: float = 30.0,
    ) -> HttpResponse:
        self.sent.append(
            {"method": method, "url": url, "headers": dict(headers or {}), "body": body}
        )
        if self.malformed:
            raise MalformedRequest(f"unsupported protocol in {url!r}")
        if self.unreachable:
            raise TargetUnreachable("connection reset")
        if self.responses:
            return self.responses.pop(0)
        return HttpResponse(status_code=200, headers={}, text="{}")


class FakeVisionDriver:
    """Proposes whatever it was told to, in order. Enough to prove the loop's
    bounds; never enough to imply a model would do this."""

    def __init__(self, *gestures: ProposedGesture, available: bool = True) -> None:
        self._gestures = list(gestures)
        self._available = available
        self.asked: list[dict[str, object]] = []

    async def propose(
        self,
        *,
        goal: str,
        screen: Screen,
        allowed: tuple[ActionKind, ...],
        history: tuple[str, ...] = (),
    ) -> ProposedGesture:
        if not self._available:
            raise VisionUnavailable("no vision backend")
        self.asked.append({"goal": goal, "screen": screen, "allowed": allowed, "history": history})
        if not self._gestures:
            return ProposedGesture(action=ActionKind.HOVER, refusal="nothing left to try")
        return self._gestures.pop(0)


class FakeUiDriver:
    """Answers a queue of outcomes and records what it was asked to do."""

    def __init__(self, *, available: bool = True, digest: str = "Finish: 100,200") -> None:
        self.available = available
        self.digest = digest
        self.asked: list[dict[str, object]] = []
        self.outcomes: list[UiOutcome] = []
        self.captures = 0

    def will_find(self, strategy: LocatorStrategy, candidates: int = 1) -> None:
        self.outcomes.append(UiOutcome(performed=True, matched_by=strategy, candidates=candidates))

    def will_not_find(self) -> None:
        self.outcomes.append(UiOutcome(performed=False, detail="no control matched"))

    async def perform(
        self,
        *,
        action: ActionKind,
        locators: tuple[ResolvedLocator, ...],
        value: str | None = None,
    ) -> UiOutcome:
        if not self.available:
            raise UiUnavailable("no browser is attached")
        self.asked.append({"action": action, "locators": locators, "value": value})
        return self.outcomes.pop(0) if self.outcomes else UiOutcome(performed=True)

    async def current_url(self) -> str | None:
        return "https://wms.test/portal"

    async def capture(self) -> Screen:
        if not self.available:
            raise UiUnavailable("no browser is attached")
        # Counted, because "which browser did the rung that looks photograph"
        # is the whole question when a run is performed in somebody else's.
        self.captures += 1
        return Screen(
            image=b"\x89PNG-not-really",
            mime_type="image/png",
            width=1280,
            height=800,
            text_digest=self.digest,
        )

    def for_session(self, debugger_url: str) -> FakeUiDriver:
        """The same fake: what matters is that callers ask for the browser they
        opened rather than the configured one."""
        return self

    async def perform_at(
        self, *, action: ActionKind, x: int, y: int, value: str | None = None
    ) -> UiOutcome:
        if not self.available:
            raise UiUnavailable("no browser is attached")
        self.asked.append({"action": action, "at": (x, y), "value": value})
        return self.outcomes.pop(0) if self.outcomes else UiOutcome(performed=True)


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


def _terms(text: str) -> list[str]:
    """Mirrors SqlKnowledgeRepository: any word, not the whole phrase."""
    skip = {"a", "an", "the", "at", "in", "on", "of", "to", "for", "and"}
    return [w for w in re.findall(r"[A-Za-z0-9]+", text.lower()) if len(w) > 2 and w not in skip]


class FakeKnowledgeRepository:
    def __init__(self) -> None:
        self.rows: dict[str, KnowledgeEntry] = {}

    async def add(self, entry: KnowledgeEntry) -> None:
        self.rows[str(entry.id)] = entry

    async def save(self, entry: KnowledgeEntry) -> None:
        self.rows[str(entry.id)] = entry

    async def current(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str
    ) -> KnowledgeEntry | None:
        for entry in self.rows.values():
            if (
                entry.tenant_id == tenant_id
                and entry.system == system
                and entry.kind is kind
                and entry.key == key
                and entry.current
            ):
                return entry
        return None

    async def history(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str, limit: int = 10
    ) -> tuple[KnowledgeEntry, ...]:
        # Newest last in, newest first out: the fake has no clock of its own and
        # every entry a test writes carries the same instant.
        found = [
            entry
            for entry in self.rows.values()
            if entry.tenant_id == tenant_id
            and entry.system == system
            and entry.kind is kind
            and entry.key == key
        ]
        return tuple(reversed(found))[:limit]

    async def without_embedding(
        self, tenant_id: TenantId, *, limit: int = 200
    ) -> tuple[KnowledgeEntry, ...]:
        pending = [
            entry
            for entry in self.rows.values()
            if entry.tenant_id == tenant_id and entry.current and not entry.embedding
        ]
        return tuple(pending[:limit])

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
        found = [
            entry
            for entry in self.rows.values()
            if entry.tenant_id == tenant_id
            and entry.current
            and (system is None or entry.system == system)
            and (not kinds or entry.kind in kinds)
            and (min_evidence is None or entry.evidence.rank >= min_evidence.rank)
            and (
                not _terms(terms)
                or any(
                    word in entry.title.lower() or word in entry.key.lower()
                    for word in _terms(terms)
                )
            )
        ]
        return tuple(found[:limit])


class FakeEmbedder:
    """Deterministic and meaningless: enough to prove a vector is stored and
    passed, never enough to imply the numbers mean something."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.asked: list[tuple[str, ...]] = []

    @property
    def available(self) -> bool:
        return self._available

    @property
    def dimensions(self) -> int:
        return 3

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        self.asked.append(texts)
        if not self._available:
            return tuple(() for _ in texts)
        return tuple((float(len(text)), 1.0, 0.0) for text in texts)


class FakeThreadRepository:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], Thread] = {}

    async def add(self, thread: Thread) -> None:
        self.rows[(str(thread.tenant_id), str(thread.id))] = thread

    async def get(self, tenant_id: TenantId, thread_id: ThreadId) -> Thread:
        try:
            return self.rows[(str(tenant_id), str(thread_id))]
        except KeyError:
            raise NotFound(f"thread {thread_id} not found") from None

    async def save(self, thread: Thread) -> None:
        await self.add(thread)

    async def list_for_tenant(
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Thread, ...]:
        rows = [t for (tenant, _), t in self.rows.items() if tenant == str(tenant_id)]
        rows.sort(key=lambda thread: thread.opened_at, reverse=True)
        return tuple(rows[offset : offset + limit])


class FakeModelCallRepository:
    def __init__(self) -> None:
        self.calls: list[ModelCall] = []

    async def add(self, call: ModelCall) -> None:
        self.calls.append(call)

    async def list_for_run(self, tenant_id: TenantId, run_id: RunId) -> tuple[ModelCall, ...]:
        return tuple(
            call for call in self.calls if call.tenant_id == tenant_id and call.run_id == run_id
        )


class FakeBrowserSessionRepository:
    """Ownership, in a dict. The conflict on a second claim is the behaviour
    under test, not an implementation detail of Postgres."""

    def __init__(self) -> None:
        self.rows: dict[str, tuple[str, datetime]] = {}

    async def claim(
        self,
        tenant_id: TenantId,
        session_id: BrowserSessionId,
        opened_by: PrincipalId,
        opened_at: datetime,
    ) -> None:
        if str(session_id) in self.rows:
            raise Conflict(f"browser session {session_id} is already held")
        self.rows[str(session_id)] = (str(tenant_id), opened_at)

    async def held_by(self, tenant_id: TenantId) -> tuple[BrowserSessionId, ...]:
        return tuple(
            BrowserSessionId(held)
            for held, (owner, _) in self.rows.items()
            if owner == str(tenant_id)
        )

    async def all_held(self) -> tuple[tuple[BrowserSessionId, datetime], ...]:
        return tuple((BrowserSessionId(held), when) for held, (_, when) in self.rows.items())

    async def release(self, session_id: BrowserSessionId) -> None:
        self.rows.pop(str(session_id), None)


class FakeDeviceRepository:
    def __init__(self) -> None:
        self.rows: dict[str, AgentDevice] = {}

    async def add(self, device: AgentDevice) -> None:
        self.rows[device.id.value] = device

    async def get(self, tenant_id: TenantId, device_id: DeviceId) -> AgentDevice:
        device = self.rows.get(device_id.value)
        if device is None or device.tenant_id != tenant_id:
            raise NotFound(f"device {device_id} was not found")
        return device

    async def save(self, device: AgentDevice) -> None:
        self.rows[device.id.value] = device

    async def registered_as(
        self, tenant_id: TenantId, principal_id: PrincipalId, label: str
    ) -> AgentDevice | None:
        return next(
            (
                device
                for device in self.rows.values()
                if device.tenant_id == tenant_id
                and device.principal_id == principal_id
                and device.label == label
            ),
            None,
        )

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[AgentDevice, ...]:
        mine = [device for device in self.rows.values() if device.tenant_id == tenant_id]
        return tuple(sorted(mine, key=lambda device: device.last_seen_at, reverse=True))


class FakeObservationRepository:
    """The conflict on a second add is the behaviour under test: an upload the
    extension retried must not be counted twice."""

    def __init__(self) -> None:
        self.rows: dict[str, ObservationBatch] = {}

    async def add(self, batch: ObservationBatch) -> None:
        if batch.id.value in self.rows:
            raise Conflict(f"observation batch {batch.id} is already stored")
        self.rows[batch.id.value] = batch

    async def get(self, tenant_id: TenantId, batch_id: BatchId) -> ObservationBatch | None:
        batch = self.rows.get(batch_id.value)
        return batch if batch is not None and batch.tenant_id == tenant_id else None

    async def between(
        self,
        tenant_id: TenantId,
        *,
        since: datetime,
        until: datetime | None = None,
        principal_id: PrincipalId | None = None,
    ) -> tuple[ObservationBatch, ...]:
        found = [
            batch
            for batch in self.rows.values()
            if batch.tenant_id == tenant_id
            and batch.ended_at >= since
            and (until is None or batch.started_at <= until)
            and (principal_id is None or batch.principal_id == principal_id)
        ]
        return tuple(sorted(found, key=lambda batch: batch.started_at))

    async def for_recording(
        self, tenant_id: TenantId, recording_id: RecordingId
    ) -> tuple[ObservationBatch, ...]:
        return tuple(
            sorted(
                (
                    batch
                    for batch in self.rows.values()
                    if batch.tenant_id == tenant_id and batch.recording_id == recording_id
                ),
                key=lambda batch: batch.started_at,
            )
        )

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]:
        return tuple({batch.tenant_id for batch in self.rows.values() if batch.ended_at >= since})

    async def forget(self, tenant_id: TenantId, ids: tuple[BatchId, ...]) -> None:
        for batch_id in ids:
            batch = self.rows.get(batch_id.value)
            if batch is not None and batch.tenant_id == tenant_id:
                del self.rows[batch_id.value]


class FakeCandidateRepository:
    def __init__(self) -> None:
        self.rows: dict[str, TaskCandidate] = {}

    async def add(self, candidate: TaskCandidate) -> None:
        self.rows[candidate.id.value] = candidate

    async def get(self, tenant_id: TenantId, candidate_id: CandidateId) -> TaskCandidate:
        candidate = self.rows.get(candidate_id.value)
        if candidate is None or candidate.tenant_id != tenant_id:
            raise NotFound(f"candidate {candidate_id} was not found")
        return candidate

    async def save(self, candidate: TaskCandidate) -> None:
        self.rows[candidate.id.value] = candidate

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        status: CandidateStatus | None = None,
        principal_id: PrincipalId | None = None,
        seen_at_least: int = 0,
        host: str | None = None,
    ) -> tuple[TaskCandidate, ...]:
        found = [
            candidate
            for candidate in self.rows.values()
            if candidate.tenant_id == tenant_id
            and (status is None or candidate.status is status)
            and (principal_id is None or candidate.principal_id == principal_id)
            and (host is None or candidate.host == host.lower())
            and candidate.times_seen >= seen_at_least
        ]
        return tuple(sorted(found, key=lambda one: one.times_seen, reverse=True))


class FakeObservationPolicyRepository:
    def __init__(self) -> None:
        self.rows: dict[str, ObservationPolicy] = {}

    async def get(self, tenant_id: TenantId) -> ObservationPolicy | None:
        return self.rows.get(tenant_id.value)

    async def save(self, tenant_id: TenantId, policy: ObservationPolicy) -> None:
        self.rows[tenant_id.value] = policy


class FakeAgentDrivers:
    """Drivers for a browser somebody else is sitting in front of.

    Records which device was asked for, because the thing worth proving is that
    a run bound to one operator's browser never reaches another's -- or, worse,
    quietly reaches the deployment's own.
    """

    def __init__(
        self, ui: UiDriver | None = None, http: HttpCaller | None = None, *, connected: bool = True
    ) -> None:
        self.driver = ui or FakeUiDriver()
        self.caller = http or FakeHttpCaller()
        self.connected = connected
        self.asked_for: list[tuple[str, str]] = []
        self.told: tuple[str | None, bool] = (None, False)

    def ui(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        origin: str | None = None,
        may_take_focus: bool = False,
    ) -> UiDriver:
        self.asked_for.append((str(tenant_id), str(device_id)))
        # What the run said about the page and the screen, so a test can read
        # back what the browser would have been told.
        self.told = (origin, may_take_focus)
        if not self.connected:
            raise UiUnavailable(f"{device_id} has no channel open")
        return self.driver

    def http(self, tenant_id: TenantId, device_id: DeviceId) -> HttpCaller:
        self.asked_for.append((str(tenant_id), str(device_id)))
        if not self.connected:
            raise TargetUnreachable(f"{device_id} has no channel open")
        return self.caller

    async def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return (DeviceId("dev-1"),) if self.connected else ()


class FakeTriggerRepository:
    def __init__(self) -> None:
        self.rows: dict[str, Trigger] = {}

    async def add(self, trigger: Trigger) -> None:
        self.rows[trigger.id.value] = trigger

    async def get(self, tenant_id: TenantId, trigger_id: TriggerId) -> Trigger:
        trigger = self.rows.get(trigger_id.value)
        if trigger is None or trigger.tenant_id != tenant_id:
            raise NotFound(f"trigger {trigger_id} was not found")
        return trigger

    async def save(self, trigger: Trigger) -> None:
        self.rows[trigger.id.value] = trigger

    async def remove(self, tenant_id: TenantId, trigger_id: TriggerId) -> None:
        trigger = self.rows.get(trigger_id.value)
        if trigger is not None and trigger.tenant_id == tenant_id:
            del self.rows[trigger_id.value]

    async def list_for_tenant(
        self, tenant_id: TenantId, *, skill_id: SkillId | None = None
    ) -> tuple[Trigger, ...]:
        mine = [
            trigger
            for trigger in self.rows.values()
            if trigger.tenant_id == tenant_id and (skill_id is None or trigger.skill_id == skill_id)
        ]
        return tuple(sorted(mine, key=lambda trigger: trigger.created_at, reverse=True))

    async def find(self, trigger_id: TriggerId) -> Trigger | None:
        return self.rows.get(trigger_id.value)


class FakeScheduler:
    """A clock that keeps a list. What matters is that a trigger which cannot
    be scheduled is never stored, and a paused one leaves nothing behind."""

    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.scheduled: dict[str, str] = {}
        self.unschedule_calls: list[str] = []

    async def schedule(self, trigger: Trigger) -> None:
        if not self.available:
            raise SchedulerUnavailable("the fake scheduler is switched off")
        self.scheduled[trigger.id.value] = trigger.cron or ""

    async def unschedule(self, trigger_id: TriggerId) -> None:
        self.unschedule_calls.append(trigger_id.value)
        self.scheduled.pop(trigger_id.value, None)


class FakeRunDispatcher:
    """The process that holds a browser, standing in for itself."""

    def __init__(self, *, reachable: bool = True) -> None:
        self.reachable = reachable
        self.asked: list[tuple[str, str]] = []
        self.with_values: list[dict[str, str]] = []
        self.may_take_focus = False

    async def start(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        version: int | None = None,
        authorized_by: bool = False,
        medium: Medium = Medium.NETWORK,
        may_take_focus: bool = False,
    ) -> RunId:
        if not self.reachable:
            raise DispatchFailed(f"{device_id} has no channel open anywhere")
        self.asked.append((skill_id.value, device_id.value))
        self.with_values.append(dict(parameters))
        self.may_take_focus = may_take_focus
        return RunId(f"run-dispatched-{len(self.asked)}")


class FakeUnitOfWork:
    """Counts commits. Does not simulate rollback -- the repositories hold the
    same objects the use case mutated. Transactions are proved in
    ``tests/integration`` against real Postgres.
    """

    recordings: RecordingRepository
    skills: SkillRepository
    connections: ConnectionRepository
    runs: RunRepository
    knowledge: KnowledgeRepository
    model_calls: ModelCallRepository
    threads: ThreadRepository
    browser_sessions: BrowserSessionRepository
    devices: DeviceRepository
    observations: ObservationRepository
    observation_policies: ObservationPolicyRepository
    candidates: CandidateRepository
    triggers: TriggerRepository

    def __init__(self) -> None:
        self.recordings = FakeRecordingRepository()
        self.skills = FakeSkillRepository()
        self.connections = FakeConnectionRepository()
        self.runs = FakeRunRepository()
        self.knowledge = FakeKnowledgeRepository()
        self.model_calls = FakeModelCallRepository()
        self.threads = FakeThreadRepository()
        self.browser_sessions = FakeBrowserSessionRepository()
        self.devices = FakeDeviceRepository()
        self.observations = FakeObservationRepository()
        self.observation_policies = FakeObservationPolicyRepository()
        self.candidates = FakeCandidateRepository()
        self.triggers = FakeTriggerRepository()
        self.commits = 0
        self.rollbacks = 0
        self.commit_raises: Exception | None = None
        """What ``commit`` should raise instead of committing.

        A fake that cannot fail cannot prove what a caller does when a commit
        does -- and losing a write to somebody else's concurrent one is exactly
        the failure a caller has to handle rather than log."""

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, *exc: object) -> None:
        if exc[0] is not None:
            await self.rollback()

    async def commit(self) -> None:
        if self.commit_raises is not None:
            raise self.commit_raises
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeIntentParser:
    """Reads what it was told to read. Never asked what to run.

    Exists so the reading can be tested without a model: what matters is that a
    reading is *validated* against the library rather than obeyed, and that is
    the same code whether the reading came from Gemini or from here.
    """

    def __init__(self, reading: Reading | None = None, *, available: bool = True) -> None:
        self._reading = reading or Reading()
        self.available = available
        self.asked: list[str] = []

    async def extract(
        self, utterance: str, *, parameters: tuple[str, ...], context: str = ""
    ) -> Extraction:
        return Extraction()

    async def read(self, utterance: str, *, after: str = "") -> Reading:
        self.asked.append(utterance)
        return self._reading


# Every fake, held against the port it stands in for. One line each, and the
# reason they are here rather than as base classes: a fake that inherits from a
# Protocol satisfies it by inheritance and can still drift in signature. These
# are structural checks, which is what the application actually depends on.
#
# The drift they exist to catch has happened more than once -- a port grew a
# method and the fake did not, or answered a different shape, so a use case was
# exercised against something production never produces. `make lint` type-checks
# this file for exactly these lines.
_blobs: BlobStore = FakeBlobStore()
_browser: BrowserProvider = FakeBrowserProvider()
_caller: HttpCaller = FakeHttpCaller()
_embedder: Embedder = FakeEmbedder()
_transcriber: Transcriber = FakeTranscriber()
_ui: UiDriver = FakeUiDriver()
_vault: CredentialVault = FakeCredentialVault()
_vision: VisionDriver = FakeVisionDriver()
_sign_in: SignInDriver = FakeSignInDriver()
_uow: UnitOfWork = FakeUnitOfWork()
_clock: Clock = FakeClock()
_ids: IdFactory = FakeIdFactory()
_devices: DeviceRepository = FakeDeviceRepository()
_observations: ObservationRepository = FakeObservationRepository()
_observation_policies: ObservationPolicyRepository = FakeObservationPolicyRepository()
_agents: AgentDrivers = FakeAgentDrivers()
_scheduler: Scheduler = FakeScheduler()
_dispatcher: RunDispatcher = FakeRunDispatcher()
_triggers: TriggerRepository = FakeTriggerRepository()
_candidates: CandidateRepository = FakeCandidateRepository()
