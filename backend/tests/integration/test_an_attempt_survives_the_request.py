"""An attempt that is written is an attempt that is still there afterwards.

`SqlUnitOfWork.__aexit__` closes the session and does NOT commit -- one request
is one transaction and the caller says when it ends. The recorder flushed and
never committed, so every insert was thrown away as the block closed, silently,
while every door went on reporting that it had written one. The table stayed
empty for an evening.

The unit tests could not see it: `FakeUnitOfWork.attempts.record` appends to a
list, so it is there whether anything commits or not -- and the contract suite
says so in its own header, that transactions are deliberately not under
contract because a fake's `commit` is a counter. Which leaves this: the real
store, through the real use case, read back through a second block.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.context import RequestContext
from sro.application.observation.record_attempt import RecordAttempt
from sro.domain.observation.attempts import NOTHING
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.unit.fakes import FakeClock, FakeIdFactory

pytestmark = pytest.mark.anyio

TENANT = TenantId("greyorange")
CTX = RequestContext(tenant_id=TENANT, principal_id=PrincipalId("rudy"))


async def test_an_attempt_is_still_there_after_the_block_closes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    recorder = RecordAttempt(SqlUnitOfWork(session_factory), FakeIdFactory(), FakeClock())

    await recorder.execute(
        CTX,
        asked_for="approve a step",
        came_of=NOTHING,
        why="that step had already been let out",
        about={"run": "run_83efedf5"},
    )

    # A second block, a second session: what a later request would see, which
    # is the only thing that makes this a record rather than a local variable.
    async with SqlUnitOfWork(session_factory) as uow:
        kept = await uow.attempts.since(TENANT, since=datetime(2020, 1, 1, tzinfo=UTC), limit=10)

    assert [one.asked_for for one in kept] == ["approve a step"]
    assert kept[0].came_of == NOTHING
    assert kept[0].why == "that step had already been let out"
    assert kept[0].about == {"run": "run_83efedf5"}
    assert kept[0].principal == "rudy"
