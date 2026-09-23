from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sro.application.context import RequestContext
from sro.application.observation.mine_pass import MinePass
from sro.application.observation.mining_pass import MineResult
from sro.application.observation.read_gesture import ReadGestures
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap
from sro.domain.shared.identifiers import PrincipalId, TenantId

__all__ = ["MAX_READS", "MineLately"]

MAX_READS = 25

logger = logging.getLogger(__name__)


def _when(stamp: str) -> datetime:
    try:
        started = datetime.fromisoformat(stamp)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return started if started.tzinfo else started.replace(tzinfo=UTC)


K_SETTLE_S = 120.0


class MineLately:
    def __init__(
        self,
        uow: UnitOfWork,
        pass_: MinePass,
        reader: ReadGestures,
        *,
        window_hours: int,
        max_reads: int = MAX_READS,
        settle_seconds: float = K_SETTLE_S,
    ) -> None:
        self._uow = uow
        self._pass = pass_
        self._reader = reader
        self._window_hours = window_hours
        self._max_reads = max_reads
        self._settle = settle_seconds

    async def _read(self, ctx: RequestContext) -> int:
        read = 0
        for _ in range(self._max_reads):
            got = await self._reader.execute(ctx)
            read += got
            if got == 0:
                break
        return read

    async def _worth_a_pass(self, uow: UnitOfWork, tenant_id: TenantId) -> bool:
        passes = await uow.workflows.passes(tenant_id)
        if not passes:
            return True
        last = passes[-1]
        if await uow.gestures.tenants_since(_when(last.started_at)):
            return True
        if not last.left_out:
            return False
        newest = await uow.gestures.newest_arrival(tenant_id)
        if newest is None:
            return False
        held = max(1, last.window_size)
        windows = -(-(held + last.left_out) // held)
        since_anybody_worked = sum(1 for one in passes if _when(one.started_at) > newest)
        return since_anybody_worked < windows

    async def execute(self, *, now: datetime) -> dict[str, MineResult]:
        since = now - timedelta(hours=self._window_hours)
        async with self._uow as uow:
            tenants = await uow.gestures.tenants_since(since)
            still_going = set(
                await uow.gestures.tenants_since(now - timedelta(seconds=self._settle))
            )
            worth = {
                tenant_id.value: await self._worth_a_pass(uow, tenant_id) for tenant_id in tenants
            }

        mined: dict[str, MineResult] = {}
        for tenant_id in tenants:
            if tenant_id in still_going:
                logger.info("%s: still working; leaving this one to settle", tenant_id.value)
                continue
            if not worth[tenant_id.value]:
                logger.info("%s: nothing new since the last pass", tenant_id.value)
                continue
            ctx = RequestContext(tenant_id=tenant_id, principal_id=PrincipalId("miner"))
            try:
                read = await self._read(ctx)
                result = await self._pass.execute(ctx)
                mined[tenant_id.value] = replace(result, read=read)
            except OverCap as reached:
                logger.info("%s: %s", tenant_id.value, reached)
                mined[tenant_id.value] = MineResult(error=str(reached))
            except Exception as problem:
                logger.exception("%s: the mining pass could not finish", tenant_id.value)
                mined[tenant_id.value] = MineResult(error=str(problem))
        return mined
