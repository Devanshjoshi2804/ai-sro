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


def _when(stamp: str) -> datetime:
    """A pass's `started_at`, which is an ISO string on the record and a real
    timestamp in the column. An unreadable one reads as the beginning of time,
    which makes the sweep pay for a pass it might not have needed -- the safe
    direction, since the other one is a tenant that silently stops learning."""
    try:
        started = datetime.fromisoformat(stamp)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return started if started.tzinfo else started.replace(tzinfo=UTC)


K_SETTLE_S = 120.0
"""How quiet a tenant's evidence has to go before a sweep reads it.

The sweep runs every minute now rather than every hour, which is the whole
point -- a task done at 10:00 was offered back at 11:00 and an operator
reasonably asked why. What a minute-by-minute sweep introduces is the opposite
failure: reading somebody mid-task, proposing the half of a job they had
finished, and offering that half back forever.

Two minutes, against what this store holds: a doing of a real task runs 35 to
180 seconds of continuous gestures, and uploads arrive a median 27 seconds
after the moment they cover. So two minutes of silence is a person who has
stopped, not a person thinking -- and the cost of being wrong is one more
interval, because nothing is thrown away by waiting.
"""


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
        settle_seconds: float = K_SETTLE_S,
    ) -> None:
        self._uow = uow
        self._pass = pass_
        self._reader = reader
        self._window_hours = window_hours
        self._max_reads = max_reads
        self._settle = settle_seconds

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

    async def _worth_a_pass(self, uow: UnitOfWork, tenant_id: TenantId) -> bool:
        """Whether another pass over this tenant has anything new to read.

        A pass re-reads the tenant's whole history, so on evidence that has not
        changed it asks the same question and pays for the same answer. One
        measured pass over tenant `new` cost $0.34, proposed the two jobs it
        already knew and kept nothing -- and on an hourly sweep that is $8 a
        day to learn nothing.

        Two ways it IS worth paying. Evidence has arrived since the last pass
        started, which is the ordinary case. Or the last pass LEFT SOMETHING
        OUT: a day too big for one window is read across several passes, and
        the carry-over pool rotates which part -- ten simulated passes went 81%
        then 96% coverage, with nineteen gestures never shown. So a pass with
        evidence it could not hold has more to say about a day nobody added to,
        and a pass whose window held everything does not.

        A tenant that has never been mined is always worth a pass.
        """
        passes = await uow.workflows.passes(tenant_id)
        if not passes:
            return True
        # `passes` is oldest first, by `started_at` then id.
        last = passes[-1]
        if last.left_out:
            return True
        # The pass's own clock, against the server's `received_at` on a batch.
        # A pass that was refused before it read anything still wrote its row,
        # so this is "since anything last looked", which is what it should be.
        return bool(await uow.gestures.tenants_since(_when(last.started_at)))

    async def execute(self, *, now: datetime) -> dict[str, MineResult]:
        since = now - timedelta(hours=self._window_hours)
        async with self._uow as uow:
            tenants = await uow.gestures.tenants_since(since)
            # Whoever is still uploading. Asked as "who has sent anything in the
            # last `settle` seconds" rather than by reading a newest-upload
            # column, because the port already answers that question and a
            # second way to ask it is a second thing to keep true.
            still_going = set(
                await uow.gestures.tenants_since(now - timedelta(seconds=self._settle))
            )
            worth = {
                tenant_id.value: await self._worth_a_pass(uow, tenant_id) for tenant_id in tenants
            }

        mined: dict[str, MineResult] = {}
        for tenant_id in tenants:
            if tenant_id in still_going:
                # Mid-task. This sweep runs every minute now, so the operator
                # who is halfway through creating a supplier would otherwise be
                # mined at the point they had filled two fields -- and half a
                # job, proposed and kept, is a job that will be offered back
                # half done. Waiting costs one interval and nothing else: the
                # evidence does not go anywhere.
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
