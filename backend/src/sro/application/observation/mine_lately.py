from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import groupby

from sro.application.context import RequestContext
from sro.application.observation.mine_pass import MinePass
from sro.application.observation.mining_pass import (
    MineResult,
    bring_in_parameters,
    decide_sign_ins,
    decide_tabs,
    mining_lock,
)
from sro.application.observation.read_gesture import ReadGestures
from sro.application.ports.locks import AccountLocks
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.learned import K_PARAMETERS_RULE
from sro.whose import about

__all__ = ["K_ERRORED_PASSES", "MAX_READS", "MineLately"]

MAX_READS = 25

logger = logging.getLogger(__name__)


def _when(stamp: str) -> datetime:
    try:
        started = datetime.fromisoformat(stamp)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return started if started.tzinfo else started.replace(tzinfo=UTC)


K_SETTLE_S = 120.0

K_ERRORED_PASSES = 3


class MineLately:
    def __init__(
        self,
        uow: UnitOfWork,
        pass_: MinePass,
        reader: ReadGestures,
        locks: AccountLocks,
        *,
        window_hours: int,
        max_reads: int = MAX_READS,
        settle_seconds: float = K_SETTLE_S,
    ) -> None:
        self._uow = uow
        self._pass = pass_
        self._reader = reader
        self._locks = locks
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
        newest = await uow.gestures.newest_arrival(tenant_id)
        if newest is not None and newest >= _when(last.started_at):
            return True
        if last.left_out <= 0:
            return False
        errored = 0
        for one in reversed(passes):
            if one.in_tokens > 0 or one.left_out <= 0:
                break
            if newest is not None and _when(one.started_at) <= newest:
                break
            errored += 1
        return errored < K_ERRORED_PASSES

    async def _decide(self) -> None:
        async with self._uow as uow:
            undecided = await uow.workflows.undecided()
            untabbed = await uow.workflows.tabs_undecided()
        for tenant in sorted({job.tenant for job in (*undecided, *untabbed)}):
            tenant_id = TenantId(tenant)
            try:
                async with self._locks.try_hold_named(mining_lock(tenant_id)) as held:
                    if not held:
                        logger.info("%s: being mined elsewhere; deciding it next sweep", tenant)
                        continue
                    async with self._uow as uow:
                        decided = await decide_sign_ins(
                            uow, tenant_id, [job for job in undecided if job.tenant == tenant]
                        )
                        tabbed = await decide_tabs(
                            uow, tenant_id, [job for job in untabbed if job.tenant == tenant]
                        )
                        await uow.commit()
            except Exception:
                logger.exception("%s: could not decide which jobs sign in or their tabs", tenant)
                continue
            if decided:
                logger.info("%s: decided whether %d job(s) sign in", tenant, decided)
            if tabbed:
                logger.info("%s: decided the tab of %d step(s)", tenant, tabbed)

    async def _bring_in(self) -> None:
        async with self._uow as uow:
            behind = await uow.workflows.behind_the_rule(K_PARAMETERS_RULE)
        for tenant, jobs in groupby(behind, key=lambda job: job.tenant):
            tenant_id = TenantId(tenant)
            try:
                async with self._locks.try_hold_named(mining_lock(tenant_id)) as held:
                    if not held:
                        logger.info("%s: being mined elsewhere; bringing it in next sweep", tenant)
                        continue
                    async with self._uow as uow:
                        brought = await bring_in_parameters(uow, tenant_id, list(jobs))
            except Exception:
                logger.exception("%s: could not bring in its jobs' parameters", tenant)
                continue
            if brought:
                logger.info(
                    "%s: %d parameter(s) brought in by the typed-values rule", tenant, brought
                )

    async def execute(self, *, now: datetime) -> dict[str, MineResult]:
        await self._decide()
        await self._bring_in()
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
                with about(tenant=tenant_id.value, principal="miner"):
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
