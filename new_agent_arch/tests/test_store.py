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
