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

from sro.application.connection.connect_system import ConnectSystem, LoadSession, StoreSession
from sro.application.connection.session_headers import StoreSessionHeaders
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecuteStep,
    FinishRun,
    StartRun,
)
from sro.application.execution.read_runs import GetRun, ListRuns
from sro.application.induction.induce_skill import InduceSkill
from sro.application.ports.blob import BlobStore
from sro.application.ports.browser import BrowserProvider
from sro.application.ports.capture import CaptureController
from sro.application.ports.durable import DurableExecution
from sro.application.ports.http import HttpCaller
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.application.ports.transcription import Transcriber
from sro.application.ports.vault import CredentialVault, VaultUnavailable
from sro.application.recording.attach_artifact import AttachArtifact
from sro.application.recording.finish_recording import FinishRecording
from sro.application.recording.get_recording import GetRecording
from sro.application.recording.ingest_capture_events import IngestCaptureEvents
from sro.application.recording.list_recordings import ListRecordings
from sro.application.recording.live_view import GetLiveView
from sro.application.recording.media import GetRecordingMedia
from sro.application.recording.start_recording import StartRecording
from sro.application.skill.promote_skill import PromoteSkill
from sro.application.skill.read_skills import GetSkill, ListSkills
from sro.config import Settings, get_settings
from sro.infrastructure.blob.minio_store import MinioBlobStore
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.db.session import create_engine, create_session_factory
from sro.infrastructure.http.httpx_caller import HttpxCaller
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.supervisor import CaptureSupervisor
from sro.infrastructure.system import SystemClock, UuidFactory
from sro.infrastructure.telemetry.otel import configure_tracing
from sro.infrastructure.temporal.durable import TemporalDurableExecution
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
    vault: CredentialVault
    http: HttpCaller
    durable: DurableExecution
    session_factory: async_sessionmaker[AsyncSession]

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
        return InduceSkill(self.unit_of_work(), self.clock, self.ids)

    def promote_skill(self) -> PromoteSkill:
        return PromoteSkill(self.unit_of_work(), self.clock)

    def execute_skill(self) -> ExecuteSkill:
        return ExecuteSkill(self.unit_of_work(), self.http, self.vault, self.clock, self.ids)

    def start_run(self) -> StartRun:
        return StartRun(self.unit_of_work(), self.clock, self.ids)

    def execute_step(self) -> ExecuteStep:
        return ExecuteStep(self.unit_of_work(), self.http, self.vault)

    def finish_run(self) -> FinishRun:
        return FinishRun(self.unit_of_work(), self.clock)

    def get_run(self) -> GetRun:
        return GetRun(self.unit_of_work())

    def list_runs(self) -> ListRuns:
        return ListRuns(self.unit_of_work())


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
        ),
        transcriber=NullTranscriber(),
        vault=_build_vault(settings),
        http=HttpxCaller(),
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
