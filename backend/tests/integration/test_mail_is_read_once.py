"""The heartbeat look and the server poll racing on one mail, against Postgres.

The claim is an insert that does nothing on conflict, so whichever caller
inserts first reads the mail and the other skips it -- no lock, no window.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.chat.from_the_mail import FromTheMail
from sro.application.chat.mailbox import K_OURS, is_ours, mail_key
from sro.application.runtime.answer_run import AnswerRun
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.unit.application.rig.test_from_the_mail import (
    CTX,
    JOB,
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
