from pathlib import Path

import pytest

from rig.offers import record_offer
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
