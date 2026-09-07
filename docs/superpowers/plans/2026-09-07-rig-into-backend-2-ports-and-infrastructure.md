# The Rig Into The Backend — Plan 2 of 5: Ports and Infrastructure

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every seam the ported domain needs to reach the outside world —
the model, the browser, and Postgres — exists in the backend, under the
backend's own ports, with the rig's rules re-proven against a real database.

**Architecture:** The domain landed in plan 1. This plan gives it ports
(`Asker`, `Channel`, six repository protocols) and the infrastructure behind
them (`GeminiAsker`, a channel adapter over the `DeviceSockets` the backend
already runs, four alembic migrations and their SQLAlchemy repositories).
No use case is written here — plan 3 owns those. Nothing in this plan calls
a model, drives a browser, or mines anything; it only makes those possible.

**Tech Stack:** Python 3.12, FastAPI-free layers, SQLAlchemy 2 async,
alembic, Postgres 16 (testcontainers), google-genai, pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`
(*Application → ports*, *Infrastructure*, *Storage*, *Sequence* step 2).

**Base:** branch `rig-into-backend-2` off `rig-into-backend-1` (plan 1 is not
merged; this plan stacks on it).

## Global Constraints

- **Layering.** `sro.domain` imports nothing of ours and no framework: no
  pydantic, no SQLAlchemy, no `Any`, no bare generics. `sro.application`
  imports domain only. `sro.infrastructure` may import both. Import-linter
  must report **4 contracts kept** at every commit.
- **Baseline.** The backend carries **312 mypy errors in 68 files** and **2
  ruff-format violations** from before this work. Green means: the files
  this plan touches are clean, and neither number grows. Record the numbers
  before you start and again at the end.
- **Formatting.** Run `ruff format` on the files you touched, by name.
  Never `ruff format .` — it rewrites the two pre-existing violations and
  pollutes the diff.
- **Untracked files.** Never delete, move, rename or stage an untracked
  file. `backend/Untitled`, `backend/.gmail-token.json.old-client`,
  `backend/old-client_secret_*.disabled` and every `rig.db*` stay exactly
  where they are. Stage only files you created or edited, by name.
- **Behaviour is not ported twice.** A port that changes behaviour is two
  changes. Where the rig's rule and the backend's convention disagree on
  anything but naming, the rig's rule wins and the disagreement is written
  down in the module.
- **Repository convention.** `tenant_id` is the first parameter and is never
  defaulted. A missing entity raises `NotFound`, it does not return `None`,
  unless the rig's caller depends on `None` (then say so in the docstring).
  Every repository is a `Protocol` in `application/ports/repositories.py`, an
  implementation in its own module under `infrastructure/db/`, and a property
  on `UnitOfWork` and `SqlUnitOfWork`.
- **Timestamps.** Columns are `timestamptz` (`DateTime(timezone=True)`).
  Domain records keep the rig's ISO-8601 `str`; the repository parses on the
  way in and formats on the way out. The rig's pure code and its ported tests
  are untouched by the storage change.
- **Table names.** The rig's `runs` collides with the backend's own `runs`
  table; nothing else collides. The rig's tables are named:
  `gesture_batches`, `gestures`, `intents`, `orphan_requests`,
  `orphan_pages`, `mining_pool`, `mining_passes`, `workflows`,
  `workflow_steps`, `workflow_stale`, `workflow_effects`, `workflow_runs`,
  `workflow_run_steps`, `approvals`, `offers`, `chats`. The tenant column is
  `tenant_id` (the backend's name); the domain records keep `tenant`.
- **Every index leads with `tenant_id`**, so a query that forgets the tenant
  also misses its index.
- **Ported tests keep their names.** A rig test that travels keeps its name
  and the meaning of its assertions. A rig test that does not travel is
  listed by name in this plan's ledger under the task that leaves it, with
  the plan that owns it.
- **No device token table.** The backend already mints a per-browser secret
  (`agent_devices.secret`, `AgentDevice.proves`) and the extension already
  sends `X-Device-Secret`. The rig's `device_tokens` table does not travel;
  the browser's credential is the device secret, and revocation is a column
  on the device.

## File map

Created:

| File | Holds |
|---|---|
| `backend/src/sro/domain/execution/workflow_run.py` | `OUTCOMES`, `VERDICTS`, `new_run_id`, `RunStep`, `WorkflowRun` |
| `backend/src/sro/domain/observation/pool.py` | `PoolEntry`, `K_POOL_AGE`, `K_POOL_DAYS`, `RETIRED_AGE`, `RETIRED_STALE` |
| `backend/src/sro/domain/observation/mining.py` | `MiningPass` (the `passes` row) |
| `backend/src/sro/domain/chat/reading.py` | `ChatReading` (the `chats` row) |
| `backend/src/sro/application/ports/model.py` | `Asker` protocol |
| `backend/src/sro/application/ports/channel.py` | `Reply`, `Channel` protocol |
| `backend/src/sro/application/shared/locks.py` | `one_at_a_time` |
| `backend/src/sro/infrastructure/gemini/asker.py` | `GeminiAsker`, `build_config`, `truncated`, `K_MAX_OUTPUT_TOKENS` |
| `backend/src/sro/infrastructure/agent/channel.py` | `SocketChannel` over `DeviceSockets` |
| `backend/src/sro/infrastructure/db/evidence.py` | `SqlGestureRepository`, `SqlPoolRepository` |
| `backend/src/sro/infrastructure/db/workflows.py` | `SqlWorkflowRepository` |
| `backend/src/sro/infrastructure/db/workflow_runs.py` | `SqlWorkflowRunRepository` |
| `backend/src/sro/infrastructure/db/offers.py` | `SqlOfferRepository`, `SqlChatRepository` |
| `backend/src/sro/infrastructure/db/spend.py` | `SqlSpendRepository` |
| `backend/migrations/versions/20260907_0037_the_evidence_plane.py` | migration A |
| `backend/migrations/versions/20260907_0038_workflows_and_passes.py` | migration B |
| `backend/migrations/versions/20260907_0039_workflow_runs.py` | migration C |
| `backend/migrations/versions/20260907_0040_offers_chats_and_revocation.py` | migration D |
| `backend/tests/unit/domain/rig/test_workflow_run.py` | the two pure `test_runs.py` tests |
| `backend/tests/unit/infrastructure/test_asking_a_model.py` | the 22 `test_models.py` tests |
| `backend/tests/unit/infrastructure/test_the_channel_carries_the_envelope.py` | the channel tests the backend lacks |
| `backend/tests/integration/test_evidence_repositories.py` | gestures, intents, batches, orphans, pool |
| `backend/tests/integration/test_workflow_repositories.py` | workflows, steps, stale, effects, passes |
| `backend/tests/integration/test_workflow_run_repositories.py` | runs, steps, approvals, orphaned runs |
| `backend/tests/integration/test_offer_repositories.py` | offers, chats, device revocation |
| `backend/tests/integration/test_spend_and_audit_reads.py` | the day's sum and the audit's reads |

Modified:

| File | Change |
|---|---|
| `backend/src/sro/domain/observation/gesture.py` | `GestureBatch` added |
| `backend/src/sro/domain/skill/offers.py` | `Offer` added beside `OfferRow` |
| `backend/src/sro/domain/observation/device.py` | `AgentDevice.revoked_at`, `revoked` |
| `backend/src/sro/application/ports/repositories.py` | six protocols; `UnitOfWork` properties |
| `backend/src/sro/application/ports/agent.py` | `AgentDrivers.drop` |
| `backend/src/sro/infrastructure/db/models.py` | sixteen table rows |
| `backend/src/sro/infrastructure/db/repositories.py` | `SqlUnitOfWork` wires the new repositories; `SqlDeviceRepository` learns revocation |
| `backend/src/sro/infrastructure/agent/sockets.py` | `DeviceSockets.drop` |
| `backend/src/sro/infrastructure/agent/drivers.py` | `drop` on the drivers |
| `backend/tests/unit/fakes.py` | `FakeAsker`, `FakeChannel` |

---

## Task 0: The branch

**Files:** none.

- [ ] **Step 1: Branch**

```bash
git checkout rig-into-backend-1
git checkout -b rig-into-backend-2
```

- [ ] **Step 2: Record the baseline**

```bash
cd backend
uv run mypy src tests 2>&1 | tail -1
uv run ruff format --check . 2>&1 | tail -1
uv run lint-imports 2>&1 | tail -1
```

Expected: 312 errors in 68 files; 2 files would be reformatted; 4 contracts
kept. Write all three into the ledger.

**Done by the controller, not a subagent.**

---

## Task 1: The records the store keeps

**Files:**
- Create: `backend/src/sro/domain/execution/workflow_run.py`
- Create: `backend/src/sro/domain/observation/pool.py`
- Create: `backend/src/sro/domain/observation/mining.py`
- Create: `backend/src/sro/domain/chat/reading.py`
- Modify: `backend/src/sro/domain/observation/gesture.py`
- Modify: `backend/src/sro/domain/skill/offers.py`
- Test: `backend/tests/unit/domain/rig/test_workflow_run.py`

**Interfaces:**
- Consumes: nothing outside the domain.
- Produces: `WorkflowRun`, `RunStep`, `OUTCOMES`, `VERDICTS`, `new_run_id`,
  `PoolEntry`, `K_POOL_AGE`, `K_POOL_DAYS`, `RETIRED_AGE`, `RETIRED_STALE`,
  `MiningPass`, `ChatReading`, `GestureBatch`, `Offer` — every repository in
  Tasks 4-8 stores and returns these and nothing else.

Sources, to be copied field for field: `new_agent_arch/src/rig/runs.py`
(`OUTCOMES`, `VERDICTS`, `new_run_id`, `RunStep`, `Run`),
`new_agent_arch/src/rig/pool.py` lines 1-52 (`K_POOL_AGE`, `K_POOL_DAYS`,
`RETIRED_AGE`, `RETIRED_STALE`, `PoolEntry`), the `passes` and `chats` and
`batches` and `offers` tables in `new_agent_arch/src/rig/store.py`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/unit/domain/rig/test_workflow_run.py`, both names from
`new_agent_arch/tests/test_runs.py`:

```python
def test_a_run_id_has_the_shape_the_other_ids_have() -> None:
    run_id = new_run_id()
    assert run_id.startswith("run_")
    assert len(run_id) == len("run_") + 32


def test_the_vocabularies_are_closed() -> None:
    assert set(OUTCOMES) == {"running", "held", "stopped", "refused", "aborted", "failed"}
    assert set(VERDICTS) == {
        "held",
        "failed",
        "unclear",
        "withheld",
        "refused",
        "skipped",
        "awaiting",
        "done_by_operator",
    }
```

- [ ] **Step 2: Run them and watch them fail**

`uv run pytest tests/unit/domain/rig/test_workflow_run.py -v` — ImportError.

- [ ] **Step 3: Write the records**

`domain/execution/workflow_run.py` takes the rig's `Run` renamed
`WorkflowRun` (the backend's `domain/execution/run.py` already owns `Run`),
its `RunStep` unchanged, and the two vocabulary tuples with their
docstrings. `dict[str, Any]` on `sent`, `result` and `withheld` entries
becomes `dict[str, object]`; `values: dict[str, str]` is unchanged.

`domain/observation/pool.py` takes `PoolEntry` and the four constants with
their docstrings verbatim. The ageing rule itself is not here — it is SQL,
and it lives with the repository in Task 4.

`domain/observation/mining.py`:

```python
@dataclass(frozen=True, slots=True)
class MiningPass:
    """One reading of one tenant's day, and what it cost.

    A pass makes exactly one model call. Every workflow it found names this
    pass rather than carrying a copy of its bill: three workflows out of one
    $0.04 call summed to $0.12 when they each carried it.
    """

    id: str
    tenant: str
    started_at: str
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    proposed: int = 0
    kept: int = 0
    rejected: int = 0
    coverage: float = 0.0
    skew: float = 0.0
    lopsided: bool = False
    error: str | None = None
```

`domain/chat/reading.py`:

```python
@dataclass(frozen=True, slots=True)
class ChatReading:
    """One sentence the chat door read, and what the reading cost.

    The sentence is not kept: it is an operator's words about a warehouse,
    and the bill is what this record is for.
    """

    id: str
    tenant: str
    at: str
    workflow_id: str | None = None
    in_tokens: int = 0
    out_tokens: int = 0
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    error: str | None = None
```

`domain/observation/gesture.py` gains, beside `Gesture`:

```python
@dataclass(frozen=True, slots=True)
class GestureBatch:
    """What one upload said about itself.

    ``started_at`` and ``ended_at`` are the device's own clock for the window
    the batch covers, against ``received_at``'s server clock; ``recording_id``
    names which teaching recording a demonstration batch belongs to.
    """

    batch_id: str
    device_id: str
    tenant: str
    mode: str
    received_at: str
    started_at: str = ""
    ended_at: str = ""
    recording_id: str | None = None
    accepted: int = 0
    rejected: int = 0
```

`domain/skill/offers.py` gains, beside the existing `OfferRow` (which stays
exactly what `counsel_over` reads):

```python
@dataclass(frozen=True, slots=True)
class Offer:
    """One offer the extension made from a recognised prefix, and its fate."""

    id: str
    tenant: str
    workflow_id: str
    device_id: str
    k: int
    fate: str
    at: str
    run_id: str | None = None
```

- [ ] **Step 4: Run the tests**

`uv run pytest tests/unit/domain/rig -q` — all pass.

- [ ] **Step 5: Gates**

`uv run mypy src tests | tail -1` (no growth), `uv run lint-imports`
(4 kept), `uv run ruff check` and `ruff format` on the touched files.

- [ ] **Step 6: Commit**

```bash
git add src/sro/domain/execution/workflow_run.py src/sro/domain/observation/pool.py \
        src/sro/domain/observation/mining.py src/sro/domain/chat/reading.py \
        src/sro/domain/observation/gesture.py src/sro/domain/skill/offers.py \
        tests/unit/domain/rig/test_workflow_run.py
git commit -m "feat(domain): the records a store has to keep"
```

---

## Task 2: Asking a model

**Files:**
- Create: `backend/src/sro/application/ports/model.py`
- Create: `backend/src/sro/application/shared/locks.py`
- Create: `backend/src/sro/infrastructure/gemini/asker.py`
- Modify: `backend/tests/unit/fakes.py`
- Test: `backend/tests/unit/infrastructure/test_asking_a_model.py`

**Interfaces:**
- Consumes: `sro.domain.shared.prices` — `Answer`, `Effort`, `price`,
  `is_priced` (all landed in plan 1).
- Produces: `Asker` (the port every rig model call goes through),
  `GeminiAsker`, `build_config`, `truncated`, `K_MAX_OUTPUT_TOKENS`,
  `one_at_a_time`, `FakeAsker`.

Source: `new_agent_arch/src/rig/models.py`. Everything above `PRICES` and
below `is_priced` travels; the pricing tables themselves are already in
`sro.domain.shared.prices` and are imported, never copied.

- [ ] **Step 1: Write the failing tests**

Copy all 22 tests from `new_agent_arch/tests/test_models.py` that plan 1 left
behind, keeping their names:

`test_a_fake_asker_records_what_it_was_asked`,
`test_a_fake_asker_runs_out_and_says_so`,
`test_the_request_config_never_enables_search_grounding`,
`test_the_request_config_lets_the_model_finish_a_whole_day`,
`test_gemini_asker_names_a_cut_off_answer_rather_than_calling_it_not_json`,
`test_gemini_asker_happy_path_parses_data_and_prices_it`,
`test_gemini_asker_reports_a_blocked_response_as_an_error`,
`test_gemini_asker_reports_non_json_text_as_an_error`,
`test_gemini_asker_flags_unpriced_when_usage_metadata_is_missing`,
`test_gemini_asker_flags_unpriced_when_usage_counts_are_none`,
`test_gemini_asker_flags_unpriced_for_an_unknown_model`,
`test_gemini_asker_survives_the_client_raising`,
`test_a_call_that_never_returned_does_not_claim_to_be_free`,
`test_gemini_asker_ask_really_routes_through_build_config`,
`test_the_config_carries_the_effort_and_still_no_tools`,
`test_no_effort_builds_no_thinking_config`,
`test_gemini_asker_hands_the_effort_to_the_config`,
`test_an_empty_instruction_is_not_sent_as_an_empty_part`,
`test_thinking_tokens_are_part_of_the_bill`,
`test_a_lock_belongs_to_the_loop_that_asked_for_it`,
`test_one_loop_gets_one_lock_per_name`,
`test_the_lock_still_excludes`.

Change only the imports: `rig.models` becomes
`sro.infrastructure.gemini.asker` for the asker and its config,
`sro.application.shared.locks` for the lock, `tests.unit.fakes` for
`FakeAsker`, and `sro.domain.shared.prices` for `Answer`.

- [ ] **Step 2: Run them and watch them fail**

`uv run pytest tests/unit/infrastructure/test_asking_a_model.py -v`.

- [ ] **Step 3: The port**

`application/ports/model.py`:

```python
"""The structured-output port every mined-workflow model call goes through.

The backend's ``IntentParser`` stays for utterances. This is the seam the
reading loop, the mining pass, the planner, the verifier and the chat door
all ask through, and the one place a fake goes in for every test that would
otherwise cost money.
"""

from __future__ import annotations

from typing import Protocol

from sro.domain.shared.prices import Answer, Effort


class Asker(Protocol):
    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, object],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer: ...
```

- [ ] **Step 4: The lock**

`application/shared/locks.py` takes `one_at_a_time` and its `_LOCKS`
weak-keyed dictionary from `rig/models.py` verbatim, docstring and all.
Create `application/shared/__init__.py` if the package does not exist.

- [ ] **Step 5: The asker**

`infrastructure/gemini/asker.py` takes `K_MAX_OUTPUT_TOKENS`, `truncated`,
`build_config` and `GeminiAsker` from `rig/models.py` verbatim, with these
changes and no others:

- `schema: dict[str, Any]` becomes `dict[str, object]` on every signature
  (`build_config` and `ask`). The value handed to the SDK is `dict(schema)`.
- `price`, `is_priced`, `Answer` and `Effort` are imported from
  `sro.domain.shared.prices`.
- The module docstring keeps the sentence about search grounding: it is
  never enabled, because it voids zero data retention and this process reads
  live customer payloads.

`GeminiAsker.__init__` keeps its `client: Any | None = None` escape hatch
for tests; `Any` here is the SDK's own untyped client, and this module is
already in the mypy per-module `Any` allowance list — add it there if it is
not (`pyproject.toml`, beside `sro.application.capture.rig_wire`).

- [ ] **Step 6: The fake**

`FakeAsker` from `rig/models.py` goes into `backend/tests/unit/fakes.py`
verbatim, keeping the comment explaining why it awaits `asyncio.sleep(0)`.

- [ ] **Step 7: Run the tests**

`uv run pytest tests/unit/infrastructure/test_asking_a_model.py -q` — 22
pass.

- [ ] **Step 8: Gates and commit**

```bash
git commit -m "feat(model): the port every reading asks through, and Gemini behind it"
```

---

## Task 3: The channel to a browser

**Files:**
- Create: `backend/src/sro/application/ports/channel.py`
- Create: `backend/src/sro/infrastructure/agent/channel.py`
- Modify: `backend/src/sro/infrastructure/agent/sockets.py`
- Modify: `backend/src/sro/infrastructure/agent/drivers.py`
- Modify: `backend/src/sro/application/ports/agent.py`
- Modify: `backend/tests/unit/fakes.py`
- Test: `backend/tests/unit/infrastructure/test_the_channel_carries_the_envelope.py`

**Interfaces:**
- Consumes: `DeviceSockets` (`infrastructure/agent/sockets.py`) as it stands.
- Produces: `Reply`, `Channel` (the port plan 3's runner and verifier send
  every command through), `SocketChannel`, `FakeChannel`,
  `DeviceSockets.drop`, `AgentDrivers.drop`.

The backend already runs the rig's channel: `DeviceSockets` is
`rig/channel.py::DeviceChannel` with tenant-keyed sockets, the same envelope
(`command_id`, `kind`, `run_id`, `deadline_ms`, `payload`), the same busy
handling and the same late-answer rule. Do not write a second one. What is
missing is a port the runner can hold, a `drop`, and two behaviours the rig's
channel had that the backend's does not.

- [ ] **Step 1: Write the failing tests**

`backend/tests/unit/infrastructure/test_the_channel_carries_the_envelope.py`.
Three names from `new_agent_arch/tests/test_channel.py` — the backend's
`test_the_channel_to_a_browser.py` already covers the other eight, and a
second copy of a passing test is not a port:

- `test_an_explicit_deadline_is_honoured_and_a_non_positive_one_never_ships`
  — a non-positive deadline answers `ok=False, error_kind="timeout"` and
  nothing reaches the socket.
- `test_the_fake_channel_answers_by_kind_and_remembers_what_was_sent` —
  against `FakeChannel`.
- `test_a_revoked_browser_is_dropped_and_reads_as_offline` — new name for
  the rig's `drop`: after `drop`, `online()` does not name the device and a
  `send` raises `DeviceUnreachable`.

Plus one this plan owes:

- `test_the_channel_port_carries_the_kinds_a_run_sends` — `SocketChannel`
  passes `kind`, `payload`, `run_id` and the deadline through unchanged for
  each of `ui.url`, `screenshot`, `ui.perform`, `ui.perform_at`, `http.send`,
  `navigate` and `abort`.

- [ ] **Step 2: Run them and watch them fail**

- [ ] **Step 3: The port**

`application/ports/channel.py`:

```python
"""One command down, one answer back.

The extension dials out and the backend sends commands down the socket it
opened; there is no route that drives a browser, because one would let a
leaked device id reach a browser that is not the caller's.

This is the seam a run holds. ``AgentDrivers`` is the typed view of the same
sockets for the backend's own executor; a mined workflow sends the envelope
itself, because what it sends is what the demonstration recorded.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from sro.domain.shared.identifiers import DeviceId, TenantId


@dataclass(frozen=True, slots=True)
class Reply:
    ok: bool
    result: Mapping[str, object] = field(default_factory=dict)
    error_kind: str | None = None
    error_detail: str | None = None

    @property
    def detail(self) -> str:
        """What went wrong, keeping the kind the extension named."""
        if self.error_kind and self.error_detail:
            return f"{self.error_kind}: {self.error_detail}"
        return self.error_detail or self.error_kind or ""


class Channel(Protocol):
    async def send(
        self,
        tenant_id: TenantId,
        device_id: DeviceId,
        *,
        kind: str,
        payload: Mapping[str, object],
        run_id: str | None = None,
        deadline_s: float | None = None,
    ) -> Reply: ...

    def online(self, tenant_id: TenantId) -> tuple[DeviceId, ...]: ...

    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool: ...
```

- [ ] **Step 4: `drop` on the sockets**

`DeviceSockets` gains:

```python
    def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        """Forget whatever socket this device holds: it is offline from here
        on, whether or not the browser has noticed.

        The one caller is a tenant revoking a browser, and a revoked browser
        that still read as connected would be an audit line nobody could
        trust.
        """
        key = _key(tenant_id, device_id)
        self._busy.pop(key, None)
        return self._sockets.pop(key, None) is not None
```

`AgentDrivers` gains `def drop(self, tenant_id: TenantId, device_id: DeviceId) -> bool`
with that docstring, and `SocketAgentDrivers` in `drivers.py` implements it
by delegating.

- [ ] **Step 5: The adapter**

`infrastructure/agent/channel.py`:

```python
class SocketChannel:
    """The ``Channel`` port over the sockets the API worker already holds."""

    def __init__(self, sockets: DeviceSockets) -> None:
        self._sockets = sockets

    async def send(...) -> Reply:
        if deadline_s is not None and deadline_s <= 0:
            # Not folded into `timeout_s or default`: that could not express a
            # short deadline near zero and let a negative one reach the wire.
            return Reply(ok=False, error_kind="timeout", error_detail="a non-positive deadline")
        answer = await self._sockets.send(
            tenant_id, device_id, kind=kind, payload=payload, run_id=run_id, timeout_s=deadline_s
        )
        return Reply(
            ok=answer.ok,
            result=answer.result,
            error_kind=answer.error_kind,
            error_detail=answer.error_detail,
        )
```

with `online` and `drop` delegating.

- [ ] **Step 6: The fake**

`FakeChannel` from `rig/channel.py` into `backend/tests/unit/fakes.py`,
answering `Reply`, keyed by kind, recording every envelope, and answering an
unscripted kind with `not_actionable` — a test that forgot to script a kind
must fail the way a real run would rather than hang. Its `send` takes the
port's signature (tenant first).

- [ ] **Step 7: Run the tests, gates, commit**

```bash
git commit -m "feat(channel): the port a run sends its own envelope down"
```

---

## Task 4: The evidence plane

**Files:**
- Create: `backend/migrations/versions/20260907_0037_the_evidence_plane.py`
- Create: `backend/src/sro/infrastructure/db/evidence.py`
- Modify: `backend/src/sro/infrastructure/db/models.py`
- Modify: `backend/src/sro/application/ports/repositories.py`
- Modify: `backend/src/sro/infrastructure/db/repositories.py`
- Test: `backend/tests/integration/test_evidence_repositories.py`

**Interfaces:**
- Consumes: `Gesture`, `GestureBatch`, `Intent`, `ValueSeen`, `PoolEntry`,
  `Call`, `PageMark` (domain), `Base` (`infrastructure/db/models.py`).
- Produces: `GestureRepository`, `PoolRepository`, `uow.gestures`,
  `uow.pool`.

Source of every column: the `batches`, `gestures`, `intents`,
`orphan_requests`, `orphan_pages` and `pool` tables in
`new_agent_arch/src/rig/store.py`, and the queries in `rig/api.py`,
`rig/pool.py`, `rig/mine.py`, `rig/shapes.py` and `rig/runner.py` that read
them (`grep -n "FROM gestures\|FROM intents\|FROM pool\|FROM batches" new_agent_arch/src/rig/*.py`).
Every comment in the rig's DDL explaining *why* a column exists travels to
the SQLAlchemy row or to the migration; a column whose reason is lost is a
column the next person drops.

- [ ] **Step 1: Write the failing tests**

`backend/tests/integration/test_evidence_repositories.py`, against the
`session_factory` fixture in `tests/integration/conftest.py`:

- `test_a_batch_id_is_not_written_twice` (from `test_store.py`) — the second
  save of a batch id is refused, and the first batch's rows stand.
- `test_a_gesture_survives_the_round_trip_with_its_calls_and_page_marks`
- `test_the_device_clock_and_the_recording_a_batch_belongs_to_are_kept`
- `test_another_tenants_gestures_are_not_returned`
- `test_an_intent_replaces_the_reading_before_it`
- `test_a_reading_can_record_that_its_cost_is_not_trustworthy` (from
  `test_store.py`)
- `test_gestures_with_no_reading_yet_are_the_ones_the_loop_takes` — the
  `LEFT JOIN intents ... WHERE i.gesture_id IS NULL` query, ordered by `at`.
- `test_an_orphaned_request_keeps_the_batch_and_the_tab_it_came_from`
- `test_the_same_orphan_twice_is_one_row`
- `test_an_unclaimed_gesture_enters_the_pool_at_age_zero_and_a_cited_one_leaves`
- `test_re_entering_the_pool_does_not_reset_the_clock`
- `test_only_what_a_reading_was_shown_ages`
- `test_an_empty_window_still_moves_what_everything_waited`
- `test_an_entry_past_its_age_retires_and_says_which_cap_retired_it`
- `test_an_entry_older_than_the_stale_window_retires_as_stale`
- `test_a_retired_entry_is_not_offered_and_is_still_readable_with_its_reason`

The last seven are the `test_pool.py` rules that are SQL. The remaining 14
`test_pool.py` tests drive `mine()`'s use of the pool and are plan 3.

- [ ] **Step 2: Run them and watch them fail**

`uv run pytest tests/integration/test_evidence_repositories.py -v`

- [ ] **Step 3: The tables**

In `infrastructure/db/models.py`, six rows. Column for column from the rig,
with the type changes the constraint list names:

`GestureBatchRow` (`gesture_batches`): `batch_id` PK `String(64)`,
`tenant_id`, `device_id`, `mode`, `started_at`/`ended_at` `String(64)`
defaulting `""` (the device's own clock, kept as it was sent),
`recording_id` nullable, `received_at` `DateTime(timezone=True)`,
`accepted`/`rejected` integers.

`GestureRow` (`gestures`): `id` PK, `tenant_id`, `stream_id`, `batch_id`,
`at` `Float` (Unix seconds — recorder.js's own format, and every ordering in
the rig is on it), `url`, `system`, `tab_id` `Integer`, `frame_url`,
`page_url`, `gesture` JSONB, `requests` JSONB default list, `page_events`
JSONB default list. Indexes `ix_gestures_tenant_at (tenant_id, at)` and
`ix_gestures_stream (tenant_id, stream_id, at)`.

`IntentRow` (`intents`): `gesture_id` PK, `tenant_id`, `act`, `object_`
(column name `object`), `system`, `page`, `values_seen` JSONB default list,
`continues`, `confidence`, `why`, `model`, `in_tokens`, `out_tokens`,
`thought_tokens`, `cost_usd` `Float`, `unpriced` `Boolean`, `created_at`
`DateTime(timezone=True)`, `error`. Index `ix_intents_tenant_created
(tenant_id, created_at)` — the spend sum reads it.

`OrphanRequestRow` (`orphan_requests`): PK `(batch_id, request_id)`,
`tenant_id`, `payload` JSONB.

`OrphanPageRow` (`orphan_pages`): `id` `BigInteger` identity PK, `batch_id`,
`tenant_id`, `at` `String(64)`, `payload` JSONB.

`PoolRow` (`mining_pool`): PK `(tenant_id, gesture_id)`, `age`, `waited`,
`retired` `Boolean`, `reason` default `""`, `entered_at`
`DateTime(timezone=True)`. Keep the rig's two-clock comment: `age` counts
readings the entry was shown and not cited, `waited` counts passes it was
passed over, and one counter cannot be both.

- [ ] **Step 4: The migration**

`20260907_0037_the_evidence_plane.py`, `revision = "0037"`,
`down_revision = "0036"`. Creates the six tables and their indexes.
`downgrade()` drops them in reverse. The docstring says what the evidence
plane is and why the rig's `rowid` tiebreak became `id bigserial` on
`orphan_pages`.

- [ ] **Step 5: The protocols**

In `application/ports/repositories.py`:

```python
class GestureRepository(Protocol):
    """The evidence plane: what a browser sent, what was read out of it."""

    async def add_batch(self, batch: GestureBatch) -> None:
        """Raises ``Conflict`` if that batch id was already written.

        An upload retried after its answer was lost must not be stored twice:
        the second copy would double every gesture in it and be mined as a
        second doing of the same job.
        """
        ...

    async def add_gestures(self, gestures: tuple[Gesture, ...]) -> None: ...

    async def gestures_for(
        self, tenant_id: TenantId, *, ids: tuple[str, ...] | None = None
    ) -> tuple[Gesture, ...]:
        """Ordered by ``at``. ``ids`` narrows to a citation set."""
        ...

    async def unread(self, tenant_id: TenantId, *, limit: int) -> tuple[Gesture, ...]:
        """Gestures with no intent row yet, oldest first."""
        ...

    async def save_intent(self, intent: Intent) -> None:
        """Replaces any earlier reading of that gesture."""
        ...

    async def intents_for(self, tenant_id: TenantId) -> tuple[Intent, ...]: ...

    async def add_orphan_request(
        self, tenant_id: TenantId, *, batch_id: str, request_id: str, payload: Mapping[str, object]
    ) -> None:
        """The same orphan twice is one row."""
        ...

    async def add_orphan_page(
        self, tenant_id: TenantId, *, batch_id: str, at: str, payload: Mapping[str, object]
    ) -> None: ...

    async def batch_owner(self, batch_id: str) -> str | None:
        """Which device uploaded that batch. ``None`` when nothing did."""
        ...

    async def count(self, tenant_id: TenantId) -> int: ...

    async def streams(self, tenant_id: TenantId) -> tuple[tuple[str, float, int], ...]:
        """(stream id, the last gesture's ``at``, how many), newest first."""
        ...


class PoolRepository(Protocol):
    """Evidence a pass did not place, waiting to be shown again."""

    async def add_unclaimed(
        self, tenant_id: TenantId, *, window_ids: tuple[str, ...], claimed: frozenset[str]
    ) -> int: ...

    async def age(self, tenant_id: TenantId, *, shown: tuple[str, ...] | None = None) -> int: ...

    async def waiting(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]: ...

    async def ids(self, tenant_id: TenantId) -> tuple[str, ...]: ...

    async def retired(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]: ...
```

- [ ] **Step 6: The implementation**

`infrastructure/db/evidence.py` holds `SqlGestureRepository` and
`SqlPoolRepository` with their private row↔record mappers. `mappers.py` is
not touched: a repository's mapping lives with it.

`add_unclaimed` is the rig's: delete every claimed id first — in full, not
only where it intersects the window, because a pooled gesture is packed into
the window beside fresh ones — then `INSERT ... ON CONFLICT DO NOTHING` for
each uncited id, so a gesture that has sat unplaced through three passes
keeps the age those passes gave it.

`age` is the rig's `age_pool`, with `INSERT OR IGNORE` becoming `ON CONFLICT
DO NOTHING` and the three-valued-logic branch kept: an empty `shown` moves
`waited` for every live entry rather than folding into a `NOT IN ()` that
matches nothing.

- [ ] **Step 7: Wire the unit of work**

`uow.gestures` and `uow.pool` on the `UnitOfWork` protocol and on
`SqlUnitOfWork.__aenter__`.

- [ ] **Step 8: Run the tests, gates, commit**

Also run `uv run pytest tests/integration/test_the_migrations_run.py` — it
applies every migration to an empty database, and the new one has to pass it.

```bash
git commit -m "feat(store): the evidence plane, on Postgres"
```

---

## Task 5: Workflows, their steps, and the passes that found them

**Files:**
- Create: `backend/migrations/versions/20260907_0038_workflows_and_passes.py`
- Create: `backend/src/sro/infrastructure/db/workflows.py`
- Modify: `models.py`, `ports/repositories.py`, `db/repositories.py`
- Test: `backend/tests/integration/test_workflow_repositories.py`

**Interfaces:**
- Consumes: `Workflow`, `Step`, `MiningPass`, `RunProof` (domain).
- Produces: `WorkflowRepository`, `uow.workflows`.

Sources: `rig/workflows.py` (`save_workflow`, `known_workflows`),
`rig/effects.py` (`record_effect`, `forget_effects`, the `earned` query),
`rig/mine.py` (the `passes` insert and the `rekey` update), `rig/runner.py`
(the `workflow_stale` insert and delete), `rig/api.py` (the stale count).

- [ ] **Step 1: Write the failing tests**

Four names from `new_agent_arch/tests/test_workflows.py`:
`test_a_workflow_survives_a_round_trip`,
`test_a_workflow_names_the_pass_that_found_it`,
`test_another_tenants_workflows_are_not_returned`,
`test_saving_the_same_workflow_twice_keeps_one`.

Plus the effects and stale rules, which plan 1 ported as pure rules and
which nothing has yet proven against a store:

- `test_an_effect_is_recorded_once_per_step_of_a_run`
- `test_a_failed_write_forgets_every_effect_the_workflow_had`
- `test_the_proof_a_run_leaves_is_read_back_as_the_domain_reads_it` — the
  repository builds one `RunProof` per live held run from
  `workflow_run_steps` and `workflow_effects`, and `earned_from` decides.
  (Depends on Task 6's tables. **Do Task 6 before this test**, or mark it
  and land it in Task 6 — the plan's order is 4, 6, 5 for this reason; see
  the ledger's pre-flight.)
- `test_a_step_only_the_weakest_rung_found_is_marked_stale_once`
- `test_a_step_that_matched_properly_again_is_not_stale_any_more`
- `test_a_pass_records_what_it_cost_even_when_it_found_nothing`

- [ ] **Step 2: Run them and watch them fail**

- [ ] **Step 3: The tables**

`WorkflowRow` (`workflows`): `id` PK, `tenant_id`, `pass_id` default `""`,
`title`, `narrative`, `systems` JSONB, `parameters` JSONB, `shape_key`
JSONB, `same_as`, `unproven` JSONB, `created_at` timestamptz. Index
`(tenant_id, created_at)`.

`WorkflowStepRow` (`workflow_steps`): PK `(workflow_id, ord)`, `says`,
`system`, `cites` JSONB, `parameters` JSONB.

`WorkflowStaleRow` (`workflow_stale`): PK `(workflow_id, ord)`,
`matched_by`, `noticed_at` timestamptz. Keep the rig's comment: one row per
step, so a workflow run daily reports the same weak step once rather than
daily.

`WorkflowEffectRow` (`workflow_effects`): PK `(workflow_id, run_id, ord)`,
`verified_by`, `at` timestamptz. Keep the comment: never by a picture; three
runs whose every write is in here is what buys a job the right to write
unasked, and one failed write empties it.

`MiningPassRow` (`mining_passes`): `id` PK, `tenant_id`, `started_at`
timestamptz, the five token/cost columns, `proposed`, `kept`, `rejected`,
`coverage`, `skew`, `lopsided`, `error`. Index `(tenant_id, started_at)`.

- [ ] **Step 4: The migration** — `0038`, down_revision `0037`.

- [ ] **Step 5: The protocol**

```python
class WorkflowRepository(Protocol):
    async def save(self, workflow: Workflow) -> None:
        """Whole workflow, steps replaced rather than appended."""
        ...

    async def known(self, tenant_id: TenantId) -> tuple[Workflow, ...]:
        """Oldest first, which is the order the miner resolves against."""
        ...

    async def get(self, tenant_id: TenantId, workflow_id: str) -> Workflow: ...

    async def rekey(self, tenant_id: TenantId, workflow_id: str, key: tuple[str, ...]) -> None: ...

    async def add_pass(self, mining_pass: MiningPass) -> None: ...

    async def mark_stale(
        self, workflow_id: str, ord_: int, *, matched_by: str, noticed_at: str
    ) -> None: ...

    async def clear_stale(self, workflow_id: str, ord_: int) -> None: ...

    async def stale_count(self, workflow_id: str) -> int: ...

    async def record_effect(
        self, workflow_id: str, *, run_id: str, ord_: int, verified_by: str, at: str
    ) -> None: ...

    async def forget_effects(self, workflow_id: str) -> int:
        """How many were forgotten. One failed write empties the register."""
        ...

    async def proofs(self, tenant_id: TenantId, workflow_id: str) -> tuple[RunProof, ...]:
        """One per live run of this workflow that held, for ``earned_from``."""
        ...
```

- [ ] **Step 6: The implementation, the unit of work, the tests, commit**

```bash
git commit -m "feat(store): workflows, the steps they cite, and what they earned"
```

---

## Task 6: Runs, their steps, and the approvals on them

**Files:**
- Create: `backend/migrations/versions/20260907_0039_workflow_runs.py`
- Create: `backend/src/sro/infrastructure/db/workflow_runs.py`
- Modify: `models.py`, `ports/repositories.py`, `db/repositories.py`
- Test: `backend/tests/integration/test_workflow_run_repositories.py`

**Interfaces:**
- Consumes: `WorkflowRun`, `RunStep` (Task 1).
- Produces: `WorkflowRunRepository`, `uow.workflow_runs`.

Source: `rig/runs.py` in full, plus the approval insert and the awaiting
queries in `rig/api.py`.

- [ ] **Step 1: Write the failing tests**

Six names from `new_agent_arch/tests/test_runs.py`:
`test_a_run_round_trips_with_every_step_and_every_withheld_write`,
`test_saving_again_replaces_the_steps_rather_than_appending`,
`test_a_run_still_running_when_the_rig_starts_is_failed_and_says_why`,
`test_the_flags_a_run_carries_survive_the_round_trip`,
`test_an_orphan_with_no_step_at_all_gets_one_that_says_who_failed`,
`test_the_reason_lands_on_the_step_the_orphan_died_in`.

Plus the approval rules, from `test_api.py`/`test_devices.py`, kept by name
where they were repository-shaped and renamed where the route half is plan 4:

- `test_the_first_tap_wins_and_a_second_on_the_same_step_is_not_a_second_authorisation`
  — `ON CONFLICT DO NOTHING`, and the stored `device_id` is the first
  approver's.
- `test_an_approval_names_the_browser_whose_panel_the_tap_came_from`
- `test_a_run_waiting_on_a_person_is_found_by_the_step_that_is_awaiting`
- `test_another_tenants_run_is_not_found`

- [ ] **Step 2: Run them and watch them fail**

- [ ] **Step 3: The tables**

`WorkflowRunRow` (`workflow_runs`): `id` PK, `tenant_id`, `workflow_id`,
`device_id`, `values` JSONB, `started_by`, `live` `Boolean`, `allow_focus`
`Boolean`, `started_at` timestamptz, `finished_at` nullable timestamptz,
`outcome` default `"running"`, `withheld` JSONB default list (the writes a
dry run produced and did not send, in full — this is what a person reads
before pressing through to live), the five token/cost columns. Index
`(tenant_id, workflow_id, started_at)` and `(tenant_id, device_id, outcome)`
— the second is the busy check, which asks whether this browser already has
a run in flight.

`WorkflowRunStepRow` (`workflow_run_steps`): PK `(run_id, ord)`, `says`,
`planned_by`, `sent` JSONB nullable, `result` JSONB nullable, `verdict`,
`verdict_by`, `reason`, `matched_by`, `stale` `Boolean`, `before_url`,
`after_url`, the five token/cost columns.

`ApprovalRow` (`approvals`): PK `(run_id, ord)`, `at` timestamptz,
`device_id` nullable. The rig's comment travels: the first tap wins.

- [ ] **Step 4: The migration** — `0039`, down_revision `0038`.

- [ ] **Step 5: The protocol**

```python
class WorkflowRunRepository(Protocol):
    async def save(self, run: WorkflowRun) -> None:
        """Whole run, every time: called after every step so the panel can
        poll, with steps replaced rather than appended."""
        ...

    async def get(self, tenant_id: TenantId, run_id: str) -> WorkflowRun | None:
        """``None``, not ``NotFound``: every caller answers 404 itself."""
        ...

    async def for_workflow(self, tenant_id: TenantId, workflow_id: str) -> tuple[WorkflowRun, ...]: ...

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        """The run this browser is already driving, if any."""
        ...

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]:
        """(run id, step ord, what the step says) for every step waiting on a
        person, across browsers: anyone may answer a parked run."""
        ...

    async def approve(self, run_id: str, ord_: int, *, at: str, device_id: str | None) -> bool:
        """Whether this tap was the one that authorised the step."""
        ...

    async def approvals(self, run_id: str) -> tuple[tuple[int, str, str | None], ...]: ...

    async def fail_orphans(self, reason: str) -> int:
        """Every run still ``running`` is marked failed, and how many there were.

        Called once at startup, across tenants — nobody is making the request.
        One worker owns every run, so a row that says ``running`` when the
        process starts is a run nobody is driving. The reason lands on the
        last step, or on a new step when the run never reached one.
        """
        ...
```

- [ ] **Step 6: The implementation, the unit of work, the tests, commit**

```bash
git commit -m "feat(store): a run, its steps, and who said yes"
```

---

## Task 7: Offers, chats, and revoking a browser

**Files:**
- Create: `backend/migrations/versions/20260907_0040_offers_chats_and_revocation.py`
- Create: `backend/src/sro/infrastructure/db/offers.py`
- Modify: `models.py`, `ports/repositories.py`, `db/repositories.py`,
  `domain/observation/device.py`
- Test: `backend/tests/integration/test_offer_repositories.py`

**Interfaces:**
- Consumes: `Offer`, `OfferRow`, `counsel_over`, `K_WINDOW` (domain),
  `ChatReading`, `AgentDevice`.
- Produces: `OfferRepository`, `ChatRepository`, `AgentDevice.revoked_at`,
  `DeviceRepository.revoke`, `uow.offers`, `uow.chats`.

Source: `rig/offers.py`'s two selects and its insert, the `chats` insert and
select in `rig/api.py`, `rig/devices.py`'s `revoke`.

- [ ] **Step 1: Write the failing tests**

From `new_agent_arch/tests/test_offers.py`, the one left by name plus the
three whose repository half plan 1 owed:

- `test_an_offer_is_recorded_under_an_id_of_its_own` — `off_` + 32 hex, one
  row.
- `test_an_arrival_nudge_is_not_evidence_either_way` — the `k > 0` filter is
  in the query.
- `test_only_the_newest_ten_offers_are_read` — `LIMIT K_WINDOW`.
- `test_offers_in_the_same_second_are_read_in_the_order_they_arrived` — the
  `ORDER BY at DESC, seq DESC` tiebreak, which is what the rig's `rowid`
  did.

Plus:

- `test_a_chat_reading_records_what_it_cost_and_never_the_sentence`
- `test_revoking_a_browser_stops_it_speaking_for_itself`
- `test_revoking_twice_is_not_a_second_revocation` — returns `False`.

- [ ] **Step 2: Run them and watch them fail**

- [ ] **Step 3: The tables and the column**

`OfferRow` (`offers`): `id` PK, `seq` `BigInteger` identity (the tiebreak
the rig got from `rowid`; two offers in the same second are read in the
order they arrived), `tenant_id`, `workflow_id`, `device_id`, `k`, `fate`,
`run_id` nullable, `at` timestamptz. Index
`(tenant_id, workflow_id, at)`.

`ChatRow` (`chats`): `id` PK, `tenant_id`, `workflow_id` nullable, the five
token/cost columns, `error`, `at` timestamptz. Index `(tenant_id, at)` — the
day's sum reads it.

`AgentDeviceRow` gains `revoked_at` nullable timestamptz, and
`AgentDevice` gains `revoked_at: str | None = None` with a `revoked`
property. Nothing in this plan refuses a revoked device — that is the auth
dependency, plan 4 — but the column and the record are what it will read.

- [ ] **Step 4: The migration** — `0040`, down_revision `0039`. Creates the
two tables and adds the one column.

- [ ] **Step 5: The protocols**

```python
class OfferRepository(Protocol):
    async def record(self, offer: Offer) -> None: ...

    async def newest(
        self, tenant_id: TenantId, workflow_id: str, *, limit: int
    ) -> tuple[OfferRow, ...]:
        """Newest first, ``at`` then arrival — the window ``counsel_over``
        reads. Nudges (``k = 0``) are excluded: an arrival is not evidence
        either way."""
        ...

    async def newest_for_device(
        self, tenant_id: TenantId, workflow_id: str, device_id: DeviceId, *, limit: int
    ) -> tuple[OfferRow, ...]:
        """The same window, one browser's. Resting is per browser."""
        ...

    async def fates(self, tenant_id: TenantId, workflow_id: str) -> Mapping[str, int]: ...


class ChatRepository(Protocol):
    async def record(self, reading: ChatReading) -> None: ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[ChatReading, ...]: ...
```

`DeviceRepository` gains:

```python
    async def revoke(self, tenant_id: TenantId, device_id: DeviceId, *, at: str) -> bool:
        """Whether there was a live browser to revoke."""
        ...
```

- [ ] **Step 6: The implementation, the unit of work, the tests, commit**

```bash
git commit -m "feat(store): what was offered, what a sentence cost, and a browser withdrawn"
```

---

## Task 8: The day's spend, and what the audit reads

**Files:**
- Create: `backend/src/sro/infrastructure/db/spend.py`
- Modify: `ports/repositories.py`, `db/repositories.py`, and the four
  repository modules (each gains its `since` read)
- Test: `backend/tests/integration/test_spend_and_audit_reads.py`

**Interfaces:**
- Consumes: the four billed tables — `intents`, `mining_passes`,
  `workflow_runs`, `chats`.
- Produces: `SpendRepository`, `uow.spend`, and a `since` read on gestures,
  workflow runs, offers, chats and devices.

Source: `spent_today` and `SPENT_IN` in `rig/api.py`, and the audit's own
queries there. The rule stays exactly the rig's: sum `cost_usd` over the
four tables since midnight UTC, each with its own timestamp column, and
report separately how many of those rows were blind (`unpriced`) — a day
whose cost cannot be trusted is not a cheap day.

`over_cap` itself is a pure rule and belongs to plan 3's
`application/intent/spend.py`; this task only produces the numbers it
judges.

- [ ] **Step 1: Write the failing tests**

- `test_the_day_sums_every_table_that_can_be_billed`
- `test_a_row_from_yesterday_is_not_in_todays_day` — the midnight UTC
  boundary, proven with a row one second either side.
- `test_a_blind_row_is_counted_as_blind_and_still_summed`
- `test_another_tenants_spending_is_not_in_this_days`
- `test_the_audit_reads_each_kind_since_a_time_newest_first`
- `test_a_since_with_no_zone_is_read_as_utc` — the `since` normalisation the
  spec names.

- [ ] **Step 2: Run them and watch them fail**

- [ ] **Step 3: The protocol**

```python
@dataclass(frozen=True, slots=True)
class DaySpend:
    cost_usd: float
    blind: int


class SpendRepository(Protocol):
    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend:
        """Everything this tenant has been billed for since midnight UTC.

        Four tables, one predicate each: a reading, a mining pass, a run and
        a chat are the only things that cost money, and a cap that reads
        three of them is a cap.
        """
        ...
```

`DaySpend` lives in `domain/shared/prices.py`, beside `Answer`.

- [ ] **Step 4: The implementation and the `since` reads**

`SqlSpendRepository` issues the four `SUM(cost_usd)` /
`SUM(unpriced::int)` selects. Each of the four repositories gains a
`since(tenant_id, *, since: str)` read returning its own records, newest
first, which is what plan 3's audit use case assembles.

- [ ] **Step 5: Tests, gates, commit**

```bash
git commit -m "feat(store): the day, and the four tables that can bill it"
```

---

## Task 9: The count, and what is left

**Files:**
- Modify: this plan (ledger table), `docs/17-agent-architecture.md` note if
  the design doc's phase-2 line needs correcting.

- [ ] **Step 1: Count**

Count the tests this plan added and the rig tests it ported by name. Fill in
the table below. Every rig test in `test_models.py`, `test_channel.py`,
`test_store.py`, `test_runs.py`, `test_workflows.py`, `test_offers.py`,
`test_pool.py` and `test_devices.py` is accounted for as ported, left to
plan 3, left to plan 4, or **dropped with a reason** — the SQLite migration
ladder is gone, so `test_store.py`'s `ADDED_COLUMNS` tests do not travel and
the alembic migration test replaces them.

- [ ] **Step 2: Deferred minors**

Land every minor the task reviews deferred to this batch.

- [ ] **Step 3: Gates and commit**

```bash
git commit -m "docs(plan): what plan 2 ported, and what plans 3 and 4 still owe"
```

---

## Ledger

| Rig test file | Rig / ported here | Left, and to which plan |
|---|---|---|
| `test_models.py` | 26 / 22 | 4 ported in plan 1 (pricing) |
| `test_channel.py` | 11 / | |
| `test_store.py` | 7 / | |
| `test_runs.py` | 8 / | |
| `test_workflows.py` | 5 / | |
| `test_offers.py` | 10 / | |
| `test_pool.py` | 21 / | |
| `test_devices.py` | 13 / | |
| **Total** | | |

**Added by this plan:** (fill in)

**Gates at head:** ruff clean; format 2 pre-existing; contracts 4 kept;
mypy 312 baseline; `tests/unit` and `tests/integration` green.
