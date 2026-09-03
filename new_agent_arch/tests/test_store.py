from pathlib import Path

from rig.store import Store


def test_migrate_creates_every_table(tmp_path: Path) -> None:
    store = Store(tmp_path / "rig.db")
    store.migrate()

    names = {
        row["name"] for row in store.query("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"batches", "gestures", "intents", "orphan_requests"} <= names


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    store.migrate()

    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 0


def test_a_row_survives_a_reconnect(tmp_path: Path) -> None:
    path = tmp_path / "rig.db"
    Store(path).migrate()

    Store(path).execute(
        "INSERT INTO batches (batch_id, device_id, tenant, mode, received_at)"
        " VALUES (?, ?, ?, ?, ?)",
        ("bat_browsertest_1", "dev_browsertest", "new", "passive", "2026-09-03T10:00:00+05:30"),
    )

    rows = Store(path).query("SELECT * FROM batches")
    assert len(rows) == 1
    assert rows[0]["mode"] == "passive"


def test_a_batch_id_is_not_written_twice(tmp_path: Path) -> None:
    """Ingest is idempotent on batch_id; the store is where that is enforced."""
    import sqlite3

    import pytest

    path = tmp_path / "rig.db"
    store = Store(path)
    store.migrate()
    row = ("bat_1", "dev_1", "new", "passive", "2026-09-03T10:00:00+05:30")
    sql = (
        "INSERT INTO batches (batch_id, device_id, tenant, mode, received_at)"
        " VALUES (?, ?, ?, ?, ?)"
    )
    store.execute(sql, row)

    with pytest.raises(sqlite3.IntegrityError):
        store.execute(sql, row)


def test_a_reading_can_record_that_its_cost_is_not_trustworthy(tmp_path: Path) -> None:
    """unpriced distinguishes a call that cost nothing from one whose cost
    could not be established. A schema without it silently understates the bill."""
    store = Store(tmp_path / "rig.db")
    store.migrate()
    store.execute(
        "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, gesture_json)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ("ges_1", "new", "dev_1", "bat_1", 1.0, "{}"),
    )

    store.execute(
        "INSERT INTO intents (gesture_id, tenant, unpriced, created_at) VALUES (?, ?, ?, ?)",
        ("ges_1", "new", 1, "2026-09-03T10:00:00+05:30"),
    )

    row = store.query("SELECT unpriced FROM intents WHERE gesture_id = ?", ("ges_1",))[0]

    assert bool(row["unpriced"]) is True
