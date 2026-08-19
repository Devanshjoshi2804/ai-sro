"""What a QA pass found, kept so it cannot come back.

Each of these was a real answer this system gave: an internal error for a
request that was merely wrong, an outage passed through from a hosted model, a
stream that hung for fifteen minutes on somebody else's run.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.application.execution.answer import read_answer
from sro.application.intent.narrow import _mentions
from sro.domain.execution.run import Run, RunId
from sro.domain.shared.errors import DomainError
from sro.domain.skill.promotion import PromotionStage
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from sro.interface.http.errors import _status_for
from tests import factories as f
from tests.unit.fakes import FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for


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


class TestErrorsThatSaidNothing:
    def test_a_domain_error_nobody_mapped_is_still_the_requests_fault(self) -> None:
        """It answered 500 with the right sentence inside it, which sends the
        operator to report an outage and a developer to the wrong place."""

        class Unmapped(DomainError):
            code = "unmapped"

        assert _status_for(Unmapped("that field has no list behind it")) == 422

    def test_an_unknown_enum_value_is_a_bad_request_not_a_crash(self) -> None:
        """`promote to "wizard"` raised ValueError inside the handler."""
        from pydantic import ValidationError

        from sro.interface.http.schemas import PromoteRequest

        with pytest.raises(ValidationError):
            PromoteRequest(version=1, to="wizard")


class TestWordsThatAreNotValues:
    def test_a_word_inside_another_word_is_not_a_mention(self) -> None:
        """ "all" sits inside `allowMultipleOpenContainers`, and matching it
        there made "list all transport modes" ask which field "all" names."""
        assert not _mentions("Multiple Open Containers (allowMultipleOpenContainers)", "all")

    def test_a_word_that_is_the_label_is_a_mention(self) -> None:
        assert _mentions("Parcel (smallPackageFlag)", "parcel")


class TestSayingNothingFoundProperly:
    def test_no_records_reads_as_english(self) -> None:
        """ "There are no supplier." — the entity is singular everywhere else,
        and this is the one sentence where that reads as broken."""
        answer = read_answer('{"data": []}', url="https://wms.test/x?limit=50")

        assert answer is not None
        assert answer.sentence("supplier") == "Nothing matched — no supplier came back."


class TestARunStartedFromAThread:
    """`skill_id` was optional in the body and unchecked: leaving it out built
    `SkillId("")`, started a durable workflow against no skill at all, and the
    only sign of it was a 404 from an unrelated line further down — the run
    itself kept going as an orphan nothing could trace back to this request."""

    async def test_missing_skill_id_is_refused_before_any_run_starts(
        self, client: httpx.AsyncClient
    ) -> None:
        thread = await client.post("/v1/threads")
        thread_id = thread.json()["id"]

        response = await client.post(
            f"/v1/threads/{thread_id}/runs",
            json={"parameters": {}, "medium": "network"},
        )

        assert response.status_code == 422
        assert "skill_id" in response.json()["detail"]


class TestABatchOfNothing:
    """`{"items": []}` answered 201 with zero runs and nothing performed --
    which reads as success for a batch the operator never actually confirmed,
    since there was no table to confirm."""

    async def test_an_empty_batch_is_refused_not_silently_completed(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork
    ) -> None:
        skill = f.skill()
        await uow.skills.add(skill)

        response = await client.post(f"/v1/skills/{skill.id}/batch", json={"items": []})

        assert response.status_code == 422


class TestAPursuitBelongsToOneTenant:
    """Every other resource here 404s across tenants; a pursuit -- driving a
    browser on somebody's behalf and about to write into their thread -- did
    not, because `pursuit_id` was trusted to be unguessable instead of checked.
    Also: the fake container never set `pursuits` at all, so this endpoint had
    never been exercised by any test before now."""

    async def test_another_tenant_cannot_poll_this_one_s_pursuit(
        self, client: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        progress = container.pursuits.start("pur_test", "adjust an LPN", tenant_id=f.TENANT.value)

        response = await client.get(f"/v1/threads/t-1/pursue/{progress.id}")
        assert response.status_code == 200

        app = create_app()
        app.dependency_overrides[get_container] = lambda: container
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token_for(tenant='rival')}"},
        ) as rival:
            theirs = await rival.get(f"/v1/threads/t-1/pursue/{progress.id}")

        assert theirs.status_code == 404


class TestTheKnowledgeBaseIngestPathIsReal:
    """`make ingest-kb` pointed at `knowledge-base/blue-yonder-sce/`, a
    directory that has never existed -- the real files sit directly under
    `knowledge-base/index/` and `knowledge-base/http/`. Every default-args run
    read zero claims and exited 1, and the module's own per-file warning made
    that read as "an empty knowledge base" rather than as a broken path."""

    def test_the_default_root_actually_has_the_catalogue_under_it(self) -> None:
        from sro.infrastructure.knowledge.ingest import _DEFAULT_ROOT

        assert (_DEFAULT_ROOT / "index" / "app-map.json").is_file()
        assert (_DEFAULT_ROOT / "http" / "status-matrix.json").is_file()


class TestARunAgainstASkillThatIsNotThere:
    """The skill was read *after* the workflow was scheduled, so a thread run
    naming a skill this tenant does not have answered 404 while the run it had
    already started went off and failed on its own -- out of sight of the
    request that caused it, and with a run id the thread never got told."""

    async def test_nothing_is_scheduled_before_the_skill_is_known(
        self, client: httpx.AsyncClient, container: _FakeContainer
    ) -> None:
        thread = await client.post("/v1/threads")

        response = await client.post(
            f"/v1/threads/{thread.json()['id']}/runs",
            json={"skill_id": "skill-nope", "parameters": {}, "medium": "network"},
        )

        assert response.status_code == 404
        assert container.durable.started == []


class TestARunTheBreakerStopped:
    """The breaker exists to ask a person to look. Started from a thread it
    asked nobody: the refusal was raised inside the workflow, after the request
    had answered 201 with the id of a run that was never created, so the console
    watched "opening the connection" forever for a run stopped on purpose."""

    async def test_a_refusal_reaches_the_operator_rather_than_the_worker_log(
        self, client: httpx.AsyncClient, uow: FakeUnitOfWork, container: _FakeContainer
    ) -> None:
        version = f.skill_version()
        skill = f.skill(versions=0)
        skill.add_version(version)
        version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
        await uow.skills.add(skill)
        for index in range(3):
            failed = Run(
                id=RunId(f"old-{index}"),
                tenant_id=f.TENANT,
                skill_id=skill.id,
                skill_version=1,
                stage=PromotionStage.SHADOW,
                parameters={},
                requested_by=f.OPERATOR,
                started_at=f.at(800),
                target_system=skill.objective_key.target_system,
            )
            failed.fail(f.at(900), "the system answered with its login page")
            await uow.runs.add(failed)

        thread = await client.post("/v1/threads")
        response = await client.post(
            f"/v1/threads/{thread.json()['id']}/runs",
            json={
                "skill_id": skill.id.value,
                "parameters": {"shipment_id": "1"},
                "medium": "network",
            },
        )

        assert response.status_code == 409
        assert "look" in response.json()["detail"]
        assert container.durable.started == []
