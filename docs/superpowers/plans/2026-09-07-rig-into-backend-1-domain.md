# The rig into the backend, plan 1 of 5: the backup branch and the domain

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Park the rule-based mining on a backup branch, and move every pure module of the rig into the backend's domain layer with its tests, under the backend's import contracts and no-Any typing, without changing what any of it computes.

**Architecture:** The rig's records, shape key, identity resolution, parameter learning, served shape, offers counsel, locator ladder, verify belts, earned rule, planner schemas and prices are arithmetic and prompts with no I/O. They become modules under `backend/src/sro/domain/`, named so they do not collide with the backend's existing `earned.py`, `locator.py`, `parameter.py`, `plan.py`, `verdict.py`. The rig's wire models (pydantic) go to `application/capture/rig_wire.py`, and `correlate` (wire to domain) to `application/observation/correlate.py`, because the domain tests build gestures through them. Nothing in this plan touches storage, routes, the extension or the rig package itself.

**Tech Stack:** Python 3.12, `uv`, pytest, mypy strict with `disallow_any_explicit` and `disallow_any_generics` on `sro.domain.*` and `sro.application.*`, import-linter (`uv run lint-imports`), ruff.

**Spec:** `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`

## Global Constraints

- Domain modules import nothing from `sro.application`, `sro.infrastructure`, `sro.interface`, `sro.container`, `sro.config`, `fastapi`, `sqlalchemy`, `temporalio`, `httpx`, `boto3`, `playwright` (import-linter contract "Domain is pure"). `pydantic` is not on that list but is not used in the domain either: the domain's gesture types are frozen dataclasses.
- No explicit `Any` and no bare generics in `sro.domain.*` and `sro.application.*` except modules listed in the mypy override; this plan adds exactly one, `sro.application.capture.rig_wire`.
- Every ported test keeps its name and its assertions. A test that needed the rig's SQLite store does not move in this plan; it is listed by name under the task that leaves it for plan 3, and the count is written in the ledger.
- Behaviour does not change. Constants keep their values: `K_TEXT_IDENTITY_MAX = 40`, `K_SAME_EVIDENCE = 0.5`, `K_SAME_JOB = 0.5`, `K_MIN_SHARED_STEPS = 2`, `K_EARNED_RUNS = 3`, `STATE_BELTS = ("status", "read")`, `K_OFFER_AFTER = 2`, `K_WINDOW = 10`, `K_ENOUGH = 3`, `K_QUIET_HOURS = 24`, `K_WEAK_LOCATORS = frozenset({"css_path", None})`.
- The pipeline is green after every task: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src tests && uv run lint-imports && uv run pytest tests/unit -q`.
- Commits end with the two trailers the repository uses (`Co-Authored-By`, `Claude-Session`).
- Never delete, move, rename or stage an untracked file. `backend/Untitled`, `backend/.gmail-token.json.old-client`, `backend/old-client_secret_*.disabled` and every `rig.db*` stay where they are.

---

## File map

| Creates | Responsibility | From |
|---|---|---|
| `backend/src/sro/application/capture/rig_wire.py` | the extension's batch protocol, pydantic | `new_agent_arch/src/rig/wire.py` |
| `backend/src/sro/application/observation/correlate.py` | wire batch to domain gestures, `system_of` | `new_agent_arch/src/rig/correlate.py` |
| `backend/src/sro/domain/observation/gesture.py` | `Component`, `Target`, `Action`, `Gesture`, `ValueSeen`, `Intent`, `Body`, `Call` | `new_agent_arch/src/rig/records.py` and the fields of `wire.py` the domain reads |
| `backend/src/sro/domain/observation/trim.py` | what of a gesture reaches a prompt | `new_agent_arch/src/rig/trim.py` |
| `backend/src/sro/domain/skill/workflow.py` | `Step`, `Workflow`, `cited_ids` | `new_agent_arch/src/rig/workflows.py` (dataclasses only) |
| `backend/src/sro/domain/observation/identity.py` | `target_identity`, `shape_key`, `containment`, `jaccard`, `Resolution`, `resolve` | `new_agent_arch/src/rig/shape.py`, `identity.py` |
| `backend/src/sro/domain/skill/learned.py` | `control_name`, `Parameter`, `parameters_across` | `new_agent_arch/src/rig/parameters.py` |
| `backend/src/sro/domain/skill/offers.py` | `FATES`, `REFUSED`, the four `K_`, `Counsel`, `counsel_over`, `clamped` | `new_agent_arch/src/rig/offers.py` (rule half) |
| `backend/src/sro/domain/skill/shape.py` | `Shape`, `typed_at`, `walkable`, `shape_of` | `new_agent_arch/src/rig/shapes.py` (pure half) |
| `backend/src/sro/domain/execution/evidence.py` | locator ladder, `origin_of`, `primary_gesture`, `recorded_call`, `writes`, `allowlist` | `new_agent_arch/src/rig/locators.py` |
| `backend/src/sro/domain/execution/belts.py` | `Verdict`, `expected_statuses`, `confirming_read`, `mentions`, `K_WEAK_LOCATORS`, `RunProof`, `earned_from`, `state_verified` | `new_agent_arch/src/rig/verify.py` (pure half), `effects.py` (rule) |
| `backend/src/sro/domain/execution/planning.py` | `PLAN_SCHEMA`, `SIGHT_SCHEMA`, `SIGHT_ACTIONS`, both instruction strings, `KINDS`, `Planned`, `Look`, `value_for`, `unreplayable` | `new_agent_arch/src/rig/planner.py` (pure half) |
| `backend/src/sro/domain/shared/prices.py` | `PRICES`, `price`, `is_priced`, `Answer` | `new_agent_arch/src/rig/models.py` (pricing and the answer record) |
| `backend/tests/unit/domain/rig/…` | the ported tests | `new_agent_arch/tests/…` |
| `backend/tests/unit/domain/rig/conftest.py` | `BATCH` fixture and `gestures()` helper | `new_agent_arch/tests/fixtures.py` |

Modifies: `backend/pyproject.toml` (one mypy override line).

---

### Task 0: The backup branch

**Files:** none in the tree.

- [ ] **Step 1: Create and push the branch**

```bash
cd /Users/devansh.j/GreyOrange/AI-SRO
git branch backup/rule-based-mining main
git push origin backup/rule-based-mining
git log --oneline -1 backup/rule-based-mining
```

Expected: the last line names the same commit as `main`.

- [ ] **Step 2: Record it**

Append to `docs/17-agent-architecture.md`, at the top under the title:

```markdown
> **Superseded on 2026-09-07.** The mining half of this document (segment,
> cluster, the signature, the miner) is replaced by
> `docs/new-agent-doc-arc/README.md` and is being ported per
> `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`.
> The code as it stood is on the branch `backup/rule-based-mining`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/17-agent-architecture.md
git commit -m "docs: the rule-based mining is superseded, and where it went"
```

---

### Task 1: The wire models and the correlator, in the application layer

**Files:**
- Create: `backend/src/sro/application/capture/rig_wire.py`
- Create: `backend/src/sro/application/observation/correlate.py`
- Modify: `backend/pyproject.toml` (mypy override)
- Test: `backend/tests/unit/application/test_rig_wire.py`

**Interfaces:**
- Produces: `rig_wire.Batch`, `rig_wire.parse_batch(raw: dict[str, object]) -> tuple[Batch, list[RejectedEvent]]`, `rig_wire.REDACTED`, `rig_wire.redact_url`; `correlate.correlate(batch: Batch, tenant: str) -> tuple[list[Gesture], list[Request], list[PageEvent], int]`, `correlate.system_of(url: str | None) -> str | None`. Same names and signatures as the rig.
- Consumes: `sro.domain.observation.gesture` from Task 2. Do Task 2 first; this task's test needs both.

- [ ] **Step 1: Copy the wire models**

```bash
cp new_agent_arch/src/rig/wire.py backend/src/sro/application/capture/rig_wire.py
```

Then edit the module docstring's first line to read `"""The extension's batch protocol, as the rig defined it. Pydantic, because it is a wire format."""` and leave everything else as it is. The file imports only pydantic and the standard library.

- [ ] **Step 2: Allow `Any` in that one module**

In `backend/pyproject.toml`, the override that names `sro.application.induction.jsonutil`:

```toml
module = ["sro.application.induction.jsonutil", "sro.application.capture.decode", "sro.application.capture.rig_wire"]
```

- [ ] **Step 3: Copy the correlator and repoint its imports**

```bash
cp new_agent_arch/src/rig/correlate.py backend/src/sro/application/observation/correlate.py
```

Replace the two rig imports at the top with:

```python
from sro.application.capture.rig_wire import Batch, GestureEvent, PageEvent, RequestEvent, SnapshotEvent
from sro.domain.observation.gesture import Gesture, new_gesture_id
```

Where `correlate` builds a `Gesture(...)`, it passes `gesture=event.gesture` (a wire `Gesture`). The domain `Gesture.action` is a frozen dataclass (Task 2), so replace that argument with `action=as_action(event.gesture)` and add at the bottom of the file:

```python
def as_action(wire: WireGesture) -> Action:
    """The wire gesture as the domain sees it: the fields the arithmetic
    reads, and nothing the recorder might add next week."""
    target = wire.target
    component = target.component if target else None
    return Action(
        kind=wire.kind,
        value=wire.value,
        secret=wire.secret,
        at=wire.at,
        url=wire.url,
        target=None
        if target is None
        else Target(
            tag=target.tag,
            role=target.role,
            name=target.name,
            secret=target.secret,
            text=target.text,
            test_id=target.testId,
            css_path=target.cssPath,
            xpath=target.xpath,
            component=None
            if component is None
            else Component(
                item_id=component.itemId,
                query=component.query,
                field_label=component.fieldLabel,
                name=component.name,
                xtype=component.xtype,
            ),
        ),
    )
```

with `from sro.application.capture.rig_wire import Gesture as WireGesture` and `from sro.domain.observation.gesture import Action, Component, Target` added to the imports. `requests` and `page_events` on the domain `Gesture` keep the wire `Request` and `PageEvent` types for now: those two are read by `evidence.py` and `belts.py` through the `Call` view in Task 2, Step 3.

- [ ] **Step 4: Write the test**

`backend/tests/unit/application/test_rig_wire.py`:

```python
"""The rig's protocol arrives whole: a batch parses, one bad event does not
cost the batch, and the correlator hands the domain what the arithmetic reads."""

from sro.application.capture.rig_wire import Batch, parse_batch
from sro.application.observation.correlate import correlate, system_of
from tests.unit.domain.rig.conftest import BATCH


def test_the_measured_batch_parses_and_correlates() -> None:
    batch, rejected = parse_batch(BATCH)
    assert rejected == []
    gestures, requests, pages, dropped = correlate(batch, "acme")
    assert len(gestures) == 7
    assert {g.action.kind for g in gestures} == {"type", "select", "upload", "click", "press"}
    typed = next(g for g in gestures if g.action.value == "ACME-4471")
    assert typed.action.target and typed.action.target.name == "Client Code"
    assert typed.system == "http://127.0.0.1:63319"


def test_one_unparseable_event_does_not_cost_the_batch() -> None:
    raw = dict(BATCH, events=[*BATCH["events"], {"kind": "gesture", "gesture": {"kind": "wave"}}])
    batch, rejected = parse_batch(raw)
    assert len(rejected) == 1 and rejected[0].index == len(BATCH["events"])
    assert len(batch.events) == len(BATCH["events"])


def test_system_of_is_the_origin() -> None:
    assert system_of("https://wms.example:8443/a/b?c=1") == "https://wms.example:8443"
    assert system_of(None) is None
    assert system_of("about:blank") is None
```

- [ ] **Step 5: Run, then commit**

```bash
cd backend && uv run pytest tests/unit/application/test_rig_wire.py -q && uv run mypy src tests && uv run lint-imports
git add src/sro/application/capture/rig_wire.py src/sro/application/observation/correlate.py pyproject.toml tests/unit/application/test_rig_wire.py
git commit -m "feat(observation): the rig's wire protocol and correlator, in the application layer"
```

---

### Task 2: The domain gesture

**Files:**
- Create: `backend/src/sro/domain/observation/gesture.py`
- Create: `backend/tests/unit/domain/rig/__init__.py`, `backend/tests/unit/domain/rig/conftest.py`
- Test: `backend/tests/unit/domain/rig/test_gesture.py`

**Interfaces:**
- Produces: `Component(item_id, query, field_label, name, xtype)`, `Target(tag, role, name, secret, text, test_id, css_path, xpath, component)`, `Action(kind, value, secret, at, url, target)`, `Gesture(id, tenant, stream_id, batch_id, at, url, system, tab_id, frame_url, action, page_url, requests, page_events)`, `ValueSeen(field, value)`, `Intent(...)` with the rig's fields, `new_gesture_id() -> str`, `Body(text, size_bytes, mime_type, redacted_fields, blob_uri)`, `Call(method, url, request_headers, request_body, status, response_body)`.

- [ ] **Step 1: Write the module**

```python
"""What the rig keeps of a gesture, as the arithmetic reads it.

Frozen, framework-free. The wire format the extension speaks is
`sro.application.capture.rig_wire`; `correlate` there turns one into these.
Every module in the domain that reads a control's identity, a typed value or
a recorded call reads it from here and from nowhere else.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Literal

Kind = Literal["click", "type", "select", "press", "upload", "scroll", "hover"]


def new_gesture_id() -> str:
    return "ges_" + secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class Component:
    """What an ExtJS page knows about the control; None on plain HTML."""

    item_id: str | None = None
    query: str | None = None
    field_label: str | None = None
    name: str | None = None
    xtype: str | None = None


@dataclass(frozen=True, slots=True)
class Target:
    tag: str | None = None
    role: str | None = None
    name: str | None = None
    secret: bool = False
    text: str | None = None
    test_id: str | None = None
    css_path: str | None = None
    xpath: str | None = None
    component: Component | None = None


@dataclass(frozen=True, slots=True)
class Action:
    """The gesture itself: what was done, to what, with what typed."""

    kind: Kind
    at: float
    value: str | None = None
    secret: bool = False
    url: str | None = None
    target: Target | None = None


@dataclass(frozen=True, slots=True)
class Body:
    text: str | None = None
    size_bytes: int = 0
    mime_type: str | None = None
    redacted_fields: tuple[str, ...] = ()
    blob_uri: str | None = None


@dataclass(frozen=True, slots=True)
class Call:
    """A recorded exchange, the part of it the belts read: never a response
    body's text beyond what `confirming_read` compares."""

    method: str
    url: str
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: Body | None = None
    status: int | None = None
    response_body: Body | None = None


@dataclass(frozen=True, slots=True)
class PageMark:
    at: float
    page_kind: str
    url: str | None = None
    detail: str | None = None


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
    action: Action
    page_url: str | None = None
    requests: list[Call] = field(default_factory=list)
    page_events: list[PageMark] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
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
    thought_tokens: int = 0
    cost_usd: float = 0.0
    unpriced: bool = False
    error: str | None = None
```

Note for the correlator (Task 1, Step 3): it builds `Call` and `PageMark` from the wire `Request` and `PageEvent` with `as_call(request)` and `as_mark(event)` defined beside `as_action`, copying the named fields; `Body.redacted_fields` is `tuple(body.redacted_fields)`.

- [ ] **Step 2: The fixture**

`backend/tests/unit/domain/rig/conftest.py`:

```python
"""The one measured batch every rig test was built on, and the gestures it
correlates to. Copied from `new_agent_arch/tests/fixtures.py`; the constant
is the same bytes."""

from sro.application.capture.rig_wire import Batch
from sro.application.observation.correlate import correlate
from sro.domain.observation.gesture import Gesture

BATCH: dict[str, object] = {  # paste the dict from new_agent_arch/tests/fixtures.py verbatim
}


def gestures(tenant: str = "acme") -> list[Gesture]:
    found, _, _, _ = correlate(Batch.model_validate(BATCH), tenant)
    return found
```

Copy `BATCH` from `new_agent_arch/tests/fixtures.py` by hand; it is the only content of that file besides its docstring.

- [ ] **Step 3: The test**

`backend/tests/unit/domain/rig/test_gesture.py`:

```python
from sro.domain.observation.gesture import Action, Component, Gesture, Target, new_gesture_id


def test_a_gesture_id_has_the_rig_shape() -> None:
    assert new_gesture_id().startswith("ges_") and len(new_gesture_id()) == 36


def test_the_domain_gesture_is_built_from_parts_and_the_parts_are_frozen() -> None:
    action = Action(
        kind="type",
        at=1.0,
        value="ACME-4471",
        target=Target(name="Client Code", component=Component(item_id="clientCode")),
    )
    g = Gesture(
        id="ges_1", tenant="acme", stream_id="s", batch_id="b", at=1.0, url=None,
        system="http://127.0.0.1:63319", tab_id=1, frame_url=None, action=action,
    )
    assert g.action.target and g.action.target.component
    assert g.action.target.component.item_id == "clientCode"
    try:
        action.value = "x"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("an action changed after the fact")
```

- [ ] **Step 4: Run, then commit**

```bash
cd backend && uv run pytest tests/unit/domain/rig -q && uv run mypy src tests && uv run lint-imports
git add src/sro/domain/observation/gesture.py tests/unit/domain/rig
git commit -m "feat(domain): the gesture as the rig's arithmetic reads it"
```

---

### Task 3: The workflow

**Files:**
- Create: `backend/src/sro/domain/skill/workflow.py`
- Test: `backend/tests/unit/domain/rig/test_workflow.py`

**Interfaces:**
- Produces: `Step(order, says, system, cites: list[str], parameters: list[str])`, `Workflow(id, tenant, title, narrative, systems, steps, parameters: list[dict[str, object]], unproven: list[str], shape_key, same_as, pass_id)`, `cited_ids(workflow) -> set[str]`, `new_workflow_id() -> str`.

- [ ] **Step 1: Copy the dataclasses**

From `new_agent_arch/src/rig/workflows.py` take `new_workflow_id`, `Step`, `Workflow`, `cited_ids` verbatim. Leave `save_workflow` and `known_workflows` behind (plan 3). Replace `parameters: list[dict[str, Any]]` with `parameters: list[dict[str, object]]`; every reader in this plan indexes it with `isinstance` checks already.

- [ ] **Step 2: The test**

Port `new_agent_arch/tests/test_workflows.py`: keep the tests that build a `Workflow` and assert on `cited_ids` or the id shape; leave for plan 3 any test that calls `save_workflow`, `known_workflows` or takes a `store`. List the left ones by name in the ledger.

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): the workflow and its steps"
```

---

### Task 4: Identity: the shape key and resolution

**Files:**
- Create: `backend/src/sro/domain/observation/identity.py`
- Test: `backend/tests/unit/domain/rig/test_shape.py`, `backend/tests/unit/domain/rig/test_identity.py`

**Interfaces:**
- Produces: `ShapeKey`, `target_identity(gesture) -> str`, `K_TEXT_IDENTITY_MAX`, `shape_key(gestures) -> ShapeKey`, `containment`, `jaccard`, `K_SAME_EVIDENCE`, `K_SAME_JOB`, `K_MIN_SHARED_STEPS`, `Resolution`, `resolve(proposal: Workflow, known: list[Workflow]) -> Resolution`.

- [ ] **Step 1: Copy both rig files into one module**

Concatenate `new_agent_arch/src/rig/shape.py` then `identity.py` (its docstring becomes a section comment). Replace imports with:

```python
from collections.abc import Set as AbstractSet

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Workflow
```

In `target_identity`, the rig reads `gesture.gesture.target`, `component.itemId`, `component.query`, `target.testId`; the domain names are `gesture.action.target`, `component.item_id`, `component.query`, `target.test_id`. In `shape_key`, `gesture.gesture.kind` becomes `gesture.action.kind`. Nothing else changes.

- [ ] **Step 2: Port the tests**

Copy `new_agent_arch/tests/test_shape.py` and `test_identity.py`. Replace `from rig.` imports with the new module paths; replace `_gestures()` helpers that use `correlate(Batch.model_validate(BATCH), ...)` with `from tests.unit.domain.rig.conftest import gestures`. Tests that build a `Gesture` by hand must build `Action(...)`/`Target(...)`/`Component(...)` with the snake_case names. Tests that need a store (`_store`, `save_batch`, `rekey`) stay for plan 3; list them.

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): the shape key and identity resolution, as the rig computed them"
```

---

### Task 5: Parameters learned across doings

**Files:**
- Create: `backend/src/sro/domain/skill/learned.py`
- Test: `backend/tests/unit/domain/rig/test_parameters.py`

**Interfaces:**
- Produces: `control_name(gesture) -> str | None`, `Parameter(name, seen)`, `parameters_across(doings: list[tuple[Workflow, Mapping[str, Gesture], list[Intent]]]) -> dict[str, Parameter]` (the rig's signature, unchanged).

- [ ] **Step 1: Copy `new_agent_arch/src/rig/parameters.py`**, repoint imports to `sro.domain.observation.gesture` and `sro.domain.skill.workflow`, and rename the attribute reads (`gesture.gesture.target` to `gesture.action.target`, `component.itemId` to `item_id`, `fieldLabel` to `field_label`, `gesture.gesture.value` to `gesture.action.value`).

- [ ] **Step 2: Port `test_parameters.py`** the same way. Every test there builds workflows and gestures by hand; none needs a store.

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): parameters learned across doings"
```

---

### Task 6: Offers: the fates and the counsel rule

**Files:**
- Create: `backend/src/sro/domain/skill/offers.py`
- Test: `backend/tests/unit/domain/rig/test_offers.py`

**Interfaces:**
- Produces: `FATES`, `REFUSED`, `K_OFFER_AFTER`, `K_WINDOW`, `K_ENOUGH`, `K_QUIET_HOURS`, `Counsel(offer_after, quiet_until)` with `as_json()`, `OfferRow(k: int, fate: str, at: str)`, `counsel_over(window: Sequence[OfferRow], newest_for_device: Sequence[OfferRow], now: datetime) -> Counsel`, `clamped(at: str, now: datetime) -> str`.

- [ ] **Step 1: Write the module**

Copy the constants, their docstrings, `Counsel` and `as_json` from `new_agent_arch/src/rig/offers.py`. Replace `record_offer` and `counsel` with the pure pair; the queries move to the application layer in plan 3:

```python
@dataclass(frozen=True, slots=True)
class OfferRow:
    k: int
    fate: str
    at: str


def clamped(at: str, now: datetime) -> str:
    """The browser's clock, never ahead of the rig's: parsed, made aware,
    and capped at `now`. `counsel_over` reads the newest offers and rests a
    job a day after the last refusal, and a browser a year fast would
    otherwise own the window, and the rest, for a year."""
    when = datetime.fromisoformat(at)
    when = (when if when.tzinfo else when.replace(tzinfo=UTC)).astimezone(UTC)
    return min(when, now).isoformat()


def counsel_over(
    window: Sequence[OfferRow], newest_for_device: Sequence[OfferRow], now: datetime
) -> Counsel:
    """`window`: the tenant's newest `K_WINDOW` offers of the job with k > 0,
    newest first. `newest_for_device`: the asking browser's newest `K_ENOUGH`
    of the same, newest first; empty when no browser is named. The rules are
    the rig's, unchanged: see `Counsel`."""
    offer_after = K_OFFER_AFTER
    diverged = [row.k for row in window if row.fate == "diverged"]
    if len(window) >= K_ENOUGH and 2 * len(diverged) >= len(window):
        offer_after = max(offer_after, max(diverged) + 1)
    quiet_until = None
    newest = list(newest_for_device)
    if len(newest) == K_ENOUGH and all(row.fate in REFUSED for row in newest):
        until = datetime.fromisoformat(newest[0].at) + timedelta(hours=K_QUIET_HOURS)
        if until > now:
            quiet_until = until.isoformat()
    return Counsel(offer_after=offer_after, quiet_until=quiet_until)
```

- [ ] **Step 2: Port `test_offers.py`**

Every test there goes through `record_offer` and `counsel` against a store. Rewrite each as a call to `counsel_over` with the rows it would have read: for example `test_three_refusals_running_rest_the_job_for_a_day_on_that_browser` becomes

```python
def test_three_refusals_running_rest_the_job_for_a_day_on_that_browser() -> None:
    rows = [OfferRow(2, "dismissed", _at(12)), OfferRow(2, "did_it", _at(11)), OfferRow(2, "dismissed", _at(10))]
    resting = counsel_over(rows, rows[:3], now=_when(13))
    assert resting.quiet_until == (_when(12) + timedelta(hours=K_QUIET_HOURS)).isoformat()
    assert counsel_over(rows, rows[:2], now=_when(13)).quiet_until is None, "two is not enough"
    assert counsel_over(rows, [], now=_when(13)).quiet_until is None, "no browser, no rest"
    assert counsel_over(rows, rows[:3], now=_when(12, day=7)).quiet_until is None, "the day passed"
```

with `_when(hour, day=6) -> datetime` and `_at(hour) -> str` helpers. Keep every rule the rig's tests pin: the default; refusal broken by expired or accepted; k = 0 excluded (that becomes the caller's query, so the test moves to plan 3 and is listed); diverged half-or-more with 3 of 6 moving and 3 of 7 not; the newest ten (a caller's `LIMIT`, plan 3); same-second order (caller's `rowid`, plan 3); the clamp, through `clamped`.

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): the offers' fates and the counsel rule, without the queries"
```

---

### Task 7: The served shape

**Files:**
- Create: `backend/src/sro/domain/skill/shape.py`
- Test: `backend/tests/unit/domain/rig/test_shapes.py`

**Interfaces:**
- Produces: `Shape(id, title, starts_on, hosts, shape, parameters, held_runs, offer_after, quiet_until)` with `as_json()`, `typed_at(cited: list[tuple[Gesture, Step]], parameter: dict[str, object]) -> int | None`, `walkable(cited) -> list[tuple[Gesture, Step]]`, `shape_of(workflow, cited, *, held: int, advice: Counsel) -> Shape | None`.

- [ ] **Step 1: Write the module**

Take `Shape`, `_typed_at` (renamed `typed_at`, with both passes and their comments) from `new_agent_arch/src/rig/shapes.py`. Then the pure remainder of `shapes_for`'s loop body as one function:

```python
def shape_of(
    workflow: Workflow, cited: list[tuple[Gesture, Step]], *, held: int, advice: Counsel
) -> Shape | None:
    """One workflow as the extension needs it, or None when it cannot be
    served: nothing cited, or a start its own evidence never names."""
    if not cited:
        return None
    gestures = [gesture for gesture, _ in cited]
    by_id = {g.id: g for g in gestures}
    first_step = min(workflow.steps, key=lambda s: s.order)
    first = primary_gesture(first_step, by_id) or gestures[0]
    starts_on = first.page_url or first.url
    hosts = sorted(allowlist(workflow, by_id))
    if system_of(starts_on) not in hosts:
        return None
    walk = walkable(cited)
    return Shape(
        id=workflow.id,
        title=workflow.title,
        starts_on=starts_on,
        hosts=hosts,
        shape=[list(triple) for triple in shape_key([g for g, _ in walk])],
        parameters=[
            {"name": str(p["name"]), "at": typed_at(walk, p)}
            for p in workflow.parameters
            if isinstance(p, dict) and p.get("name")
        ],
        held_runs=held,
        offer_after=max(K_OFFER_AFTER, min(advice.offer_after, len(walk) - 1)),
        quiet_until=advice.quiet_until,
    )


def walkable(cited: list[tuple[Gesture, Step]]) -> list[tuple[Gesture, Step]]:
    return [pair for pair in cited if target_identity(pair[0]) != "anon|scroll"]
```

`system_of` is `sro.application.observation.correlate.system_of` in Task 1, which the domain may not import. Move `system_of` into `sro.domain.shared.hosts` (a module that exists; add the function there with the rig's body) and import it from there in both the correlator and this module. The held gate (`ran and held == 0`) and the per-workflow queries stay in the application use case (plan 3).

- [ ] **Step 2: Port `test_shapes.py`**

Every test there goes through `shapes_for(store, ...)`. Rewrite the pure ones against `shape_of` with `cited` built from `gestures()` and a `Workflow` built by hand: the parameter index by the declaring step, the scroll dropped from the served shape, a parameter typed after a scroll, a badly declared parameter dropped, the cap at the last gesture but one and never under the default, a learned parameter placed by the control that typed it, a start the evidence never names refused. The held gate, the resting device, the stored-key recompute and the evidence-partly-gone tests stay for plan 3; list them.

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): the served shape, without the queries"
```

---

### Task 8: The evidence a plan acts on: locators

**Files:**
- Create: `backend/src/sro/domain/execution/evidence.py`
- Test: `backend/tests/unit/domain/rig/test_locators.py`

- [ ] **Step 1: Copy `new_agent_arch/src/rig/locators.py`** as `evidence.py`, repoint imports, rename attribute reads to the domain names (`gesture.action.target`, `target.component.query`, `target.test_id`, `target.css_path`), and change every `dict[str, Any]` to `dict[str, str]` (a locator is `{"strategy": ..., "query": ...}` and nothing else; assert that in the test).

- [ ] **Step 2: Port `test_locators.py`**; none of it needs a store.

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): the locator ladder and what a step's evidence says"
```

---

### Task 9: The belts: verify's decisions and the earned rule

**Files:**
- Create: `backend/src/sro/domain/execution/belts.py`
- Test: `backend/tests/unit/domain/rig/test_belts.py`

**Interfaces:**
- Produces: `Verdict(state, by, reason, answer=None)`, `expected_statuses`, `confirming_read`, `mentions(body: str, values: Mapping[str, str]) -> bool`, `K_WEAK_LOCATORS`, `K_EARNED_RUNS`, `STATE_BELTS`, `RunProof(run_id, wrote, verified)`, `earned_from(proofs: Sequence[RunProof]) -> bool`, `state_verified(verified_by: str) -> bool`.

- [ ] **Step 1: Write the module**

From `new_agent_arch/src/rig/verify.py` take `Verdict`, `expected_statuses`, `confirming_read`, `_leaves` and `_mentions` (renamed `mentions`), and `INSTRUCTIONS` with the verify schema. The `async def verify(...)` that sends a probe and asks a model stays for plan 3. From `runner.py` take `K_WEAK_LOCATORS`. From `effects.py` take the constants and make the rule pure. The rig's `earned` walks the workflow's live runs that held; a run counts when it has at least one write step (a `run_steps` row whose result says `wrote`) and every write step has a state-verified effect; `K_EARNED_RUNS` counting runs earn. Written pure:

```python
@dataclass(frozen=True, slots=True)
class RunProof:
    """One live run that held, reduced to the two sets the rule compares:
    the steps that wrote, and the steps a state belt verified."""

    run_id: str
    wrote: frozenset[int]
    verified: frozenset[int]

    @property
    def proves(self) -> bool:
        """A run with no write proves nothing about writing. One with a write
        a state belt did not see proves the opposite."""
        return bool(self.wrote) and self.wrote <= self.verified


def earned_from(proofs: Sequence[RunProof]) -> bool:
    """Whether a job may write unasked: `K_EARNED_RUNS` live held runs, each
    with every write verified by state (`STATE_BELTS`). Effects decided by
    screen are never recorded, so `verified` here is state by construction."""
    return sum(1 for proof in proofs if proof.proves) >= K_EARNED_RUNS


def state_verified(verified_by: str) -> bool:
    """The gate `record_effect` keeps: only a state belt's verdict is an effect."""
    return verified_by in STATE_BELTS
```

The application use case (plan 3) builds one `RunProof` per live held run from `run_steps` and `workflow_effects`, as the rig's `earned` query does, and calls `earned_from`.

- [ ] **Step 2: Port the tests**

From `test_verify.py`: every test of `expected_statuses`, `confirming_read`, `_mentions`. From `test_effects.py`: every test, rewritten to build `RunProof` rows instead of writing runs and effects to a store: three proving runs earn; two do not; a run with no write does not count; a run with one write unverified does not count; a screen-verified effect is not state (`state_verified("screen") is False`). `forget_effects` and the `finally`-block reset are repository and use-case behaviour (plan 3) and their tests are listed.

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): the verify belts and the earned rule, pure"
```

---

### Task 10: Planning: schemas, instructions and the value rule (and the whole of `trim.py`)

**Files:**
- Create: `backend/src/sro/domain/execution/planning.py`
- Test: `backend/tests/unit/domain/rig/test_planning.py`

- [ ] **Step 1: Write the module**

From `new_agent_arch/src/rig/planner.py` take `KINDS`, `PLAN_SCHEMA`, `INSTRUCTIONS` (renamed `PLAN_INSTRUCTIONS`), `Look`, `Planned`, `_value_for` (renamed `value_for`), `_unreplayable` (renamed `unreplayable`), `SIGHT_SCHEMA`, `SIGHT_ACTIONS`, `SIGHT_INSTRUCTIONS`. `plan_step` and `plan_by_sight` call the model and stay for plan 3. `Planned.answer: Answer` refers to `sro.domain.shared.prices.Answer` (Task 11); do Task 11 first. `dict[str, Any]` on the schemas becomes `dict[str, object]`; on `Planned.payload` it becomes `dict[str, object]` too.

Also from `new_agent_arch/src/rig/trim.py`: the whole file as `sro/domain/observation/trim.py` with imports repointed (`Body`, `Call`, `Target` from the domain gesture; `REDACTED` needs a home the domain may import: move the constant to `sro.domain.shared.hosts` beside `system_of`, and have `rig_wire.py` import it from there).

What landed (Task 10, commits b32c758..ca224dd): the whole of `trim.py` AND the rig's wire redaction engine with it -- all 29 definitions, the credential vocabulary included -- because `body_keys` applies those rules to every body that reaches a prompt and the domain may not import `sro.application`; `rig_wire.py` re-exports them. Task 12 then split the engine back out into `sro/domain/observation/redaction.py`, so `trim.py` is A2 again and the vocabulary has one address both belts import.

- [ ] **Step 2: Port the tests**

From `test_planner.py`: `test_the_schema_is_the_specs`-style tests, every `_value_for` test, `_unreplayable` tests, and the sight schema shape test (`SIGHT_SCHEMA`'s action enum is `["click", "type", "press"]`). The `plan_step`/`plan_by_sight` tests go to plan 3. From `test_trim.py`: everything.

Add one test that walks every `*_SCHEMA` in `sro.domain` for `additionalProperties` (the rig's `test_no_schema_in_the_package_uses_what_the_developer_api_refuses`, with `pkgutil` over `sro.domain`).

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): the planner's schemas, instructions and the value rule"
```

---

### Task 11: Prices and the answer record

**Files:**
- Create: `backend/src/sro/domain/shared/prices.py`
- Test: `backend/tests/unit/domain/rig/test_prices.py`

- [ ] **Step 1: Write the module**

From `new_agent_arch/src/rig/models.py` take `PRICES`, `price`, `is_priced`, `Effort`, and `Answer` (a frozen dataclass; `data: dict[str, object] | None`). `build_config`, `truncated`, `K_MAX_OUTPUT_TOKENS`, `GeminiAsker` and `FakeAsker` are infrastructure and test support, plan 2.

- [ ] **Step 2: Port from `test_models.py`** the three price tests (`a price is dollars per million tokens`, `an unknown model costs nothing and does not raise`, `a long prompt doubles gemini 3.1 pro rates`).

- [ ] **Step 3: Run, commit**

```bash
git commit -am "feat(domain): prices and the answer record"
```

---

### Task 12: The contracts hold, and the count is written down

**Files:**
- Modify: `docs/superpowers/plans/2026-09-07-rig-into-backend-1-domain.md` (this file: the ledger table at the end)

- [ ] **Step 1: The whole pipeline**

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src tests && uv run lint-imports && uv run pytest tests/unit -q
```

Expected: all green. `lint-imports` must report every contract kept; a domain module importing `sro.application` anywhere is a failed task, not a fixable warning.

- [ ] **Step 2: The count**

```bash
cd backend && uv run pytest tests/unit/domain/rig tests/unit/application/test_rig_wire.py -q | tail -1
cd ../new_agent_arch && uv run pytest tests/test_shape.py tests/test_identity.py tests/test_parameters.py tests/test_offers.py tests/test_shapes.py tests/test_locators.py tests/test_verify.py tests/test_effects.py tests/test_planner.py tests/test_trim.py tests/test_workflows.py tests/test_models.py -q | tail -1
```

Write both numbers, and the names of every test left for plan 3, into the table below. The ported count plus the left count must equal the rig's count for those files.

- [ ] **Step 3: Commit**

```bash
git commit -am "docs(plan): the domain is ported; what waits for the application layer"
```

## Ledger: tests left for a later plan

Counted 2026-09-07 at the head of this branch.

```
$ cd backend && uv run pytest tests/unit/domain/rig \
    tests/unit/application/test_rig_wire.py \
    tests/unit/application/test_rig_wire_protocol.py \
    tests/unit/application/test_correlate.py -q | tail -1
217 passed in 0.41s

$ cd new_agent_arch && uv run pytest tests/test_shape.py tests/test_identity.py \
    tests/test_parameters.py tests/test_offers.py tests/test_shapes.py \
    tests/test_locators.py tests/test_verify.py tests/test_effects.py \
    tests/test_planner.py tests/test_trim.py tests/test_workflows.py \
    tests/test_models.py tests/test_values.py tests/test_wire.py \
    tests/test_correlate.py -q -p no:cacheprovider | tail -1
282 passed in 3.06s
```

**Ported: 217 of 282.**

That line does not add up on its own, and the reason is worth writing down.
**197 of the rig's 282 tests are ported; 85 are left below; 197 + 85 = 282**,
which is the identity the plan wanted. The backend's 217 is those 197 plus
**20 tests this plan added** that no rig test is behind:

- `test_planning.py` (8): the three `unreplayable` cases, two `value_for`
  cases, `test_the_sight_schema_offers_only_the_actions_a_point_can_take`,
  `test_a_secret_gesture_carries_no_value_from_anywhere`, and the schema walk
  the plan itself asked for
  (`test_no_schema_in_the_package_uses_what_the_developer_api_refuses`).
- `test_belts.py` (3):
  `test_the_read_shows_a_whole_value_at_any_depth_and_never_a_substring_of_one`,
  which is `test_verify.py`'s two value-matching tests merged onto `mentions`
  (both rig originals are still counted as left, since only their pure half
  crossed); `test_a_status_is_read_off_the_reply_only_when_the_reply_carries_one`;
  and Task 12's untimed write.
- `test_rig_wire.py` (3): the batch that parses and correlates, `system_of`,
  and a second reading of `test_one_unparseable_event_does_not_cost_the_batch`
  (the port itself is in `test_rig_wire_protocol.py`).
- `test_gesture.py` (2), `test_workflow.py` (1): the domain types the rig had
  no separate tests for.
- One each in `test_locators.py`
  (`test_a_status_that_lies_about_completing_does_not_decide_the_origin`, from
  the Task 8 fix round), `test_trim.py`
  (`test_a_secret_flag_on_either_the_gesture_or_its_target_is_a_credential`)
  and `test_shapes.py` (Task 12's unsorted step list).

196 of the 197 ports keep the rig's own name. The one exception is
`test_css_path_and_xpath_are_not_sent_to_the_model`, which the rig spells
`test_cssPath_and_xpath_are_not_sent_to_the_model`.

| Rig test file | Rig / ported | Left behind (needs a store, a model call, or a query) |
|---|---|---|
| `test_shape.py` | 9 / 9 | — |
| `test_identity.py` | 15 / 15 | — |
| `test_parameters.py` | 14 / 14 | — |
| `test_values.py` | 16 / 16 | — |
| `test_locators.py` | 13 / 13 | — |
| `test_effects.py` | 9 / 9 | — |
| `test_wire.py` | 41 / 41 | — |
| `test_correlate.py` | 16 / 16 | — |
| `test_trim.py` | 33 / 32 | `test_no_credential_on_a_touched_control_reaches_either_prompt` (walks `parse_batch`, `save_batch`, `Store`, `_row_to_gesture` and `window.as_evidence`) |
| `test_offers.py` | 10 / 9 | `test_an_offer_is_recorded_under_an_id_of_its_own` (`record_offer` mints `off_` + 16 hex and inserts the row). Three more keep their names here with pure bodies and still owe plan 3 a repository-side test: the `k > 0` filter (`test_an_arrival_nudge_is_not_evidence_either_way`), the `LIMIT K_WINDOW` cut (`test_only_the_newest_ten_offers_are_read`) and the `ORDER BY at DESC, rowid DESC` tiebreak (`test_offers_in_the_same_second_are_read_in_the_order_they_arrived`) |
| `test_workflows.py` | 5 / 1 | `test_a_workflow_survives_a_round_trip`, `test_a_workflow_names_the_pass_that_found_it`, `test_another_tenants_workflows_are_not_returned`, `test_saving_the_same_workflow_twice_keeps_one` |
| `test_shapes.py` | 17 / 11 | `test_an_unproven_workflow_is_not_served`, `test_the_held_gate_is_per_workflow_and_never_silences_one_that_never_ran`, `test_a_workflow_that_cannot_be_served_never_withdraws_the_ones_behind_it`, `test_a_stored_key_from_an_older_rule_is_recomputed_once`, `test_a_workflow_whose_evidence_is_partly_gone_keeps_its_key`, `test_a_workflow_that_cannot_be_rekeyed_does_not_stop_the_others`. `test_a_resting_job_is_served_marked_for_the_browser_that_refused_it` is here by name; only the counsel query behind it is left |
| `test_verify.py` | 30 / 6 | The 24 that drive `async def verify(...)` through a fake channel and asker: `test_a_call_that_returned_the_status_the_evidence_expects_is_held_by_status`, `test_a_call_the_warehouse_rejected_is_failed_by_status`, `test_a_ui_step_is_confirmed_by_the_read_the_evidence_shows_the_page_makes`, `test_a_read_that_did_not_come_back_2xx_decides_nothing`, `test_the_read_matches_a_whole_value_not_a_substring_of_one`\*, `test_the_probe_never_carries_a_header_the_boundary_struck_out`, `test_a_status_that_already_decided_is_not_second_guessed_by_a_read`, `test_a_status_the_operator_also_got_is_still_a_refusal`, `test_the_screenshot_is_last_and_least`, `test_no_screenshot_and_no_state_is_unclear_not_held`, `test_a_command_the_browser_refused_is_failed_before_anything_is_verified`, `test_a_confirming_read_whose_url_carries_a_marker_is_never_sent`, `test_the_call_that_returned_exactly_400_is_a_refusal_not_a_success`, `test_a_2xx_the_evidence_never_saw_does_not_hold_by_status`, `test_with_no_status_in_the_evidence_only_a_2xx_holds`, `test_the_probe_is_a_bodiless_get_sent_to_this_run_and_this_browser`, `test_a_read_that_did_not_show_the_value_says_which_read_it_was`, `test_a_read_that_came_back_300_is_not_a_read_that_came_back`, `test_a_value_nested_inside_the_read_is_still_a_value_the_read_shows`\*, `test_a_read_that_is_not_json_is_matched_on_its_text`, `test_nothing_to_decide_on_is_unclear_and_says_so`, `test_a_model_that_answered_nothing_leaves_the_step_unclear_with_its_error`, `test_the_screen_verdict_is_the_models_own_word_and_its_own_reason`, `test_the_screen_belt_is_told_the_step_the_command_and_both_pictures_words`. \*these two have their pure assertions ported onto `mentions`; only the belt-order path through `verify` is left |
| `test_planner.py` | 28 / 1 | The 27 `plan_step` / `plan_by_sight` tests: `test_a_ui_plan_carries_the_evidence_locators_not_the_models`, `test_the_values_the_run_was_given_are_what_the_model_sees_not_the_recorded_ones`, `test_an_http_plan_replays_the_recorded_call_with_redacted_headers_dropped`, `test_an_http_plan_whose_body_the_store_never_kept_is_downgraded_to_the_interface`, `test_a_model_that_could_not_answer_plans_nothing_and_says_why`, `test_a_kind_the_protocol_does_not_have_is_planned_as_nothing`, `test_a_retry_carries_the_failure_and_the_second_screenshot`, `test_an_http_plan_whose_url_carries_a_struck_out_credential_is_downgraded`, `test_every_way_out_hands_back_the_reading_that_paid_for_it`, `test_a_navigate_with_nowhere_to_go_is_not_a_navigate`, `test_the_why_on_the_plan_is_the_models_own_and_empty_when_it_gave_none`, `test_a_step_that_only_cites_a_scroll_is_still_planned_from_it`, `test_the_action_is_the_models_when_the_protocol_has_it_and_the_gestures_when_not`, `test_a_value_is_carried_for_every_action_that_takes_one_and_for_no_other`, `test_with_no_value_from_the_run_or_the_model_the_recorded_one_stands`, `test_a_recorded_call_with_no_body_is_replayed_as_it_was`, `test_an_http_plan_carries_the_body_the_operator_sent`, `test_an_http_plan_for_a_step_whose_evidence_made_no_call_plans_nothing`, `test_the_model_is_told_where_the_step_was_demonstrated_and_under_what_effort`, `test_a_rescue_is_shown_the_page_the_failed_attempt_left_behind`, `test_a_first_attempt_carries_no_second_picture`, `test_the_failed_attempts_picture_is_named_by_its_position`, `test_a_replayed_call_still_carries_the_answer_that_planned_it`, `test_the_sight_rung_is_asked_with_the_screen_its_size_and_the_demonstrated_control`, `test_the_corner_of_the_screen_is_on_it_and_its_far_edge_is_not`, `test_no_picture_no_size_or_no_answer_is_no_plan`, `test_nothing_to_type_is_no_plan_and_a_press_carries_no_value` |
| `test_models.py` | 26 / 4 | Plan **2**, not 3 — these need `GeminiAsker`, `FakeAsker`, `build_config`, `K_MAX_OUTPUT_TOKENS` and `one_at_a_time`, all infrastructure: `test_a_fake_asker_records_what_it_was_asked`, `test_a_fake_asker_runs_out_and_says_so`, `test_the_request_config_never_enables_search_grounding`, `test_the_request_config_lets_the_model_finish_a_whole_day`, `test_gemini_asker_names_a_cut_off_answer_rather_than_calling_it_not_json`, `test_gemini_asker_happy_path_parses_data_and_prices_it`, `test_gemini_asker_reports_a_blocked_response_as_an_error`, `test_gemini_asker_reports_non_json_text_as_an_error`, `test_gemini_asker_flags_unpriced_when_usage_metadata_is_missing`, `test_gemini_asker_flags_unpriced_when_usage_counts_are_none`, `test_gemini_asker_flags_unpriced_for_an_unknown_model`, `test_gemini_asker_survives_the_client_raising`, `test_a_call_that_never_returned_does_not_claim_to_be_free`, `test_gemini_asker_ask_really_routes_through_build_config`, `test_the_config_carries_the_effort_and_still_no_tools`, `test_no_effort_builds_no_thinking_config`, `test_gemini_asker_hands_the_effort_to_the_config`, `test_an_empty_instruction_is_not_sent_as_an_empty_part`, `test_thinking_tokens_are_part_of_the_bill`, `test_a_lock_belongs_to_the_loop_that_asked_for_it`, `test_one_loop_gets_one_lock_per_name`, `test_the_lock_still_excludes` |
| **Total** | **282 / 197** | **85** |

Also left with them, from the source modules: `save_workflow` and
`known_workflows` (`rig/workflows.py`); `record_offer`'s insert and
`counsel`'s two selects (`rig/offers.py`); `shapes_for`'s loop, held gate and
rekeying (`rig/shapes.py`); `async def verify(...)`, `record_effect`,
`forget_effects` and the `RunProof` query (`rig/verify.py`, `rig/effects.py`);
`plan_step`, `plan_by_sight`, `ACTIONS` and the `Asker`/`Effort` plumbing
(`rig/planner.py`); and `GeminiAsker`, `FakeAsker`, `build_config` and
`one_at_a_time` (`rig/models.py`, plan 2). The ingest use case also has to
keep the wire batch it parsed, because `correlate` returns domain values and
the orphan event's own row is no longer among them.
