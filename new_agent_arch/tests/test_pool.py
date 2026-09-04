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
