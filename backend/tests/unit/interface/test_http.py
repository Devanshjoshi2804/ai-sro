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
from sro.application.execution.approvals import Approvals
from sro.application.execution.one_time_secrets import OneTimeSecrets
from sro.application.execution.pursuits import Pursuits
from sro.application.execution.stops import Stops
from sro.application.ports.auth import Caller
from sro.application.ports.capture import CaptureController
from sro.application.ports.repositories import UnitOfWork
from sro.config import Settings, get_settings
from sro.container import Container
from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.shared.identifiers import (
    BrowserSessionId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
)
from sro.domain.skill.plan import NetworkPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.template import Template
from sro.infrastructure.agent.sockets import DeviceSockets
from sro.infrastructure.auth.signed_tokens import SignedTokens
from sro.infrastructure.gemini.null_interpreter import NoInterpreter
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
    FakeIntentParser,
    FakeRunDispatcher,
    FakeScheduler,
    FakeSignInDriver,
    FakeToolCaller,
    FakeTranscriber,
    FakeUiDriver,
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
        # No reading of the demonstration in tests: the description is the one
        # part of a skill a model writes, and asserting on model prose is how a
        # suite starts failing for reasons nobody changed.
        self.interpreter = NoInterpreter()
        self.vault = FakeCredentialVault()
        # A supervisor with no browser behind it: start/stop are no-ops, which
        # is what these tests want -- the capture loop has its own coverage in
        # tests/integration/test_steel_capture.py.
        self.capture = FakeCaptureSupervisor()
        # Teaching asks whether the system is open before it opens a browser.
        # Here nothing is reachable and nothing is stored, so the answer is "no"
        # and the endpoint's own refusal is what the tests see.
        self.http = FakeHttpCaller()
        # No connectors, which is what a deployment that configured none has.
        # A skill with a tool step then records that there was nothing to call,
        # which is the answer, rather than pretending the step is impossible.
        self.tools = FakeToolCaller(available=False)
        self.http.unreachable = True
        self.sign_in_driver = FakeSignInDriver()
        # Real credential checking, with a key that lives for the length of the
        # test: the wiring under test includes who is allowed to ask.
        self.credentials = SignedTokens(TEST_SECRET)
        self.ui = FakeUiDriver()
        self.vision = None
        # No model for the rig's own passes. `None` is what a deployment with
        # no key gets, and what the miner and the runner must refuse to run on.
        self.asker = None
        self.tokens = None
        self.intent_parser = FakeIntentParser()
        self.pursuits = Pursuits()
        # Hand-set beside the pursuits: this container writes its own
        # `__init__`, so the dataclass defaults never run for it.
        self.stops = Stops()
        # Beside the stops, and for the same reason: a run parked on a person
        # waits on an event in this process, so a container with a register of
        # its own is a tap nothing is waiting on.
        self.approvals = Approvals()
        # Beside the stops and the approvals, for the same reason: a one-time
        # password is held in this process's memory, and a container that
        # writes its own `__init__` needs its own store.
        self.one_time_secrets = OneTimeSecrets()
        self.agent_sockets = DeviceSockets()
        self.scheduler = FakeScheduler()
        self.dispatcher = FakeRunDispatcher()
        # Last: the executor it wraps reaches for the http caller and the
        # driver above, so the fakes have to exist before it is built.
        self.durable = FakeDurableExecution(execute=self.execute_skill())

    def unit_of_work(self) -> UnitOfWork:
        # `hand_out`, not the bare instance: the real container returns a
        # `SqlUnitOfWork` whose repositories do not exist until `async with`
        # opens its session, and a use case that forgets the block has to
        # fail here rather than against a customer's database.
        return self._uow.hand_out()


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


TEST_SECRET = "a-key-that-exists-only-in-this-test"  # noqa: S105 -- not a credential


def token_for(tenant: str = "", principal: str = "") -> str:
    return SignedTokens(TEST_SECRET).issue(
        Caller(
            tenant_id=TenantId(tenant) if tenant else f.TENANT,
            principal_id=PrincipalId(principal) if principal else f.OPERATOR,
        ),
        lasting_hours=1,
    )


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
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


class TestHealth:
    async def test_liveness_touches_nothing(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_liveness_says_which_code_is_answering(self, client: httpx.AsyncClient) -> None:
        """The field that turns "the fix is on disk" into "the fix is running"."""
        response = await client.get("/health")

        assert response.json()["revision"] == get_settings().revision
        assert response.json()["revision"]


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
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        """A real recording is read through the same door on purpose: a path
        nobody registered answers 404 with this exact problem document, so
        without it this proves the route absent rather than well-mannered."""
        real = f.recording(frames=0)
        await uow.recordings.add(real)

        response = await client.get("/v1/recordings/nope")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["status"] == 404
        assert (await client.get(f"/v1/recordings/{real.id}")).status_code == 200

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


class TestTheDoor:
    """What a stranger on the network can do, which should be nothing."""

    async def test_without_a_credential_nothing_is_served(self, container: _FakeContainer) -> None:
        app = create_app()
        app.dependency_overrides[get_container] = lambda: container
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as anonymous:
            response = await anonymous.get("/v1/skills")

        assert response.status_code == 401
        assert "credential" in response.json()["detail"]

    async def test_a_forged_credential_is_refused(self, container: _FakeContainer) -> None:
        forged = SignedTokens("not-this-deployments-key").issue(
            Caller(tenant_id=f.TENANT, principal_id=f.OPERATOR), lasting_hours=1
        )
        app = create_app()
        app.dependency_overrides[get_container] = lambda: container
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {forged}"},
        ) as impostor:
            response = await impostor.get("/v1/skills")

        assert response.status_code == 401

    async def test_health_stays_open_because_a_load_balancer_has_no_token(
        self, client: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        app = create_app()
        app.dependency_overrides[get_container] = lambda: container
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as anonymous:
            assert (await anonymous.get("/health")).status_code == 200

    async def test_one_tenant_cannot_see_another_s_work(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
    ) -> None:
        """The isolation every use case assumes, exercised through the door."""
        await uow.skills.add(f.skill(name="Adjust inventory"))

        app = create_app()
        app.dependency_overrides[get_container] = lambda: container
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
        ) as rival:
            theirs = await rival.get("/v1/skills")

        assert [s["name"] for s in (await client.get("/v1/skills")).json()] == ["Adjust inventory"]
        assert theirs.json() == []


class TestBrowsersAreNotShared:
    """A live browser is a signed-in WMS. Before ownership was recorded, the
    listing endpoint handed every session id in the deployment to any caller
    with a token, and both endpoints below took one on the caller's word.
    """

    async def test_the_listing_shows_only_your_own_browsers(
        self, client: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        await container.browsers().open(
            RequestContext(tenant_id=TenantId("rival"), principal_id=PrincipalId("somebody-else"))
        )

        response = await client.get("/v1/connections/browsers")

        assert response.status_code == 200
        assert response.json() == []

    async def test_storing_a_session_from_a_browser_that_is_not_yours_is_refused(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
    ) -> None:
        """This one emptied their cookies into the caller's vault: naming
        somebody else's browser was the entire attack.

        The caller's own browser is stored through the same door on purpose. A
        `/v1/connections/{id}/session` that was never registered answers the
        same 404, so a refusal on its own proves the endpoint absent rather
        than the ownership check present -- and this is the one regression
        where "absent" and "safe" must not be allowed to look alike.
        """
        theirs = await container.browsers().open(
            RequestContext(tenant_id=TenantId("rival"), principal_id=PrincipalId("somebody-else"))
        )
        mine = await container.browsers().open(
            RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
        )
        await _connected(uow, container)

        response = await client.post(
            f"/v1/connections/con-1/session?browser_session_id={theirs.id}"
        )

        assert response.status_code == 404
        assert (
            await client.post(f"/v1/connections/con-1/session?browser_session_id={mine.id}")
        ).status_code == 200


class TestRunReversal:
    """`GET /v1/runs/{id}` offers an undo by paging the tenant's whole skill
    library, not just its first fifty -- the one button whose entire value is
    the operator being able to rely on it. See `_LIBRARY_PAGE` in
    `sro.interface.http.v1.routers.runs`."""

    async def test_a_matching_delete_past_the_default_page_is_still_found(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        for i in range(60):
            await uow.skills.add(f.skill(id=SkillId(f"pad-{i}"), name=f"padding {i}"))

        version = f.skill_version(
            steps=(
                f.step(
                    index=0,
                    network_plan=NetworkPlan(
                        method="DELETE",
                        url=Template("https://wms.test/api/workOperations/$operation_id"),
                        body=None,
                        expected_status=204,
                    ),
                    ui_plan=None,
                ),
            ),
            parameters=(f.parameter(name="operation_id", observed_values=("NDPCK",)),),
        )
        undoer = f.skill(id=SkillId("undoer"), name="Delete a work operation", versions=0)
        undoer.add_version(version)
        version.promote(PromotionStage.SHADOW, f.at(10), f.OPERATOR)
        version.promote(PromotionStage.ASSISTED, f.at(20), f.OPERATOR)
        await uow.skills.add(undoer)

        run = Run(
            id=RunId("run-1"),
            tenant_id=f.TENANT,
            skill_id=SkillId("some-other-skill"),
            skill_version=1,
            stage=PromotionStage.ASSISTED,
            parameters={},
            requested_by=f.OPERATOR,
            started_at=f.at(0),
            authorized_by=f.OPERATOR,
            target_system="wms",
        )
        run.record(
            StepOutcome(
                index=0,
                medium=Medium.NETWORK,
                disposition=StepDisposition.PERFORMED,
                intent="create the work operation",
                method="POST",
                url="https://wms.test/api/workOperations",
                status_code=201,
            )
        )
        run.learn("operation_id", "NDPCK")
        run.finish(f.at(60))
        await uow.runs.add(run)

        response = await client.get("/v1/runs/run-1")

        assert response.status_code == 200
        assert response.json()["reversal"] == {
            "skill_id": "undoer",
            # The version the undo was validated against, and what its delete
            # step says it does. Both are on the wire because the panel names
            # what "Undo that" will remove before it is pressed, and pins the
            # version it was offered against when it is.
            "version": 1,
            "removes": "release the wave",
            "parameters": {"operation_id": "NDPCK"},
        }
