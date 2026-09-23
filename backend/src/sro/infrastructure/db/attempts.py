from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import AttemptRepository
from sro.domain.observation.attempts import Attempt, as_row
from sro.domain.shared.identifiers import TenantId
from sro.infrastructure.db.codec import when
from sro.infrastructure.db.models import AttemptRow

logger = logging.getLogger(__name__)


class SqlAttemptRepository(AttemptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, attempt: Attempt) -> None:
        row = as_row(attempt)
        try:
            self._session.add(
                AttemptRow(
                    id=row["id"],
                    tenant_id=row["tenant_id"],
                    at=when(str(row["at"])),
                    principal=row["principal"],
                    asked_for=row["asked_for"],
                    came_of=row["came_of"],
                    why=row["why"],
                    about=row["about"],
                )
            )
            await self._session.flush()
        except Exception:
            logger.exception(
                "an attempt could not be recorded: %s came to %s",
                attempt.asked_for,
                attempt.came_of,
            )

    async def since(
        self, tenant_id: TenantId, *, since: datetime, limit: int
    ) -> tuple[Attempt, ...]:
        rows = (
            (
                await self._session.execute(
                    select(AttemptRow)
                    .where(AttemptRow.tenant_id == tenant_id.value, AttemptRow.at >= since)
                    .order_by(AttemptRow.at.desc(), AttemptRow.seq.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return tuple(
            Attempt(
                id=row.id,
                tenant=row.tenant_id,
                at=row.at.isoformat(),
                asked_for=row.asked_for,
                came_of=row.came_of,
                principal=row.principal,
                why=row.why,
                about=dict(row.about or {}),
            )
            for row in rows
        )


__all__ = ["SqlAttemptRepository"]
