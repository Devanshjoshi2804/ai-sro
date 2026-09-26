"""Two presses of one question, against Postgres: one answer, one run.

Two panels, or Do it and a typed yes, reach the door at the same instant. The
answer closes the question under the thread's row lock, so the second press
finds it closed; and the run is recorded against the offer it answers under a
unique index, so a second start of that offer is refused even from a path
that never read the thread.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.converse import Converse, StartThread
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.chat.asking import Pending
from sro.domain.chat.thread import Message, MessageId, Speaker
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.shared.errors import Conflict
from sro.infrastructure.db.repositories import SqlUnitOfWork
from sro.infrastructure.system import UuidFactory
from tests import factories as f
from tests.unit.application.rig.test_from_the_mail import CTX, JOB, _held_in
from tests.unit.application.rig.test_start_workflow_run import _starter
from tests.unit.fakes import FakeClock, FakeDurableExecution, FakeEmbedder
from tests.unit.runtime_support import save_job


def _converse(sessions: async_sessionmaker[AsyncSession]) -> Converse:
    uow = SqlUnitOfWork(sessions)
    return Converse(
        uow, ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder()))), FakeClock(), UuidFactory()
    )


async def test_two_presses_of_one_question_give_one_answer(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = await _held_in(SqlUnitOfWork(session_factory))
    thread = await StartThread(uow, FakeClock(), UuidFactory()).execute(CTX)
    await AskAboutTheOffer(uow, FakeClock(), UuidFactory()).execute(
        CTX,
        Pending(
            workflow_id=JOB,
            title="Create a Customer Type",
            values={"Customer Type": "X", "Customer Type Description": "e"},
            missing=(),
            mail_thread="t-2",
        ),
        mail_thread="t-2",
        ask_to_run=True,
    )
    async with SqlUnitOfWork(session_factory) as reading:
        question = (await reading.threads.get(CTX.tenant_id, thread.id)).messages[-1].id.value

    one, other = await asyncio.gather(
        *(
            _converse(session_factory).execute(
                CTX, thread_id=thread.id, text="yes", answering=question
            )
            for _ in range(2)
        )
    )

    # What each press hands its browser: a `resume` is a run the browser starts.
    told = [(reply.messages[-1].decision or {}).get("resume") for reply in (one, other)]
    assert sorted(bool(it) for it in told) == [False, True], told
    async with SqlUnitOfWork(session_factory) as reading:
        said = (await reading.threads.get(CTX.tenant_id, thread.id)).messages
    assert sum(bool((m.decision or {}).get("resume")) for m in said) == 1
    assert any(m.text.startswith("That question is no longer open") for m in said)


async def test_two_starts_of_one_offer_make_one_run(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with SqlUnitOfWork(session_factory) as uow:
        await save_job(uow, "wfl_ct")
        await uow.commit()

    async def start() -> WorkflowRun:
        return await _starter(
            SqlUnitOfWork(session_factory),
            durable=FakeDurableExecution(),
            steel_tenants=frozenset({f.TENANT.value}),
        ).execute(
            CTX,
            workflow_id="wfl_ct",
            device_id=None,
            values={"Customer Type": "GT2"},
            live=True,
            allow_focus=False,
            offer="msg_question",
        )

    done = await asyncio.gather(start(), start(), return_exceptions=True)

    assert sorted(type(one).__name__ for one in done) == ["Conflict", "WorkflowRun"], done
    assert any(isinstance(one, Conflict) for one in done)
    async with SqlUnitOfWork(session_factory) as uow:
        assert len(await uow.workflow_runs.for_workflow(f.TENANT, "wfl_ct")) == 1


async def test_a_write_begun_before_an_answer_keeps_the_answer(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The poll reads the thread, the operator leaves the question, then the
    poll writes. A thread that is written whole would put the question back."""
    uow = await _held_in(SqlUnitOfWork(session_factory))
    thread = await StartThread(uow, FakeClock(), UuidFactory()).execute(CTX)
    await AskAboutTheOffer(uow, FakeClock(), UuidFactory()).execute(
        CTX,
        Pending(
            workflow_id=JOB,
            title="Create a Customer Type",
            values={"Customer Type": "X", "Customer Type Description": "e"},
            missing=(),
            mail_thread="t-2",
        ),
        mail_thread="t-2",
        ask_to_run=True,
    )
    async with SqlUnitOfWork(session_factory) as reading:
        question = (await reading.threads.get(CTX.tenant_id, thread.id)).messages[-1].id.value

    async with SqlUnitOfWork(session_factory) as poll:
        seen = await poll.threads.get(CTX.tenant_id, thread.id)
        await _converse(session_factory).execute(
            CTX, thread_id=thread.id, text="no", answering=question
        )
        seen.say(
            Message(
                id=MessageId("msg_later"),
                speaker=Speaker.ASSISTANT,
                text="something the poll had to say",
                said_at=FakeClock().now(),
            )
        )
        await poll.threads.save(seen)
        await poll.commit()

    async with SqlUnitOfWork(session_factory) as reading:
        said = (await reading.threads.get(CTX.tenant_id, thread.id)).messages
    assert any(m.text.startswith("Left ") for m in said), [m.text for m in said]
    assert said[-1].text == "something the poll had to say"
    again = await _converse(session_factory).execute(
        CTX, thread_id=thread.id, text="yes", answering=question
    )
    assert not any((m.decision or {}).get("resume") for m in again.messages)
