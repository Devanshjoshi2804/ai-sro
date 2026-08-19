"""Composition root. The only module allowed to import ``sro.infrastructure``.

Everything above this line depends on protocols; the choice of Postgres, MinIO
or Steel is made here and nowhere else. Swapping an adapter is an edit to this
file, which is the whole point of the dependency rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.connection.check_session import CheckSession
from sro.application.connection.connect_system import (
    AcknowledgeFailures,
    ConnectSystem,
    LoadSession,
    RefreshSession,
    StoreSession,
)
from sro.application.connection.keep_open import KeepSessionsOpen
from sro.application.connection.release_strays import ReleaseStrayBrowsers
from sro.application.connection.session_headers import StoreSessionHeaders
from sro.application.connection.session_life import SessionLife
from sro.application.connection.sign_in import EnsureSignedIn, SignIn, StoreCredentials
from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.execution.batch import RunBatch
from sro.application.execution.choices import ListChoices
from sro.application.execution.derived_read import AskTheSystem
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecuteStep,
    FinishRun,
    StartRun,
)
from sro.application.execution.pursue_goal import PursueGoal
from sro.application.execution.pursuits import Pursuits
from sro.application.execution.read_runs import GetRun, ListRuns
from sro.application.execution.self_heal import SelfHeal
from sro.application.execution.vision_step import PerformWithVision
from sro.application.induction.induce_skill import InduceSkill
from sro.application.induction.understand import UnderstandRecording
from sro.application.intent.narrow import NarrowARead
from sro.application.intent.next_steps import SuggestNext
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.backfill import BackfillEmbeddings
from sro.application.knowledge.learn_from_run import LearnFromRun
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.read_knowledge import ReadKnowledge
from sro.application.knowledge.record_claim import RecordClaims
from sro.application.knowledge.retrieve import Retrieve
from sro.application.ports.auth import Credentials
from sro.application.ports.blob import BlobStore
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.capture import CaptureController
from sro.application.ports.durable import DurableExecution
from sro.application.ports.embedding import Embedder
from sro.application.ports.http import HttpCaller
from sro.application.ports.intent import IntentParser
from sro.application.ports.interpretation import WorkflowInterpreter
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.sign_in import SignInDriver
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.token import TokenSource
from sro.application.ports.transcription import Transcriber
from sro.application.ports.ui import UiDriver
from sro.application.ports.vault import CredentialVault, VaultUnavailable
from sro.application.ports.vision import VisionDriver
from sro.application.recording.attach_artifact import AttachArtifact
from sro.application.recording.finish_recording import FinishRecording
from sro.application.recording.get_recording import GetRecording
from sro.application.recording.ingest_capture_events import IngestCaptureEvents
from sro.application.recording.list_recordings import ListRecordings
from sro.application.recording.live_view import GetLiveView
from sro.application.recording.media import GetRecordingMedia
from sro.application.recording.start_recording import StartRecording
from sro.application.skill.describe_skill import DescribeSkill
from sro.application.skill.promote_skill import PromoteSkill
from sro.application.skill.read_skills import GetSkill, ListSkills
from sro.config import Settings, get_settings
from sro.infrastructure.auth.keycloak import KeycloakTokens
from sro.infrastructure.auth.signed_tokens import SignedTokens
from sro.infrastructure.blob.minio_store import MinioBlobStore
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.db.session import create_engine, create_session_factory
from sro.infrastructure.gemini.computer_use import GeminiVisionDriver
from sro.infrastructure.gemini.intent import GeminiIntentParser
from sro.infrastructure.gemini.interpreter import GeminiInterpreter
from sro.infrastructure.gemini.null_intent import NoIntentParser
from sro.infrastructure.gemini.null_interpreter import NoInterpreter
from sro.infrastructure.http.httpx_caller import HttpxCaller
from sro.infrastructure.knowledge.embedding import GeminiEmbedder, NoEmbedder
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.sign_in import PlaywrightSignIn
from sro.infrastructure.steel.supervisor import CaptureSupervisor
from sro.infrastructure.steel.ui_driver import PlaywrightUiDriver
from sro.infrastructure.system import SystemClock, UuidFactory
from sro.infrastructure.telemetry.otel import configure_tracing
from sro.infrastructure.temporal.durable import TemporalDurableExecution
from sro.infrastructure.transcription.gemini import GeminiTranscriber
from sro.infrastructure.transcription.null import NullTranscriber
from sro.infrastructure.vault.file_vault import FileCredentialVault


@dataclass
class Container:
    """Long-lived adapters, built once per process.

    Use cases are cheap objects built per call: they hold a unit of work, which
    must not be shared between concurrent requests.
    """

    settings: Settings
    clock: Clock
    ids: IdFactory
    blobs: BlobStore
    browser: BrowserProvider
    transcriber: Transcriber
    embedder: Embedder
    vision: VisionDriver | None
    interpreter: WorkflowInterpreter
    intent_parser: IntentParser
    vault: CredentialVault
    http: HttpCaller
    ui: UiDriver
    sign_in_driver: SignInDriver
    tokens: TokenSource | None
    credentials: Credentials
    durable: DurableExecution
    session_factory: async_sessionmaker[AsyncSession]

    pursuits: Pursuits = field(default_factory=Pursuits)

    _sessions_first_seen: dict[str, datetime] = field(default_factory=dict)
    """When the stray sweep first saw a browser nothing claims. Held here
    because a use case is built per call and this has to outlive one sweep."""
    """Pursuits this process is driving. In memory on purpose: the browser one
    was driving does not survive a restart either, and a half-finished pursuit
    resumed against a screen nobody can see is worse than one that stopped."""

    capture: CaptureController = field(init=False)
    """Set by ``build_container``: the supervisor is built from the container's
    own use-case factories, so it cannot be a constructor argument."""

    def unit_of_work(self) -> UnitOfWork:
        return SqlUnitOfWork(self.session_factory)

    async def database_reachable(self) -> bool:
        """Readiness probe. Lives here so the interface layer stays free of SQL."""
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True

    def start_recording(self) -> StartRecording:
        return StartRecording(self.unit_of_work(), self.browser, self.clock, self.ids)

    def ingest_capture_events(self) -> IngestCaptureEvents:
        return IngestCaptureEvents(self.unit_of_work())

    def attach_artifact(self) -> AttachArtifact:
        return AttachArtifact(self.unit_of_work(), self.blobs, self.clock, self.transcriber)

    def list_recordings(self) -> ListRecordings:
        return ListRecordings(self.unit_of_work())

    def connect_system(self) -> ConnectSystem:
        return ConnectSystem(self.unit_of_work(), self.browser, self.clock, self.ids)

    def store_session(self) -> StoreSession:
        return StoreSession(self.unit_of_work(), self.vault, self.clock, self.browser)

    def store_credentials(self) -> StoreCredentials:
        return StoreCredentials(self.unit_of_work(), self.vault)

    def session_life(self) -> SessionLife:
        return SessionLife(self.unit_of_work(), self.record_claims())

    def sign_in(self) -> SignIn:
        return SignIn(
            self.unit_of_work(),
            self.vault,
            self.browser,
            self.sign_in_driver,
            self.refresh_session(),
            self.session_life(),
            self.clock,
        )

    def ensure_signed_in(self) -> EnsureSignedIn:
        return EnsureSignedIn(
            self.sign_in(),
            self.check_session(),
            self.unit_of_work(),
            self.session_life(),
            self.clock,
        )

    def watch_browsers(self) -> WatchBrowsers:
        return WatchBrowsers(self.browser)

    def release_stray_browsers(self) -> ReleaseStrayBrowsers:
        return ReleaseStrayBrowsers(
            self.unit_of_work(),
            self.browser,
            self.watch_browsers(),
            self.pursuits,
            self.clock,
            self._sessions_first_seen,
        )

    def keep_sessions_open(self) -> KeepSessionsOpen:
        return KeepSessionsOpen(
            self.unit_of_work(), self.ensure_signed_in(), self.release_stray_browsers()
        )

    def acknowledge_failures(self) -> AcknowledgeFailures:
        return AcknowledgeFailures(self.unit_of_work(), self.clock)

    def check_session(self) -> CheckSession:
        return CheckSession(
            self.unit_of_work(),
            self.vault,
            self.http,
            self.browser,
            self.refresh_session(),
        )

    def refresh_session(self) -> RefreshSession:
        return RefreshSession(self.unit_of_work(), self.vault, self.clock)

    def store_session_headers(self) -> StoreSessionHeaders:
        return StoreSessionHeaders(self.unit_of_work(), self.vault)

    def load_session(self) -> LoadSession:
        return LoadSession(self.unit_of_work(), self.vault)

    def get_recording(self) -> GetRecording:
        return GetRecording(self.unit_of_work())

    def list_skills(self) -> ListSkills:
        return ListSkills(self.unit_of_work())

    def get_skill(self) -> GetSkill:
        return GetSkill(self.unit_of_work())

    def get_live_view(self) -> GetLiveView:
        return GetLiveView(self.unit_of_work(), self.browser)

    def get_recording_media(self) -> GetRecordingMedia:
        return GetRecordingMedia(self.unit_of_work(), self.blobs)

    def finish_recording(self) -> FinishRecording:
        return FinishRecording(self.unit_of_work(), self.browser, self.clock)

    def induce_skill(self) -> InduceSkill:
        return InduceSkill(
            self.unit_of_work(), self.clock, self.ids, self.ask_about(), self.interpreter
        )

    def understand_recording(self) -> UnderstandRecording:
        return UnderstandRecording(self.unit_of_work(), self.interpreter, self.clock, self.ids)

    def promote_skill(self) -> PromoteSkill:
        return PromoteSkill(self.unit_of_work(), self.clock)

    def describe_skill(self) -> DescribeSkill:
        return DescribeSkill(self.unit_of_work())

    def learn_from_run(self) -> LearnFromRun:
        return LearnFromRun(self.record_claims())

    def perform_with_vision(self) -> PerformWithVision:
        return PerformWithVision(
            self.ui,
            self.vision,
            self.clock,
            egress_enabled=self.settings.vision_enabled,
            destination=f"gemini:{self.settings.gemini_vision_model}",
            model=self.settings.gemini_vision_model,
        )

    def execute_skill(self) -> ExecuteSkill:
        return ExecuteSkill(
            self.unit_of_work(),
            self.http,
            self.vault,
            self.clock,
            self.ids,
            self.ui,
            self.learn_from_run(),
            self.perform_with_vision(),
        )

    def start_run(self) -> StartRun:
        return StartRun(self.unit_of_work(), self.clock, self.ids)

    def pursue_goal(self) -> PursueGoal:
        return PursueGoal(
            self.unit_of_work(),
            self.vault,
            self.browser,
            self.ui,
            self.vision,
            self.clock,
            self.capture,
            self.start_recording(),
            self.finish_recording(),
            self.understand_recording(),
            egress_enabled=self.settings.vision_enabled,
            model=self.settings.gemini_vision_model,
        )

    def self_heal(self) -> SelfHeal:
        return SelfHeal(
            self.unit_of_work(),
            self.vault,
            self.browser,
            self.check_session(),
            self.ensure_signed_in(),
            self.record_claims(),
            self.refresh_session(),
        )

    def execute_step(self) -> ExecuteStep:
        return ExecuteStep(
            self.unit_of_work(),
            self.http,
            self.vault,
            self.ui,
            self.perform_with_vision(),
            self.self_heal(),
            self.tokens,
        )

    def finish_run(self) -> FinishRun:
        return FinishRun(self.unit_of_work(), self.clock, self.learn_from_run())

    def record_claims(self) -> RecordClaims:
        return RecordClaims(self.unit_of_work(), self.clock, self.ids, self.embedder)

    def backfill_embeddings(self) -> BackfillEmbeddings:
        return BackfillEmbeddings(self.unit_of_work(), self.embedder)

    def ask_about(self) -> AskAbout:
        return AskAbout(self.unit_of_work(), self.record_claims())

    def read_knowledge(self) -> ReadKnowledge:
        return ReadKnowledge(self.unit_of_work())

    def retrieve_knowledge(self) -> Retrieve:
        return Retrieve(self.unit_of_work(), self.embedder)

    def start_thread(self) -> StartThread:
        return StartThread(self.unit_of_work(), self.clock, self.ids)

    def converse(self) -> Converse:
        return Converse(
            self.unit_of_work(),
            self.resolve_intent(),
            self.clock,
            self.ids,
            self.execute_skill(),
            self.narrow_a_read(),
            self.ask_the_system(),
            self.ask_about(),
            self.suggest_next(),
        )

    def read_threads(self) -> ReadThreads:
        return ReadThreads(self.unit_of_work())

    def plan_task(self) -> PlanTask:
        return PlanTask(self.retrieve_knowledge())

    def suggest_next(self) -> SuggestNext:
        return SuggestNext(self.unit_of_work(), self.intent_parser)

    def narrow_a_read(self) -> NarrowARead:
        return NarrowARead(
            self.unit_of_work(), self.intent_parser, self.ask_about(), self.ask_the_system()
        )

    def ask_the_system(self) -> AskTheSystem:
        return AskTheSystem(self.unit_of_work(), self.http, self.vault)

    def resolve_intent(self) -> ResolveIntent:
        return ResolveIntent(self.unit_of_work(), self.plan_task(), self.intent_parser)

    def run_batch(self) -> RunBatch:
        return RunBatch(self.execute_skill())

    def list_choices(self) -> ListChoices:
        return ListChoices(self.unit_of_work(), self.http, self.vault)

    def get_run(self) -> GetRun:
        return GetRun(self.unit_of_work())

    def list_runs(self) -> ListRuns:
        return ListRuns(self.unit_of_work())


def _build_transcriber(settings: Settings) -> Transcriber:
    """Narration leaves the deployment, so it takes two switches, not one.

    A key on its own is not consent to send a customer's operators' voices to a
    hosted model; `transcription_enabled` is that decision, made per deployment.
    """
    if settings.transcription_enabled and settings.gemini_api_key:
        return GeminiTranscriber(settings.gemini_api_key, settings.gemini_transcription_model)
    return NullTranscriber()


def _build_intent_parser(settings: Settings) -> IntentParser:
    """Reading values out of an operator's sentence. Same switch as the rest:
    the words they type are theirs, and sending them is a decision."""
    if settings.interpretation_enabled and settings.gemini_api_key:
        return GeminiIntentParser(settings.gemini_api_key, settings.gemini_intent_model)
    return NoIntentParser()


def _build_interpreter(settings: Settings) -> WorkflowInterpreter:
    """Reading a demonstration sends its calls and bodies to a hosted model."""
    if settings.interpretation_enabled and settings.gemini_api_key:
        return GeminiInterpreter(settings.gemini_api_key, settings.gemini_interpreter_model)
    return NoInterpreter()


def _build_vision(settings: Settings) -> VisionDriver | None:
    """Two switches again, and the more consequential pair: this one sends a
    picture of a customer's live warehouse system."""
    if settings.vision_enabled and settings.gemini_api_key:
        return GeminiVisionDriver(settings.gemini_api_key, settings.gemini_vision_model)
    return None


def _build_embedder(settings: Settings) -> Embedder:
    """Same two-switch rule as transcription: a key is not consent to send."""
    if settings.knowledge_embeddings_enabled and settings.gemini_api_key:
        return GeminiEmbedder(settings.gemini_api_key, settings.gemini_embedding_model)
    return NoEmbedder()


def _build_vault(settings: Settings) -> CredentialVault:
    """A vault that refuses to start beats one that writes plaintext.

    The failure is deferred to first use rather than to boot: reading recordings
    and reviewing skills need no secrets, and an API that will not start because
    nobody has generated a key yet is worse than one that says so when a
    connection is attempted.
    """
    try:
        return FileCredentialVault(path=Path(settings.vault_path), key=settings.vault_key)
    except VaultUnavailable as exc:
        return _UnavailableVault(str(exc))


@dataclass(frozen=True, slots=True)
class _UnavailableVault:
    reason: str

    async def store(self, key: str, value: str) -> None:
        raise VaultUnavailable(self.reason)

    async def get(self, key: str) -> str | None:
        raise VaultUnavailable(self.reason)

    async def delete(self, key: str) -> None:
        raise VaultUnavailable(self.reason)


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    configure_tracing(
        service_name=settings.service_name,
        endpoint=settings.otlp_endpoint,
        environment=settings.environment,
    )

    engine = create_engine(settings.database_url, echo=settings.debug)

    container = Container(
        settings=settings,
        clock=SystemClock(),
        ids=UuidFactory(),
        blobs=MinioBlobStore(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
            region=settings.s3_region,
        ),
        browser=SteelClient(
            settings.steel_base_url,
            settings.steel_cdp_url,
            session_timeout_seconds=settings.steel_session_timeout_seconds,
            dimensions=(settings.browser_width, settings.browser_height),
        ),
        transcriber=_build_transcriber(settings),
        embedder=_build_embedder(settings),
        vision=_build_vision(settings),
        interpreter=_build_interpreter(settings),
        intent_parser=_build_intent_parser(settings),
        vault=(built_vault := _build_vault(settings)),
        http=HttpxCaller(),
        ui=PlaywrightUiDriver(settings.ui_debugger_url),
        sign_in_driver=PlaywrightSignIn(),
        tokens=(
            KeycloakTokens(
                built_vault,
                realm_url=settings.keycloak_realm_url,
                client_id=settings.keycloak_client_id,
                client_secret=settings.keycloak_client_secret,
            )
            if settings.keycloak_realm_url and settings.keycloak_client_id
            else None
        ),
        credentials=SignedTokens(settings.auth_secret),
        durable=TemporalDurableExecution(
            address=settings.temporal_address, namespace=settings.temporal_namespace
        ),
        session_factory=create_session_factory(engine),
    )
    container.capture = CaptureSupervisor(
        blobs=container.blobs,
        ingest=container.ingest_capture_events,
        artifacts=container.attach_artifact,
        drain_interval_seconds=settings.capture_drain_interval_seconds,
        inline_body_limit_bytes=settings.inline_body_limit_bytes,
        screenshot_per_gesture=settings.capture_screenshot_per_frame,
        video=settings.capture_video,
        video_fps=settings.capture_video_fps,
        redact_secrets=settings.capture_redact_secret_values,
    )
    return container
