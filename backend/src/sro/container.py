"""Composition root. The only module allowed to import ``sro.infrastructure``.

Everything above this line depends on protocols; the choice of Postgres, MinIO
or Steel is made here and nowhere else. Swapping an adapter is an edit to this
file, which is the whole point of the dependency rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.analytics.audit import ReadAudit
from sro.application.analytics.summary import ReadSummary
from sro.application.capture.devices import ReadRoster, RestoreDevice, RevokeDevice
from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.read_chat import ReadChat
from sro.application.chat.read_threads import ReadThreads
from sro.application.connection.browsers import Browsers
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
from sro.application.execution.pursue_goal import PursueGoal
from sro.application.execution.pursuits import Pursuits
from sro.application.execution.read_runs import GetRun, ListRuns, StopRun
from sro.application.execution.revise_run import ReviseRun
from sro.application.execution.run_from_preview import RunFromPreview
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
from sro.application.induction.induce_skill import InduceSkill
from sro.application.induction.seed_from_flow import SeedSkillFromFlow
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
from sro.application.observation.artifacts import StoreObservationArtifact
from sro.application.observation.demonstrate import AssembleDemonstration
from sro.application.observation.forget import ForgetObservations
from sro.application.observation.ingest import IngestObservation
from sro.application.observation.learn import LearnWhatRepeats
from sro.application.observation.mine import MineEverything, MineObservations
from sro.application.observation.mine_pass import MinePass
from sro.application.observation.policy import ReadObservationPolicy, SetObservationPolicy
from sro.application.observation.propose import AnswerJoin, ProposeAboutCandidates
from sro.application.observation.read_pool import ReadPool
from sro.application.observation.read_shots import ReadShots
from sro.application.observation.register import (
    GrantHost,
    ReadDevice,
    RecordHeartbeat,
    RegisterDevice,
    RevokeHost,
)
from sro.application.observation.retain import SweepRetention
from sro.application.observation.teach import (
    DismissCandidate,
    ReadCandidates,
    TeachCandidate,
    TeachWorkflow,
)
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
from sro.application.ports.model import Asker
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
from sro.application.recording.get_recording import GetRecording
from sro.application.recording.ingest_capture_events import IngestCaptureEvents
from sro.application.recording.list_recordings import ListRecordings
from sro.application.recording.live_view import GetLiveView
from sro.application.recording.media import GetRecordingMedia
from sro.application.recording.start_recording import StartRecording
from sro.application.skill.add_assertion import AddAssertion
from sro.application.skill.adopt_rig_workflow import AdoptRigWorkflow
from sro.application.skill.describe_skill import DescribeSkill
from sro.application.skill.map_step_to_tool import MapStepToTool
from sro.application.skill.promote_skill import PromoteSkill
from sro.application.skill.read_doings import ReadDoings
from sro.application.skill.read_skills import GetSkill, ListSkills
from sro.application.skill.read_workflows import ReadEvidence, ReadWorkflows
from sro.application.skill.record_offer import RecordOffer
from sro.application.skill.repair_drift import RepairDrift
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
from sro.domain.shared.prices import DaySpend
from sro.infrastructure.agent.channel import SocketChannel
from sro.infrastructure.agent.drivers import RemoteAgents
from sro.infrastructure.agent.sockets import DeviceSockets
from sro.infrastructure.auth.keycloak import KeycloakTokens
from sro.infrastructure.auth.signed_tokens import SignedTokens
from sro.infrastructure.blob.minio_store import MinioBlobStore
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.db.schema_version import SchemaVersion, announce, schema_version
from sro.infrastructure.db.session import create_engine, create_session_factory
from sro.infrastructure.gemini.asker import GeminiAsker
from sro.infrastructure.gemini.computer_use import GeminiVisionDriver
from sro.infrastructure.gemini.intent import GeminiIntentParser
from sro.infrastructure.gemini.interpreter import GeminiInterpreter
from sro.infrastructure.gemini.null_intent import NoIntentParser
from sro.infrastructure.gemini.null_interpreter import NoInterpreter
from sro.infrastructure.http.api_runs import ApiRunDispatcher
from sro.infrastructure.http.httpx_caller import HttpxCaller
from sro.infrastructure.knowledge.embedding import GeminiEmbedder, NoEmbedder
from sro.infrastructure.knowledge.write_endpoints import load_verified_writes
from sro.infrastructure.mcp.client import McpServer, McpToolCaller
from sro.infrastructure.mcp.server import SkillToolServer
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.sign_in import PlaywrightSignIn
from sro.infrastructure.steel.supervisor import CaptureSupervisor
from sro.infrastructure.steel.ui_driver import PlaywrightUiDriver
from sro.infrastructure.system import SystemClock, UuidFactory
from sro.infrastructure.telemetry.otel import configure_tracing
from sro.infrastructure.temporal.durable import TemporalDurableExecution
from sro.infrastructure.temporal.schedules import TemporalScheduler
from sro.infrastructure.transcription.gemini import GeminiTranscriber
from sro.infrastructure.transcription.null import NullTranscriber
from sro.infrastructure.vault.file_vault import FileCredentialVault


@dataclass
class Container:
    """Long-lived adapters, built once per process.

    Use cases are cheap objects built per call: they hold a unit of work, which
    must not be shared between concurrent requests.
    """

    _schema_announced: bool = field(default=False, init=False, repr=False)
    """Whether the schema line has been written this process. See
    `_announce_once`: the fact is worth saying, and worth saying once."""

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
    """The model the rig's own passes ask, or ``None`` where none is configured.

    Separate from ``interpreter`` and ``intent_parser``, which each answer one
    narrow question with their own model name. This is the general one: the
    miner and the runner hand it a schema and an instruction and read structured
    JSON back, and both need to bill what they spent, which is why the port
    carries ``Answer`` rather than a string.

    ``None`` rather than a no-op double, deliberately. A miner with nothing to
    ask must not run and quietly find nothing -- that reads exactly like a day
    with no work in it. The caller that checks and refuses now exists: it is
    `asker_or_refuse` in `application/ports/model.py`, and every door that needs
    a model reaches it through that one function.

    Which doors those are is NOT written down here any more. This paragraph
    used to name them and count them, with a note saying the count went up
    "when task 5 lands and not before" -- and task 5 landed, and the sentence
    stayed at two for a week, on the same attribute that carried a "nothing
    reads this" defect the week before. It wrote its own trip-wire and nobody
    tripped it, which is what a prose trip-wire is worth. The count now lives
    in `test_every_door_that_needs_a_model_refuses_through_the_one_guard`,
    which fails on the commit that adds or removes a caller instead of on the
    commit that reads the comment.

    The check is deliberately not on this attribute and not a method here. Each
    caller takes `Asker | None` and refuses at the top of its own `execute`, so
    a deployment with no model still builds every factory and fails at use
    rather than at construction.
    """
    intent_parser: IntentParser
    vault: CredentialVault
    http: HttpCaller
    tools: ToolCaller
    ui: UiDriver
    sign_in_driver: SignInDriver
    tokens: TokenSource | None
    credentials: Credentials
    durable: DurableExecution
    scheduler: Scheduler
    dispatcher: RunDispatcher
    session_factory: async_sessionmaker[AsyncSession]

    agent_sockets: DeviceSockets = field(default_factory=DeviceSockets)
    """Channels to operators' browsers, open right now, in this process.

    In memory for the same reason as the pursuits below: a socket does not
    survive a restart, so a durable record of which browser was connected would
    only ever be a record of which browser used to be."""

    stops: Stops = field(default_factory=Stops)

    """Runs somebody has asked to stop. In memory beside the pursuits and the
    sockets, and for the same reason: the task that would honour it is in this
    process, so an intention that outlived the process would outlive the only
    thing able to act on it."""

    approvals: Approvals = field(default_factory=Approvals)

    """Runs parked in front of a person, and the event each one waits on. In
    memory for `Stops`' reason and one more of its own: the wait is an
    `asyncio.Event` in the task driving the run, so a tap that landed in another
    process would set an event nothing is waiting on. That is the same
    one-worker assumption the sockets above already make, and
    `application/execution/approvals.py` is where its end is written down."""

    pursuits: Pursuits = field(default_factory=Pursuits)

    """Pursuits this process is driving. In memory on purpose: the browser one
    was driving does not survive a restart either, and a half-finished pursuit
    resumed against a screen nobody can see is worse than one that stopped."""

    capture: CaptureController = field(init=False)
    """Set by ``build_container``: the supervisor is built from the container's
    own use-case factories, so it cannot be a constructor argument."""

    def unit_of_work(self) -> UnitOfWork:
        return SqlUnitOfWork(self.session_factory)

    async def readiness(self) -> dict[str, bool]:
        """Both halves of "can this process serve", on ONE connection.

        Reachable and current are different questions: a database that answers
        `SELECT 1` while four migrations behind is reachable and useless, and
        until this existed the only symptom was a 500 from whichever call
        touched a missing column first.

        One session for both, deliberately. Asked on a probe endpoint, which
        under load is called far more often than anything else here -- two
        sessions per call is how a readiness check becomes the thing that
        exhausts the pool it exists to report on.

        Lives here so the interface layer stays free of SQL, and returns plain
        booleans so it stays free of the infrastructure's types as well.
        """
        try:
            async with self.session_factory() as session:
                await session.execute(text("SELECT 1"))
                version = await schema_version(session)
        except SQLAlchemyError:
            return {"database": False, "schema": False}
        self._announce_once(version)
        return {"database": True, "schema": version.current}

    def _announce_once(self, version: SchemaVersion) -> None:
        """Write the schema line to the log the first time anybody probes.

        Not from the lifespan, where it belongs on the face of it: a check
        there opens a connection before the process serves anything, and every
        app instance would hold one from boot. The contract suite builds many
        apps and exhausted Postgres on the first run of exactly that -- which
        is a fair warning about what it would do to a deployment that starts
        several workers against a small connection limit.

        A probe is where the fact is wanted anyway, it already has the session
        open, and nothing that matters is lost: a deployment probes readiness
        within seconds of starting, and a developer sees the line the first
        time they or their tooling ask.
        """
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
        # No drivers, where `revoke_device` above has them: letting a browser
        # back in opens no socket, and a use case with no `AgentDrivers` cannot
        # grow one by accident.
        return RestoreDevice(self.unit_of_work())

    def read_audit(self) -> ReadAudit:
        return ReadAudit(self.unit_of_work())

    def serve_shapes(self) -> ServeShapes:
        return ServeShapes(self.unit_of_work(), self.clock)

    def read_workflows(self) -> ReadWorkflows:
        return ReadWorkflows(self.unit_of_work())

    def read_evidence(self) -> ReadEvidence:
        return ReadEvidence(self.unit_of_work())

    def read_shots(self) -> ReadShots:
        return ReadShots(self.unit_of_work(), self.blobs)

    def read_pool(self) -> ReadPool:
        return ReadPool(self.unit_of_work())

    async def read_spend(self, ctx: RequestContext) -> DaySpend:
        """What this tenant has been billed since midnight, on this clock.

        A method rather than a factory like the two above, and the reason is
        the plain one: ``spent_today`` is a bare function, so there is no
        class to construct and a factory would be a wrapper for its own sake.
        Not "nothing route-supplied to hold" -- the tenant IS route-supplied,
        it arrives on the ``ctx`` below, and ``ServeShapes`` holds nothing
        route-supplied either. ``record_offer`` next door was a bare function
        too, and became a class anyway, because it took a bare ``tenant_id``.

        That is the line: takes the whole context and never a bare
        ``tenant_id``, so the one seam where passing the wrong tenant is the
        failure stays out of the interface layer -- the same reason
        ``ServeShapes.execute`` takes one, and the reason ``RecordOffer``
        exists as a class at all. ``now`` is supplied here because which day
        is being asked about is a decision no route may make: one that read a
        clock would answer for the server's day.
        """
        # Entered here, not inside ``spent_today``: a unit of work has no
        # repositories until its session opens, and ``over_cap``'s other
        # callers pass one that is already open.
        async with self.unit_of_work() as uow:
            return await spent_today(uow, ctx.tenant_id, now=self.clock.now())

    def record_offer(self) -> RecordOffer:
        """A factory, where ``read_spend`` above is a method, and not because
        this one has more to hold: ``record_offer`` is a bare function like
        ``spent_today``, but it takes a bare ``tenant_id``. A route calling it
        would unpack the caller itself, at the one seam where passing the
        wrong tenant is the failure. ``RecordOffer`` takes the context
        instead, and the clock ``clamped`` needs comes from here so that no
        route reads one."""
        return RecordOffer(self.unit_of_work(), self.clock)

    def adopt_rig_workflow(self) -> AdoptRigWorkflow:
        return AdoptRigWorkflow(self.unit_of_work(), self.clock, self.ids)

    def mine_observations(self) -> MineObservations:
        return MineObservations(self.unit_of_work(), self.blobs, self.ids)

    def mine_pass(self) -> MinePass:
        """The model-first rig's pass, which until now had no caller in `src/`.

        `asker` is handed over as `Asker | None` rather than through
        `asker_or_refuse` here: a factory that raised would make this method
        itself unbuildable, and a deployment with no key would fail at
        construction instead of at the one call that needs a model.

        Not `mine_observations` above. That one clusters a week of observation
        into task candidates with no model in the loop at all; this one packs
        one window, makes one call and writes one `mining_passes` row.
        """
        return MinePass(
            self.unit_of_work(),
            asker=self.asker,
            model=self.settings.gemini_mine_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
            # `work_only` reads a workflow's own systems, which have no path --
            # so only the host:port half of `our_own_origins` applies here.
            ours=frozenset(host_port for host_port, _ in self.settings.our_own_origins()),
        )

    def read_chat(self) -> ReadChat:
        """The chat door's reader, which until now had no caller in `src/`.

        `gemini_plan_model` and NOT `gemini_mine_model` beside it. A chat door
        and a mining door look like they should share a model and must not: an
        operator is standing at a screen waiting for this answer, so it is the
        fast one -- the same trade `gemini_intent_model` records having
        measured at ~2.3s against ~4.8s for the pro model. This is the rig's
        own wiring: `api.py:1507` hands `understand` `settings().plan_model`.

        Not `resolve_intent`. That one resolves an utterance over this tenant's
        *skills* with no model in the loop at all; this one resolves it over
        the *workflows* a mining pass read, and it spends money doing it.

        `asker` is handed over as `Asker | None` rather than through
        `asker_or_refuse` here, for `mine_pass`'s reason: a factory that raised
        would make this method itself unbuildable, and a deployment with no key
        would fail at construction instead of at the one call that needs a
        model.
        """
        return ReadChat(
            self.unit_of_work(),
            asker=self.asker,
            model=self.settings.gemini_plan_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
        )

    def mine_everything(self) -> MineEverything:
        return MineEverything(
            self.unit_of_work(), self.mine_observations(), self.propose_about_candidates()
        )

    def answer_join(self) -> AnswerJoin:
        return AnswerJoin(self.unit_of_work())

    def propose_about_candidates(self) -> ProposeAboutCandidates:
        """The three model slots over what the miner found, and the offer said
        out loud. The model slots do nothing at all when no interpreter is
        configured; the offer is written either way, because which tasks are
        worth offering was never a model's decision."""
        return ProposeAboutCandidates(self.unit_of_work(), self.interpreter, self.clock, self.ids)

    def read_candidates(self) -> ReadCandidates:
        return ReadCandidates(self.unit_of_work())

    def teach_candidate(self) -> TeachCandidate:
        return TeachCandidate(
            self.unit_of_work(),
            self.blobs,
            self.clock,
            self.ids,
            self.understand_recording(),
            self.induce_skill(),
        )

    def learn_what_repeats(self) -> LearnWhatRepeats:
        return LearnWhatRepeats(self.unit_of_work(), self.teach_candidate())

    def teach_workflow(self) -> TeachWorkflow:
        """Two candidates as one skill. The pair diffed is two occurrences of
        the whole job, so this goes through the two-run induction rather than
        the single-demonstration reading a lone candidate gets."""
        return TeachWorkflow(
            self.unit_of_work(),
            self.blobs,
            self.clock,
            self.ids,
            self.induce_skill(),
            self.interpreter,
        )

    def dismiss_candidate(self) -> DismissCandidate:
        return DismissCandidate(self.unit_of_work(), self.clock, self.ids)

    def create_trigger(self) -> CreateTrigger:
        return CreateTrigger(self.unit_of_work(), self.clock, self.ids, self.scheduler)

    def read_triggers(self) -> ReadTriggers:
        return ReadTriggers(self.unit_of_work())

    def set_trigger_enabled(self) -> SetTriggerEnabled:
        return SetTriggerEnabled(self.unit_of_work(), self.scheduler)

    def delete_trigger(self) -> DeleteTrigger:
        return DeleteTrigger(self.unit_of_work(), self.scheduler)

    def fire_trigger(self) -> FireTrigger:
        return FireTrigger(
            self.unit_of_work(),
            self.clock,
            self.durable,
            ids=self.ids,
            dispatcher=self.dispatcher,
            scheduler=self.scheduler,
        )

    def answer_confirmation(self) -> AnswerConfirmation:
        return AnswerConfirmation(
            self.unit_of_work(), self.clock, self.ids, self.durable, self.dispatcher
        )

    def read_confirmations(self) -> ReadConfirmations:
        return ReadConfirmations(self.unit_of_work())

    def expire_confirmations(self) -> ExpireConfirmations:
        return ExpireConfirmations(self.unit_of_work(), self.clock)

    def receive_inbound(self) -> ReceiveInbound:
        return ReceiveInbound(self.unit_of_work(), self.fire_trigger())

    def agents(self) -> AgentDrivers:
        """Drivers that perform in an operator's own browser."""
        return RemoteAgents(self.agent_sockets)

    def browsers(self) -> Browsers:
        """The only way to open, find or release a browser.

        Everything that used to take ``self.browser`` takes this instead, so
        an unowned session cannot be produced by anything this system runs.
        """
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

    # -- observation ---------------------------------------------------------

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

    def assemble_demonstration(self) -> AssembleDemonstration:
        return AssembleDemonstration(self.unit_of_work(), self.blobs)

    def forget_observations(self) -> ForgetObservations:
        return ForgetObservations(self.unit_of_work(), self.blobs, self.clock)

    def sweep_retention(self) -> SweepRetention:
        return SweepRetention(self.unit_of_work(), self.blobs, self.clock)

    def attach_artifact(self) -> AttachArtifact:
        return AttachArtifact(self.unit_of_work(), self.blobs, self.clock, self.transcriber)

    def list_recordings(self) -> ListRecordings:
        return ListRecordings(self.unit_of_work())

    def connect_system(self) -> ConnectSystem:
        return ConnectSystem(self.unit_of_work(), self.browser, self.clock, self.ids)

    def store_session(self) -> StoreSession:
        return StoreSession(
            self.unit_of_work(), self.vault, self.clock, self.browser, self.browsers()
        )

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

    def get_recording(self) -> GetRecording:
        return GetRecording(self.unit_of_work())

    def list_skills(self) -> ListSkills:
        return ListSkills(self.unit_of_work())

    def get_skill(self) -> GetSkill:
        return GetSkill(self.unit_of_work())

    def read_doings(self) -> ReadDoings:
        return ReadDoings(self.unit_of_work())

    def map_step_to_tool(self) -> MapStepToTool:
        return MapStepToTool(self.unit_of_work(), self.clock, self.tools)

    def add_assertion(self) -> AddAssertion:
        return AddAssertion(self.unit_of_work(), self.clock)

    def grant_host(self) -> GrantHost:
        return GrantHost(self.unit_of_work(), self.clock)

    def revoke_host(self) -> RevokeHost:
        return RevokeHost(self.unit_of_work())

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

    def seed_skill_from_flow(self) -> SeedSkillFromFlow:
        return SeedSkillFromFlow(
            self.unit_of_work(), self.clock, self.ids, self.understand_recording()
        )

    def promote_skill(self) -> PromoteSkill:
        return PromoteSkill(self.unit_of_work(), self.clock)

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

    def stop_run(self) -> StopRun:
        return StopRun(self.unit_of_work(), self.stops)

    def start_workflow_run(self) -> StartWorkflowRun:
        """The press on a mined job. Not `start_run` above, which mints the row
        for a skill run keyed on a `RunId`.

        `SocketChannel` over the sockets this worker already holds, rather than
        a second channel: `DeviceSockets` mints the command ids and correlates
        the answers, and a run that opened its own would be talking to a
        browser nobody else could hear. The stop register and the approval
        register are the process-wide ones for the same reason -- the tap and
        the stop button arrive on routes in this process, and a second register
        is a tap nothing is waiting on.

        `gemini_plan_model` plans and `gemini_rescue_model` rescues: a clean
        step never touches the expensive one, and the wiring is the rig's own
        (`api.py:1140`).

        `verified_writes` reads `knowledge-base/index/write-endpoints.json`,
        cached by `load_verified_writes` -- an empty ledger where the
        knowledge base is not checked out beside this deployment, never an
        error.
        """
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
            verified_writes=load_verified_writes(),
        )

    def list_workflow_runs(self) -> ListWorkflowRuns:
        """The runs of mined jobs, newest first. Not `list_runs` above, which
        lists skill runs keyed on a `RunId`."""
        return ListWorkflowRuns(self.unit_of_work())

    def get_workflow_run(self) -> GetWorkflowRun:
        """One run of a mined job. Not `get_run` above, for the same reason."""
        return GetWorkflowRun(self.unit_of_work())

    def abort_workflow_run(self) -> AbortWorkflowRun:
        """The stop button on a run of a mined job. Not `stop_run` above, which
        reaches a skill run through `uow.runs` on a `RunId`.

        Both process-wide registers, and both for the reason `start_workflow_run`
        gives: the task that honours a stop is waiting on the ones this container
        handed it, and a use case built with registers of its own would set a
        flag nothing ever reads and release a wait nobody is holding.
        """
        return AbortWorkflowRun(self.unit_of_work(), self.stops, self.approvals)

    def approve_workflow_step(self) -> ApproveWorkflowStep:
        """The Yes on a run of a mined job, and the other half of the seam
        `abort_workflow_run` above opens.

        The same process-wide `approvals` for the reason `start_workflow_run`
        gives: the task parked on a person is waiting on the register this
        container handed it, and a use case built with one of its own would
        release a wait nobody is holding.

        The clock, because the row says WHEN the write was let out. A route
        never reads one.
        """
        return ApproveWorkflowStep(self.unit_of_work(), self.approvals, self.clock)

    def call_run_wrong(self) -> CallRunWrong:
        return CallRunWrong(self.unit_of_work(), self.clock)

    def revise_run(self) -> ReviseRun:
        return ReviseRun(self.unit_of_work(), self.clock)

    def mcp_server(self) -> SkillToolServer:
        """A tool per runnable skill. One server per process: tenant comes from
        the bearer token on each MCP request, not from how this is built --
        and the use cases are passed as factories, not instances, so each
        request gets its own `UnitOfWork` the same way an HTTP route does."""
        return SkillToolServer(
            credentials=self.credentials,
            list_skills=self.list_skills,
            get_skill=self.get_skill,
            durable=self.durable,
            get_run=self.get_run,
        )

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


def _build_asker(settings: Settings) -> Asker | None:
    """The same two switches as its neighbours: a key is not consent to send.

    ``interpretation_enabled`` is the switch, because what this sends is what
    that switch is about -- a tenant's captured gestures and the bodies of
    their calls, read by a hosted model.
    """
    if settings.interpretation_enabled and settings.gemini_api_key:
        return GeminiAsker(settings.gemini_api_key)
    return None


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
    credentials = SignedTokens(settings.auth_secret)

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
        asker=_build_asker(settings),
        intent_parser=_build_intent_parser(settings),
        vault=(built_vault := _build_vault(settings)),
        http=HttpxCaller(),
        tools=McpToolCaller(_servers(settings.mcp_servers)),
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
        credentials=credentials,
        scheduler=TemporalScheduler(
            address=settings.temporal_address, namespace=settings.temporal_namespace
        ),
        # Mints its own short-lived credential for the trigger's principal, so
        # a scheduled run is asked for by the person who put it on the clock.
        dispatcher=ApiRunDispatcher(settings.api_url, credentials),
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


def _servers(configured: str) -> tuple[McpServer, ...]:
    """`name=url#token, name=url` into connectors.

    A malformed entry is skipped rather than raising: one typo in a
    comma-separated setting must not stop a deployment whose other connectors
    are fine, and a connector that is absent is already an answer this system
    knows how to give.
    """
    found: list[McpServer] = []
    for entry in configured.split(","):
        name, sep, rest = entry.strip().partition("=")
        if not sep or not name.strip() or not rest.strip():
            continue
        url, _, token = rest.partition("#")
        found.append(McpServer(name=name.strip(), url=url.strip(), token=token.strip()))
    return tuple(found)
