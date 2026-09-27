from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.aliases import JobAlias
from sro.infrastructure.db.repositories import SqlUnitOfWork

ACME, OTHER = TenantId("acme"), TenantId("other")


async def test_one_alias_per_wording_and_the_later_answer_wins(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    first = JobAlias("Cost Centre", "Department", "clerk", datetime(2026, 9, 25, 9, tzinfo=UTC))
    later = JobAlias("cost  centre", "Region", "lead", datetime(2026, 9, 25, 10, tzinfo=UTC))
    async with SqlUnitOfWork(session_factory) as uow:
        await uow.workflows.confirm_alias(ACME, "wfl_ct", first)
        await uow.workflows.confirm_alias(ACME, "wfl_ct", later)
        await uow.commit()

    async with SqlUnitOfWork(session_factory) as uow:
        assert await uow.workflows.aliases_for(ACME, "wfl_ct") == (later,)
        assert await uow.workflows.aliases_for(ACME, "wfl_other") == ()
        assert await uow.workflows.aliases_for(OTHER, "wfl_ct") == ()


async def test_aliases_come_back_oldest_first(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    older = JobAlias("region code", "Region", "clerk", datetime(2026, 9, 25, 9, tzinfo=UTC))
    newer = JobAlias("cost centre", "Department", "clerk", datetime(2026, 9, 25, 10, tzinfo=UTC))
    async with SqlUnitOfWork(session_factory) as uow:
        await uow.workflows.confirm_alias(ACME, "wfl_ct", newer)
        await uow.workflows.confirm_alias(ACME, "wfl_ct", older)
        await uow.commit()

    async with SqlUnitOfWork(session_factory) as uow:
        assert await uow.workflows.aliases_for(ACME, "wfl_ct") == (older, newer)
