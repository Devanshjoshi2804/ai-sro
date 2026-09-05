# Offer and Approve Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The extension recognises a proven job from its first two gestures and offers to finish it; a run started that way pauses before each write for a tap in the panel until the job has earned autonomy.

**Architecture:** Recognition is arithmetic and runs in the extension: the rig serves each proven workflow's `shape_key`, the service worker keeps a per-tab tail of gesture triples and matches it against cached shapes on every gesture, and one `target_identity` rule lives in Python with a generated JavaScript twin tested against one fixture. The offer reuses the nudge slot. The runner gains `from_step`, an `awaiting` verdict released by an approve route, and a `workflow_effects` table that decides when writes stop asking. The panel polls the rig run each second and draws it.

**Tech Stack:** Python 3.12, FastAPI, SQLite (`new_agent_arch/`); MV3 Chrome extension, ES modules, `node --test` (`new-chrome-extension/`); the backend's `generate_extension_recorder.py` as the generator for the JS twin.

**Spec:** `docs/superpowers/specs/2026-09-06-offer-and-approve-design.md`

## Global Constraints

- Never import from `sro.*` in `new_agent_arch/src/`. The generator lives in the backend and emits text; it never imports `rig`.
- Recognition uses no model. `Asker.ask` is not called on the offer path; search grounding is never enabled anywhere.
- `target_identity` has one Python definition (`rig/shape.py`) and one generated JavaScript twin (`new-chrome-extension/src/background/shape.generated.js`, written by `make gen-recorder`). Both are tested against `new-chrome-extension/fixtures/shape-identity.json`. Never hand-edit a generated file.
- Constants, verbatim: `K_TAIL = 12`, `K_OFFER_AFTER = 2`, `K_APPROVAL_WAIT_S = 300`, `K_EARNED_RUNS = 3`, `K_RUN_POLL_MS = 1000`. The shape cache reuses `CANDIDATES_FRESH_MS` (300 000) and the nudge reuses `LIFETIME_MS` (90 000).
- Credential values never reach a prompt, a payload, a stored record, a log line, or a route answer. A gesture whose control is secret contributes no value; the parameter is missing.
- `live` still defaults false at `POST /v1/runs`. An offer's Yes says `live: true` explicitly.
- Screen-only verification never counts as an effect. `workflow_effects` rows come only from `held` by `status` or `read`.
- Dry runs never pause. Earned workflows never pause. Everything else about the runner (allowlist before send, one rescue, the write-rescue gate, the `finally`) is unchanged.
- No offer on an unwatched tab, while `performing()`, while the operator is `busy`, or while muted. A rig that is down means no shapes, no offer, no error shown.
- Every new route takes the existing bearer (`Depends(authorised)`); the rig bearer never enters the panel realm.
- Gates: `new_agent_arch/`: `uv run ruff check src tests scripts`, `uv run ruff format --check src tests scripts`, `uv run mypy src`, `uv run pytest -q` (491 today). Repo root: `make test-extension`, `make lint-extension`. Backend: `uv run pytest tests/unit/infrastructure -q -k generated` after touching the generator.
- Commit only named files. Never `git add -A` (untracked credential files sit under `backend/`). Never commit `rig.db`.
- Commit trailer: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_013zJkLruANn5fw99AJZAHKu`.

## File Structure

| File | Responsibility |
|---|---|
| `new_agent_arch/src/rig/shapes.py` (new) | `shapes_for(store, tenant)`: the served shape entries, `parameters[].at` derived from `seen_values` |
| `new_agent_arch/src/rig/store.py` | tables `offers`, `workflow_effects` |
| `new_agent_arch/src/rig/offers.py` (new) | `record_offer`, `FATES` |
| `new_agent_arch/src/rig/effects.py` (new) | `record_effect`, `forget_effects`, `earned` |
| `new_agent_arch/src/rig/runs.py` | `VERDICTS` gains `awaiting`, `done_by_operator` |
| `new_agent_arch/src/rig/runner.py` | `Approvals`, `from_step`, the `awaiting` pause, effects wiring |
| `new_agent_arch/src/rig/api.py` | `GET /v1/shapes`, `POST /v1/offers`, `POST /v1/runs/{id}/approve`, `from_step` on `POST /v1/runs` |
| `backend/src/sro/infrastructure/steel/generate_extension_recorder.py` | emits `shape.generated.js` |
| `new-chrome-extension/fixtures/shape-identity.json` (new) | the shared identity fixture |
| `new-chrome-extension/src/background/shape.generated.js` (generated) | `targetIdentity`, `tripleOf` |
| `new-chrome-extension/src/background/recognise.js` (new) | pure: `tailWith`, `match`, `diverged`, `valuesFrom` |
| `new-chrome-extension/src/background/api.js` | `shapes`, `reportOffer`, `rigStart`, `rigApprove` |
| `new-chrome-extension/src/background/state.js` | `tails`, `setTails` |
| `new-chrome-extension/src/background/service-worker.js` | `considerOffer`, offer endings, `start-rig-run`, `approve-rig-run`, the run poll |
| `new-chrome-extension/src/panel/ledger.js` | the upgraded offer card |
| `new-chrome-extension/src/panel/run-card.js` | live rig steps, the `awaiting` row |
| `docs/new-agent-doc-arc/findings.md` | *An offer lands*, the live measurement written for the operator |

---

### Task 1: The rig serves shapes and records offers

**Files:**
- Create: `new_agent_arch/src/rig/shapes.py`
- Create: `new_agent_arch/src/rig/offers.py`
- Modify: `new_agent_arch/src/rig/store.py` (SCHEMA: `offers` table)
- Modify: `new_agent_arch/src/rig/api.py` (`GET /v1/shapes`, `POST /v1/offers`, in the route block before `GET /`)
- Test: `new_agent_arch/tests/test_shapes.py`, `new_agent_arch/tests/test_api.py` (append)

**Interfaces:**
- Consumes: `rig.shape.shape_key`, `rig.locators.allowlist`, `rig.runs.runs_for`, `rig.workflows.known_workflows`, `rig.api._row_to_gesture` (deferred import, as `runner.py` does).
- Produces:
  - `shapes.Shape` dataclass: `id, title, starts_on: str | None, hosts: list[str], shape: list[list[str]], parameters: list[dict[str, Any]]` (each `{"name": str, "at": int | None}`), `held_runs: int`.
  - `shapes.shapes_for(store, tenant) -> list[Shape]` — proven workflows only (empty `unproven`); when the tenant has any run at all, only workflows with ≥ 1 run `held`.
  - `offers.FATES = ("accepted", "dismissed", "did_it", "expired", "diverged")`; `offers.record_offer(store, *, tenant, workflow_id, k, fate, run_id, device_id, at) -> str` (the offer id).
  - Routes: `GET /v1/shapes` → `{"shapes": [asdict(shape), ...]}`; `POST /v1/offers` body `{workflow_id, k, fate, run_id?, device_id, at}` → `201 {"offer_id"}`; 400 on a fate not in `FATES` or a workflow the tenant does not hold.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_shapes.py
from pathlib import Path

from rig.api import save_batch
from rig.runs import Run, save_run
from rig.shapes import shapes_for
from rig.store import Store
from rig.wire import Batch
from rig.workflows import Step, Workflow, save_workflow
from tests.fixtures import BATCH


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    save_batch(store, Batch.model_validate(BATCH), "acme")
    return store


def _ids(store: Store) -> list[str]:
    return [r["id"] for r in store.query("SELECT id FROM gestures ORDER BY at")]


def _workflow(store: Store, wid: str = "wfl_1", unproven: list[str] | None = None) -> Workflow:
    ids = _ids(store)
    typed = next(
        r["id"]
        for r in store.query("SELECT id, gesture_json FROM gestures ORDER BY at")
        if '"kind": "type"' in r["gesture_json"] and '"value": "ACME-4471"' in r["gesture_json"]
    )
    wf = Workflow(
        id=wid,
        tenant="acme",
        title="create a client",
        narrative="n",
        systems=["http://127.0.0.1:63319"],
        steps=[
            Step(order=0, says="type the code", system=None, cites=[typed], parameters=["clientCode"]),
            Step(order=1, says="save", system=None, cites=[ids[-1]]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["ACME-4471"]}],
        unproven=unproven or [],
    )
    save_workflow(store, wf)
    return wf


def test_a_proven_workflow_is_served_as_its_shape_with_where_each_parameter_was_typed(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    _workflow(store)

    [shape] = shapes_for(store, "acme")

    assert shape.id == "wfl_1" and shape.title == "create a client"
    assert shape.starts_on and shape.starts_on.startswith("http://127.0.0.1:63319")
    assert "http://127.0.0.1:63319" in shape.hosts
    assert len(shape.shape) == 2 and shape.shape[0][2] == "type" and shape.shape[1][2] == "click"
    assert shape.parameters == [{"name": "clientCode", "at": 0}], (
        "the parameter was typed at shape index 0"
    )
    assert shape.held_runs == 0


def test_an_unproven_workflow_is_not_served(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _workflow(store, unproven=["the save was never confirmed"])
    assert shapes_for(store, "acme") == []


def test_once_any_run_exists_only_workflows_that_have_held_are_served(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _workflow(store, "wfl_1")
    _workflow(store, "wfl_2")
    save_run(
        store,
        Run(
            id="run_1", tenant="acme", workflow_id="wfl_1", device_id="dev_1", values={},
            started_by="form", live=True, allow_focus=True,
            started_at="2026-09-06T10:00:00+00:00", finished_at="2026-09-06T10:01:00+00:00",
            outcome="held",
        ),
    )

    served = shapes_for(store, "acme")

    assert [s.id for s in served] == ["wfl_1"]
    assert served[0].held_runs == 1


def test_a_parameter_no_cited_gesture_typed_has_no_index(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    wf.parameters.append({"name": "description", "seen_values": ["never typed here"]})
    save_workflow(store, wf)

    [shape] = shapes_for(store, "acme")

    assert {"name": "description", "at": None} in shape.parameters
```

```python
# tests/test_api.py (append; reuse this file's existing `_client`/token helpers by name)
def test_the_shapes_route_serves_what_shapes_for_computes(tmp_path: Path) -> None:
    client, headers, store = _client(tmp_path)
    _seed_workflow(store)  # this file's helper that saves the fixture workflow, or copy test_shapes._workflow
    got = client.get("/v1/shapes", headers=headers)
    assert got.status_code == 200
    [shape] = got.json()["shapes"]
    assert shape["id"] == "wfl_1" and shape["parameters"] == [{"name": "clientCode", "at": 0}]


def test_an_offer_and_its_fate_are_recorded(tmp_path: Path) -> None:
    client, headers, store = _client(tmp_path)
    _seed_workflow(store)
    body = {"workflow_id": "wfl_1", "k": 2, "fate": "diverged", "device_id": "dev_1",
            "at": "2026-09-06T10:00:00+00:00"}
    got = client.post("/v1/offers", json=body, headers=headers)
    assert got.status_code == 201 and got.json()["offer_id"].startswith("off_")
    rows = store.query("SELECT workflow_id, k, fate, run_id FROM offers")
    assert [tuple(r) for r in rows] == [("wfl_1", 2, "diverged", None)]


def test_an_offer_with_a_fate_nobody_named_is_refused(tmp_path: Path) -> None:
    client, headers, store = _client(tmp_path)
    _seed_workflow(store)
    body = {"workflow_id": "wfl_1", "k": 2, "fate": "maybe", "device_id": "dev_1", "at": "x"}
    assert client.post("/v1/offers", json=body, headers=headers).status_code == 400
    body["fate"], body["workflow_id"] = "accepted", "wfl_nope"
    assert client.post("/v1/offers", json=body, headers=headers).status_code == 400
```

If `test_api.py` has no `_client`/`_seed_workflow` pair, read how `test_the_stop_button_flips_the_flag_and_tells_the_browser` builds its app and store, and use that pattern by name; do not invent a second one.

- [ ] **Step 2: Run them to verify they fail**

Run: `cd new_agent_arch && uv run pytest tests/test_shapes.py tests/test_api.py -q -k "shape or offer"`
Expected: FAIL — `ModuleNotFoundError: No module named 'rig.shapes'`, then 404s.

- [ ] **Step 3: The store**

Append to `SCHEMA` in `store.py`, after `workflow_stale`:

```sql
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
```

- [ ] **Step 4: `shapes.py` and `offers.py`**

```python
# src/rig/shapes.py
"""What the extension matches a live tail against.

One entry per proven workflow: its shape -- (system, control identity, kind)
per cited gesture in step order, the same key `identity.py` resolves on -- and
where in that shape each declared parameter was typed. Computed from the cited
gestures rather than read from `workflow.shape_key`, so the parameter indices
are indices into the very list the extension will walk.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from rig.locators import allowlist
from rig.records import Gesture
from rig.runs import runs_for
from rig.shape import shape_key
from rig.store import Store
from rig.workflows import Workflow, known_workflows


@dataclass(frozen=True, slots=True)
class Shape:
    id: str
    title: str
    starts_on: str | None
    hosts: list[str]
    shape: list[list[str]]
    parameters: list[dict[str, Any]]
    held_runs: int = 0

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


def _cited(store: Store, workflow: Workflow) -> list[Gesture]:
    from rig.api import _row_to_gesture  # api imports this module for the route

    wanted = [c for step in sorted(workflow.steps, key=lambda s: s.order) for c in step.cites]
    if not wanted:
        return []
    marks = ",".join("?" * len(wanted))
    rows = store.query(
        f"SELECT * FROM gestures WHERE tenant = ? AND id IN ({marks})",
        (workflow.tenant, *wanted),
    )
    by_id = {row["id"]: _row_to_gesture(row) for row in rows}
    return [by_id[c] for c in wanted if c in by_id]


def _typed_at(gestures: list[Gesture], parameter: dict[str, Any]) -> int | None:
    seen = {str(v) for v in parameter.get("seen_values", [])}
    for index, gesture in enumerate(gestures):
        if gesture.gesture.value is not None and gesture.gesture.value in seen:
            return index
    return None


def shapes_for(store: Store, tenant: str) -> list[Shape]:
    """Every proven workflow, as the extension needs it.

    A tenant with runs on record is asked a harder question -- has this one
    ever held -- because an offer to do a job the runner has never finished is
    an offer to fail in front of somebody. A tenant with no runs yet has to be
    offered something, or nothing is ever run.
    """
    any_runs = bool(store.query("SELECT 1 FROM runs WHERE tenant = ? LIMIT 1", (tenant,)))
    served: list[Shape] = []
    for workflow in known_workflows(store, tenant):
        if workflow.unproven:
            continue
        held = sum(1 for r in runs_for(store, tenant, workflow.id) if r.outcome == "held")
        if any_runs and held == 0:
            continue
        gestures = _cited(store, workflow)
        if not gestures:
            continue
        first = gestures[0]
        by_id = {g.id: g for g in gestures}
        served.append(
            Shape(
                id=workflow.id,
                title=workflow.title,
                starts_on=first.page_url or first.url,
                hosts=sorted(allowlist(workflow, by_id)),
                shape=[list(triple) for triple in shape_key(gestures)],
                parameters=[
                    {"name": str(p["name"]), "at": _typed_at(gestures, p)}
                    for p in workflow.parameters
                    if isinstance(p, dict) and p.get("name")
                ],
                held_runs=held,
            )
        )
    return served
```

```python
# src/rig/offers.py
"""What was offered, and what became of it.

Written by the extension, which made the offer, over `POST /v1/offers`. Read
by nobody yet: this is the labelled record of whether recognition was right,
and the share of `diverged` is what decides whether `K_OFFER_AFTER` moves.
"""

from __future__ import annotations

import secrets

from rig.store import Store

FATES = ("accepted", "dismissed", "did_it", "expired", "diverged")
"""accepted: Yes was pressed and a run started. dismissed: No thanks. did_it:
the operator made the workflow's write themselves while it asked. expired: the
nudge's lifetime passed. diverged: the tail stopped matching the prefix."""


def record_offer(
    store: Store,
    *,
    tenant: str,
    workflow_id: str,
    k: int,
    fate: str,
    run_id: str | None,
    device_id: str,
    at: str,
) -> str:
    if fate not in FATES:
        raise ValueError(f"{fate!r} is not a fate an offer can have")
    offer_id = "off_" + secrets.token_hex(8)
    with store.connect() as connection:
        connection.execute(
            "INSERT INTO offers (id, tenant, workflow_id, device_id, k, fate, run_id, at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (offer_id, tenant, workflow_id, device_id, k, fate, run_id, at),
        )
    return offer_id
```

- [ ] **Step 5: The routes**

In `api.py`, before `GET /`:

```python
    @app.get("/v1/shapes", dependencies=[Depends(authorised)])
    async def shapes() -> dict[str, Any]:
        """What the extension matches a live tail against. Arithmetic on the
        way out and arithmetic on the way in: no model is on this path."""
        from rig.shapes import shapes_for

        return {"shapes": [s.as_json() for s in shapes_for(store, tenant)]}

    @app.post("/v1/offers", status_code=201, dependencies=[Depends(authorised)])
    async def offered(body: dict[str, Any]) -> dict[str, Any]:
        from rig.offers import FATES, record_offer
        from rig.workflows import known_workflows

        workflow_id = str(body.get("workflow_id") or "")
        if workflow_id not in {w.id for w in known_workflows(store, tenant)}:
            raise HTTPException(status_code=400, detail="no such workflow")
        fate = str(body.get("fate") or "")
        if fate not in FATES:
            raise HTTPException(status_code=400, detail=f"fate must be one of {', '.join(FATES)}")
        k = body.get("k")
        if not isinstance(k, int) or k < 0:
            raise HTTPException(status_code=400, detail="k must be a non-negative integer")
        run_id = body.get("run_id")
        offer_id = record_offer(
            store,
            tenant=tenant,
            workflow_id=workflow_id,
            k=k,
            fate=fate,
            run_id=str(run_id) if isinstance(run_id, str) and run_id else None,
            device_id=str(body.get("device_id") or ""),
            at=str(body.get("at") or _now()),
        )
        return {"offer_id": offer_id}
```

- [ ] **Step 6: Run the tests and the gates**

Run: `cd new_agent_arch && uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src`
Expected: all pass; the suite count rises by 7.

- [ ] **Step 7: Commit**

```bash
git add new_agent_arch/src/rig/shapes.py new_agent_arch/src/rig/offers.py new_agent_arch/src/rig/store.py new_agent_arch/src/rig/api.py new_agent_arch/tests/test_shapes.py new_agent_arch/tests/test_api.py
git commit -m "feat(rig): the shapes the extension matches against, and a record of every offer"
```

### Task 2: One `target_identity`, two languages

**Files:**
- Create: `new-chrome-extension/fixtures/shape-identity.json`
- Modify: `backend/src/sro/infrastructure/steel/generate_extension_recorder.py` (emit `shape.generated.js`)
- Generated: `new-chrome-extension/src/background/shape.generated.js` (by `make gen-recorder`)
- Test: `new_agent_arch/tests/test_shape.py` (append), `new-chrome-extension/src/background/shape.generated.test.mjs`, `backend/tests/unit/infrastructure/test_generated_scripts_are_current.py` (parametrise the new file)

**Interfaces:**
- Consumes: `rig.shape.target_identity(gesture: Gesture) -> str` as the reference semantics. `wire.Target` fields: `role, name, testId, text, secret, component{itemId, query}`; `wire.Gesture.kind`.
- Produces: `shape.generated.js` exporting `targetIdentity(target, kind) -> string` and `tripleOf({system, target, kind}) -> [system, identity, kind]` with exactly the Python rule: `component.itemId`, else `component.query`, else `${role}|${name}` when both, else `name|${name}`, else `test|${testId}`, else `text|${text}`, else `anon|${kind}`; a null target is `anon|${kind}`. `system` is passed in by the caller (the tab's origin), never derived here.

- [ ] **Step 1: The shared fixture**

```json
[
  {"name": "an ExtJS control with an itemId",
   "kind": "type", "target": {"component": {"itemId": "wm.workAreas.code", "query": "textfield[name=code]"}, "role": null, "name": "Code", "testId": null, "text": null},
   "identity": "wm.workAreas.code"},
  {"name": "an ExtJS control with only a query",
   "kind": "click", "target": {"component": {"itemId": null, "query": "button[text=Save]"}, "role": "button", "name": "Save", "testId": null, "text": "Save"},
   "identity": "button[text=Save]"},
  {"name": "a plain control with role and name",
   "kind": "click", "target": {"component": null, "role": "button", "name": "Save", "testId": null, "text": "Save"},
   "identity": "button|Save"},
  {"name": "a name without a role",
   "kind": "type", "target": {"component": null, "role": null, "name": "Client code", "testId": null, "text": null},
   "identity": "name|Client code"},
  {"name": "a test id when nothing else names it",
   "kind": "click", "target": {"component": null, "role": null, "name": null, "testId": "save-btn", "text": null},
   "identity": "test|save-btn"},
  {"name": "text as the last resort",
   "kind": "click", "target": {"component": null, "role": null, "name": null, "testId": null, "text": "Continue"},
   "identity": "text|Continue"},
  {"name": "a secret field still has an identity, never a value",
   "kind": "type", "target": {"component": null, "role": "textbox", "name": "Password", "testId": null, "text": null, "secret": true},
   "identity": "textbox|Password"},
  {"name": "a scroll has no target",
   "kind": "scroll", "target": null,
   "identity": "anon|scroll"},
  {"name": "a target with nothing to say",
   "kind": "click", "target": {"component": null, "role": null, "name": null, "testId": null, "text": null},
   "identity": "anon|click"}
]
```

- [ ] **Step 2: The failing tests, both sides**

```python
# tests/test_shape.py (append)
import json
from pathlib import Path

from rig.records import Gesture
from rig.shape import target_identity
from rig.wire import Gesture as WireGesture

FIXTURE = Path(__file__).resolve().parents[2] / "new-chrome-extension/fixtures/shape-identity.json"


def test_the_python_identity_agrees_with_the_shared_fixture() -> None:
    for case in json.loads(FIXTURE.read_text()):
        wire = WireGesture.model_validate(
            {"kind": case["kind"], "target": case["target"], "at": 0.0, "value": None}
        )
        gesture = Gesture(
            id="g", tenant="t", stream_id="s", batch_id="b", at=0.0, url=None, system=None,
            tab_id=None, frame_url=None, gesture=wire,
        )
        assert target_identity(gesture) == case["identity"], case["name"]
```

```js
// new-chrome-extension/src/background/shape.generated.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { targetIdentity, tripleOf } from "./shape.generated.js";

const cases = JSON.parse(readFileSync(new URL("../../fixtures/shape-identity.json", import.meta.url)));

test("the generated identity agrees with the shared fixture", () => {
  for (const c of cases) assert.equal(targetIdentity(c.target, c.kind), c.identity, c.name);
});

test("a triple carries the system the caller names", () => {
  assert.deepEqual(
    tripleOf({ system: "https://h", target: cases[0].target, kind: cases[0].kind }),
    ["https://h", cases[0].identity, cases[0].kind],
  );
});
```

Run: `cd new_agent_arch && uv run pytest tests/test_shape.py -q` — expected PASS already (the Python rule is the reference; if a case fails, the fixture is wrong, not the code). Run `node new-chrome-extension/src/background/shape.generated.test.mjs` — expected FAIL, module not found.

- [ ] **Step 3: The generator emits the twin**

In `generate_extension_recorder.py`, add beside the other outputs:

```python
_BACKGROUND = Path(__file__).resolve().parents[5] / "new-chrome-extension" / "src" / "background"
SHAPE_OUT = _BACKGROUND / "shape.generated.js"


def shape_source() -> str:
    """The rig's `target_identity`, as an ES module. The rule is written once
    here as text; `rig/shape.py` is the reference and both are held to
    `fixtures/shape-identity.json`. Never edit the output; edit this."""
    return '''// GENERATED by backend/src/sro/infrastructure/steel/generate_extension_recorder.py
// -- do not edit. The reference is new_agent_arch/src/rig/shape.py:target_identity;
// both are tested against fixtures/shape-identity.json.

/** What to call the control this gesture touched, stably across occurrences. */
export function targetIdentity(target, kind) {
  if (!target) return `anon|${kind}`;
  const component = target.component;
  if (component) {
    if (component.itemId) return component.itemId;
    if (component.query) return component.query;
  }
  if (target.role && target.name) return `${target.role}|${target.name}`;
  if (target.name) return `name|${target.name}`;
  if (target.testId) return `test|${target.testId}`;
  if (target.text) return `text|${target.text}`;
  return `anon|${kind}`;
}

/** One entry of a shape: which system, which control, touched how. */
export function tripleOf({ system, target, kind }) {
  return [system || "", targetIdentity(target, kind), kind];
}
'''
```

and add `(SHAPE_OUT, shape_source())` to the list in `main()`. Parametrise `test_generated_scripts_are_current.py` with the new pair. Run `make gen-recorder`; confirm `git status` shows exactly the new generated file.

- [ ] **Step 4: Run both tests and the backend drift test**

Run: `node new-chrome-extension/src/background/shape.generated.test.mjs && cd backend && uv run pytest tests/unit/infrastructure/test_generated_scripts_are_current.py -q`
Expected: PASS. Add the new `.mjs` to the Makefile's `test-extension` list if that target enumerates files.

- [ ] **Step 5: Commit**

```bash
git add new-chrome-extension/fixtures/shape-identity.json backend/src/sro/infrastructure/steel/generate_extension_recorder.py new-chrome-extension/src/background/shape.generated.js new-chrome-extension/src/background/shape.generated.test.mjs backend/tests/unit/infrastructure/test_generated_scripts_are_current.py new_agent_arch/tests/test_shape.py Makefile
git commit -m "feat: one control identity, in Python and in the browser, held to one fixture"
```

### Task 3: The matcher

**Files:**
- Create: `new-chrome-extension/src/background/recognise.js`
- Test: `new-chrome-extension/src/background/recognise.test.mjs`

**Interfaces:**
- Consumes: `tripleOf` from `shape.generated.js` (callers build the triple; this module only compares).
- Produces (pure, no `chrome`):
  - `K_TAIL = 12`, `K_OFFER_AFTER = 2`
  - `tailWith(tail, entry) -> tail'` where `entry = {triple, value, secret, at}`; drops `anon|scroll` triples; keeps the last `K_TAIL`.
  - `match(tail, shapes, { origin }) -> { workflowId, title, k, values, missing, parameters } | null` — shapes are the route's entries; only shapes whose `shape[0][0] === origin` are considered; `k` is the longest value `>= K_OFFER_AFTER` such that the tail ends with `shape.slice(0, k)`, triples compared as joined strings; ties by longer `k`, then `held_runs`.
  - `diverged(tail, offer, shapes) -> boolean` — the tail no longer ends with the offer's prefix.
  - `valuesFrom(tail, shape, k) -> { values, missing }` — for each parameter with `at !== null && at < k`, the tail entry at that shape position contributes its `value` unless `secret`; every other parameter name is in `missing`.

- [ ] **Step 1: The failing tests**

```js
// recognise.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { K_OFFER_AFTER, K_TAIL, diverged, match, tailWith, valuesFrom } from "./recognise.js";

const H = "https://wms.example";
const workArea = {
  id: "wfl_wa", title: "Create Work Area", held_runs: 2,
  shape: [[H, "wm.workAreas.code", "type"], [H, "wm.workAreas.desc", "type"], [H, "button|Save", "click"]],
  parameters: [{ name: "workArea", at: 0 }, { name: "description", at: 1 }],
};
const operation = {
  id: "wfl_op", title: "Create Work Operation", held_runs: 0,
  shape: [[H, "wm.workAreas.code", "type"], [H, "wm.ops.code", "type"], [H, "button|Save", "click"]],
  parameters: [{ name: "workArea", at: 0 }, { name: "operation", at: 1 }],
};
const shapes = [workArea, operation];
const typed = (identity, value, extra = {}) => ({ triple: [H, identity, "type"], value, secret: false, at: 1, ...extra });

test("one gesture offers nothing", () => {
  const tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  assert.equal(match(tail, shapes, { origin: H }), null);
  assert.equal(K_OFFER_AFTER, 2);
});

test("two gestures offer the job whose prefix they are, with the values typed so far", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "north dock"));
  const offer = match(tail, shapes, { origin: H });
  assert.equal(offer.workflowId, "wfl_wa");
  assert.equal(offer.k, 2);
  assert.deepEqual(offer.values, { workArea: "NEWTESTS", description: "north dock" });
  assert.deepEqual(offer.missing, []);
});

test("a shared first step resolves to whichever job the second step names", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS"));
  tail = tailWith(tail, typed("wm.ops.code", "PICK"));
  assert.equal(match(tail, shapes, { origin: H }).workflowId, "wfl_op");
});

test("a shape on another origin is never matched", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, shapes, { origin: "https://elsewhere" }), null);
});

test("scrolls are not part of a shape and do not break a prefix", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, { triple: [H, "anon|scroll", "scroll"], value: "300", secret: false, at: 2 });
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.equal(match(tail, shapes, { origin: H }).k, 2);
});

test("the tail is bounded", () => {
  let tail = [];
  for (let i = 0; i < 20; i++) tail = tailWith(tail, typed(`c${i}`, "v"));
  assert.equal(tail.length, K_TAIL);
});

test("a secret control contributes no value and the parameter is missing", () => {
  let tail = tailWith([], typed("wm.workAreas.code", null, { secret: true }));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  const { values, missing } = valuesFrom(tail, workArea, 2);
  assert.deepEqual(values, { description: "b" });
  assert.deepEqual(missing, ["workArea"]);
});

test("a parameter typed later than the prefix is missing, and one never typed is too", () => {
  const later = { ...workArea, parameters: [{ name: "workArea", at: 0 }, { name: "code", at: 2 }, { name: "never", at: null }] };
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  assert.deepEqual(valuesFrom(tail, later, 2).missing, ["code", "never"]);
});

test("going another way ends the offer", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "A"));
  tail = tailWith(tail, typed("wm.workAreas.desc", "b"));
  const offer = match(tail, shapes, { origin: H });
  assert.equal(diverged(tail, offer, shapes), false);
  tail = tailWith(tail, typed("somewhere.else", "x"));
  assert.equal(diverged(tail, offer, shapes), true);
  tail = tailWith(tail, { triple: [H, "button|Save", "click"], value: null, secret: false, at: 3 });
  assert.equal(diverged(tail, offer, shapes), true, "a prefix broken once does not mend");
});
```

Run: `node new-chrome-extension/src/background/recognise.test.mjs` — expected FAIL, module not found.

- [ ] **Step 2: The module**

```js
// recognise.js
// Which proven job the operator has just started, decided from the last few
// gestures on the tab. Arithmetic on the shape the rig serves -- no model, no
// waiting for the once-a-minute flush -- so an offer can land on the second
// gesture, not a minute after it.

export const K_TAIL = 12;
export const K_OFFER_AFTER = 2;

const key = (triple) => triple.join(" ");

/** The tail with one more gesture. Scrolls are noise in a prefix and are dropped. */
export function tailWith(tail, entry) {
  if (entry.triple[1] === "anon|scroll") return tail;
  return [...tail, entry].slice(-K_TAIL);
}

function endsWith(tail, prefix) {
  if (prefix.length > tail.length) return false;
  const from = tail.length - prefix.length;
  return prefix.every((triple, i) => key(triple) === key(tail[from + i].triple));
}

/** Values typed so far for the parameters the prefix has reached. */
export function valuesFrom(tail, shape, k) {
  const values = {};
  const missing = [];
  const from = tail.length - k;
  for (const p of shape.parameters || []) {
    const entry = p.at !== null && p.at < k ? tail[from + p.at] : null;
    if (entry && !entry.secret && entry.value != null) values[p.name] = entry.value;
    else missing.push(p.name);
  }
  return { values, missing };
}

/** The best job this tail is a prefix of, or null. */
export function match(tail, shapes, { origin }) {
  let best = null;
  for (const shape of shapes) {
    if (!shape.shape?.length || shape.shape[0][0] !== origin) continue;
    for (let k = Math.min(shape.shape.length, tail.length); k >= K_OFFER_AFTER; k--) {
      if (!endsWith(tail, shape.shape.slice(0, k))) continue;
      if (!best || k > best.k || (k === best.k && (shape.held_runs || 0) > best.heldRuns)) {
        best = { workflowId: shape.id, title: shape.title, k, heldRuns: shape.held_runs || 0, shape };
      }
      break;
    }
  }
  if (!best) return null;
  const { values, missing } = valuesFrom(tail, best.shape, best.k);
  return {
    workflowId: best.workflowId,
    title: best.title,
    k: best.k,
    values,
    missing,
    parameters: (best.shape.parameters || []).map((p) => p.name),
  };
}

/** Whether the tail has stopped being this offer's prefix. */
export function diverged(tail, offer, shapes) {
  const shape = shapes.find((s) => s.id === offer.workflowId);
  if (!shape) return true;
  return !endsWith(tail, shape.shape.slice(0, offer.k));
}
```

- [ ] **Step 3: Run, lint, commit**

Run: `node new-chrome-extension/src/background/recognise.test.mjs && make lint-extension` — expected PASS. Add the test to `test-extension`.

```bash
git add new-chrome-extension/src/background/recognise.js new-chrome-extension/src/background/recognise.test.mjs Makefile
git commit -m "feat(extension): the job a tail of gestures is the start of, decided without a model"
```

### Task 4: Wired: shapes cached, tails kept, offers made and ended

**Files:**
- Create: `new-chrome-extension/src/background/offering.js` (the pure decision)
- Modify: `new-chrome-extension/src/background/api.js` (`shapes`, `reportOffer`, `rigStart`, `rigApprove`)
- Modify: `new-chrome-extension/src/background/state.js` (`tails`, `setTails`)
- Modify: `new-chrome-extension/src/background/service-worker.js` (`considerOffer`, offer endings, arrival candidates from the rig, `start-rig-run`, `drop-nudge` reporting)
- Modify: `new-chrome-extension/src/panel/nudge.js` (`fire` carries `source`, `workflowId`, `k`, `values`, `missing`, `parameters`)
- Test: `new-chrome-extension/src/panel/nudge.test.mjs` (extend), `new-chrome-extension/src/background/offering.test.mjs` (new)

**Interfaces:**
- Consumes: Task 1's routes, Task 3's `recognise.js`, Task 2's `tripleOf`, the nudge module (`shouldFire`, `fire`, `sweep`, `onCall`, `LIFETIME_MS`), `state.nudges/setNudges/muted/deviceId`, `showNudge/hideNudge`, `performing()` from `commands.js`.
- Produces:
  - `api.shapes() -> shapes[]` (GET `${rigUrl}/v1/shapes`, rig bearer, `isMirrorable` guard, `[]` on any failure).
  - `api.reportOffer({workflow_id, k, fate, run_id, device_id, at})` (POST `/v1/offers`, swallows errors).
  - `api.rigStart(body) -> {run_id}` (POST `/v1/runs`, throws `ApiError` carrying the route's `detail`).
  - `api.rigApprove(runId) -> {approved}` (POST `/v1/runs/{id}/approve`).
  - A nudge record gains `source: "rig" | "backend"`, and for rig offers `workflowId, k, values, missing, parameters`; an arrival nudge from a rig shape has `k: 0`.
  - `offering.decideOffer({ tail, shapes, open, origin, now }) -> { replace: nudge | null, end: "diverged" | null }` — pure.
  - Worker messages: `start-rig-run {nudgeId, values}` → posts the run, `setActiveRun({runId, at, source: "rig"})`, marks the nudge `accepted`, reports; `drop-nudge {nudgeId}` reports `dismissed` for a rig nudge.

- [ ] **Step 1: Failing tests**

```js
// offering.test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { decideOffer } from "./offering.js";
import { tailWith } from "./recognise.js";

const H = "https://wms.example";
const shape = { id: "wfl_wa", title: "Create Work Area", held_runs: 1, starts_on: `${H}/wa`,
  shape: [[H, "a", "type"], [H, "b", "type"], [H, "save", "click"]], parameters: [{ name: "workArea", at: 0 }] };
const typed = (id, value) => ({ triple: [H, id, "type"], value, secret: false, at: 1 });

test("a matched prefix becomes a rig offer carrying k and the values", () => {
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const { replace, end } = decideOffer({ tail, shapes: [shape], open: null, origin: H, now: 1000 });
  assert.equal(end, null);
  assert.equal(replace.source, "rig");
  assert.equal(replace.workflowId, "wfl_wa");
  assert.equal(replace.k, 2);
  assert.deepEqual(replace.values, { workArea: "NEW" });
  assert.equal(replace.state, "open");
});

test("an open offer is replaced only by a longer prefix", () => {
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const first = decideOffer({ tail, shapes: [shape], open: null, origin: H, now: 1000 }).replace;
  assert.equal(decideOffer({ tail, shapes: [shape], open: first, origin: H, now: 2000 }).replace, null);
  const longer = tailWith(tail, { triple: [H, "save", "click"], value: null, secret: false, at: 3 });
  assert.equal(decideOffer({ tail: longer, shapes: [shape], open: first, origin: H, now: 3000 }).replace.k, 3);
});

test("a tail that goes elsewhere ends the open offer as diverged", () => {
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const first = decideOffer({ tail, shapes: [shape], open: null, origin: H, now: 1000 }).replace;
  const away = tailWith(tail, typed("elsewhere", "y"));
  assert.equal(decideOffer({ tail: away, shapes: [shape], open: first, origin: H, now: 2000 }).end, "diverged");
});

test("a concrete rig offer outranks an arrival nudge", () => {
  const tail = tailWith(tailWith([], typed("a", "NEW")), typed("b", "x"));
  const open = { id: "n_1", source: "backend", state: "open" };
  const { replace, end } = decideOffer({ tail, shapes: [shape], open, origin: H, now: 1000 });
  assert.equal(end, null);
  assert.equal(replace.source, "rig");
});
```

In `nudge.test.mjs`, add one case: `fire(candidate, now, {...})` on a candidate with `source: "rig", workflow_id, k, values, missing, parameters` carries all six onto the nudge; a candidate without `source` yields `source: "backend"`, `k: 0`.

Run: `node new-chrome-extension/src/background/offering.test.mjs` — FAIL, module not found.

- [ ] **Step 2: `offering.js`, `nudge.fire`, `api.js`, `state.js`**

```js
// offering.js -- the decision, pure; the worker does the I/O around it.
import { fire } from "../panel/nudge.js";
import { diverged, match } from "./recognise.js";

export function decideOffer({ tail, shapes, open, origin, now }) {
  const rigOpen = open && open.source === "rig" && open.state === "open" && open.k > 0 ? open : null;
  if (rigOpen && diverged(tail, rigOpen, shapes)) return { replace: null, end: "diverged" };
  const found = match(tail, shapes, { origin });
  if (!found) return { replace: null, end: null };
  if (rigOpen && found.k <= rigOpen.k) return { replace: null, end: null };
  const shape = shapes.find((s) => s.id === found.workflowId);
  const replace = fire(
    { id: found.workflowId, title: found.title, starts_on: shape?.starts_on || origin,
      source: "rig", workflow_id: found.workflowId, k: found.k,
      values: found.values, missing: found.missing, parameters: found.parameters },
    now,
  );
  return { replace, end: null };
}
```

`nudge.fire` gains, inside the returned object: `source: candidate.source || "backend", workflowId: candidate.workflow_id || null, k: candidate.k || 0, values: candidate.values || {}, missing: candidate.missing || [], parameters: candidate.parameters || []`.

`api.js`, beside `rigRun`. Extract the header construction `rigRun` uses into `rigHeaders()` (`Authorization: Bearer <rigToken>`, `Content-Type: application/json`) if it is inline:

```js
  shapes: async () => {
    const base = await state.rigUrl();
    if (!isMirrorable(base)) return [];
    try {
      const r = await fetch(`${base}/v1/shapes`, { headers: await rigHeaders() });
      if (!r.ok) return [];
      return (await r.json()).shapes || [];
    } catch {
      return [];
    }
  },
  reportOffer: async (body) => {
    const base = await state.rigUrl();
    if (!isMirrorable(base)) return;
    try {
      await fetch(`${base}/v1/offers`, { method: "POST", headers: await rigHeaders(), body: JSON.stringify(body) });
    } catch {
      // The record is a nicety; the offer already happened.
    }
  },
  rigStart: async (body) => {
    const base = await state.rigUrl();
    if (!isMirrorable(base)) throw new ApiError(0, { detail: "no rig is configured" });
    const r = await fetch(`${base}/v1/runs`, { method: "POST", headers: await rigHeaders(), body: JSON.stringify(body) });
    if (!r.ok) throw new ApiError(r.status, await r.json().catch(() => ({ detail: r.statusText })));
    return r.json();
  },
  rigApprove: async (runId) => {
    const base = await state.rigUrl();
    if (!isMirrorable(base)) throw new ApiError(0, { detail: "no rig is configured" });
    const r = await fetch(`${base}/v1/runs/${encodeURIComponent(runId)}/approve`, { method: "POST", headers: await rigHeaders(), body: "{}" });
    if (!r.ok) throw new ApiError(r.status, await r.json().catch(() => ({ detail: r.statusText })));
    return r.json();
  },
```

`state.js`: `KEYS.tails = "sro.tails"`, `tails: () => read(KEYS.tails, {})`, `setTails: (t) => write(KEYS.tails, t)`.

- [ ] **Step 3: The worker**

In the `case "gesture"` handler, after the two `operatorIsWorking()` calls:

```js
        void considerOffer(sender?.tab?.id ?? null, message.gesture);
```

and the functions, beside `considerNudge`:

```js
// -- offering to finish the job they have just started ------------------------

let shapesHeld = { at: 0, list: [] };
async function shapesFor() {
  if (Date.now() - shapesHeld.at < CANDIDATES_FRESH_MS) return shapesHeld.list;
  shapesHeld = { at: Date.now(), list: await api.shapes() };
  return shapesHeld.list;
}

function originOf(url) {
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

async function considerOffer(tabId, gesture) {
  try {
    if (tabId === null || !(await isWatched(tabId))) return;
    if (performing()) return;
    const origin = originOf(gesture.url);
    if (!origin) return;
    const tails = await state.tails();
    const tail = tailWith(tails[tabId] || [], {
      triple: tripleOf({ system: origin, target: gesture.target, kind: gesture.kind }),
      value: gesture.secret ? null : (gesture.value ?? null),
      secret: Boolean(gesture.secret || gesture.target?.secret),
      at: gesture.at,
    });
    await state.setTails({ ...tails, [tabId]: tail });
    const shapes = await shapesFor();
    if (!shapes.length) return;
    const held = await state.nudges();
    const open = held.find((n) => n.state === "open" && n.tabId === tabId) || null;
    const now = Date.now();
    const { replace, end } = decideOffer({ tail, shapes, open, origin, now });
    if (end && open) await endOffer(open, end, held);
    if (replace) {
      const muted = await state.muted();
      if (muted[replace.startsOn] && muted[replace.startsOn] > now) return;
      const made = { ...replace, tabId };
      const rest = (await state.nudges()).filter((n) => n.id !== open?.id);
      if (open && open.source === "rig" && open.state === "open") void report(open, "dismissed");
      await state.setNudges([made, ...rest].slice(0, MAX_NUDGES));
      await showNudge(tabId, `${made.title} — want me to finish it?`);
    }
  } catch {
    // A tab that closed, a rig that is down. Nothing offered is the quiet answer.
  }
}

async function endOffer(nudge, fate, held) {
  await state.setNudges(held.map((n) => (n.id === nudge.id ? { ...n, state: fate } : n)));
  void hideNudge(nudge.tabId);
  void report(nudge, fate);
}

async function report(nudge, fate, runId = null) {
  if (nudge.source !== "rig" || !nudge.workflowId) return;
  void api.reportOffer({
    workflow_id: nudge.workflowId, k: nudge.k || 0, fate, run_id: runId,
    device_id: await state.deviceId(), at: new Date().toISOString(),
  });
}
```

Hook the existing endings. In `sweepNudges` and in `considerNudge`'s sweep, a rig nudge whose state leaves `open` for anything but `by-hand` reports `expired`. In `didItThemselves`, a rig nudge that becomes `by-hand` reports `did_it`. Arrival: in `candidatesFor(host)`, merge the rig's shapes whose `starts_on` host equals `host`, each as `{ id: s.id, title: s.title, starts_on: s.starts_on, source: "rig", workflow_id: s.id, k: 0, values: {}, missing: s.parameters.map((p) => p.name), parameters: s.parameters.map((p) => p.name) }`.

Panel messages, in the worker's message switch:

```js
    case "start-rig-run": {
      const held = await state.nudges();
      const nudge = held.find((n) => n.id === message.nudgeId);
      if (!nudge || nudge.source !== "rig") return { ok: false, error: "no such offer" };
      const values = { ...(nudge.values || {}), ...(message.values || {}) };
      let started;
      try {
        started = await api.rigStart({
          workflow_id: nudge.workflowId, values, device_id: await state.deviceId(),
          live: true, allow_focus: true, started_by: "offer", from_step: nudge.k || 0,
        });
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
      await state.setActiveRun({ runId: started.run_id, at: Date.now(), source: "rig" });
      await state.setNudges(held.map((n) => (n.id === nudge.id ? { ...n, state: "accepted" } : n)));
      void hideNudge(nudge.tabId);
      void report(nudge, "accepted", started.run_id);
      return { ok: true, run_id: started.run_id };
    }
```

In the existing dismiss path for a nudge (find it by its use of `mute` from `nudge.js`): when the nudge is `source === "rig"`, `void report(nudge, "dismissed")`.

- [ ] **Step 4: Run everything, commit**

Run: `make test-extension && make lint-extension` — PASS.

```bash
git add new-chrome-extension/src/background/offering.js new-chrome-extension/src/background/offering.test.mjs new-chrome-extension/src/background/api.js new-chrome-extension/src/background/state.js new-chrome-extension/src/background/service-worker.js new-chrome-extension/src/panel/nudge.js new-chrome-extension/src/panel/nudge.test.mjs Makefile
git commit -m "feat(extension): offer to finish the job on its second gesture, and say how each offer ended"
```

### Task 5: The offer card

**Files:**
- Modify: `new-chrome-extension/src/panel/ledger.js` (`nudging` draws the rig form)
- Modify: `new-chrome-extension/src/panel/panel.js` (the nudge press for a rig nudge sends `start-rig-run` with the typed values)
- Test: `new-chrome-extension/src/panel/ledger.test.mjs` (extend)

**Interfaces:**
- Consumes: a nudge record with `source: "rig"`, `k`, `values`, `missing`, `parameters`, `title` (Task 4); worker message `start-rig-run {nudgeId, values}`.
- Produces: the card. Copy, verbatim: a prefix offer says `` `${title} — ${typed}, so far. Want me to finish it?` `` where `typed` is the values joined by `, `; an arrival offer (`k === 0`) says `` `${title} — want me to do it?` ``. One `<input>` per `missing` name, placeholder the name. Buttons **Yes, finish it** (or **Yes, do it** at `k === 0`) and **No thanks**. Yes is `disabled` until every input is non-blank after `trim()`. Every string reaches the DOM through `textContent`.

- [ ] **Step 1: Failing tests**

```js
// ledger.test.mjs (append; use this file's DOM harness and the way it renders one nudge today)
test("a rig offer asks for what is missing and cannot start until it has it", () => {
  const nudge = { id: "n_1", source: "rig", state: "open", title: "Create Work Area", k: 2,
    values: { workArea: "NEWTESTS" }, missing: ["description"], parameters: ["workArea", "description"], tabId: 1 };
  const item = renderNudge(nudge);
  assert.match(item.querySelector(".what").textContent, /NEWTESTS, so far\. Want me to finish it\?/);
  const field = item.querySelector("input[placeholder=description]");
  assert.ok(field);
  const yes = [...item.querySelectorAll("button")].find((b) => /Yes, finish it/.test(b.textContent));
  assert.equal(yes.disabled, true);
  field.value = "north dock";
  field.dispatchEvent(new Event("input"));
  assert.equal(yes.disabled, false);
});

test("a rig arrival nudge offers to do it from the start", () => {
  const nudge = { id: "n_2", source: "rig", state: "open", title: "Create Work Area", k: 0,
    values: {}, missing: ["workArea"], parameters: ["workArea"], tabId: 1 };
  const item = renderNudge(nudge);
  assert.match(item.querySelector(".what").textContent, /want me to do it\?/);
  assert.ok([...item.querySelectorAll("button")].find((b) => /Yes, do it/.test(b.textContent)));
});

test("a backend nudge is drawn exactly as before", () => {
  const item = renderNudge({ id: "n_3", state: "open", title: "Create workOperations", tabId: 1 });
  assert.match(item.querySelector(".what").textContent, /you have done this here before/);
  assert.equal(item.querySelector("input"), null);
});
```

`renderNudge` is whatever this test file already uses to draw one nudge through `ledger(...)`; if there is none, add a five-line helper that builds a `thread` with no messages and `local = { offers: [], nudges: [nudge] }` and returns the `li[data-kind=nudge]`.

- [ ] **Step 2: `nudging` for a rig offer**

In `ledger.js`, first line of `nudging`: `if (nudge.source === "rig" && nudge.state === "open") return offeringToFinish(nudge, onPress);` and add:

```js
function offeringToFinish(nudge, onPress) {
  const item = document.createElement("li");
  item.className = "message";
  item.dataset.speaker = "system";
  item.dataset.kind = "nudge";
  item.dataset.state = "open";
  item.dataset.id = nudge.id;

  const typed = Object.values(nudge.values || {}).join(", ");
  const what = document.createElement("p");
  what.className = "what";
  what.textContent =
    nudge.k > 0
      ? `${nudge.title} — ${typed}, so far. Want me to finish it?`
      : `${nudge.title} — want me to do it?`;
  item.append(what);

  const fields = new Map();
  for (const name of nudge.missing || []) {
    const field = document.createElement("input");
    field.type = "text";
    field.placeholder = name;
    fields.set(name, field);
    item.append(field);
  }

  const yes = document.createElement("button");
  yes.type = "button";
  yes.textContent = nudge.k > 0 ? "Yes, finish it" : "Yes, do it";
  const no = document.createElement("button");
  no.type = "button";
  no.className = "quiet";
  no.textContent = "No thanks";
  const ready = () => [...fields.values()].every((f) => f.value.trim());
  yes.disabled = !ready();
  for (const field of fields.values()) field.addEventListener("input", () => (yes.disabled = !ready()));
  yes.addEventListener("click", () => {
    const values = Object.fromEntries([...fields].map(([name, f]) => [name, f.value.trim()]));
    onPress?.("start-rig-run", nudge, item, yes, { values });
  });
  no.addEventListener("click", () => onPress?.("drop-nudge", nudge, item, no));
  item.append(yes, no);
  return item;
}
```

In `panel.js`, where nudge presses are answered, add the two answers: `"start-rig-run"` → `button.disabled = true; const got = await ask({ kind: "start-rig-run", nudgeId: nudge.id, values: extra?.values || {} }); said(got.ok ? "started — watching it below" : got.error || "nothing started"); await refresh();` and `"drop-nudge"` → the existing dismiss.

- [ ] **Step 3: Run, lint, commit**

Run: `make test-extension && make lint-extension` — PASS.

```bash
git add new-chrome-extension/src/panel/ledger.js new-chrome-extension/src/panel/ledger.test.mjs new-chrome-extension/src/panel/panel.js
git commit -m "feat(panel): the offer to finish the job, with the blanks asked on the card"
```

### Task 6: A run that starts at step k

**Files:**
- Modify: `new_agent_arch/src/rig/runs.py` (`VERDICTS` gains `awaiting`, `done_by_operator`)
- Modify: `new_agent_arch/src/rig/runner.py` (`run_workflow(..., from_step: int = 0)`)
- Modify: `new_agent_arch/src/rig/api.py` (`from_step` on `POST /v1/runs`)
- Test: `new_agent_arch/tests/test_runner.py` (append), `new_agent_arch/tests/test_api.py` (append)

**Interfaces:**
- Consumes: the runner loop as it stands (`for step in sorted(workflow.steps, ...)`, `budget = len(workflow.steps) + K_STEP_SLACK`).
- Produces: `run_workflow(..., from_step=0)`. Steps with `order < from_step` are recorded `verdict="done_by_operator"`, `verdict_by="none"`, `reason="performed by the operator before the offer; cites " + ", ".join(step.cites)`, no command, no model call, no look. The budget is `len(steps) - skipped + K_STEP_SLACK`. `POST /v1/runs` accepts `from_step` (int, default 0); a value `< 0`, non-int, or `>= len(steps)` is a 400. `VERDICTS = ("held", "failed", "unclear", "withheld", "refused", "skipped", "awaiting", "done_by_operator")`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_runner.py (append)
async def test_a_run_started_mid_job_records_the_operators_steps_and_performs_the_rest(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(2), "ui.perform": [Reply(ok=True, result={"performed": True, "matched_by": "component"})]})
    asker = FakeAsker(_plan("click"), Answer(data={"held": True, "why": "saved"}))

    run = await run_workflow(
        store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
        asker=asker, plan_model="flash", rescue_model="pro", live=True, allow_focus=True,
        started_by="offer", from_step=1,
    )

    assert [s.verdict for s in run.steps] == ["done_by_operator", "held"]
    assert run.steps[0].verdict_by == "none" and wf.steps[0].cites[0] in run.steps[0].reason
    assert run.steps[0].sent is None and run.steps[0].in_tokens == 0, "nothing asked, nothing sent"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1
    assert run.outcome == "held"
```

If `FakeAsker` answers one `Answer` for every call, use the per-schema asker pattern `scripts/dry_run.py` builds (plan answer for `PLAN_SCHEMA`, verdict answer otherwise) — copy that small class into the test file rather than importing from `scripts/`.

```python
# tests/test_api.py (append)
def test_a_run_can_start_where_the_operator_left_off(tmp_path: Path) -> None:
    client, headers, store = _client(tmp_path)   # the file's helper; FakeChannel online as dev_test
    _seed_workflow(store)
    body = {"workflow_id": "wfl_1", "values": {"clientCode": "A"}, "device_id": "dev_test",
            "live": False, "from_step": 1}
    got = client.post("/v1/runs", json=body, headers=headers)
    assert got.status_code == 202
    run = load_run(store, "acme", got.json()["run_id"])
    assert run is not None and run.steps[0].verdict == "done_by_operator"


def test_a_from_step_past_the_job_is_refused(tmp_path: Path) -> None:
    client, headers, store = _client(tmp_path)
    _seed_workflow(store)
    body = {"workflow_id": "wfl_1", "values": {"clientCode": "A"}, "device_id": "dev_test", "from_step": 2}
    assert client.post("/v1/runs", json=body, headers=headers).status_code == 400
    body["from_step"] = -1
    assert client.post("/v1/runs", json=body, headers=headers).status_code == 400
```

Run: `cd new_agent_arch && uv run pytest tests/test_runner.py tests/test_api.py -q -k "mid_job or from_step or left_off"` — FAIL (`from_step` unexpected keyword; 202 with wrong verdict).

- [ ] **Step 2: The runner**

In `run_workflow`'s signature add `from_step: int = 0`. Where `budget` is computed:

```python
    ordered = sorted(workflow.steps, key=lambda s: s.order)
    skipped_by_operator = [s for s in ordered if s.order < from_step]
    budget = len(ordered) - len(skipped_by_operator) + K_STEP_SLACK
```

At the top of the `for step in ordered:` body, before the abort check:

```python
            if step.order < from_step:
                # The operator did this one before the offer was made. Recorded
                # so the run reads whole, cited so a reviewer can see what it
                # was, and never sent: the job is being finished, not redone.
                run.steps.append(
                    RunStep(
                        order=step.order,
                        says=step.says,
                        verdict="done_by_operator",
                        verdict_by="none",
                        reason="performed by the operator before the offer; cites "
                        + ", ".join(step.cites),
                    )
                )
                _total(run)
                save_run(store, run)
                continue
```

Keep the loop's later `record.verdict not in ("held", "withheld")` stop condition unchanged: it never sees these records because of the `continue`, and the `for/else` still yields `held` when every performed step held.

- [ ] **Step 3: The route**

In `start_run`, after the `absent` check:

```python
        from_step = body.get("from_step", 0)
        if not isinstance(from_step, int) or from_step < 0 or from_step >= len(workflow.steps):
            raise HTTPException(
                status_code=400,
                detail=f"from_step must be a step of this job (0..{len(workflow.steps) - 1})",
            )
```

and pass `from_step=from_step` into `run_workflow(...)`.

- [ ] **Step 4: Gates, commit**

Run: `cd new_agent_arch && uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src` — PASS.

```bash
git add new_agent_arch/src/rig/runs.py new_agent_arch/src/rig/runner.py new_agent_arch/src/rig/api.py new_agent_arch/tests/test_runner.py new_agent_arch/tests/test_api.py
git commit -m "feat(rig): a run can start where the operator left off"
```

### Task 7: Approval before a write

**Files:**
- Modify: `new_agent_arch/src/rig/runner.py` (`Approvals`, `K_APPROVAL_WAIT_S`, the `awaiting` pause; `earned` consulted via a callable so Task 8 can supply it)
- Modify: `new_agent_arch/src/rig/api.py` (`POST /v1/runs/{run_id}/approve`)
- Test: `new_agent_arch/tests/test_runner.py` (append), `new_agent_arch/tests/test_api.py` (append)

**Interfaces:**
- Consumes: `Aborts` as the pattern; `writes(step, by_id)`; `save_run`.
- Produces:
  - `runner.K_APPROVAL_WAIT_S = 300`.
  - `runner.Approvals` — `ClassVar` dict of `run_id -> asyncio.Event`; `Approvals.wait_for(run_id, timeout) -> bool` (creates the event, waits, returns whether it was set), `Approvals.approve(run_id) -> bool` (sets the event if one is waiting; False otherwise), `Approvals.awaiting(run_id) -> bool`, `Approvals.forget(run_id)`.
  - `run_workflow(..., earned: Callable[[str], bool] = lambda workflow_id: False)` — Task 8 passes the real one; default asks every time.
  - Route `POST /v1/runs/{run_id}/approve` → `{"approved": true}`; 409 `"nothing is awaiting approval on this run"` when `Approvals.awaiting(run_id)` is False.

- [ ] **Step 1: Failing tests**

```python
# tests/test_runner.py (append)
async def test_a_live_write_waits_for_approval_and_goes_out_when_it_comes(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [
        Reply(ok=True, result={"performed": True, "matched_by": "component"}),
        Reply(ok=True, result={"performed": True, "matched_by": "component"}),
    ]})
    asker = _per_schema_asker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    task = asyncio.create_task(run_workflow(
        store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
        asker=asker, plan_model="flash", rescue_model="pro", live=True, allow_focus=True,
        started_by="offer",
    ))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if Approvals.awaiting_any():
            break
    else:
        raise AssertionError("the write never paused")

    run_id = next(iter(Approvals.waiting()))
    saved = load_run(store, "acme", run_id)
    assert saved is not None and saved.steps[-1].verdict == "awaiting"
    assert saved.steps[-1].sent is not None, "the panel shows what would go out"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1, "the read step went; the write waits"

    assert Approvals.approve(run_id) is True
    run = await task
    assert run.outcome == "held"
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 2


async def test_a_write_nobody_approves_stops_the_run(tmp_path: Path, monkeypatch) -> None:
    import rig.runner as runner_module
    monkeypatch.setattr(runner_module, "K_APPROVAL_WAIT_S", 0.05)
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _per_schema_asker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))

    run = await run_workflow(
        store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
        asker=asker, plan_model="flash", rescue_model="pro", live=True, allow_focus=True,
        started_by="offer",
    )

    assert run.outcome == "stopped"
    assert "nobody approved" in run.steps[-1].reason
    assert [s["kind"] for s in channel.sent].count("ui.perform") == 1


async def test_a_dry_run_never_pauses(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [Reply(ok=True, result={"performed": True})]})
    asker = _per_schema_asker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))
    run = await asyncio.wait_for(run_workflow(
        store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
        asker=asker, plan_model="flash", rescue_model="pro", live=False, allow_focus=True,
        started_by="form",
    ), timeout=5)
    assert [s.verdict for s in run.steps] == ["held", "withheld"]


async def test_an_earned_workflow_writes_without_asking(tmp_path: Path) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "ui.perform": [
        Reply(ok=True, result={"performed": True}), Reply(ok=True, result={"performed": True}),
    ]})
    asker = _per_schema_asker(plan=_plan("click"), verdict=Answer(data={"held": True, "why": "ok"}))
    run = await asyncio.wait_for(run_workflow(
        store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
        asker=asker, plan_model="flash", rescue_model="pro", live=True, allow_focus=True,
        started_by="offer", earned=lambda _wid: True,
    ), timeout=5)
    assert run.outcome == "held" and not Approvals.awaiting_any()
```

`_per_schema_asker(plan, verdict)`: a test-local `Asker` whose `ask` returns `plan` when `schema is PLAN_SCHEMA` else `verdict`, recording each call in `.asked` like `FakeAsker`. Copy the shape `scripts/dry_run.py` uses.

```python
# tests/test_api.py (append)
def test_approve_with_nothing_waiting_is_refused(tmp_path: Path) -> None:
    client, headers, _ = _client(tmp_path)
    got = client.post("/v1/runs/run_x/approve", json={}, headers=headers)
    assert got.status_code == 409


def test_approve_releases_a_waiting_write(tmp_path: Path) -> None:
    from rig.runner import Approvals
    client, headers, _ = _client(tmp_path)
    async def waits() -> bool:
        return await Approvals.wait_for("run_w", timeout=2)
    import asyncio
    loop = asyncio.new_event_loop()
    task = loop.create_task(waits())
    loop.run_until_complete(asyncio.sleep(0))
    got = client.post("/v1/runs/run_w/approve", json={}, headers=headers)
    assert got.status_code == 200 and got.json() == {"approved": True}
    assert loop.run_until_complete(task) is True
    loop.close()
```

If the TestClient's portal makes the second test awkward, assert instead that `Approvals.approve("run_w")` returns True after `Approvals.wait_for` has been entered in a background thread's loop; the property under test is the route setting the event.

Run: `cd new_agent_arch && uv run pytest tests/test_runner.py tests/test_api.py -q -k "approv or pauses or earned"` — FAIL.

- [ ] **Step 2: `Approvals` and the pause**

In `runner.py`, beside `Aborts`:

```python
K_APPROVAL_WAIT_S = 300.0
"""How long a live write waits for a tap before the run stops and asks. Five
minutes is a person reading the panel, not a person who has gone home."""


class Approvals:
    """A write waiting for a person, keyed by run. In-process, like `Aborts`,
    and for the same reason: one uvicorn worker owns every run."""

    _waiting: ClassVar[dict[str, asyncio.Event]] = {}

    @classmethod
    async def wait_for(cls, run_id: str, timeout: float) -> bool:
        event = cls._waiting.setdefault(run_id, asyncio.Event())
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except TimeoutError:
            return False
        finally:
            cls._waiting.pop(run_id, None)

    @classmethod
    def approve(cls, run_id: str) -> bool:
        event = cls._waiting.get(run_id)
        if event is None:
            return False
        event.set()
        return True

    @classmethod
    def awaiting(cls, run_id: str) -> bool:
        return run_id in cls._waiting

    @classmethod
    def awaiting_any(cls) -> bool:
        return bool(cls._waiting)

    @classmethod
    def waiting(cls) -> set[str]:
        return set(cls._waiting)

    @classmethod
    def forget(cls, run_id: str) -> None:
        cls._waiting.pop(run_id, None)
```

`run_workflow` gains `earned: Callable[[str], bool] = lambda _workflow_id: False`. Immediately after the dry-run withhold block (`if not live and mutates: ... break`) and before `reply = await channel.send(...)`:

```python
                # A live write, on a job that has not yet earned the right to
                # write unasked: shown in the panel with what would go out, and
                # held until somebody taps. Dry runs never reach here.
                if mutates and not earned(workflow.id):
                    record.verdict, record.verdict_by = "awaiting", "none"
                    record.reason = "waiting for a person to approve the write"
                    record.sent = {"kind": planned.kind, "payload": planned.payload}
                    _total(run)
                    save_run(store, run)
                    if not await Approvals.wait_for(run.id, K_APPROVAL_WAIT_S):
                        record.verdict, record.verdict_by = "failed", "none"
                        record.reason = "nobody approved the write within five minutes"
                        verdict = Verdict("failed", "none", record.reason)
                        break
                    if Aborts.is_aborted(run.id):
                        verdict = Verdict("failed", "none", "stopped while waiting for approval")
                        break
```

If `record.sent` is set elsewhere after the send, keep that assignment; this earlier one is what the panel reads while waiting. In the `finally`, add `Approvals.forget(run.id)` beside `Aborts.forget`. The abort route already flips `Aborts`; make it also call `Approvals.approve(run_id)` so a Stop pressed during a wait releases the wait, and the check above turns it into the aborted path.

- [ ] **Step 3: The route**

```python
    @app.post("/v1/runs/{run_id}/approve", dependencies=[Depends(authorised)])
    async def approve_run(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """A person saw the write the panel showed and said go."""
        from rig.runner import Approvals

        if not Approvals.approve(run_id):
            raise HTTPException(status_code=409, detail="nothing is awaiting approval on this run")
        return {"approved": True}
```

- [ ] **Step 4: Gates, commit**

Run: `cd new_agent_arch && uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src` — PASS.

```bash
git add new_agent_arch/src/rig/runner.py new_agent_arch/src/rig/api.py new_agent_arch/tests/test_runner.py new_agent_arch/tests/test_api.py
git commit -m "feat(rig): a live write waits for a person until the job has earned not to"
```

### Task 8: Earned autonomy

**Files:**
- Create: `new_agent_arch/src/rig/effects.py`
- Modify: `new_agent_arch/src/rig/store.py` (`workflow_effects` table)
- Modify: `new_agent_arch/src/rig/runner.py` (record effects, reset on a failed write)
- Modify: `new_agent_arch/src/rig/api.py` (`earned=` wired into `start_run`)
- Test: `new_agent_arch/tests/test_effects.py`, `new_agent_arch/tests/test_runner.py` (append)

**Interfaces:**
- Consumes: Task 7's `earned` callable; the runner's held branch (`if verdict.state == "held":`) and its failed-write knowledge (`mutates`).
- Produces:
  - `effects.K_EARNED_RUNS = 3`
  - `effects.record_effect(store, *, workflow_id, run_id, order, verified_by, at)` — only `verified_by in ("status", "read")` is stored; anything else is ignored.
  - `effects.forget_effects(store, workflow_id) -> int`
  - `effects.earned(store, workflow_id) -> bool` — count of distinct `run_id` in `workflow_effects` for this workflow whose live run has every write step recorded here `>= K_EARNED_RUNS`. "Every write step" is computed against `run_steps`: for each run, the set of `ord` with `sent` naming a write (Task 7 stores `sent` before the wait; `_result` after) — simplest correct rule: a run counts when it is `outcome = 'held'` and `live = 1` and every one of its `run_steps` rows with a mutation (`writes()` is not available in SQL, so the runner records the write set itself: see Step 2) has a row here.

- [ ] **Step 1: Failing tests**

```python
# tests/test_effects.py
from pathlib import Path

from rig.effects import K_EARNED_RUNS, earned, forget_effects, record_effect
from rig.runs import Run, RunStep, save_run
from rig.store import Store


def _store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "rig.db")
    store.migrate()
    return store


def _held_run(store: Store, run_id: str, writes: list[int]) -> None:
    save_run(store, Run(
        id=run_id, tenant="acme", workflow_id="wfl_1", device_id="d", values={}, started_by="offer",
        live=True, allow_focus=True, started_at="2026-09-06T10:00:00+00:00",
        finished_at="2026-09-06T10:01:00+00:00", outcome="held",
        steps=[RunStep(order=o, says="s", verdict="held", verdict_by="status", stale=False, matched_by=None,
                       result={"ok": True, "status": 201, "matched_by": None, "wrote": True}) for o in writes],
    ))


def test_three_live_runs_whose_writes_all_verified_by_state_earn_autonomy(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        record_effect(store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="status", at="t")
        assert earned(store, "wfl_1") is (i == K_EARNED_RUNS - 1)


def test_a_screen_only_verification_is_not_an_effect(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        record_effect(store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="screen", at="t")
    assert earned(store, "wfl_1") is False


def test_a_run_with_one_unverified_write_does_not_count(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1, 3])
        record_effect(store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="read", at="t")
    assert earned(store, "wfl_1") is False


def test_a_failed_write_starts_the_earning_again(tmp_path: Path) -> None:
    store = _store(tmp_path)
    for i in range(K_EARNED_RUNS):
        _held_run(store, f"run_{i}", writes=[1])
        record_effect(store, workflow_id="wfl_1", run_id=f"run_{i}", order=1, verified_by="status", at="t")
    assert earned(store, "wfl_1")
    assert forget_effects(store, "wfl_1") == K_EARNED_RUNS
    assert earned(store, "wfl_1") is False
```

```python
# tests/test_runner.py (append)
async def test_a_held_write_verified_by_state_is_recorded_as_an_effect_and_a_failed_one_forgets_them(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    wf = _workflow(store)
    channel = FakeChannel({**_looks(4), "http.send": [Reply(ok=True, result={"status": 201, "body": "{}", "headers": {}})]})
    asker = _per_schema_asker(
        plan=Answer(data={"kind": "http.send", "action": None, "value": None, "url": None, "why": "w"}),
        verdict=Answer(data={"held": True, "why": "ok"}),
    )
    run = await run_workflow(store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
                             asker=asker, plan_model="flash", rescue_model="pro", live=True, allow_focus=True,
                             started_by="offer", earned=lambda _w: True)
    rows = store.query("SELECT run_id, ord, verified_by FROM workflow_effects WHERE workflow_id = ?", (wf.id,))
    assert [tuple(r) for r in rows] == [(run.id, 1, "status")]
    assert run.steps[-1].result.get("wrote") is True

    channel = FakeChannel({**_looks(4), "http.send": [Reply(ok=True, result={"status": 500, "body": "", "headers": {}})]})
    await run_workflow(store, wf, values={"clientCode": "THIRD"}, channel=channel, device_id="dev_test",
                       asker=asker, plan_model="flash", rescue_model="pro", live=True, allow_focus=True,
                       started_by="offer", earned=lambda _w: True)
    assert store.query("SELECT 1 FROM workflow_effects WHERE workflow_id = ?", (wf.id,)) == []
```

Run: `cd new_agent_arch && uv run pytest tests/test_effects.py tests/test_runner.py -q -k effect` — FAIL.

- [ ] **Step 2: Store, module, runner**

Store: append to `SCHEMA`

```sql
CREATE TABLE IF NOT EXISTS workflow_effects (
    workflow_id TEXT NOT NULL,
    run_id      TEXT NOT NULL,
    ord         INTEGER NOT NULL,
    verified_by TEXT NOT NULL,
    at          TEXT NOT NULL,
    PRIMARY KEY (workflow_id, run_id, ord)
);
```

```python
# src/rig/effects.py
"""When a job has earned the right to write without asking.

D2 of the autonomous-workflows design: autonomy is earned by verified effect,
not by counting runs. A write counts only when the verifier decided `held` by
state -- a status the server answered, or a read that showed the record -- and
never by a picture. A failed write un-earns the job: the next runs ask again.
"""

from __future__ import annotations

from rig.store import Store

K_EARNED_RUNS = 3
STATE_BELTS = ("status", "read")


def record_effect(
    store: Store, *, workflow_id: str, run_id: str, order: int, verified_by: str, at: str
) -> None:
    if verified_by not in STATE_BELTS:
        return
    with store.connect() as connection:
        connection.execute(
            "INSERT OR REPLACE INTO workflow_effects (workflow_id, run_id, ord, verified_by, at)"
            " VALUES (?, ?, ?, ?, ?)",
            (workflow_id, run_id, order, verified_by, at),
        )


def forget_effects(store: Store, workflow_id: str) -> int:
    with store.connect() as connection:
        cursor = connection.execute(
            "DELETE FROM workflow_effects WHERE workflow_id = ?", (workflow_id,)
        )
        return int(cursor.rowcount)


def earned(store: Store, workflow_id: str) -> bool:
    """Three live runs that held, each with every write step verified by state.

    A write step is a run_steps row whose stored result says `wrote`; the
    runner marks it so at send time, because SQL cannot ask `writes()`.
    """
    runs = store.query(
        "SELECT id FROM runs WHERE workflow_id = ? AND live = 1 AND outcome = 'held'", (workflow_id,)
    )
    counted = 0
    for run in runs:
        wrote = {
            r["ord"]
            for r in store.query(
                "SELECT ord, result FROM run_steps WHERE run_id = ?", (run["id"],)
            )
            if r["result"] and '"wrote": true' in r["result"]
        }
        if not wrote:
            continue
        verified = {
            r["ord"]
            for r in store.query(
                "SELECT ord FROM workflow_effects WHERE workflow_id = ? AND run_id = ?",
                (workflow_id, run["id"]),
            )
        }
        if wrote <= verified:
            counted += 1
    return counted >= K_EARNED_RUNS
```

Confirm `run_steps.result` is stored as JSON text with `json.dumps` default separators (`": "` with a space) — read `save_run`; if it uses compact separators, match the substring accordingly, or store a `wrote INTEGER` column instead. The plan's preference: add `"wrote": True` to `_result(reply)`'s dict when `mutates` (pass `mutates` into `_result`), so it is one more key in the record and no schema change.

Runner: in the `held` branch, beside `mark_stale`:

```python
                    if mutates and live:
                        record_effect(
                            store, workflow_id=workflow.id, run_id=run.id, order=step.order,
                            verified_by=verdict.by, at=_now(),
                        )
```

and where a write's verdict ends `failed` on a live run (after the rung loop, when `record.verdict == "failed" and mutates and live`): `forget_effects(store, workflow.id)`. `_result(reply, wrote=False)` adds `"wrote": True` when asked; pass `wrote=mutates` at the call site.

API: in `start_run`, pass `earned=lambda wid: earned(store, wid)` (import from `rig.effects`) into `run_workflow`.

- [ ] **Step 3: Gates, commit**

Run: `cd new_agent_arch && uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src` — PASS.

```bash
git add new_agent_arch/src/rig/effects.py new_agent_arch/src/rig/store.py new_agent_arch/src/rig/runner.py new_agent_arch/src/rig/api.py new_agent_arch/tests/test_effects.py new_agent_arch/tests/test_runner.py
git commit -m "feat(rig): a job earns the right to write unasked by three runs whose writes verified by state"
```

### Task 9: The live run in the panel, with Approve

**Files:**
- Modify: `new-chrome-extension/src/background/service-worker.js` (poll the rig run while active; `approve-rig-run`)
- Modify: `new-chrome-extension/src/background/api.js` (`rigRun` also maps `awaiting`, `done_by_operator`, and each step's `sent`)
- Modify: `new-chrome-extension/src/panel/run-card.js` (`glyphFor` for the new verdicts; the `awaiting` row with Approve and Stop)
- Modify: `new-chrome-extension/src/panel/panel.js` (`performing()` draws `runCard` when `status.performing.run` is present)
- Test: `new-chrome-extension/src/panel/run-card.test.mjs` (extend), `new-chrome-extension/src/background/finishing.test.mjs` (extend for the mapping)

**Interfaces:**
- Consumes: `api.rigRun(runId)` (Task 11 of the runner plan), `api.rigApprove` (Task 4), `status.performing` with `source` (runner plan Task 11), `runCard({run, ...}, {onPress})`.
- Produces:
  - `api.rigRun` steps carry `sent` (the planned command, when present) and `outcome` may now be `awaiting` or `done_by_operator`.
  - `K_RUN_POLL_MS = 1000` in the worker; while `activeRun.source === "rig"` and the last answer's `status === "running"`, `status.performing.run` is the mapped run.
  - `glyphFor("awaiting") === "⏸"`, `glyphFor("done_by_operator") === "✓"`.
  - An `awaiting` step row shows the words of the planned command and two buttons **Approve** and **Stop**; `onPress("approve", run, card, button)` and `onPress("stop", ...)`.
  - Worker message `approve-rig-run {runId}` → `api.rigApprove`.

- [ ] **Step 1: Failing tests**

```js
// run-card.test.mjs (append; use this file's harness)
test("an awaiting step shows what would go out and asks for approval", () => {
  const run = { id: "run_1", source: "rig", status: "running", steps: [
    { index: 0, outcome: "held", says: "type the code" },
    { index: 1, outcome: "awaiting", says: "save", sent: { kind: "ui.perform", payload: { action: "click", locators: [{ strategy: "role_and_name", query: "button|Save" }] } } },
  ] };
  const pressed = [];
  const card = runCard({ run }, { onPress: (answer) => pressed.push(answer) });
  const row = card.querySelector('.step[data-index="1"]');
  assert.equal(row.querySelector(".glyph").textContent, "⏸");
  assert.match(row.textContent, /click button\|Save/);
  const approve = [...row.querySelectorAll("button")].find((b) => b.textContent === "Approve");
  const stop = [...row.querySelectorAll("button")].find((b) => b.textContent === "Stop");
  assert.ok(approve && stop);
  approve.click();
  assert.deepEqual(pressed, ["approve"]);
});

test("a step the operator did is drawn done, not in flight", () => {
  const run = { id: "run_1", source: "rig", status: "running", steps: [
    { index: 0, outcome: "done_by_operator", says: "type the code" },
  ] };
  const card = runCard({ run }, {});
  assert.equal(card.querySelector('.step[data-index="0"] .glyph').textContent, "✓");
  assert.equal(card.querySelector("button"), null);
});
```

In `finishing.test.mjs`, extend the `api.rigRun` mapping case: a rig step `{order: 1, verdict: "awaiting", says: "save", sent: {...}}` maps to `{index: 1, outcome: "awaiting", says: "save", reason: "", sent: {...}}`.

Run: `node new-chrome-extension/src/panel/run-card.test.mjs` — FAIL.

- [ ] **Step 2: `glyphFor`, the awaiting row, the mapping**

`glyphFor` string arm: `{ held: "✓", done_by_operator: "✓", withheld: "⏸", awaiting: "⏸", failed: "✗", refused: "✗", skipped: "○" }`.

In `stepRow`, after the glyph and intent are appended and before the `change` control:

```js
  if (typeof outcome === "string" && outcome === "awaiting" && live) {
    const words = document.createElement("span");
    words.className = "planned";
    words.textContent = wordsFor(step.sent);
    const approve = document.createElement("button");
    approve.type = "button";
    approve.textContent = "Approve";
    approve.addEventListener("click", () => onPress?.("approve", run, row, approve));
    const stop = document.createElement("button");
    stop.type = "button";
    stop.className = "quiet";
    stop.textContent = "Stop";
    stop.addEventListener("click", () => onPress?.("stop", run, row, stop));
    row.append(words, approve, stop);
  }
```

with `stepRow` taking `onPress` from `runCard` (thread it through the existing call), and

```js
/** A planned command in words. `textContent` only; the payload is the model's and the page's. */
function wordsFor(sent) {
  if (!sent) return "";
  const p = sent.payload || {};
  if (sent.kind === "http.send") return `${p.method || "call"} ${p.url || ""}`;
  if (sent.kind === "navigate") return `open ${p.url || ""}`;
  const where = (p.locators || [])[0]?.query || "";
  return `${p.action || "act"}${p.value ? ` "${p.value}"` : ""} ${where}`.trim();
}
```

`api.rigRun`'s step mapping adds `sent: step.sent || null`.

- [ ] **Step 3: The worker polls, and approves**

In the worker, beside `checkFinishing`:

```js
const K_RUN_POLL_MS = 1000;
let rigRunShown = null;
let rigPoll = null;

async function pollRigRun() {
  const active = await state.activeRun();
  if (!active || active.source !== "rig") {
    rigRunShown = null;
    return;
  }
  try {
    rigRunShown = await api.rigRun(active.runId);
  } catch {
    // Keep the last picture; the next tick asks again.
  }
  if (rigRunShown?.status === "running") {
    clearTimeout(rigPoll);
    rigPoll = setTimeout(() => void pollRigRun(), K_RUN_POLL_MS);
  }
}
```

Start it wherever `setActiveRun({... source: "rig"})` is called (Task 4's `start-rig-run`) and on worker start when an active rig run is stored. In the status object: `performing: live && { ...live, source, run: source === "rig" ? rigRunShown : undefined }`. Message:

```js
    case "approve-rig-run": {
      try {
        return await api.rigApprove(message.runId);
      } catch (error) {
        return { ok: false, error: error.problem?.detail || error.message };
      }
    }
```

`panel.js`'s `performing()` card: when `status.performing.run` is present, append `runCard({ run: status.performing.run }, { onPress: async (answer, run, row, button) => { button.disabled = true; if (answer === "approve") { const got = await ask({ kind: "approve-rig-run", runId: run.id }); if (got?.error) said(got.error); } else if (answer === "stop") { await ask({ kind: "abort-run", runId: run.id }); } await refresh(); } })` under the existing card body. The band, `busy`, and everything else in `performing()` stay as they are.

- [ ] **Step 4: Run, lint, commit**

Run: `make test-extension && make lint-extension` — PASS.

```bash
git add new-chrome-extension/src/background/service-worker.js new-chrome-extension/src/background/api.js new-chrome-extension/src/panel/run-card.js new-chrome-extension/src/panel/run-card.test.mjs new-chrome-extension/src/panel/panel.js new-chrome-extension/src/background/finishing.test.mjs
git commit -m "feat(panel): a rig run drawn as it runs, and a write approved where it is shown"
```

### Task 10: The offer lands — written for the operator

**Files:**
- Modify: `docs/new-agent-doc-arc/findings.md` (new section *An offer lands*, after *A run performs*)
- Modify: `new_agent_arch/scripts/dry_run.py` (print the served shapes: `GET /v1/shapes` over the same app, one line per workflow with its shape length and parameter indices)

**Interfaces:**
- Consumes: everything above.
- Produces: the section, and the script's new block. No number in the section that the script did not print.

- [ ] **Step 1: The script prints the shapes**

After the runs table in `dry_run.py`, call `client.get("/v1/shapes")` on the same app and print:

```
shapes served: N of 8 workflows
  <title>: <len(shape)> triples; parameters: <name>@<at>, ...   (or "none declared")
```

and, for each workflow, what a tail of its first two triples would match against every other served shape: `match()`'s logic is JavaScript, so print the Python equivalent in the script (`shape.shape[:2] == other.shape[:2]`) as `shares its first two steps with: <titles>` or `distinct at two`. This is the number that says whether `K_OFFER_AFTER = 2` can tell the corpus's jobs apart.

- [ ] **Step 2: The section**

Write *An offer lands* with: what the script printed (shapes served, first-two-step collisions); what is proven by the suites (matcher, identity twin, `from_step`, approval, earning, the card); what is not (an offer on a real gesture stream, the panel's poll against a live rig, the value of `K_OFFER_AFTER` on this corpus); and the operator's recipe, exact commands: `make serve`, point the extension at the rig (options page fields **Rig URL** / **Rig token**), watch the WMS tab, start the work area job by hand, expect the card on the second gesture, Yes, watch the panel, Approve the save, repeat three times, and on the fourth expect no Approve. Record for each: gestures before the offer; seconds from the last gesture to the card; whether the offer named the right job; how the run ended; whether the fourth run asked.

- [ ] **Step 3: Gates, commit**

Run: `cd new_agent_arch && uv run python scripts/dry_run.py && uv run ruff check scripts && sqlite3 rig.db "select count(*) from runs"` — the last prints `0`.

```bash
git add new_agent_arch/scripts/dry_run.py docs/new-agent-doc-arc/findings.md
git commit -m "docs: an offer lands -- what the suites prove, and the measurement left for a person"
```

---

## Self-review

**Spec coverage.** Shapes route and offer record: Task 1. One identity, two languages: Task 2. The matcher, `K_TAIL`, `K_OFFER_AFTER`, secret handling, divergence: Task 3. Cache per `CANDIDATES_FRESH_MS`, tails in `state`, one offer per tab, longer-`k` replacement, the five fates reported, arrival from rig shapes, the nudge guards: Task 4. The card, its copy, Yes disabled until filled: Task 5. `from_step`, `done_by_operator`, budget, 400: Task 6. `awaiting`, `K_APPROVAL_WAIT_S`, approve route, Stop releases, dry never pauses, earned never pauses: Task 7. `workflow_effects`, state belts only, reset on failure, `K_EARNED_RUNS`: Task 8. Poll at `K_RUN_POLL_MS`, live rows, Approve/Stop on the row, bearer stays in the worker: Task 9. Verification 1–5 are the tasks' tests; 6 and 7 are Task 10's recipe. Refusals: unwatched/performing/muted (Task 4 guards), unserved host (Task 1's `hosts` from `allowlist`; a `starts_on` outside `hosts` cannot occur since both derive from the same cited gestures — stated, not gated), blank parameter (Task 5 card + existing route), approve when not awaiting (Task 7), screen never an effect (Task 8), rig down is silent (Task 4's `api.shapes` returns `[]`).

**Placeholders.** None: every step carries its code or its exact command. Two places delegate a small choice to the implementer with the rule stated (Task 5's `renderNudge` helper; Task 8's `wrote` marker vs a column) — both name the preferred answer.

**Type consistency.** `Shape.parameters[].at: int | None` (T1) ↔ `p.at !== null && p.at < k` (T3). Nudge fields `source, workflowId, k, values, missing, parameters` (T4 `fire`) ↔ the card (T5) ↔ `start-rig-run` (T4). `from_step` (T6 route and runner) ↔ `nudge.k` (T4). `Approvals.approve/wait_for/awaiting/awaiting_any/waiting/forget` (T7) ↔ the route and the abort route (T7). `earned: Callable[[str], bool]` (T7) ↔ `effects.earned(store, wid)` wired in T8. `api.rigRun` step `sent` (T9) ↔ `record.sent = {"kind", "payload"}` (T7). `glyphFor("awaiting")` (T9) ↔ verdict string `"awaiting"` (T6 `VERDICTS`).
