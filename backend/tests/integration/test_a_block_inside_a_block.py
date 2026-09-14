"""A unit of work opened inside a unit of work, against a real session.

The gap this closes is the one the unit suite cannot see. `FakeUnitOfWork`'s
`_entered` is sticky and its `__aexit__` is a no-op on success, so a nested
`async with uow:` is invisible to every one of the 3000 tests that use it --
while against `SqlUnitOfWork` the inner block used to open a SECOND session and
then close it and null `_session` on the way out, so the outer block's next
`commit()` raised "SqlUnitOfWork must be used as an async context manager" and
the first session's connection never went back to the pool.

That is not a hypothetical shape. `run_workflow` claims a write inside
`StartWorkflowRun`'s block, so the first live run of a job that creates a
record died at its first mutating step, with the RuntimeError's text rendered
in the panel as the reason -- and the claim it had just committed then refused
the operator's retry for half an hour, saying the write "may have landed" when
nothing was ever sent. `InduceSkill` runs `AskAbout`'s whole block inside its
own on the same instance.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.infrastructure.db.repositories import SqlUnitOfWork


async def test_the_inner_block_is_the_same_session_and_the_outer_one_survives_it(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = SqlUnitOfWork(session_factory)

    async with uow as outer:
        outside = outer._session
        async with uow as inner:
            assert inner._session is outside, "the inner block opened a second session"
            await inner.commit()

        # The three the old code broke, in the order it broke them.
        assert outer._session is outside, "the inner block closed the outer session"
        await outer.commit()
        assert await outer.workflow_runs.in_flight(TenantId("t"), DeviceId("dev-1")) is None, (
            "the outer block could not query after the inner one closed"
        )

    assert uow._session is None, "the outermost exit left the session open"


async def test_a_connection_is_not_leaked_by_the_nesting(postgres_url: str) -> None:
    """The half that wedges the API rather than failing one run.

    A second session opened and abandoned holds its connection until the pool
    is exhausted; the API's `pool_size=5, max_overflow=10` means about fifteen
    runs before every request hangs on checkout. Its own engine, because
    `conftest` builds `NullPool` -- which keeps no connections and so cannot
    show a leak -- and this is the one test that needs a pool to count.
    """
    engine = create_async_engine(postgres_url, pool_size=1, max_overflow=0)
    try:
        uow = SqlUnitOfWork(async_sessionmaker(engine, expire_on_commit=False))
        async with uow:
            await uow.commit()
            async with uow:
                await uow.commit()

        assert engine.pool.checkedout() == 0, "a nested block left a connection checked out"

        # And the pool of one still hands it out, which is the symptom an
        # operator meets: with the connection leaked, this hangs until it
        # times out.
        async with uow:
            await uow.commit()
    finally:
        await engine.dispose()


async def test_an_exception_inside_the_inner_block_rolls_back_and_still_closes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    uow = SqlUnitOfWork(session_factory)

    with pytest.raises(ValueError):
        async with uow:
            async with uow:
                raise ValueError("the inner block failed")

    assert uow._session is None, "a failing nested block left the session open"
