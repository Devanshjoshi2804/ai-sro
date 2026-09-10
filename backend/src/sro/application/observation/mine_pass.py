"""One mining pass, asked for from outside the process.

`mining_pass.mine` had no caller in `src/` at all: every mining result this
project has measured came from a script somebody ran by hand. This is the seam
a route can reach it through.
"""

from __future__ import annotations

from datetime import datetime

from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.observation.mining_pass import MineResult, mine
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap

__all__ = ["MinePass"]


class MinePass:
    """Read this tenant's day, once, and bill it.

    A class where ``mine`` is a bare function, for the reason
    ``container.record_offer`` is one: ``mine`` takes a bare ``tenant_id``, and
    a route calling it would unpack the caller itself at the one seam where
    passing the wrong tenant is the failure. ``now`` is taken from the
    container's clock here for the same reason ``Container.read_spend`` takes
    it there -- which day is being billed is not a decision a route may make.

    Both refusals happen here rather than inside ``mine``. ``mine`` takes an
    ``Asker`` and cannot be given ``None``; and its own cap check
    (``mining_pass.py:296``) returns a ``MineResult`` carrying the reason,
    which is right for a pass that got as far as trying and wrong for a request
    that should never have been admitted -- a caller hammering the door would
    get 200s describing its own refusals. Raised here, the door answers 503 and
    429, which is what those two facts are.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        *,
        asker: Asker | None,
        model: str,
        clock: Clock,
        cap_usd: float,
    ) -> None:
        self._uow = uow
        self._asker = asker
        self._model = model
        self._clock = clock
        self._cap_usd = cap_usd

    async def execute(self, ctx: RequestContext) -> MineResult:
        # Before the session is opened and long before a window is packed:
        # neither refusal needs a database, and a 503 that first took a
        # connection is a 503 that made the outage slightly worse.
        asker = asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        # One session, entered here. `mine`'s docstring: "`uow` is already
        # open: the pass commits its own writes and never enters or leaves the
        # block, so the caller owns the session." A second unit of work for
        # the cap check would be a repository read off a `SqlUnitOfWork`
        # nobody entered, which is `50864cf` -- green in every unit test and
        # an AttributeError against real Postgres.
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            return await mine(
                uow,
                tenant_id=ctx.tenant_id,
                asker=asker,
                model=self._model,
                now=now,
                cap_usd=self._cap_usd,
            )
