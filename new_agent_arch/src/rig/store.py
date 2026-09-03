"""SQLite, opened per call. A rig does not need a connection pool."""

import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    batch_id    TEXT PRIMARY KEY,
    device_id   TEXT NOT NULL,
    tenant      TEXT NOT NULL,
    mode        TEXT NOT NULL,
    received_at TEXT NOT NULL,
    accepted    INTEGER NOT NULL DEFAULT 0,
    rejected    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gestures (
    id           TEXT PRIMARY KEY,
    tenant       TEXT NOT NULL,
    stream_id    TEXT NOT NULL,
    batch_id     TEXT NOT NULL,
    at           REAL NOT NULL,      -- Unix seconds, float: recorder.js's own format
    url          TEXT,
    system       TEXT,               -- scheme+host, derived at ingest
    tab_id       INTEGER,
    frame_url    TEXT,
    gesture_json TEXT NOT NULL,
    requests     TEXT NOT NULL DEFAULT '[]',
    page_events  TEXT NOT NULL DEFAULT '[]',
    shot_ref     TEXT,
    ax_ref       TEXT
);
CREATE INDEX IF NOT EXISTS gestures_tenant_at ON gestures (tenant, at);
CREATE INDEX IF NOT EXISTS gestures_stream    ON gestures (stream_id, at);

CREATE TABLE IF NOT EXISTS intents (
    gesture_id  TEXT PRIMARY KEY,
    tenant      TEXT NOT NULL,
    act         TEXT,
    object      TEXT,
    system      TEXT,
    page        TEXT,
    values_seen TEXT NOT NULL DEFAULT '[]',
    continues   TEXT,
    confidence  TEXT,
    why         TEXT,
    model       TEXT,
    in_tokens   INTEGER NOT NULL DEFAULT 0,
    out_tokens  INTEGER NOT NULL DEFAULT 0,
    cost_usd    REAL NOT NULL DEFAULT 0.0,
    unpriced    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    error       TEXT
);

CREATE TABLE IF NOT EXISTS orphan_requests (
    request_id TEXT NOT NULL,
    batch_id   TEXT NOT NULL,
    tenant     TEXT NOT NULL,
    payload    TEXT NOT NULL,
    PRIMARY KEY (batch_id, request_id)
);

CREATE TABLE IF NOT EXISTS orphan_pages (
    batch_id TEXT NOT NULL,
    tenant   TEXT NOT NULL,
    at       TEXT NOT NULL,
    payload  TEXT NOT NULL,
    PRIMARY KEY (batch_id, at, payload)
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def migrate(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self.connect() as connection:
            connection.execute(sql, params)

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute(sql, params))
