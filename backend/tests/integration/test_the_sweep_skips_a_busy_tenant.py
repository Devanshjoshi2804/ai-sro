"""The background sweep never waits on a tenant another worker is mining.

`mining:{tenant}` is a Postgres advisory lock, held by `mine` for a whole
pass. The sweep's sign-in decisions only try for it: a tenant whose lock is
held elsewhere is skipped at once, quietly, and decided on a later sweep --
another worker already doing that tenant's work is the right outcome.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from sro.application.context import RequestContext
from sro.application.observation.mine_lately import MineLately
from sro.application.observation.mining_pass import MineResult
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Workflow
from sro.infrastructure.db.locks import PostgresAccountLocks
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.integration.test_account_locks import (
    _granted_advisory_locks,
    _waiting_advisory_locks,
)

BUSY, FREE = TenantId("busy-corp"), TenantId("free-corp")


class _Nothing:
    async def execute(self, ctx: RequestContext) -> MineResult:
        return MineResult()


class _NothingRead:
    async def execute(self, ctx: RequestContext) -> int:
        return 0


async def _signs_in(
    session_factory: async_sessionmaker[AsyncSession], tenant: TenantId
) -> bool | None:
    async with SqlUnitOfWork(session_factory) as uow:
        return (await uow.workflows.get(tenant, f"wfl_{tenant.value}")).signs_in


async def test_the_sweep_skips_a_tenant_mined_elsewhere_and_decides_another(
    engine: AsyncEngine,
    postgres_url: str,
    session_factory: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    async with SqlUnitOfWork(session_factory) as uow:
        for tenant in (BUSY, FREE):
            await uow.workflows.save(
                Workflow(id=f"wfl_{tenant.value}", tenant=tenant.value, title="t", narrative="n")
            )
        await uow.commit()

    elsewhere = create_async_engine(postgres_url, poolclass=NullPool)
    try:
        sweep = MineLately(
            SqlUnitOfWork(session_factory),
            _Nothing(),
            _NothingRead(),
            PostgresAccountLocks(engine),
            window_hours=24,
        )
        async with PostgresAccountLocks(elsewhere).hold_named(f"mining:{BUSY.value}"):
            await asyncio.wait_for(sweep.execute(now=datetime.now(tz=UTC)), timeout=5.0)
            assert await _waiting_advisory_locks(engine) == 0
            assert await _granted_advisory_locks(engine) == 1
            assert await _signs_in(session_factory, BUSY) is None
        assert await _signs_in(session_factory, FREE) is False
    finally:
        await elsewhere.dispose()

    assert not [record for record in caplog.records if record.levelno >= logging.WARNING]
