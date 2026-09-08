"""In-memory implementations of every port.

If a new port cannot be faked in a few lines it is describing an implementation
rather than a capability, and should be redesigned before it gets an adapter.
"""

from __future__ import annotations

import asyncio
import re
import sys
from collections.abc import AsyncIterator, Callable, Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import count
from types import MappingProxyType

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.induction.induce_skill import InducedSkill, InduceSkill
from sro.application.ports.agent import AgentDrivers
from sro.application.ports.blob import BlobStore
from sro.application.ports.browser import BrowserProvider, BrowserSession, BrowserUnavailable
from sro.application.ports.channel import Channel, Reply
from sro.application.ports.dispatch import DispatchFailed, RunDispatcher
from sro.application.ports.embedding import Embedder
from sro.application.ports.http import (
    HttpCaller,
    HttpResponse,
    MalformedRequest,
    TargetUnreachable,
)
from sro.application.ports.intent import Extraction, Reading
from sro.application.ports.model import Asker
from sro.application.ports.repositories import (
    BrowserSessionRepository,
    CandidateRepository,
    ChatRepository,
    ConfirmationRepository,
    ConnectionRepository,
    DeviceRepository,
    GestureRepository,
    KnowledgeRepository,
    ModelCallRepository,
    ObservationPolicyRepository,
    ObservationRepository,
    OfferRepository,
    PoolRepository,
    RecordingRepository,
    RunRepository,
    SkillRepository,
    SpendRepository,
    ThreadRepository,
    ToolCallRepository,
    TriggerRepository,
    UnitOfWork,
    WorkflowRepository,
    WorkflowRunRepository,
)
from sro.application.ports.schedule import Scheduler, SchedulerUnavailable
from sro.application.ports.sign_in import SignInDriver, SignInFailed, SignInResult
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.tools import ToolOffered, ToolResult, ToolsUnavailable
from sro.application.ports.transcription import TranscribedSegment, Transcriber
from sro.application.ports.ui import ResolvedLocator, UiDriver, UiOutcome, UiUnavailable
from sro.application.ports.vault import CredentialVault
from sro.application.ports.vision import (
    ProposedGesture,
    Screen,
    VisionDriver,
    VisionUnavailable,
)
from sro.domain.chat.reading import ChatReading
from sro.domain.chat.thread import MessageId, Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId, ConnectionStatus
from sro.domain.execution.belts import RunProof, state_verified
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Medium, Run, RunId
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.knowledge.entry import (
    EntryKind,
    EvidenceLevel,
    KnowledgeEntry,
    KnowledgeId,
)
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.gesture import Gesture, GestureBatch, Intent
from sro.domain.observation.identity import ShapeKey
from sro.domain.observation.mining import MiningPass
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.observation.pool import (
    K_POOL_AGE,
    K_POOL_DAYS,
    RETIRED_PASSES,
    RETIRED_STALE,
    PoolEntry,
)
from sro.domain.recording.events import ActionKind
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

# `Answer` is already the trigger confirmation's; this one is a model's reply.
from sro.domain.shared.prices import Answer as ModelAnswer
from sro.domain.shared.prices import DaySpend, Effort
from sro.domain.skill.locator import LocatorStrategy
from sro.domain.skill.offers import Offer, OfferRow
from sro.domain.skill.skill import Skill
from sro.domain.skill.workflow import Workflow
from sro.domain.trigger.confirmation import Answer, Confirmation
from sro.domain.trigger.trigger import Trigger
from sro.infrastructure.db.codec import when


def _stored(moment: str) -> str:
    """An ISO instant as the store hands it back.

    Every clock the rig kept as text is a ``timestamptz`` here, and the driver
    returns one in UTC however the writer spelled it: ``12:00+02:00`` is read
    back as ``10:00+00:00``. A fake that hands back the string it was given
    disagrees with the store about the value, and -- because ISO text sorts by
    its digits rather than by its instant -- about the order too.

    Kept by ``tests/contract/test_the_repositories_agree.py``, which is where
    this was found.
    """
    return when(moment).astimezone(UTC).isoformat()


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
        self._confirmations = count(1)
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

    def new_confirmation_id(self) -> ConfirmationId:
        return ConfirmationId(f"cnf-{next(self._confirmations)}")

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

    async def list_prefix(self, prefix: str) -> dict[str, int]:
        return {
            f"s3://sro-artifacts/{key}": len(data)
            for key, data in self.objects.items()
            if key.startswith(prefix)
        }

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

        self.authorised: list[str | None] = []
        """One entry per call, whose name is on the write. A trigger's author
        and the person who approved one of its fires are different people, and
        which of them a run carries is the point of the confirmation queue."""

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
        self.authorised.append(authorized_by)
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
        self,
        tenant_id: TenantId,
        *,
        opened_by: PrincipalId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Thread, ...]:
        rows = [
            t
            for (tenant, _), t in self.rows.items()
            if tenant == str(tenant_id) and (opened_by is None or t.opened_by == opened_by)
        ]
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

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[AgentDevice, ...]:
        at = when(since)
        found = [
            device
            for device in self.rows.values()
            if device.tenant_id == tenant_id
            and (
                device.registered_at >= at
                or (device.revoked_at is not None and when(device.revoked_at) >= at)
            )
        ]
        return tuple(sorted(found, key=lambda device: device.registered_at, reverse=True))

    async def revoke(self, tenant_id: TenantId, device_id: DeviceId, *, at: str) -> bool:
        device = await self.get(tenant_id, device_id)
        if device.revoked:
            # The first revocation stands, as the store's condition makes it.
            return False
        device.revoked_at = at
        return True

    async def restore(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        device = await self.get(tenant_id, device_id)
        if not device.revoked:
            # Never revoked, so this press moved nothing -- and the secret is
            # left exactly as the store leaves it.
            return False
        device.revoked_at = None
        return True


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
        self.sent_to: str | None = None
        """The screen the browser was told to be on, where the demonstration
        recorded one."""

        self.named: tuple[str, int | None, int | None] = ("", None, None)
        """What the band in the operator's page would say. A run driving
        somebody's own browser has to be legible there rather than only in the
        panel, and the page can only say what the driver was told."""
        self.held: float | None = None

    def ui(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        origin: str | None = None,
        may_take_focus: bool = False,
        starts_on: str | None = None,
        doing: str = "",
        step: int | None = None,
        of: int | None = None,
    ) -> UiDriver:
        self.asked_for.append((str(tenant_id), str(device_id)))
        self.named = (doing, step, of)
        self.sent_to = starts_on
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

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        was_connected, self.connected = self.connected, False
        return was_connected

    async def held_for(self, tenant_id: TenantId, device_id: DeviceId) -> float | None:
        """Whatever a test set. `None` unless it says otherwise, because a
        browser that is not typing is the ordinary case."""
        return self.held


class FakeChannel:
    """Scripted replies by command kind, and a record of every envelope sent.

    The seam every mined-workflow test goes through. An unscripted kind answers
    `not_actionable`, which is what a real extension says to a command it does
    not have -- so a test that forgot to script a kind fails the way a real run
    would rather than hanging.
    """

    def __init__(self, script: Mapping[str, list[Reply]] | None = None) -> None:
        self.script = {kind: list(replies) for kind, replies in (script or {}).items()}
        self.sent: list[dict[str, object]] = []

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]:
        return (DeviceId("dev-1"),)

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        return False

    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply:
        self.sent.append(
            {
                "tenant_id": str(tenant_id),
                "device_id": str(device_id),
                "kind": kind,
                "payload": dict(payload),
                "run_id": run_id,
            }
        )
        queued = self.script.get(kind)
        if queued:
            return queued.pop(0)
        return Reply(
            ok=False, error_kind="not_actionable", error_detail=f"this extension has no {kind}"
        )


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


class FakeConfirmationRepository:
    def __init__(self) -> None:
        self.rows: dict[str, Confirmation] = {}

    async def add(self, confirmation: Confirmation) -> None:
        self.rows[confirmation.id.value] = confirmation

    async def get(self, tenant_id: TenantId, confirmation_id: ConfirmationId) -> Confirmation:
        found = self.rows.get(confirmation_id.value)
        if found is None or found.tenant_id != tenant_id:
            raise NotFound(f"confirmation {confirmation_id} not found")
        return found

    async def save(self, confirmation: Confirmation) -> None:
        self.rows[confirmation.id.value] = confirmation

    async def waiting(self, tenant_id: TenantId) -> tuple[Confirmation, ...]:
        return tuple(
            sorted(
                (
                    row
                    for row in self.rows.values()
                    if row.tenant_id == tenant_id and row.answer is Answer.WAITING
                ),
                key=lambda row: row.asked_at,
            )
        )


class FakeToolCallRepository:
    """A set, which is what the real one is: a key is claimed or it is not."""

    def __init__(self) -> None:
        self.claimed: dict[tuple[str, str], str] = {}

    async def remember(self, tenant_id: TenantId, key: str, *, tool: str, at: datetime) -> bool:
        if (tenant_id.value, key) in self.claimed:
            return False
        self.claimed[(tenant_id.value, key)] = tool
        return True


class FakeGestureRepository:
    """The evidence plane in three dicts.

    The two rules worth faking are the two the store enforces: a batch id is
    claimed once, and a second reading of one gesture replaces the first.
    """

    def __init__(self) -> None:
        self.batches: dict[str, GestureBatch] = {}
        self.rows: dict[str, Gesture] = {}
        self.intents: dict[str, Intent] = {}
        self.read_at: dict[str, datetime] = {}
        """When each reading was stored. The store keeps it in
        ``intents.created_at``, taken from the server's clock inside
        ``save_intent`` -- the record itself does not carry it, so a fake that
        answers ``intents_since`` has to keep it here."""

        self.orphan_requests: dict[tuple[str, str], Mapping[str, object]] = {}
        self.orphan_pages: list[tuple[str, str, str, Mapping[str, object]]] = []

    async def add_batch(self, batch: GestureBatch) -> None:
        if batch.batch_id in self.batches:
            raise Conflict(f"gesture batch {batch.batch_id} is already stored")
        self.batches[batch.batch_id] = batch

    async def add_gestures(self, gestures: tuple[Gesture, ...]) -> None:
        # A repeat is a ``Conflict``, as the store's unique id makes it. Writing
        # into the dict swallowed the second copy instead, so the fake said a
        # retried upload doubles nothing and the store said it is an error --
        # and ``add_batch`` raises one method over precisely to stop that
        # double. Checked before anything is written, because the store rolls
        # back and leaves none of them stored.
        fresh: dict[str, Gesture] = {}
        for gesture in gestures:
            if gesture.id in self.rows or gesture.id in fresh:
                raise Conflict("one of these gestures is already stored")
            fresh[gesture.id] = gesture
        self.rows.update(fresh)

    async def gestures_for(
        self, tenant_id: TenantId, *, ids: tuple[str, ...] | None = None
    ) -> tuple[Gesture, ...]:
        found = [
            gesture
            for gesture in self.rows.values()
            if gesture.tenant == tenant_id.value and (ids is None or gesture.id in ids)
        ]
        # (at, id), as the store orders it: `at` is the browser's clock and
        # two gestures of one burst share it.
        return tuple(sorted(found, key=lambda gesture: (gesture.at, gesture.id)))

    async def unread(self, tenant_id: TenantId, *, limit: int) -> tuple[Gesture, ...]:
        found = [
            gesture
            for gesture in await self.gestures_for(tenant_id)
            if gesture.id not in self.intents
        ]
        return tuple(found[:limit])

    async def save_intent(self, intent: Intent) -> None:
        self.intents[intent.gesture_id] = intent
        # The server's clock, as ``save_intent`` takes it, and taken again on a
        # second reading: the row is replaced, not appended to.
        self.read_at[intent.gesture_id] = datetime.now(tz=UTC)

    async def intents_for(self, tenant_id: TenantId) -> tuple[Intent, ...]:
        return tuple(intent for intent in self.intents.values() if intent.tenant == tenant_id.value)

    async def intents_since(self, tenant_id: TenantId, *, since: str) -> tuple[Intent, ...]:
        # On instants, never on the ISO text: the store compares timestamps,
        # and a naive string sorts beside an offset-bearing one with neither
        # being wrong.
        at = when(since)
        found = [
            intent
            for intent in await self.intents_for(tenant_id)
            if self.read_at[intent.gesture_id] >= at
        ]
        return tuple(
            # (created_at, gesture_id) reversed, as the store orders it: a
            # batch of readings saved in one call shares the server clock, and
            # a stable sort on the clock alone is only accidentally total.
            sorted(
                found,
                key=lambda intent: (self.read_at[intent.gesture_id], intent.gesture_id),
                reverse=True,
            )
        )

    async def add_orphan_request(
        self,
        tenant_id: TenantId,
        *,
        batch_id: str,
        request_id: str,
        payload: Mapping[str, object],
    ) -> None:
        self.orphan_requests.setdefault((batch_id, request_id), payload)

    async def add_orphan_page(
        self, tenant_id: TenantId, *, batch_id: str, at: str, payload: Mapping[str, object]
    ) -> None:
        self.orphan_pages.append((tenant_id.value, batch_id, at, payload))

    async def batch_owner(self, batch_id: str) -> str | None:
        batch = self.batches.get(batch_id)
        return None if batch is None else batch.device_id

    async def count(self, tenant_id: TenantId) -> int:
        return len(await self.gestures_for(tenant_id))

    async def streams(self, tenant_id: TenantId) -> tuple[tuple[str, float, int], ...]:
        seen: dict[str, tuple[float, int]] = {}
        for gesture in await self.gestures_for(tenant_id):
            last, many = seen.get(gesture.stream_id, (gesture.at, 0))
            seen[gesture.stream_id] = (max(last, gesture.at), many + 1)
        return tuple(
            (stream_id, last, many)
            # Newest first, the stream id breaking the tie -- and ascending
            # within it, as the store's `ORDER BY last DESC, stream_id` is.
            for stream_id, (last, many) in sorted(
                sorted(seen.items()), key=lambda one: one[1][0], reverse=True
            )
        )


class FakePoolRepository:
    """The carryover pool, with the rig's two clocks and both its caps.

    Faithful rather than convenient: an entry ages only when it was shown, an
    empty window still moves everything's waiting, and retirement is a flag
    rather than a delete -- a retired entry is still packed on its own merits.
    """

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], PoolEntry] = {}
        self.retired_ids: set[tuple[str, str]] = set()

    async def add_unclaimed(
        self, tenant_id: TenantId, *, window_ids: tuple[str, ...], claimed: frozenset[str]
    ) -> int:
        for gesture_id in claimed:
            self.rows.pop((tenant_id.value, gesture_id), None)
            self.retired_ids.discard((tenant_id.value, gesture_id))
        added = 0
        now = datetime.now(tz=UTC).isoformat()
        for gesture_id in dict.fromkeys(window_ids):
            key = (tenant_id.value, gesture_id)
            if gesture_id in claimed or key in self.rows:
                continue
            self.rows[key] = PoolEntry(
                gesture_id=gesture_id, tenant=tenant_id.value, age=0, entered_at=now
            )
            added += 1
        return added

    async def age(self, tenant_id: TenantId, *, shown: tuple[str, ...] | None = None) -> int:
        stale_before = datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS)
        retired = 0
        for key, entry in list(self.rows.items()):
            if key[0] != tenant_id.value or key in self.retired_ids:
                continue
            if shown is None:
                entry = replace(entry, age=entry.age + 1)
            elif entry.gesture_id in shown:
                entry = replace(entry, age=entry.age + 1, waited=0)
            else:
                # Including when `shown` is empty: a pass that packed nothing
                # passed everything over.
                entry = replace(entry, waited=entry.waited + 1)
            if entry.age > K_POOL_AGE:
                entry = replace(entry, reason=RETIRED_PASSES)
            elif when(entry.entered_at) < stale_before:
                entry = replace(entry, reason=RETIRED_STALE)
            if entry.reason:
                self.retired_ids.add(key)
                retired += 1
            self.rows[key] = entry
        return retired

    async def waiting(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        return self._entries(tenant_id, retired=False)

    async def ids(self, tenant_id: TenantId) -> tuple[str, ...]:
        return tuple(entry.gesture_id for entry in self._entries(tenant_id, retired=False))

    async def retired(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        return self._entries(tenant_id, retired=True)

    def _entries(self, tenant_id: TenantId, *, retired: bool) -> tuple[PoolEntry, ...]:
        found = [
            entry
            for key, entry in self.rows.items()
            if key[0] == tenant_id.value and (key in self.retired_ids) is retired
        ]
        return tuple(sorted(found, key=lambda entry: (entry.entered_at, entry.gesture_id)))


class FakeWorkflowRunRepository:
    """Runs, their steps, and the approvals on them, in two dicts.

    Faithful rather than convenient. A run is stored and returned as a copy, so
    the "steps are replaced, not appended" rule is real here and a caller that
    mutates what it loaded does not silently rewrite the store. Approvals take
    the first tap only, and the orphan sweep crosses tenants -- the two rules
    a caller can actually get wrong.
    """

    def __init__(self) -> None:
        self.rows: dict[str, WorkflowRun] = {}
        self.approved: dict[tuple[str, int], tuple[str, str | None]] = {}

    async def save(self, run: WorkflowRun) -> None:
        kept = deepcopy(run)
        # Both clocks as the store hands them back, not as the caller spelled
        # them: `started_at` is what three reads order on.
        kept.started_at = _stored(kept.started_at)
        if kept.finished_at is not None:
            kept.finished_at = _stored(kept.finished_at)
        self.rows[run.id] = kept

    async def get(self, tenant_id: TenantId, run_id: str) -> WorkflowRun | None:
        run = self.rows.get(run_id)
        return None if run is None or run.tenant != tenant_id.value else deepcopy(run)

    async def for_workflow(self, tenant_id: TenantId, workflow_id: str) -> tuple[WorkflowRun, ...]:
        found = [
            run
            for run in self.rows.values()
            if run.tenant == tenant_id.value and run.workflow_id == workflow_id
        ]
        # (started_at, id) on instants, as the store orders it: it compares
        # `timestamptz`, and two runs of one workflow can share an instant --
        # an order that is not total is an order that changes between reads.
        return tuple(
            deepcopy(run) for run in sorted(found, key=lambda run: (when(run.started_at), run.id))
        )

    async def tallies(self, tenant_id: TenantId) -> Mapping[str, tuple[int, int]]:
        # A workflow with no runs contributes no key, as the store's GROUP BY
        # gives it no row: the caller defaults it to (0, 0).
        counted: dict[str, tuple[int, int]] = {}
        for run in self.rows.values():
            if run.tenant != tenant_id.value:
                continue
            ran, held = counted.get(run.workflow_id, (0, 0))
            counted[run.workflow_id] = (ran + 1, held + (run.outcome == "held"))
        return counted

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[WorkflowRun, ...]:
        # Newest first, and on instants: the store compares `timestamptz`, and
        # `(started_at, id)` reversed is what keeps the order total.
        at = when(since)
        found = [
            run
            for run in self.rows.values()
            if run.tenant == tenant_id.value and when(run.started_at) >= at
        ]
        return tuple(
            deepcopy(run)
            for run in sorted(found, key=lambda run: (when(run.started_at), run.id), reverse=True)
        )

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        driving = [
            run
            for run in self.rows.values()
            if run.tenant == tenant_id.value
            and run.device_id == device_id.value
            and run.outcome == "running"
        ]
        driving.sort(key=lambda run: (when(run.started_at), run.id))
        return driving[0].id if driving else None

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]:
        parked = [
            (when(run.started_at), run.id, step.order, step.says)
            for run in self.rows.values()
            # Only a run still in flight, as the query is: a step left
            # `awaiting` on a finished run is not waiting on anybody.
            if run.tenant == tenant_id.value and run.outcome == "running"
            for step in run.steps
            if step.verdict == "awaiting"
        ]
        return tuple((run_id, order, says) for _, run_id, order, says in sorted(parked))

    async def approve(self, run_id: str, ord_: int, *, at: str, device_id: str | None) -> bool:
        if (run_id, ord_) in self.approved:
            return False
        # Normalised, as the store's `timestamptz` hands it back: `approvals`
        # is read by the audit, which compares the string it gets.
        self.approved[(run_id, ord_)] = (_stored(at), device_id)
        return True

    async def approvals(self, run_id: str) -> tuple[tuple[int, str, str | None], ...]:
        return tuple(
            (order, at, device_id)
            for (approved_run, order), (at, device_id) in sorted(self.approved.items())
            if approved_run == run_id
        )

    async def fail_orphans(self, reason: str) -> int:
        # Every tenant, as at startup: nobody is making the request, and a run
        # left running in one tenant goes on 409-ing its browser.
        now = datetime.now(tz=UTC).isoformat()
        orphans = sorted(
            (run for run in self.rows.values() if run.outcome == "running"),
            key=lambda run: (when(run.started_at), run.id),
        )
        for run in orphans:
            if run.steps:
                last = run.steps[-1]
                last.verdict, last.verdict_by, last.reason = "failed", "none", reason
            else:
                run.steps.append(
                    RunStep(order=0, says="", verdict="failed", verdict_by="none", reason=reason)
                )
            run.outcome = "failed"
            run.finished_at = now
        return len(orphans)


class FakeWorkflowRepository:
    """Workflows, their passes, their weak steps and their earned writes.

    Faithful rather than convenient, because the mining and runner suites will
    be built on it. Workflows are stored and returned as copies, so "steps are
    replaced, not appended" is real here. ``known`` is oldest first and a
    re-save moves a workflow to the end, which is what the store's ``created_at``
    does. ``record_effect`` keeps the state-belt gate -- a picture is not an
    effect -- and asks the domain rather than holding a second copy of the belt
    list. ``proofs`` reads the runs from the run repository, because in the
    store they are one database.
    """

    def __init__(self, runs: FakeWorkflowRunRepository | None = None) -> None:
        self.rows: dict[str, Workflow] = {}
        self.passes_made: list[MiningPass] = []
        self.poisoned = False
        """A statement has failed and the session will take no more.

        Postgres refuses every further statement on a transaction that has
        raised -- ``InFailedSQLTransactionError`` -- until somebody rolls it
        back, and it discards everything that transaction had written. A fake
        whose writes go on working after one raised cannot show a caller that
        the row it writes in a ``finally`` is lost, which is exactly what the
        mining pass writes there. Set by a test; cleared only by
        ``FakeUnitOfWork.rollback``, which is the only thing that clears it in
        the store either.

        On this repository alone, because the pass's two writes -- the workflow
        and the bill -- both land here. Widen it the day another use case needs
        a dead session somewhere else.
        """
        self.stale: dict[tuple[str, int], tuple[str | None, str]] = {}
        self.effects: dict[tuple[str, str, int], tuple[str, str]] = {}
        self.runs = runs if runs is not None else FakeWorkflowRunRepository()
        self._saved = count()
        self._created: dict[str, int] = {}

    def _alive(self) -> None:
        if self.poisoned:
            raise RuntimeError("current transaction is aborted, commands ignored")

    async def save(self, workflow: Workflow) -> None:
        self._alive()
        self.rows[workflow.id] = deepcopy(workflow)
        # The store rewrites ``created_at`` on a re-save, as INSERT OR REPLACE
        # did, so a re-saved workflow moves to the end of ``known``.
        self._created[workflow.id] = next(self._saved)

    async def known(self, tenant_id: TenantId) -> tuple[Workflow, ...]:
        found = [row for row in self.rows.values() if row.tenant == tenant_id.value]
        # (created_at, id), as the store orders it. The counter stands in for
        # the clock, and the id is the same tiebreak -- two workflows of one
        # pass can share an instant in Postgres, and the fake and the store
        # disagreeing about which comes first is a job resolved into the wrong
        # one of them, because `resolve` breaks ties with a strict `>`.
        found.sort(key=lambda row: (self._created[row.id], row.id))
        return tuple(deepcopy(row) for row in found)

    async def get(self, tenant_id: TenantId, workflow_id: str) -> Workflow:
        row = self.rows.get(workflow_id)
        if row is None or row.tenant != tenant_id.value:
            raise NotFound(f"workflow {workflow_id} was not found")
        return deepcopy(row)

    async def rekey(self, tenant_id: TenantId, workflow_id: str, key: ShapeKey) -> None:
        row = self.rows.get(workflow_id)
        if row is not None and row.tenant == tenant_id.value:
            row.shape_key = [list(entry) for entry in key]

    async def add_pass(self, mining_pass: MiningPass) -> None:
        self._alive()
        # The store's plain INSERT, which refuses a second row under one id:
        # a pass id is minted per reading, so that would be one model call
        # billed twice.
        if any(row.id == mining_pass.id for row in self.passes_made):
            raise Conflict(f"mining pass {mining_pass.id} is already stored")
        self.passes_made.append(replace(mining_pass, started_at=_stored(mining_pass.started_at)))

    async def passes(self, tenant_id: TenantId) -> tuple[MiningPass, ...]:
        made = [row for row in self.passes_made if row.tenant == tenant_id.value]
        return tuple(sorted(made, key=lambda row: (when(row.started_at), row.id)))

    async def mark_stale(
        self, workflow_id: str, ord_: int, *, matched_by: str | None, noticed_at: str
    ) -> None:
        # One row per step, so a job run every morning reports its weak step
        # once rather than daily.
        self.stale[(workflow_id, ord_)] = (matched_by, noticed_at)

    async def clear_stale(self, workflow_id: str, ord_: int) -> None:
        self.stale.pop((workflow_id, ord_), None)

    async def stale_count(self, workflow_id: str) -> int:
        return sum(1 for workflow, _ in self.stale if workflow == workflow_id)

    async def record_effect(
        self, workflow_id: str, *, run_id: str, ord_: int, verified_by: str, at: str
    ) -> None:
        # Never by a picture: a model reading a screenshot is not evidence
        # anything was written.
        if not state_verified(verified_by):
            return
        self.effects[(workflow_id, run_id, ord_)] = (verified_by, at)

    async def forget_effects(self, workflow_id: str) -> int:
        doomed = [key for key in self.effects if key[0] == workflow_id]
        for key in doomed:
            del self.effects[key]
        return len(doomed)

    async def proofs(self, tenant_id: TenantId, workflow_id: str) -> tuple[RunProof, ...]:
        held = [
            run
            for run in (await self.runs.for_workflow(tenant_id, workflow_id))
            if run.live and run.outcome == "held"
        ]
        return tuple(
            RunProof(
                run_id=run.id,
                wrote=frozenset(
                    step.order for step in run.steps if (step.result or {}).get("wrote")
                ),
                verified=frozenset(
                    ord_
                    for (workflow, effect_run, ord_) in self.effects
                    if workflow == workflow_id and effect_run == run.id
                ),
            )
            for run in held
        )


class FakeOfferRepository:
    """What was offered, in a list, in the order it arrived.

    Faithful rather than convenient, because plan 3's counsel is built on it.
    The list order IS the store's ``seq``: the window is a stable sort on ``at``
    over the reverse of it, which is what ``ORDER BY at DESC, seq DESC`` does,
    and ``k > 0`` is filtered here rather than by the caller because that is
    where the query does it.
    """

    def __init__(self) -> None:
        self.rows: list[Offer] = []

    async def record(self, offer: Offer) -> None:
        self.rows.append(replace(offer, at=_stored(offer.at)))

    async def newest(
        self, tenant_id: TenantId, workflow_id: str, *, limit: int
    ) -> tuple[OfferRow, ...]:
        return self._window(
            lambda offer: offer.tenant == tenant_id.value and offer.workflow_id == workflow_id,
            limit,
        )

    async def newest_for_device(
        self, tenant_id: TenantId, workflow_id: str, device_id: DeviceId, *, limit: int
    ) -> tuple[OfferRow, ...]:
        return self._window(
            lambda offer: (
                offer.tenant == tenant_id.value
                and offer.workflow_id == workflow_id
                and offer.device_id == device_id.value
            ),
            limit,
        )

    async def fates(self, tenant_id: TenantId, workflow_id: str) -> Mapping[str, int]:
        counted: dict[str, int] = {}
        for offer in self.rows:
            if offer.tenant == tenant_id.value and offer.workflow_id == workflow_id:
                counted[offer.fate] = counted.get(offer.fate, 0) + 1
        return counted

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[Offer, ...]:
        # Reversed first, then a stable sort on the instant: offers that tie
        # keep the reverse of arrival order, which is the store's ``seq DESC``.
        at = when(since)
        found = [
            offer
            for offer in reversed(self.rows)
            if offer.tenant == tenant_id.value and when(offer.at) >= at
        ]
        found.sort(key=lambda offer: when(offer.at), reverse=True)
        return tuple(found)

    def _window(self, mine: Callable[[Offer], bool], limit: int) -> tuple[OfferRow, ...]:
        # Reversed first, then sorted on the instant: Python's sort is stable,
        # so offers that tie keep the reversed arrival order, which is the
        # `seq DESC` half of the tiebreak. On the instant rather than on the ISO
        # text, because the store compares `timestamptz` -- `record` has already
        # normalised what it stored, and this says the rule out loud.
        found = [offer for offer in reversed(self.rows) if mine(offer) and offer.k > 0]
        found.sort(key=lambda offer: when(offer.at), reverse=True)
        return tuple(OfferRow(k=offer.k, fate=offer.fate, at=offer.at) for offer in found[:limit])


class FakeChatRepository:
    """What the chat door cost. Never what it read -- there is nowhere to put
    it here either, which is the point."""

    def __init__(self) -> None:
        self.rows: list[ChatReading] = []

    async def record(self, reading: ChatReading) -> None:
        self.rows.append(replace(reading, at=_stored(reading.at)))

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[ChatReading, ...]:
        # On instants rather than on the ISO text the record carries: the store
        # compares ``timestamptz``, and text ordering disagrees with it the
        # moment two rows carry different offsets -- or one carries none.
        at = when(since)
        found = [
            reading
            for reading in self.rows
            if reading.tenant == tenant_id.value and when(reading.at) >= at
        ]
        # (at, id) reversed, as the store orders it: `at` comes off the record,
        # so two readings can carry one instant and there is no arrival column.
        return tuple(
            sorted(found, key=lambda reading: (when(reading.at), reading.id), reverse=True)
        )


class FakeSpendRepository:
    """The day's bill, summed off the other fakes rather than out of a dict.

    The four tables are four repositories here, so this holds none of its own
    rows: it reads theirs, with the rig's predicates. A fake that could be
    handed a total nobody spent would prove nothing about a cap.
    """

    def __init__(
        self,
        gestures: FakeGestureRepository,
        workflows: FakeWorkflowRepository,
        workflow_runs: FakeWorkflowRunRepository,
        chats: FakeChatRepository,
    ) -> None:
        self._gestures = gestures
        self._workflows = workflows
        self._workflow_runs = workflow_runs
        self._chats = chats

    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend:
        aware = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
        midnight = aware.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        since = midnight.isoformat()

        readings = await self._gestures.intents_since(tenant_id, since=since)
        passes = [
            one
            for one in await self._workflows.passes(tenant_id)
            if when(one.started_at) >= midnight
        ]
        runs = await self._workflow_runs.since(tenant_id, since=since)
        chats = await self._chats.since(tenant_id, since=since)

        usd = (
            sum(one.cost_usd for one in readings)
            + sum(one.cost_usd for one in passes)
            + sum(one.cost_usd for one in runs)
            + sum(one.cost_usd for one in chats)
        )
        # A call that errored was never billed, so it is unpriced without being
        # blind; a run carries no error column, so its blind row is the one
        # that billed nothing at all. The rig's `SPENT_IN`, predicate for
        # predicate.
        blind = (
            sum(1 for one in readings if one.unpriced and one.error is None)
            + sum(1 for one in passes if one.unpriced and one.error is None)
            + sum(1 for one in runs if one.unpriced and one.cost_usd == 0.0)
            + sum(1 for one in chats if one.unpriced and one.error is None)
        )
        return DaySpend(cost_usd=usd, blind=blind)


_REPOSITORIES = frozenset(
    {
        "recordings",
        "skills",
        "connections",
        "runs",
        "knowledge",
        "model_calls",
        "threads",
        "browser_sessions",
        "devices",
        "observations",
        "gestures",
        "workflow_runs",
        "workflows",
        "offers",
        "chats",
        "spend",
        "pool",
        "observation_policies",
        "candidates",
        "triggers",
        "tool_calls",
        "confirmations",
    }
)
"""Every attribute `strict` refuses before entry -- the ports `SqlUnitOfWork`
assigns inside its own `__aenter__`, and has not got before it."""


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
    gestures: GestureRepository
    workflow_runs: WorkflowRunRepository
    workflows: WorkflowRepository
    offers: OfferRepository
    chats: ChatRepository
    spend: SpendRepository
    pool: PoolRepository
    observation_policies: ObservationPolicyRepository
    candidates: CandidateRepository
    triggers: TriggerRepository
    tool_calls: ToolCallRepository
    confirmations: ConfirmationRepository

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
        self.gestures = FakeGestureRepository()
        self.workflow_runs = FakeWorkflowRunRepository()
        # One database in the store, so the workflow repository reads the
        # same runs: ``proofs`` walks them. Held concretely as well, because
        # ``rollback`` has to clear its poison and the attribute above is
        # declared as the port -- a port has no such flag.
        self._workflows = FakeWorkflowRepository(self.workflow_runs)
        self.workflows = self._workflows
        self.offers = FakeOfferRepository()
        self.chats = FakeChatRepository()
        # One database in the store: the day's bill is summed over the same
        # four repositories the rest of the unit of work writes to.
        self.spend = FakeSpendRepository(
            self.gestures, self._workflows, self.workflow_runs, self.chats
        )
        self.pool = FakePoolRepository()
        self.observation_policies = FakeObservationPolicyRepository()
        self.candidates = FakeCandidateRepository()
        self.triggers = FakeTriggerRepository()
        self.tool_calls = FakeToolCallRepository()
        self.confirmations = FakeConfirmationRepository()
        self.commits = 0
        self.rollbacks = 0
        self.commit_raises: Exception | None = None
        """What ``commit`` should raise instead of committing.

        A fake that cannot fail cannot prove what a caller does when a commit
        does -- and losing a write to somebody else's concurrent one is exactly
        the failure a caller has to handle rather than log."""

    strict = False
    """Refuse a repository until the session opens, as the real one does.

    `SqlUnitOfWork` assigns every repository inside `__aenter__`, so touching
    one before is an `AttributeError` there and a working read here -- a fake
    more permissive than the thing it doubles, which is how `ServeShapes` and
    `read_spend` shipped without an `async with` and passed 2299 tests.

    Off by default and armed by the seam that owns the session: the container
    hands out a unit of work nobody has entered, so `_FakeContainer` arms it
    on the way out. Left off for a test calling a bare function like
    `over_cap` or `shapes_for` directly -- those are documented to take a
    session their caller already opened, and the test IS that caller."""

    _entered = False

    def __getattribute__(self, name: str) -> object:
        if (
            name in _REPOSITORIES
            and object.__getattribute__(self, "strict")
            and not object.__getattribute__(self, "_entered")
            # Asked by `sro`, not by a test. The instance is shared, so the
            # fixture that plants a workflow before the request reaches this
            # too -- and a test standing in for the store it is arranging is
            # not the caller that has to hold a session.
            and sys._getframe(1).f_globals.get("__name__", "").startswith("sro.")
        ):
            raise AttributeError(
                f"{name!r} before __aenter__: a unit of work has no repositories"
                " until its session opens. Open `async with self._uow as uow:`"
                " and read the repository off `uow`."
            )
        return object.__getattribute__(self, name)

    def hand_out(self) -> FakeUnitOfWork:
        """This one, as a container hands it out: strict, and not yet entered.

        The instance is shared so the store survives the request, which the
        real one has a database for. The unopened-ness is what is restored."""
        self.strict = True
        self._entered = False
        return self

    async def __aenter__(self) -> FakeUnitOfWork:
        self._entered = True
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
        # A rollback makes a killed session usable again, which is the half
        # this fake models. It does not throw away what the transaction had
        # written -- the class does not simulate rollback at all, and the
        # integration suite is where that half is proved.
        self._workflows.poisoned = False


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


class FakeAsker:
    """Queued answers, and a record of every question.

    Not a dataclass: it takes *answers positionally, and @dataclass would
    replace this __init__ with a generated one.
    """

    def __init__(self, *answers: ModelAnswer) -> None:
        self.answers = list(answers)
        self.asked: list[dict[str, object]] = []

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, object],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> ModelAnswer:
        # Yield, because the real thing does. Without a suspension point this
        # double never lets another task interleave, so any test racing two
        # callers with asyncio.gather passes whether or not the code under test
        # actually serialises -- it proves the double, not the code.
        await asyncio.sleep(0)
        self.asked.append(
            {
                "model": model,
                "instructions": instructions,
                "evidence": evidence,
                "schema": schema,
                "image": image,
                "images": images,
                "effort": effort,
            }
        )
        if not self.answers:
            return ModelAnswer(error="the fake ran out of answers")
        return self.answers.pop(0)


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
_channel: Channel = FakeChannel()
_scheduler: Scheduler = FakeScheduler()
_dispatcher: RunDispatcher = FakeRunDispatcher()
_triggers: TriggerRepository = FakeTriggerRepository()
_tool_calls: ToolCallRepository = FakeToolCallRepository()
_confirmations: ConfirmationRepository = FakeConfirmationRepository()
_candidates: CandidateRepository = FakeCandidateRepository()
_asker: Asker = FakeAsker()


class FakeToolCaller:
    """A connector that answers whatever the test told it to."""

    def __init__(
        self,
        answers: dict[str, ToolResult] | None = None,
        *,
        offers: dict[str, tuple[ToolOffered, ...]] | None = None,
        available: bool = True,
    ) -> None:
        self._answers = answers or {}
        self._offers = offers or {}
        self._available = available
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    @property
    def available(self) -> bool:
        return self._available

    async def list_tools(self, server: str) -> tuple[ToolOffered, ...]:
        if server not in self._offers:
            raise ToolsUnavailable(f"no connector called {server}")
        return self._offers[server]

    async def call(self, server: str, tool: str, arguments: Mapping[str, str]) -> ToolResult:
        if not self._available:
            raise ToolsUnavailable("no connectors are configured")
        self.calls.append((server, tool, dict(arguments)))
        answer = self._answers.get(tool)
        if answer is None:
            raise ToolsUnavailable(f"{server} offers no tool called {tool}")
        return answer
