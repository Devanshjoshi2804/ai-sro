from __future__ import annotations

import logging
from collections.abc import Mapping

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock, IdFactory
from sro.domain.observation.attempts import Attempt

logger = logging.getLogger(__name__)

ABOUT = ("run", "workflow", "thread", "device", "offer", "trigger", "command")


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
            logger.exception("an attempt could not be made: %s came to %s", asked_for, came_of)
            return
        async with self._uow as uow:
            await uow.attempts.record(attempt)
            await uow.commit()


__all__ = ["ABOUT", "RecordAttempt"]
