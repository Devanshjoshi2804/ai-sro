"""The heartbeat look and the server poll racing on one mail, against Postgres.

The claim is an insert that does nothing on conflict, so whichever caller
inserts first reads the mail and the other skips it -- no lock, no window.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.chat.announce import SayWhatHappened
from sro.application.chat.from_the_mail import FromTheMail
from sro.application.chat.mailbox import K_OURS, elsewhere_key, is_ours, mail_key
from sro.application.runtime.answer_run import AnswerRun
from sro.domain.execution.progress import Progress
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    JOB,
    _asking_on_t9,
    _found,
    _held_in,
    _mail,
    _Mailbox,
    _reading,
    _Reads,
)
from tests.unit.fakes import FakeClock, FakeDurableExecution, FakeIdFactory


async def test_the_heartbeat_look_and_the_poll_racing_read_one_mail_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _held_in(SqlUnitOfWork(session_factory))
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please create customer type GT2")})
    reads = _Reads(_reading(JOB), _reading(JOB))
    heartbeat, poll = (
        FromTheMail(
            SqlUnitOfWork(session_factory),
            mailbox,
            reads,
            answer=AnswerRun(SqlUnitOfWork(session_factory), FakeDurableExecution()),
            clock=FakeClock(),
            ids=FakeIdFactory(),
        )
        for _ in range(2)
    )

    one, other = await asyncio.gather(heartbeat.execute(CTX), poll.execute(CTX))

    assert one.read + other.read == 1
    assert len(reads.saw) == 1


async def test_only_a_read_claim_written_as_ours_is_ours(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """A legacy send's `mail_key` row has the tool K_OURS; the look's read of
    the operator's own mail has another. Only the first is this system's."""
    uow, now = SqlUnitOfWork(session_factory), datetime.now(tz=UTC)
    async with uow as unit:
        await unit.tool_calls.remember(CTX.tenant_id, mail_key("sent"), tool=K_OURS, at=now)
        await unit.tool_calls.remember(CTX.tenant_id, mail_key("read"), tool="read", at=now)
        await unit.commit()
    since = now - timedelta(days=1)

    assert await is_ours(uow, CTX, {"id": "sent"}, since=since)
    assert not await is_ours(uow, CTX, {"id": "read"}, since=since)


async def test_two_forgets_racing_on_one_mark_take_it_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """`finish` and a colleague's look both tell the starter a reply sat in a
    mailbox they cannot read; whichever forgets the mark tells, the other not."""
    uow = SqlUnitOfWork(session_factory)
    async with uow as unit:
        await unit.tool_calls.remember(
            CTX.tenant_id, "elsewhere:r:q", tool="t", at=datetime.now(tz=UTC)
        )
        await unit.commit()

    async def _forget() -> bool:
        async with SqlUnitOfWork(session_factory) as unit:
            took = await unit.tool_calls.forget(CTX.tenant_id, "elsewhere:r:q")
            await unit.commit()
        return took

    assert sorted(await asyncio.gather(_forget(), _forget())) == [False, True]


async def test_a_note_that_fails_to_be_said_leaves_its_mark_for_the_retry(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """The mark is forgotten in the unit of work that says the note, so a
    failure between the two keeps it, and the retried `finish` tells."""
    run = await (await _asking_on_t9()).saved_run()
    key = elsewhere_key(run.id, Progress.of(run.progress).asking["id"])
    uow = SqlUnitOfWork(session_factory)
    async with uow as unit:
        await unit.tool_calls.remember(CTX.tenant_id, key, tool="t", at=datetime.now(tz=UTC))
        await unit.commit()
    say = SayWhatHappened(uow, FakeClock(), FakeIdFactory())

    async def _fails(*args: object, **kwargs: object) -> None:
        raise RuntimeError("the thread could not be written")

    say.execute = _fails  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        await say.answered_elsewhere(CTX, run)

    async with uow as unit:
        assert await unit.tool_calls.held(
            CTX.tenant_id, key, since=datetime.now(tz=UTC) - timedelta(days=1)
        )
