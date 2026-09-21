"""Attempts, written and read back.

The domain's own module says what an attempt is and why one exists. This is
the half that touches a database, and the only thing it adds is a rule the
port states and this has to keep: **recording an attempt never raises.**

Every caller is a door in the middle of answering somebody, and most of them
are in the middle of refusing somebody. A refusal that becomes a 500 because
the recording of it failed is strictly worse than the silence this replaces --
the operator loses the sentence that told them what was wrong, and gains an
outage.
"""

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
            # Broad on purpose, and said out loud rather than swallowed: the
            # log is where this fact lives anyway, so a table that will not
            # take it loses the durable copy and not the fact itself.
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
                    # `at` then arrival, which is `offers`' rule and for its
                    # reason: several attempts share a second, and a day read
                    # from the end needs "newest" to be a total order.
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
