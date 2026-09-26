from __future__ import annotations

from datetime import datetime

from sro.application.chat.understand import Understood, read_utterance
from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap

__all__ = ["ReadChat"]


class ReadChat:
    def __init__(
        self,
        uow: UnitOfWork,
        *,
        asker: Asker | None,
        clock: Clock,
        cap_usd: float,
    ) -> None:
        self._uow = uow
        self._asker = asker
        self._clock = clock
        self._cap_usd = cap_usd

    async def execute(self, ctx: RequestContext, *, utterance: str) -> Understood:
        asker = asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            return await read_utterance(
                uow,
                tenant_id=ctx.tenant_id,
                utterance=utterance,
                asker=asker,
                now=now,
            )
