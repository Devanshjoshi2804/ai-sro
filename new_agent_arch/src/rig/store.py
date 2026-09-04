"""SQLite, opened per call. A rig does not need a connection pool."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    batch_id    TEXT PRIMARY KEY,
    device_id   TEXT NOT NULL,
    tenant      TEXT NOT NULL,
    mode        TEXT NOT NULL,
    -- The device's own clock for the window this batch covers, against
    -- received_at's server clock. The protocol requires both and the rig
    -- discarded both, which is the same silent loss `shot_ref` was deleted for
    -- -- except these two carry something nothing else does.
    started_at  TEXT NOT NULL DEFAULT '',
    ended_at    TEXT NOT NULL DEFAULT '',
    -- Which teaching recording this batch belongs to. `mode` says a batch was
    -- a demonstration; without this, nothing says WHICH, and the extension
    -- refuses to mix two recordings into one batch precisely so that this is
    -- answerable.
    recording_id TEXT,
    received_at TEXT NOT NULL,
    accepted    INTEGER NOT NULL DEFAULT 0,
    rejected    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS gestures (
    id           TEXT PRIMARY KEY,
    tenant       TEXT NOT NULL,  -- written for plan 2's sake; nothing filters on it yet -- one tenant today
    stream_id    TEXT NOT NULL,
    batch_id     TEXT NOT NULL,
    at           REAL NOT NULL,      -- Unix seconds, float: recorder.js's own format
    url          TEXT,
    system       TEXT,               -- scheme+host, derived at ingest
    tab_id       INTEGER,
    frame_url    TEXT,
    -- The TAB's url, which is not the frame's. A gesture inside a portal that
    -- hosts its screens in an iframe reports the frame's src in `url`, and a
    -- run told to open that would load the frame's document outside the shell
    -- that gives it its session. This is the address an operator would type.
    page_url     TEXT,
    gesture_json TEXT NOT NULL,
    requests     TEXT NOT NULL DEFAULT '[]',
    page_events  TEXT NOT NULL DEFAULT '[]'
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
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    tenant   TEXT NOT NULL,
    at       TEXT NOT NULL,
    payload  TEXT NOT NULL
);

-- One reading of one tenant's day. This is the row that has a cost: a pass
-- makes exactly one model call, and every workflow below names the pass that
-- found it rather than carrying a copy of its bill. Copying it meant three
-- workflows out of one $0.04 call summed to $0.12 -- an overstatement that
-- grew with how well the pass did.
CREATE TABLE IF NOT EXISTS passes (
    id         TEXT PRIMARY KEY,
    tenant     TEXT NOT NULL,
    started_at TEXT NOT NULL,
    in_tokens  INTEGER NOT NULL DEFAULT 0,
    out_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd   REAL NOT NULL DEFAULT 0.0,
    unpriced   INTEGER NOT NULL DEFAULT 0,
    proposed   INTEGER NOT NULL DEFAULT 0,
    kept       INTEGER NOT NULL DEFAULT 0,
    rejected   INTEGER NOT NULL DEFAULT 0,
    coverage   REAL NOT NULL DEFAULT 0.0,
    skew       REAL NOT NULL DEFAULT 0.0,
    lopsided   INTEGER NOT NULL DEFAULT 0,
    -- Why it found nothing, when it found nothing for a reason the API gave.
    -- An honest zero and a refused call are the same row without this.
    error      TEXT
);
CREATE INDEX IF NOT EXISTS passes_tenant ON passes (tenant, started_at);

CREATE TABLE IF NOT EXISTS workflows (
    id         TEXT PRIMARY KEY,
    tenant     TEXT NOT NULL,
    pass_id    TEXT NOT NULL DEFAULT '',
    title      TEXT,
    narrative  TEXT,
    systems    TEXT NOT NULL DEFAULT '[]',
    parameters TEXT NOT NULL DEFAULT '[]',
    shape_key  TEXT NOT NULL DEFAULT '[]',
    same_as    TEXT,
    unproven   TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS workflows_tenant ON workflows (tenant, created_at);

CREATE TABLE IF NOT EXISTS pool (
    gesture_id TEXT NOT NULL,
    tenant     TEXT NOT NULL,
    age        INTEGER NOT NULL DEFAULT 0,
    retired    INTEGER NOT NULL DEFAULT 0,
    -- Why it retired, empty while it is still live. Evidence that leaves the
    -- prompt without a record is the failure this architecture exists to avoid.
    reason     TEXT NOT NULL DEFAULT '',
    entered_at TEXT NOT NULL,
    PRIMARY KEY (tenant, gesture_id)
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    workflow_id TEXT NOT NULL,
    ord         INTEGER NOT NULL,
    says        TEXT,
    system      TEXT,
    cites       TEXT NOT NULL DEFAULT '[]',
    parameters  TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (workflow_id, ord)
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Commit on a clean exit, roll back on exception -- then close either way.

        sqlite3's own connection context manager is transactional only; it
        never closes the file handle. Wrapping it here keeps every caller's
        `with store.connect() as connection:` and its commit/rollback
        semantics unchanged, while making sure the connection is actually
        closed instead of resting on CPython refcounting to do it.
        """
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def migrate(self) -> None:
        """Create what is missing. It cannot ALTER what is already there.

        Every statement above is CREATE ... IF NOT EXISTS, so a column added to
        an existing table never appears in a store that predates it -- the new
        table arrives, the new column does not, and the first query naming it
        fails at runtime rather than here. That is acceptable while the rig's
        stores are scratch databases rebuilt from captured batches, which is
        what they are today. It will not be the day one of them is worth
        keeping.
        """
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self.connect() as connection:
            connection.execute(sql, params)

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute(sql, params))
