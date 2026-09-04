from datetime import UTC, datetime, timedelta
from pathlib import Path

from rig.pool import (
    K_POOL_AGE,
    K_POOL_DAYS,
    RETIRED_PASSES,
    RETIRED_STALE,
    add_unclaimed,
    age_pool,
    pool_ids,
    retired_entries,
    waiting,
)
from rig.store import Store


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def test_what_no_workflow_claimed_enters_the_pool(tmp_path: Path) -> None:
    store = _store(tmp_path)

    added = add_unclaimed(store, "acme", ["ges_1", "ges_2", "ges_3"], {"ges_1"})

    assert added == 2
    assert set(pool_ids(store, "acme")) == {"ges_2", "ges_3"}


def test_a_claimed_gesture_leaves_the_pool(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1", "ges_2"], set())

    add_unclaimed(store, "acme", ["ges_1", "ges_2"], {"ges_1"})

    assert pool_ids(store, "acme") == ["ges_2"]


def test_the_pool_is_tenant_wide_not_per_stream(tmp_path: Path) -> None:
    """One operator's Blue Yonder half must be able to meet another's SAP half."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    add_unclaimed(store, "other", ["ges_2"], set())

    assert pool_ids(store, "acme") == ["ges_1"]


def test_an_entry_retires_after_enough_passes(tmp_path: Path) -> None:
    """Retirement takes it out of the prompt, never out of the store."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())

    for _ in range(K_POOL_AGE):
        assert age_pool(store, "acme") == 0

    assert age_pool(store, "acme") == 1
    assert pool_ids(store, "acme") == []
    assert store.query("SELECT count(*) AS n FROM pool")[0]["n"] == 1


def test_re_entering_the_pool_does_not_double_it(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    add_unclaimed(store, "acme", ["ges_1"], set())

    assert pool_ids(store, "acme") == ["ges_1"]


def test_re_entering_the_pool_does_not_reset_the_clock(tmp_path: Path) -> None:
    """Otherwise a gesture in every window is immortal and nothing retires."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())

    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")
        assert add_unclaimed(store, "acme", ["ges_1"], set()) == 0

    assert pool_ids(store, "acme") == []


def test_a_claimed_gesture_leaves_even_when_it_is_not_in_this_window(
    tmp_path: Path,
) -> None:
    """A pooled gesture is packed beside the fresh ones, so a pass can cite
    evidence that is only in the pool. `claimed` is not a subset of the window."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_old"], set())

    added = add_unclaimed(store, "acme", ["ges_new"], {"ges_old"})

    assert added == 1
    assert pool_ids(store, "acme") == ["ges_new"]


def test_a_retired_entry_says_which_cap_retired_it(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())

    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")

    entries = retired_entries(store, "acme")
    assert [(entry.gesture_id, entry.reason) for entry in entries] == [("ges_1", RETIRED_PASSES)]
    assert entries[0].age == K_POOL_AGE + 1


def test_an_entry_too_old_in_days_retires_before_it_runs_out_of_passes(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    long_ago = (datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS + 1)).isoformat()
    store.execute("UPDATE pool SET entered_at = ?", (long_ago,))

    assert age_pool(store, "acme") == 1

    entries = retired_entries(store, "acme")
    assert [(entry.gesture_id, entry.reason, entry.age) for entry in entries] == [
        ("ges_1", RETIRED_STALE, 1)
    ]
    assert pool_ids(store, "acme") == []


def test_a_retired_entry_is_not_aged_or_retired_twice(tmp_path: Path) -> None:
    """Including by the other cap: a row already out for passes must not be
    re-reported as a fresh drop the week its entry date goes stale."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")
    store.execute(
        "UPDATE pool SET entered_at = ?",
        ((datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS + 1)).isoformat(),),
    )

    assert age_pool(store, "acme") == 0

    entry = retired_entries(store, "acme")[0]
    assert (entry.age, entry.reason) == (K_POOL_AGE + 1, RETIRED_PASSES)


def test_ageing_one_tenant_does_not_retire_another(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    add_unclaimed(store, "other", ["ges_2"], set())

    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")

    assert pool_ids(store, "acme") == []
    assert pool_ids(store, "other") == ["ges_2"]


def test_ageing_one_tenant_does_not_age_another(tmp_path: Path) -> None:
    """Retiring on a tenant filter while counting passes without one is the
    sibling mistake: the eviction looks scoped and the clock is not."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    add_unclaimed(store, "other", ["ges_2"], set())
    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")

    assert age_pool(store, "other") == 0
    assert pool_ids(store, "other") == ["ges_2"]


def test_a_stale_sweep_does_not_reach_another_tenant(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    add_unclaimed(store, "other", ["ges_2"], set())
    store.execute(
        "UPDATE pool SET entered_at = ?",
        ((datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS + 1)).isoformat(),),
    )

    assert age_pool(store, "acme") == 1
    assert pool_ids(store, "other") == ["ges_2"]
    assert retired_entries(store, "other") == []


def test_one_tenants_claim_does_not_evict_anothers_pool(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    add_unclaimed(store, "other", ["ges_1"], set())

    add_unclaimed(store, "acme", [], {"ges_1"})

    assert pool_ids(store, "acme") == []
    assert pool_ids(store, "other") == ["ges_1"]


def test_a_live_entry_is_not_reported_as_dropped(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1", "ges_2"], set())
    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")
    add_unclaimed(store, "acme", ["ges_3"], set())

    assert [entry.gesture_id for entry in retired_entries(store, "acme")] == [
        "ges_1",
        "ges_2",
    ]


def test_dropped_evidence_is_reported_per_tenant(tmp_path: Path) -> None:
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1"], set())
    add_unclaimed(store, "other", ["ges_2"], set())
    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")
        age_pool(store, "other")

    assert [entry.gesture_id for entry in retired_entries(store, "acme")] == ["ges_1"]


def test_evidence_the_budget_left_out_does_not_age(tmp_path: Path) -> None:
    """Measured on a synthetic all-tabs day of 3,240 gestures, which is the
    scale broad capture produces: the window holds ~200, the day needs 17
    passes to be seen once, K_POOL_AGE is 6 -- and ageing every entry every
    pass retired 2,630 of 3,240 having never once put them in front of the
    model. The mechanism built to stop the same tail losing forever guaranteed
    it instead."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_shown", "ges_waiting"], set())

    # Seven passes, and only one of the two is ever in a window.
    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme", ["ges_shown"])

    retired = {entry.gesture_id for entry in retired_entries(store, "acme")}

    assert "ges_shown" in retired, "shown six times and never cited: it retires"
    assert "ges_waiting" not in retired, "never shown, so it never spent its patience"
    assert "ges_waiting" in pool_ids(store, "acme")


def test_a_caller_with_no_window_ages_everything(tmp_path: Path) -> None:
    """None is not the same as an empty window: a caller that names no window
    is not claiming the window was empty."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_a", "ges_b"], set())

    for _ in range(K_POOL_AGE + 1):
        age_pool(store, "acme")

    assert {e.gesture_id for e in retired_entries(store, "acme")} == {"ges_a", "ges_b"}


def test_waiting_reports_how_long_each_entry_has_waited(tmp_path: Path) -> None:
    """Two clocks, and a reader that returned one of them as a constant.

    `waiting()` built its PoolEntry without the `waited` column, so every entry
    came back at 0 however long it had been passed over -- and the priority
    that rotates the day is computed from exactly that number. The pool ageing
    was correct; the reader was blind, and the window went on showing the same
    468 gestures every pass."""
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_shown", "ges_passed_over"], set())

    age_pool(store, "acme", ["ges_shown"])
    age_pool(store, "acme", ["ges_shown"])

    by_id = {entry.gesture_id: entry for entry in waiting(store, "acme")}

    assert by_id["ges_passed_over"].waited == 2, "passed over twice"
    assert by_id["ges_passed_over"].age == 0, "never shown, so never read"
    assert by_id["ges_shown"].waited == 0, "shown, so its waiting restarted"
    assert by_id["ges_shown"].age == 2, "read twice and cited neither time"


def test_a_pass_that_packed_nothing_still_makes_the_pool_wait(tmp_path: Path) -> None:
    """`NOT IN (NULL)` is NULL, not TRUE, and NULL matches no row.

    An empty window took the `shown is not None` branch and built the SQL
    `gesture_id NOT IN (NULL)`, so the waiting update matched nothing and every
    entry's second clock froze. A pass that packs no evidence is exactly when
    the pool most needs to record that nobody was seen -- the budget was spent
    on something else, and next pass these entries should outrank it. Silently
    freezing is the "the day did not rotate" failure the second clock exists to
    prevent, wearing a branch nobody reads.
    """
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_1", "ges_2"], set())

    age_pool(store, "acme", [])

    by_id = {entry.gesture_id: entry for entry in waiting(store, "acme")}
    assert by_id["ges_1"].waited == 1, "an empty window passed it over"
    assert by_id["ges_2"].waited == 1
    assert by_id["ges_1"].age == 0, "nothing was read, so nothing aged"


def test_a_retired_entry_reports_the_waiting_it_actually_did(tmp_path: Path) -> None:
    """The sibling of the reader that was fixed, which was not.

    `waiting()` learned to read the `waited` column; `retired_entries()` builds
    the same PoolEntry two functions down and did not, so everything the pool
    gave up on reported `waited=0`. That is the worst place to lose the number:
    an entry retired by STALENESS having never once been shown is the exact
    loss the two clocks were built to make visible, and it reported as though
    it had been in front of the model the whole time.
    """
    store = _store(tmp_path)
    add_unclaimed(store, "acme", ["ges_seen", "ges_starved"], set())

    for _ in range(3):
        age_pool(store, "acme", ["ges_seen"])
    long_ago = (datetime.now(tz=UTC) - timedelta(days=K_POOL_DAYS + 1)).isoformat()
    store.execute("UPDATE pool SET entered_at = ? WHERE gesture_id = ?", (long_ago, "ges_starved"))
    age_pool(store, "acme", ["ges_seen"])

    retired = {entry.gesture_id: entry for entry in retired_entries(store, "acme")}
    assert retired["ges_starved"].reason == RETIRED_STALE
    assert retired["ges_starved"].age == 0, "it was never once shown"
    assert retired["ges_starved"].waited == 4, "and it was passed over every pass"
