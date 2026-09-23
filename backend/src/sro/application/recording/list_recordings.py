from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.domain.recording.recording import Recording
from sro.domain.shared.objective import ObjectiveKey


class ListRecordings:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        ctx: RequestContext,
        *,
        objective_key: ObjectiveKey | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Recording, ...]:
        async with self._uow as uow:
            return await uow.recordings.list_for_tenant(
                ctx.tenant_id, objective_key=objective_key, limit=limit, offset=offset
            )
