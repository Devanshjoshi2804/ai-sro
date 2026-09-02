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
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import ASGITransport

from sro.application.chat.converse import StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.context import RequestContext
from sro.application.observation.propose import ProposeAboutCandidates
from sro.application.observation.teach import DismissCandidate
from sro.domain.chat.thread import Message, Speaker, Thread
from sro.domain.observation.candidate import WORTH_OFFERING, Episode, TaskCandidate
from sro.domain.shared.identifiers import BatchId, CandidateId, PrincipalId
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


# -- an offer is written into the thread --------------------------------------
#
# The offer is the one thing in the panel that most wanted to survive the panel
# closing, and it was the one thing that did not. These are about it being a
# message: said once, said to the right operator, and said only about tasks
# somebody would actually want offered.

NINE = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
ADJUST = "PUT wm/inventory/adjust → GET wm/inventory/*"


class _NoInterpreter:
    """No model configured. Offering is not a model's decision -- how often
    something was done is counted, not read -- so every test below runs without
    one, and the offer still has to be made."""

    available = False

    async def read(self, evidence: str) -> object:
        raise AssertionError("offering must not read a demonstration")

    async def name_task(self, evidence: str) -> object:
        raise AssertionError("offering must not ask a model to name anything")

    async def judge_join(self, kind: str, first: str, second: str) -> object:
        raise AssertionError("offering must not ask a model anything")


def _candidate(
    ident: str = "cnd-1",
    *,
    times: int = WORTH_OFFERING,
    principal: PrincipalId | None = None,
    signature: str = ADJUST,
    title: str = "Update adjust on wms.acme.test",
    named_by_model: bool = False,
) -> TaskCandidate:
    return TaskCandidate(
        id=CandidateId(ident),
        tenant_id=f.TENANT,
        principal_id=principal or f.OPERATOR,
        signature=signature,
        host="wms.acme.test",
        title=title,
        named_by_model=named_by_model,
        episodes=tuple(
            Episode(
                started_at=NINE + timedelta(days=day),
                ended_at=NINE + timedelta(days=day, seconds=51),
                host="wms.acme.test",
                batch_ids=(BatchId("bat-1"),),
            )
            for day in range(times)
        ),
    )


def _propose(uow: FakeUnitOfWork) -> ProposeAboutCandidates:
    return ProposeAboutCandidates(uow, _NoInterpreter(), FakeClock(), FakeIdFactory())


def _offers_in(thread: Thread) -> list[Message]:
    return [m for m in thread.messages if (m.decision or {}).get("kind") == "offer"]


async def _thread_of(uow: FakeUnitOfWork, ctx: RequestContext = CTX) -> Thread | None:
    return await ReadThreads(uow).current(ctx)


async def test_a_task_worth_offering_is_said_out_loud_once() -> None:
    """The offer is a message in the conversation, so it survives the panel
    closing and the console sees the same exchange.

    Twice, because that is what actually happens: mining sweeps run every
    quarter of an hour over evidence they have already read, and a candidate
    that has not changed is proposed about again every time.
    """
    uow = FakeUnitOfWork()
    await uow.candidates.add(_candidate())

    first = await _propose(uow).execute(CTX)
    second = await _propose(uow).execute(CTX)

    thread = await _thread_of(uow)
    assert thread is not None
    assert len(_offers_in(thread)) == 1, "the same offer was posted by a second sweep"
    assert (first.offered, second.offered) == (1, 0)
    stored = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    assert stored.offered_at is not None, "the offer was said and not written down"


async def test_a_candidate_not_yet_worth_offering_says_nothing() -> None:
    """Twice is a coincidence and the operator knows it. Being asked about
    coincidences is how a recommendation surface gets ignored."""
    uow = FakeUnitOfWork()
    await uow.candidates.add(_candidate(times=WORTH_OFFERING - 1))

    proposed = await _propose(uow).execute(CTX)

    assert proposed.offered == 0
    assert await _thread_of(uow) is None, "a thread was started to say nothing in"


async def test_a_dismissed_candidate_is_not_offered() -> None:
    """A person already said no to this one. Asking again next week as though
    it were new is the reason a dismissal is kept rather than deleted."""
    uow = FakeUnitOfWork()
    dismissed = _candidate()
    dismissed.dismiss("not worth automating")
    await uow.candidates.add(dismissed)

    proposed = await _propose(uow).execute(CTX)

    assert proposed.offered == 0
    assert await _thread_of(uow) is None


async def test_the_offer_is_written_into_the_operator_s_own_thread() -> None:
    """The sweep runs as `miner`, which is nobody's conversation. An offer
    posted into the sweep's own thread is one the operator never sees."""
    uow = FakeUnitOfWork()
    await uow.candidates.add(_candidate())
    miner = RequestContext(tenant_id=f.TENANT, principal_id=PrincipalId("miner"))

    await _propose(uow).execute(miner)

    assert await _thread_of(uow, miner) is None
    thread = await _thread_of(uow)
    assert thread is not None
    assert len(_offers_in(thread)) == 1


async def test_the_offer_joins_the_conversation_the_operator_is_already_in() -> None:
    """One continuous thread. An offer in a thread of its own is a second
    conversation, which is the thing this whole change is undoing."""
    uow = FakeUnitOfWork()
    existing = await StartThread(uow, FakeClock(), FakeIdFactory()).execute(CTX)
    await uow.candidates.add(_candidate())

    await _propose(uow).execute(CTX)

    thread = await _thread_of(uow)
    assert thread is not None
    assert thread.id == existing.id


async def test_the_offer_carries_what_the_buttons_need() -> None:
    """The prose is for the operator; the decision is for the panel."""
    uow = FakeUnitOfWork()
    candidate = _candidate()
    await uow.candidates.add(candidate)

    await _propose(uow).execute(CTX)

    thread = await _thread_of(uow)
    assert thread is not None
    (offer,) = _offers_in(thread)
    assert offer.speaker is Speaker.SYSTEM
    assert offer.decision["kind"] == "offer"
    assert offer.decision["candidate_id"] == candidate.id.value
    assert offer.decision["times"] == WORTH_OFFERING
    assert offer.decision["seconds_each"] == 51
    assert offer.decision["host"] == "wms.acme.test"
    # Both halves. A decision with no prose is a message nobody can read, and
    # prose with no decision is a message the panel cannot draw buttons on.
    assert offer.text == "You've created 3 adjusts here — about 51s each."


async def test_the_offer_carries_the_sentence_the_ask_box_will_open_with() -> None:
    """Pressing "Do the next one" opens the same ask box every sentence goes
    through, and the panel fills it from the candidate's own words --
    `suggestedSentence` reads `title`, `named_by_model` and `signature`. An
    offer that carries none of them opens that box blank, even for a task a
    model has already named.
    """
    uow = FakeUnitOfWork()
    candidate = _candidate(title="Adjust an LPN after a short ship", named_by_model=True)
    await uow.candidates.add(candidate)

    await _propose(uow).execute(CTX)

    thread = await _thread_of(uow)
    assert thread is not None
    (offer,) = _offers_in(thread)
    assert offer.decision["title"] == "Adjust an LPN after a short ship"
    assert offer.decision["named_by_model"] is True
    # The fallback, for a candidate no model named: the panel reads the noun
    # off the signature itself.
    assert offer.decision["signature"] == ADJUST


async def test_a_model_named_task_is_offered_in_the_model_s_own_sentence() -> None:
    """A title a model wrote is a full sentence conjugated as one. Spliced into
    the noun's slot it reads "You've created 3 Adjust an LPN after a short
    ship" -- which is what the panel already learned, and is the reason this
    ports its wording rather than inventing a second one."""
    uow = FakeUnitOfWork()
    await uow.candidates.add(
        _candidate(title="Adjust an LPN after a short ship", named_by_model=True)
    )

    await _propose(uow).execute(CTX)

    thread = await _thread_of(uow)
    assert thread is not None
    (offer,) = _offers_in(thread)
    assert offer.text == (
        "Adjust an LPN after a short ship — you've done this 3 times, about 51s each. "
        "Want me to do the next one?"
    )


async def test_a_signature_with_no_word_in_it_is_still_said_in_english() -> None:
    """Vaguer is better than visibly broken: every segment substituted leaves
    no noun, and a placeholder in its slot is worse than "this"."""
    uow = FakeUnitOfWork()
    await uow.candidates.add(_candidate(signature="PUT */*"))

    await _propose(uow).execute(CTX)

    thread = await _thread_of(uow)
    assert thread is not None
    (offer,) = _offers_in(thread)
    assert offer.text == "You've done this 3 times here — about 51s each."


async def test_posting_an_offer_starts_nothing() -> None:
    """A message is a thing said; the press is the authorisation. If saying it
    out loud could start a run, an assisted run's record of consent would be a
    sentence the system wrote to itself."""
    uow = FakeUnitOfWork()
    await uow.candidates.add(_candidate())

    await _propose(uow).execute(CTX)

    assert uow.runs.rows == {}, "an offer started a run nobody pressed anything for"
    stored = await uow.candidates.get(f.TENANT, CandidateId("cnd-1"))
    assert stored.status_is_new, "an offer decided something about the candidate"


async def _answers_in(uow: FakeUnitOfWork, principal: PrincipalId) -> list[Message]:
    """Every message recording what came of an offer, in this operator's thread."""
    thread = await ReadThreads(uow).current(RequestContext(f.TENANT, principal))
    if thread is None:
        return []
    return [m for m in thread.messages if (m.decision or {}).get("kind") == "answered"]


async def test_saying_yes_to_an_offer_is_recorded_in_the_conversation(
    uow: FakeUnitOfWork,
) -> None:
    """The console showed every offer permanently unanswered, and a reopened
    panel drew both buttons again as though the question were still open."""
    candidate = _candidate(times=WORTH_OFFERING)
    candidate.offered_at = NINE
    await uow.candidates.add(candidate)
    await uow.commit()

    await DismissCandidate(uow, FakeClock(NINE), FakeIdFactory()).execute(
        RequestContext(f.TENANT, f.OPERATOR), candidate_id=candidate.id, reason="not this one"
    )

    (said,) = await _answers_in(uow, f.OPERATOR)
    assert said.speaker is Speaker.SYSTEM
    assert said.decision["answer"] == "dismissed"
    assert said.decision["candidate_id"] == candidate.id.value


async def test_an_offer_nobody_made_gets_no_answer(uow: FakeUnitOfWork) -> None:
    """A candidate dismissed from the console was never asked about. Answering
    a question nobody put would start a conversation to say it into."""
    candidate = _candidate(times=WORTH_OFFERING)
    assert candidate.offered_at is None
    await uow.candidates.add(candidate)
    await uow.commit()

    await DismissCandidate(uow, FakeClock(NINE), FakeIdFactory()).execute(
        RequestContext(f.TENANT, f.OPERATOR), candidate_id=candidate.id, reason="no"
    )

    assert await _answers_in(uow, f.OPERATOR) == []
    assert await ReadThreads(uow).current(RequestContext(f.TENANT, f.OPERATOR)) is None, (
        "answering an offer nobody made started a conversation"
    )


async def test_the_answer_lands_in_the_operator_s_thread_not_the_caller_s(
    uow: FakeUnitOfWork,
) -> None:
    """Dismissal can be done on somebody's behalf. A message in the wrong
    conversation is worse than none: the operator never sees it, and somebody
    else sees work they did not do."""
    theirs = PrincipalId("someone-else")
    candidate = _candidate(principal=theirs)
    candidate.offered_at = NINE
    await uow.candidates.add(candidate)
    await uow.commit()

    await DismissCandidate(uow, FakeClock(NINE), FakeIdFactory()).execute(
        RequestContext(f.TENANT, f.OPERATOR), candidate_id=candidate.id, reason="no"
    )

    assert len(await _answers_in(uow, theirs)) == 1
    assert await _answers_in(uow, f.OPERATOR) == []
