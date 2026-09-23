from __future__ import annotations

from dataclasses import dataclass

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.observation.pool import PoolEntry


@dataclass(frozen=True, slots=True)
class Pool:
    waiting: tuple[PoolEntry, ...]

    retired: tuple[PoolEntry, ...]


class ReadPool:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext) -> Pool:
        async with self._uow as uow:
            return Pool(
                waiting=await uow.pool.waiting(ctx.tenant_id),
                retired=await uow.pool.retired(ctx.tenant_id),
            )
