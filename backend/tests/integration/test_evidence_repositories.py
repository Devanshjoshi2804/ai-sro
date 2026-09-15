"""The evidence plane against real Postgres.

What a browser uploaded, what was read out of it, and the pool of evidence a
mining pass did not place. The rules under test are the rig's own: they were
SQLite there and are SQL here, and a rule that changed on the way across is
the failure this port exists to avoid.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.domain.observation.gesture import (
    Action,
    Body,
    Call,
    Gesture,
    GestureBatch,
    Intent,
    PageMark,
    Target,
    ValueSeen,
)
from sro.domain.observation.pool import (
    K_POOL_AGE,
    K_POOL_DAYS,
    RETIRED_PASSES,
    RETIRED_STALE,
)
from sro.domain.shared.errors import Conflict
from sro.domain.shared.identifiers import TenantId
from sro.infrastructure.db.models import (
    GestureBatchRow,
    OrphanPageRow,
    OrphanRequestRow,
    PoolRow,
)
from sro.infrastructure.db.repositories import SqlUnitOfWork

TENANT = TenantId("acme")
OTHER_TENANT = TenantId("other-corp")


def _gesture(
    gesture_id: str, *, tenant: str = "acme", at: float = 1.0, **overrides: object
) -> Gesture:
    fields: dict[str, object] = {
        "id": gesture_id,
        "tenant": tenant,
        "stream_id": "dev_1",
        "batch_id": "bat_1",
        "at": at,
        "url": "https://wms.example/orders",
        "system": "https://wms.example",
        "tab_id": 7,
        "frame_url": "https://wms.example/orders",
        "page_url": "https://wms.example/",
        "action": Action(
            kind="click",
            at=at,
            url="https://wms.example/orders",
            target=Target(tag="button", name="Save", css_path="button#save"),
        ),
    }
    fields.update(overrides)
    return Gesture(**fields)


def _batch(batch_id: str = "bat_1", **overrides: object) -> GestureBatch:
    fields: dict[str, object] = {
        "batch_id": batch_id,
        "device_id": "dev_1",
        "tenant": "acme",
        "mode": "passive",
        "received_at": "2026-09-03T10:00:00+00:00",
    }
    fields.update(overrides)
    return GestureBatch(**fields)


class TestGestures:
    async def test_a_batch_id_is_not_written_twice(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """An upload retried after its answer was lost must not be stored
        twice: the second copy would double every gesture in it."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_batch(_batch())
            await uow.gestures.add_gestures((_gesture("ges_1"),))
            await uow.commit()

        with pytest.raises(Conflict):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.gestures.add_batch(_batch())
                await uow.gestures.add_gestures((_gesture("ges_2"),))
                await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            kept = await uow.gestures.gestures_for(TENANT)

        assert [gesture.id for gesture in kept] == ["ges_1"]

    async def test_a_gesture_survives_the_round_trip_with_its_calls_and_page_marks(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        gesture = _gesture(
            "ges_1",
            requests=[
                Call(
                    method="POST",
                    url="https://wms.example/api/orders",
                    request_id="req_0",
                    started_at=1.5,
                    request_headers={"content-type": "application/json"},
                    request_body=Body(
                        text='{"dock":"D3"}',
                        size_bytes=13,
                        mime_type="application/json",
                        redacted_fields=("password",),
                    ),
                    status=200,
                    tab_id=7,
                )
            ],
            page_events=[
                PageMark(at=0.5, page_kind="navigated", url="https://wms.example/", tab_id=7)
            ],
        )

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures((gesture,))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            loaded = (await uow.gestures.gestures_for(TENANT))[0]

        assert loaded.action.target is not None
        assert loaded.action.target.css_path == "button#save"
        assert loaded.page_url == "https://wms.example/"
        call = loaded.requests[0]
        assert call.request_id == "req_0"
        assert call.request_headers == {"content-type": "application/json"}
        assert call.request_body is not None
        assert call.request_body.redacted_fields == ("password",)
        assert loaded.page_events[0].page_kind == "navigated"

    async def test_the_device_clock_and_the_recording_a_batch_belongs_to_are_kept(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The device's own window against the server's received_at, and which
        teaching recording a demonstration batch belongs to. The protocol
        requires all three and the rig once discarded the first two."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_batch(
                _batch(
                    mode="teaching",
                    started_at="2026-09-03T10:00:00+05:30",
                    ended_at="2026-09-03T10:00:20+05:30",
                    recording_id="rec_9",
                    accepted=3,
                    rejected=1,
                )
            )
            await uow.commit()

        async with session_factory() as session:
            row = (await session.execute(select(GestureBatchRow))).scalar_one()

        assert row.started_at == "2026-09-03T10:00:00+05:30"
        assert row.ended_at == "2026-09-03T10:00:20+05:30"
        assert row.recording_id == "rec_9"
        assert (row.accepted, row.rejected) == (3, 1)

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.gestures.batch_owner("bat_1") == "dev_1"
            assert await uow.gestures.batch_owner("bat_never") is None

    async def test_an_empty_heartbeat_does_not_make_a_tenant_look_busy(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """The bug this exists for, and it stopped the product doing its job.

        A watching extension uploads on its timer whether or not anybody did
        anything, so an idle browser posts an empty batch a minute forever.
        `MineLately` reads `tenants_since` to ask "is this tenant mid-task"
        and skips one that is -- sensibly, so somebody halfway through
        creating a supplier is not mined at two fields filled.

        An empty heartbeat answered yes. So a tenant read as `still working;
        leaving this one to settle` for as long as the browser stayed
        connected, and mining never ran *while the product was in use*. Seen
        on the QA deployment: fifty-four gestures captured, five empty batches
        after them, nothing mined five minutes later.
        """
        since = datetime(2026, 9, 3, 9, 0, tzinfo=UTC)
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_batch(_batch("bat_worked"))
            await uow.gestures.add_gestures((_gesture("ges_1", batch_id="bat_worked"),))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            busy = await uow.gestures.tenants_since(since)
        assert TENANT in busy, "a batch that carried work says the tenant is working"

        # The heartbeats that follow, after the operator has stopped.
        async with SqlUnitOfWork(session_factory) as uow:
            for number in range(3):
                await uow.gestures.add_batch(
                    _batch(f"bat_idle_{number}", received_at="2026-09-03T11:00:00+00:00")
                )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            later = await uow.gestures.tenants_since(datetime(2026, 9, 3, 10, 30, tzinfo=UTC))

        assert TENANT not in later, (
            "an idle browser's heartbeat kept the tenant mid-task, and mining never ran"
        )

    async def test_another_tenants_gestures_are_not_returned(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures(
                (_gesture("ges_1"), _gesture("ges_2", tenant="other-corp"))
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert [g.id for g in await uow.gestures.gestures_for(TENANT)] == ["ges_1"]
            assert [g.id for g in await uow.gestures.gestures_for(OTHER_TENANT)] == ["ges_2"]

    async def test_a_stream_reports_its_last_gesture_and_how_many(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures(
                (
                    _gesture("ges_1", at=1.0),
                    _gesture("ges_2", at=9.0),
                    _gesture("ges_3", at=5.0, stream_id="dev_2"),
                )
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.gestures.count(TENANT) == 3
            assert await uow.gestures.streams(TENANT) == (("dev_1", 9.0, 2), ("dev_2", 5.0, 1))
            cited = await uow.gestures.gestures_for(TENANT, ids=("ges_3", "ges_1"))

        assert [gesture.id for gesture in cited] == ["ges_1", "ges_3"], "ordered by at"

    async def test_an_intent_replaces_the_reading_before_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures((_gesture("ges_1"),))
            await uow.gestures.save_intent(
                Intent(gesture_id="ges_1", tenant="acme", act="search", in_tokens=10)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.save_intent(
                Intent(
                    gesture_id="ges_1",
                    tenant="acme",
                    act="create",
                    object="order",
                    values_seen=[ValueSeen(field="dock", value="D3")],
                    in_tokens=20,
                    out_tokens=5,
                    thought_tokens=4,
                    cost_usd=0.04,
                )
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            intents = await uow.gestures.intents_for(TENANT)

        assert len(intents) == 1, "one reading per gesture; the later one replaces it"
        assert (intents[0].act, intents[0].object) == ("create", "order")
        assert intents[0].values_seen == [ValueSeen(field="dock", value="D3")]
        assert (intents[0].in_tokens, intents[0].thought_tokens) == (20, 4)

    async def test_a_reading_can_record_that_its_cost_is_not_trustworthy(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """`unpriced` distinguishes a call that cost nothing from one whose
        cost could not be established. Without it the bill is understated."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures((_gesture("ges_1"),))
            await uow.gestures.save_intent(
                Intent(gesture_id="ges_1", tenant="acme", unpriced=True, cost_usd=0.0)
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            intents = await uow.gestures.intents_for(TENANT)

        assert intents[0].unpriced is True
        assert intents[0].cost_usd == 0.0

    async def test_gestures_with_no_reading_yet_are_the_ones_the_loop_takes(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A read gesture is never re-asked, error or not: the model was asked,
        it answered, and it was billed."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_gestures(
                (
                    _gesture("ges_read", at=1.0),
                    _gesture("ges_c", at=4.0),
                    _gesture("ges_b", at=3.0),
                    _gesture("ges_other", at=2.0, tenant="other-corp"),
                )
            )
            await uow.gestures.save_intent(
                Intent(gesture_id="ges_read", tenant="acme", error="the model refused")
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            unread = await uow.gestures.unread(TENANT, limit=200)
            capped = await uow.gestures.unread(TENANT, limit=1)

        assert [gesture.id for gesture in unread] == ["ges_b", "ges_c"], "oldest first"
        assert [gesture.id for gesture in capped] == ["ges_b"]

    async def test_an_orphaned_request_keeps_the_batch_and_the_tab_it_came_from(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.gestures.add_orphan_request(
                TENANT,
                batch_id="bat_1",
                request_id="req_0",
                payload={"tab_id": 7, "request": {"url": "https://wms.example/api/orders"}},
            )
            await uow.gestures.add_orphan_page(
                TENANT,
                batch_id="bat_1",
                at="2026-09-03T10:00:00+00:00",
                payload={"page_kind": "navigated", "url": "https://wms.example/"},
            )
            await uow.commit()

        async with session_factory() as session:
            row = (await session.execute(select(OrphanRequestRow))).scalar_one()
            page = (await session.execute(select(OrphanPageRow))).scalar_one()

        assert (row.batch_id, row.request_id) == ("bat_1", "req_0")
        assert row.payload["tab_id"] == 7
        # Both orphan tables are write-only through the protocol, so nothing
        # else in the suite would notice an unstamped or mis-stamped tenant --
        # and an orphan is evidence one tenant's audit may read.
        assert (row.tenant_id, page.tenant_id) == (TENANT.value, TENANT.value)

    async def test_the_same_orphan_twice_is_one_row(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """A batch replayed re-offers its orphans; the second copy is not a
        second call. Pages have no such key on purpose -- two distinct page
        events can share a batch, an instant and a payload."""
        async with SqlUnitOfWork(session_factory) as uow:
            for _ in range(2):
                await uow.gestures.add_orphan_request(
                    TENANT, batch_id="bat_1", request_id="req_0", payload={"n": 1}
                )
                await uow.gestures.add_orphan_page(
                    TENANT, batch_id="bat_1", at="2026-09-03T10:00:00+00:00", payload={"n": 1}
                )
            await uow.commit()

        async with session_factory() as session:
            requests = await session.scalar(select(func.count()).select_from(OrphanRequestRow))
            pages = await session.scalar(select(func.count()).select_from(OrphanPageRow))

        assert requests == 1, "(batch_id, request_id) is the key, and it holds"
        assert pages == 2, "a page has no such key: two distinct events can look identical"


class TestPool:
    async def test_an_unclaimed_gesture_enters_the_pool_at_age_zero_and_a_cited_one_leaves(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """`claimed` is cleared in full, not only where it intersects the
        window: a pooled gesture is packed beside the fresh ones, so a pass can
        cite evidence that is only in the pool."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(TENANT, window_ids=("ges_old",), claimed=frozenset())
            await uow.pool.add_unclaimed(OTHER_TENANT, window_ids=("ges_old",), claimed=frozenset())
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            added = await uow.pool.add_unclaimed(
                TENANT,
                window_ids=("ges_new", "ges_cited"),
                claimed=frozenset({"ges_cited", "ges_old"}),
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            live = await uow.pool.waiting(TENANT)
            assert await uow.pool.ids(TENANT) == ("ges_new",)
            assert await uow.pool.ids(OTHER_TENANT) == ("ges_old",), "one tenant's claim is its own"

        assert added == 1
        assert (live[0].age, live[0].waited, live[0].reason) == (0, 0, "")

    async def test_re_entering_the_pool_does_not_reset_the_clock(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Otherwise a gesture in every window is immortal and nothing retires."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
            await uow.commit()

        for _ in range(K_POOL_AGE + 1):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.pool.age(TENANT)
                assert (
                    await uow.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
                    == 0
                )
                await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.pool.ids(TENANT) == ()

    async def test_only_what_a_reading_was_shown_ages(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """An entry the budget left out was not read, was not passed over, and
        has not used up any patience. Ageing every entry every pass retired
        2,630 of 3,240 having never once put them in front of the model."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(
                TENANT, window_ids=("ges_shown", "ges_waiting"), claimed=frozenset()
            )
            await uow.commit()

        for _ in range(2):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.pool.age(TENANT, shown=("ges_shown",))
                await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            by_id = {entry.gesture_id: entry for entry in await uow.pool.waiting(TENANT)}

        assert (by_id["ges_shown"].age, by_id["ges_shown"].waited) == (2, 0)
        assert (by_id["ges_waiting"].age, by_id["ges_waiting"].waited) == (0, 2)

    async def test_ageing_one_tenant_does_not_age_another(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Retiring on a tenant filter while counting passes without one is the
        sibling mistake: the eviction looks scoped and the clock is not.

        Split the shared predicate so only the caps keep the tenant filter and
        every suite here stays green: one tenant's pass advances every other
        tenant's `age` and `waited`, and because the sweep *is* scoped the
        damage is silent until those tenants are next mined -- at which point
        their unplaced evidence retires at `age > K_POOL_AGE` and is out of the
        window for good. All three shapes of call, because each bumps on a
        predicate of its own."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
            await uow.pool.add_unclaimed(OTHER_TENANT, window_ids=("ges_2",), claimed=frozenset())
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.age(TENANT)
            await uow.pool.age(TENANT, shown=())
            await uow.pool.age(TENANT, shown=("ges_1",))
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            theirs = await uow.pool.waiting(OTHER_TENANT)

        assert [(one.gesture_id, one.age, one.waited) for one in theirs] == [("ges_2", 0, 0)], (
            "neither clock is another tenant's to move"
        )

    async def test_a_caller_with_no_window_ages_everything(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """``None`` is not an empty window: a caller that names no window is not
        claiming nothing was read, so every live entry ages. Three planted, not
        one -- with a single entry "everything" and "the first one" are the same
        assertion."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(
                TENANT, window_ids=("ges_a", "ges_b", "ges_c"), claimed=frozenset()
            )
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.age(TENANT)
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            waiting = await uow.pool.waiting(TENANT)

        assert [(one.gesture_id, one.age, one.waited) for one in waiting] == [
            ("ges_a", 1, 0),
            ("ges_b", 1, 0),
            ("ges_c", 1, 0),
        ]

    async def test_an_empty_window_still_moves_what_everything_waited(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """`gesture_id NOT IN (NULL)` is NULL, not TRUE, and NULL matches no
        row. An empty window folded into the general case froze every entry's
        second clock -- the "the day did not rotate" failure it exists to
        prevent, wearing a branch nobody reads."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(TENANT, window_ids=("ges_1", "ges_2"), claimed=frozenset())
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.age(TENANT, shown=())
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            by_id = {entry.gesture_id: entry for entry in await uow.pool.waiting(TENANT)}

        assert by_id["ges_1"].waited == 1, "an empty window passed it over"
        assert by_id["ges_2"].waited == 1
        assert by_id["ges_1"].age == 0, "nothing was read, so nothing aged"

    async def test_an_entry_past_its_age_retires_and_says_which_cap_retired_it(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
            await uow.pool.add_unclaimed(OTHER_TENANT, window_ids=("ges_2",), claimed=frozenset())
            await uow.commit()

        retired_on = []
        for _ in range(K_POOL_AGE + 1):
            async with SqlUnitOfWork(session_factory) as uow:
                retired_on.append(await uow.pool.age(TENANT))
                await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            entries = await uow.pool.retired(TENANT)
            assert await uow.pool.ids(OTHER_TENANT) == ("ges_2",), "ageing is per tenant"
            assert await uow.pool.retired(OTHER_TENANT) == ()

        assert retired_on == [0] * K_POOL_AGE + [1]
        assert [(entry.gesture_id, entry.reason, entry.age) for entry in entries] == [
            ("ges_1", RETIRED_PASSES, K_POOL_AGE + 1)
        ]

    async def test_an_entry_older_than_the_stale_window_retires_as_stale(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Two caps, because a pool that only counts passes keeps an entry
        forever in a tenant nobody is mining. Whichever comes first, and the
        row says which.

        The starved entry is the one the two clocks exist for: never once
        shown, so `age` is 0 and only `waited` records that it was there at
        all. A retired read that reported `waited=0` would hide exactly the
        loss the pool was built to make visible."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(
                TENANT, window_ids=("ges_starved", "ges_seen"), claimed=frozenset()
            )
            await uow.pool.add_unclaimed(OTHER_TENANT, window_ids=("ges_old",), claimed=frozenset())
            await uow.commit()

        long_ago = datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS + 1)
        async with session_factory() as session:
            # The other tenant's entry is exactly as old, so only the tenant
            # predicate can keep this sweep out of that pool.
            rows = await session.execute(
                select(PoolRow).where(PoolRow.gesture_id.in_(("ges_starved", "ges_old")))
            )
            for row in rows.scalars():
                row.entered_at = long_ago
            await session.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.pool.age(TENANT, shown=("ges_seen",)) == 1
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            entries = await uow.pool.retired(TENANT)
            assert await uow.pool.ids(TENANT) == ("ges_seen",)
            assert await uow.pool.ids(OTHER_TENANT) == ("ges_old",), "the sweep is per tenant"
            assert await uow.pool.retired(OTHER_TENANT) == ()

        assert [(entry.gesture_id, entry.reason, entry.age, entry.waited) for entry in entries] == [
            ("ges_starved", RETIRED_STALE, 0, 1)
        ]

    async def test_a_retired_entry_is_not_offered_and_is_still_readable_with_its_reason(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        """Retirement takes it out of the prompt, never out of the store -- and
        a row already out for passes must not be re-reported as a fresh drop
        the week its entry date goes stale."""
        async with SqlUnitOfWork(session_factory) as uow:
            await uow.pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
            await uow.commit()
        for _ in range(K_POOL_AGE + 1):
            async with SqlUnitOfWork(session_factory) as uow:
                await uow.pool.age(TENANT)
                await uow.commit()

        long_ago = datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS + 1)
        async with session_factory() as session:
            row = (await session.execute(select(PoolRow))).scalar_one()
            row.entered_at = long_ago
            await session.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.pool.age(TENANT) == 0, "not retired twice, and not by the other cap"
            await uow.commit()

        async with SqlUnitOfWork(session_factory) as uow:
            assert await uow.pool.waiting(TENANT) == ()
            assert await uow.pool.ids(TENANT) == ()
            entry = (await uow.pool.retired(TENANT))[0]

        assert (entry.age, entry.waited, entry.reason) == (K_POOL_AGE + 1, 0, RETIRED_PASSES)
