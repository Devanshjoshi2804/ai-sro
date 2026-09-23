"""The panel is a conversation: the thread this operator is already in.

`ReadThreads.current` answers "the conversation I am in" without splitting it
by tab, by host, or by anybody else's principal. `GET /v1/threads/current` is
what turns that into "make me one if I don't have one yet" -- reading and
writing kept as two different things, done by two different pieces of code:
`ReadThreads` only ever reads, and `StartThread` is the one place a thread is
made.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from sro.application.chat.converse import StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.domain.shared.identifiers import PrincipalId
from sro.interface.http.app import create_app
from sro.interface.http.deps import get_container
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer, token_for

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
OTHER = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("other@acme.test"))


async def test_the_current_thread_is_this_operator_s_most_recent() -> None:
    """One continuous conversation, not one per tab and not one per host: a job
    that spans a mailbox and the warehouse system belongs in one place."""
    uow = FakeUnitOfWork()
    ids, clock = FakeIdFactory(), FakeClock()
    start = StartThread(uow, clock, ids)
    older = await start.execute(CTX)
    clock.advance(60)
    newest = await start.execute(CTX)
    clock.advance(60)
    await start.execute(OTHER)

    found = await ReadThreads(uow).current(CTX)

    assert found is not None
    assert found.id == newest.id
    assert found.id != older.id


async def test_reading_current_answers_none_when_this_operator_has_no_thread() -> None:
    """A reader, not a writer: an absent thread is an honest `None`, not a
    silently created one. Making one belongs to `StartThread`."""
    uow = FakeUnitOfWork()

    found = await ReadThreads(uow).current(CTX)

    assert found is None


async def test_another_operator_s_thread_is_never_returned() -> None:
    """A thread must never be returned across operators or tenants -- a
    security boundary, not a nicety."""
    uow = FakeUnitOfWork()
    ids, clock = FakeIdFactory(), FakeClock()
    theirs = await StartThread(uow, clock, ids).execute(OTHER)

    found = await ReadThreads(uow).current(CTX)

    assert found is None
    assert theirs.opened_by != CTX.principal_id


async def test_a_busy_tenant_does_not_lose_this_operator_s_thread() -> None:
    """The principal belongs in the query, not in a filter over a page of the
    tenant's newest.

    The console starts a thread on every first ask, so a handful of colleagues
    between this operator's two visits is enough to push theirs out of any
    window -- and what that silently does is start them a second conversation
    and orphan every offer already said in the first, because `offered_at`
    never lets one be said twice.
    """
    uow = FakeUnitOfWork()
    ids, clock = FakeIdFactory(), FakeClock()
    start = StartThread(uow, clock, ids)
    mine = await start.execute(CTX)
    for _ in range(50):
        clock.advance(60)
        await start.execute(OTHER)

    found = await ReadThreads(uow).current(CTX)

    assert found is not None, "the operator's own thread fell out of the tenant's newest page"
    assert found.id == mine.id


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> _FakeContainer:
    return _FakeContainer(uow)


@pytest.fixture
async def client(container: _FakeContainer) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token_for()}"},
    ) as http:
        yield http


class TestTheCurrentThreadRoute:
    async def test_current_is_not_read_as_a_thread_id(self, client: httpx.AsyncClient) -> None:
        """`GET /threads/current` must resolve here, not fall through to
        `GET /threads/{thread_id}` and 404 on a thread literally named
        "current".

        Declared before `/{thread_id}` in the router is what makes this pass;
        move it below that route and this is the test that catches it.
        """
        response = await client.get("/v1/threads/current")

        assert response.status_code == 200, response.text

    async def test_an_operator_with_no_thread_gets_one(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/v1/threads/current")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["opened_by"] == f.OPERATOR.value
        assert body["messages"] == []

    async def test_the_same_operator_gets_the_same_thread_back(
        self, client: httpx.AsyncClient
    ) -> None:
        """Continuous, not a new thread minted on every call."""
        first = await client.get("/v1/threads/current")
        second = await client.get("/v1/threads/current")

        assert first.json()["id"] == second.json()["id"]
