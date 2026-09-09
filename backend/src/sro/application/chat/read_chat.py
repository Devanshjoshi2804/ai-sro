"""One sentence, read from outside the process.

`read_utterance` had no caller in `src/` at all: the ported chat reader was
reachable only from its own test, and every offer it has ever made came from a
script somebody ran by hand. This is the seam a route can reach it through.

**Not `POST /v1/intent/resolve`.** That one resolves an utterance over the
tenant's *skills*, arithmetic and no model. This one resolves over the
*workflows* a mining pass read out of what an operator was seen doing, and it
spends money doing it. Two resolvers, two vocabularies, one verb between them.
"""

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
    """Read one operator's sentence against this tenant's jobs, and bill it.

    ``MinePass``'s twin and deliberately not its subclass: the two share two
    refusals and nothing else. Mining takes no input from its caller and this
    takes a sentence, and a base class holding two refusals would be an
    abstraction over a coincidence.

    A class where ``read_utterance`` is a bare function, for ``MinePass``'s
    reason: ``read_utterance`` takes a bare ``tenant_id``, and a route calling
    it would unpack the caller itself at the one seam where passing the wrong
    tenant reads somebody else's jobs. ``now`` is taken from the container's
    clock here rather than in the route, because which day is being billed is
    not a decision a route may make.

    Both refusals happen here rather than inside ``read_utterance``. That
    function takes an ``Asker`` and cannot be given ``None``; and it writes a
    ``chats`` row for every reading it makes, refusal included -- so a cap
    checked after it would bill a row for a call the tenant was just told it
    could not make, and a caller hammering the door would fill the very table
    the cap is summed from. Raised here, the door answers 503 and 429, which is
    what those two facts are.
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

    async def execute(self, ctx: RequestContext, *, utterance: str) -> Understood:
        # Before the session is opened: neither refusal needs a database, and a
        # 503 that first took a connection is a 503 that made the outage
        # slightly worse.
        asker = asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        # One session, entered here. `read_utterance` reads the workflows and
        # commits the bill through the `uow` it is handed and never enters or
        # leaves the block, so the caller owns the session. A second unit of
        # work for the cap check would be a repository read off a
        # `SqlUnitOfWork` nobody entered, which is `50864cf` -- green in every
        # unit test and an AttributeError against real Postgres.
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            return await read_utterance(
                uow,
                tenant_id=ctx.tenant_id,
                utterance=utterance,
                asker=asker,
                model=self._model,
                now=now,
            )
