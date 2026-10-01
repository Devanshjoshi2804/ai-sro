from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import FeedbackRepository
from sro.domain.chat.feedback import Feedback
from sro.domain.shared.identifiers import TenantId
from sro.infrastructure.db.models import ChatFeedbackRow


def _feedback(row: ChatFeedbackRow) -> Feedback:
    return Feedback(
        id=row.id,
        tenant=row.tenant_id,
        operator=row.operator,
        thread_id=row.thread_id,
        message_id=row.message_id,
        kind=row.kind,
        created_at=row.created_at,
        said=row.said,
        brain=dict(row.brain or {}),
        other=dict(row.other or {}),
        status=row.status,
        note=row.note,
    )


class SqlFeedbackRepository(FeedbackRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, one: Feedback) -> bool:
        taken = await self._session.execute(
            insert(ChatFeedbackRow)
            .values(
                id=one.id,
                tenant_id=one.tenant,
                operator=one.operator,
                thread_id=one.thread_id,
                message_id=one.message_id,
                kind=one.kind,
                said=one.said,
                brain=one.brain,
                other=one.other,
                status=one.status,
                note=one.note,
                created_at=one.created_at,
            )
            .on_conflict_do_nothing(index_elements=["tenant_id", "message_id", "kind"])
            .returning(ChatFeedbackRow.id)
        )
        return taken.scalar_one_or_none() is not None

    async def get(self, tenant_id: TenantId, feedback_id: str) -> Feedback | None:
        row = (
            await self._session.execute(
                select(ChatFeedbackRow).where(
                    ChatFeedbackRow.tenant_id == tenant_id.value, ChatFeedbackRow.id == feedback_id
                )
            )
        ).scalar_one_or_none()
        return _feedback(row) if row is not None else None

    async def newest(
        self,
        tenant_id: TenantId,
        *,
        statuses: Sequence[str] = (),
        kind: str = "",
        since: datetime | None = None,
        limit: int,
    ) -> tuple[Feedback, ...]:
        where = [ChatFeedbackRow.tenant_id == tenant_id.value]
        if statuses:
            where.append(ChatFeedbackRow.status.in_(statuses))
        if kind:
            where.append(ChatFeedbackRow.kind == kind)
        if since is not None:
            where.append(ChatFeedbackRow.created_at >= since)
        rows = (
            (
                await self._session.execute(
                    select(ChatFeedbackRow)
                    .where(*where)
                    .order_by(ChatFeedbackRow.created_at.desc(), ChatFeedbackRow.seq.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return tuple(_feedback(row) for row in rows)

    async def mark(self, tenant_id: TenantId, feedback_id: str, *, status: str, note: str) -> bool:
        done = await self._session.execute(
            update(ChatFeedbackRow)
            .where(ChatFeedbackRow.tenant_id == tenant_id.value, ChatFeedbackRow.id == feedback_id)
            .values(status=status, note=note)
            .returning(ChatFeedbackRow.id)
        )
        return done.scalar_one_or_none() is not None


__all__ = ["SqlFeedbackRepository"]
