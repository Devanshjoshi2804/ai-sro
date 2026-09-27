from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import ColumnElement, Update, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sro.application.ports.repositories import GestureRepository, PoolRepository
from sro.domain.observation.driving import Uploaded
from sro.domain.observation.gesture import (
    Action,
    Call,
    Gesture,
    GestureBatch,
    Intent,
    PageMark,
    ValueSeen,
)
from sro.domain.observation.pool import (
    K_MINE_ATTEMPTS,
    K_POOL_AGE,
    K_POOL_DAYS,
    RETIRED_PASSES,
    RETIRED_STALE,
    RETIRED_UNMINABLE,
    PoolEntry,
)
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import TenantId
from sro.infrastructure.db.codec import dump, when
from sro.infrastructure.db.models import (
    GestureBatchRow,
    GestureRow,
    IntentRow,
    OrphanPageRow,
    OrphanRequestRow,
    PoolRow,
)

_ACTION = TypeAdapter(Action)
_CALLS = TypeAdapter(list[Call])
_PAGE_MARKS = TypeAdapter(list[PageMark])
_VALUES_SEEN = TypeAdapter(list[ValueSeen])


def _gesture_to_row(gesture: Gesture) -> GestureRow:
    return GestureRow(
        id=gesture.id,
        tenant_id=gesture.tenant,
        stream_id=gesture.stream_id,
        batch_id=gesture.batch_id,
        at=gesture.at,
        url=gesture.url,
        system=gesture.system,
        tab_id=gesture.tab_id,
        frame_url=gesture.frame_url,
        page_url=gesture.page_url,
        gesture=dump(_ACTION, gesture.action),
        requests=dump(_CALLS, gesture.requests),
        page_events=dump(_PAGE_MARKS, gesture.page_events),
    )


def _row_to_gesture(row: GestureRow) -> Gesture:
    return Gesture(
        id=row.id,
        tenant=row.tenant_id,
        stream_id=row.stream_id,
        batch_id=row.batch_id,
        at=row.at,
        url=row.url,
        system=row.system,
        tab_id=row.tab_id,
        frame_url=row.frame_url,
        page_url=row.page_url,
        action=_ACTION.validate_python(row.gesture),
        requests=_CALLS.validate_python(row.requests or []),
        page_events=_PAGE_MARKS.validate_python(row.page_events or []),
    )


def _intent_values(intent: Intent, *, created_at: datetime) -> dict[str, Any]:
    return {
        "gesture_id": intent.gesture_id,
        "tenant_id": intent.tenant,
        "act": intent.act,
        "object_": intent.object,
        "page": intent.page,
        "values_seen": dump(_VALUES_SEEN, intent.values_seen),
        "confidence": intent.confidence,
        "why": intent.why,
        "model": intent.model,
        "in_tokens": intent.in_tokens,
        "out_tokens": intent.out_tokens,
        "thought_tokens": intent.thought_tokens,
        "cost_usd": intent.cost_usd,
        "unpriced": intent.unpriced,
        "created_at": created_at,
        "error": intent.error,
    }


def _row_to_intent(row: IntentRow) -> Intent:
    return Intent(
        gesture_id=row.gesture_id,
        tenant=row.tenant_id,
        act=row.act,
        object=row.object_,
        page=row.page,
        values_seen=_VALUES_SEEN.validate_python(row.values_seen or []),
        confidence=row.confidence,
        why=row.why,
        model=row.model,
        in_tokens=row.in_tokens,
        out_tokens=row.out_tokens,
        thought_tokens=row.thought_tokens,
        cost_usd=row.cost_usd,
        unpriced=row.unpriced,
        error=row.error,
    )


def _when(said: str) -> datetime | None:
    try:
        return datetime.fromisoformat(said) if said else None
    except ValueError:
        return None


class SqlGestureRepository(GestureRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_batch(self, batch: GestureBatch) -> None:
        self._session.add(
            GestureBatchRow(
                batch_id=batch.batch_id,
                tenant_id=batch.tenant,
                device_id=batch.device_id,
                mode=batch.mode,
                started_at=batch.started_at,
                ended_at=batch.ended_at,
                recording_id=batch.recording_id,
                received_at=when(batch.received_at),
                accepted=batch.accepted,
                rejected=batch.rejected,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"gesture batch {batch.batch_id} is already stored") from clash

    async def add_gestures(self, gestures: tuple[Gesture, ...]) -> None:
        self._session.add_all([_gesture_to_row(gesture) for gesture in gestures])
        try:
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict("one of these gestures is already stored") from clash

    async def gestures_for(
        self,
        tenant_id: TenantId,
        *,
        ids: tuple[str, ...] | None = None,
        after: float | None = None,
        before: float | None = None,
        stream_id: str | None = None,
    ) -> tuple[Gesture, ...]:
        query = select(GestureRow).where(GestureRow.tenant_id == tenant_id.value)
        if stream_id is not None:
            query = query.where(GestureRow.stream_id == stream_id)
        if ids is not None:
            query = query.where(GestureRow.id.in_(ids))
        if after is not None:
            query = query.where(GestureRow.at > after)
        if before is not None:
            query = query.where(GestureRow.at <= before)
        rows = (
            (await self._session.execute(query.order_by(GestureRow.at, GestureRow.id)))
            .scalars()
            .all()
        )
        return tuple(_row_to_gesture(row) for row in rows)

    async def uploads_for(
        self, tenant_id: TenantId, batch_ids: tuple[str, ...]
    ) -> Mapping[str, Uploaded]:
        if not batch_ids:
            return {}
        rows = (
            (
                await self._session.execute(
                    select(GestureBatchRow).where(
                        GestureBatchRow.tenant_id == tenant_id.value,
                        GestureBatchRow.batch_id.in_(batch_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        return {
            row.batch_id: Uploaded(
                device_id=row.device_id,
                ended_at=_when(row.ended_at),
                received_at=row.received_at,
            )
            for row in rows
        }

    async def unread(self, tenant_id: TenantId, *, limit: int) -> tuple[Gesture, ...]:
        query = (
            select(GestureRow)
            .outerjoin(IntentRow, IntentRow.gesture_id == GestureRow.id)
            .where(IntentRow.gesture_id.is_(None), GestureRow.tenant_id == tenant_id.value)
            .order_by(GestureRow.at, GestureRow.id)
            .limit(limit)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(_row_to_gesture(row) for row in rows)

    async def newest_arrival(self, tenant_id: TenantId) -> datetime | None:
        carried = (
            select(GestureRow.id).where(GestureRow.batch_id == GestureBatchRow.batch_id).exists()
        )
        newest: datetime | None = await self._session.scalar(
            select(func.max(GestureBatchRow.received_at)).where(
                GestureBatchRow.tenant_id == tenant_id.value, carried
            )
        )
        return newest

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]:
        carried = (
            select(GestureRow.id).where(GestureRow.batch_id == GestureBatchRow.batch_id).exists()
        )
        rows = await self._session.execute(
            select(GestureBatchRow.tenant_id)
            .where(GestureBatchRow.received_at >= since, carried)
            .distinct()
        )
        return tuple(TenantId(tenant) for tenant in rows.scalars())

    async def save_intent(self, intent: Intent) -> None:
        values = _intent_values(intent, created_at=datetime.now(tz=UTC))
        statement = pg_insert(IntentRow).values(**values)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["gesture_id"],
                set_={
                    column.name: statement.excluded[column.name]
                    for attribute in IntentRow.__mapper__.column_attrs
                    if attribute.key in values and attribute.key != "gesture_id"
                    for column in attribute.columns
                },
            )
        )

    async def intents_for(
        self, tenant_id: TenantId, *, ids: tuple[str, ...] | None = None
    ) -> tuple[Intent, ...]:
        query = (
            select(IntentRow)
            .where(IntentRow.tenant_id == tenant_id.value)
            .execution_options(populate_existing=True)
        )
        if ids is not None:
            query = query.where(IntentRow.gesture_id.in_(ids))
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(_row_to_intent(row) for row in rows)

    async def intents_since(self, tenant_id: TenantId, *, since: str) -> tuple[Intent, ...]:
        query = (
            select(IntentRow)
            .where(IntentRow.tenant_id == tenant_id.value, IntentRow.created_at >= when(since))
            .order_by(IntentRow.created_at.desc(), IntentRow.gesture_id.desc())
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(_row_to_intent(row) for row in rows)

    async def add_orphan_request(
        self,
        tenant_id: TenantId,
        *,
        batch_id: str,
        request_id: str,
        payload: Mapping[str, object],
    ) -> None:
        await self._session.execute(
            pg_insert(OrphanRequestRow)
            .values(
                batch_id=batch_id,
                request_id=request_id,
                tenant_id=tenant_id.value,
                payload=dict(payload),
            )
            .on_conflict_do_nothing(index_elements=["batch_id", "request_id"])
        )

    async def add_orphan_page(
        self, tenant_id: TenantId, *, batch_id: str, at: str, payload: Mapping[str, object]
    ) -> None:
        self._session.add(
            OrphanPageRow(
                batch_id=batch_id, tenant_id=tenant_id.value, at=at, payload=dict(payload)
            )
        )

    async def batch_owner(self, batch_id: str) -> str | None:
        owner: str | None = await self._session.scalar(
            select(GestureBatchRow.device_id).where(GestureBatchRow.batch_id == batch_id)
        )
        return owner

    async def count(self, tenant_id: TenantId) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(GestureRow)
            .where(GestureRow.tenant_id == tenant_id.value)
        )
        return int(total or 0)

    async def streams(self, tenant_id: TenantId) -> tuple[tuple[str, float, int], ...]:
        last = func.max(GestureRow.at)
        query = (
            select(GestureRow.stream_id, last, func.count())
            .where(GestureRow.tenant_id == tenant_id.value)
            .group_by(GestureRow.stream_id)
            .order_by(last.desc(), GestureRow.stream_id)
        )
        rows = (await self._session.execute(query)).all()
        return tuple((stream_id, float(at), int(many)) for stream_id, at, many in rows)


class SqlPoolRepository(PoolRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_unclaimed(
        self, tenant_id: TenantId, *, window_ids: tuple[str, ...], claimed: frozenset[str]
    ) -> int:
        if claimed:
            await self._session.execute(
                delete(PoolRow)
                .where(PoolRow.tenant_id == tenant_id.value, PoolRow.gesture_id.in_(claimed))
                .execution_options(synchronize_session=False)
            )
        entering = [
            gesture_id for gesture_id in dict.fromkeys(window_ids) if gesture_id not in claimed
        ]
        if not entering:
            return 0
        now = datetime.now(tz=UTC)
        statement = pg_insert(PoolRow).values(
            [
                {
                    "tenant_id": tenant_id.value,
                    "gesture_id": gesture_id,
                    "age": 0,
                    "waited": 0,
                    "retired": False,
                    "reason": "",
                    "entered_at": now,
                }
                for gesture_id in entering
            ]
        )
        added = await self._session.execute(
            statement.on_conflict_do_nothing(index_elements=["tenant_id", "gesture_id"]).returning(
                PoolRow.gesture_id
            )
        )
        return len(added.all())

    async def age(
        self, tenant_id: TenantId, *, shown: tuple[str, ...] | None = None, failed: bool = False
    ) -> int:
        live: tuple[ColumnElement[bool], ...] = (
            PoolRow.tenant_id == tenant_id.value,
            PoolRow.retired.is_(False),
        )
        if shown is None:
            await self._session.execute(
                self._bump(*live, age=PoolRow.age + 1),
            )
        else:
            ids = tuple(dict.fromkeys(shown))
            if not ids:
                await self._session.execute(self._bump(*live, waited=PoolRow.waited + 1))
            else:
                await self._session.execute(
                    self._bump(
                        *live,
                        PoolRow.gesture_id.in_(ids),
                        **(
                            {"failed": PoolRow.failed + 1}
                            if failed
                            else {"age": PoolRow.age + 1, "waited": 0}
                        ),
                    )
                )
                if not failed:
                    await self._session.execute(
                        self._bump(*live, PoolRow.gesture_id.notin_(ids), waited=PoolRow.waited + 1)
                    )

        passes = await self._session.execute(
            self._bump(
                *live, PoolRow.age > K_POOL_AGE, retired=True, reason=RETIRED_PASSES
            ).returning(PoolRow.gesture_id)
        )
        stale = await self._session.execute(
            self._bump(
                *live,
                PoolRow.age > 0,
                PoolRow.entered_at < datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS),
                retired=True,
                reason=RETIRED_STALE,
            ).returning(PoolRow.gesture_id)
        )
        unminable = await self._session.execute(
            self._bump(
                *live,
                PoolRow.failed >= K_MINE_ATTEMPTS,
                retired=True,
                reason=RETIRED_UNMINABLE,
            ).returning(PoolRow.gesture_id)
        )
        return len(passes.all()) + len(stale.all()) + len(unminable.all())

    async def waiting(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        return await self._entries(tenant_id, retired=False)

    async def ids(self, tenant_id: TenantId) -> tuple[str, ...]:
        return tuple(entry.gesture_id for entry in await self.waiting(tenant_id))

    async def retired(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        return await self._entries(tenant_id, retired=True)

    async def retire(
        self, tenant_id: TenantId, gesture_ids: tuple[str, ...], *, reason: str
    ) -> int:
        gone = await self._session.execute(
            self._bump(
                PoolRow.tenant_id == tenant_id.value,
                PoolRow.retired.is_(False),
                PoolRow.gesture_id.in_(gesture_ids),
                retired=True,
                reason=reason,
            ).returning(PoolRow.gesture_id)
        )
        return len(gone.all())

    @staticmethod
    def _bump(*where: ColumnElement[bool], **values: Any) -> Update:
        return (
            update(PoolRow)
            .where(*where)
            .values(**values)
            .execution_options(synchronize_session=False)
        )

    async def _entries(self, tenant_id: TenantId, *, retired: bool) -> tuple[PoolEntry, ...]:
        query = (
            select(
                PoolRow.gesture_id,
                PoolRow.tenant_id,
                PoolRow.age,
                PoolRow.entered_at,
                PoolRow.reason,
                PoolRow.waited,
                PoolRow.failed,
            )
            .where(PoolRow.tenant_id == tenant_id.value, PoolRow.retired.is_(retired))
            .order_by(PoolRow.entered_at, PoolRow.gesture_id)
        )
        rows = (await self._session.execute(query)).all()
        return tuple(
            PoolEntry(
                gesture_id=gesture_id,
                tenant=tenant,
                age=age,
                entered_at=entered_at.isoformat(),
                reason=reason,
                waited=waited,
                failed=failed,
            )
            for gesture_id, tenant, age, entered_at, reason, waited, failed in rows
        )
