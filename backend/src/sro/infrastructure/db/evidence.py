"""The evidence plane on Postgres: gestures, their readings, and the pool.

The rules here are the rig's, and they were SQLite there. Three of them had to
be translated rather than copied, and each translation is marked where it
happens:

* ``INSERT OR IGNORE`` and ``INSERT OR REPLACE`` become ``ON CONFLICT DO
  NOTHING`` and ``ON CONFLICT DO UPDATE`` on a named conflict target. SQLite's
  forms swallow *every* constraint; naming the target means a different
  constraint failing is still an error rather than a silent no-op.
* ``orphan_pages`` keyed on SQLite's ``rowid`` alias becomes a bigserial
  identity. It is a surrogate either way, and the reason it is one is that two
  distinct page events can share a batch, an instant and a payload.
* The empty-``shown`` branch of ``age`` stays spelled out. ``gesture_id NOT IN
  ()`` is not a predicate that matches everything -- under three-valued logic
  it matches nothing -- so a pass that packed no evidence would leave every
  entry's waiting frozen, which is the failure the second clock exists to
  prevent.

The row-to-record mapping lives here rather than in ``mappers.py``: a
repository's mapping belongs with the repository, and there are four shapes
here that nothing else reads.
"""

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
    K_POOL_AGE,
    K_POOL_DAYS,
    RETIRED_PASSES,
    RETIRED_STALE,
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
        "continues": intent.continues,
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
        continues=row.continues,
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
    """A device's own timestamp, as it sent it, or nothing.

    Empty for uploads from before the protocol carried both clocks, and
    `fromisoformat` is strict: what it cannot read is a clock this cannot
    reason about, which is not an error -- it is one gesture left alone.
    """
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
            # Flushed here rather than at commit, and before the gestures are
            # added: whether this upload is a retry has to be settled before
            # anything it carries is written, and a claim the rest of the block
            # then fails to follow rolls back with it. An id claimed but never
            # followed by its gestures can never be retried -- the events it
            # named are gone, and the id says they were handled.
            await self._session.flush()
        except IntegrityError as clash:
            await self._session.rollback()
            raise Conflict(f"gesture batch {batch.batch_id} is already stored") from clash

    async def add_gestures(self, gestures: tuple[Gesture, ...]) -> None:
        self._session.add_all([_gesture_to_row(gesture) for gesture in gestures])
        try:
            # Flushed and translated here for ``add_batch``'s reason and one
            # more: a gesture id already stored is a retried upload the batch
            # claim did not catch, and doubling a tenant's evidence is exactly
            # what that claim exists to stop. The caller has to hear it as a
            # ``Conflict`` rather than as whatever the driver raises at commit
            # -- and that is the only shape a fake can be held to.
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
    ) -> tuple[Gesture, ...]:
        query = select(GestureRow).where(GestureRow.tenant_id == tenant_id.value)
        if ids is not None:
            query = query.where(GestureRow.id.in_(ids))
        if after is not None:
            query = query.where(GestureRow.at > after)
        if before is not None:
            query = query.where(GestureRow.at <= before)
        # The id breaks a tie the rig left open: `at` is the browser's clock in
        # milliseconds and two gestures of one burst share it, so `at` alone is
        # not a total order -- and in `unread` below, where the order decides
        # which 200 are read, that is a different set rather than a different
        # order.
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
                # Kept as the device sent it, which is a string and may be
                # empty: uploads predating the two clocks carry neither, and a
                # batch that cannot say what its clock was doing is one nothing
                # here will guess about.
                ended_at=_when(row.ended_at),
                received_at=row.received_at,
            )
            for row in rows
        }

    async def unread(self, tenant_id: TenantId, *, limit: int) -> tuple[Gesture, ...]:
        # A gesture that was read is never offered again, error or not: the
        # model was asked, it answered, and it was billed. Re-asking the same
        # evidence with the same prompt bills again for the same likely answer.
        query = (
            select(GestureRow)
            .outerjoin(IntentRow, IntentRow.gesture_id == GestureRow.id)
            .where(IntentRow.gesture_id.is_(None), GestureRow.tenant_id == tenant_id.value)
            .order_by(GestureRow.at, GestureRow.id)
            .limit(limit)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(_row_to_gesture(row) for row in rows)

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]:
        # ``received_at`` and not ``ended_at``: the first is when this process
        # took the upload and the second is the device's own clock, kept as a
        # string exactly as it was sent. A browser with a wrong clock would
        # otherwise take its tenant out of every sweep or put it in every one.
        #
        # **Batches that carried something.** A watching extension uploads on
        # its timer whether or not anybody did anything, so an idle browser
        # posts an empty batch a minute, forever. `MineLately` reads this to
        # ask "is this tenant mid-task", and an empty heartbeat answered yes --
        # so a tenant was `still working; leaving this one to settle` for as
        # long as the browser stayed connected, and mining never ran at all
        # while the product was in use. Seen on the QA deployment: fifty-four
        # gestures captured, five empty batches after them, and nothing mined
        # five minutes later.
        #
        # An `exists` rather than a join: one row per tenant is wanted, and a
        # join would multiply by the gestures before the `distinct` took them
        # away again.
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
        # ``created_at`` is the server's, taken here rather than carried on the
        # record: it is when the reading was stored, and the spend window is
        # summed over it.
        statement = pg_insert(IntentRow).values(
            **_intent_values(intent, created_at=datetime.now(tz=UTC))
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["gesture_id"],
                # Every column but the key takes the new reading's value, which
                # is what INSERT OR REPLACE did: a second reading of one
                # gesture supersedes the first rather than sitting beside it.
                set_={
                    column.name: statement.excluded[column.name]
                    for column in IntentRow.__table__.columns
                    if column.name != "gesture_id"
                },
            )
        )

    async def intents_for(self, tenant_id: TenantId) -> tuple[Intent, ...]:
        query = (
            select(IntentRow)
            .where(IntentRow.tenant_id == tenant_id.value)
            # The upsert above is a Core statement, so a row this session had
            # already loaded would otherwise come back at its old reading.
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return tuple(_row_to_intent(row) for row in rows)

    async def intents_since(self, tenant_id: TenantId, *, since: str) -> tuple[Intent, ...]:
        query = (
            select(IntentRow)
            .where(IntentRow.tenant_id == tenant_id.value, IntentRow.created_at >= when(since))
            # The gesture id breaks the tie: ``created_at`` is the server
            # clock inside ``save_intent`` and a batch of readings saved in one
            # call routinely shares it, so the clock alone is not a total order
            # -- and an order that is not total is one that changes between
            # reads of the same rows.
            .order_by(IntentRow.created_at.desc(), IntentRow.gesture_id.desc())
            # The reading a caller has just saved is the one it is most likely
            # to be reading back, and ``save_intent`` upserts with a Core
            # statement -- so, as in ``intents_for``, the identity map must not
            # hand back the reading this session superseded.
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
        # No dedup key, unlike its sibling above: two distinct page events can
        # share a batch, an instant and a payload, and the batch's own primary
        # key already makes re-ingesting a batch a no-op.
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
            # The stream id breaks the tie: two streams whose last gesture
            # shares an instant would otherwise swap places between reads.
            .order_by(last.desc(), GestureRow.stream_id)
        )
        rows = (await self._session.execute(query)).all()
        return tuple((stream_id, float(at), int(many)) for stream_id, at, many in rows)


class SqlPoolRepository(PoolRepository):
    """The rig's ``pool`` module, one storage layer down.

    Live and retired are two reads because a retired entry is still a row: it
    stops being offered ahead of fresh evidence and goes on being packed on its
    own merits, so nothing here ever deletes one. The only entry that leaves is
    one a pass cited, and it leaves because it was placed.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_unclaimed(
        self, tenant_id: TenantId, *, window_ids: tuple[str, ...], claimed: frozenset[str]
    ) -> int:
        if claimed:
            # In full, not only where it intersects the window. A pooled
            # gesture is packed beside the fresh ones, so a pass can cite
            # evidence that is already in the pool -- and clearing only the
            # intersection would leave that citation to age out and retire
            # despite having been placed.
            await self._session.execute(
                delete(PoolRow)
                .where(PoolRow.tenant_id == tenant_id.value, PoolRow.gesture_id.in_(claimed))
                # ``synchronize_session=False`` for the same reason ``_bump``
                # gives: no PoolRow is ever loaded as an ORM object here, so
                # there is no session state to keep in step and asking for one
                # only buys a SELECT of the rows about to go.
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
        # DO NOTHING, the rig's OR IGNORE: a gesture that has sat unplaced
        # through three passes keeps the age those passes gave it. Re-entering
        # must not reset the clock, or nothing in a recurring window ever
        # retires -- and it leaves a retired row retired, which is a decision.
        # RETURNING rather than rowcount, because how many actually entered is
        # the answer, and it is what the caller reports.
        added = await self._session.execute(
            statement.on_conflict_do_nothing(index_elements=["tenant_id", "gesture_id"]).returning(
                PoolRow.gesture_id
            )
        )
        return len(added.all())

    async def age(self, tenant_id: TenantId, *, shown: tuple[str, ...] | None = None) -> int:
        live: tuple[ColumnElement[bool], ...] = (
            PoolRow.tenant_id == tenant_id.value,
            PoolRow.retired.is_(False),
        )
        if shown is None:
            # No window named is not the same as an empty one: a caller with no
            # window is not claiming nothing was read.
            await self._session.execute(
                self._bump(*live, age=PoolRow.age + 1),
            )
        else:
            ids = tuple(dict.fromkeys(shown))
            if not ids:
                # Spelled out rather than folded into the general case.
                # ``gesture_id NOT IN ()`` matches nothing under three-valued
                # logic, so a pass that packed no evidence would have frozen
                # every entry's waiting -- the "the day did not rotate" failure
                # the second clock exists to prevent, behind a branch nobody
                # reads. A pass that packs nothing is exactly when the pool
                # most needs to record that nobody was seen.
                await self._session.execute(self._bump(*live, waited=PoolRow.waited + 1))
            else:
                # Shown: one reading older, and its waiting starts again.
                await self._session.execute(
                    self._bump(
                        *live,
                        PoolRow.gesture_id.in_(ids),
                        age=PoolRow.age + 1,
                        waited=0,
                    )
                )
                # Passed over: one pass of waiting, which is what raises it next
                # time. Ageing was doing both jobs, so an entry read six times
                # outranked one never seen at all and the day did not rotate.
                await self._session.execute(
                    self._bump(*live, PoolRow.gesture_id.notin_(ids), waited=PoolRow.waited + 1)
                )

        # Two caps, because a pool that only counts passes keeps an entry
        # forever in a tenant nobody is mining, and one that only counts days
        # retires an entry a busy tenant has already reconsidered fifty times.
        # Whichever comes first, and the row says which -- both filtered on
        # `retired = 0`, so nothing is retired twice or re-reported by the
        # other cap.
        # RETURNING rather than ``rowcount``, as in ``add_unclaimed``: which
        # rows actually retired is the answer, and it is one shape everywhere
        # rather than the driver's own count.
        passes = await self._session.execute(
            self._bump(
                *live, PoolRow.age > K_POOL_AGE, retired=True, reason=RETIRED_PASSES
            ).returning(PoolRow.gesture_id)
        )
        stale = await self._session.execute(
            self._bump(
                *live,
                PoolRow.entered_at < datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS),
                retired=True,
                reason=RETIRED_STALE,
            ).returning(PoolRow.gesture_id)
        )
        return len(passes.all()) + len(stale.all())

    async def waiting(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        return await self._entries(tenant_id, retired=False)

    async def ids(self, tenant_id: TenantId) -> tuple[str, ...]:
        return tuple(entry.gesture_id for entry in await self.waiting(tenant_id))

    async def retired(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        return await self._entries(tenant_id, retired=True)

    @staticmethod
    def _bump(*where: ColumnElement[bool], **values: Any) -> Update:
        # ``synchronize_session=False`` because nothing in this repository ever
        # loads a PoolRow as an ORM object -- the reads below select columns --
        # so there is no in-session state for the UPDATE to keep in step with,
        # and asking for one would have SQLAlchemy fetch the affected rows
        # first to do it.
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
            )
            for gesture_id, tenant, age, entered_at, reason, waited in rows
        )
