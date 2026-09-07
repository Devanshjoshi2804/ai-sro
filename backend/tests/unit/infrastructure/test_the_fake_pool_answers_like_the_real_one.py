"""The pool fake, held to the same rules `tests/integration` proves of the SQL.

A fake that ages differently from the store is worse than no fake: the use
cases built on it would pass against a lie. These are the four rules of the
rig's `age_pool` that are easy to get wrong in memory, and the one of
`add_unclaimed` that costs a gesture its history.
"""

from __future__ import annotations

from sro.domain.observation.pool import K_POOL_AGE, RETIRED_PASSES
from sro.domain.shared.identifiers import TenantId
from tests.unit.fakes import FakePoolRepository

TENANT = TenantId("acme")
OTHER = TenantId("other-corp")


async def test_only_what_a_reading_was_shown_ages() -> None:
    pool = FakePoolRepository()
    await pool.add_unclaimed(TENANT, window_ids=("ges_shown", "ges_waiting"), claimed=frozenset())

    await pool.age(TENANT, shown=("ges_shown",))
    await pool.age(TENANT, shown=("ges_shown",))

    by_id = {entry.gesture_id: entry for entry in await pool.waiting(TENANT)}
    assert (by_id["ges_shown"].age, by_id["ges_shown"].waited) == (2, 0)
    assert (by_id["ges_waiting"].age, by_id["ges_waiting"].waited) == (0, 2)


async def test_an_empty_window_still_moves_what_everything_waited() -> None:
    pool = FakePoolRepository()
    await pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())

    await pool.age(TENANT, shown=())

    entry = (await pool.waiting(TENANT))[0]
    assert (entry.age, entry.waited) == (0, 1)


async def test_an_entry_past_its_age_retires_once_and_says_why() -> None:
    pool = FakePoolRepository()
    await pool.add_unclaimed(TENANT, window_ids=("ges_1",), claimed=frozenset())
    await pool.add_unclaimed(OTHER, window_ids=("ges_2",), claimed=frozenset())

    retired_on = [await pool.age(TENANT) for _ in range(K_POOL_AGE + 2)]

    assert retired_on == [0] * K_POOL_AGE + [1, 0], "retired once, and not again"
    assert await pool.ids(TENANT) == ()
    assert await pool.ids(OTHER) == ("ges_2",), "ageing is per tenant"
    entry = (await pool.retired(TENANT))[0]
    assert (entry.reason, entry.age) == (RETIRED_PASSES, K_POOL_AGE + 1)


async def test_re_entering_does_not_reset_the_clock_and_a_citation_leaves() -> None:
    pool = FakePoolRepository()
    await pool.add_unclaimed(TENANT, window_ids=("ges_old",), claimed=frozenset())
    await pool.age(TENANT)

    assert await pool.add_unclaimed(TENANT, window_ids=("ges_old",), claimed=frozenset()) == 0
    assert (await pool.waiting(TENANT))[0].age == 1

    # Cleared in full: a pass can cite evidence that is only in the pool, so
    # `claimed` is not a subset of the window it was drawn beside.
    added = await pool.add_unclaimed(
        TENANT, window_ids=("ges_new",), claimed=frozenset({"ges_old"})
    )

    assert added == 1
    assert await pool.ids(TENANT) == ("ges_new",)
