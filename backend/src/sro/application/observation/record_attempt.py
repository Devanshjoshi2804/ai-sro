"""Writing down what somebody asked for, from the door that answered them.

The domain says what an attempt is. This is the one way to make one, and it
exists so that a door can record one in a single line while it is busy doing
something else -- because the doors that most need to are the ones in the
middle of refusing somebody, and a recorder that takes five lines and a
transaction is a recorder that does not get called.

**It cannot fail the thing it records.** The repository swallows and logs its
own errors, and this adds the other half: a caller passing something the
domain refuses gets it written down as a fault here rather than raised into a
door that was already answering. Nothing this returns is ever checked, and
nothing in this system's behaviour reads the table.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.observation.attempts import Attempt

logger = logging.getLogger(__name__)

ABOUT = ("run", "workflow", "thread", "device", "offer", "trigger", "command")
"""What an attempt may name. The telemetry plane's list, for its reason: this
row leaves the tenant's deployment whenever somebody exports an audit, and a
bag that can hold anything ends up holding what a customer is called."""


class RecordAttempt:
    def __init__(self, uow: UnitOfWork, ids: IdFactory, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    async def execute(
        self,
        ctx: RequestContext,
        *,
        asked_for: str,
        came_of: str,
        why: str = "",
        about: Mapping[str, str] | None = None,
    ) -> None:
        """One attempt, written where a person can read it back.

        `ctx` supplies who: the tenant it belongs to and the principal who
        asked. A door with no person behind it -- a trigger firing on its own
        schedule -- passes the tenant's own context and the principal comes out
        whatever that context carries, which is the honest answer rather than a
        name invented here.
        """
        try:
            attempt = Attempt(
                id=f"att_{self._ids.new_run_id().value.split('_', 1)[-1]}",
                tenant=ctx.tenant_id.value,
                at=self._clock.now().isoformat(),
                asked_for=asked_for,
                came_of=came_of,
                principal=ctx.principal_id.value,
                why=why,
                about={
                    key: str(value)
                    for key, value in (about or {}).items()
                    if key in ABOUT and value
                },
            )
        except Exception:
            # A door asking for an outcome this system does not recognise is a
            # bug in that door, and it is not one the person in front of it
            # should be told about by a 500.
            logger.exception("an attempt could not be made: %s came to %s", asked_for, came_of)
            return
        async with self._uow as uow:
            await uow.attempts.record(attempt)


__all__ = ["ABOUT", "RecordAttempt"]
