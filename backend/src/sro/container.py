from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from sro.application.analytics.audit import ReadAudit
from sro.application.analytics.summary import ReadSummary
from sro.application.capture.devices import ReadRoster, RestoreDevice, RevokeDevice
from sro.application.chat.about_an_offer import AskAboutTheOffer, SayTheRunStarted
from sro.application.chat.ask_the_asker import DraftForTheAsker, SendTheDraft
from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.from_the_mail import FromTheMail
from sro.application.chat.read_chat import ReadChat
from sro.application.chat.read_threads import ReadThreads
from sro.application.chat.reading_an_answer import IsItAnAnswer
from sro.application.connection.browsers import Browsers
from sro.application.connection.check_session import CheckSession
from sro.application.connection.connect_system import (
    AcknowledgeFailures,
    ConnectSystem,
    LoadSession,
    RefreshSession,
    StoreSession,
)
from sro.application.connection.establish_token import EstablishToken
from sro.application.connection.keep_open import KeepSessionsOpen
from sro.application.connection.list_connections import ListConnections
from sro.application.connection.refusals import ForgetsRefusalOnWrite
from sro.application.connection.release_strays import ReleaseStrayBrowsers
from sro.application.connection.session_headers import StoreSessionHeaders
from sro.application.connection.session_life import SessionLife
from sro.application.connection.sign_in import EnsureSignedIn, SignIn, StoreCredentials
from sro.application.connection.watch_browser import WatchBrowsers
from sro.application.context import RequestContext
from sro.application.execution.approvals import Approvals
from sro.application.execution.batch import RunBatch
from sro.application.execution.call_run_wrong import CallRunWrong
from sro.application.execution.choices import ListChoices
from sro.application.execution.derived_read import AskTheSystem
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecuteStep,
    FinishRun,
    StartRun,
)
from sro.application.execution.gather import GatherContext
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.pursue_goal import PursueGoal
from sro.application.execution.pursuits import Pursuits
from sro.application.execution.read_runs import GetRun, ListRuns, StopRun
from sro.application.execution.run_from_preview import RunFromPreview
from sro.application.execution.run_workflow import fail_orphans
from sro.application.execution.self_heal import SelfHeal
from sro.application.execution.stops import Stops
from sro.application.execution.vision_step import PerformWithVision
from sro.application.execution.workflow_runs import (
    AbortWorkflowRun,
    ApproveWorkflowStep,
    GetWorkflowRun,
    ListWorkflowRuns,
    StartWorkflowRun,
)
from sro.application.induction.understand import UnderstandRecording
from sro.application.intent.narrow import NarrowARead
from sro.application.intent.next_steps import SuggestNext
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.intent.spend import spent_today
from sro.application.knowledge.backfill import BackfillEmbeddings
from sro.application.knowledge.learn_from_run import LearnFromRun
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.read_knowledge import ReadKnowledge
from sro.application.knowledge.record_claim import RecordClaims
from sro.application.knowledge.retrieve import Retrieve
from sro.application.lookup.plan_lookups import PlanLookups
from sro.application.lookup.run_lookups import RunLookups
from sro.application.observation.artifacts import StoreObservationArtifact
from sro.application.observation.forget import ForgetObservations
from sro.application.observation.ingest import IngestObservation
from sro.application.observation.mine_lately import MineLately
from sro.application.observation.mine_pass import MinePass
from sro.application.observation.policy import ReadObservationPolicy, SetObservationPolicy
from sro.application.observation.read_gesture import ReadGestures
from sro.application.observation.read_shots import ReadShots
from sro.application.observation.record_attempt import RecordAttempt
from sro.application.observation.register import (
    GrantHost,
    ReadDevice,
    RecordHeartbeat,
    RegisterDevice,
    RevokeHost,
)
from sro.application.observation.retain import SweepRetention
from sro.application.ports.agent import AgentDrivers
from sro.application.ports.auth import Credentials
from sro.application.ports.blob import BlobStore
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.capture import CaptureController
from sro.application.ports.dispatch import RunDispatcher
from sro.application.ports.durable import DurableExecution
from sro.application.ports.embedding import Embedder
from sro.application.ports.http import HttpCaller
from sro.application.ports.intent import IntentParser
from sro.application.ports.interpretation import WorkflowInterpreter
from sro.application.ports.locks import AccountLocks
from sro.application.ports.model import Asker
from sro.application.ports.page import PageDriver
from sro.application.ports.pool import BrowserPool
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.schedule import Scheduler
from sro.application.ports.sign_in import SignInDriver
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.token import TokenSource
from sro.application.ports.tools import ToolCaller
from sro.application.ports.transcription import Transcriber
from sro.application.ports.ui import UiDriver
from sro.application.ports.vault import CredentialVault, VaultUnavailable
from sro.application.ports.vision import VisionDriver
from sro.application.recording.attach_artifact import AttachArtifact
from sro.application.recording.finish_recording import FinishRecording
from sro.application.recording.ingest_capture_events import IngestCaptureEvents
from sro.application.recording.start_recording import StartRecording
from sro.application.skill.describe_skill import DescribeSkill
from sro.application.skill.read_skills import GetSkill, ListSkills
from sro.application.skill.read_workflows import ReadEvidence, ReadWorkflows
from sro.application.skill.record_offer import RecordOffer
from sro.application.skill.repair_drift import RepairDrift
from sro.application.skill.retire_workflow import RetireWorkflow
from sro.application.skill.serve_shapes import ServeShapes
from sro.application.trigger.answer_confirmation import (
    AnswerConfirmation,
    ExpireConfirmations,
    ReadConfirmations,
)
from sro.application.trigger.create_trigger import CreateTrigger
from sro.application.trigger.fire_trigger import FireTrigger
from sro.application.trigger.read_triggers import DeleteTrigger, ReadTriggers, SetTriggerEnabled
from sro.application.trigger.receive_inbound import ReceiveInbound
from sro.config import Settings, get_settings
from sro.domain.chat.asking import Pending
from sro.domain.shared.prices import DaySpend
from sro.infrastructure.agent.channel import SocketChannel
from sro.infrastructure.agent.drivers import RemoteAgents
from sro.infrastructure.agent.sockets import DeviceSockets
from sro.infrastructure.auth.keycloak import KeycloakTokens
from sro.infrastructure.auth.signed_tokens import SignedTokens
from sro.infrastructure.blob.minio_store import MinioBlobStore
from sro.infrastructure.db.locks import K_LOCK_CONNECT_TIMEOUT_S, PostgresAccountLocks
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.db.schema_version import SchemaVersion, announce, schema_version
from sro.infrastructure.db.session import create_engine, create_session_factory
from sro.infrastructure.gemini.asker import GeminiAsker
from sro.infrastructure.gemini.computer_use import GeminiVisionDriver
from sro.infrastructure.gemini.intent import GeminiIntentParser
from sro.infrastructure.gemini.interpreter import GeminiInterpreter
from sro.infrastructure.gemini.metered import Meter, metered_client
from sro.infrastructure.gemini.null_intent import NoIntentParser
from sro.infrastructure.gemini.null_interpreter import NoInterpreter
from sro.infrastructure.http.api_runs import ApiRunDispatcher
from sro.infrastructure.http.httpx_caller import HttpxCaller
from sro.infrastructure.knowledge.embedding import GeminiEmbedder, NoEmbedder
from sro.infrastructure.knowledge.write_endpoints import load_verified_writes
from sro.infrastructure.mcp.client import McpServer, McpToolCaller
from sro.infrastructure.mcp.server import SkillToolServer
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.driver import SteelDriver
from sro.infrastructure.steel.pool import SteelPool
from sro.infrastructure.steel.sign_in import PlaywrightSignIn
from sro.infrastructure.steel.supervisor import CaptureSupervisor
from sro.infrastructure.steel.ui_driver import PlaywrightUiDriver
from sro.infrastructure.system import SystemClock, UuidFactory
from sro.infrastructure.telemetry.otel import configure_tracing, watch_queries, watch_requests
from sro.infrastructure.temporal.durable import TemporalDurableExecution
from sro.infrastructure.temporal.schedules import TemporalScheduler
from sro.infrastructure.transcription.gemini import GeminiTranscriber
from sro.infrastructure.transcription.null import NullTranscriber
from sro.infrastructure.vault.file_vault import FileCredentialVault
from sro.infrastructure.vault.secret_manager import SecretManagerVault

RUNS_LOCK = 5721966


@dataclass
class Container:
    _schema_announced: bool = field(default=False, init=False, repr=False)

    _mining_asker: Asker | None = field(default=None, init=False, repr=False)

    _mining_asker_from: Asker | None = field(default=None, init=False, repr=False)

    settings: Settings
    clock: Clock
    ids: IdFactory
    blobs: BlobStore
    browser: BrowserProvider
    transcriber: Transcriber
    embedder: Embedder
    vision: VisionDriver | None
    interpreter: WorkflowInterpreter
    asker: Asker | None
    intent_parser: IntentParser
    vault: CredentialVault
    http: HttpCaller
    tools: ToolCaller
    ui: UiDriver
    sign_in_driver: SignInDriver
    locks: AccountLocks
    pool: BrowserPool
    driver: PageDriver
    tokens: TokenSource | None
    credentials: Credentials
    durable: DurableExecution
    scheduler: Scheduler
    dispatcher: RunDispatcher
    session_factory: async_sessionmaker[AsyncSession]
    meter: Meter

    engine: AsyncEngine | None = None

    lock_engine: AsyncEngine | None = None

    agent_sockets: DeviceSockets = field(default_factory=DeviceSockets)

    stops: Stops = field(default_factory=Stops)

    one_time_secrets: OneTimeSecrets = field(default_factory=OneTimeSecrets)

    approvals: Approvals = field(default_factory=Approvals)

    pursuits: Pursuits = field(default_factory=Pursuits)

    capture: CaptureController = field(init=False)

    driving_runs: AsyncConnection | None = None

    def unit_of_work(self) -> UnitOfWork:
        return SqlUnitOfWork(self.session_factory)

    async def claim_the_runs(self) -> bool:
        if self.engine is None:
            return True
        connection = await self.engine.connect()
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        held = (
            await connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": RUNS_LOCK})
        ).scalar()
        if not held:
            await connection.close()
            return False
        self.driving_runs = connection
        return True

    async def sweep_orphaned_runs(self, reason: str) -> int:
        async with self.unit_of_work() as uow:
            return await fail_orphans(uow, reason)

    async def readiness(self) -> dict[str, bool]:
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
                version = await schema_version(session)
        except SQLAlchemyError:
            return {"database": False, "schema": False}
        self._announce_once(version)
        return {"database": True, "schema": version.current}

    def _announce_once(self, version: SchemaVersion) -> None:
        if self._schema_announced:
            return
        self._schema_announced = True
        announce(version)

    def read_summary(self) -> ReadSummary:
        return ReadSummary(self.unit_of_work())

    def read_roster(self) -> ReadRoster:
        return ReadRoster(self.unit_of_work(), self.agents())

    def revoke_device(self) -> RevokeDevice:
        return RevokeDevice(self.unit_of_work(), self.agents(), self.clock)

    def restore_device(self) -> RestoreDevice:
        return RestoreDevice(self.unit_of_work())

    def read_audit(self) -> ReadAudit:
        return ReadAudit(self.unit_of_work())

    def serve_shapes(self) -> ServeShapes:
        return ServeShapes(self.unit_of_work(), self.clock)

    def read_workflows(self) -> ReadWorkflows:
        return ReadWorkflows(self.unit_of_work())

    def retire_workflow(self) -> RetireWorkflow:
        return RetireWorkflow(self.unit_of_work(), self.clock)

    def read_evidence(self) -> ReadEvidence:
        return ReadEvidence(self.unit_of_work())

    def read_shots(self) -> ReadShots:
        return ReadShots(self.unit_of_work(), self.blobs)

    async def read_spend(self, ctx: RequestContext) -> DaySpend:
        async with self.unit_of_work() as uow:
            return await spent_today(uow, ctx.tenant_id, now=self.clock.now())

    def record_offer(self) -> RecordOffer:
        return RecordOffer(self.unit_of_work(), self.clock)

    def _patient_asker(self) -> Asker | None:
        if self._mining_asker is None or self._mining_asker_from is not self.asker:
            self._mining_asker_from = self.asker
            self._mining_asker = _patient_asker_for(self.settings, self.asker, self.meter)
        return self._mining_asker

    def mine_pass(self) -> MinePass:
        return MinePass(
            self.unit_of_work(),
            asker=self._patient_asker(),
            model=self.settings.gemini_mine_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
            ours=frozenset(host_port for host_port, _ in self.settings.our_own_origins()),
        )

    def mine_lately(self) -> MineLately:
        return MineLately(
            self.unit_of_work(),
            self.mine_pass(),
            self.read_gestures(),
            window_hours=self.settings.mining_window_hours,
        )

    def read_gestures(self) -> ReadGestures:
        return ReadGestures(
            self.unit_of_work(),
            asker=self.asker,
            model=self.settings.gemini_read_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
            blobs=self.blobs,
            tail_size=self.settings.gemini_read_tail,
            at_once=self.settings.gemini_read_at_once,
        )

    def read_chat(self) -> ReadChat:
        return ReadChat(
            self.unit_of_work(),
            asker=self.asker,
            model=self.settings.gemini_plan_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
        )

    def plan_lookups(self) -> PlanLookups:
        return PlanLookups(
            self.unit_of_work(),
            self.retrieve_knowledge(),
            self.asker,
            model=self.settings.gemini_plan_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
        )

    def run_lookups(self) -> RunLookups:
        return RunLookups(self.unit_of_work(), SocketChannel(self.agent_sockets))

    def create_trigger(self) -> CreateTrigger:
        return CreateTrigger(
            self.unit_of_work(),
            self.clock,
            self.ids,
            self.scheduler,
            can_gather=self.can_gather,
        )

    def read_triggers(self) -> ReadTriggers:
        return ReadTriggers(self.unit_of_work())

    def set_trigger_enabled(self) -> SetTriggerEnabled:
        return SetTriggerEnabled(self.unit_of_work(), self.scheduler)

    def delete_trigger(self) -> DeleteTrigger:
        return DeleteTrigger(self.unit_of_work(), self.scheduler)

    def record_attempt(self) -> RecordAttempt:
        return RecordAttempt(self.unit_of_work(), self.ids, self.clock)

    def fire_trigger(self) -> FireTrigger:
        return FireTrigger(
            self.unit_of_work(),
            self.clock,
            self.durable,
            ids=self.ids,
            dispatcher=self.dispatcher,
            scheduler=self.scheduler,
            start_run=self.start_workflow_run(),
            pursuits=self.pursuits,
        )

    def answer_confirmation(self) -> AnswerConfirmation:
        return AnswerConfirmation(
            self.unit_of_work(),
            self.clock,
            self.ids,
            self.durable,
            self.dispatcher,
            start_run=self.start_workflow_run(),
            pursuits=self.pursuits,
        )

    def read_confirmations(self) -> ReadConfirmations:
        return ReadConfirmations(self.unit_of_work())

    def expire_confirmations(self) -> ExpireConfirmations:
        return ExpireConfirmations(self.unit_of_work(), self.clock)

    def receive_inbound(self) -> ReceiveInbound:
        return ReceiveInbound(self.unit_of_work(), self.fire_trigger())

    def agents(self) -> AgentDrivers:
        return RemoteAgents(self.agent_sockets)

    def browsers(self) -> Browsers:
        return Browsers(self.browser, self.unit_of_work(), self.clock, self.ids)

    def start_recording(self) -> StartRecording:
        return StartRecording(
            self.unit_of_work(),
            self.browser,
            self.clock,
            self.ids,
            self.browsers(),
            self.settings.attach_hosts,
        )

    def ingest_capture_events(self) -> IngestCaptureEvents:
        return IngestCaptureEvents(self.unit_of_work())

    def register_device(self) -> RegisterDevice:
        return RegisterDevice(self.unit_of_work(), self.clock, self.ids)

    def record_heartbeat(self) -> RecordHeartbeat:
        return RecordHeartbeat(self.unit_of_work(), self.clock)

    def read_device(self) -> ReadDevice:
        return ReadDevice(self.unit_of_work())

    def read_observation_policy(self) -> ReadObservationPolicy:
        return ReadObservationPolicy(self.unit_of_work())

    def set_observation_policy(self) -> SetObservationPolicy:
        return SetObservationPolicy(self.unit_of_work())

    def ingest_observation(self) -> IngestObservation:
        return IngestObservation(self.unit_of_work(), self.blobs, self.clock)

    def store_observation_artifact(self) -> StoreObservationArtifact:
        return StoreObservationArtifact(self.unit_of_work(), self.blobs, self.clock)

    def forget_observations(self) -> ForgetObservations:
        return ForgetObservations(self.unit_of_work(), self.blobs, self.clock)

    def sweep_retention(self) -> SweepRetention:
        return SweepRetention(self.unit_of_work(), self.blobs, self.clock)

    def attach_artifact(self) -> AttachArtifact:
        return AttachArtifact(self.unit_of_work(), self.blobs, self.clock, self.transcriber)

    def connect_system(self) -> ConnectSystem:
        return ConnectSystem(self.unit_of_work(), self.browser, self.clock, self.ids)

    def store_session(self) -> StoreSession:
        return StoreSession(
            self.unit_of_work(), self.vault, self.clock, self.browser, self.browsers()
        )

    def store_credentials(self) -> StoreCredentials:
        return StoreCredentials(self.unit_of_work(), self.vault)

    def establish_token(self) -> EstablishToken:
        return EstablishToken(self.unit_of_work(), self.tokens)

    def list_connections(self) -> ListConnections:
        return ListConnections(self.unit_of_work())

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
            self.browsers(),
        )

    def refresh_session(self) -> RefreshSession:
        return RefreshSession(self.unit_of_work(), self.vault, self.clock)

    def store_session_headers(self) -> StoreSessionHeaders:
        return StoreSessionHeaders(self.unit_of_work(), self.vault)

    def load_session(self) -> LoadSession:
        return LoadSession(self.unit_of_work(), self.vault)

    def list_skills(self) -> ListSkills:
        return ListSkills(self.unit_of_work())

    def get_skill(self) -> GetSkill:
        return GetSkill(self.unit_of_work())

    def grant_host(self) -> GrantHost:
        return GrantHost(self.unit_of_work(), self.clock)

    def revoke_host(self) -> RevokeHost:
        return RevokeHost(self.unit_of_work())

    def finish_recording(self) -> FinishRecording:
        return FinishRecording(self.unit_of_work(), self.browser, self.clock)

    def understand_recording(self) -> UnderstandRecording:
        return UnderstandRecording(self.unit_of_work(), self.interpreter, self.clock, self.ids)

    def describe_skill(self) -> DescribeSkill:
        return DescribeSkill(self.unit_of_work())

    def learn_from_run(self) -> LearnFromRun:
        return LearnFromRun(self.record_claims())

    def repair_drift(self) -> RepairDrift:
        return RepairDrift(self.unit_of_work(), self.clock, self.ask_about())

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
            self.agents(),
            self.repair_drift(),
            self.stops,
            self.tools,
        )

    def start_run(self) -> StartRun:
        return StartRun(self.unit_of_work(), self.clock, self.ids)

    def run_from_preview(self) -> RunFromPreview:
        return RunFromPreview(self.unit_of_work(), self.clock, self.execute_skill())

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
            self.browsers(),
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
            self.browsers(),
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
            self.agents(),
            self.tools,
            self.clock,
        )

    def finish_run(self) -> FinishRun:
        return FinishRun(
            self.unit_of_work(), self.clock, self.learn_from_run(), self.repair_drift()
        )

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
            self.read_chat(),
            can_gather=self.can_gather,
            plan_lookups=self.plan_lookups(),
            run_lookups=self.run_lookups(),
            answers=IsItAnAnswer(self.asker, model=self.settings.gemini_plan_model),
        )

    def ask_about_the_offer(self) -> AskAboutTheOffer:
        return AskAboutTheOffer(self.unit_of_work(), self.clock, self.ids, self._drafting_for)

    def draft_for_the_asker(self) -> DraftForTheAsker:
        return DraftForTheAsker(self.unit_of_work(), self.tools, self.clock, self.ids)

    def send_the_draft(self) -> SendTheDraft:
        return SendTheDraft(self.unit_of_work(), self.tools, self.clock, self.ids)

    def say_the_run_started(self) -> SayTheRunStarted:
        return SayTheRunStarted(self.unit_of_work(), self.clock, self.ids)

    def from_the_mail(self) -> FromTheMail:
        return FromTheMail(
            self.unit_of_work(),
            self.tools,
            self.asker,
            model=self.settings.gemini_plan_model,
            clock=self.clock,
            ids=self.ids,
            cap_usd=self.settings.daily_usd_cap,
            gather=GatherContext(
                tools=self.tools, asker=self.asker, model=self.settings.gemini_plan_model
            )
            if self.asker is not None
            else None,
        )

    @property
    def can_gather(self) -> bool:
        return self.tools.available and self.asker is not None

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

    def stop_run(self) -> StopRun:
        return StopRun(self.unit_of_work(), self.stops)

    def start_workflow_run(self) -> StartWorkflowRun:
        return StartWorkflowRun(
            self.unit_of_work(),
            channel=SocketChannel(self.agent_sockets),
            asker=self.asker,
            plan_model=self.settings.gemini_plan_model,
            rescue_model=self.settings.gemini_rescue_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
            stops=self.stops,
            approvals=self.approvals,
            one_time_secrets=self.one_time_secrets,
            verified_writes=load_verified_writes(),
            vault=self.vault,
            retrieve=self.retrieve_knowledge(),
            gather=GatherContext(
                tools=self.tools, asker=self.asker, model=self.settings.gemini_plan_model
            )
            if self.asker is not None
            else None,
            ids=self.ids,
            asker_drafts=self._drafting,
        )

    async def _drafting(self, ctx: RequestContext, run_id: str, pending: Pending) -> bool:
        return await self.draft_for_the_asker().execute(ctx, pending, run_id=run_id)

    async def _drafting_for(self, ctx: RequestContext, pending: Pending, thread: str) -> bool:
        return await self.draft_for_the_asker().execute(ctx, pending, thread=thread)

    def list_workflow_runs(self) -> ListWorkflowRuns:
        return ListWorkflowRuns(self.unit_of_work())

    def get_workflow_run(self) -> GetWorkflowRun:
        return GetWorkflowRun(self.unit_of_work())

    def abort_workflow_run(self) -> AbortWorkflowRun:
        return AbortWorkflowRun(self.unit_of_work(), self.stops, self.approvals)

    def approve_workflow_step(self) -> ApproveWorkflowStep:
        return ApproveWorkflowStep(self.unit_of_work(), self.approvals, self.clock)

    def call_run_wrong(self) -> CallRunWrong:
        return CallRunWrong(self.unit_of_work(), self.clock)

    def mcp_server(self) -> SkillToolServer:
        return SkillToolServer(
            credentials=self.credentials,
            list_skills=self.list_skills,
            get_skill=self.get_skill,
            durable=self.durable,
            get_run=self.get_run,
        )

    def list_runs(self) -> ListRuns:
        return ListRuns(self.unit_of_work())


def _build_transcriber(settings: Settings, meter: Meter) -> Transcriber:
    if settings.transcription_enabled and settings.gemini_api_key:
        return GeminiTranscriber(
            settings.gemini_transcription_model,
            client=metered_client(settings.gemini_api_key, meter),
        )
    return NullTranscriber()


def _build_intent_parser(settings: Settings, meter: Meter) -> IntentParser:
    if settings.interpretation_enabled and settings.gemini_api_key:
        return GeminiIntentParser(
            settings.gemini_intent_model,
            client=metered_client(settings.gemini_api_key, meter),
        )
    return NoIntentParser()


def _build_interpreter(settings: Settings, meter: Meter) -> WorkflowInterpreter:
    if settings.interpretation_enabled and settings.gemini_api_key:
        return GeminiInterpreter(
            settings.gemini_interpreter_model,
            client=metered_client(settings.gemini_api_key, meter),
        )
    return NoInterpreter()


def _patient_asker_for(settings: Settings, asker: Asker | None, meter: Meter) -> Asker | None:
    if not isinstance(asker, GeminiAsker):
        return asker
    return _gemini_asker(settings, meter, timeout_ms=settings.gemini_mine_timeout_ms)


def _gemini_asker(settings: Settings, meter: Meter, *, timeout_ms: int) -> GeminiAsker:
    return GeminiAsker(client=metered_client(settings.gemini_api_key, meter, timeout_ms=timeout_ms))


def _build_asker(settings: Settings, meter: Meter) -> Asker | None:
    if settings.interpretation_enabled and settings.gemini_api_key:
        return _gemini_asker(settings, meter, timeout_ms=settings.gemini_timeout_ms)
    return None


def _build_vision(settings: Settings, meter: Meter) -> VisionDriver | None:
    if settings.vision_enabled and settings.gemini_api_key:
        return GeminiVisionDriver(
            settings.gemini_vision_model,
            client=metered_client(settings.gemini_api_key, meter),
        )
    return None


def _build_embedder(settings: Settings, meter: Meter) -> Embedder:
    if settings.knowledge_embeddings_enabled and settings.gemini_api_key:
        return GeminiEmbedder(
            settings.gemini_embedding_model,
            client=metered_client(settings.gemini_api_key, meter),
        )
    return NoEmbedder()


def _build_pool(settings: Settings) -> SteelPool:
    pairs = {pair for urls in settings.steel_urls.values() for pair in urls}
    pairs.add((settings.steel_base_url, settings.steel_cdp_url))
    clients = {
        api: SteelClient(
            api,
            cdp,
            capacity=settings.steel_sessions_per_container,
            public_base_url=settings.steel_public_base_url,
            session_timeout_seconds=settings.steel_session_timeout_seconds,
            dimensions=(settings.browser_width, settings.browser_height),
        )
        for api, cdp in pairs
    }
    containers_by_tenant = {
        tenant: tuple(api for api, _ in urls) for tenant, urls in settings.steel_urls.items()
    }
    return SteelPool(
        clients,
        containers_by_tenant=containers_by_tenant,
        fallback=(settings.steel_base_url,),
        per_container=settings.steel_sessions_per_container,
    )


def _build_vault(settings: Settings) -> CredentialVault:
    try:
        if settings.vault_project:
            return SecretManagerVault(project=settings.vault_project)
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


def instrument(app: Any) -> None:
    watch_requests(app)


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    configure_tracing(
        service_name=settings.service_name,
        endpoint=settings.otlp_endpoint,
        environment=settings.environment,
    )

    engine = create_engine(settings.database_url, echo=settings.debug)
    if settings.otlp_endpoint:
        watch_queries(engine)
    credentials = SignedTokens(settings.auth_secret)
    sessions = create_session_factory(engine)
    clock = SystemClock()
    meter = Meter(lambda: SqlUnitOfWork(sessions), clock=clock, cap_usd=settings.daily_usd_cap)
    lock_engine = create_engine(
        settings.database_url,
        poolclass=NullPool,
        connect_args={"timeout": K_LOCK_CONNECT_TIMEOUT_S},
    )

    container = Container(
        settings=settings,
        clock=clock,
        ids=UuidFactory(),
        blobs=MinioBlobStore(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            public_endpoint_url=settings.s3_public_endpoint_url,
        ),
        browser=SteelClient(
            settings.steel_base_url,
            settings.steel_cdp_url,
            public_base_url=settings.steel_public_base_url,
            session_timeout_seconds=settings.steel_session_timeout_seconds,
            dimensions=(settings.browser_width, settings.browser_height),
        ),
        transcriber=_build_transcriber(settings, meter),
        embedder=_build_embedder(settings, meter),
        vision=_build_vision(settings, meter),
        interpreter=_build_interpreter(settings, meter),
        asker=_build_asker(settings, meter),
        intent_parser=_build_intent_parser(settings, meter),
        vault=(built_vault := ForgetsRefusalOnWrite(_build_vault(settings))),
        http=HttpxCaller(),
        tools=McpToolCaller(_servers(settings.mcp_servers), vault=built_vault),
        ui=PlaywrightUiDriver(settings.ui_debugger_url),
        sign_in_driver=PlaywrightSignIn(),
        locks=PostgresAccountLocks(lock_engine),
        pool=_build_pool(settings),
        driver=SteelDriver(settings.page_code_path),
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
        credentials=credentials,
        scheduler=TemporalScheduler(
            address=settings.temporal_address, namespace=settings.temporal_namespace
        ),
        dispatcher=ApiRunDispatcher(settings.api_url, credentials),
        durable=TemporalDurableExecution(
            address=settings.temporal_address, namespace=settings.temporal_namespace
        ),
        session_factory=sessions,
        engine=engine,
        lock_engine=lock_engine,
        meter=meter,
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


def _servers(configured: str) -> tuple[McpServer, ...]:
    found: list[McpServer] = []
    for entry in configured.split(","):
        name, sep, rest = entry.strip().partition("=")
        if not sep or not name.strip() or not rest.strip():
            continue
        url, _, _dropped = rest.partition("#")
        if url.strip():
            found.append(McpServer(name=name.strip(), url=url.strip()))
    return tuple(found)
