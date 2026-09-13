"""Every tenant that has been recorded lately, mined without being asked.

`MinePass` is the rig's miner and the only thing that had ever called it was a
person: `POST /v1/mine`, or a script somebody ran. So a deployment learned
exactly as often as somebody remembered to press the button, which is not what
a tenant's own brain means -- the whole promise is that the work is watched,
the repetition is noticed, and the job comes back without a human deciding to
look.

Not `MineEverything`, which is the pre-rig sweep: that one clusters
`observations` into `task_candidates` with no model, and then teaches every
candidate it has seen three times. This reads `gestures` and writes
`workflows`. Neither reads the other's tables, and this deployment runs on this
one.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sro.application.context import RequestContext
from sro.application.observation.mine_pass import MinePass
from sro.application.observation.mining_pass import MineResult
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap
from sro.domain.shared.identifiers import PrincipalId

__all__ = ["MineLately"]

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

    def __init__(self, uow: UnitOfWork, pass_: MinePass, *, window_hours: int) -> None:
        self._uow = uow
        self._pass = pass_
        self._window_hours = window_hours

    async def execute(self, *, now: datetime) -> dict[str, MineResult]:
        since = now - timedelta(hours=self._window_hours)
        async with self._uow as uow:
            tenants = await uow.gestures.tenants_since(since)

        mined: dict[str, MineResult] = {}
        for tenant_id in tenants:
            ctx = RequestContext(tenant_id=tenant_id, principal_id=PrincipalId("miner"))
            try:
                mined[tenant_id.value] = await self._pass.execute(ctx)
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
