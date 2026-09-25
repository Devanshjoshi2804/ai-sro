from __future__ import annotations

from datetime import datetime

from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.observation.mining_pass import MineResult, mine
from sro.application.ports.locks import AccountLocks
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap

__all__ = ["MinePass"]


class MinePass:
    def __init__(
        self,
        uow: UnitOfWork,
        *,
        asker: Asker | None,
        locks: AccountLocks,
        model: str,
        clock: Clock,
        cap_usd: float,
        ours: frozenset[str] = frozenset(),
    ) -> None:
        self._uow = uow
        self._asker = asker
        self._locks = locks
        self._model = model
        self._clock = clock
        self._cap_usd = cap_usd
        self._ours = ours

    async def execute(self, ctx: RequestContext) -> MineResult:
        asker = asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            return await mine(
                uow,
                tenant_id=ctx.tenant_id,
                asker=asker,
                locks=self._locks,
                model=self._model,
                now=now,
                cap_usd=self._cap_usd,
                ours=self._ours,
            )
