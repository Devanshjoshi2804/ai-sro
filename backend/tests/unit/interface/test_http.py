"""HTTP surface against fake adapters.

No database and no browser: what is under test is the wiring, the wire shapes and
the error mapping, all of which break independently of any infrastructure.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.application.context import RequestContext
from sro.application.ports.capture import CaptureController
from sro.application.ports.repositories import UnitOfWork
from sro.config import Settings
from sro.container import Container
from sro.domain.shared.identifiers import BrowserSessionId, RecordingId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import (
    FakeBlobStore,
    FakeBrowserProvider,
    FakeClock,
    FakeDurableExecution,
    FakeIdFactory,
    FakeTranscriber,
    FakeUnitOfWork,
)


class _FakeContainer(Container):
    """A container whose unit of work is the in-memory one.

    Subclassing keeps the use-case factories -- the code under test -- exactly as
    production builds them.
    """

    def __init__(self, uow: FakeUnitOfWork) -> None:
        self._uow = uow
        self.settings = Settings()
        self.clock = FakeClock()
        self.ids = FakeIdFactory()
        self.blobs = FakeBlobStore()
        self.browser = FakeBrowserProvider()
        self.transcriber = FakeTranscriber()
        # A supervisor with no browser behind it: start/stop are no-ops, which
        # is what these tests want -- the capture loop has its own coverage in
        # tests/integration/test_steel_capture.py.
        self.capture = FakeCaptureSupervisor()
        self.durable = FakeDurableExecution(self.induce_skill())

    def unit_of_work(self) -> UnitOfWork:
        return self._uow


class FakeCaptureSupervisor(CaptureController):
    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []

    async def start(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        debugger_url: str,
        start_url: str | None = None,
    ) -> None:
        self.started.append(str(recording_id))

    async def stop(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        self.stopped.append(str(recording_id))

    async def stop_all(self) -> None:
        return None


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
async def client(uow: FakeUnitOfWork) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: _FakeContainer(uow)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Tenant-Id": f.TENANT.value, "X-Principal-Id": f.OPERATOR.value},
    ) as http:
        yield http


class TestHealth:
    async def test_liveness_touches_nothing(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestRecordings:
    async def test_starting_a_recording_returns_a_live_view(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.post(
            "/v1/recordings",
            json={
                "objective_key": {
                    "objective_type": "release_wave",
                    "target_system": "blue_yonder",
                    "entity_type": "wave",
                    "facility": "DC01",
                    "direction": "outbound",
                },
                "start_url": "https://wms.test",
            },
        )

        assert response.status_code == 201
        assert response.json()["live_view_url"]

    async def test_an_unknown_recording_is_a_problem_document(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/v1/recordings/nope")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["status"] == 404

    async def test_a_recording_renders_its_frames(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        recording = f.recording(frames=0)
        recording.append_frame(f.frame(requests=(f.request(),)))
        await uow.recordings.add(recording)

        response = await client.get(f"/v1/recordings/{recording.id}")
        body = response.json()

        assert response.status_code == 200
        assert body["frame_count"] == 1
        assert body["frames"][0]["primary_request"].startswith("POST ")


class TestLiveView:
    async def test_an_open_recording_points_at_its_session(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        recording = f.recording(frames=0)
        recording.attach_browser_session(BrowserSessionId("sess-9"))
        await uow.recordings.add(recording)

        response = await client.get(f"/v1/recordings/{recording.id}/live-view")

        assert response.status_code == 200
        assert "sess-9" in response.json()["live_view_url"]

    async def test_a_sealed_recording_has_no_live_view(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        recording = f.recording(frames=1, sealed=True)
        await uow.recordings.add(recording)

        response = await client.get(f"/v1/recordings/{recording.id}/live-view")

        assert response.status_code == 200
        assert response.json()["live_view_url"] is None


class TestSkills:
    async def test_promoting_past_the_permitted_stage_is_refused(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        skill = f.skill()
        await uow.skills.add(skill)

        response = await client.post(
            f"/v1/skills/{skill.id}/promote",
            json={"version": 1, "to": "autonomous"},
        )

        assert response.status_code == 422
        assert "autonomous" in response.json()["detail"]

    async def test_promotion_to_shadow_is_allowed(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        skill = f.skill()
        await uow.skills.add(skill)

        response = await client.post(
            f"/v1/skills/{skill.id}/promote",
            json={"version": 1, "to": "shadow"},
        )

        assert response.status_code == 200
        assert response.json()["stage"] == "shadow"
