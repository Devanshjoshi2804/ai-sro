from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from rig.offers import K_ENOUGH, K_OFFER_AFTER, K_QUIET_HOURS, counsel, record_offer
from rig.store import Store


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def test_an_offer_is_recorded_under_an_id_of_its_own(tmp_path: Path) -> None:
    store = _store(tmp_path)
    offer_id = record_offer(
        store,
        tenant="acme",
        workflow_id="wfl_1",
        k=3,
        fate="accepted",
        run_id="run_1",
        device_id="dev_1",
        at="2026-09-06T10:00:00+00:00",
    )

    # Eight bytes of randomness, hex: the shape every other id in the rig has,
    # and enough of it that two offers made in the same second cannot collide.
    assert offer_id.startswith("off_") and len(offer_id) == 20
    assert int(offer_id[4:], 16) >= 0
    rows = store.query("SELECT id, fate, run_id FROM offers")
    assert [tuple(r) for r in rows] == [(offer_id, "accepted", "run_1")]


def test_a_fate_the_protocol_does_not_have_is_refused_and_named(tmp_path: Path) -> None:
    """The last belt behind the route's own check, and it says which word it
    would not take -- a caller told only "bad fate" has to guess."""
    with pytest.raises(ValueError, match="ignored"):
        record_offer(
            _store(tmp_path),
            tenant="acme",
            workflow_id="wfl_1",
            k=3,
            fate="ignored",
            run_id=None,
            device_id="dev_1",
            at="2026-09-06T10:00:00+00:00",
        )


def _offer(store: Store, fate: str, k: int = 2, hour: int = 10) -> None:
    record_offer(
        store,
        tenant="acme",
        workflow_id="wfl_1",
        k=k,
        fate=fate,
        run_id=None,
        device_id="dev_1",
        at=f"2026-09-06T{hour:02d}:00:00+00:00",
    )


def _at(hour: int, day: int = 6) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=UTC)


def test_a_job_nobody_has_answered_is_offered_at_the_default(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert counsel(store, tenant="acme", workflow_id="wfl_1") == counsel(
        store, tenant="acme", workflow_id="wfl_1", now=_at(12)
    )
    advice = counsel(store, tenant="acme", workflow_id="wfl_1")
    assert advice.offer_after == K_OFFER_AFTER and advice.quiet_until is None


def test_three_refusals_running_rest_the_job_for_a_day(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _offer(store, "dismissed", hour=10)
    _offer(store, "did_it", hour=11)
    assert counsel(store, tenant="acme", workflow_id="wfl_1", now=_at(12)).quiet_until is None
    _offer(store, "dismissed", hour=12)

    resting = counsel(store, tenant="acme", workflow_id="wfl_1", now=_at(13))
    assert resting.quiet_until == (_at(12) + timedelta(hours=K_QUIET_HOURS)).isoformat(), (
        "a day from the last refusal"
    )
    assert (
        counsel(store, tenant="acme", workflow_id="wfl_1", now=_at(12, day=7)).quiet_until is None
    )
    # The tenant of a different job hears nothing of it.
    assert counsel(store, tenant="acme", workflow_id="wfl_2", now=_at(13)).quiet_until is None


def test_an_offer_the_operator_did_not_refuse_breaks_the_run(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _offer(store, "dismissed", hour=10)
    _offer(store, "dismissed", hour=11)
    _offer(store, "expired", hour=12)
    _offer(store, "dismissed", hour=13)
    assert counsel(store, tenant="acme", workflow_id="wfl_1", now=_at(14)).quiet_until is None
    _offer(store, "accepted", hour=14)
    _offer(store, "dismissed", hour=15)
    _offer(store, "dismissed", hour=16)
    assert counsel(store, tenant="acme", workflow_id="wfl_1", now=_at(17)).quiet_until is None


def test_offers_that_keep_diverging_move_the_job_past_where_they_diverged(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for hour in range(10, 10 + K_ENOUGH - 1):
        _offer(store, "diverged", k=2, hour=hour)
    assert counsel(store, tenant="acme", workflow_id="wfl_1").offer_after == K_OFFER_AFTER, (
        "two offers are not enough to read"
    )
    _offer(store, "diverged", k=3, hour=13)
    assert counsel(store, tenant="acme", workflow_id="wfl_1").offer_after == 4, (
        "one past the deepest k that diverged"
    )
    # Half or more of the window must have diverged; four accepted after three
    # diverged brings the share under half and the threshold home.
    for hour in range(14, 18):
        _offer(store, "accepted", k=4, hour=hour)
    assert counsel(store, tenant="acme", workflow_id="wfl_1").offer_after == K_OFFER_AFTER


def test_only_the_newest_ten_offers_are_read(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for hour in range(3):
        _offer(store, "diverged", k=2, hour=hour)
    for hour in range(3, 13):
        _offer(store, "accepted", k=2, hour=hour)
    assert counsel(store, tenant="acme", workflow_id="wfl_1").offer_after == K_OFFER_AFTER, (
        "three diverged offers from the morning are outside the window of ten"
    )
