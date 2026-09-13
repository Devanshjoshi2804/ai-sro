"""Every tenant that has been recorded lately, read and mined without asking.

Both halves of the rig's learning cycle had a person in them. `MinePass` was
reachable from `POST /v1/mine` and from a script; `ReadGestures` from a route
and from `sro.cli.read_cron`, whose own docstring offers a crontab line. So a
deployment learned exactly as often as somebody remembered -- which is not what
a tenant's own brain means. The promise is that the work is watched, the
repetition is noticed and the job comes back, and none of that can wait on a
human deciding to look.

Read first, then mine, and the order is not arranged for tidiness. A mining
pass packs its window out of gestures and their READINGS; an unread gesture
carries no intent row, so mining ahead of the reader spends the most expensive
call in the system on evidence nobody has understood yet.

Not `MineEverything`, which is the pre-rig sweep: that one clusters
`observations` into `task_candidates` with no model, and then teaches every
candidate it has seen three times. This reads `gestures` and writes
`workflows`. Neither reads the other's tables, and this deployment runs on this
one.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timedelta

from sro.application.context import RequestContext
from sro.application.observation.mine_pass import MinePass
from sro.application.observation.mining_pass import MineResult
from sro.application.observation.read_gesture import ReadGestures
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap
from sro.domain.shared.identifiers import PrincipalId

__all__ = ["MAX_READS", "MineLately"]

MAX_READS = 25
"""How many reading passes one tenant gets in one sweep.

`ReadGestures` reads at most `READING_LIMIT` (200) gestures per call, so a
sweep that made one pass would read 200 an hour however many were captured, and
a busy tenant would fall further behind every hour with nothing anywhere saying
so. Passes repeat until one finds nothing left, which is the honest end of the
job.

Bounded anyway, at 5,000 gestures for one tenant in one sweep. Not a budget --
`daily_usd_cap` is the budget and `OverCap` is what stops a sweep that reaches
it -- but a stop against a pass that keeps reporting progress it is not making,
so a broken reader costs one sweep rather than every sweep at once. The same
number and the same argument as `sro.cli.read_cron.MAX_PASSES`, which is the
hand-run version of this."""

logger = logging.getLogger(__name__)


class MineLately:
    """One pass for each tenant whose browsers uploaded in the window.

    Tenant-blind, like every scheduled sweep in this system and for the same
    reason: there is no request behind it and nobody to take a tenant from. It
    asks which tenants have evidence and then mines each one inside its own
    context.

    One tenant's refusal is one tenant's refusal. A spend cap reached, a model
    that will not answer, a pass that raised something nobody predicted -- each
    is caught per tenant, because a sweep that stops at the first one lets the
    tenant whose name sorts first decide whether anybody else learns today.

    What is NOT caught is the sweep's own read of who to mine: if that fails
    there is nothing to iterate and the caller's loop logs it and waits for the
    next interval.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        pass_: MinePass,
        reader: ReadGestures,
        *,
        window_hours: int,
        max_reads: int = MAX_READS,
    ) -> None:
        self._uow = uow
        self._pass = pass_
        self._reader = reader
        self._window_hours = window_hours
        self._max_reads = max_reads

    async def _read(self, ctx: RequestContext) -> int:
        """Everything unread, up to the bound. One `ReadGestures` call reads at
        most `READING_LIMIT` gestures, so a sweep that made one pass would leave
        a busy tenant falling further behind every hour with nothing saying so.

        A fresh door per pass: each opens, commits and closes its own unit of
        work, and re-entering a spent one is not a thing the container promises.
        """
        read = 0
        for _ in range(self._max_reads):
            got = await self._reader.execute(ctx)
            read += got
            if got == 0:
                break
        return read

    async def execute(self, *, now: datetime) -> dict[str, MineResult]:
        since = now - timedelta(hours=self._window_hours)
        async with self._uow as uow:
            tenants = await uow.gestures.tenants_since(since)

        mined: dict[str, MineResult] = {}
        for tenant_id in tenants:
            ctx = RequestContext(tenant_id=tenant_id, principal_id=PrincipalId("miner"))
            try:
                read = await self._read(ctx)
                result = await self._pass.execute(ctx)
                mined[tenant_id.value] = replace(result, read=read)
            except OverCap as reached:
                # Not an error and not a surprise: the cap is the deployment
                # saying how much a day of learning may cost, and a sweep that
                # logged an exception for it would cry wolf every hour after
                # the budget was spent.
                logger.info("%s: %s", tenant_id.value, reached)
                mined[tenant_id.value] = MineResult(error=str(reached))
            except Exception as problem:
                logger.exception("%s: the mining pass could not finish", tenant_id.value)
                mined[tenant_id.value] = MineResult(error=str(problem))
        return mined
