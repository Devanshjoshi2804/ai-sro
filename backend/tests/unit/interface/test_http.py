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
    FakeCredentialVault,
    FakeDurableExecution,
    FakeEmbedder,
    FakeHttpCaller,
    FakeIdFactory,
    FakeSignInDriver,
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
        # Before the durable fake: it builds induction, which now records what it
        # could not decide, which needs somewhere to put it.
        self.embedder = FakeEmbedder()
        self.vault = FakeCredentialVault()
        # A supervisor with no browser behind it: start/stop are no-ops, which
        # is what these tests want -- the capture loop has its own coverage in
        # tests/integration/test_steel_capture.py.
        self.capture = FakeCaptureSupervisor()
        self.durable = FakeDurableExecution(self.induce_skill())
        # Teaching asks whether the system is open before it opens a browser.
        # Here nothing is reachable and nothing is stored, so the answer is "no"
        # and the endpoint's own refusal is what the tests see.
        self.http = FakeHttpCaller()
        self.http.unreachable = True
        self.sign_in_driver = FakeSignInDriver()

    def unit_of_work(self) -> UnitOfWork:
        return self._uow


class FakeCaptureSupervisor(CaptureController):
    def __init__(self) -> None:
        self.started: list[str] = []
        self.stopped: list[str] = []
        self.restored = False

    async def start(
        self,
        ctx: RequestContext,
        *,
        recording_id: RecordingId,
        debugger_url: str,
        start_url: str | None = None,
        session_cookies: tuple[dict[str, object], ...] = (),
    ) -> None:
        self.started.append(str(recording_id))
        self.restored = bool(session_cookies)

    async def stop(self, ctx: RequestContext, *, recording_id: RecordingId) -> None:
        self.stopped.append(str(recording_id))

    async def snapshot_cookies(self, recording_id: RecordingId) -> list[dict[str, object]]:
        return []

    async def stop_all(self) -> None:
        return None


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


@pytest.fixture
async def client(
    uow: FakeUnitOfWork, container: _FakeContainer
) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
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


async def _connected(uow: FakeUnitOfWork, container: _FakeContainer) -> None:
    """A system somebody has already signed in to."""
    import json

    from sro.domain.connection.connection import Connection, ConnectionId

    connection = Connection(
        id=ConnectionId("con-1"),
        tenant_id=f.TENANT,
        name="Blue Yonder",
        target_system="blue_yonder",
        base_url="https://wms.test/portal",
        created_at=f.T0,
    )
    connection.authenticated(f.at(10))
    await uow.connections.add(connection)
    await container.vault.store(
        connection.session_key,
        json.dumps({"origin": connection.base_url, "cookies": [{"name": "s", "value": "1"}]}),
    )


class TestRecordings:
    async def test_starting_a_recording_returns_a_live_view(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
    ) -> None:
        await _connected(uow, container)

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

    async def test_teaching_refuses_before_a_login_page_can_appear(
        self, client: httpx.AsyncClient
    ) -> None:
        """Nobody is signed in to this system. Said now, rather than discovered
        three clicks into a demonstration of the identity provider."""
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

        assert response.status_code == 409
        assert "nobody is signed in" in response.json()["detail"]
        assert "Connect it once" in response.json()["detail"]

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


class TestProblemDocuments:
    async def test_a_malformed_body_is_a_problem_document_like_everything_else(
        self, client: httpx.AsyncClient
    ) -> None:
        """FastAPI's default answer is a list of objects, which breaks the
        contract every other failure keeps — and a client that renders `detail`
        crashes on it rather than showing the operator what was wrong."""
        response = await client.post("/v1/recordings", json={"objective_key": 12})

        assert response.status_code == 422
        assert response.headers["content-type"].startswith("application/problem+json")
        problem = response.json()
        assert isinstance(problem["detail"], str)
        assert "objective_key" in problem["detail"]
