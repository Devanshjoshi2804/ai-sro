"""F1 against Postgres: one question for every required field, and a drop that
ends the ask, through the real thread rows.

The asking state is the thread (`messages` JSONB, appended under the row lock
by `get_for_answer`). What these prove is that `asks`, `dropped` and a note's
kept `values` survive the real mapper, and that two presses of one question
still give one outcome when that outcome is F1's note.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.converse import Converse, StartThread
from sro.application.chat.read_threads import ReadThreads
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.asking import NEEDS, Pending, pending_job
from sro.domain.chat.thread import ThreadId
from sro.domain.shared.identifiers import PrincipalId
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.system import UuidFactory
from tests.unit.application.rig.test_from_the_mail import CTX, JOB, _held_in
from tests.unit.fakes import FakeClock, FakeEmbedder


def _converse(sessions: async_sessionmaker[AsyncSession]) -> Converse:
    uow = SqlUnitOfWork(sessions)
    return Converse(
        uow, ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder()))), FakeClock(), UuidFactory()
    )


async def _asked(sessions: async_sessionmaker[AsyncSession]) -> tuple[str, str]:
    uow = await _held_in(SqlUnitOfWork(sessions))
    thread = await StartThread(uow, FakeClock(), UuidFactory()).execute(CTX)
    await AskAboutTheOffer(uow, FakeClock(), UuidFactory()).execute(
        CTX,
        Pending(
            workflow_id=JOB,
            title="Create a Customer Type",
            values={},
            missing=("Customer Type", "Customer Type Description"),
        ),
    )
    async with SqlUnitOfWork(sessions) as reading:
        question = (await reading.threads.get(CTX.tenant_id, thread.id)).messages[-1]
    assert question.decision is not None and question.decision["kind"] == NEEDS
    assert [one["name"] for one in question.decision["asks"]] == [
        "Customer Type",
        "Customer Type Description",
    ]
    return thread.id.value, question.id.value


async def test_what_is_still_missing_rides_the_real_thread_row(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    thread_id, _ = await _asked(session_factory)
    said = await _converse(session_factory).execute(
        CTX, thread_id=ThreadId(thread_id), text="Customer Type: GPP"
    )

    async with SqlUnitOfWork(session_factory) as reading:
        messages = (await reading.threads.get(CTX.tenant_id, ThreadId(thread_id))).messages
    waiting = pending_job(messages)
    assert waiting is not None and waiting.missing == ("Customer Type Description",)
    assert waiting.values == {"Customer Type": "GPP"}
    assert said.messages[-1].decision is not None
    assert said.messages[-1].decision["asks"] == [
        {"name": "Customer Type Description", "max_length": None, "options": []}
    ]


async def test_two_presses_where_the_first_ends_the_ask_give_one_note(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    thread_id, question = await _asked(session_factory)
    await asyncio.gather(
        _converse(session_factory).execute(
            CTX,
            thread_id=ThreadId(thread_id),
            text="Customer Type: GPP, don't have customer type description",
            answering=question,
        ),
        _converse(session_factory).execute(
            CTX, thread_id=ThreadId(thread_id), text="first run", answering=question
        ),
    )

    async with SqlUnitOfWork(session_factory) as reading:
        said = (await reading.threads.get(CTX.tenant_id, ThreadId(thread_id))).messages
    closed = [m for m in said if m.text.startswith("That question is no longer open")]
    assert len(closed) == 1, [m.text for m in said]
    notes = [m.decision for m in said if m.decision and m.decision.get("kind") == "note"]
    assert len(notes) <= 1, notes
    for note in notes:
        assert note["values"] == {"Customer Type": "GPP"}, "M1: the note keeps the values"
        assert note["dropped"] == ["Customer Type Description"]
        assert pending_job(said) is None, "a note left the ask open"


async def test_the_thread_holding_an_offer_is_found_by_its_message_id(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """S4 M1: a run's request is read from the thread that holds its offer --
    matched inside the `messages` JSONB, which no type checks -- and only
    from a thread its starter opened."""
    thread_id, offer = await _asked(session_factory)
    newer = await StartThread(SqlUnitOfWork(session_factory), FakeClock(), UuidFactory()).execute(
        CTX
    )
    assert newer.id.value != thread_id

    async with SqlUnitOfWork(session_factory) as uow:
        found = await uow.threads.holding(
            CTX.tenant_id, opened_by=CTX.principal_id, message_id=offer
        )
        assert found is not None and found.id.value == thread_id
        assert any(one.id.value == offer for one in found.messages)
        assert (
            await uow.threads.holding(
                CTX.tenant_id, opened_by=PrincipalId("colleague"), message_id=offer
            )
            is None
        ), "a thread somebody else opened is never the starter's request"
        assert (
            await uow.threads.holding(
                CTX.tenant_id, opened_by=CTX.principal_id, message_id="msg_nobody"
            )
            is None
        )


async def test_a_question_s_chat_is_one_row_apart_from_the_operator_s_own(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """QA 2026-09-29: a mail's question has a chat of its own. Two writers
    opening it open one row (its id is derived); it is never `current`; and a
    run it starts is found by the chat that names it, inside `messages`."""
    uow = await _held_in(SqlUnitOfWork(session_factory))
    mine = await StartThread(uow, FakeClock(), UuidFactory()).execute(CTX)
    asked = {"kind": NEEDS, "workflow_id": JOB, "missing": ["Customer Type"]}

    def say() -> SayWhatHappened:
        return SayWhatHappened(SqlUnitOfWork(session_factory), FakeClock(), UuidFactory())

    await asyncio.gather(
        *(
            say().execute(
                CTX, for_operator=CTX.principal_id, text="What?", decision=asked, about="t-9"
            )
            for _ in range(2)
        )
    )
    await say().execute(
        CTX,
        for_operator=CTX.principal_id,
        text="Running it now.",
        decision={"kind": "job", "run_id": "run_vet"},
        about="t-9",
    )

    chat = await ReadThreads(uow).asking(CTX, "t-9")
    assert chat is not None and len(chat.messages) == 3
    assert [one.id for one in await ReadThreads(uow).asked(CTX)] == [chat.id]
    current = await ReadThreads(uow).current(CTX)
    assert current is not None and current.id == mine.id
    async with SqlUnitOfWork(session_factory) as reading:
        named = await reading.threads.naming(
            CTX.tenant_id, opened_by=CTX.principal_id, run_id="run_vet"
        )
    assert named is not None and named.id == chat.id
