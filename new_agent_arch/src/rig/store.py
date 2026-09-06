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
    tenant       TEXT NOT NULL,  -- every reader filters on it: the mining pass, the pool, the reading loop and the routes
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
    -- Inside out_tokens, not beside it: thinking is billed at the output rate
    -- and out_tokens is what the bill is computed from. Kept as its own column
    -- because on Flash it is ~84% of billed output, and a reader with one
    -- number cannot tell a long answer from a long silence.
    thought_tokens INTEGER NOT NULL DEFAULT 0,
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
    thought_tokens INTEGER NOT NULL DEFAULT 0,  -- inside out_tokens; see `intents`
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
    -- Two clocks, because they measure opposite things and one counter cannot
    -- be both. `age` counts readings this entry was SHOWN and not cited, and
    -- runs out at K_POOL_AGE. `waited` counts passes it was PASSED OVER, and
    -- drives priority so the day rotates. Using age for both made an entry
    -- that had been read six times outrank one never seen at all.
    age        INTEGER NOT NULL DEFAULT 0,
    waited     INTEGER NOT NULL DEFAULT 0,
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

-- A step whose control was only found by the weakest rung of the locator
-- ladder. The run succeeded; the step is about to break. One row per step, so
-- a workflow run daily reports the same weak step once rather than daily.
CREATE TABLE IF NOT EXISTS workflow_stale (
    workflow_id TEXT NOT NULL,
    ord         INTEGER NOT NULL,
    matched_by  TEXT,
    noticed_at  TEXT NOT NULL,
    PRIMARY KEY (workflow_id, ord)
);

-- One write a live run made and the verifier then saw hold by STATE -- a status
-- the server answered, or a read that showed the record. Never by a picture: a
-- model reading a screenshot is not evidence anything was written. Three runs
-- whose every write is in here is what buys a job the right to write unasked,
-- and one failed write empties it for that workflow.
CREATE TABLE IF NOT EXISTS workflow_effects (
    workflow_id TEXT NOT NULL,
    run_id      TEXT NOT NULL,
    ord         INTEGER NOT NULL,
    verified_by TEXT NOT NULL,
    at          TEXT NOT NULL,
    PRIMARY KEY (workflow_id, run_id, ord)
);
-- A row per approval a person gave: which step of which run, and when. The
-- first tap wins; a second on the same step is not a second authorisation.
CREATE TABLE IF NOT EXISTS approvals (
    run_id    TEXT NOT NULL,
    ord       INTEGER NOT NULL,
    at        TEXT NOT NULL,
    device_id TEXT,               -- the browser whose panel the tap came from
    PRIMARY KEY (run_id, ord)
);

-- Every offer the extension made from a recognised prefix, and what became of
-- it. The labelled record of whether recognition was right: the share of
-- `diverged` is what decides whether the prefix length ever moves.
CREATE TABLE IF NOT EXISTS offers (
    id          TEXT PRIMARY KEY,
    tenant      TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    k           INTEGER NOT NULL,
    fate        TEXT NOT NULL,
    run_id      TEXT,
    at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS offers_by_workflow ON offers (tenant, workflow_id, at);

CREATE TABLE IF NOT EXISTS runs (
    id          TEXT PRIMARY KEY,
    tenant      TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    device_id   TEXT NOT NULL,
    values_json TEXT NOT NULL DEFAULT '{}',
    started_by  TEXT NOT NULL DEFAULT '',
    live        INTEGER NOT NULL DEFAULT 0,
    allow_focus INTEGER NOT NULL DEFAULT 0,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    outcome     TEXT NOT NULL DEFAULT 'running',
    -- The writes a dry run produced and did not send, in full. This is what a
    -- person reads before pressing through to live.
    withheld    TEXT NOT NULL DEFAULT '[]',
    in_tokens   INTEGER NOT NULL DEFAULT 0,
    out_tokens  INTEGER NOT NULL DEFAULT 0,
    thought_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd    REAL NOT NULL DEFAULT 0.0,
    unpriced    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS runs_tenant ON runs (tenant, workflow_id, started_at);

CREATE TABLE IF NOT EXISTS run_steps (
    run_id      TEXT NOT NULL,
    ord         INTEGER NOT NULL,
    says        TEXT NOT NULL DEFAULT '',
    planned_by  TEXT,
    sent        TEXT,             -- the command envelope's kind and payload, JSON
    result      TEXT,             -- what the extension answered, JSON
    verdict     TEXT NOT NULL,
    verdict_by  TEXT NOT NULL DEFAULT '',
    reason      TEXT NOT NULL DEFAULT '',
    matched_by  TEXT,
    stale       INTEGER NOT NULL DEFAULT 0,
    before_url  TEXT,
    after_url   TEXT,
    in_tokens   INTEGER NOT NULL DEFAULT 0,
    out_tokens  INTEGER NOT NULL DEFAULT 0,
    thought_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd    REAL NOT NULL DEFAULT 0.0,
    unpriced    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, ord)
);
"""


# Columns added to tables that already existed in an earlier store. Append
# only, and never reorder: a store is migrated by replaying this from wherever
# it stopped. Every declaration needs a default, because ALTER TABLE ADD COLUMN
# has to fill the rows already there.
#
# The two that earned this list: gestures.page_url and intents.thought_tokens.
ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("gestures", "page_url", "TEXT"),
    ("approvals", "device_id", "TEXT"),
    ("batches", "started_at", "TEXT NOT NULL DEFAULT ''"),
    ("batches", "ended_at", "TEXT NOT NULL DEFAULT ''"),
    ("batches", "recording_id", "TEXT"),
    ("intents", "thought_tokens", "INTEGER NOT NULL DEFAULT 0"),
    ("passes", "thought_tokens", "INTEGER NOT NULL DEFAULT 0"),
    ("pool", "waited", "INTEGER NOT NULL DEFAULT 0"),
)


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
        """Create what is missing, and add columns a store predates.

        The CREATE statements above are all IF NOT EXISTS, so they bring a new
        TABLE to an old store and never a new COLUMN. That gap was documented
        as acceptable while the rig's stores are scratch databases -- and then
        cost two hand-patched databases in one afternoon, `page_url` and
        `thought_tokens`, each failing at the first query naming it rather than
        here. `scripts/measure.py --db` copies an old store forward, so the
        reachable path is the ordinary one.

        ADDED_COLUMNS is the honest minimum: an explicit, ordered, append-only
        list rather than a schema differ. SQLite's ALTER TABLE ADD COLUMN is
        the one migration it does cheaply and safely, which is why this covers
        added columns and nothing else. A change SQLite cannot do in place --
        dropping a column, changing a type, adding a constraint -- still needs
        a rebuilt store, and this will not pretend otherwise.
        """
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            for table, column, declaration in ADDED_COLUMNS:
                names = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
                if not names or column in names:
                    # No table means the CREATE above just made it with the
                    # column already in place; present means an earlier run
                    # added it. Neither is an error, and both are the common
                    # case -- a fresh store takes this path for every row.
                    continue
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self.connect() as connection:
            connection.execute(sql, params)

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute(sql, params))
