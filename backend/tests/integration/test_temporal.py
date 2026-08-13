"""Durable execution against a real Temporal, with a real worker in-process.

The workflows were provably correct in isolation long before anything called
them. What these prove is the wiring: that the API's path reaches a worker, and
that a demonstration nobody comes back to ends by itself.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client
from temporalio.worker import Worker

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.ports.repositories import UnitOfWork
from sro.config import Settings
from sro.container import Container
from sro.domain.recording.recording import RecordingStatus
from sro.domain.shared.identifiers import BrowserSessionId, RecordingId
from sro.infrastructure.blob.minio_store import MinioBlobStore
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.system import SystemClock, UuidFactory
from sro.infrastructure.temporal.activities import Activities
from sro.infrastructure.temporal.durable import TemporalDurableExecution
from sro.infrastructure.temporal.workflows import InductionWorkflow, RecordingSessionWorkflow
from sro.infrastructure.transcription.null import NullTranscriber
from tests import factories as f
from tests.unit.fakes import FakeBrowserProvider

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
ADDRESS = "localhost:7233"

# Own queues per run: a developer's `make worker` is pointed at the development
# database and would otherwise pick up this suite's work and fail to find it.
RUN = uuid.uuid4().hex[:8]
TEST_DEFAULT_QUEUE = f"test-default-{RUN}"
TEST_BROWSER_QUEUE = f"test-browser-{RUN}"


@pytest.fixture
async def temporal_client() -> AsyncIterator[Client]:
    try:
        client = await asyncio.wait_for(Client.connect(ADDRESS), timeout=5)
    except Exception as exc:
        pytest.skip(f"Temporal is not running: {exc}")
    yield client


@pytest.fixture
def container(session_factory: async_sessionmaker[AsyncSession]) -> Container:
    """Production wiring with fakes only where the world is unavailable."""
    settings = Settings(otlp_endpoint=None)
    built = Container(
        settings=settings,
        clock=SystemClock(),
        ids=UuidFactory(),
        blobs=MinioBlobStore(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket=settings.s3_bucket,
        ),
        browser=FakeBrowserProvider(),
        transcriber=NullTranscriber(),
        durable=TemporalDurableExecution(
            address=ADDRESS,
            default_queue=TEST_DEFAULT_QUEUE,
            browser_queue=TEST_BROWSER_QUEUE,
        ),
        session_factory=session_factory,
    )
    return built


@pytest.fixture
async def worker(temporal_client: Client, container: Container) -> AsyncIterator[None]:
    activities = Activities(container)
    default = Worker(
        temporal_client,
        task_queue=TEST_DEFAULT_QUEUE,
        workflows=[InductionWorkflow],
        activities=[activities.induce_skill],
    )
    browser = Worker(
        temporal_client,
        task_queue=TEST_BROWSER_QUEUE,
        workflows=[RecordingSessionWorkflow],
        activities=[activities.abandon_stale_recording, activities.close_browser_session],
    )
    async with default, browser:
        yield


async def _seal_two_runs(uow: UnitOfWork) -> tuple[str, str]:
    runs = []
    for index, value in enumerate(("W-1001", "W-2002")):
        recording = f.recording(frames=0, id=RecordingId(f"rec-temporal-{index}"))
        recording.append_frame(
            f.frame(requests=(f.request(url=f"https://wms.test/api/waves/{value}/release"),))
        )
        recording.seal(f.at(300))
        async with uow as unit:
            await unit.recordings.add(recording)
            await unit.commit()
        runs.append(recording.id.value)
    return runs[0], runs[1]


class TestInduction:
    async def test_induction_runs_through_the_workflow(
        self, worker: None, container: Container, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        first, second = await _seal_two_runs(SqlUnitOfWork(session_factory))

        induced = await container.durable.induce_skill(
            CTX,
            first=RecordingId(first),
            second=RecordingId(second),
        )

        assert induced.version == 1
        assert induced.step_count == 1
        # The wave id varies between the runs, so it must be a parameter.
        assert induced.input_parameter_count == 1

        async with SqlUnitOfWork(session_factory) as unit:
            stored = await unit.skills.get(f.TENANT, induced.skill_id)
        assert stored.latest.version == 1

    async def test_a_bad_pair_fails_the_caller_rather_than_retrying_forever(
        self, worker: None, container: Container, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        first, _ = await _seal_two_runs(SqlUnitOfWork(session_factory))

        with pytest.raises(InductionFailed) as failure:
            await container.durable.induce_skill(
                CTX, first=RecordingId(first), second=RecordingId(first)
            )

        # The supervisor has to read this. "Activity task failed" is not a reason.
        assert "two different recordings" in str(failure.value)


class TestSessionDeadline:
    async def test_a_demonstration_nobody_finishes_is_reaped(
        self, worker: None, container: Container, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        recording = f.recording(frames=1, id=RecordingId("rec-abandoned"))
        recording.attach_browser_session(BrowserSessionId("sess-gone"))
        async with SqlUnitOfWork(session_factory) as unit:
            await unit.recordings.add(recording)
            await unit.commit()

        started = await container.durable.watch_recording(
            CTX,
            recording_id=recording.id,
            browser_session_id=BrowserSessionId("sess-gone"),
            timeout_seconds=0,  # the deadline is already past
        )
        assert started

        handle = (await Client.connect(ADDRESS)).get_workflow_handle(f"recording-{recording.id}")
        assert await handle.result() is True

        async with SqlUnitOfWork(session_factory) as unit:
            stored = await unit.recordings.get(f.TENANT, recording.id)
        assert stored.status is RecordingStatus.ABANDONED
        assert stored.abandon_reason == "session timed out without being finished"

    async def test_finishing_cancels_the_deadline(
        self, worker: None, container: Container, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        recording = f.recording(frames=1, id=RecordingId("rec-finished"))
        recording.attach_browser_session(BrowserSessionId("sess-live"))
        async with SqlUnitOfWork(session_factory) as unit:
            await unit.recordings.add(recording)
            await unit.commit()

        await container.durable.watch_recording(
            CTX,
            recording_id=recording.id,
            browser_session_id=BrowserSessionId("sess-live"),
            timeout_seconds=300,
        )
        await container.durable.recording_finished(CTX, recording_id=recording.id)

        handle = (await Client.connect(ADDRESS)).get_workflow_handle(f"recording-{recording.id}")
        # False: the deadline ended because the demonstration ended, not because
        # anything was reaped.
        assert await asyncio.wait_for(handle.result(), timeout=20) is False

        async with SqlUnitOfWork(session_factory) as unit:
            stored = await unit.recordings.get(f.TENANT, recording.id)
        assert stored.status is RecordingStatus.CAPTURING

    async def test_signalling_a_deadline_that_never_existed_is_silent(
        self, temporal_client: Client, container: Container
    ) -> None:
        # Temporal was down when the recording started, so no deadline exists.
        # Finishing must not fail because of it.
        await container.durable.recording_finished(
            CTX, recording_id=RecordingId("rec-never-watched")
        )
