# Evidence in, intents out — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The rig receives the extension's capture live, stores every gesture with
its correlated calls verbatim, gives each one a model's reading, and shows the
result on a page with what it cost.

**Architecture:** One standalone FastAPI process in `new_agent_arch/`, SQLite on
disk, pure functions behind one ingest endpoint and one read API. No dependency
on `backend/` — see *Decision: no path dependency*. This is sub-plan 1 of three;
it deliberately contains no miner and no runner.

**Tech Stack:** Python 3.12+, uv, FastAPI, `google-genai`, stdlib `sqlite3`,
pytest. No ORM, no Alembic, no Redis, no Temporal.

**Spec:** [`docs/superpowers/specs/2026-09-03-model-first-workflow-mining-design.md`](../specs/2026-09-03-model-first-workflow-mining-design.md)
**Algorithms:** [`docs/new-agent-doc-arc/algorithms.md`](../../new-agent-doc-arc/algorithms.md) — A1, A2, A3 are implemented here.
**Protocol:** [`docs/14-extension-protocol.md`](../../14-extension-protocol.md) — frozen; this plan matches it and does not change it.

---

## Decomposition

The spec covers three subsystems. Executing them as one plan produces a document
nobody finishes and a branch nobody can review. Each of these produces working,
testable software on its own, and each answers a different question:

| Plan | Contains | Answers |
|---|---|---|
| **1 — this one** | ingest, per-gesture intents, the page, cost accounting | Can a model read a single gesture usefully, and what does a day cost? |
| **2 — the miner** | window packing (A4), shape key (A5), shared values (A6), umbrella (A7–A8), citation checks (A9–A10), identity (A11), pool (A12) | **The bet.** Does one pass find the Blue Yonder + SAP job the current pipeline structurally cannot? |
| **3 — the runner** | locators (A13), step loop, state-first verification (A14), escalation (A15), chat and form | Can a proven workflow be performed in the operator's own browser? |

Plan 2 is where the claim lives. Plan 1 exists because plan 2 cannot be written
against evidence that is not flowing yet.

## Decision: no path dependency on `backend/`

The spec permits reusing `backend/`. This plan declines it, and the reasoning
belongs here rather than in a surprised reviewer's head. A survey of the backend
found:

- **There are no per-event Pydantic models to reuse.** `ObservationBatchRequest`
  (`backend/src/sro/interface/http/schemas.py:1564`) types the envelope and
  leaves `events: list[dict[str, Any]]`; the four kinds are checked by a
  hand-written screener, `admit()` in
  `backend/src/sro/application/observation/admit.py:42`. There is nothing to
  import.
- The rig needs **structured output, reasoning-effort control and per-call token
  accounting**. Backend's model ports (`WorkflowInterpreter`, `IntentParser`)
  answer different questions and return frozen domain DTOs; bending them here
  would change files the other pipeline depends on.
- Backend has **no uv workspace** — a path dependency means
  `sro = { path = "../backend", editable = true }`, which makes the rig fail to
  install whenever `backend/` is mid-refactor.

**What we take instead of code: the committed golden fixtures.**
`new-chrome-extension/fixtures/` holds `batch.json` and per-kind files produced
by a real browser test. Task 2 parses those, so "matches the protocol" is a test
against reality rather than against a doc someone retyped.

**Consequence to respect:** if the protocol changes, both projects change. That
is what "frozen" means.

## Global Constraints

- Python **>= 3.12**. `uv` will fetch one; the repo's backend venv runs 3.14.7.
- **Never import from `sro.*`.** Task 1 adds a test that fails if anything does.
- **Credential values never reach storage or a prompt.** `secret == true` ⇒
  `value` is dropped in the parser, before any row is written. From `AGENTS.md`;
  it now guards the model boundary too.
- **Search grounding must never be enabled** on a Gemini call — it voids zero
  data retention (30-day storage, no opt-out). Task 5 asserts the config carries
  no tools.
- **Screenshots sent to the File API must be deleted after the call.** They
  persist until the caller deletes them.
- Gesture `at` stays **Unix seconds as a float** — that is what `recorder.js`
  emits. Every other timestamp is RFC 3339 with an offset.
- **Money is recorded per call.** A task that adds a model call and no cost row
  is incomplete.
- Ruff line length 100, target py312, matching `backend/pyproject.toml`.
- **`ruff format` is the authority on layout, and this plan's code blocks are
  not.** They are authoritative for behaviour, names, values and structure; they
  are hand-written prose and their whitespace is not canonical. After
  transcribing a task's code, run `uv run ruff format src tests` and commit what
  it produces. Every task ends with three gates clean: `ruff check`,
  `ruff format --check`, `mypy src`. Two tasks shipped un-formatted before this
  was written down, and `make lint` would have failed in Task 7 — three tasks
  after the cause.

## Fixture facts the code must honour

Read from `new-chrome-extension/fixtures/batch.json`. Each of these breaks a
naive model, and each has a test:

1. **`component` is `null` on plain HTML controls** — only ExtJS widgets carry
   one. It is not an absent key; it is an explicit `null`.
2. **A `request` event carries its own `tab_id` and `frame_url`.** A1 therefore
   never guesses a request's tab from its host.
3. **`secret` is absent on click, press and upload; `value` is absent only on
   click.** `gesture-press.json` carries `"value": "Enter"` and
   `gesture-upload.json` carries `"value": "manifest.csv"`. Both fields need
   defaults either way.
4. **`status`, `request_body` and `response_body` are `null`** on a failed
   request (`http://127.0.0.1:1/never`, `failure_reason: "Failed to fetch"`).
5. **Bodies are not always JSON** — one is
   `clientCode=ACME-4471&dock=D3`, form-encoded.
6. **`batch_id` is not 32 hex** — the real one is `bat_browsertest_418908ee_1`.
   Do not validate its shape.
7. Timestamps end in `Z`. `datetime.fromisoformat` handles that on 3.12.

## File structure

```
new_agent_arch/
  pyproject.toml            uv project; no dependency on backend
  Makefile                  serve, test, lint
  README.md                 how to run it
  src/rig/
    __init__.py
    config.py               Settings, RIG_ prefix                    T1
    store.py                SQLite schema and queries                T1
    wire.py                 the protocol's shapes                    T2
    records.py              Gesture, Intent — what we keep           T2
    correlate.py            A1 — requests to their gesture           T3
    trim.py                 A2 — a gesture as the model sees it      T4
    models.py               Gemini, structured output, cost          T5
    intents.py              A3 — one call per gesture                T6
    api.py                  FastAPI: ingest, read, the page          T7,T8
    web/index.html          streams, gestures, intents, spend        T8
  tests/
    fixtures.py             loads the committed golden fixtures      T2
    test_store.py  test_standalone.py                                T1
    test_wire.py  test_correlate.py  test_trim.py                    T2,T3,T4
    test_models.py  test_intents.py  test_api.py                     T5,T6,T7
```

---

### Task 1: Project skeleton, config, and the store

**Files:**
- Create: `new_agent_arch/pyproject.toml`, `new_agent_arch/Makefile`
- Create: `new_agent_arch/src/rig/__init__.py`, `new_agent_arch/src/rig/config.py`, `new_agent_arch/src/rig/store.py`
- Test: `new_agent_arch/tests/test_store.py`, `new_agent_arch/tests/test_standalone.py`

**Interfaces:**
- Produces: `Settings` with fields `db_path: Path`, `gemini_api_key: str`,
  `ingest_token: str`, `intent_model: str`, `tenant: str`; `settings() -> Settings`
  (cached). `Store(path: Path)` with `.connect() -> sqlite3.Connection`,
  `.migrate() -> None`, `.execute(sql, params=()) -> None`,
  `.query(sql, params=()) -> list[sqlite3.Row]`.

- [ ] **Step 1: Write the failing tests**

`new_agent_arch/tests/test_store.py`:

```python
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
```

`new_agent_arch/tests/test_standalone.py`:

```python
import ast
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"


def _imports_sro(path: Path) -> bool:
    """Every static import of the backend, including the forms a prefix match
    misses: `import os, sro` and `if x: import sro`.

    Deliberately not detected: importlib.import_module("sro"), __import__, exec.
    Those are evasion; this guard is against accidental coupling.
    """
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            if any(a.name == "sro" or a.name.startswith("sro.") for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "sro" or module.startswith("sro."):
                return True
    return False


def test_the_rig_never_imports_the_backend() -> None:
    """Standalone by design. See 'Decision: no path dependency' in the plan."""
    offenders = [str(path) for path in SRC.rglob("*.py") if _imports_sro(path)]

    assert offenders == []


def test_the_guard_catches_an_import_hidden_in_a_list(tmp_path: Path) -> None:
    """The prefix match this replaced missed exactly this form."""
    sneaky = tmp_path / "sneaky.py"
    sneaky.write_text("import os, sro\n")

    assert _imports_sro(sneaky) is True


def test_the_guard_leaves_an_innocent_module_alone(tmp_path: Path) -> None:
    innocent = tmp_path / "innocent.py"
    innocent.write_text("import srossignol\nfrom os import path\n")

    assert _imports_sro(innocent) is False


def test_the_package_imports_with_nothing_else_on_the_path() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import rig.store; import rig.config; print('ok')"],
        capture_output=True,
        text=True,
        cwd=SRC,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
```

- [ ] **Step 2: Run them**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/ -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'rig'`.

- [ ] **Step 3: Create the project**

`new_agent_arch/pyproject.toml`:

```toml
[project]
name = "rig"
version = "0.1.0"
description = "Model-first workflow mining rig. Standalone; see docs/new-agent-doc-arc."
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "google-genai>=2.7",
    "python-multipart>=0.0.20",
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "httpx>=0.27", "ruff>=0.7", "mypy>=1.13"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rig"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src", "."]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
```

`new_agent_arch/src/rig/__init__.py`:

```python
"""A rig for model-first workflow mining. Standalone; it never imports sro."""
```

`new_agent_arch/src/rig/config.py`:

```python
"""Settings. Env prefix RIG_, so nothing collides with the backend's SRO_."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RIG_", env_file=".env", extra="ignore")

    db_path: Path = Path("rig.db")
    gemini_api_key: str = ""
    ingest_token: str = "dev-only-not-a-secret"
    intent_model: str = "gemini-3.8-flash"
    tenant: str = "new"


@lru_cache
def settings() -> Settings:
    return Settings()
```

`new_agent_arch/src/rig/store.py`:

```python
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
```

`new_agent_arch/Makefile`:

```make
# The rig. Standalone: it shares nothing with backend/ but the wire protocol.

.PHONY: help install serve test lint

help:
	@echo "install  install dependencies"
	@echo "serve    run the rig on :8100"
	@echo "test     run the tests"
	@echo "lint     ruff + mypy"

install:
	uv sync --all-extras

serve:
	uv run uvicorn rig.api:app --reload --port 8100

test:
	uv run pytest -q

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy src
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv sync --all-extras && uv run pytest tests/ -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/
git commit -m "feat(rig): a store, and a project that imports nothing from the backend"
```

---

### Task 2: The wire, proved against the committed fixtures

**Files:**
- Create: `new_agent_arch/src/rig/wire.py`, `new_agent_arch/src/rig/records.py`
- Create: `new_agent_arch/tests/fixtures.py`
- Test: `new_agent_arch/tests/test_wire.py`

**Interfaces:**
- Produces: `Batch`, `GestureEvent`, `RequestEvent`, `PageEvent`, `SnapshotEvent`,
  `Gesture` (wire), `Target`, `Component`, `Request`, `Body` — Pydantic models;
  `Gesture` (record), `Intent`, `ValueSeen` dataclasses; `new_gesture_id() -> str`.
- Note the name clash: `rig.wire.Gesture` is the wire shape,
  `rig.records.Gesture` is the stored row. Later tasks import the record as
  `Gesture` and the wire one as `WireGesture`.

- [ ] **Step 1: Write the failing test**

`new_agent_arch/tests/fixtures.py`:

```python
"""The extension's own committed fixtures, produced by a real browser test.

Parsing these is what proves the rig matches the protocol; a hand-retyped dict
would only prove somebody retyped it consistently.
"""

import json
from pathlib import Path

FIXTURES = (
    Path(__file__).parent.parent.parent / "new-chrome-extension" / "fixtures"
)


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text())


BATCH = load("batch")
GESTURE_TYPE = load("gesture-type")
GESTURE_CLICK = load("gesture-click")
GESTURE_SECRET = load("gesture-secret")
REQUEST_POST = load("request-post")
REQUEST_FAILED = load("request-failed")
PAGE_NAVIGATED = load("page-navigated")
```

`new_agent_arch/tests/test_wire.py`:

```python
import pytest
from pydantic import ValidationError

from rig.wire import Batch, GestureEvent, RequestEvent
from tests.fixtures import (
    BATCH,
    GESTURE_CLICK,
    GESTURE_SECRET,
    GESTURE_TYPE,
    REQUEST_FAILED,
    REQUEST_POST,
)


def test_the_committed_batch_parses_unchanged() -> None:
    batch = Batch.model_validate(BATCH)

    assert batch.device_id == "dev_browsertest"
    assert batch.mode == "passive"
    assert len(batch.events) == len(BATCH["events"])


def test_a_batch_id_is_not_required_to_be_hex() -> None:
    """The real one is bat_browsertest_418908ee_1."""
    assert Batch.model_validate(BATCH).batch_id.startswith("bat_")


def test_an_extjs_control_keeps_its_component_chain() -> None:
    event = GestureEvent.model_validate(GESTURE_TYPE)

    assert event.gesture.target.component is not None
    assert event.gesture.target.component.itemId == "clientCode"
    assert event.gesture.target.component.query == "panel#clients textfield#clientCode"


def test_a_plain_html_control_has_component_null() -> None:
    """Only ExtJS widgets carry one. It is an explicit null, not an absent key."""
    select = next(
        e
        for e in BATCH["events"]
        if e["kind"] == "gesture" and e["gesture"]["kind"] == "select"
    )

    event = GestureEvent.model_validate(select)

    assert event.gesture.target.component is None


def test_a_click_carries_neither_value_nor_secret() -> None:
    assert "value" not in GESTURE_CLICK["gesture"]
    assert "secret" not in GESTURE_CLICK["gesture"]

    event = GestureEvent.model_validate(GESTURE_CLICK)

    assert event.gesture.value is None
    assert event.gesture.secret is False


def test_a_credential_value_does_not_survive_parsing() -> None:
    """AGENTS.md: credential values never reach storage. This is the boundary."""
    loud = {**GESTURE_SECRET}
    loud["gesture"] = {**GESTURE_SECRET["gesture"], "value": "hunter2"}

    event = GestureEvent.model_validate(loud)

    assert event.gesture.secret is True
    assert event.gesture.value is None
    assert "hunter2" not in event.model_dump_json()


def test_a_request_event_carries_its_own_tab() -> None:
    """A1 relies on this instead of guessing a tab from a host."""
    event = RequestEvent.model_validate(REQUEST_POST)

    assert event.tab_id is not None


def test_a_failed_request_has_no_status_and_no_bodies() -> None:
    event = RequestEvent.model_validate(REQUEST_FAILED)

    assert event.request.status is None
    assert event.request.response_body is None
    assert event.request.failure_reason


def test_a_target_with_no_usable_signal_is_refused() -> None:
    naked = {
        "kind": "gesture",
        "gesture": {
            "kind": "click",
            "target": {"tag": "div", "component": None},
            "at": 1.0,
            "url": "https://wms.example/",
        },
        "tab_id": 1,
    }

    with pytest.raises(ValidationError):
        GestureEvent.model_validate(naked)
```

- [ ] **Step 2: Run it**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_wire.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'rig.wire'`.

- [ ] **Step 3: Implement**

`new_agent_arch/src/rig/wire.py`:

```python
"""The extension's wire shapes, from docs/14-extension-protocol.md.

Copied rather than imported: see 'Decision: no path dependency' in the plan.
Proved against new-chrome-extension/fixtures/, which a real browser produced.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator


class Component(BaseModel):
    framework: str | None = None
    xtype: str | None = None
    itemId: str | None = None
    name: str | None = None
    fieldLabel: str | None = None
    text: str | None = None
    query: str | None = None
    chain: list[str] = Field(default_factory=list)


class Target(BaseModel):
    tag: str | None = None
    role: str | None = None
    name: str | None = None
    secret: bool = False
    text: str | None = None
    testId: str | None = None
    cssPath: str | None = None
    xpath: str | None = None
    bounds: dict[str, float] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    component: Component | None = None      # null on plain HTML; only ExtJS has one

    @model_validator(mode="after")
    def must_carry_some_signal(self) -> "Target":
        """The protocol refuses a fingerprint with nothing to match on."""
        if not any((self.role, self.name, self.text, self.testId, self.cssPath, self.xpath)):
            raise ValueError("element fingerprint carries no usable signal")
        return self


class Gesture(BaseModel):
    kind: Literal["click", "type", "select", "press", "upload", "scroll", "hover"]
    target: Target
    value: str | None = None            # absent on click and press
    secret: bool = False                # absent on everything but a credential field
    modifiers: list[str] = Field(default_factory=list)
    at: float                           # Unix seconds, float — recorder.js's format
    url: str | None = None

    @model_validator(mode="after")
    def a_credential_value_is_dropped_here(self) -> "Gesture":
        """AGENTS.md: credential values never reach storage. This is the boundary."""
        if self.secret or self.target.secret:
            object.__setattr__(self, "value", None)
        return self


class GestureEvent(BaseModel):
    kind: Literal["gesture"]
    gesture: Gesture
    tab_id: int | None = None
    frame_url: str | None = None
    page_url: str | None = None


class Body(BaseModel):
    text: str | None = None
    size_bytes: int = 0
    mime_type: str | None = None
    encoding: str | None = None
    redacted_fields: list[str] = Field(default_factory=list)
    blob_uri: str | None = None


class Request(BaseModel):
    request_id: str
    method: str
    url: str
    resource_type: str | None = None
    started_at: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: Body | None = None
    status: int | None = None           # null on a failed request
    status_text: str | None = None
    response_headers: dict[str, str] = Field(default_factory=dict)
    response_body: Body | None = None
    redirect_chain: list[Any] = Field(default_factory=list)
    duration_ms: int | None = None
    from_cache: bool = False
    failure_reason: str | None = None
    blocked_reason: str | None = None


class RequestEvent(BaseModel):
    kind: Literal["request"]
    request: Request
    tab_id: int | None = None
    frame_url: str | None = None


class PageEvent(BaseModel):
    kind: Literal["page"]
    at: str
    page_kind: str
    url: str | None = None
    detail: str | None = None
    tab_id: int | None = None


class SnapshotEvent(BaseModel):
    kind: Literal["snapshot"]
    url: str | None = None
    taken_at: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)


Event = Annotated[
    GestureEvent | RequestEvent | PageEvent | SnapshotEvent,
    Field(discriminator="kind"),
]


class Batch(BaseModel):
    batch_id: str
    device_id: str
    started_at: str
    ended_at: str
    mode: Literal["passive", "teaching"] = "passive"
    recording_id: str | None = None
    events: list[Event]
```

`new_agent_arch/src/rig/records.py`:

```python
"""What the rig keeps. A1 fills `requests`; A3 produces `Intent`."""

import secrets
from dataclasses import dataclass, field

from rig.wire import Gesture as WireGesture
from rig.wire import PageEvent, Request


def new_gesture_id() -> str:
    return "ges_" + secrets.token_hex(16)


@dataclass
class Gesture:
    id: str
    tenant: str
    stream_id: str
    batch_id: str
    at: float
    url: str | None
    system: str | None
    tab_id: int | None
    frame_url: str | None
    gesture: WireGesture
    requests: list[Request] = field(default_factory=list)
    page_events: list[PageEvent] = field(default_factory=list)
    shot_ref: str | None = None
    ax_ref: str | None = None


@dataclass
class ValueSeen:
    field: str
    value: str


@dataclass
class Intent:
    gesture_id: str
    tenant: str
    act: str | None = None
    object: str | None = None
    system: str | None = None
    page: str | None = None
    values_seen: list[ValueSeen] = field(default_factory=list)
    continues: str | None = None
    confidence: str | None = None
    why: str | None = None
    model: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_wire.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/src/rig/wire.py new_agent_arch/src/rig/records.py new_agent_arch/tests/
git commit -m "feat(rig): the frozen wire, proved against the browser's own fixtures"
```

---

### Task 3: A1 — requests find their gesture

**Files:**
- Create: `new_agent_arch/src/rig/correlate.py`
- Test: `new_agent_arch/tests/test_correlate.py`

**Interfaces:**
- Consumes: `Batch`, `GestureEvent`, `RequestEvent`, `PageEvent`, `Request` from
  `rig.wire`; `Gesture`, `new_gesture_id` from `rig.records`.
- Produces: `correlate(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Request]]`
  — gestures in time order with their requests and page events attached, plus the
  orphans; `system_of(url: str | None) -> str | None`; `ATTRIBUTION_SECONDS = 10.0`.

- [ ] **Step 1: Write the failing test**

`new_agent_arch/tests/test_correlate.py`:

```python
import copy
from datetime import datetime, timezone

from rig.correlate import ATTRIBUTION_SECONDS, correlate, system_of
from rig.wire import Batch
from tests.fixtures import BATCH, GESTURE_TYPE, REQUEST_POST

TENANT = "new"


def _rfc3339(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _batch(events: list[dict]) -> Batch:
    return Batch.model_validate({**copy.deepcopy(BATCH), "events": copy.deepcopy(events)})


def _request(started_at: str, request_id: str, tab_id: int) -> dict:
    event = copy.deepcopy(REQUEST_POST)
    event["request"]["started_at"] = started_at
    event["request"]["request_id"] = request_id
    event["tab_id"] = tab_id
    return event


def test_the_whole_committed_batch_correlates() -> None:
    gestures, orphans = correlate(Batch.model_validate(BATCH), TENANT)

    assert len(gestures) == 7
    assert sum(len(g.requests) for g in gestures) + len(orphans) == 5


def test_a_call_belongs_to_the_gesture_that_caused_it() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    call = _request(_rfc3339(at + 0.2), "r1", tab)

    gestures, orphans = correlate(_batch([GESTURE_TYPE, call]), TENANT)

    assert len(gestures[0].requests) == 1
    assert orphans == []


def test_a_call_before_any_gesture_is_an_orphan_and_is_kept() -> None:
    """Orphans are stored, never dropped: a background poll is evidence."""
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    early = _request(_rfc3339(at - 60), "r1", tab)

    gestures, orphans = correlate(_batch([early, GESTURE_TYPE]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_long_after_a_gesture_is_not_attributed_to_it() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    late = _request(_rfc3339(at + ATTRIBUTION_SECONDS + 1), "r1", tab)

    gestures, orphans = correlate(_batch([GESTURE_TYPE, late]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_never_crosses_into_another_tab() -> None:
    """The request event carries its own tab; nothing is guessed from the host."""
    at = GESTURE_TYPE["gesture"]["at"]
    other_tab = _request(_rfc3339(at + 0.2), "r1", GESTURE_TYPE["tab_id"] + 1)

    gestures, orphans = correlate(_batch([GESTURE_TYPE, other_tab]), TENANT)

    assert gestures[0].requests == []
    assert len(orphans) == 1


def test_a_call_goes_to_the_most_recent_gesture_in_its_tab() -> None:
    tab = GESTURE_TYPE["tab_id"]
    first = copy.deepcopy(GESTURE_TYPE)
    first["gesture"]["at"] = 1000.0
    second = copy.deepcopy(GESTURE_TYPE)
    second["gesture"]["at"] = 1002.0
    call = _request(_rfc3339(1004.0), "r1", tab)

    gestures, _ = correlate(_batch([first, second, call]), TENANT)
    owned = {g.at: len(g.requests) for g in gestures}

    assert owned[1002.0] == 1
    assert owned[1000.0] == 0


def test_events_need_not_arrive_sorted() -> None:
    tab = GESTURE_TYPE["tab_id"]
    at = GESTURE_TYPE["gesture"]["at"]
    call = _request(_rfc3339(at + 0.2), "r1", tab)

    gestures, _ = correlate(_batch([call, GESTURE_TYPE]), TENANT)

    assert len(gestures[0].requests) == 1


def test_the_system_is_the_scheme_and_host() -> None:
    assert system_of("https://wms.example/data/WM/wm/suppliers") == "https://wms.example"
    assert system_of("http://127.0.0.1:63319/") == "http://127.0.0.1:63319"
    assert system_of(None) is None
```

- [ ] **Step 2: Run it**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_correlate.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'rig.correlate'`.

- [ ] **Step 3: Implement**

`new_agent_arch/src/rig/correlate.py`:

```python
"""A1 — a request belongs to the gesture that caused it, or to nobody.

The existing pipeline learned this against a real browser: a request arriving
after a drain belongs to the previous action, and only traffic with no owning
gesture at all is an orphan. Orphans are stored, not discarded — a background
poll is evidence that a background poll happened.
"""

from datetime import datetime
from urllib.parse import urlparse

from rig.records import Gesture, new_gesture_id
from rig.wire import Batch, GestureEvent, PageEvent, Request, RequestEvent

ATTRIBUTION_SECONDS = 10.0


def system_of(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _epoch(rfc3339: str) -> float:
    return datetime.fromisoformat(rfc3339).timestamp()


def correlate(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Request]]:
    gestures: list[Gesture] = []
    requests: list[tuple[float, int | None, Request]] = []
    pages: list[tuple[float, PageEvent]] = []

    for event in batch.events:
        if isinstance(event, GestureEvent):
            gestures.append(
                Gesture(
                    id=new_gesture_id(),
                    tenant=tenant,
                    stream_id=batch.device_id,
                    batch_id=batch.batch_id,
                    at=event.gesture.at,
                    url=event.gesture.url,
                    system=system_of(event.gesture.url),
                    tab_id=event.tab_id,
                    frame_url=event.frame_url,
                    gesture=event.gesture,
                )
            )
        elif isinstance(event, RequestEvent):
            requests.append((_epoch(event.request.started_at), event.tab_id, event.request))
        elif isinstance(event, PageEvent):
            pages.append((_epoch(event.at), event))

    gestures.sort(key=lambda gesture: gesture.at)

    orphans: list[Request] = []
    for when, tab_id, request in sorted(requests, key=lambda triple: triple[0]):
        owner = _owner(gestures, when, tab_id)
        if owner is None:
            orphans.append(request)
        else:
            owner.requests.append(request)

    for when, page in sorted(pages, key=lambda pair: pair[0]):
        owner = _owner(gestures, when, page.tab_id)
        if owner is not None:
            owner.page_events.append(page)

    return gestures, orphans


def _owner(gestures: list[Gesture], when: float, tab_id: int | None) -> Gesture | None:
    """The last gesture in the same tab, within the attribution window."""
    best: Gesture | None = None
    for gesture in gestures:
        if gesture.at > when:
            break
        if tab_id is not None and gesture.tab_id != tab_id:
            continue
        if when - gesture.at > ATTRIBUTION_SECONDS:
            continue
        best = gesture
    return best
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_correlate.py -v
```

Expected: 8 passed. The fixture holds **7 gestures and 5 requests**, and all five
requests fall in the last gesture's tab and window, so orphans are 0. If a count
disagrees, print the actual split before touching the algorithm — the fixture is
the authority, not the number written here.

- [ ] **Step 5: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/src/rig/correlate.py new_agent_arch/tests/test_correlate.py
git commit -m "feat(rig): a call belongs to the gesture that caused it, or to nobody"
```

---

### Task 4: A2 — a gesture as the model sees it

**Files:**
- Create: `new_agent_arch/src/rig/trim.py`
- Test: `new_agent_arch/tests/test_trim.py`

**Interfaces:**
- Consumes: `Gesture` from `rig.records`; `Body`, `Request`, `Target` from `rig.wire`.
- Produces: `trim(gesture: Gesture) -> dict[str, Any]`; `thin(target: Target) -> bool`;
  `path_shape(url: str) -> str`; `body_keys(body: Body | None) -> dict[str, str] | None`;
  `VALUE_CHARS = 80`; `BODY_KEYS = 40`.

- [ ] **Step 1: Write the failing test**

`new_agent_arch/tests/test_trim.py`:

```python
import json

from rig.correlate import correlate
from rig.trim import path_shape, thin, trim
from rig.wire import Batch, Target
from tests.fixtures import BATCH, GESTURE_TYPE


def _typed_gesture():
    gestures, _ = correlate(Batch.model_validate(BATCH), "new")
    return next(g for g in gestures if g.gesture.kind == "type" and not g.gesture.secret)


def test_the_component_chain_survives_because_it_is_what_names_the_control() -> None:
    trimmed = trim(_typed_gesture())

    assert trimmed["target"]["itemId"] == "clientCode"
    assert trimmed["target"]["fieldLabel"] == "Client Code"


def test_a_control_with_no_component_still_trims() -> None:
    gestures, _ = correlate(Batch.model_validate(BATCH), "new")
    select = next(g for g in gestures if g.gesture.kind == "select")

    trimmed = trim(select)

    assert trimmed["target"]["itemId"] is None
    assert trimmed["target"]["name"] == "Dock"


def test_cssPath_and_xpath_are_not_sent_to_the_model() -> None:
    """Long, meaningless to a model, and the two locators that break."""
    text = json.dumps(trim(_typed_gesture()))

    assert "cssPath" not in text
    assert "xpath" not in text
    assert "/html/body" not in text


def test_a_json_body_keeps_its_keys() -> None:
    gestures, _ = correlate(Batch.model_validate(BATCH), "new")
    with_post = next(
        g for g in gestures if any(r.method == "POST" for r in g.requests)
    )

    calls = trim(with_post)["calls"]
    posted = next(c for c in calls if c["method"] == "POST")

    assert "clientCode" in posted["body_keys"]


def test_a_form_encoded_body_keeps_its_keys_too() -> None:
    """One of the committed calls is clientCode=ACME-4471&dock=D3."""
    from rig.trim import body_keys
    from rig.wire import Body

    body = Body(
        text="clientCode=ACME-4471&dock=D3",
        mime_type="application/x-www-form-urlencoded",
    )

    assert body_keys(body) == {"clientCode": "ACME-4471", "dock": "D3"}


def test_a_failed_call_with_no_body_does_not_explode() -> None:
    from rig.trim import body_keys

    assert body_keys(None) is None


def test_a_long_value_is_truncated() -> None:
    from rig.trim import VALUE_CHARS, body_keys
    from rig.wire import Body

    body = Body(text=json.dumps({"note": "x" * 500}), mime_type="application/json")

    assert len(body_keys(body)["note"]) <= VALUE_CHARS


def test_a_credential_gesture_carries_no_value() -> None:
    gestures, _ = correlate(Batch.model_validate(BATCH), "new")
    secret = next(g for g in gestures if g.gesture.secret)

    assert trim(secret)["value"] is None


def test_a_target_with_a_label_is_not_thin() -> None:
    assert thin(Target.model_validate(GESTURE_TYPE["gesture"]["target"])) is False


def test_a_target_with_only_a_css_path_is_thin() -> None:
    bare = Target.model_validate({"tag": "div", "cssPath": "div > div:nth-child(3)"})

    assert thin(bare) is True


def test_an_id_in_a_path_becomes_a_star() -> None:
    assert path_shape("https://x/data/WM/wm/addresses/1183") == "/data/WM/wm/addresses/*"
    assert path_shape("https://x/api/orders") == "/api/orders"
```

- [ ] **Step 2: Run it**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_trim.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'rig.trim'`.

- [ ] **Step 3: Implement**

`new_agent_arch/src/rig/trim.py`:

```python
"""A2 — what one gesture looks like to the model that reads it.

Token discipline, because A3 runs once per gesture and a day is thousands of
them. cssPath and xpath are excluded on purpose: long, meaningless to a model,
and the two locators that break. The runner still reads them from the stored row.
"""

import json
from typing import Any
from urllib.parse import parse_qsl, urlparse

from rig.records import Gesture
from rig.wire import Body, Request, Target

VALUE_CHARS = 80
BODY_KEYS = 40


def thin(target: Target) -> bool:
    """True when nothing here would tell a model what the control is."""
    component = target.component
    return not any(
        (
            target.name,
            target.text,
            component.fieldLabel if component else None,
            component.itemId if component else None,
        )
    )


def path_shape(url: str) -> str:
    """/data/WM/wm/addresses/1183 -> /data/WM/wm/addresses/*"""
    parts = urlparse(url).path.split("/")
    return "/".join("*" if _looks_like_an_id(part) else part for part in parts)


def _looks_like_an_id(part: str) -> bool:
    return bool(part) and (part.isdigit() or (len(part) > 12 and "-" in part))


def body_keys(body: Body | None) -> dict[str, str] | None:
    """Keys and short values. Never the prose, never the whole payload."""
    if body is None or not body.text:
        return None

    parsed: object
    if body.mime_type == "application/x-www-form-urlencoded":
        parsed = dict(parse_qsl(body.text))
    else:
        try:
            parsed = json.loads(body.text)
        except (ValueError, TypeError):
            return {"_": body.text[:VALUE_CHARS]}

    if not isinstance(parsed, dict):
        return {"_": str(parsed)[:VALUE_CHARS]}

    return {key: str(parsed[key])[:VALUE_CHARS] for key in list(parsed)[:BODY_KEYS]}


def _call(request: Request) -> dict[str, Any]:
    return {
        "method": request.method,
        "path": path_shape(request.url),
        "host": urlparse(request.url).netloc,
        "status": request.status,
        "failed": request.failure_reason,
        "body_keys": body_keys(request.request_body),
        "response_keys": body_keys(request.response_body),
    }


def trim(gesture: Gesture) -> dict[str, Any]:
    target = gesture.gesture.target
    component = target.component
    return {
        "kind": gesture.gesture.kind,
        "target": {
            "role": target.role,
            "name": target.name,
            "text": target.text,
            "testId": target.testId,
            "itemId": component.itemId if component else None,
            "fieldLabel": component.fieldLabel if component else None,
            "xtype": component.xtype if component else None,
            "query": component.query if component else None,
        },
        "value": gesture.gesture.value,
        "url": path_shape(gesture.url) if gesture.url else None,
        "host": urlparse(gesture.url).netloc if gesture.url else None,
        "calls": [_call(request) for request in gesture.requests],
        "page": [event.page_kind for event in gesture.page_events],
    }
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_trim.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/src/rig/trim.py new_agent_arch/tests/test_trim.py
git commit -m "feat(rig): a gesture, small enough to ask about thousands of times"
```

---

### Task 5: The model, and what it cost

**Files:**
- Create: `new_agent_arch/src/rig/models.py`
- Test: `new_agent_arch/tests/test_models.py`

**Interfaces:**
- Consumes: `settings()` from `rig.config`.
- Produces: `Answer(data: dict | None, in_tokens: int, out_tokens: int, cost_usd: float, error: str | None)`
  (frozen dataclass); `Asker` Protocol with
  `async ask(*, model: str, instructions: str, evidence: str, schema: dict, image: bytes | None = None) -> Answer`;
  `GeminiAsker(api_key: str)` implementing it; `FakeAsker(*answers: Answer)` for
  tests, recording `.asked: list[dict]`; `PRICES: dict[str, tuple[float, float]]`
  in dollars per million input/output tokens; `price(model, in_tokens, out_tokens) -> float`.

The structured-output shape is the one the backend's adapters already use
(`backend/src/sro/infrastructure/gemini/interpreter.py:178`): a plain JSON-Schema
`dict` passed as `response_schema` with `response_mime_type="application/json"`.

- [ ] **Step 1: Write the failing test**

`new_agent_arch/tests/test_models.py`:

```python
import pytest

from rig.models import PRICES, Answer, FakeAsker, price


def test_a_price_is_dollars_per_million_tokens() -> None:
    """Gemini 3.8 Flash: $0.75 in, $3.75 out, introductory to 2026-12-31."""
    assert PRICES["gemini-3.8-flash"] == (0.75, 3.75)

    assert price("gemini-3.8-flash", 1_000_000, 0) == pytest.approx(0.75)
    assert price("gemini-3.8-flash", 0, 1_000_000) == pytest.approx(3.75)
    assert price("gemini-3.8-flash", 1000, 200) == pytest.approx(0.00075 + 0.00075)


def test_an_unknown_model_costs_nothing_and_does_not_raise() -> None:
    """A rig must not fall over because a price list is stale."""
    assert price("gemini-9-imaginary", 1000, 1000) == 0.0


async def test_a_fake_asker_records_what_it_was_asked() -> None:
    asker = FakeAsker(Answer(data={"act": "typed a client code"}, in_tokens=10, out_tokens=5))

    answer = await asker.ask(
        model="gemini-3.8-flash",
        instructions="read this",
        evidence="{}",
        schema={"type": "object"},
    )

    assert answer.data == {"act": "typed a client code"}
    assert asker.asked[0]["model"] == "gemini-3.8-flash"


async def test_a_fake_asker_runs_out_and_says_so() -> None:
    asker = FakeAsker()

    answer = await asker.ask(
        model="m", instructions="i", evidence="e", schema={"type": "object"}
    )

    assert answer.data is None
    assert answer.error


def test_the_request_config_never_enables_search_grounding() -> None:
    """Grounding voids zero data retention: 30-day storage, no opt-out."""
    from rig.models import build_config

    config = build_config(schema={"type": "object"})

    assert getattr(config, "tools", None) is None
    assert config.response_mime_type == "application/json"
```

- [ ] **Step 2: Run it**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'rig.models'`.

- [ ] **Step 3: Implement**

`new_agent_arch/src/rig/models.py`:

```python
"""Gemini, with structured output and a bill.

Every call records its tokens and what they cost. A model call with no cost row
is a model call nobody can defend at the end of the month.

Search grounding is never enabled: it voids zero data retention (thirty days of
storage, no opt-out), and this process reads live customer payloads.
"""

import json
from dataclasses import dataclass
from typing import Any, Protocol

# Dollars per million tokens, (input, output).
PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.8-flash": (0.75, 3.75),        # introductory, to 2026-12-31
    "gemini-3-flash": (0.50, 3.00),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.1-pro": (2.00, 12.00),         # doubles to (4, 18) above 200K
}


def price(model: str, in_tokens: int, out_tokens: int) -> float:
    rates = PRICES.get(model)
    if rates is None:
        return 0.0
    return in_tokens * rates[0] / 1_000_000 + out_tokens * rates[1] / 1_000_000


@dataclass(frozen=True, slots=True)
class Answer:
    data: dict[str, Any] | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    cost_usd: float = 0.0
    error: str | None = None


class Asker(Protocol):
    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
    ) -> Answer: ...


def build_config(*, schema: dict[str, Any]) -> Any:
    """The config every call uses. No tools, ever — see the module docstring."""
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
    )


class GeminiAsker:
    def __init__(self, api_key: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
    ) -> Answer:
        from google.genai import types

        parts: list[Any] = [instructions, evidence]
        if image is not None:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/png"))

        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=parts,
                config=build_config(schema=schema),
            )
        except Exception as problem:  # a rig keeps going; the row records why
            return Answer(error=f"{type(problem).__name__}: {problem}")

        usage = getattr(response, "usage_metadata", None)
        in_tokens = getattr(usage, "prompt_token_count", 0) or 0
        out_tokens = getattr(usage, "candidates_token_count", 0) or 0

        try:
            data = json.loads(response.text or "{}")
        except ValueError as problem:
            return Answer(
                in_tokens=in_tokens,
                out_tokens=out_tokens,
                cost_usd=price(model, in_tokens, out_tokens),
                error=f"not json: {problem}",
            )

        return Answer(
            data=data,
            in_tokens=in_tokens,
            out_tokens=out_tokens,
            cost_usd=price(model, in_tokens, out_tokens),
        )


class FakeAsker:
    """Queued answers, and a record of every question.

    Not a dataclass: it takes *answers positionally, and @dataclass would
    replace this __init__ with a generated one.
    """

    def __init__(self, *answers: Answer) -> None:
        self.answers = list(answers)
        self.asked = []

    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, Any],
        image: bytes | None = None,
    ) -> Answer:
        self.asked.append(
            {
                "model": model,
                "instructions": instructions,
                "evidence": evidence,
                "schema": schema,
                "image": image,
            }
        )
        if not self.answers:
            return Answer(error="the fake ran out of answers")
        return self.answers.pop(0)
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_models.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/src/rig/models.py new_agent_arch/tests/test_models.py
git commit -m "feat(rig): a model call that records what it cost, and never grounds"
```

---

### Task 6: A3 — one reading per gesture

**Files:**
- Create: `new_agent_arch/src/rig/intents.py`
- Test: `new_agent_arch/tests/test_intents.py`

**Interfaces:**
- Consumes: `Gesture`, `Intent`, `ValueSeen` from `rig.records`; `trim`, `thin`
  from `rig.trim`; `Asker`, `Answer` from `rig.models`.
- Produces: `INTENT_SCHEMA: dict[str, Any]`; `INSTRUCTIONS: str`; `TAIL = 8`;
  `async read_gesture(gesture: Gesture, *, tail: list[Intent], asker: Asker, model: str, image: bytes | None = None) -> Intent`;
  `one_line(intent: Intent) -> str`.

- [ ] **Step 1: Write the failing test**

`new_agent_arch/tests/test_intents.py`:

```python
from rig.correlate import correlate
from rig.intents import TAIL, INTENT_SCHEMA, one_line, read_gesture
from rig.models import Answer, FakeAsker
from rig.records import Intent
from rig.wire import Batch
from tests.fixtures import BATCH

MODEL = "gemini-3.8-flash"


def _gestures():
    gestures, _ = correlate(Batch.model_validate(BATCH), "new")
    return gestures


def _answer(**data) -> Answer:
    base = {
        "act": "typed a client code",
        "object": "client",
        "system": "http://127.0.0.1:63319",
        "page": "orders",
        "values_seen": [{"field": "clientCode", "value": "ACME-4471"}],
        "continues": None,
        "confidence": "high",
        "why": "the field is labelled Client Code",
    }
    return Answer(data={**base, **data}, in_tokens=400, out_tokens=60, cost_usd=0.0005)


async def test_a_gesture_becomes_an_intent() -> None:
    gesture = _gestures()[0]
    asker = FakeAsker(_answer())

    intent = await read_gesture(gesture, tail=[], asker=asker, model=MODEL)

    assert intent.gesture_id == gesture.id
    assert intent.act == "typed a client code"
    assert intent.values_seen[0].field == "clientCode"
    assert intent.confidence == "high"


async def test_the_cost_of_the_call_lands_on_the_intent() -> None:
    asker = FakeAsker(_answer())

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.in_tokens == 400
    assert intent.out_tokens == 60
    assert intent.cost_usd > 0
    assert intent.model == MODEL


async def test_a_refusal_leaves_an_intent_that_says_so() -> None:
    """A failed reading must not lose the gesture; the window still gets it."""
    asker = FakeAsker(Answer(error="503 from the model"))

    intent = await read_gesture(_gestures()[0], tail=[], asker=asker, model=MODEL)

    assert intent.act is None
    assert intent.error == "503 from the model"


async def test_only_the_last_eight_intents_are_carried_as_context() -> None:
    tail = [Intent(gesture_id=f"ges_{n}", tenant="new", act=f"did {n}") for n in range(20)]
    asker = FakeAsker(_answer())

    await read_gesture(_gestures()[0], tail=tail, asker=asker, model=MODEL)

    sent = asker.asked[0]["evidence"]

    assert "did 19" in sent
    assert "did 12" in sent
    assert "did 11" not in sent
    assert TAIL == 8


async def test_a_thin_target_is_asked_about_with_a_picture() -> None:
    gestures = _gestures()
    thin_one = next(g for g in gestures if g.gesture.secret)  # no name, no label
    asker = FakeAsker(_answer(), _answer())

    await read_gesture(thin_one, tail=[], asker=asker, model=MODEL, image=b"PNG")

    assert asker.asked[0]["image"] == b"PNG"


async def test_a_named_target_is_asked_about_without_one() -> None:
    named = next(g for g in _gestures() if g.gesture.kind == "select")
    asker = FakeAsker(_answer())

    await read_gesture(named, tail=[], asker=asker, model=MODEL, image=b"PNG")

    assert asker.asked[0]["image"] is None


async def test_no_credential_value_reaches_the_prompt() -> None:
    secret = next(g for g in _gestures() if g.gesture.secret)
    asker = FakeAsker(_answer())

    await read_gesture(secret, tail=[], asker=asker, model=MODEL)

    assert "hunter2" not in asker.asked[0]["evidence"]
    assert '"value": null' in asker.asked[0]["evidence"]


def test_the_schema_requires_an_act_and_a_reason() -> None:
    assert set(INTENT_SCHEMA["required"]) >= {"act", "why"}


def test_one_line_is_one_line() -> None:
    line = one_line(Intent(gesture_id="ges_1", tenant="new", act="typed a code", object="client"))

    assert "\n" not in line
    assert "typed a code" in line
```

- [ ] **Step 2: Run it**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_intents.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'rig.intents'`.

- [ ] **Step 3: Implement**

`new_agent_arch/src/rig/intents.py`:

```python
"""A3 — one model call per gesture, and never a batch of them.

Batching stream items into a shared call degrades each item through semantic
interference and diluted attention; measured accuracy decays roughly
A(T) = A_max * e^(-b(T-1)) in batch size while throughput only saturates. The
saving is small and the cost is per-item quality. So: one gesture, one call.
"""

import json
from typing import Any

from rig.models import Asker
from rig.records import Gesture, Intent, ValueSeen
from rig.trim import thin, trim

TAIL = 8

INSTRUCTIONS = """You are reading one thing a warehouse operator just did in a browser.

You are given the gesture, the control it touched, the network calls it caused,
and a few lines of what the same person did just before.

Say what they did, in the words an operator would use. Name the object they were
working on. List the values you can see them entering. Say whether this looks
like a continuation of the previous doing.

Do not guess at a value you cannot see. Do not describe the HTML."""

INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "act": {"type": "string", "description": "what the person did, in their words"},
        "object": {"type": "string", "description": "the thing they were working on"},
        "system": {"type": "string"},
        "page": {"type": "string"},
        "values_seen": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"field": {"type": "string"}, "value": {"type": "string"}},
                "required": ["field", "value"],
            },
        },
        "continues": {"type": "string", "description": "empty unless it continues the last doing"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "why": {"type": "string", "description": "one sentence"},
    },
    "required": ["act", "why"],
}


def one_line(intent: Intent) -> str:
    parts = [intent.act or "(unread)"]
    if intent.object:
        parts.append(f"on {intent.object}")
    return " ".join(parts).replace("\n", " ")


async def read_gesture(
    gesture: Gesture,
    *,
    tail: list[Intent],
    asker: Asker,
    model: str,
    image: bytes | None = None,
) -> Intent:
    recent = [one_line(intent) for intent in tail[-TAIL:]]
    evidence = json.dumps(
        {"gesture": trim(gesture), "just_before": recent},
        indent=2,
        sort_keys=True,
    )

    answer = await asker.ask(
        model=model,
        instructions=INSTRUCTIONS,
        evidence=evidence,
        schema=INTENT_SCHEMA,
        image=image if thin(gesture.gesture.target) else None,
    )

    intent = Intent(
        gesture_id=gesture.id,
        tenant=gesture.tenant,
        model=model,
        in_tokens=answer.in_tokens,
        out_tokens=answer.out_tokens,
        cost_usd=answer.cost_usd,
        error=answer.error,
    )
    if answer.data is None:
        return intent

    data = answer.data
    intent.act = data.get("act")
    intent.object = data.get("object")
    intent.system = data.get("system")
    intent.page = data.get("page")
    intent.continues = data.get("continues") or None
    intent.confidence = data.get("confidence")
    intent.why = data.get("why")
    intent.values_seen = [
        ValueSeen(field=str(seen.get("field", "")), value=str(seen.get("value", "")))
        for seen in data.get("values_seen") or []
        if seen.get("field")
    ]
    return intent
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_intents.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/src/rig/intents.py new_agent_arch/tests/test_intents.py
git commit -m "feat(rig): every gesture gets a reading, and a refusal is one too"
```

---

### Task 7: Ingest, and the loop that reads what arrives

**Files:**
- Create: `new_agent_arch/src/rig/api.py`
- Test: `new_agent_arch/tests/test_api.py`

**Interfaces:**
- Consumes: everything from Tasks 1–6.
- Produces: `app: FastAPI`; `build_app(*, store: Store, asker: Asker, token: str, tenant: str, read_on_ingest: bool = True) -> FastAPI`;
  `save_batch(store: Store, batch: Batch, tenant: str) -> tuple[int, bool]`
  returning `(accepted, already_had_it)`; `async read_new_gestures(store: Store, asker: Asker, model: str) -> int`
  returning how many intents were written; `save_intent(store: Store, intent: Intent) -> None`;
  `tail_for(store: Store, stream_id: str, before: float) -> list[Intent]`.
- Routes: `POST /v1/observations`, `POST /v1/observations/artifacts`,
  `GET /v1/health`.

- [ ] **Step 1: Write the failing test**

`new_agent_arch/tests/test_api.py`:

```python
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rig.api import build_app, read_new_gestures, save_batch
from rig.models import Answer, FakeAsker
from rig.store import Store
from rig.wire import Batch
from tests.fixtures import BATCH

TOKEN = "test-token"


@pytest.fixture
def store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


@pytest.fixture
def client(store: Store) -> TestClient:
    return TestClient(
        build_app(
            store=store,
            asker=FakeAsker(),
            token=TOKEN,
            tenant="new",
            read_on_ingest=False,
        )
    )


def _auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_one_unparseable_event_does_not_cost_the_batch(client: TestClient, store: Store) -> None:
    """The protocol: "A rejected event does not reject the batch."""
    raw = json.loads(json.dumps(BATCH))
    raw["events"].append(
        {
            "kind": "gesture",
            "gesture": {
                "kind": "drag",
                "target": {"tag": "div", "cssPath": "div#x"},
                "at": 1.0,
                "url": "https://wms.example/",
            },
            "tab_id": 1,
        }
    )

    response = client.post("/v1/observations", json=raw, headers=_auth())

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == 7
    assert body["rejected"] == 1
    assert body["problems"][0]["index"] == len(BATCH["events"])
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_a_batch_is_accepted_and_its_gestures_are_stored(client: TestClient, store: Store) -> None:
    response = client.post("/v1/observations", json=BATCH, headers=_auth())

    assert response.status_code == 202
    assert response.json()["accepted"] == 7
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_the_same_batch_twice_stores_one_copy(client: TestClient, store: Store) -> None:
    """Idempotent on batch_id: the extension retries, and must not double-count."""
    client.post("/v1/observations", json=BATCH, headers=_auth())
    again = client.post("/v1/observations", json=BATCH, headers=_auth())

    assert again.status_code == 202
    assert again.json()["already_had_it"] is True
    assert store.query("SELECT count(*) AS n FROM gestures")[0]["n"] == 7


def test_an_orphan_call_is_kept(client: TestClient, store: Store) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())

    stored = store.query("SELECT count(*) AS n FROM orphan_requests")[0]["n"]
    owned = sum(
        len(json.loads(row["requests"]))
        for row in store.query("SELECT requests FROM gestures")
    )

    assert stored + owned == 5


def test_a_credential_value_is_nowhere_on_disk(
    client: TestClient, store: Store, tmp_path: Path
) -> None:
    """WAL mode keeps recent writes in rig.db-wal, so reading rig.db alone
    would pass this test without proving anything."""
    loud = json.loads(json.dumps(BATCH))
    for event in loud["events"]:
        if event["kind"] == "gesture" and event["gesture"].get("secret"):
            event["gesture"]["value"] = "hunter2"

    client.post("/v1/observations", json=loud, headers=_auth())

    written = b"".join(
        path.read_bytes() for path in tmp_path.glob("rig.db*")
    ).decode("latin-1")

    assert "rig.db" in str(list(tmp_path.glob("rig.db*")))   # the files exist
    assert "hunter2" not in written


def test_a_malformed_envelope_is_refused_with_422_not_500(client: TestClient) -> None:
    """A bad event is tolerated. A bad batch is not, and says so usefully."""
    headless = {key: value for key, value in BATCH.items() if key != "batch_id"}

    response = client.post("/v1/observations", json=headless, headers=_auth())

    assert response.status_code == 422


def test_no_token_is_refused(client: TestClient) -> None:
    assert client.post("/v1/observations", json=BATCH).status_code == 401


def test_a_wrong_token_is_refused(client: TestClient) -> None:
    response = client.post(
        "/v1/observations", json=BATCH, headers={"Authorization": "Bearer nope"}
    )

    assert response.status_code == 401


async def test_every_stored_gesture_gets_read_once(store: Store) -> None:
    save_batch(store, Batch.model_validate(BATCH), "new")
    asker = FakeAsker(*[_ok() for _ in range(7)])

    written = await read_new_gestures(store, asker, "gemini-3.8-flash")

    assert written == 7
    assert store.query("SELECT count(*) AS n FROM intents")[0]["n"] == 7

    again = await read_new_gestures(store, asker, "gemini-3.8-flash")

    assert again == 0


async def test_a_reading_that_failed_is_still_written(store: Store) -> None:
    """Otherwise the loop retries it forever and the bill never stops."""
    save_batch(store, Batch.model_validate(BATCH), "new")
    asker = FakeAsker(*[Answer(error="503") for _ in range(7)])

    await read_new_gestures(store, asker, "gemini-3.8-flash")

    rows = store.query("SELECT error FROM intents")
    assert len(rows) == 7
    assert all(row["error"] == "503" for row in rows)


def _ok() -> Answer:
    return Answer(
        data={"act": "did a thing", "why": "because", "confidence": "high"},
        in_tokens=400,
        out_tokens=60,
        cost_usd=0.0005,
    )
```

- [ ] **Step 2: Run it**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_api.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'rig.api'`.

- [ ] **Step 3: Implement**

`new_agent_arch/src/rig/api.py`:

```python
"""The rig's one process: take what the extension saw, read it, show it."""

import asyncio
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, Header, HTTPException, UploadFile
from pydantic import ValidationError

from rig.config import settings
from rig.correlate import correlate
from rig.intents import read_gesture
from rig.models import Asker, GeminiAsker
from rig.records import Gesture, Intent, ValueSeen
from rig.store import Store
from rig.wire import Batch, Gesture as WireGesture, parse_batch


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def save_batch(store: Store, batch: Batch, tenant: str) -> tuple[int, bool]:
    """Store one batch and its gestures. Idempotent on batch_id."""
    try:
        store.execute(
            "INSERT INTO batches (batch_id, device_id, tenant, mode, received_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (batch.batch_id, batch.device_id, tenant, batch.mode, _now()),
        )
    except sqlite3.IntegrityError:
        return 0, True

    gestures, orphans = correlate(batch, tenant)

    with store.connect() as connection:
        for gesture in gestures:
            connection.execute(
                "INSERT INTO gestures (id, tenant, stream_id, batch_id, at, url, system,"
                " tab_id, frame_url, gesture_json, requests, page_events)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    gesture.id,
                    gesture.tenant,
                    gesture.stream_id,
                    gesture.batch_id,
                    gesture.at,
                    gesture.url,
                    gesture.system,
                    gesture.tab_id,
                    gesture.frame_url,
                    gesture.gesture.model_dump_json(),
                    json.dumps([r.model_dump(mode="json") for r in gesture.requests]),
                    json.dumps([p.model_dump(mode="json") for p in gesture.page_events]),
                ),
            )
        for orphan in orphans:
            connection.execute(
                "INSERT OR IGNORE INTO orphan_requests (request_id, batch_id, tenant, payload)"
                " VALUES (?, ?, ?, ?)",
                (orphan.request_id, batch.batch_id, tenant, orphan.model_dump_json()),
            )
        connection.execute(
            "UPDATE batches SET accepted = ? WHERE batch_id = ?",
            (len(gestures), batch.batch_id),
        )

    return len(gestures), False


def _row_to_gesture(row: sqlite3.Row) -> Gesture:
    return Gesture(
        id=row["id"],
        tenant=row["tenant"],
        stream_id=row["stream_id"],
        batch_id=row["batch_id"],
        at=row["at"],
        url=row["url"],
        system=row["system"],
        tab_id=row["tab_id"],
        frame_url=row["frame_url"],
        gesture=WireGesture.model_validate_json(row["gesture_json"]),
        requests=[],
        page_events=[],
        shot_ref=row["shot_ref"],
    )


def _row_to_intent(row: sqlite3.Row) -> Intent:
    return Intent(
        gesture_id=row["gesture_id"],
        tenant=row["tenant"],
        act=row["act"],
        object=row["object"],
        system=row["system"],
        page=row["page"],
        values_seen=[ValueSeen(**seen) for seen in json.loads(row["values_seen"])],
        continues=row["continues"],
        confidence=row["confidence"],
        why=row["why"],
        model=row["model"],
        in_tokens=row["in_tokens"],
        out_tokens=row["out_tokens"],
        cost_usd=row["cost_usd"],
        error=row["error"],
    )


def save_intent(store: Store, intent: Intent) -> None:
    store.execute(
        "INSERT OR REPLACE INTO intents (gesture_id, tenant, act, object, system, page,"
        " values_seen, continues, confidence, why, model, in_tokens, out_tokens,"
        " cost_usd, created_at, error)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            intent.gesture_id,
            intent.tenant,
            intent.act,
            intent.object,
            intent.system,
            intent.page,
            json.dumps([asdict(seen) for seen in intent.values_seen]),
            intent.continues,
            intent.confidence,
            intent.why,
            intent.model,
            intent.in_tokens,
            intent.out_tokens,
            intent.cost_usd,
            _now(),
            intent.error,
        ),
    )


def tail_for(store: Store, stream_id: str, before: float) -> list[Intent]:
    rows = store.query(
        "SELECT i.* FROM intents i JOIN gestures g ON g.id = i.gesture_id"
        " WHERE g.stream_id = ? AND g.at < ? ORDER BY g.at DESC LIMIT 8",
        (stream_id, before),
    )
    return list(reversed([_row_to_intent(row) for row in rows]))


async def read_new_gestures(store: Store, asker: Asker, model: str) -> int:
    """Every stored gesture with no intent gets exactly one reading."""
    rows = store.query(
        "SELECT g.* FROM gestures g LEFT JOIN intents i ON i.gesture_id = g.id"
        " WHERE i.gesture_id IS NULL ORDER BY g.at LIMIT 200"
    )

    written = 0
    for row in rows:
        gesture = _row_to_gesture(row)
        intent = await read_gesture(
            gesture,
            tail=tail_for(store, gesture.stream_id, gesture.at),
            asker=asker,
            model=model,
        )
        save_intent(store, intent)
        written += 1
    return written


def build_app(
    *,
    store: Store,
    asker: Asker,
    token: str,
    tenant: str,
    read_on_ingest: bool = True,
) -> FastAPI:
    """read_on_ingest=False in tests: a background reading task racing the
    assertions makes every ingest test depend on scheduling."""
    app = FastAPI(title="rig")
    app.state.store = store
    app.state.asker = asker
    app.state.token = token
    app.state.tenant = tenant

    def authorised(authorization: Annotated[str | None, Header()] = None) -> None:
        if authorization != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="the rig did not accept that token")

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/observations", status_code=202, dependencies=[Depends(authorised)])
    async def observations(raw: dict[str, Any]) -> dict[str, Any]:
        # Not `batch: Batch`. FastAPI would validate the whole envelope at once,
        # and one unrecognised event -- a gesture kind the extension shipped
        # last week -- would fail the request and lose every good event beside
        # it. The protocol is explicit that a rejected event does not reject the
        # batch, so the events are parsed one at a time.
        #
        # The cost of taking a raw dict is that FastAPI no longer answers a
        # malformed envelope with a 422 of its own, so this does. A bad event is
        # tolerated; a bad batch is still refused, and refused with the status
        # the caller can act on.
        try:
            batch, rejected = parse_batch(raw)
        except ValidationError as problem:
            raise HTTPException(status_code=422, detail=problem.errors()) from problem
        accepted, already = save_batch(store, batch, tenant)
        if read_on_ingest and not already:
            asyncio.create_task(_read_soon(store, asker))
        return {
            "batch_id": batch.batch_id,
            "accepted": accepted,
            "rejected": len(rejected),
            "problems": [{"index": r.index, "reason": r.reason} for r in rejected],
            "already_had_it": already,
        }

    @app.post("/v1/observations/artifacts", status_code=201, dependencies=[Depends(authorised)])
    async def artifact(
        batch_id: Annotated[str, Form()],
        kind: Annotated[str, Form()],
        file: UploadFile,
        frame_index: Annotated[int | None, Form()] = None,
    ) -> dict[str, Any]:
        blob = settings().db_path.parent / "artifacts" / batch_id
        blob.mkdir(parents=True, exist_ok=True)
        name = f"{kind}-{frame_index if frame_index is not None else 'x'}.png"
        data = await file.read()
        (blob / name).write_bytes(data)
        return {"uri": str(blob / name), "size_bytes": len(data)}

    return app


async def _read_soon(store: Store, asker: Asker) -> None:
    try:
        await read_new_gestures(store, asker, settings().intent_model)
    except Exception:  # a reading loop must not take the process with it
        pass


def _default_app() -> FastAPI:
    config = settings()
    store = Store(config.db_path)
    store.migrate()
    asker = GeminiAsker(config.gemini_api_key) if config.gemini_api_key else None
    if asker is None:
        raise RuntimeError("set RIG_GEMINI_API_KEY")
    return build_app(
        store=store, asker=asker, token=config.ingest_token, tenant=config.tenant
    )


app = _default_app() if settings().gemini_api_key else FastAPI(title="rig (no key)")
```

- [ ] **Step 4: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_api.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Run the whole suite and lint**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest -q && make lint
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/src/rig/api.py new_agent_arch/tests/test_api.py
git commit -m "feat(rig): a batch arrives, and every gesture in it is read once"
```

---

### Task 8: The page

**Files:**
- Modify: `new_agent_arch/src/rig/api.py` — add the read routes and mount the page
- Create: `new_agent_arch/src/rig/web/index.html`
- Modify: `new_agent_arch/tests/test_api.py` — append the read-route tests

**Interfaces:**
- Consumes: `Store`, `_row_to_intent` from Task 7.
- Produces routes: `GET /v1/streams`, `GET /v1/gestures?stream=&limit=`,
  `GET /v1/spend`, `GET /` (the page).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_api.py`)

```python
def test_the_streams_route_names_each_browser(client: TestClient) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())

    body = client.get("/v1/streams", headers=_auth()).json()

    assert body["streams"][0]["stream_id"] == "dev_browsertest"
    assert body["streams"][0]["gestures"] == 7


def test_the_gestures_route_pairs_each_gesture_with_its_reading(
    client: TestClient, store: Store
) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())
    row = store.query("SELECT id, tenant FROM gestures ORDER BY at LIMIT 1")[0]
    from rig.api import save_intent
    from rig.records import Intent

    save_intent(store, Intent(gesture_id=row["id"], tenant=row["tenant"], act="typed a code"))

    body = client.get("/v1/gestures?stream=dev_browsertest", headers=_auth()).json()

    assert len(body["gestures"]) == 7
    assert body["gestures"][0]["intent"]["act"] == "typed a code"
    assert body["gestures"][1]["intent"] is None


def test_the_spend_route_adds_up_what_the_readings_cost(
    client: TestClient, store: Store
) -> None:
    client.post("/v1/observations", json=BATCH, headers=_auth())
    from rig.api import save_intent
    from rig.records import Intent

    for row in store.query("SELECT id, tenant FROM gestures"):
        save_intent(
            store,
            Intent(
                gesture_id=row["id"],
                tenant=row["tenant"],
                act="x",
                in_tokens=400,
                out_tokens=60,
                cost_usd=0.0005,
            ),
        )

    body = client.get("/v1/spend", headers=_auth()).json()

    assert body["gestures_read"] == 7
    assert body["cost_usd"] == pytest.approx(0.0035)
    assert body["in_tokens"] == 2800


def test_the_page_is_served(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "rig" in response.text.lower()
```

- [ ] **Step 2: Run them**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest tests/test_api.py -v
```

Expected: FAIL — 404 on the new routes.

- [ ] **Step 3: Add the routes**

Insert inside `build_app`, before `return app`:

```python
    @app.get("/v1/streams", dependencies=[Depends(authorised)])
    def streams() -> dict[str, Any]:
        rows = store.query(
            "SELECT stream_id, count(*) AS gestures, min(at) AS first, max(at) AS last"
            " FROM gestures GROUP BY stream_id ORDER BY last DESC"
        )
        return {"streams": [dict(row) for row in rows]}

    @app.get("/v1/gestures", dependencies=[Depends(authorised)])
    def gestures(stream: str | None = None, limit: int = 200) -> dict[str, Any]:
        sql = (
            "SELECT g.id, g.stream_id, g.at, g.url, g.system, g.gesture_json,"
            " g.requests, i.act, i.object, i.page, i.confidence, i.why, i.values_seen,"
            " i.cost_usd, i.error"
            " FROM gestures g LEFT JOIN intents i ON i.gesture_id = g.id"
        )
        params: tuple[Any, ...] = ()
        if stream:
            sql += " WHERE g.stream_id = ?"
            params = (stream,)
        sql += " ORDER BY g.at LIMIT ?"
        params = (*params, limit)

        out = []
        for row in store.query(sql, params):
            wire = json.loads(row["gesture_json"])
            out.append(
                {
                    "id": row["id"],
                    "at": row["at"],
                    "url": row["url"],
                    "system": row["system"],
                    "kind": wire["kind"],
                    "target": wire["target"].get("name")
                    or (wire["target"].get("component") or {}).get("fieldLabel"),
                    "calls": len(json.loads(row["requests"])),
                    "intent": None
                    if row["act"] is None and row["error"] is None
                    else {
                        "act": row["act"],
                        "object": row["object"],
                        "page": row["page"],
                        "confidence": row["confidence"],
                        "why": row["why"],
                        "values_seen": json.loads(row["values_seen"] or "[]"),
                        "cost_usd": row["cost_usd"],
                        "error": row["error"],
                    },
                }
            )
        return {"gestures": out}

    @app.get("/v1/spend", dependencies=[Depends(authorised)])
    def spend() -> dict[str, Any]:
        row = store.query(
            "SELECT count(*) AS n, coalesce(sum(in_tokens), 0) AS i,"
            " coalesce(sum(out_tokens), 0) AS o, coalesce(sum(cost_usd), 0.0) AS c"
            " FROM intents"
        )[0]
        gestures_total = store.query("SELECT count(*) AS n FROM gestures")[0]["n"]
        return {
            "gestures": gestures_total,
            "gestures_read": row["n"],
            "in_tokens": row["i"],
            "out_tokens": row["o"],
            "cost_usd": round(row["c"], 6),
            "per_gesture_usd": round(row["c"] / row["n"], 8) if row["n"] else 0.0,
        }

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return (Path(__file__).parent / "web" / "index.html").read_text()
```

Add to the imports at the top of `api.py`:

```python
from pathlib import Path

from fastapi.responses import HTMLResponse
```

- [ ] **Step 4: Write the page**

`new_agent_arch/src/rig/web/index.html`:

```html
<!doctype html>
<meta charset="utf-8">
<title>rig — evidence in, intents out</title>
<style>
  :root {
    --ground: #08090b; --raised: #0d0f13; --line: rgba(255,255,255,.09);
    --text: #f4f5f7; --body: #97a0ac; --muted: #6b7280; --accent: #DC582A;
    --clean: #22c55e; --refused: #f87171;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--ground); color: var(--body);
    font: 14px/1.5 Inter, system-ui, sans-serif;
  }
  header {
    display: flex; gap: 24px; align-items: baseline; padding: 16px 24px;
    border-bottom: 1px solid var(--line); position: sticky; top: 0;
    background: var(--ground);
  }
  h1 { font: 600 16px Inter, system-ui, sans-serif; color: var(--text); margin: 0; }
  .spend { margin-left: auto; font-family: "JetBrains Mono", ui-monospace, monospace; }
  .spend b { color: var(--text); font-weight: 500; }
  main { padding: 16px 24px; }
  .row {
    display: grid; grid-template-columns: 90px 1fr 1fr 70px; gap: 16px;
    padding: 10px 12px; border-bottom: 1px solid var(--line); align-items: start;
  }
  .row:hover { background: var(--raised); }
  .kind {
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 12px;
    color: var(--accent);
  }
  .what { color: var(--text); }
  .why { color: var(--muted); font-size: 12px; }
  .unread { color: var(--muted); font-style: italic; }
  .error { color: var(--refused); }
  .values {
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 12px;
    color: var(--body);
  }
  .cost {
    font-family: "JetBrains Mono", ui-monospace, monospace; font-size: 12px;
    color: var(--muted); text-align: right;
  }
  select {
    background: var(--raised); color: var(--text); border: 1px solid var(--line);
    border-radius: 8px; padding: 6px 10px; font: inherit;
  }
</style>

<header>
  <h1>rig</h1>
  <select id="stream"></select>
  <div class="spend" id="spend"></div>
</header>
<main id="rows"></main>

<script>
  const token = new URLSearchParams(location.search).get("token") || "dev-only-not-a-secret";
  const head = { headers: { Authorization: "Bearer " + token } };

  async function get(path) {
    const response = await fetch(path, head);
    if (!response.ok) throw new Error(path + " " + response.status);
    return response.json();
  }

  function line(g) {
    const intent = g.intent;
    const what = intent?.error
      ? `<span class="error">unread — ${intent.error}</span>`
      : intent?.act
        ? `<span class="what">${intent.act}</span><div class="why">${intent.why ?? ""}</div>`
        : `<span class="unread">not read yet</span>`;
    const values = (intent?.values_seen ?? [])
      .map((v) => `${v.field}=${v.value}`)
      .join("  ");
    return `<div class="row">
      <div class="kind">${g.kind}${g.calls ? " ·" + g.calls : ""}</div>
      <div>${what}</div>
      <div class="values">${values}</div>
      <div class="cost">${intent?.cost_usd ? "$" + intent.cost_usd.toFixed(5) : ""}</div>
    </div>`;
  }

  async function draw() {
    const spend = await get("/v1/spend");
    document.getElementById("spend").innerHTML =
      `<b>${spend.gestures_read}</b>/${spend.gestures} read ·
       <b>$${spend.cost_usd.toFixed(4)}</b> ·
       $${spend.per_gesture_usd.toFixed(6)} a gesture`;

    const picker = document.getElementById("stream");
    const { streams } = await get("/v1/streams");
    if (picker.options.length !== streams.length) {
      picker.innerHTML = streams
        .map((s) => `<option value="${s.stream_id}">${s.stream_id} (${s.gestures})</option>`)
        .join("");
    }

    const chosen = picker.value || streams[0]?.stream_id;
    if (!chosen) return;
    const { gestures } = await get("/v1/gestures?stream=" + encodeURIComponent(chosen));
    document.getElementById("rows").innerHTML = gestures.map(line).join("");
  }

  document.getElementById("stream").addEventListener("change", draw);
  draw();
  setInterval(draw, 3000);
</script>
```

- [ ] **Step 5: Run the tests**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO/new_agent_arch && uv run pytest -q && make lint
```

Expected: 12 passed in `test_api.py`, whole suite green.

- [ ] **Step 6: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new_agent_arch/src/rig/api.py new_agent_arch/src/rig/web/ new_agent_arch/tests/test_api.py
git commit -m "feat(rig): a page that says what was read, and what it cost"
```

---

### Task 9: The extension posts to the rig as well

**Files:**
- Create: `new-chrome-extension/src/background/mirror.js` — the second post, alone
- Modify: `new-chrome-extension/src/background/state.js` — a second base URL
- Modify: `new-chrome-extension/src/background/api.js` — call it from the two uploads
- Modify: `new-chrome-extension/src/options/options.html` — fields for it
- Modify: `new-chrome-extension/src/options/options.js` — read and save them
- Modify: `new-chrome-extension/manifest.json` — host permission
- Modify: `Makefile` — add the new test to `test-browser`
- Test: `new-chrome-extension/src/background/mirror.test.mjs`

**Interfaces:**
- Consumes: `state.rigUrl()`, `state.rigToken()` (added in Step 3).
- Produces: `mirrorTo(base, token, path, { body, form, fetcher }) -> Promise<void>`
  in a **new module of its own**, `mirror.js`. **Returns nothing and throws
  nothing.**

**Why its own file:** the test runs under plain `node`, and `api.js` imports
`state.js`, which reaches for `chrome.storage` at module scope. A module with no
imports is a module a test can load. `api.js` then imports `mirrorTo` from it.

**The constraint that matters:** `upload.js` writes `state.pendingBatch()` before
the POST and drops rows on a permanent 4xx. A second destination must never
influence that path — a rig that is down, slow, or refusing must be invisible to
the extension's queue bookkeeping.

- [ ] **Step 1: Write the failing test**

`new-chrome-extension/src/background/mirror.test.mjs`:

```js
import assert from "node:assert/strict";
import test from "node:test";

import { mirrorTo } from "./mirror.js";

test("a mirror posts the same body to the second base", async () => {
  const seen = [];
  const fetcher = async (url, options) => {
    seen.push({ url, options });
    return { ok: true, status: 202 };
  };

  await mirrorTo("http://localhost:8100", "rig-token", "/v1/observations", {
    body: { batch_id: "bat_1" },
    fetcher,
  });

  assert.equal(seen.length, 1);
  assert.equal(seen[0].url, "http://localhost:8100/v1/observations");
  assert.equal(seen[0].options.headers.Authorization, "Bearer rig-token");
  assert.equal(JSON.parse(seen[0].options.body).batch_id, "bat_1");
});

test("a mirror to a rig that is down does not throw", async () => {
  const fetcher = async () => {
    throw new Error("ECONNREFUSED");
  };

  await mirrorTo("http://localhost:8100", "t", "/v1/observations", {
    body: {},
    fetcher,
  });
});

test("a mirror that is refused does not throw", async () => {
  const fetcher = async () => ({ ok: false, status: 401 });

  await mirrorTo("http://localhost:8100", "t", "/v1/observations", {
    body: {},
    fetcher,
  });
});

test("no rig configured means no request at all", async () => {
  let called = false;
  const fetcher = async () => {
    called = true;
    return { ok: true, status: 202 };
  };

  await mirrorTo("", "t", "/v1/observations", { body: {}, fetcher });

  assert.equal(called, false);
});
```

- [ ] **Step 2: Run it**

```bash
node /Users/devansh.j/GreyOrange/AI-SRO/new-chrome-extension/src/background/mirror.test.mjs
```

Expected: FAIL — `Cannot find module .../mirror.js`.

- [ ] **Step 3: Add the second base to `state.js`**

Add beside the existing `apiUrl` key and default:

```js
// in KEYS
rigUrl: "sro.rigUrl",
rigToken: "sro.rigToken",
```

```js
export const DEFAULT_RIG_URL = "";   // empty means: do not mirror
```

Add to the exported state object, beside `apiUrl` / `setApiUrl`:

```js
rigUrl: () => read(KEYS.rigUrl, DEFAULT_RIG_URL),
setRigUrl: (url) => write(KEYS.rigUrl, (url || "").replace(/\/+$/, "")),
rigToken: () => read(KEYS.rigToken, ""),
setRigToken: (value) => write(KEYS.rigToken, value || ""),
```

- [ ] **Step 4: Write `mirror.js`**

`new-chrome-extension/src/background/mirror.js` — no imports, so a test can load
it under plain node:

```js
/**
 * Post a copy of an upload to the rig, if one is configured.
 *
 * Deliberately silent: the rig is a second reader, not a second source of
 * truth. upload.js drops queued rows on a permanent 4xx from the backend, and
 * a rig that is down, slow, or refusing must never be able to reach that
 * decision.
 */
export async function mirrorTo(base, token, path, { body, form, fetcher = fetch } = {}) {
  if (!base) return;
  try {
    const options = { method: "POST", headers: {} };
    if (token) options.headers.Authorization = `Bearer ${token}`;
    if (form) {
      options.body = form;
    } else {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    await fetcher(`${base}${path}`, options);
  } catch {
    // The rig is optional. Its silence is not the extension's problem.
  }
}
```

Then in `new-chrome-extension/src/background/api.js`, add the import beside the
existing ones:

```js
import { mirrorTo } from "./mirror.js";
```

and a small helper next to `call`:

```js
async function mirror(path, options) {
  await mirrorTo(await state.rigUrl(), await state.rigToken(), path, options);
}
```

Finally wrap the two upload calls in the exported `api` object:

```js
observations: async (batch) => {
  const answer = await call("/v1/observations", { method: "POST", body: batch });
  await mirror("/v1/observations", { body: batch });
  return answer;
},
artifact: async (form) => {
  const answer = await call("/v1/observations/artifacts", { method: "POST", form });
  await mirror("/v1/observations/artifacts", { form });
  return answer;
},
```

The backend call stays first and its result is what is returned, so the queue
sees exactly what it saw before.

- [ ] **Step 5: Add the options field**

In `new-chrome-extension/src/options/options.html`, after the `api-url` field:

```html
<label for="rig-url">Rig URL (optional — a second reader)</label>
<input id="rig-url" type="url" placeholder="http://localhost:8100">

<label for="rig-token">Rig token</label>
<input id="rig-token" type="text" placeholder="dev-only-not-a-secret">
```

In `new-chrome-extension/src/options/options.js`, beside the `api-url` lines:

```js
$("rig-url").value = await state.rigUrl();
$("rig-token").value = await state.rigToken();
```

```js
await state.setRigUrl($("rig-url").value);
await state.setRigToken($("rig-token").value);
```

- [ ] **Step 6: Add the host permission**

In `new-chrome-extension/manifest.json`, add to `host_permissions`:

```json
"http://localhost:8100/*"
```

- [ ] **Step 7: Register the test**

In `Makefile`, in the `test-browser` block, beside the other background tests:

```make
	node new-chrome-extension/src/background/mirror.test.mjs
```

- [ ] **Step 8: Run everything**

```bash
node /Users/devansh.j/GreyOrange/AI-SRO/new-chrome-extension/src/background/mirror.test.mjs
cd /Users/devansh.j/GreyOrange/AI-SRO && npx eslint new-chrome-extension/src/background/
```

Expected: 4 tests pass, no lint errors.

- [ ] **Step 9: Prove the queue is untouched**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
node new-chrome-extension/src/background/queue.test.mjs
node new-chrome-extension/src/background/queue.upgrade.test.mjs
node new-chrome-extension/src/background/finishing.test.mjs
```

Expected: all pass, unchanged. If any of these move, the mirror has reached into
upload bookkeeping and the change is wrong.

- [ ] **Step 10: Commit**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git add new-chrome-extension/src/background/mirror.js \
        new-chrome-extension/src/background/mirror.test.mjs \
        new-chrome-extension/src/background/api.js \
        new-chrome-extension/src/background/state.js \
        new-chrome-extension/src/options/options.html \
        new-chrome-extension/src/options/options.js \
        new-chrome-extension/manifest.json \
        Makefile
git status --short          # confirm nothing under src/panel/ is staged
git commit -m "feat(extension): a second reader, whose silence is not our problem"
```

**Never `git add new-chrome-extension/`.** The working tree carries unrelated
uncommitted edits under `src/panel/` that belong to another branch's work; a
directory-wide add would sweep them into this commit.

---

## Verification of the whole

1. `cd new_agent_arch && uv run pytest -q && make lint` — green.
2. `make test-browser` at the repo root — green, including `mirror.test.mjs`.
3. **Live.** Start the rig with a real key:
   ```bash
   cd new_agent_arch
   RIG_GEMINI_API_KEY=... RIG_INGEST_TOKEN=local make serve
   ```
   Set both fields in the extension's options page. Do the supplier task by hand
   in Blue Yonder. Open `http://localhost:8100/?token=local`.
   - Every gesture appears within seconds of doing it.
   - Each one carries a sentence an operator would recognise.
   - The typed supplier name appears in `values_seen`.
4. **The credential check.** On any page with a password field, type the literal
   string `zebra-canary-9418`, then:
   ```bash
   grep -c "zebra-canary-9418" new_agent_arch/rig.db || echo "clean"
   ```
   Must print `clean`. Run it against the artifacts directory too.
5. **The cost check.** After a real half-hour of work, read the header: the
   per-gesture figure should be near **$0.0005**, and the day's projection near
   **a dollar** for two thousand gestures. If it is an order out, that is the
   number the architecture document promised and it is wrong — say so before
   plan 2 starts.
6. **The backend is unaffected.** `cd backend && uv run pytest tests/unit -q` and
   the extension's own upload tests still pass; the rig being down must change
   nothing.

## Out of scope

- **The miner.** Windows, the umbrella pass, identity, the pool — plan 2.
- **The runner.** Locators, the step loop, verification — plan 3.
- **Screenshots to the model.** `read_gesture` accepts an `image` and the thin-
  target rule is tested, but nothing captures or passes one yet: the artifacts
  endpoint stores them on disk and plan 2 wires them through. The File API
  deletion rule applies the moment that happens.
- **Accessibility trees.** Capture uses the component chain; the debugger
  attaches only during runs, which is plan 3.
- **Authentication worth the name.** One shared token from config, on localhost.
  The rig reads live customer payloads, so this is a thing to fix before it runs
  anywhere but a developer's machine, and it is written down here rather than
  discovered later.
- **Retention.** Nothing deletes old evidence yet.
