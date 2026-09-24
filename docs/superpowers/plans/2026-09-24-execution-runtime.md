# Execution Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every mined job runs end to end on a Steel browser on our VM, as a durable Temporal run that walks the tool → API → UI → sight ladder per step, and the extension stops executing.

**Architecture:** A `RunWorkflow` per run (Temporal, worker process only) calls idempotent activities that load the job and the run's `progress` row, lease the account's Steel session through a Postgres-backed `SessionBroker`, and hand each step to a `StepExecutor` that tries the first lane not on the step's known-broken list. The UI lane and the extension share one page-code file (`globalThis.sroPage`); the recorder captures the evidence the UI lane needs (§4), and every lane success teaches the lane above it.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async + Alembic (Postgres), Temporal (`temporalio`), Playwright over CDP to self-hosted Steel, httpx, Gemini (`gemini-3.8-flash`, `gemini-3.1-pro-preview`) through the metered client, MCP Gmail connector, Chrome MV3 extension (plain JS, `node --test`).

**Spec:** docs/superpowers/specs/2026-09-24-execution-runtime-design.md

## Global Constraints

1. **Root cause only.** Fix a bad value or state once, where it is produced, for every caller. No hardcoded host, IdP path, page text, job name, tenant or incident-specific branch; sign-in and session state are decided by structure (spec §5.6). Code that learns from failures and improves itself is fine.
2. **Backend source carries no comments or docstrings.** Exceptions: docstrings under `backend/src/sro/interface/http/`, docstrings on pydantic models and classes in `frontend/openapi.json`, and tool directives (`# noqa`, `# type: ignore[...]`, `# pragma`, `# fmt:`). Every explanation — including the reasoning behind each named constant — goes to `docs/code-notes/<source path>.md` under `## \`<qualname>\`, [line N](…#LN): <Kind>` with the text quoted. The same rule holds for `backend/scripts/` and for `new-chrome-extension/src/page/page-code.js`. Update or remove notes for code you change or delete; `make check-code-notes` must pass.
3. **Architecture.** `interface → application → domain`; infrastructure only through `container.py`. `uv run lint-imports` keeps 4 contracts. A new port only for a new effect: this plan adds exactly three (`BrowserPool`, `PageDriver`, `AccountLocks`). `grep -rn "unit_of_work()" backend/src/sro/interface/` prints nothing.
4. **Tests first.** Failing test, see it fail, then code. Unit tests in `backend/tests/unit` (Steel, httpx, MCP and Gemini faked, spec §8.1); SQL gets an integration test in `backend/tests/integration`; CDP/Playwright gets a browser test in `backend/tests/browser` with pages served by the test.
5. **Commands.**
   - backend tests: `cd backend && uv run pytest <path> -q -o faulthandler_timeout=120`
   - integration: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest <path> -q -o faulthandler_timeout=120`
   - extension: `make test-extension` and `make lint-extension`
   - browser: `cd backend && uv run pytest tests/browser/<file> -q -o faulthandler_timeout=120`
6. **Gates before each commit** (from `backend/`): `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src tests` (exactly the 2 pre-existing errors in `tests/unit/application/test_converse.py` and `tests/unit/domain/chat/test_asking.py` allowed), `uv run lint-imports`, `uv run pytest tests/unit -q -o faulthandler_timeout=120`, plus the integration and browser tests you touched. A wire schema change runs `make types` from the repo root and commits `frontend/openapi.json` and `frontend/src/lib/api/generated.ts`; `uv run pytest tests/contract -q` passes.
7. **Schema changes are additive.** Alembic, next free number after `0072` taken **at merge** (numbers below are provisional: 0073–0077), `down_revision` = the head at that moment, `alembic heads` shows one head. New nullable/defaulted columns, new tables, new or replaced indexes. Never drop a table or column.
8. **Recorder changes** are made in `backend/src/sro/infrastructure/steel/recorder.js` and generated with `make gen-recorder`. Never hand-edit `new-chrome-extension/src/content/recorder.generated.js` (or any `*.generated.js`); `tests/unit/infrastructure/test_generated_scripts_are_current.py` must pass.
9. **One page-code source.** `new-chrome-extension/src/page/page-code.js` is the only locator and page-reading code. The extension and Steel load the same file; never a Python re-implementation, never a copy (spec §6.4).
10. **Credentials.** A password, a saved session state, a cookie or a CSRF value never reaches a log, a Temporal payload, evidence, or a `workflow_runs` row. They live in the vault only. Password answers go through `PUT /v1/secrets`, never through the `answer` signal.
11. **Mutation floors are ratchets.** `scripts/mutation_floor.py` floors never drop; a task that drops a score strengthens its tests.
12. **Implementers never drive live QA.** Steps marked **LIVE QA** are run by the user. Deploy only with `infra/docker-compose.deploy.yml` (the base file's ports collide with the box's Postgres). A code change is not live until the worker restarts; every task that touches activities says so in its report.
13. **Git.** One branch per task from the latest merged tip; merge to `main` only on the user's explicit "merge". Conventional commit messages ending `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. Never push. Never touch, move or delete an untracked file (`designof-panel/`, `docs/21-*.md` are the user's). Never delete files outside the task's scope.
14. **Exact values from the spec, as named constants:** step activity heartbeat timeout 30 s (`K_STEP_HEARTBEAT_S = 30`); step start-to-close 5 min (`K_STEP_LIMIT_S = 300`); vault value limit 64 KiB (`K_VAULT_VALUE_BYTES = 65536`); sight model `gemini-3.8-flash`, one escalation to `gemini-3.1-pro-preview`; verdicts `done | read | failed | unknown`; lease states `signing_in | ready | expired | broken`; rollout setting `executor: extension | steel`, first tenant `greyorange`; vault keys `{tenant}/{origin}/{username}/password` and `…/state`.

### Build discipline (ponytail) — binds every implementer and reviewer

Stop at the first rung that holds: (1) does it need to exist at all — speculative need, skip it; (2) already in this codebase — reuse the helper or pattern, look before writing; (3) stdlib; (4) native platform or database feature; (5) an installed dependency — never add one for a few lines; (6) one line; (7) only then the minimum code that works.

- Understand first: read the task and every file it touches, trace the real flow, grep every caller before editing a shared function. Root cause, fixed once where all callers route through.
- No unrequested abstractions (no one-implementation interface beyond the three ports above, no one-product factory, no config for a constant), no scaffolding for later. Deletion over addition; boring over clever; fewest files; shortest working diff.
- A deliberate corner with a known ceiling gets a note naming the ceiling and the upgrade path, in the code-notes file (Global Constraint 2).
- Non-trivial logic leaves one runnable check (a focused test). No per-function suites unless asked.
- Never simplify away: validation at trust boundaries, data-loss error handling, security, accessibility.
- Reviewers flag over-building as a finding: code that did not need to exist, re-implemented helpers, unrequested abstraction.
- **No workarounds.** The shortest diff never means one. Forbidden, and ranked Important by reviewers: allowlists or exception sets for "pre-existing" offenders (fix them); host lists or IdP path lists; timing windows or sleeps where a structural signal exists; shaping data, notes or tests to fit around a tool bug (fix the tool); rewriting a test to keep a dead path green (delete the path).

---

## File Structure

Clean architecture, enforced by import-linter: `domain` (pure), `application` (use cases and ports), `infrastructure` (adapters, reached from `container.py` only), `interface` (HTTP).

### Created

| File | Responsibility | Task |
|---|---|---|
| `backend/scripts/steel_sessions.py` | Throwaway probe: sessions and contexts per self-hosted Steel container | C0 |
| `backend/src/sro/domain/execution/account.py` | `Account` (tenant, origin, username), vault keys, advisory-lock key; `Lease`, `LeaseState`, `K_LEASE_TTL`, `K_VAULT_VALUE_BYTES` | S1 |
| `backend/src/sro/domain/execution/lanes.py` | `Lane`, `Verdict`, `StepResult`, `Broken`, the ladder `lanes_for`, failure fingerprints, write-confirmation rules, `after_matches`, `K_SIGHT_ACTIONS` | X3 |
| `backend/src/sro/domain/execution/progress.py` | `Progress` / `StepMark` (the `workflow_runs.progress` JSONB), write idempotency, `run_budget`, step-activity limits | D1 |
| `backend/src/sro/application/ports/locks.py` | `AccountLocks` port: the per-account session lock | S3 |
| `backend/src/sro/application/ports/pool.py` | `BrowserPool` port: open/close a Steel session in a container with free capacity | S4 |
| `backend/src/sro/application/ports/page.py` | `PageDriver` port and its value types: tabs, state, page code calls, calls seen, headers, screenshots, points | S5 (grown by S6, S10, X4, X7) |
| `backend/src/sro/application/runtime/__init__.py` | package marker (empty) | S7 |
| `backend/src/sro/application/runtime/broker.py` | `SessionBroker`: acquire, reattach, release, reauth, headers; `Held`; `NeedsAPerson` | S7, S8, S10 |
| `backend/src/sro/application/runtime/step.py` | `LaneContext` and the `StepLane` protocol every lane implements | X3 |
| `backend/src/sro/application/runtime/ui_lane.py` | UI lane: page-code act in the recorded frame, condition waits, verification | X4 |
| `backend/src/sro/application/runtime/api_lane.py` | API lane: verified replay through httpx with broker headers; read-back | X5 |
| `backend/src/sro/application/runtime/tool_lane.py` | Tool lane: mailbox steps through the MCP Gmail connector | X6 |
| `backend/src/sro/application/runtime/sight_lane.py` | Sight lane: Gemini computer use on a Steel screenshot, CDP points | X7 |
| `backend/src/sro/application/runtime/executor.py` | `StepExecutor`: walks the ladder for one step | X8 |
| `backend/src/sro/application/runtime/teach.py` | `Teach`: known-broken list, mending, sight → locator, UI → API promotion | X9 |
| `backend/src/sro/application/runtime/run_steps.py` | `RunSteps`: the activity bodies (prepare, acquire, step, finish, release, stopped, answered) | D2, D4, D5, D6 |
| `backend/src/sro/application/runtime/answer_run.py` | `AnswerRun` use case: validate an answer and signal the workflow | D5 |
| `backend/src/sro/infrastructure/db/locks.py` | `PostgresAccountLocks`: `pg_advisory_lock` on a dedicated connection | S3 |
| `backend/src/sro/infrastructure/steel/pool.py` | `SteelPool`: containers from `steel_urls`, capacity from QA-0 | S4 |
| `backend/src/sro/infrastructure/steel/driver.py` | `SteelDriver`: one CDP connection per session, tabs by target id, page code injected, network log | S5 (grown by S6, S10, X4, X7) |
| `new-chrome-extension/src/page/page-code.js` | The one page-code file, a classic script exposing `globalThis.sroPage` | X1 (grown by S6, X2) |
| `new-chrome-extension/src/page/page-code.test.mjs` | Node self-checks of `page-code.js` (moved from `in-page.test.mjs`) | X1, X2 |
| `backend/tests/unit/runtime_support.py` | Shared builders and doubles for the runtime's unit tests (steps with evidence, scripted drivers and lanes, a run world) | X4 (grown by S7–D6) |
| `backend/tests/browser/steel_rig.py` | Local identity-provider chain (form, redirect, app) and served pages shared by runtime browser/integration tests | S5 |
| `backend/tests/browser/test_the_steel_driver.py` | SteelDriver against served pages over local Chromium CDP | S5, S6, S10, X4, X7 |
| `backend/tests/browser/test_page_code_parity.py` | §8.2 parity suite: extension injection vs `add_init_script` choose the same element | X2 |
| `backend/tests/integration/test_leases.py` | Lease SQL: unique live lease, beat, expiry | S2 |
| `backend/tests/integration/test_account_locks.py` | Advisory lock excludes a second holder across connections | S3 |
| `backend/tests/integration/test_runs_on_local_steel.py` | §8.3 scenarios against local Steel + Temporal test server | S7, S8, D2, D4, D6 |
| `backend/scripts/shadow.py` | Rollout step 1: dry Steel runs beside extension runs, verdicts compared | R1 |
| `backend/migrations/versions/2026xxxx_0073_a_gesture_keeps_its_tree.py` | `gestures.tree` JSONB | E6 |
| `backend/migrations/versions/2026xxxx_0074_sign_in_pages_are_watched.py` | Heal stored policies whose `exclude_hosts` is exactly the old default | E7 |
| `backend/migrations/versions/2026xxxx_0075_a_session_is_leased.py` | Lease columns and the one-live-lease index on `browser_sessions` | S2 |
| `backend/migrations/versions/2026xxxx_0076_a_lane_known_broken.py` | `known_broken` table | X8 |
| `backend/migrations/versions/2026xxxx_0077_a_run_keeps_its_progress.py` | `workflow_runs.progress`, `workflow_runs.executor`, the per-device index narrowed to extension runs | D1 |

### Modified

| File | Change | Task |
|---|---|---|
| `new-chrome-extension/src/background/service-worker.js` | `popupEvent`/`pageEvent` carry `opener_tab_id` | A0 |
| `backend/src/sro/application/capture/rig_wire.py` | Wire fields: `opener_tab_id`, `landmarks`, `frame_path`, `detail`, `trusted`, `prior`, snapshot `tab_id` | A0, E2–E6 |
| `backend/src/sro/domain/observation/gesture.py` | `PageMark.opener_tab_id`; `Target.bounds/attributes/landmarks`; `Component.chain`; `Action.modifiers/detail/trusted/frame_path/after`; `Landmark`, `FrameHop`, `AfterState`; `Gesture.tree` | A0, E1–E6 |
| `backend/src/sro/application/observation/correlate.py` | `as_action`/`as_mark` keep every captured field; after-state join; tree attached to its gesture | A0, E1–E6 |
| `backend/src/sro/infrastructure/steel/recorder.js` (+ generated copy) | `landmarksOf`, `framePathOf`, click `detail`/`isTrusted`, `stateOf` + `prior` | E2–E5 |
| `backend/src/sro/domain/skill/signing_in.py` | Enter-submit by `detail == 0`; `PageSignals` and the structural sign-in predicates | E4, S6 |
| `backend/src/sro/application/observation/redact.py` | A snapshot's tree keeps no credential-field value | E6 |
| `backend/src/sro/infrastructure/db/evidence.py`, `models.py` | `gestures.tree` round trip; lease columns; `known_broken`; run `progress`/`executor` | E6, S2, X8, D1 |
| `backend/src/sro/domain/observation/policy.py` | `DEFAULT_EXCLUSIONS = ()` | E7 |
| `backend/src/sro/application/ports/repositories.py` | `BrowserSessionRepository` lease methods; `WorkflowRepository` known-broken methods | S2, X8 |
| `backend/src/sro/infrastructure/db/repositories.py`, `workflows.py`, `workflow_runs.py` | SQL for leases, known-broken, progress/executor, `fail_orphans` narrowed | S2, X8, D1 |
| `backend/tests/unit/fakes.py` | Fakes for leases, locks, pool, page driver, known-broken, durable runs | S2–S5, X8, D2 |
| `backend/src/sro/interface/http/v1/routers/secrets.py`, `schemas.py` | Password stored under the account key when a username is given | S1 |
| `backend/src/sro/config.py` | `steel_urls`, `steel_sessions_per_container`, `page_code_path`, `steel_tenants` | S4, X1, D3 |
| `infra/docker-compose.yml`, `infra/docker-compose.deploy.yml` | `steel-1…steel-N` services | S4 |
| `backend/src/sro/infrastructure/steel/client.py` | One-browser refusal becomes per-container capacity | S4 |
| `backend/src/sro/application/connection/release_strays.py` | Releases only expired leases; `GRACE` and `Pursuits.sessions()` gone | S9 |
| `backend/src/sro/application/connection/sign_in.py` | `tagged_logins` extracted from `_recorded` for reuse by the broker | S7 |
| `new-chrome-extension/src/background/commands.js` | Injects `page-code.js` by `files`, calls `sroPage.<name>` | X1 |
| `new-chrome-extension/src/background/in-page.js`, `in-page.test.mjs` | Deleted after the move | X1 |
| `backend/Dockerfile`, `Makefile` (`images`), `.github/workflows/ci.yml` | Named build context `page`; CI image hash check | X1 |
| `backend/src/sro/interface/http/v1/routers/health.py`, `backend/scripts/smoke.py` | `/health` reports the page code's sha256; smoke compares it | X1 |
| `backend/src/sro/domain/execution/workflow_run.py` | `WorkflowRun.progress`, `WorkflowRun.executor` | D1 |
| `backend/src/sro/application/ports/durable.py`, `infrastructure/temporal/{workflows,activities,durable,worker,queues}.py` | `RunWorkflow` on the `runs` queue; `start_run`, `cancel_run`, `answer_run` | D2, D4, D5 |
| `backend/src/sro/application/execution/workflow_runs.py` | `StartWorkflowRun` starts Steel tenants' runs durably; `AbortWorkflowRun` cancels them | D3, D4 |
| `backend/src/sro/application/chat/from_the_mail.py` | A sure mail with all required values starts the run (Steel tenants) | D3 |
| `backend/src/sro/interface/http/v1/routers/workflow_runs.py` | `POST /v1/workflow-runs/{id}/answer` | D5 |
| `backend/src/sro/container.py` | Factories for everything above | S3–D5 |
| `backend/src/sro/interface/http/app.py` | Startup sweep leaves Steel runs alone | D1 |
| `new-chrome-extension/src/background/commands.js`, `service-worker.js`, `showing.js` | Executing kinds removed | R2 |
| `backend/src/sro/infrastructure/steel/ui_driver.py` and the old skill engine | Removed after measurement | R3 |

---

## Streams and order

Five streams, one implementer each, plus the probe that comes first. Within a stream, tasks run in the order listed; a task starts from the latest merged tip.

| Stream | Spec | Tasks |
|---|---|---|
| **—** probe | §5.1, §8 QA-0 | C0 |
| **E** evidence contract | §4, §5.6 (capture), parent §5.4 | A0, E1, E2, E3, E4, E5, E6, E7 |
| **S** session broker and pool | §5 | S1, S2, S3, S4, S5, S6, S7, S8, S9, S10 |
| **X** executors, lanes, page code | §3, §6 | X1, X2, X3, X4, X5, X6, X7, X8, X9 |
| **D** durable runs | §7 | D1, D2, D3, D4, D5, D6 |
| **R** rollout and removals | §9, §10 | R1, R2, R3 |

### Dependency graph

```
C0 (QA-0) ──────────────────────────────► S4
A0 ─┐ (independent)
E1 → E2 → E3 → E4 → E5 → E6        E7 (independent)
S1 → S2 ─┐
S3 ──────┤
S4 ──────┤
X1 → S5 → S6 ───────────┤
X3 → X4 (+S5, X2) ──────┴─► S7 → S8 ─┐
X1 → X2 ──────► X4                    ├─► S9
                       S7 → S10 → X5  │
X3 → X6                               │
X4 → X7                               │
X4, X5, X6, X7 → X8 → X9              │
D1 ─┐                                 │
S7, S8, X9 ──► D2 → D3 ──► (QA-1, QA-3)
               D2 → D4, D5, D6 ──► (QA-4, QA-5)
X5 + X9 on QA ──► QA-2
D3 → R1 (shadow) ;  QA-1…QA-5 = POC ──► R2 ; R3 measure-first after R2
```

Parallel start (no shared files): **C0, A0, E1, E7, S1, S3, X1, X3, D1**. C0 blocks only S4.

**Interfaces frozen in review** (their owners' reviews are the gate for the consumers):
- `Lease`, `Account` (S1) → S2, S7, D2.
- `PageDriver` + `SessionRef` (S5) → S6, S7, S10, X4, X7.
- `Held`, `NeedsAPerson`, `SessionBroker.acquire/reattach/reauth/headers/release` (S7, S10) → X4, X5, X7, D2.
- `Lane`, `Verdict`, `StepResult`, `Broken`, `LaneContext`, `StepLane` (X3) → X4–X9, D2.
- `Progress`, `StepMark` (D1) → D2, D4–D6.
- `page-code.js` `sroPage` API (X1, X2, S6) → S5, X4, X7, parity suite.

---

## C0: How many sessions does one self-hosted Steel container hold? (§5.1, §12 risk 1) — **LIVE QA: QA-0**

Throwaway probe. Its outcome decides the broker's shape (S4); no product code changes here.

**Files:**
- Create: `backend/scripts/steel_sessions.py`
- Create: `backend/tests/unit/test_steel_sessions_probe.py`
- Create: `docs/code-notes/backend/scripts/steel_sessions.py.md`
- Modify: `docs/code-notes/backend/src/sro/infrastructure/steel/client.py.md` (append the measured answer under `## \`SteelClient.open\`, [line 49](…#L49): Note`)

**Interfaces:**
- Consumes: Steel's HTTP API (`POST /v1/sessions`, `GET /v1/sessions/{id}`, `POST /v1/sessions/{id}/release`) and the container's CDP `/json/version`, as `SteelClient` uses them today (`infrastructure/steel/client.py:49-148`).
- Produces: `verdict(seen: Seen) -> Literal["sessions", "contexts", "one-per-container"]`, printed with the observations. S4 reads the answer: `one-per-container` → `steel_sessions_per_container = 1` (the spec's baseline); `sessions` → the measured number of sessions; `contexts` → S4's context variant.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_steel_sessions_probe.py
from scripts.steel_sessions import Seen, verdict


def test_two_live_sessions_on_their_own_endpoints_are_sessions() -> None:
    seen = Seen(True, False, True, True, True)
    assert verdict(seen) == "sessions"


def test_one_session_with_isolated_lasting_contexts_is_contexts() -> None:
    seen = Seen(False, True, True, True, False)
    assert verdict(seen) == "contexts"


def test_anything_less_is_one_account_per_container() -> None:
    assert verdict(Seen(False, True, True, False, False)) == "one-per-container"
    assert verdict(Seen(True, True, False, False, True)) == "one-per-container"
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/unit/test_steel_sessions_probe.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'scripts.steel_sessions'`.

- [ ] **Step 3: Write the probe**

```python
# backend/scripts/steel_sessions.py
from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from typing import Literal

import httpx
from playwright.async_api import async_playwright

PROBE = "https://probe.example"


@dataclass(frozen=True, slots=True)
class Seen:
    second_session_live: bool
    same_cdp_endpoint: bool
    contexts_isolated: bool
    context_survives_disconnect: bool
    other_survives_release: bool


def verdict(seen: Seen) -> Literal["sessions", "contexts", "one-per-container"]:
    if seen.second_session_live and not seen.same_cdp_endpoint and seen.other_survives_release:
        return "sessions"
    if seen.contexts_isolated and seen.context_survives_disconnect:
        return "contexts"
    return "one-per-container"


async def _session(client: httpx.AsyncClient, base: str) -> dict[str, object]:
    made = (await client.post(f"{base}/v1/sessions", json={"timeout": 600_000})).json()
    for _ in range(10):
        body = (await client.get(f"{base}/v1/sessions/{made['id']}")).json()
        if str(body.get("status", "")).lower() == "live":
            return dict(body)
        await asyncio.sleep(0.5)
    return dict(body)


async def _cdp(client: httpx.AsyncClient, cdp: str) -> str:
    version = (await client.get(f"{cdp}/json/version")).json()
    path = httpx.URL(str(version["webSocketDebuggerUrl"])).path
    return f"ws://{httpx.URL(cdp).netloc.decode()}{path}"


async def probe(base: str, cdp: str) -> Seen:
    async with httpx.AsyncClient(timeout=30.0) as client:
        first = await _session(client, base)
        second = await _session(client, base)
        second_live = str(second.get("status", "")).lower() == "live"
        same_endpoint = first.get("websocketUrl") == second.get("websocketUrl")
        endpoint = await _cdp(client, cdp)
        async with async_playwright() as driver:
            browser = await driver.chromium.connect_over_cdp(endpoint)
            one, two = await browser.new_context(), await browser.new_context()
            await one.add_cookies([{"name": "who", "value": "one", "url": PROBE}])
            isolated = not await two.cookies(PROBE)
            raw = await browser.new_browser_cdp_session()
            made = await raw.send("Target.createBrowserContext", {"disposeOnDetach": False})
            target = await raw.send(
                "Target.createTarget",
                {"url": "about:blank", "browserContextId": made["browserContextId"]},
            )
            await browser.close()
            again = await driver.chromium.connect_over_cdp(endpoint)
            raw = await again.new_browser_cdp_session()
            targets = (await raw.send("Target.getTargets"))["targetInfos"]
            survives = any(one["targetId"] == target["targetId"] for one in targets)
            await again.close()
        await client.post(f"{base}/v1/sessions/{first['id']}/release")
        after = (await client.get(f"{base}/v1/sessions/{second['id']}")).json()
        other_alive = str(after.get("status", "")).lower() == "live"
        await client.post(f"{base}/v1/sessions/{second['id']}/release")
    return Seen(second_live, same_endpoint, isolated, survives, other_alive)


def main() -> None:
    seen = asyncio.run(probe(sys.argv[1], sys.argv[2]))
    print(json.dumps({"verdict": verdict(seen), **asdict(seen)}, indent=2))


if __name__ == "__main__":
    main()
```

Code notes (`docs/code-notes/backend/scripts/steel_sessions.py.md`): why each of the five observations is taken, that `disposeOnDetach: false` is what a worker restart needs (spec §5.5 "Worker restart"), and that the script is deleted once S4 has recorded the answer.

- [ ] **Step 4: Run it and see it pass**

Run: `cd backend && uv run pytest tests/unit/test_steel_sessions_probe.py -q -o faulthandler_timeout=120`
Expected: `3 passed`.

- [ ] **Step 5: LIVE QA (QA-0, the user runs it)**

On the QA box: `sudo docker compose -f infra/docker-compose.deploy.yml exec -T api python scripts/steel_sessions.py http://steel:3000 http://steel:9223`. Record the printed JSON in the task report and under `SteelClient.open` in `docs/code-notes/backend/src/sro/infrastructure/steel/client.py.md`.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/steel_sessions.py backend/tests/unit/test_steel_sessions_probe.py docs/code-notes/backend/scripts/steel_sessions.py.md docs/code-notes/backend/src/sro/infrastructure/steel/client.py.md
git commit -m "chore(steel): probe sessions and contexts per container (QA-0)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

# Stream E — evidence contract (spec §4)

## A0: The extension records which tab opened a popup (parent spec §5.4; kept from the steel-migration plan)

The extension receives the opener and drops it: `service-worker.js:1337-1355` `popupEvent` reads `d.sourceTabId` only for the policy check, and `pageEvent` (`:1357-1383`) always queues `detail: null`. The runtime depends on the stored opener to tell a run's tabs apart once design 2 derives tab roles.

**Files:**
- Modify: `new-chrome-extension/src/background/service-worker.js:1337-1383` (`popupEvent`, `pageEvent`)
- Modify: `new-chrome-extension/src/background/offering-worker.test.mjs` (the `webNavigation` stub near line 72 holds the popup listener; one new test)
- Modify: `backend/src/sro/application/capture/rig_wire.py:256-269` (`PageEvent.opener_tab_id`)
- Modify: `backend/src/sro/domain/observation/gesture.py:75-81` (`PageMark.opener_tab_id`)
- Modify: `backend/src/sro/application/observation/correlate.py:184-191` (`as_mark`)
- Test: `backend/tests/unit/application/test_correlate.py`

**Interfaces:**
- Produces: queued page event `{kind: "page", page_kind: "popup_opened", tab_id, opener_tab_id, …}`; `PageMark.opener_tab_id: int | None`.
- Consumes: nothing new. No time-order inference anywhere (Global Constraint: no timing windows where a structural signal exists).

- [ ] **Step 1: Write the failing tests**

In `offering-worker.test.mjs`, change the stub line `onCreatedNavigationTarget: { addListener: () => {} },` inside the `webNavigation` stub to `onCreatedNavigationTarget: { addListener: (fn) => (globalThis.__popup = fn) },`, then append:

```js
test("a popup says which tab opened it", async () => {
  ready();
  await queue.clear();

  await globalThis.__popup({
    sourceTabId: TAB,
    tabId: 2,
    url: `${H}/picker`,
    timeStamp: Date.now(),
  });

  const rows = await queue.peek(20);
  const mark = rows
    .map((row) => row.event)
    .find((event) => event.kind === "page" && event.page_kind === "popup_opened");
  assert.equal(mark.tab_id, 2);
  assert.equal(mark.opener_tab_id, TAB);
});
```

In `backend/tests/unit/application/test_correlate.py` append:

```python
def test_a_popup_mark_keeps_the_tab_that_opened_it() -> None:
    popup = {**copy.deepcopy(PAGE_NAVIGATED), "page_kind": "popup_opened", "opener_tab_id": 7}

    _, _, marks, _ = correlate(_batch([popup]), TENANT)

    assert marks[0].opener_tab_id == 7
```

- [ ] **Step 2: Run them and see them fail**

Run: `make test-extension` — Expected: FAIL in `offering-worker.test.mjs`, `assert.equal(mark.opener_tab_id, TAB)`: `undefined !== 1`.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py -q -o faulthandler_timeout=120 -k popup` — Expected: FAIL, `AttributeError: 'PageMark' object has no attribute 'opener_tab_id'`.

- [ ] **Step 3: Implement**

`service-worker.js`:

```js
async function popupEvent(d) {
  // …unchanged down to the watch…
  await pageEvent("popup_opened", d.tabId, d.url, d.timeStamp, d.sourceTabId);
}

async function pageEvent(page_kind, tab_id, url, timeStamp, opener_tab_id = null) {
  try {
    // …unchanged checks…
    await queue.enqueue({
      kind: "page",
      at: new Date(timeStamp).toISOString(),
      page_kind,
      url: redactUrl(url),
      detail: null,
      tab_id,
      opener_tab_id,
    });
  } catch (error) {
    await state.setLastError(`could not queue a page event: ${String(error)}`);
  }
}
```

`rig_wire.py` `PageEvent`: add `opener_tab_id: int | None = None` after `tab_id`.
`gesture.py` `PageMark`: add `opener_tab_id: int | None = None` after `tab_id`.
`correlate.py` `as_mark`: add `opener_tab_id=event.opener_tab_id,`.

- [ ] **Step 4: Run them and see them pass**

Run: `make test-extension && make lint-extension` — Expected: all suites exit 0.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py -q -o faulthandler_timeout=120` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add new-chrome-extension/src/background/service-worker.js new-chrome-extension/src/background/offering-worker.test.mjs backend/src/sro/application/capture/rig_wire.py backend/src/sro/domain/observation/gesture.py backend/src/sro/application/observation/correlate.py backend/tests/unit/application/test_correlate.py
git commit -m "feat(capture): a popup records the tab that opened it

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## E1: Keep what is captured — bounds, attributes, component chain, modifiers (§4.1)

`correlate.py:121-153` `as_action` drops `Target.bounds`, `Target.attributes` (already redacted by `rig_wire.redact_attributes`), `Component.chain` and `Gesture.modifiers`. The stored gesture JSON is the `Action` dumped by `TypeAdapter(Action)` (`infrastructure/db/evidence.py:43-82`), so new dataclass fields need no migration.

**Files:**
- Modify: `backend/src/sro/domain/observation/gesture.py:16-48` (`Component`, `Target`, `Action`)
- Modify: `backend/src/sro/application/observation/correlate.py:121-153` (`as_action`)
- Test: `backend/tests/unit/application/test_correlate.py`

**Interfaces:**
- Produces: `Target.bounds: dict[str, float]`, `Target.attributes: dict[str, Any]` (both `field(default_factory=dict, hash=False)` so a `Target` stays hashable), `Component.chain: tuple[str, ...]`, `Action.modifiers: tuple[str, ...]`.
- Consumed by: X4's page-code payload and snapshot repair (bounds, attributes, chain).

- [ ] **Step 1: Write the failing test**

```python
from sro.infrastructure.db.evidence import _gesture_to_row, _row_to_gesture


def test_every_captured_detail_of_the_control_is_kept_and_stored() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    target = event["gesture"]["target"]
    target["bounds"] = {"x": 10.0, "y": 20.0, "width": 80.0, "height": 24.0}
    target["attributes"] = {"name": "clientCode", "autocomplete": "off"}
    target["component"] = {
        "xtype": "textfield",
        "itemId": "clientCode",
        "query": "panel#clients textfield#clientCode",
        "chain": ["panel#clients", "textfield#clientCode"],
    }
    event["gesture"]["modifiers"] = ["shift"]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)
    stored = _row_to_gesture(_gesture_to_row(gestures[0]))

    action = stored.action
    assert action.target is not None and action.target.component is not None
    assert action.target.bounds == {"x": 10.0, "y": 20.0, "width": 80.0, "height": 24.0}
    assert action.target.attributes == {"name": "clientCode", "autocomplete": "off"}
    assert action.target.component.chain == ("panel#clients", "textfield#clientCode")
    assert action.modifiers == ("shift",)
    assert hash(action)
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py -q -o faulthandler_timeout=120 -k every_captured`
Expected: FAIL, `AttributeError: 'Target' object has no attribute 'bounds'`.

- [ ] **Step 3: Implement**

`gesture.py`:

```python
from typing import Any, Literal
...
@dataclass(frozen=True, slots=True)
class Component:
    item_id: str | None = None
    query: str | None = None
    field_label: str | None = None
    name: str | None = None
    xtype: str | None = None
    required: bool | None = None
    chain: tuple[str, ...] = ()


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
    required: bool | None = None

    component: Component | None = None
    bounds: dict[str, float] = field(default_factory=dict, hash=False)
    attributes: dict[str, Any] = field(default_factory=dict, hash=False)


@dataclass(frozen=True, slots=True)
class Action:
    kind: Kind
    at: float
    value: str | None = None
    secret: bool = False
    url: str | None = None
    target: Target | None = None
    modifiers: tuple[str, ...] = ()
```

`correlate.py` `as_action`: pass `modifiers=tuple(wire.modifiers)` on `Action`, `bounds=dict(target.bounds)` and `attributes=dict(target.attributes)` on `Target`, `chain=tuple(component.chain)` on `Component`.

Code notes (`docs/code-notes/backend/src/sro/domain/observation/gesture.py.md`): `Target.bounds`/`attributes` are excluded from the hash because a dict cannot be hashed and a `Target` is used as a value; what each field is for (spec §4.1, §6.4).

- [ ] **Step 4: Run it and see it pass**

Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py tests/unit/domain -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/domain/observation/gesture.py backend/src/sro/application/observation/correlate.py backend/tests/unit/application/test_correlate.py docs/code-notes/backend/src/sro/domain/observation/gesture.py.md
git commit -m "feat(evidence): keep bounds, attributes, component chain and modifiers

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## E2: The semantic path — labelled ancestors, no debugger (§4.2)

The recorder records the role and accessible name of each region, dialog, grid and form above the element, up to the document. This is the page code's `within` scope (X2 strategy 3).

**Files:**
- Modify: `backend/src/sro/infrastructure/steel/recorder.js:252-303` (`describe` gains `landmarks`; new helpers `landmarkRole`, `ownName`, `landmarksOf` above it)
- Regenerate: `new-chrome-extension/src/content/recorder.generated.js` with `make gen-recorder`
- Create: `new-chrome-extension/src/content/evidence.test.mjs`
- Modify: `backend/src/sro/application/capture/rig_wire.py:68-97` (`Landmark` model, `Target.landmarks`)
- Modify: `backend/src/sro/domain/observation/gesture.py` (`Landmark`, `Target.landmarks`)
- Modify: `backend/src/sro/application/observation/correlate.py` (`as_action`)
- Test: `backend/tests/unit/application/test_correlate.py`

**Interfaces:**
- Produces: recorder target `landmarks: [{role, name}]` outermost first; wire `Landmark(role: str, name: str)` with `name` through `redact_shapes`; domain `Landmark(role: str, name: str)` and `Target.landmarks: tuple[Landmark, ...] = ()`.
- Consumed by: X2 (`within` strategy, snapshot repair score).

- [ ] **Step 1: Write the failing tests**

```js
// new-chrome-extension/src/content/evidence.test.mjs
// Run with `node src/content/evidence.test.mjs`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const source = readFileSync(
  fileURLToPath(new URL("./recorder.generated.js", import.meta.url)),
  "utf8",
);

function body(name) {
  const at = source.indexOf(`const ${name} = (`);
  assert.notEqual(at, -1, `${name} is not in the generated recorder`);
  let depth = 0;
  for (let i = source.indexOf("{", source.indexOf("=>", at)); i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}" && (depth -= 1) === 0) return source.slice(at, i + 1);
  }
  throw new Error(`${name} never closes`);
}

export function lift(names, globals = {}) {
  const text = names.map(body).join(";\n");
  return new Function(
    ...Object.keys(globals),
    `const MAX_TEXT = 200; const MAX_VALUE = 4096; ${text}; return { ${names.join(", ")} };`,
  )(...Object.values(globals));
}

const el = (tag, attrs = {}, parent = null) => ({
  nodeType: 1,
  tagName: tag.toUpperCase(),
  parentElement: parent,
  getAttribute: (name) => (name in attrs ? attrs[name] : null),
});

test("the labelled ancestors are recorded outermost first", () => {
  const document = { getElementById: (id) => (id === "t" ? { innerText: "New Customer" } : null) };
  const { landmarksOf } = lift(["landmarkRole", "ownName", "landmarksOf"], { document });
  const dialog = el("div", { role: "dialog", "aria-labelledby": "t" });
  const form = el("form", { "aria-label": "Customer" }, dialog);
  const unnamed = el("section", {}, form);
  const input = el("input", {}, unnamed);

  assert.deepEqual(landmarksOf(input), [
    { role: "dialog", name: "New Customer" },
    { role: "form", name: "Customer" },
  ]);
});
```

`test_correlate.py`:

```python
def test_the_labelled_ancestors_reach_the_stored_target() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"]["target"]["landmarks"] = [{"role": "dialog", "name": "New Customer"}]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    target = gestures[0].action.target
    assert target is not None
    assert [(one.role, one.name) for one in target.landmarks] == [("dialog", "New Customer")]
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd new-chrome-extension && node --test src/content/evidence.test.mjs` — Expected: FAIL, `landmarkRole is not in the generated recorder`.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py -q -o faulthandler_timeout=120 -k labelled` — Expected: FAIL, `AttributeError: 'Target' object has no attribute 'landmarks'`.

- [ ] **Step 3: Implement**

`recorder.js`, above `describe`:

```js
  const landmarkRole = (el) => {
    const written = el.getAttribute('role');
    const named = ['region', 'dialog', 'alertdialog', 'grid', 'treegrid', 'form'];
    if (written) return named.includes(written) ? written : null;
    const tag = el.tagName.toLowerCase();
    if (tag === 'form') return 'form';
    if (tag === 'dialog') return 'dialog';
    if (tag === 'section') return 'region';
    return null;
  };

  const ownName = (el) => {
    const aria = el.getAttribute('aria-label');
    if (aria && aria.trim()) return aria.trim().slice(0, MAX_TEXT);
    const by = el.getAttribute('aria-labelledby');
    if (!by) return null;
    const said = by
      .split(/\s+/)
      .map((id) => (document.getElementById(id) || {}).innerText || '')
      .join(' ')
      .trim();
    return said ? said.slice(0, MAX_TEXT) : null;
  };

  const landmarksOf = (el) => {
    const found = [];
    for (let node = el.parentElement; node && node.nodeType === 1; node = node.parentElement) {
      const role = landmarkRole(node);
      const name = role ? ownName(node) : null;
      if (role && name) found.unshift({ role, name });
    }
    return found;
  };
```

In `describe`'s returned object add `landmarks: landmarksOf(el),` after `component: component(el),`. Explanations (why only named landmarks, why no debugger) go in `docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md`, not inline. Then run `make gen-recorder`.

`rig_wire.py`:

```python
class Landmark(BaseModel):
    role: str
    name: str

    @model_validator(mode="after")
    def a_credential_in_a_landmark_is_dropped_here(self) -> "Landmark":
        self.name = redact_shapes(self.name)
        return self
```

and on `Target`: `landmarks: list[Landmark] = Field(default_factory=list)`.

`gesture.py`:

```python
@dataclass(frozen=True, slots=True)
class Landmark:
    role: str
    name: str
```

and on `Target`: `landmarks: tuple[Landmark, ...] = ()`. `correlate.py` `as_action` passes `landmarks=tuple(Landmark(role=one.role, name=one.name) for one in target.landmarks)` (import the domain `Landmark`).

- [ ] **Step 4: Run them and see them pass**

Run: `make gen-recorder && make test-extension && make lint-extension` — Expected: exit 0.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py tests/unit/infrastructure/test_generated_scripts_are_current.py -q -o faulthandler_timeout=120` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/infrastructure/steel/recorder.js new-chrome-extension/src/content/recorder.generated.js new-chrome-extension/src/content/evidence.test.mjs backend/src/sro/application/capture/rig_wire.py backend/src/sro/domain/observation/gesture.py backend/src/sro/application/observation/correlate.py backend/tests/unit/application/test_correlate.py docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md
git commit -m "feat(evidence): record the labelled ancestors of the control

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## E3: Frame identity — the iframe path (§4.3)

The recorder records the index chain from the top document to its own frame, with each frame's URL where the frame can read it (its own `location.href`; a cross-origin ancestor's origin from `location.ancestorOrigins`). The UI lane (X4) enters that frame instead of guessing.

**Files:**
- Modify: `backend/src/sro/infrastructure/steel/recorder.js:314-321` (`emit` adds `frame_path`; new helper `framePathOf`)
- Regenerate: `new-chrome-extension/src/content/recorder.generated.js`
- Modify: `new-chrome-extension/src/content/evidence.test.mjs`
- Modify: `backend/src/sro/application/capture/rig_wire.py:100-123` (`FrameHop`, `Gesture.frame_path`)
- Modify: `backend/src/sro/domain/observation/gesture.py` (`FrameHop`, `Action.frame_path`)
- Modify: `backend/src/sro/application/observation/correlate.py` (`as_action`)
- Test: `backend/tests/unit/application/test_correlate.py`

**Interfaces:**
- Produces: record `frame_path: [{index, url}]`, top-level child first, `[]` for the top document; `index` is the position in `parent.frames`; wire `FrameHop(index: int, url: str | None)` with `url` through `redact_url`, `Gesture.frame_path: list[FrameHop] | None = None`; domain `FrameHop(index: int, url: str | None = None)`, `Action.frame_path: tuple[FrameHop, ...] | None = None` — `()` is the top document, `None` is evidence recorded before this change (the UI lane then probes the frames, X4).
- Consumed by: X4 (`SteelDriver._frame`).

- [ ] **Step 1: Write the failing tests**

Append to `evidence.test.mjs`:

```js
test("a frame records where it sits, from the top down", () => {
  const { framePathOf } = lift(["framePathOf"]);
  const top = { frames: [] };
  top.parent = top;
  const shell = { parent: top, frames: [], location: { href: "https://wms.example/shell" } };
  const other = { parent: top, frames: [] };
  top.frames.push(other, shell);
  const screen = {
    parent: shell,
    frames: [],
    location: { href: "https://wms.example/screen?id=4", ancestorOrigins: ["https://wms.example"] },
  };
  shell.frames.push(screen);

  assert.deepEqual(framePathOf(screen), [
    { index: 1, url: "https://wms.example/shell" },
    { index: 0, url: "https://wms.example/screen?id=4" },
  ]);
  assert.deepEqual(framePathOf(top), []);
});
```

`test_correlate.py`:

```python
def test_the_frame_path_reaches_the_stored_action() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"]["frame_path"] = [{"index": 1, "url": "https://wms.example/shell"}]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    hop = gestures[0].action.frame_path[0]
    assert (hop.index, hop.url) == (1, "https://wms.example/shell")
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd new-chrome-extension && node --test src/content/evidence.test.mjs` — Expected: FAIL, `framePathOf is not in the generated recorder`.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py -q -o faulthandler_timeout=120 -k frame_path` — Expected: FAIL, `AttributeError: 'Action' object has no attribute 'frame_path'`.

- [ ] **Step 3: Implement**

`recorder.js`:

```js
  const framePathOf = (win) => {
    const hops = [];
    const origins = (win.location && win.location.ancestorOrigins) || [];
    let depth = 0;
    for (let here = win; here.parent && here !== here.parent; here = here.parent, depth += 1) {
      const parent = here.parent;
      let index = -1;
      for (let i = 0; i < parent.frames.length; i += 1) {
        if (parent.frames[i] === here) index = i;
      }
      let url = null;
      try {
        url = here.location.href;
      } catch {
        url = depth > 0 ? origins[depth - 1] || null : null;
      }
      hops.unshift({ index, url });
    }
    return hops;
  };
```

and in `emit`: `window.__sroRecord(JSON.stringify({ ...record, frame_path: framePathOf(window), at: Date.now() / 1000, url: location.href }));`. Why the ancestor origin stands in for an unreadable URL goes in the recorder's code notes. `make gen-recorder`.

`rig_wire.py`:

```python
class FrameHop(BaseModel):
    index: int
    url: str | None = None

    @model_validator(mode="after")
    def a_credential_in_a_frame_url_is_dropped_here(self) -> "FrameHop":
        if self.url:
            self.url = redact_url(self.url)
        return self
```

and on `Gesture`: `frame_path: list[FrameHop] | None = None`.

`gesture.py`: `FrameHop(index: int, url: str | None = None)` (frozen, slots) and `Action.frame_path: tuple[FrameHop, ...] | None = None`. `as_action`: `frame_path=None if wire.frame_path is None else tuple(FrameHop(index=hop.index, url=hop.url) for hop in wire.frame_path)`.

Add to the correlate test: a gesture event with no `frame_path` key stores `frame_path is None`; one with `"frame_path": []` stores `()`.

- [ ] **Step 4: Run them and see them pass**

Run: `make gen-recorder && make test-extension && make lint-extension` — Expected: exit 0.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py tests/unit/infrastructure/test_generated_scripts_are_current.py -q -o faulthandler_timeout=120` — Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/infrastructure/steel/recorder.js new-chrome-extension/src/content/recorder.generated.js new-chrome-extension/src/content/evidence.test.mjs backend/src/sro/application/capture/rig_wire.py backend/src/sro/domain/observation/gesture.py backend/src/sro/application/observation/correlate.py backend/tests/unit/application/test_correlate.py docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md
git commit -m "feat(evidence): record the iframe path of every gesture

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## E4: Click `detail` and `isTrusted`; an Enter-made submit is recognised structurally (§4.4)

`domain/skill/signing_in.py:34` `K_ONE_SUBMIT_S = 0.05` treats an Enter within 50 ms before the leaving submit as the same submit. A click synthesised by Enter has `detail == 0`. For evidence recorded after this change the window is not consulted; it stays only where the cut carries no click `detail` (older evidence, or a cut that is itself a key press).

**Files:**
- Modify: `backend/src/sro/infrastructure/steel/recorder.js:323-325` (click listener)
- Regenerate: `new-chrome-extension/src/content/recorder.generated.js`
- Modify: `backend/src/sro/application/capture/rig_wire.py:100-123` (`Gesture.detail`, `Gesture.trusted`)
- Modify: `backend/src/sro/domain/observation/gesture.py` (`Action.detail`, `Action.trusted`)
- Modify: `backend/src/sro/application/observation/correlate.py` (`as_action`)
- Modify: `backend/src/sro/domain/skill/signing_in.py:37-96` (`sign_in_chain.refused`, new `_same_submit`)
- Test: `backend/tests/unit/domain/test_the_way_back_in.py`

**Interfaces:**
- Produces: `Action.detail: int | None = None`, `Action.trusted: bool | None = None`.
- Changes: `sign_in_chain` drops the Enter press that produced the cut when `cut.action.detail == 0` and the press is the last cited gesture before the cut.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize(("detail", "kept"), [(0, False), (1, True), (None, True)])
def test_an_enter_that_made_the_submit_click_is_the_same_submit(
    detail: int | None, kept: bool
) -> None:
    job, gestures = _azure()
    gestures["enter"] = _did("enter", KEYCLOAK, 4.5, "press", field="input#password")
    job.steps[2].cites = ["password", "enter"]
    submit = gestures["submit"]
    gestures["submit"] = replace(submit, action=replace(submit.action, detail=detail))

    replayed = {one for step in sign_in_chain(job, gestures) for one in step.cites}

    assert ("enter" in replayed) is kept
```

(With `detail=None` the press is 0.5 s before the cut, outside the 50 ms window, so it is kept exactly as today.)

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_the_way_back_in.py -q -o faulthandler_timeout=120 -k same_submit`
Expected: FAIL, `TypeError: Action.__init__() got an unexpected keyword argument 'detail'` (from `replace`).

- [ ] **Step 3: Implement**

`recorder.js`: `listen('click', (e) => emit({ kind: 'click', target: describe(e.target), modifiers: modifiers(e), detail: e.detail, trusted: e.isTrusted }));` then `make gen-recorder`.

`rig_wire.py` `Gesture`: `detail: int | None = None`, `trusted: bool | None = None`. `gesture.py` `Action`: same two fields. `as_action`: `detail=wire.detail, trusted=wire.trusted`.

`signing_in.py`, inside `sign_in_chain` after `fields = …`:

```python
    before_cut = max(
        (one for one in cited if one.at < cut.at), key=lambda one: one.at, default=None
    )
```

and replace `if gesture.action.kind == "press" and cut.at - gesture.at <= K_ONE_SUBMIT_S:` with `if gesture.action.kind == "press" and _same_submit(cut, gesture, before_cut):`, adding:

```python
def _same_submit(cut: Gesture, press: Gesture, before_cut: Gesture | None) -> bool:
    if cut.action.detail is not None:
        return cut.action.detail == 0 and press is before_cut
    return cut.at - press.at <= K_ONE_SUBMIT_S
```

Code notes (`docs/code-notes/backend/src/sro/domain/skill/signing_in.py.md`): replace the `K_ONE_SUBMIT_S` note with the structural rule and name where the window still applies.

- [ ] **Step 4: Run it and see it pass**

Run: `make gen-recorder && make test-extension`
Run: `cd backend && uv run pytest tests/unit/domain tests/unit/application/test_correlate.py tests/unit/infrastructure/test_generated_scripts_are_current.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/infrastructure/steel/recorder.js new-chrome-extension/src/content/recorder.generated.js backend/src/sro/application/capture/rig_wire.py backend/src/sro/domain/observation/gesture.py backend/src/sro/application/observation/correlate.py backend/src/sro/domain/skill/signing_in.py backend/tests/unit/domain/test_the_way_back_in.py docs/code-notes/backend/src/sro/domain/skill/signing_in.py.md docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md
git commit -m "feat(evidence): record click detail and trust; Enter-made submits by structure

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## E5: After-state — value, visibility and enabled state after each gesture (§4.5)

The state a gesture left is the state its target is in when the operator acts next. Each record carries `prior`: the previous target's state, read in the capture phase before the new gesture's own effects. Correlate hands each `prior` back to the gesture before it on the same tab and frame.

**Files:**
- Modify: `backend/src/sro/infrastructure/steel/recorder.js` (helper `stateOf`, `let last`; `emit(record, el)` adds `prior`; every listener passes its element)
- Regenerate: `new-chrome-extension/src/content/recorder.generated.js`
- Modify: `new-chrome-extension/src/content/evidence.test.mjs`
- Modify: `backend/src/sro/application/capture/rig_wire.py` (`AfterState`, `Gesture.prior`)
- Modify: `backend/src/sro/domain/observation/gesture.py` (`AfterState`, `Action.after`)
- Modify: `backend/src/sro/application/observation/correlate.py:39-90` (`correlate` joins priors)
- Test: `backend/tests/unit/application/test_correlate.py`

**Interfaces:**
- Produces: domain `AfterState(value: str | None = None, visible: bool | None = None, enabled: bool | None = None)`; `Action.after: AfterState | None = None`. A credential field's value is never read (`stateOf` returns `value: null` for `isSecretField`).
- Consumed by: `domain/execution/lanes.after_matches` (X3), UI lane verification (X4), sight goal (X7).

- [ ] **Step 1: Write the failing tests**

`evidence.test.mjs`:

```js
test("the state a gesture left is read without a credential", () => {
  const window = { getComputedStyle: () => ({ visibility: "visible", display: "block" }) };
  const { stateOf } = lift(["isSecretName", "isSecretField", "stateOf"], {
    window,
    SECRET_WORDS: new Set(["password"]),
    wordsOf: (text) => String(text || "").toLowerCase().split(/[^a-z]+/).filter(Boolean),
  });
  const box = () => ({ width: 10, height: 10 });
  const field = (attrs, value) => ({
    nodeType: 1, isConnected: true, value, disabled: false, type: attrs.type || "text",
    getAttribute: (name) => attrs[name] ?? null, getBoundingClientRect: box,
  });

  assert.deepEqual(stateOf(field({ name: "code" }, "GT2")), { value: "GT2", visible: true, enabled: true });
  assert.equal(stateOf(field({ type: "password" }, "hunter2")).value, null);
});
```

`test_correlate.py`:

```python
def test_a_gesture_gets_the_state_its_target_was_in_when_the_next_one_came() -> None:
    first = copy.deepcopy(GESTURE_TYPE)
    second = copy.deepcopy(GESTURE_TYPE)
    second["gesture"]["at"] = first["gesture"]["at"] + 2
    second["gesture"]["prior"] = {"value": "GT2", "visible": True, "enabled": True}

    gestures, _, _, _ = correlate(_batch([first, second]), TENANT)

    after = gestures[0].action.after
    assert after is not None
    assert (after.value, after.visible, after.enabled) == ("GT2", True, True)
    assert gestures[1].action.after is None
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd new-chrome-extension && node --test src/content/evidence.test.mjs` — Expected: FAIL, `stateOf is not in the generated recorder`.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py -q -o faulthandler_timeout=120 -k next_one_came` — Expected: FAIL, `AttributeError: 'Action' object has no attribute 'after'`.

- [ ] **Step 3: Implement**

`recorder.js`, after `isSecretField`:

```js
  const stateOf = (el) => {
    if (!el || el.nodeType !== 1 || el.isConnected === false) {
      return { value: null, visible: false, enabled: null };
    }
    const box = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    const visible =
      box.width > 0 && box.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    const enabled = !(el.disabled === true || el.getAttribute('aria-disabled') === 'true');
    const value =
      isSecretField(el) || el.value === undefined || el.value === null
        ? null
        : String(el.value).slice(0, MAX_VALUE);
    return { value, visible, enabled };
  };

  let last = null;
```

`emit` becomes `const emit = (record, el = null) => { const prior = last ? stateOf(last) : null; last = el; try { window.__sroRecord(JSON.stringify({ ...record, prior, frame_path: framePathOf(window), at: Date.now() / 1000, url: location.href })); } catch { } };` and each listener passes its element: `emit({...}, e.target)` for click/keydown, `emit({...}, el)` for change/upload; scroll passes nothing. Why "the state at the next gesture" is the after-state, and the ceiling (the last gesture of a batch keeps no after-state; upgrade: update the stored previous gesture at ingest), go in the recorder's and correlate's code notes. `make gen-recorder`.

`rig_wire.py`:

```python
class AfterState(BaseModel):
    value: str | None = None
    visible: bool | None = None
    enabled: bool | None = None

    @model_validator(mode="after")
    def a_credential_in_a_state_is_dropped_here(self) -> "AfterState":
        if self.value:
            self.value = redact_shapes(self.value)
        return self
```

and `Gesture.prior: AfterState | None = None`.

`gesture.py`: `AfterState` dataclass (frozen, slots) and `Action.after: AfterState | None = None`.

`correlate.py`:

```python
    priors: dict[str, AfterState] = {}
    ...
        elif isinstance(event, GestureEvent):
            gesture = Gesture(...)
            gestures.append(gesture)
            if event.gesture.prior is not None:
                prior = event.gesture.prior
                priors[gesture.id] = AfterState(prior.value, prior.visible, prior.enabled)
    ...
    gestures.sort(key=lambda gesture: gesture.at)
    _join_after_states(gestures, priors)


def _join_after_states(gestures: list[Gesture], priors: Mapping[str, AfterState]) -> None:
    last: dict[tuple[int | None, str | None], Gesture] = {}
    for gesture in gestures:
        key = (gesture.tab_id, gesture.frame_url)
        before = last.get(key)
        if before is not None and gesture.id in priors:
            before.action = replace(before.action, after=priors[gesture.id])
        last[key] = gesture
```

- [ ] **Step 4: Run them and see them pass**

Run: `make gen-recorder && make test-extension && make lint-extension`
Run: `cd backend && uv run pytest tests/unit/application tests/unit/infrastructure/test_generated_scripts_are_current.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/infrastructure/steel/recorder.js new-chrome-extension/src/content/recorder.generated.js new-chrome-extension/src/content/evidence.test.mjs backend/src/sro/application/capture/rig_wire.py backend/src/sro/domain/observation/gesture.py backend/src/sro/application/observation/correlate.py backend/tests/unit/application/test_correlate.py docs/code-notes/backend/src/sro/infrastructure/steel/recorder.js.md docs/code-notes/backend/src/sro/application/observation/correlate.py.md
git commit -m "feat(evidence): record the state each gesture left its control in

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## E6: A snapshot is stored with its gesture, not counted and dropped (§4.6)

`correlate.py:46-47` counts every `SnapshotEvent` as ignored. The extension enqueues the tree taken before a gesture immediately after that gesture, on the same tab (`service-worker.js:1695-1697`, `takeTree(tab_id)`), so the tree belongs to the latest gesture in batch order on its tab. The accessibility graph stays off by default (`ObservationPolicy.capture_snapshots = False`).

**Files:**
- Modify: `backend/src/sro/application/capture/rig_wire.py:272-276` (`SnapshotEvent.tab_id`)
- Modify: `backend/src/sro/domain/observation/gesture.py:84-98` (`Gesture.tree`)
- Modify: `backend/src/sro/application/observation/correlate.py:39-90` (attach the tree)
- Modify: `backend/src/sro/application/observation/redact.py:25-51` (`_tree`)
- Modify: `backend/src/sro/infrastructure/db/models.py:460-485` (`GestureRow.tree`)
- Modify: `backend/src/sro/infrastructure/db/evidence.py:49-82`
- Create: `backend/migrations/versions/2026xxxx_0073_a_gesture_keeps_its_tree.py`
- Test: `backend/tests/unit/application/test_correlate.py`, `backend/tests/unit/application/test_an_extension_uploads_what_it_saw.py` (edit only if its snapshot count now differs), `backend/tests/integration/test_evidence_repositories.py`

**Interfaces:**
- Produces: `Gesture.tree: dict[str, Any] | None = None`; `correlate(...)[3]` now counts only snapshots that belong to no gesture (the name `snapshots_ignored` is kept on the wire).
- Redaction: a tree node whose `name` is a credential name (`sensitivity.is_secret_field`) loses its `value`; every string still goes through `redact_shapes`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_tree_taken_before_a_gesture_is_stored_with_it() -> None:
    tab = GESTURE_TYPE["tab_id"]
    tree = {"kind": "snapshot", "tab_id": tab, "taken_at": "2026-08-31T08:40:04.600Z",
            "snapshot": {"nodes": [{"role": {"value": "textbox"}, "name": {"value": "Client"}}]}}

    gestures, _, _, unplaced = correlate(_batch([GESTURE_TYPE, tree]), TENANT)

    assert gestures[0].tree == {"nodes": [{"role": {"value": "textbox"}, "name": {"value": "Client"}}]}
    assert unplaced == 0


def test_a_tree_with_no_gesture_before_it_on_its_tab_is_counted() -> None:
    tree = {"kind": "snapshot", "tab_id": 999, "snapshot": {"nodes": []}}

    _, _, _, unplaced = correlate(_batch([GESTURE_TYPE, tree]), TENANT)

    assert unplaced == 1
```

In `backend/tests/unit/application/test_redaction_of_trees.py` (new):

```python
from sro.application.observation.redact import redact_events


def test_a_password_node_keeps_no_value() -> None:
    event = {
        "kind": "snapshot",
        "snapshot": {
            "nodes": [
                {"name": {"value": "Password"}, "value": {"value": "hunter2"}},
                {"name": {"value": "Client"}, "value": {"value": "ACME"}},
            ]
        },
    }

    (out,) = redact_events([event])

    nodes = out["snapshot"]["nodes"]
    assert "value" not in nodes[0]
    assert nodes[1]["value"] == {"value": "ACME"}
```

In `test_evidence_repositories.py` add a round trip that saves a gesture with `tree={"nodes": [...]}` through `SqlGestureRepository.add_gestures` and reads the same dict back from `gestures_for`.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py tests/unit/application/test_redaction_of_trees.py -q -o faulthandler_timeout=120`
Expected: FAIL, `AttributeError: 'Gesture' object has no attribute 'tree'` and `AssertionError` on `"value" not in nodes[0]`.

- [ ] **Step 3: Implement**

`rig_wire.py` `SnapshotEvent`: add `tab_id: int | None = None`. `gesture.py` `Gesture`: add `tree: dict[str, Any] | None = None` after `page_events`.

`correlate.py`:

```python
    unplaced = 0
    last_on_tab: dict[int | None, Gesture] = {}
    for event in batch.events:
        if isinstance(event, SnapshotEvent):
            owner = last_on_tab.get(event.tab_id)
            if owner is None or owner.tree is not None:
                unplaced += 1
            else:
                owner.tree = dict(event.snapshot)
        elif isinstance(event, GestureEvent):
            gesture = Gesture(...)
            gestures.append(gesture)
            last_on_tab[event.tab_id] = gesture
        ...
    return gestures, orphan_requests, orphan_pages, unplaced
```

`redact.py`: in `_event`, replace `out["snapshot"] = _shapes_only(snapshot)` with `out["snapshot"] = _tree(snapshot)`, adding:

```python
def _tree(node: object) -> object:
    if isinstance(node, list):
        return [_tree(one) for one in node]
    if not isinstance(node, Mapping):
        return redact_shapes(node) if isinstance(node, str) else node
    out = {key: _tree(value) for key, value in node.items()}
    named = out.get("name")
    said = named.get("value") if isinstance(named, Mapping) else named
    if isinstance(said, str) and is_secret_field(said):
        out.pop("value", None)
    return out
```

`models.py` `GestureRow`: `tree: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True), nullable=True)`. `evidence.py`: `tree=gesture.tree` in `_gesture_to_row`, `tree=row.tree` in `_row_to_gesture`.

Migration (take the next number at merge):

```python
"""a gesture keeps its tree

Revision ID: 0073
Revises: 0072
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gestures", sa.Column("tree", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("gestures", "tree")
```

Code notes: `correlate` (why queue order places a tree; that an unplaced tree is counted, not silently dropped) and `redact._tree`.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/application -q -o faulthandler_timeout=120`
Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_evidence_repositories.py tests/integration/test_the_migrations_run.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/capture/rig_wire.py backend/src/sro/domain/observation/gesture.py backend/src/sro/application/observation/correlate.py backend/src/sro/application/observation/redact.py backend/src/sro/infrastructure/db/models.py backend/src/sro/infrastructure/db/evidence.py backend/migrations/versions/*_0073_a_gesture_keeps_its_tree.py backend/tests docs/code-notes
git commit -m "feat(evidence): store the tree taken before a gesture with that gesture

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## E7: Sign-in pages are captured under redaction (§5.6 last paragraph)

`domain/observation/policy.py:9-13` `DEFAULT_EXCLUSIONS` is a host list of identity providers. Sign-in pages are captured like any other page; the recorder already drops a credential field's value, `is_secret_field` replaces credential-named body fields, and `_redact_query` redacts an OAuth `code` beside its companions.

**Files:**
- Modify: `backend/src/sro/domain/observation/policy.py:9-13`
- Create: `backend/migrations/versions/2026xxxx_0074_sign_in_pages_are_watched.py`
- Modify: `backend/tests/unit/domain/test_observation_policy.py`
- Modify: `backend/tests/browser/conftest.py` (`_Stub.do_GET`: serve `/sign-in` and `/callback`)
- Modify: `backend/tests/browser/test_the_extension_in_a_real_chrome.py` (one test)

**Interfaces:**
- Produces: `DEFAULT_EXCLUSIONS: tuple[str, ...] = ()`. A stored policy whose `exclude_hosts` is exactly the old default list is healed to `[]` by the migration; any other list is the owner's choice and stays (named in the task report).

- [ ] **Step 1: Write the failing tests**

`test_observation_policy.py`:

```python
def test_an_identity_provider_is_watched_like_any_other_host() -> None:
    policy = ObservationPolicy().enabled()

    assert policy.allows("https://login.microsoftonline.com/common/oauth2/v2.0/authorize")
    assert policy.allows("https://blueyonderalphaus.b2clogin.com/x")
```

`conftest.py` `_Stub.do_GET`, before the `/mail` branch:

```python
        if self.path.startswith("/sign-in"):
            self._send(200, SIGN_IN_PAGE.encode(), "text/html; charset=utf-8")
            return
        if self.path.startswith("/callback"):
            self._send(200, b"<!doctype html><p>signed in</p>", "text/html; charset=utf-8")
            return
```

with

```python
SIGN_IN_PAGE = """<!doctype html><html><body>
  <form method="get" action="/callback">
    <input id="u" name="username" autocomplete="username">
    <input id="p" name="password" type="password" autocomplete="current-password">
    <input id="o" name="otp" autocomplete="one-time-code">
    <input type="hidden" name="state" value="s1">
    <input type="hidden" name="code" value="AUTHCODE-NOT-A-SECRET">
    <button id="go" type="submit">Sign in</button>
  </form>
</body></html>"""
```

`test_the_extension_in_a_real_chrome.py`:

```python
def test_a_sign_in_page_is_recorded_without_a_credential(browser: Any, stub: Any) -> None:
    base, batches = stub
    worker = _service_worker(browser)
    _sign_in(browser, worker, base)
    page = _drive(browser, f"{base}/sign-in")
    page.fill("#u", "operator")
    page.fill("#p", "hunter2-not-real")
    page.fill("#o", "424242")
    page.click("#go")
    page.wait_for_url("**/callback**")
    _flush(browser, worker)

    sent = json.dumps(batches)
    assert "operator" in sent
    for secret in ("hunter2-not-real", "424242", "AUTHCODE-NOT-A-SECRET"):
        assert secret not in sent
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_observation_policy.py -q -o faulthandler_timeout=120 -k identity_provider` — Expected: FAIL, `assert False` (the default excludes the host).
Run: `cd backend && uv run pytest tests/browser/test_the_extension_in_a_real_chrome.py -q -o faulthandler_timeout=120 -k sign_in_page` — Expected: PASS or FAIL. If a secret appears in `sent`, the leak is fixed in `domain/recording/sensitivity.py` (then `make gen-recorder`), never in the test.

- [ ] **Step 3: Implement**

`policy.py`: `DEFAULT_EXCLUSIONS: tuple[str, ...] = ()`.

Migration:

```python
"""sign-in pages are watched

A policy whose exclusions are exactly the old identity-provider default held
that default, not a choice, so it becomes empty. Any other list stays.

Revision ID: 0074
Revises: 0073
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None

OLD_DEFAULT = ["accounts.google.com", "login.microsoftonline.com", "b2clogin.com"]


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE observation_policies SET policy = jsonb_set(policy, '{exclude_hosts}', "
            "'[]'::jsonb) WHERE policy -> 'exclude_hosts' = CAST(:old AS jsonb)"
        ).bindparams(old=json.dumps(OLD_DEFAULT))
    )


def downgrade() -> None:
    return None
```

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_observation_policy.py -q -o faulthandler_timeout=120`
Run: `cd backend && uv run pytest tests/browser/test_the_extension_in_a_real_chrome.py -q -o faulthandler_timeout=120`
Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_the_migrations_run.py -q -o faulthandler_timeout=120`
Expected: all pass. Report every stored policy row the migration left alone.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/domain/observation/policy.py backend/migrations/versions/*_0074_sign_in_pages_are_watched.py backend/tests/unit/domain/test_observation_policy.py backend/tests/browser/conftest.py backend/tests/browser/test_the_extension_in_a_real_chrome.py docs/code-notes/backend/src/sro/domain/observation/policy.py.md
git commit -m "feat(capture): watch sign-in pages under redaction, no identity-provider host list

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

# Stream S — session broker and Steel pool (spec §5)

## S1: Accounts, leases and account-scoped vault keys (§5.2, §5.3 "Vault keys")

Vault keys today are `{tenant}/{origin}/{field}` (`domain/execution/secrets.py:35` `secret_key_of`), so two systems behind one identity provider, or two operators on one system, share a password key. The account key includes the username.

**Files:**
- Create: `backend/src/sro/domain/execution/account.py`
- Create: `backend/tests/unit/domain/test_an_account_has_its_own_keys.py`
- Modify: `backend/src/sro/interface/http/schemas.py:2003-2023` (`NewSecretRequest.username`)
- Modify: `backend/src/sro/interface/http/v1/routers/secrets.py:47-66` (`store_secret`)
- Modify: `backend/tests/unit/interface/test_a_password_goes_in_and_never_comes_out.py` (one test)
- Run: `make types` (commit `frontend/openapi.json`, `frontend/src/lib/api/generated.ts`)

**Interfaces:**
- Produces:
  - `Account(tenant: str, origin: str, username: str)`, `Account.of(tenant, system, username) -> Account`, `.key -> str`, `.vault_key("password" | "state") -> str` = `{tenant}/{origin}/{username}/password|state`, `.lock_id -> int` (signed 64-bit, for `pg_advisory_lock`).
  - `LeaseState` (`signing_in`, `ready`, `expired`, `broken`), `LIVE: frozenset[LeaseState]`.
  - `Lease(id, account, container_url, steel_session_id, holder, heartbeat_at, expires_at, state)`, `Lease.live(now) -> bool`, `new_lease_id() -> str` (`lse_…`).
  - `K_LEASE_TTL = timedelta(minutes=2)`, `K_VAULT_VALUE_BYTES = 64 * 1024`.
  - `PUT /v1/secrets` with `username` and `field == "password"` stores under `Account.of(tenant, system, username).vault_key("password")`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/domain/test_an_account_has_its_own_keys.py
from datetime import UTC, datetime, timedelta

from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState

NOW = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)


def test_two_systems_behind_one_provider_keep_two_passwords() -> None:
    wms = Account.of("greyorange", "https://wms.example/portal", "lena")
    tms = Account.of("greyorange", "https://tms.example/", "lena")

    assert wms.vault_key("password") == "greyorange/https://wms.example/lena/password"
    assert wms.vault_key("password") != tms.vault_key("password")


def test_two_operators_on_one_system_keep_two_states() -> None:
    lena = Account.of("greyorange", "https://wms.example", "Lena@Example.com")
    omar = Account.of("greyorange", "https://wms.example", "omar@example.com")

    assert lena.vault_key("state") == "greyorange/https://wms.example/lena@example.com/state"
    assert lena.vault_key("state") != omar.vault_key("state")
    assert lena.lock_id != omar.lock_id


def test_a_username_cannot_reach_into_another_key() -> None:
    sly = Account.of("greyorange", "https://wms.example", "a/../b")

    assert "/../" not in sly.vault_key("password")


def test_a_lease_is_live_until_its_heartbeat_runs_out() -> None:
    lease = Lease(
        "lse_1", Account.of("t", "https://wms.example", "lena"), "http://steel:3000", "s1",
        "run_1", NOW, NOW + K_LEASE_TTL, LeaseState.READY,
    )

    assert lease.live(NOW + timedelta(seconds=30))
    assert not lease.live(NOW + K_LEASE_TTL)
```

In `test_a_password_goes_in_and_never_comes_out.py`:

```python
async def test_a_password_given_with_its_username_is_kept_for_that_account(
    client: httpx.AsyncClient, container: _FakeContainer
) -> None:
    stored = await client.put("/v1/secrets", json=_body(system=f"https://{WMS}", username="lena"))

    key = f"{f.TENANT.value}/https://{WMS}/lena/password"
    assert stored.json() == {"key": key}
    assert await container.vault.get(key) == KEPT
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_an_account_has_its_own_keys.py tests/unit/interface/test_a_password_goes_in_and_never_comes_out.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.domain.execution.account'`, and the route test answers the old key.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/domain/execution/account.py
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal
from urllib.parse import quote

from sro.domain.shared.hosts import origin_of

K_LEASE_TTL = timedelta(minutes=2)

K_VAULT_VALUE_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class Account:
    tenant: str
    origin: str
    username: str

    @classmethod
    def of(cls, tenant: str, system: str, username: str) -> Account:
        return cls(tenant, origin_of(system) or system.strip().lower(), username.strip())

    @property
    def key(self) -> str:
        return f"{self.tenant}/{self.origin}/{quote(self.username.casefold(), safe='@+-_')}"

    def vault_key(self, what: Literal["password", "state"]) -> str:
        return f"{self.key}/{what}"

    @property
    def lock_id(self) -> int:
        return int.from_bytes(hashlib.sha256(self.key.encode()).digest()[:8], "big", signed=True)


class LeaseState(StrEnum):
    SIGNING_IN = "signing_in"
    READY = "ready"
    EXPIRED = "expired"
    BROKEN = "broken"


LIVE = frozenset({LeaseState.SIGNING_IN, LeaseState.READY})


@dataclass(frozen=True, slots=True)
class Lease:
    id: str
    account: Account
    container_url: str
    steel_session_id: str
    holder: str
    heartbeat_at: datetime
    expires_at: datetime
    state: LeaseState

    def live(self, now: datetime) -> bool:
        return self.state in LIVE and now < self.expires_at


def new_lease_id() -> str:
    return "lse_" + secrets.token_hex(16)
```

(`quote` with `safe='@+-_'` encodes `/` and `.`, so no username can form `/../`.)

`schemas.py` `NewSecretRequest`: add

```python
    username: str | None = None
    """The account this password signs in as. Given, the password is kept for
    that account alone, so two operators, or two systems behind one identity
    provider, never share one."""
```

`secrets.py` `store_secret`:

```python
    key = (
        Account.of(ctx.tenant_id.value, body.system, body.username).vault_key("password")
        if body.username and body.field == "password"
        else secret_key_of(ctx.tenant_id.value, body.system, body.field)
    )
```

Code notes (`docs/code-notes/backend/src/sro/domain/execution/account.py.md`): why the username is in the key (the collision), why `K_LEASE_TTL` is two minutes (four missed 30 s heartbeats), and the 64 KiB Secret Manager limit.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_an_account_has_its_own_keys.py tests/unit/interface -q -o faulthandler_timeout=120 && cd .. && make types && cd backend && uv run pytest tests/contract -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/domain/execution/account.py backend/tests/unit/domain/test_an_account_has_its_own_keys.py backend/src/sro/interface/http/schemas.py backend/src/sro/interface/http/v1/routers/secrets.py backend/tests/unit/interface/test_a_password_goes_in_and_never_comes_out.py frontend/openapi.json frontend/src/lib/api/generated.ts docs/code-notes/backend/src/sro/domain/execution/account.py.md
git commit -m "feat(sessions): accounts, leases and vault keys that include the username

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S2: Leases in Postgres, one live lease per account (§5.2)

`browser_sessions` (`infrastructure/db/models.py:247-255`) holds only capture sessions. It gains the lease fields and a unique partial index. `held_by` and `all_held` keep answering for capture sessions only (rows with no `state`), so the stray sweeper can never mistake a lease row for an orphaned capture session.

**Files:**
- Modify: `backend/src/sro/infrastructure/db/models.py:247-255` (`BrowserSessionRow`)
- Create: `backend/migrations/versions/2026xxxx_0075_a_session_is_leased.py`
- Modify: `backend/src/sro/application/ports/repositories.py:178-191` (`BrowserSessionRepository`)
- Modify: `backend/src/sro/infrastructure/db/repositories.py:524-566` (`SqlBrowserSessionRepository`)
- Modify: `backend/tests/unit/fakes.py:910-940` (`FakeBrowserSessionRepository`)
- Create: `backend/tests/integration/test_leases.py`

**Interfaces:**
- Produces on `BrowserSessionRepository`:
  - `lease(tenant_id: TenantId, lease: Lease) -> Lease` — inserts; if the account already has a live-state lease, returns that one instead.
  - `current_lease(tenant_id: TenantId, account: Account) -> Lease | None` — the account's lease in a live state (`signing_in`/`ready`), whatever its `expires_at`.
  - `get_lease(tenant_id: TenantId, lease_id: str) -> Lease | None`
  - `settle(tenant_id: TenantId, lease_id: str, *, state: LeaseState) -> None`
  - `beat(tenant_id: TenantId, lease_id: str, *, now: datetime, holder: str | None = None) -> None` — `heartbeat_at = now`, `expires_at = now + K_LEASE_TTL`.
  - `expired(*, now: datetime) -> tuple[Lease, ...]` — live-state leases with `expires_at <= now` (all tenants; the sweeper's read).
  - `busy_containers(*, now: datetime) -> tuple[str, ...]` — one entry per live lease, its `container_url`.
  - `leased_sessions() -> frozenset[str]` — the Steel session ids of every live-state lease (all tenants; the stray sweeper must never close one).

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/integration/test_leases.py
from datetime import UTC, datetime, timedelta

from sro.domain.execution.account import K_LEASE_TTL, Account, Lease, LeaseState
from sro.domain.shared.identifiers import BrowserSessionId, PrincipalId, TenantId
from sro.infrastructure.db.repositories import SqlBrowserSessionRepository

T = TenantId("greyorange")
NOW = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)
LENA = Account.of("greyorange", "https://wms.example", "lena")


def _lease(lease_id: str, container: str = "http://steel:3000") -> Lease:
    return Lease(lease_id, LENA, container, f"s-{lease_id}", "run_1", NOW, NOW + K_LEASE_TTL,
                 LeaseState.SIGNING_IN)


async def test_an_account_holds_one_live_lease(session) -> None:
    repo = SqlBrowserSessionRepository(session)

    first = await repo.lease(T, _lease("lse_a"))
    second = await repo.lease(T, _lease("lse_b"))

    assert second.id == first.id == "lse_a"


async def test_a_beaten_lease_outlives_its_ttl_and_a_silent_one_expires(session) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.READY)

    await repo.beat(T, "lse_a", now=NOW + timedelta(minutes=10))

    assert await repo.expired(now=NOW + timedelta(minutes=11)) == ()
    gone = await repo.expired(now=NOW + timedelta(minutes=13))
    assert [one.id for one in gone] == ["lse_a"]


async def test_a_settled_lease_frees_the_account_and_its_container(session) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.settle(T, "lse_a", state=LeaseState.EXPIRED)

    fresh = await repo.lease(T, _lease("lse_b", "http://steel-2:3000"))

    assert fresh.id == "lse_b"
    assert await repo.busy_containers(now=NOW) == ("http://steel-2:3000",)


async def test_capture_sessions_never_see_a_lease(session) -> None:
    repo = SqlBrowserSessionRepository(session)
    await repo.lease(T, _lease("lse_a"))
    await repo.claim(T, BrowserSessionId("capture-1"), PrincipalId("op"), NOW)

    assert await repo.held_by(T) == (BrowserSessionId("capture-1"),)
    assert [held for held, _ in await repo.all_held()] == [BrowserSessionId("capture-1")]
```

(Use the integration suite's existing `session` fixture from `backend/tests/integration/conftest.py`.)

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_leases.py -q -o faulthandler_timeout=120`
Expected: FAIL, `AttributeError: 'SqlBrowserSessionRepository' object has no attribute 'lease'`.

- [ ] **Step 3: Implement**

`models.py` `BrowserSessionRow` — add:

```python
    origin: Mapped[str | None] = mapped_column(Text)
    username: Mapped[str | None] = mapped_column(Text)
    container_url: Mapped[str | None] = mapped_column(Text)
    steel_session_id: Mapped[str | None] = mapped_column(String(128))
    holder: Mapped[str | None] = mapped_column(String(128))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str | None] = mapped_column(String(16))

    __table_args__ = (
        Index("ix_browser_sessions_tenant", "tenant_id"),
        Index(
            "uq_browser_sessions_one_live_lease",
            "tenant_id",
            "origin",
            "username",
            unique=True,
            postgresql_where=text("state IN ('signing_in', 'ready')"),
        ),
    )
```

Migration `0075` adds the eight nullable columns with `op.add_column` and creates the index with `op.create_index(..., unique=True, postgresql_where=sa.text("state IN ('signing_in', 'ready')"))`; `downgrade` drops them.

`repositories.py`:

```python
_LIVE_STATES = tuple(state.value for state in LIVE)


def _lease_of(row: BrowserSessionRow) -> Lease:
    return Lease(
        id=row.session_id,
        account=Account(row.tenant_id, row.origin or "", row.username or ""),
        container_url=row.container_url or "",
        steel_session_id=row.steel_session_id or "",
        holder=row.holder or "",
        heartbeat_at=row.heartbeat_at or row.opened_at,
        expires_at=row.expires_at or row.opened_at,
        state=LeaseState(row.state),
    )


class SqlBrowserSessionRepository(BrowserSessionRepository):
    ...
    async def lease(self, tenant_id: TenantId, lease: Lease) -> Lease:
        await self._session.execute(
            pg_insert(BrowserSessionRow)
            .values(
                session_id=lease.id,
                tenant_id=tenant_id.value,
                opened_by=lease.holder,
                opened_at=lease.heartbeat_at,
                origin=lease.account.origin,
                username=lease.account.username,
                container_url=lease.container_url,
                steel_session_id=lease.steel_session_id,
                holder=lease.holder,
                heartbeat_at=lease.heartbeat_at,
                expires_at=lease.expires_at,
                state=lease.state.value,
            )
            .on_conflict_do_nothing(
                index_elements=["tenant_id", "origin", "username"],
                index_where=BrowserSessionRow.state.in_(_LIVE_STATES),
            )
        )
        current = await self.current_lease(tenant_id, lease.account)
        assert current is not None
        return current

    async def current_lease(self, tenant_id: TenantId, account: Account) -> Lease | None:
        row = await self._session.scalar(
            select(BrowserSessionRow).where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.origin == account.origin,
                BrowserSessionRow.username == account.username,
                BrowserSessionRow.state.in_(_LIVE_STATES),
            )
        )
        return None if row is None else _lease_of(row)

    async def get_lease(self, tenant_id: TenantId, lease_id: str) -> Lease | None:
        row = await self._session.get(BrowserSessionRow, lease_id)
        if row is None or row.tenant_id != tenant_id.value or row.state is None:
            return None
        return _lease_of(row)

    async def settle(self, tenant_id: TenantId, lease_id: str, *, state: LeaseState) -> None:
        await self._session.execute(
            update(BrowserSessionRow)
            .where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.session_id == lease_id,
            )
            .values(state=state.value)
        )

    async def beat(
        self, tenant_id: TenantId, lease_id: str, *, now: datetime, holder: str | None = None
    ) -> None:
        values: dict[str, object] = {"heartbeat_at": now, "expires_at": now + K_LEASE_TTL}
        if holder is not None:
            values["holder"] = holder
        await self._session.execute(
            update(BrowserSessionRow)
            .where(
                BrowserSessionRow.tenant_id == tenant_id.value,
                BrowserSessionRow.session_id == lease_id,
                BrowserSessionRow.state.in_(_LIVE_STATES),
            )
            .values(**values)
        )

    async def expired(self, *, now: datetime) -> tuple[Lease, ...]:
        rows = await self._session.scalars(
            select(BrowserSessionRow).where(
                BrowserSessionRow.state.in_(_LIVE_STATES), BrowserSessionRow.expires_at <= now
            )
        )
        return tuple(_lease_of(row) for row in rows)

    async def busy_containers(self, *, now: datetime) -> tuple[str, ...]:
        rows = await self._session.scalars(
            select(BrowserSessionRow.container_url).where(
                BrowserSessionRow.state.in_(_LIVE_STATES), BrowserSessionRow.expires_at > now
            )
        )
        return tuple(str(url) for url in rows)

    async def leased_sessions(self) -> frozenset[str]:
        rows = await self._session.scalars(
            select(BrowserSessionRow.steel_session_id).where(
                BrowserSessionRow.state.in_(_LIVE_STATES)
            )
        )
        return frozenset(str(one) for one in rows if one)
```

and add `BrowserSessionRow.state.is_(None)` to the `where` of `held_by` and to `all_held`.

`ports/repositories.py`: declare the eight methods with the signatures above. `fakes.py`: `FakeBrowserSessionRepository.leases: dict[str, Lease]` implementing the same rules (one live-state lease per `(tenant, origin, username)`; `beat` only on a live state) — the rule, not the mechanism.

- [ ] **Step 4: Run it and see it pass**

Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_leases.py tests/integration/test_the_migrations_run.py tests/integration/test_repositories.py -q -o faulthandler_timeout=120 && uv run pytest tests/unit -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/infrastructure/db/models.py backend/migrations/versions/*_0075_a_session_is_leased.py backend/src/sro/application/ports/repositories.py backend/src/sro/infrastructure/db/repositories.py backend/tests/unit/fakes.py backend/tests/integration/test_leases.py docs/code-notes
git commit -m "feat(sessions): lease a browser per account in browser_sessions

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S3: The per-account lock is a Postgres advisory lock (§5.4)

Anything that changes an account's session (restore, sign-in, re-sign-in) takes it; ordinary steps never do. It holds across worker processes because Postgres holds it.

**Files:**
- Create: `backend/src/sro/application/ports/locks.py`
- Create: `backend/src/sro/infrastructure/db/locks.py`
- Modify: `backend/src/sro/container.py:183-230` (field `locks: AccountLocks`; built in `build_container` at `:896-975` as `PostgresAccountLocks(engine)`)
- Modify: `backend/tests/unit/fakes.py` (`FakeAccountLocks`)
- Create: `backend/tests/integration/test_account_locks.py`

**Interfaces:**
- Produces: `AccountLocks.hold(account: Account) -> AbstractAsyncContextManager[None]`; `K_LOCK_WAIT_S = 120` (in `infrastructure/db/locks.py`, passed as Postgres `lock_timeout`).

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/integration/test_account_locks.py
import asyncio

import pytest

from sro.domain.execution.account import Account
from sro.infrastructure.db.locks import PostgresAccountLocks

LENA = Account.of("greyorange", "https://wms.example", "lena")
OMAR = Account.of("greyorange", "https://wms.example", "omar")


async def test_a_second_holder_of_one_account_waits_and_another_account_does_not(engine) -> None:
    locks = PostgresAccountLocks(engine)
    async with locks.hold(LENA):
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_enter(locks, LENA), timeout=1.0)
        await asyncio.wait_for(_enter(locks, OMAR), timeout=5.0)
    await asyncio.wait_for(_enter(locks, LENA), timeout=5.0)


async def _enter(locks: PostgresAccountLocks, account: Account) -> None:
    async with locks.hold(account):
        return None
```

(`engine` is the integration suite's per-test fixture.)

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_account_locks.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.infrastructure.db.locks'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/ports/locks.py
from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sro.domain.execution.account import Account


class AccountLocks(Protocol):
    def hold(self, account: Account) -> AbstractAsyncContextManager[None]: ...
```

```python
# backend/src/sro/infrastructure/db/locks.py
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from sro.domain.execution.account import Account

K_LOCK_WAIT_S = 120


class PostgresAccountLocks:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def hold(self, account: Account) -> AsyncIterator[None]:
        async with self._engine.connect() as connection:
            await connection.execute(text(f"SET lock_timeout = '{K_LOCK_WAIT_S}s'"))
            await connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": account.lock_id})
            try:
                yield
            finally:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": account.lock_id}
                )
```

`fakes.py`:

```python
class FakeAccountLocks:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self.taken: list[str] = []

    @asynccontextmanager
    async def hold(self, account: Account) -> AsyncIterator[None]:
        lock = self._locks.setdefault(account.key, asyncio.Lock())
        async with lock:
            self.taken.append(account.key)
            yield
```

Code notes: why a session-level lock on its own connection (released when the process dies), and why 120 s (a measured sign-in takes about 50 s).

- [ ] **Step 4: Run it and see it pass**

Run: the integration command above, then `cd backend && uv run pytest tests/unit/test_container_wiring.py -q -o faulthandler_timeout=120 && uv run lint-imports`
Expected: all pass; 4 contracts kept.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/ports/locks.py backend/src/sro/infrastructure/db/locks.py backend/src/sro/container.py backend/tests/unit/fakes.py backend/tests/integration/test_account_locks.py docs/code-notes
git commit -m "feat(sessions): a per-account advisory lock for session changes

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S4: The Steel pool — containers from `steel_urls`, capacity from QA-0 (§5.1)

Depends on: C0 (QA-0's answer).

`SteelClient.open` (`client.py:49-58`) refuses whenever any session is live ("this deployment has one browser"). That rule becomes per container, with the capacity QA-0 measured.

**Files:**
- Modify: `backend/src/sro/config.py:78-86` (`steel_urls`, `steel_sessions_per_container`, `steel_containers()`)
- Modify: `backend/src/sro/infrastructure/steel/client.py:31-58` (`capacity`, `alive`)
- Create: `backend/src/sro/application/ports/pool.py`
- Create: `backend/src/sro/infrastructure/steel/pool.py`
- Modify: `backend/src/sro/container.py` (field `pool: BrowserPool`, built from `settings.steel_containers()`)
- Modify: `infra/docker-compose.yml:111-139`, `infra/docker-compose.deploy.yml:137-159, 255-259` (`x-steel` anchor; `steel-2`; `SRO_STEEL_URLS`)
- Modify: `backend/tests/unit/fakes.py` (`FakeBrowserPool`)
- Create: `backend/tests/unit/infrastructure/test_the_steel_pool.py`

**Interfaces:**
- Produces:
  - `Settings.steel_urls: tuple[tuple[str, str], ...] = ()` (`[[api_url, cdp_url], …]`, JSON in `SRO_STEEL_URLS`), `Settings.steel_sessions_per_container: int = 1`, `Settings.steel_containers() -> tuple[tuple[str, str], ...]` (falls back to `((steel_base_url, steel_cdp_url),)`).
  - `BrowserPool.open(busy: Mapping[str, int]) -> tuple[str, str]` (container url, Steel session id); `.close(container_url, steel_session_id)`; `.alive(container_url, steel_session_id) -> bool`; `.cdp_url(container_url) -> str`; `PoolFull(Exception)` with `code = "pool_full"`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/infrastructure/test_the_steel_pool.py
from typing import cast

import pytest

from sro.application.ports.pool import PoolFull
from sro.infrastructure.steel.client import SteelClient
from sro.infrastructure.steel.pool import SteelPool


class _Client:
    def __init__(self, name: str) -> None:
        self.name = name
        self.opened = 0

    async def open(self) -> object:
        self.opened += 1
        return type("S", (), {"id": f"{self.name}-{self.opened}"})()


def _pool(**clients: _Client) -> SteelPool:
    urls = {name.replace("_", "-"): client for name, client in clients.items()}
    return SteelPool(cast("dict[str, SteelClient]", {f"http://{url}:3000": c for url, c in urls.items()}), per_container=1)


async def test_a_session_goes_to_the_first_container_with_room() -> None:
    pool = _pool(steel=_Client("one"), steel_2=_Client("two"))

    assert await pool.open({"http://steel:3000": 1}) == ("http://steel-2:3000", "two-1")


async def test_a_full_pool_says_so_rather_than_sharing_a_browser() -> None:
    pool = _pool(steel=_Client("one"))

    with pytest.raises(PoolFull):
        await pool.open({"http://steel:3000": 1})
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/unit/infrastructure/test_the_steel_pool.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.application.ports.pool'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/ports/pool.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class PoolFull(Exception):
    code = "pool_full"


class BrowserPool(Protocol):
    async def open(self, busy: Mapping[str, int]) -> tuple[str, str]: ...

    async def close(self, container_url: str, steel_session_id: str) -> None: ...

    async def alive(self, container_url: str, steel_session_id: str) -> bool: ...

    async def cdp_url(self, container_url: str) -> str: ...
```

```python
# backend/src/sro/infrastructure/steel/pool.py
from __future__ import annotations

from collections.abc import Mapping

from sro.application.ports.pool import PoolFull
from sro.domain.shared.identifiers import BrowserSessionId
from sro.infrastructure.steel.client import SteelClient


class SteelPool:
    def __init__(self, clients: Mapping[str, SteelClient], *, per_container: int) -> None:
        self._clients = dict(clients)
        self._per = per_container

    async def open(self, busy: Mapping[str, int]) -> tuple[str, str]:
        for url, client in self._clients.items():
            if busy.get(url, 0) < self._per:
                session = await client.open()
                return url, str(session.id)
        raise PoolFull(
            f"all {len(self._clients)} Steel container(s) hold {self._per} session(s) each"
        )

    async def close(self, container_url: str, steel_session_id: str) -> None:
        await self._clients[container_url].close(BrowserSessionId(steel_session_id))

    async def alive(self, container_url: str, steel_session_id: str) -> bool:
        return await self._clients[container_url].alive(BrowserSessionId(steel_session_id))

    async def cdp_url(self, container_url: str) -> str:
        return await self._clients[container_url].debugger_url(BrowserSessionId(""))
```

`client.py`: `__init__` gains `capacity: int = 1`; `open` refuses when `len(holding) >= self._capacity`; add `async def alive(self, session_id: BrowserSessionId) -> bool: return (await self._status(session_id)).lower() == "live"`. The refusal message and `_held_by` stop saying "one browser"; they name the capacity.

`config.py`:

```python
    steel_urls: tuple[tuple[str, str], ...] = ()
    steel_sessions_per_container: int = 1

    def steel_containers(self) -> tuple[tuple[str, str], ...]:
        return self.steel_urls or ((self.steel_base_url, self.steel_cdp_url),)
```

`container.py`: `pool=SteelPool({api: SteelClient(api, cdp, capacity=settings.steel_sessions_per_container, public_base_url=settings.steel_public_base_url, session_timeout_seconds=settings.steel_session_timeout_seconds, dimensions=(settings.browser_width, settings.browser_height)) for api, cdp in settings.steel_containers()}, per_container=settings.steel_sessions_per_container)`.

Compose (both files): lift today's `steel` service body into `x-steel: &steel`, keep `steel: *steel` with its `DOMAIN`/`CDP_DOMAIN`, add `steel-2: {<<: *steel, environment: {DOMAIN: …, CDP_DOMAIN: steel-2:9223}}` (local: ports `3011:3000`, `9224:9223`), and set `SRO_STEEL_URLS: '[["http://steel:3000","http://steel:9223"],["http://steel-2:3000","http://steel-2:9223"]]'` on the api and worker services of the deploy file.

`fakes.py` `FakeBrowserPool`: containers `{url: capacity}`, `open` honours `busy`, records `opened`/`closed`, `alive` answers from a `dead: set[str]` of session ids a test kills.

**If QA-0 printed `sessions`:** set `steel_sessions_per_container` to the measured number in both compose files; nothing else changes.
**If QA-0 printed `contexts`:** `SteelPool.open` opens the container's one Steel session when absent and returns `(url, f"{steel_session_id}#{browser_context_id}")`, creating the context with CDP `Target.createBrowserContext {disposeOnDetach: false}`; S5's `SteelDriver` then selects `browser.contexts` by that id instead of `contexts[0]`. The lease and everything above the broker are unchanged (spec §5.1).

Code notes: the capacity rule and QA-0's answer (`docs/code-notes/backend/src/sro/infrastructure/steel/pool.py.md`).

- [ ] **Step 4: Run it and see it pass**

Run: `cd backend && uv run pytest tests/unit/infrastructure tests/unit/test_container_wiring.py tests/integration/test_steel_capture.py -q -o faulthandler_timeout=120`
Expected: pass (the Steel capture suite skips when Steel is not running).

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/config.py backend/src/sro/infrastructure/steel/client.py backend/src/sro/application/ports/pool.py backend/src/sro/infrastructure/steel/pool.py backend/src/sro/container.py infra/docker-compose.yml infra/docker-compose.deploy.yml backend/tests/unit/fakes.py backend/tests/unit/infrastructure/test_the_steel_pool.py docs/code-notes
git commit -m "feat(steel): a pool of containers with measured capacity

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S5: SteelDriver — one CDP connection per session, tabs by target id, saved state (§5.3, §5.5, §6.1 UI)

Depends on: X1 (the page-code file it injects).

`ui_driver.py` opens a new CDP connection for every call (`_AttachedPage.__aenter__`, about 630 ms each) and always drives `pages[0]`. The new driver holds one connection per Steel session, keyed by session id, and addresses pages by CDP target id so a restarted worker finds its tabs.

**Files:**
- Create: `backend/src/sro/application/ports/page.py`
- Create: `backend/src/sro/infrastructure/steel/driver.py`
- Modify: `backend/src/sro/container.py` (field `driver: PageDriver` = `SteelDriver(settings.page_code_path)`)
- Modify: `backend/tests/unit/fakes.py` (`FakePageDriver`)
- Create: `backend/tests/browser/steel_rig.py`
- Create: `backend/tests/browser/test_the_steel_driver.py`

**Interfaces:**
- Produces:
  - `SessionRef(steel_session_id: str, cdp_url: str)`; `PageGone(Exception)` (`code = "page_gone"`).
  - `PageDriver`: `open_tab(session, url) -> str` (target id), `close_tab(session, target_id)`, `goto(session, target_id, url)`, `url_of(session, target_id) -> str`, `storage_state(session) -> str` (JSON), `restore_state(session, state: str)`, `forget(session)`.
  - `steel_rig.py`: `Rig` (a local app behind a local identity-provider chain: `/` → `/idp/authorize?response_type=code&client_id=app&redirect_uri=…&state=…` → form `/idp/login` → `/cb?code=…&state=…` → `/app`; `/api/customer-types` POST 201 and GET, CSRF token from `<meta name="csrf-token">` sent as `X-CSRF-Token`, 401 without the session cookie; `rig.expire()` drops every server session), fixtures `rig` and `cdp_url` (a local Chromium with `--remote-debugging-port`, the shape of `test_a_sign_in_through_a_redirect_chain.py`'s `debugger_url`).

- [ ] **Step 1: Write the failing browser test**

```python
# backend/tests/browser/test_the_steel_driver.py
import pytest

from sro.application.ports.page import SessionRef
from sro.config import get_settings
from sro.infrastructure.steel.driver import SteelDriver
from tests.browser.steel_rig import Rig, cdp_url, cdp_url_2, rig  # noqa: F401

pytestmark = pytest.mark.browser


async def test_a_tab_is_found_again_by_its_target_id_after_a_restart(
    rig: Rig, cdp_url: str
) -> None:
    session = SessionRef("local", cdp_url)
    first = SteelDriver(get_settings().page_code_path)
    target = await first.open_tab(session, rig.url("/public"))
    await first.forget(session)

    again = SteelDriver(get_settings().page_code_path)

    assert (await again.url_of(session, target)).endswith("/public")


async def test_the_page_code_is_in_every_new_document(rig: Rig, cdp_url: str) -> None:
    session = SessionRef("local", cdp_url)
    driver = SteelDriver(get_settings().page_code_path)
    target = await driver.open_tab(session, rig.url("/public"))

    assert await driver.evaluate(session, target, "typeof globalThis.sroPage") == "object"


async def test_saved_state_signs_a_fresh_browser_in(rig: Rig, cdp_url: str, cdp_url_2: str) -> None:
    driver = SteelDriver(get_settings().page_code_path)
    one = SessionRef("one", cdp_url)
    target = await driver.open_tab(one, rig.url("/"))
    await rig.sign_in_in(driver, one, target)
    state = await driver.storage_state(one)

    two = SessionRef("two", cdp_url_2)
    await driver.restore_state(two, state)
    landed = await driver.open_tab(two, rig.url("/app"))

    assert (await driver.url_of(two, landed)).endswith("/app")
```

(`evaluate(session, target_id, expression) -> object` is a test-support method of `SteelDriver`, used by the parity suite too; `cdp_url_2` is a second local Chromium from `steel_rig.py`; `Rig.sign_in_in` fills the rig's form through Playwright directly — the broker's sign-in is S7's.)

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.infrastructure.steel.driver'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/ports/page.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SessionRef:
    steel_session_id: str
    cdp_url: str


class PageGone(Exception):
    code = "page_gone"


class PageDriver(Protocol):
    async def open_tab(self, session: SessionRef, url: str) -> str: ...

    async def close_tab(self, session: SessionRef, target_id: str) -> None: ...

    async def goto(self, session: SessionRef, target_id: str, url: str) -> None: ...

    async def url_of(self, session: SessionRef, target_id: str) -> str: ...

    async def storage_state(self, session: SessionRef) -> str: ...

    async def restore_state(self, session: SessionRef, state: str) -> None: ...

    async def forget(self, session: SessionRef) -> None: ...
```

```python
# backend/src/sro/infrastructure/steel/driver.py
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Frame, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError

from sro.application.ports.page import PageGone, SessionRef

_KEEP_STORAGE = """(() => {
  const saved = %s;
  for (const { name, value } of saved[location.origin] || []) {
    if (localStorage.getItem(name) === null) localStorage.setItem(name, value);
  }
})();"""


class SteelDriver:
    def __init__(self, page_code_path: str) -> None:
        self._page_code = Path(page_code_path)
        self._playwright: Playwright | None = None
        self._browsers: dict[str, Browser] = {}
        self._pages: dict[str, dict[str, Page]] = {}
        self._lock = asyncio.Lock()

    async def _context(self, session: SessionRef) -> BrowserContext:
        async with self._lock:
            browser = self._browsers.get(session.steel_session_id)
            if browser is None or not browser.is_connected():
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                browser = await self._playwright.chromium.connect_over_cdp(session.cdp_url)
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                await context.add_init_script(path=str(self._page_code))
                for page in context.pages:
                    for frame in page.frames:
                        await self._install(frame)
                self._browsers[session.steel_session_id] = browser
                self._pages[session.steel_session_id] = {}
            return browser.contexts[0]

    async def _install(self, frame: Frame) -> None:
        try:
            await frame.evaluate(self._page_code.read_text(encoding="utf-8"))
        except PlaywrightError:
            return None

    async def _target_of(self, page: Page) -> str:
        cdp = await page.context.new_cdp_session(page)
        try:
            info = await cdp.send("Target.getTargetInfo")
        finally:
            await cdp.detach()
        return str(info["targetInfo"]["targetId"])

    async def page(self, session: SessionRef, target_id: str) -> Page:
        context = await self._context(session)
        known = self._pages[session.steel_session_id]
        found = known.get(target_id)
        if found is not None and not found.is_closed():
            return found
        for page in context.pages:
            known[await self._target_of(page)] = page
        if target_id not in known or known[target_id].is_closed():
            raise PageGone(f"tab {target_id} is not open in session {session.steel_session_id}")
        return known[target_id]

    async def open_tab(self, session: SessionRef, url: str) -> str:
        page = await (await self._context(session)).new_page()
        await page.goto(url, wait_until="domcontentloaded")
        target = await self._target_of(page)
        self._pages[session.steel_session_id][target] = page
        return target

    async def close_tab(self, session: SessionRef, target_id: str) -> None:
        await (await self.page(session, target_id)).close()
        self._pages[session.steel_session_id].pop(target_id, None)

    async def goto(self, session: SessionRef, target_id: str, url: str) -> None:
        await (await self.page(session, target_id)).goto(url, wait_until="domcontentloaded")

    async def url_of(self, session: SessionRef, target_id: str) -> str:
        return (await self.page(session, target_id)).url

    async def evaluate(self, session: SessionRef, target_id: str, expression: str) -> object:
        return await (await self.page(session, target_id)).evaluate(expression)

    async def storage_state(self, session: SessionRef) -> str:
        return json.dumps(await (await self._context(session)).storage_state())

    async def restore_state(self, session: SessionRef, state: str) -> None:
        saved = json.loads(state)
        context = await self._context(session)
        await context.add_cookies(saved.get("cookies", []))
        kept = {one["origin"]: one.get("localStorage", []) for one in saved.get("origins", [])}
        if kept:
            await context.add_init_script(script=_KEEP_STORAGE % json.dumps(kept))

    async def forget(self, session: SessionRef) -> None:
        async with self._lock:
            browser = self._browsers.pop(session.steel_session_id, None)
            self._pages.pop(session.steel_session_id, None)
        if browser is None:
            return None
        try:
            await browser.close()
        except PlaywrightError:
            return None
```

`steel_rig.py`: a `ThreadingHTTPServer` like `test_a_sign_in_through_a_redirect_chain.py` `_server`, serving the routes in **Interfaces**; `Rig.url(path)` answers `http://127.0.0.1:<port><path>`, or `http://$SRO_STEEL_SEES_HOST:<port><path>` (default `host.docker.internal`, server bound to `0.0.0.0`) when `Rig(for_steel=True)`; fixtures `cdp_url` and `cdp_url_2` launch Chromium with `--remote-debugging-port` and skip where none is installed. The app page is:

```html
<!doctype html><html><head><meta name="csrf-token" content="{token}"></head><body>
  <form aria-label="Customer Type">
    <label for="ct">Customer Type</label><input id="ct" name="customerType">
    <button id="save" type="button">Save</button>
  </form>
  <script>
    document.getElementById("save").addEventListener("click", async () => {
      const token = document.querySelector("meta[name=csrf-token]").content;
      await fetch("/api/customer-types", {method: "POST", headers: {"X-CSRF-Token": token,
        "content-type": "application/json"}, body: JSON.stringify({name: document.getElementById("ct").value})});
    });
  </script>
</body></html>
```

`fakes.py` `FakePageDriver`: `tabs: dict[str, str]` (target → url, ids `tab-1`, `tab-2`, …), `states: dict[str, str]` per session, `dead: set[str]` of session ids whose calls raise `PageGone`, and the call log `calls: list[tuple[str, ...]]`.

Code notes: one connection per session (the 630 ms per attach measured in the parent spec §2), target ids (worker restart, §5.5), `_KEEP_STORAGE` never overwriting a value the application wrote, and why `_install` skips a frame mid-navigation (the init script covers its next document).

- [ ] **Step 4: Run it and see it pass**

Run: `cd backend && uv run pytest tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120 && uv run lint-imports`
Expected: `3 passed`; 4 contracts kept.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/ports/page.py backend/src/sro/infrastructure/steel/driver.py backend/src/sro/container.py backend/tests/unit/fakes.py backend/tests/browser/steel_rig.py backend/tests/browser/test_the_steel_driver.py docs/code-notes
git commit -m "feat(steel): a page driver with one connection per session and tabs by target id

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S6: A sign-in page is recognised by its structure (§5.6)

Depends on: X1, S5.

`_SIGN_IN_PATHS` and `is_sign_in_page` are gone (audit wave 1). A page is a sign-in page when it shows a credential input (a password input, or an `autocomplete` of `current-password`, `username` or `one-time-code`), or when its tab is inside an OAuth/OIDC round trip: an authorize request carrying `response_type`, `client_id`, `redirect_uri` and `state` not yet answered by a return carrying `code` and `state`.

**Files:**
- Modify: `backend/src/sro/domain/skill/signing_in.py` (`PageSignals`, `an_authorize_request`, `a_code_return`, `a_sign_in_page`, `asks_for_a_code`; add to `__all__`)
- Modify: `new-chrome-extension/src/page/page-code.js` (`sroPage.signals`)
- Modify: `new-chrome-extension/src/page/page-code.test.mjs`
- Modify: `backend/src/sro/application/ports/page.py` (`PageDriver.signals`)
- Modify: `backend/src/sro/infrastructure/steel/driver.py` (main-frame navigation log per page; `signals`)
- Modify: `backend/tests/unit/fakes.py` (`FakePageDriver.signals` answers `PageSignals` set per target by the test)
- Create: `backend/tests/unit/domain/test_a_sign_in_page_by_its_structure.py`
- Modify: `backend/tests/browser/test_the_steel_driver.py`

**Interfaces:**
- Produces: `PageSignals(url: str, visited: tuple[str, ...] = (), password: bool = False, autocomplete: frozenset[str] = frozenset())`; `a_sign_in_page(page: PageSignals) -> bool`; `asks_for_a_code(page: PageSignals) -> bool`; `an_authorize_request(url: str) -> bool`; `a_code_return(url: str) -> bool`; `sroPage.signals() -> {password: boolean, autocomplete: string[]}`; `PageDriver.signals(session, target_id) -> PageSignals` (union over every frame of the tab; `visited` = the tab's main-frame navigations since it was opened).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/domain/test_a_sign_in_page_by_its_structure.py
from sro.domain.skill.signing_in import PageSignals, a_sign_in_page, asks_for_a_code

AUTHORIZE = (
    "https://idp.example/authorize?response_type=code&client_id=wms"
    "&redirect_uri=https%3A%2F%2Fwms.example%2Fcb&state=s1"
)


def test_a_password_form_on_any_host_is_a_sign_in_page() -> None:
    assert a_sign_in_page(PageSignals("https://anything.example/x", password=True))


def test_an_identifier_first_page_is_a_sign_in_page() -> None:
    assert a_sign_in_page(PageSignals("https://idp.example/u", autocomplete=frozenset({"username"})))


def test_a_path_that_looks_like_a_login_is_not_one_by_itself() -> None:
    assert not a_sign_in_page(PageSignals("https://wms.example/oauth2/settings"))


def test_a_pass_through_single_sign_on_is_inside_its_round_trip() -> None:
    hopping = PageSignals("https://idp.example/sso/hop", visited=(AUTHORIZE,))

    assert a_sign_in_page(hopping)


def test_the_round_trip_ends_at_the_code_return() -> None:
    back = PageSignals(
        "https://wms.example/app", visited=(AUTHORIZE, "https://wms.example/cb?code=c&state=s1")
    )

    assert not a_sign_in_page(back)


def test_a_one_time_code_asks_for_a_person() -> None:
    otp = PageSignals("https://idp.example/mfa", autocomplete=frozenset({"one-time-code"}))

    assert a_sign_in_page(otp) and asks_for_a_code(otp)
```

`page-code.test.mjs`:

```js
test("the page says what credential inputs it shows", () => {
  globalThis.document = {
    querySelectorAll: () => [
      fakeInput({ type: "password", autocomplete: "current-password" }),
      fakeInput({ type: "text", autocomplete: "username" }),
      fakeInput({ type: "text", hidden: true, autocomplete: "one-time-code" }),
    ],
  };
  assert.deepEqual(sroPage.signals(), { password: true, autocomplete: ["current-password", "username"] });
});
```

(`fakeInput` returns an element whose `getBoundingClientRect` is empty when `hidden`.) In `test_the_steel_driver.py`: open `rig.url("/")`, which lands on the rig's form; `a_sign_in_page(await driver.signals(session, target))` is `True`, and after `rig.sign_in_in(...)` it is `False`.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_a_sign_in_page_by_its_structure.py -q -o faulthandler_timeout=120` — Expected: FAIL, `ImportError: cannot import name 'PageSignals'`.
Run: `make test-extension` — Expected: FAIL, `sroPage.signals is not a function`.

- [ ] **Step 3: Implement**

`signing_in.py`:

```python
from urllib.parse import parse_qs, urlsplit

_AUTHORIZE = frozenset({"response_type", "client_id", "redirect_uri", "state"})
_RETURN = frozenset({"code", "state"})
_CREDENTIAL = frozenset({"current-password", "username", "one-time-code"})


@dataclass(frozen=True, slots=True)
class PageSignals:
    url: str
    visited: tuple[str, ...] = ()
    password: bool = False
    autocomplete: frozenset[str] = frozenset()


def _asks(url: str) -> frozenset[str]:
    return frozenset(parse_qs(urlsplit(url).query, keep_blank_values=True))


def an_authorize_request(url: str) -> bool:
    return _AUTHORIZE <= _asks(url)


def a_code_return(url: str) -> bool:
    return _RETURN <= _asks(url)


def _in_round_trip(urls: tuple[str, ...]) -> bool:
    opened = max((n for n, url in enumerate(urls) if an_authorize_request(url)), default=-1)
    closed = max((n for n, url in enumerate(urls) if a_code_return(url)), default=-1)
    return opened > closed


def a_sign_in_page(page: PageSignals) -> bool:
    return (
        page.password
        or bool(page.autocomplete & _CREDENTIAL)
        or _in_round_trip((*page.visited, page.url))
    )


def asks_for_a_code(page: PageSignals) -> bool:
    return "one-time-code" in page.autocomplete
```

`page-code.js` (inside the `sroPage` object):

```js
  signals() {
    const shown = [...document.querySelectorAll("input")].filter((el) => {
      const box = el.getBoundingClientRect();
      return box.width > 0 && box.height > 0;
    });
    const autocomplete = [
      ...new Set(
        shown.map((el) => (el.getAttribute("autocomplete") || "").toLowerCase()).filter(Boolean),
      ),
    ];
    return {
      password: shown.some((el) => (el.type || "").toLowerCase() === "password"),
      autocomplete,
    };
  },
```

`driver.py`: `open_tab` and `_context` attach `page.on("framenavigated", …)` recording `frame.url` when `frame == page.main_frame` into `self._visited[target_id]`; `signals` evaluates `globalThis.sroPage.signals()` in every frame of the page (a frame that throws is skipped), ORs `password`, unions `autocomplete`, and returns `PageSignals(page.url, tuple(visited), password, frozenset(autocomplete))`.

Code notes: the two signals and why `username` alone counts (an identifier-first page), in `signing_in.py.md` and `page-code.js.md`.

- [ ] **Step 4: Run them and see them pass**

Run: `make test-extension && cd backend && uv run pytest tests/unit/domain tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120`
Expected: all pass. `grep -nE "oauth2|openid|login-actions|saml" backend/src/sro/domain/skill/signing_in.py` prints nothing.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/domain/skill/signing_in.py new-chrome-extension/src/page backend/src/sro/application/ports/page.py backend/src/sro/infrastructure/steel/driver.py backend/tests docs/code-notes
git commit -m "feat(sessions): recognise a sign-in page by its inputs and its OAuth round trip

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S7: The session broker acquires: attach, else lease, restore, probe, sign in (§5.3, §5.4)

Depends on: S1, S2, S3, S4, S5, S6, X3, X4.

The broker builds on the path QA actually uses (parent spec §6.4): the recorded sign-in job's chain (`sign_in_chain`, audit wave 1 Task 10) replayed with the job's recorded username and the vault password, not the unused connection-based `SignIn`.

**Files:**
- Create: `backend/src/sro/application/runtime/__init__.py` (empty)
- Create: `backend/src/sro/application/runtime/broker.py`
- Modify: `backend/src/sro/application/connection/sign_in.py:238-256` (extract `tagged_logins(uow, ctx) -> tuple[list[Workflow], dict[str, Gesture]]` from `_recorded`; `_recorded` calls it)
- Modify: `backend/src/sro/container.py` (`session_broker()`)
- Create: `backend/tests/unit/application/runtime/__init__.py`, `backend/tests/unit/application/runtime/test_the_broker.py`
- Modify: `backend/tests/unit/fakes.py` (`FakePageDriver`: `restored` log; a `signed` flag per session; `shows_sign_in_until_signed` and `refuses` switches that make `signals` answer a password form until the chain has run (or always); `signals_for_every_tab`; `expire_session()` clears `signed`)
- Modify: `backend/tests/unit/runtime_support.py` (`with_a_recorded_sign_in`, `SigningLane` with `stepped`, `secret_seen`, `sign_ins`)
- Create: `backend/tests/integration/test_runs_on_local_steel.py` (scenario: leases and restore; two tabs on one account)

**Interfaces:**
- Consumes: `Held`, `NeedsAPerson`, `LaneContext`, `StepLane` (X3); `UiLane` (X4); `BrowserSessionRepository` leases (S2); `AccountLocks` (S3); `BrowserPool` (S4); `PageDriver` (S5, S6); `RefusedCredentials`, `fingerprint` (`application/connection/refusals.py`); `recorded_login`, `sign_in_chain`, `a_sign_in_page`, `asks_for_a_code` (`domain/skill/signing_in.py`).
- Produces on `SessionBroker(uow, pool, driver, locks, vault, clock, ui)`:
  - `account_for(ctx, start_url) -> Account` — the recorded login's username for the system the run starts on (`""` where no recorded login lands there).
  - `acquire(ctx, account, start_url, *, holder: str) -> Held` — a ready lease is attached with a new tab; otherwise, under the account lock: expired or orphaned leases are settled and their Steel sessions closed, a new lease is taken (`signing_in`), the saved state restored, the start page probed, the recorded chain signed in if the probe shows a sign-in page, the state saved (if ≤ `K_VAULT_VALUE_BYTES`), and the lease settled `ready`.
  - `reattach(ctx, lease_id, target_id) -> Held` — raises `PageGone` when the session or tab is gone.
  - `release(ctx, held)` — closes the tab; the lease stays for the account's other runs and expires on silence.
  - `beat(ctx, lease_id, *, holder)`.

- [ ] **Step 1: Write the failing unit tests**

```python
# backend/tests/unit/application/runtime/test_the_broker.py
import pytest

from sro.application.context import RequestContext
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import NeedsAPerson
from sro.domain.execution.account import Account, LeaseState
from sro.domain.shared.identifiers import PrincipalId, TenantId
from sro.domain.skill.signing_in import PageSignals
from tests.unit.fakes import (
    FakeAccountLocks, FakeBrowserPool, FakeClock, FakeCredentialVault, FakePageDriver,
    FakeUnitOfWork,
)
from tests.unit.runtime_support import SigningLane, with_a_recorded_sign_in

CTX = RequestContext(TenantId("greyorange"), PrincipalId("op"))
APP = "https://wms.example/app"
LENA = Account.of("greyorange", "https://wms.example", "lena")


def _broker(
    uow: FakeUnitOfWork, driver: FakePageDriver, vault: FakeCredentialVault, lane: SigningLane | None = None
) -> SessionBroker:
    return SessionBroker(uow, FakeBrowserPool({"http://steel:3000": 1}), driver,
                         FakeAccountLocks(), vault, FakeClock(), ui=lane or SigningLane(driver))


async def test_a_restored_state_that_holds_signs_nobody_in() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await vault.store(LENA.vault_key("state"), '{"cookies": []}')
    lane = SigningLane(driver)

    held = await _broker(uow, driver, vault, lane).acquire(CTX, LENA, APP, holder="run_1")

    assert held.lease.state is LeaseState.READY
    assert lane.stepped == []
    assert driver.restored == ['{"cookies": []}']


async def test_a_sign_in_page_is_signed_through_with_the_vault_password() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await with_a_recorded_sign_in(uow, lands_on=APP, username="lena")
    await vault.store(LENA.vault_key("password"), "not-a-real-secret")
    driver.shows_sign_in_until_signed = True
    lane = SigningLane(driver)

    await _broker(uow, driver, vault, lane).acquire(CTX, LENA, APP, holder="run_1")

    assert lane.secret_seen == "not-a-real-secret"
    assert await vault.get(LENA.vault_key("state")) is not None


async def test_two_runs_on_one_account_share_one_lease_as_two_tabs() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    broker = _broker(uow, driver, vault)

    one = await broker.acquire(CTX, LENA, APP, holder="run_1")
    two = await broker.acquire(CTX, LENA, APP, holder="run_2")

    assert one.lease.id == two.lease.id
    assert one.target_id != two.target_id


async def test_a_form_that_comes_back_latches_the_password_and_asks() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await with_a_recorded_sign_in(uow, lands_on=APP, username="lena")
    await vault.store(LENA.vault_key("password"), "wrong")
    driver.shows_sign_in_until_signed = True
    driver.refuses = True

    with pytest.raises(NeedsAPerson) as asked:
        await _broker(uow, driver, vault).acquire(CTX, LENA, APP, holder="run_1")

    assert asked.value.kind == "password"
    assert await vault.get(LENA.vault_key("password") + "#refused") is not None


async def test_a_one_time_code_asks_a_person() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await with_a_recorded_sign_in(uow, lands_on=APP, username="lena")
    await vault.store(LENA.vault_key("password"), "not-a-real-secret")
    driver.signals_for_every_tab = PageSignals(APP, autocomplete=frozenset({"one-time-code"}))

    with pytest.raises(NeedsAPerson):
        await _broker(uow, driver, vault).acquire(CTX, LENA, APP, holder="run_1")
```

In `backend/tests/unit/runtime_support.py` (created by X4): `with_a_recorded_sign_in(uow, *, lands_on, username)` saves a tagged sign-in `Workflow` and its gestures (username typed, password typed with `secret=True`, a submit click whose `page_events` land on `lands_on`'s origin) into the fake repositories, in the shape `tests/unit/domain/test_the_way_back_in.py` `_azure()` builds; `SigningLane(driver)` is a `StepLane` that records `stepped`, keeps `ctx.secret` in `secret_seen`, and on the chain's last step flips `driver.signed` (unless `driver.refuses`).

The integration scenario in `test_runs_on_local_steel.py` (skips unless local Steel answers `/v1/health` and Postgres is reachable) runs the same acquire against `Rig(for_steel=True)` twice for one account and asserts one lease, two target ids, and that a third acquire after `driver.forget` + a fresh `SteelDriver` restores the saved state with no form submitted (`rig.logins == 1`).

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_broker.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.application.runtime.broker'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/broker.py
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import replace

from sro.application.connection.refusals import RefusedCredentials, fingerprint
from sro.application.connection.sign_in import tagged_logins
from sro.application.context import RequestContext
from sro.application.ports.browser import BrowserUnavailable
from sro.application.ports.locks import AccountLocks
from sro.application.ports.page import PageDriver, PageGone, SessionRef
from sro.application.ports.pool import BrowserPool
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.ports.vault import CredentialVault
from sro.application.runtime.step import Held, LaneContext, NeedsAPerson, StepLane
from sro.domain.execution.account import (
    K_LEASE_TTL, K_VAULT_VALUE_BYTES, Account, Lease, LeaseState, new_lease_id,
)
from sro.domain.skill.signing_in import (
    a_sign_in_page, asks_for_a_code, recorded_login, sign_in_chain,
)

logger = logging.getLogger(__name__)


class SessionBroker:
    def __init__(
        self,
        uow: UnitOfWork,
        pool: BrowserPool,
        driver: PageDriver,
        locks: AccountLocks,
        vault: CredentialVault,
        clock: Clock,
        *,
        ui: StepLane,
    ) -> None:
        self._uow, self._pool, self._driver = uow, pool, driver
        self._locks, self._vault, self._clock, self._ui = locks, vault, clock, ui

    async def account_for(self, ctx: RequestContext, start_url: str) -> Account:
        tagged, seen = await tagged_logins(self._uow, ctx)
        login = recorded_login(start_url, tagged, seen)
        username = (login.username or "") if login is not None else ""
        return Account.of(ctx.tenant_id.value, start_url, username)

    async def acquire(
        self, ctx: RequestContext, account: Account, start_url: str, *, holder: str
    ) -> Held:
        lease = await self._current(ctx, account)
        if lease is None or lease.state is not LeaseState.READY:
            async with self._locks.hold(account):
                lease = await self._ready(ctx, account, start_url, holder=holder)
        return await self._tab(lease, start_url)

    async def reattach(self, ctx: RequestContext, lease_id: str, target_id: str) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
        if lease is None or not lease.live(self._clock.now()):
            raise PageGone(f"lease {lease_id} is no longer live")
        held = Held(lease, target_id, await self._session(lease))
        await self._driver.url_of(held.session, target_id)
        return held

    async def release(self, ctx: RequestContext, held: Held) -> None:
        try:
            await self._driver.close_tab(held.session, held.target_id)
        except PageGone:
            return None

    async def beat(self, ctx: RequestContext, lease_id: str, *, holder: str) -> None:
        async with self._uow as uow:
            await uow.browser_sessions.beat(
                ctx.tenant_id, lease_id, now=self._clock.now(), holder=holder
            )
            await uow.commit()

    async def _current(self, ctx: RequestContext, account: Account) -> Lease | None:
        async with self._uow as uow:
            lease = await uow.browser_sessions.current_lease(ctx.tenant_id, account)
        return lease if lease is not None and lease.live(self._clock.now()) else None

    async def _ready(
        self, ctx: RequestContext, account: Account, start_url: str, *, holder: str
    ) -> Lease:
        now = self._clock.now()
        async with self._uow as uow:
            old = await uow.browser_sessions.current_lease(ctx.tenant_id, account)
            if old is not None and old.state is LeaseState.READY and old.live(now):
                return old
            if old is not None:
                await uow.browser_sessions.settle(ctx.tenant_id, old.id, state=LeaseState.EXPIRED)
            busy = Counter(await uow.browser_sessions.busy_containers(now=now))
            await uow.commit()
        if old is not None:
            await self._close(old)
        container, steel_id = await self._pool.open(busy)
        fresh = Lease(new_lease_id(), account, container, steel_id, holder, now,
                      now + K_LEASE_TTL, LeaseState.SIGNING_IN)
        async with self._uow as uow:
            lease = await uow.browser_sessions.lease(ctx.tenant_id, fresh)
            await uow.commit()
        session = await self._session(lease)
        state = await self._vault.get(account.vault_key("state"))
        if state:
            await self._driver.restore_state(session, state)
        target = await self._driver.open_tab(session, start_url)
        held = Held(lease, target, session)
        if a_sign_in_page(await self._driver.signals(session, target)):
            await self._sign_in(ctx, held, start_url)
        await self._save_state(held)
        await self._driver.close_tab(session, target)
        async with self._uow as uow:
            await uow.browser_sessions.settle(ctx.tenant_id, lease.id, state=LeaseState.READY)
            await uow.commit()
        return replace(lease, state=LeaseState.READY)

    async def _sign_in(self, ctx: RequestContext, held: Held, start_url: str) -> None:
        account = held.lease.account
        tagged, seen = await tagged_logins(self._uow, ctx)
        login = recorded_login(start_url, tagged, seen)
        job = next((one for one in tagged if login and one.id == login.job_id), None)
        if job is None:
            raise NeedsAPerson(
                f"{account.origin} asks to sign in and no recorded sign-in lands there; "
                "sign in once with the extension watching",
                kind="step",
            )
        key = account.vault_key("password")
        password = await self._vault.get(key)
        refused = RefusedCredentials(self._vault)
        if not password or await refused.standing(key, password) is not None:
            raise NeedsAPerson(
                f"no usable password is stored for {account.username} at {account.origin}",
                kind="password",
            )
        if asks_for_a_code(await self._driver.signals(held.session, held.target_id)):
            raise NeedsAPerson(f"{account.origin} asks for a one-time code", kind="step")
        lane = LaneContext.for_sign_in(ctx, job, seen, held, secret=password)
        for step in sign_in_chain(job, seen):
            result = await self._ui.execute(step, {}, lane)
            if result.verdict == "failed":
                raise NeedsAPerson(
                    f"signing in to {account.origin} stopped at '{step.says}': {result.reason}",
                    kind="step",
                )
        after = await self._driver.signals(held.session, held.target_id)
        if asks_for_a_code(after):
            raise NeedsAPerson(f"{account.origin} asks for a one-time code", kind="step")
        if a_sign_in_page(after):
            await refused.refuse(
                key,
                at=self._clock.now(),
                reason="the sign-in form came back after the password was submitted",
                fingerprint=fingerprint(key, password),
            )
            raise NeedsAPerson(
                f"the password for {account.username} at {account.origin} was refused; "
                "store a new one",
                kind="password",
            )
        await self._driver.goto(held.session, held.target_id, start_url)

    async def _save_state(self, held: Held) -> None:
        state = await self._driver.storage_state(held.session)
        if len(state.encode()) > K_VAULT_VALUE_BYTES:
            logger.warning(
                "%s: the signed-in state is %d bytes, over the vault's limit; not saved",
                held.lease.account.key, len(state.encode()),
            )
            return
        await self._vault.store(held.lease.account.vault_key("state"), state)

    async def _tab(self, lease: Lease, start_url: str) -> Held:
        session = await self._session(lease)
        return Held(lease, await self._driver.open_tab(session, start_url), session)

    async def _session(self, lease: Lease) -> SessionRef:
        return SessionRef(lease.steel_session_id, await self._pool.cdp_url(lease.container_url))

    async def _close(self, lease: Lease) -> None:
        await self._driver.forget(await self._session(lease))
        try:
            await self._pool.close(lease.container_url, lease.steel_session_id)
        except BrowserUnavailable:
            return None
```

(`LaneContext.for_sign_in` is the X3 constructor that fills an empty ledger, no learned locators, `live=True` and a fresh `asyncio.Event`.)

`sign_in.py`: move the body of `_recorded` (lines 241-255) into `async def tagged_logins(uow: UnitOfWork, ctx: RequestContext) -> tuple[list[Workflow], dict[str, Gesture]]`, returning `(tagged, seen)`; `_recorded` becomes `tagged, seen = await tagged_logins(uow, ctx); return recorded_login(connection.base_url, tagged, seen)`.

`container.py`: `def session_broker(self) -> SessionBroker: return SessionBroker(self.unit_of_work(), self.pool, self.driver, self.locks, self.vault, self.clock, ui=self.ui_lane())`.

Code notes (`broker.py.md`): the acquire order (§5.3), why a stale lease's Steel session is closed before opening another (capacity 1 per container), why the tab used for the probe is closed (each run opens its own), and why the state is not split when too large (a fresh sign-in is the fallback, spec §12).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/application/runtime tests/unit/application -q -o faulthandler_timeout=120 && uv run lint-imports`
Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_runs_on_local_steel.py -q -o faulthandler_timeout=120` (with `make up` running)
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime backend/src/sro/application/connection/sign_in.py backend/src/sro/container.py backend/tests/unit/application/runtime backend/tests/unit/runtime_support.py backend/tests/integration/test_runs_on_local_steel.py docs/code-notes
git commit -m "feat(sessions): the broker leases, restores, probes and signs in from the vault

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S8: Expiry and recovery — re-sign-in under the account lock; container crash (§5.5)

Depends on: S7.

**Files:**
- Modify: `backend/src/sro/application/runtime/broker.py` (`reauth`, `recover`)
- Modify: `backend/tests/unit/application/runtime/test_the_broker.py`
- Modify: `backend/tests/integration/test_runs_on_local_steel.py` (scenarios: container crash; expiry mid-step then re-sign-in)

**Interfaces:**
- Produces:
  - `SessionBroker.reauth(ctx, held, start_url) -> None` — under the account lock: reload the run's tab at `start_url`; if it still shows a sign-in page, sign in through the recorded chain and save the state. A run that waited on the lock finds the page signed in and continues.
  - `SessionBroker.recover(ctx, lease_id: str, start_url: str, *, holder: str) -> Held` — the session is gone (`PageGone` from `reattach`): the lease is settled `broken`, its Steel session closed, and `acquire` opens a new one (restoring the saved state).
- Consumed by: X4/X5 (`session_expired`), D2 (`PageGone` from `reattach`).

- [ ] **Step 1: Write the failing tests**

```python
async def test_runs_waiting_on_the_lock_find_the_session_already_signed_back_in() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await with_a_recorded_sign_in(uow, lands_on=APP, username="lena")
    await vault.store(LENA.vault_key("password"), "not-a-real-secret")
    lane = SigningLane(driver)
    broker = _broker(uow, driver, vault, lane)
    one = await broker.acquire(CTX, LENA, APP, holder="run_1")
    two = await broker.acquire(CTX, LENA, APP, holder="run_2")
    driver.expire_session()

    await asyncio.gather(broker.reauth(CTX, one, APP), broker.reauth(CTX, two, APP))

    assert lane.sign_ins == 1


async def test_a_crashed_container_is_replaced_and_its_state_restored() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    await vault.store(LENA.vault_key("state"), '{"cookies": []}')
    broker = _broker(uow, driver, vault)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")
    driver.dead.add(held.session.steel_session_id)

    again = await broker.recover(CTX, held.lease.id, APP, holder="run_1")

    assert again.lease.id != held.lease.id
    assert driver.restored == ['{"cookies": []}', '{"cookies": []}']
    async with uow as unit:
        old = await unit.browser_sessions.get_lease(CTX.tenant_id, held.lease.id)
    assert old is not None and old.state is LeaseState.BROKEN
```

Integration scenarios (local Steel + `Rig(for_steel=True)`): *container crash* — acquire, `docker restart` the test's Steel container through the Docker SDK (`docker.from_env().containers.get(...)`, the way `testcontainers` is already installed), `recover`, and `rig.logins` does not grow; *expiry mid-step* — acquire, `rig.expire()`, `reauth`, `rig.logins` grows by exactly one for two concurrent reauths.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_broker.py -q -o faulthandler_timeout=120`
Expected: FAIL, `AttributeError: 'SessionBroker' object has no attribute 'reauth'`.

- [ ] **Step 3: Implement**

```python
    async def reauth(self, ctx: RequestContext, held: Held, start_url: str) -> None:
        async with self._locks.hold(held.lease.account):
            await self._driver.goto(held.session, held.target_id, start_url)
            if a_sign_in_page(await self._driver.signals(held.session, held.target_id)):
                await self._sign_in(ctx, held, start_url)
                await self._save_state(held)

    async def recover(
        self, ctx: RequestContext, lease_id: str, start_url: str, *, holder: str
    ) -> Held:
        async with self._uow as uow:
            lease = await uow.browser_sessions.get_lease(ctx.tenant_id, lease_id)
        if lease is None:
            raise PageGone(f"lease {lease_id} is not known")
        async with self._locks.hold(lease.account):
            async with self._uow as uow:
                await uow.browser_sessions.settle(ctx.tenant_id, lease.id, state=LeaseState.BROKEN)
                await uow.commit()
            await self._close(lease)
        return await self.acquire(ctx, lease.account, start_url, holder=holder)
```

Code notes: why every waiter reloads before deciding (the first one through signed everyone in), and why a broken lease is not reused.

- [ ] **Step 4: Run them and see them pass**

Run: the unit command above, then the local-Steel integration command from S7.
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/broker.py backend/tests docs/code-notes
git commit -m "feat(sessions): re-sign-in once under the account lock; replace a crashed session

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S9: The sweeper releases only expired leases; the grace timer and the in-memory list go (§5.2, §10)

Depends on: S7.

`application/connection/release_strays.py` decides what is held from `self._pursuits.sessions()` (one process's memory) and a flat `GRACE = timedelta(minutes=15)` (lines 12, 44, 65). With leases, a browser is held exactly while its lease is live.

**Files:**
- Modify: `backend/src/sro/application/connection/release_strays.py:1-73`
- Modify: `backend/src/sro/container.py:507-514` (`release_stray_browsers` passes `self.pool`, `self.driver`; no `pursuits`)
- Modify: the unit suite that covers `ReleaseStrayBrowsers` (`grep -rln ReleaseStrayBrowsers backend/tests`); `backend/tests/unit/runtime_support.py` (`lease_for(uow, clock, holder=…)`, `_sweeper(uow, pool, driver, clock)`)
- Modify: `docs/code-notes/backend/src/sro/application/connection/release_strays.py.md` (remove the `GRACE` notes)

**Interfaces:**
- Produces: `ReleaseStrayBrowsers(uow, browser, watch, pool, driver, clock).execute() -> tuple[str, ...]`: (1) every lease from `expired(now=…)` has its state saved when its session still answers, its Steel session closed through the pool, and is settled `expired`; (2) a capture browser (a Steel session with no live lease and no capturing recording) is closed as before, with no grace window.

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_lease_that_stopped_beating_is_released_and_its_browser_closed() -> None:
    uow, pool, driver, clock = FakeUnitOfWork(), FakeBrowserPool({"http://steel:3000": 1}), FakePageDriver(), FakeClock()
    lease = await lease_for(uow, clock, holder="run_1")
    clock.advance(int(K_LEASE_TTL.total_seconds()) + 1)

    released = await _sweeper(uow, pool, driver, clock).execute()

    assert lease.steel_session_id in released
    assert pool.closed == [("http://steel:3000", lease.steel_session_id)]


async def test_a_lease_that_keeps_beating_survives_any_number_of_sweeps() -> None:
    uow, pool, driver, clock = FakeUnitOfWork(), FakeBrowserPool({"http://steel:3000": 1}), FakePageDriver(), FakeClock()
    lease = await lease_for(uow, clock, holder="run_1")
    for _ in range(20):
        clock.advance(60)
        async with uow:
            await uow.browser_sessions.beat(TenantId(lease.account.tenant), lease.id, now=clock.now())
        assert await _sweeper(uow, pool, driver, clock).execute() == ()
```

(`lease_for` in `tests/unit/runtime_support.py` inserts a `ready` lease; `_sweeper` builds `ReleaseStrayBrowsers` with the fakes. Twenty minutes of beating outlives the old 15-minute grace.)

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application -q -o faulthandler_timeout=120 -k "lease_that"`
Expected: FAIL, `TypeError: ReleaseStrayBrowsers.__init__() got an unexpected keyword argument` / wrong positional.

- [ ] **Step 3: Implement**

```python
class ReleaseStrayBrowsers:
    def __init__(
        self,
        uow: UnitOfWork,
        browser: BrowserProvider,
        watch: WatchBrowsers,
        pool: BrowserPool,
        driver: PageDriver,
        clock: Clock,
    ) -> None:
        self._uow, self._browser, self._watch = uow, browser, watch
        self._pool, self._driver, self._clock = pool, driver, clock

    async def execute(self) -> tuple[str, ...]:
        expired = await self._expired_leases()
        open_now = await self._watch.all_in_deployment()
        async with self._uow as uow:
            capturing = await uow.recordings.list_capturing()
            leased = await uow.browser_sessions.leased_sessions()
        in_use = {str(one.browser_session_id) for one in capturing if one.browser_session_id}
        strays: list[str] = []
        for browser in open_now:
            if browser.session_id in in_use or browser.session_id in leased:
                continue
            if browser.session_id in expired:
                continue
            try:
                await self._browser.close(BrowserSessionId(browser.session_id))
            except BrowserUnavailable:
                continue
            strays.append(browser.session_id)
        async with self._uow as uow:
            claimed = [str(held) for held, _ in await uow.browser_sessions.all_held()]
        live = {browser.session_id for browser in open_now}
        await self._forget([*strays, *(one for one in claimed if one not in live)])
        return (*expired, *strays)

    async def _expired_leases(self) -> tuple[str, ...]:
        async with self._uow as uow:
            gone = await uow.browser_sessions.expired(now=self._clock.now())
        closed: list[str] = []
        for lease in gone:
            try:
                await self._pool.close(lease.container_url, lease.steel_session_id)
            except BrowserUnavailable:
                pass
            async with self._uow as uow:
                await uow.browser_sessions.settle(
                    TenantId(lease.account.tenant), lease.id, state=LeaseState.EXPIRED
                )
                await uow.commit()
            closed.append(lease.steel_session_id)
        return tuple(closed)
```

`leased_sessions()` (S2) is every session a live lease still holds, which the capture sweep must never close. Delete `GRACE`, the `Pursuits` import, and `_in_use`'s `self._pursuits.sessions()`. `Pursuits.sessions()` loses its last reader here; it is deleted in R2 with `Pursuits`.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && grep -n "GRACE" src/sro/application/connection/release_strays.py`
Expected: pass; the grep prints nothing.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/connection/release_strays.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "fix(sessions): release only expired leases; no grace timer, no in-memory list

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## S10: Session headers for the API lane — cookies from the context, CSRF from the page's own requests (§5.7)

Depends on: S7.

`client.py:210-241` `session_headers` keeps a header only from URLs containing `"/data/"` and sleeps a fixed 6 s. The driver keeps a per-session log of the page's own requests (CDP `Network.requestWillBeSent` from the session's pages) and answers as soon as one carrying an AUTH or CSRF header (`classify_header`) for the origin has been seen.

**Files:**
- Modify: `backend/src/sro/application/ports/page.py` (`headers_for`, `cookies_for`)
- Modify: `backend/src/sro/infrastructure/steel/driver.py` (request log, `headers_for`, `cookies_for`)
- Modify: `backend/src/sro/application/runtime/broker.py` (`headers`)
- Modify: `backend/tests/unit/fakes.py`
- Modify: `backend/tests/browser/test_the_steel_driver.py`, `backend/tests/unit/application/runtime/test_the_broker.py`

**Interfaces:**
- Produces: `PageDriver.headers_for(session, origin: str, deadline_s: float) -> dict[str, str]` (lower-cased names, first value seen, AUTH/CSRF only; empty at the deadline); `PageDriver.cookies_for(session, origin) -> str` (a `Cookie` header value); `SessionBroker.headers(ctx, held, origin, *, fresh: bool = False) -> dict[str, str]` = the cookie header plus `headers_for`; `fresh=True` reloads the run's tab first so the page sends a new token. `K_HEADERS_WAIT_S = 20.0`.

- [ ] **Step 1: Write the failing tests**

Browser test: open `rig.url("/app")` signed in; `click #save` through `driver.evaluate`; `headers_for(session, rig.origin, 5.0)` returns `{"x-csrf-token": <the page's token>}` in well under 5 s (assert elapsed < 2 s), and a page that never sends one returns `{}` at the deadline. Unit test:

```python
async def test_the_api_lane_is_handed_the_session_s_cookie_and_token() -> None:
    uow, driver, vault = FakeUnitOfWork(), FakePageDriver(), FakeCredentialVault()
    driver.cookie = "sid=abc"
    driver.headers = {"x-csrf-token": "t1"}
    broker = _broker(uow, driver, vault)
    held = await broker.acquire(CTX, LENA, APP, holder="run_1")

    said = await broker.headers(CTX, held, "https://wms.example")

    assert said == {"cookie": "sid=abc", "x-csrf-token": "t1"}
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_broker.py tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120 -k "token or header"`
Expected: FAIL, `AttributeError: 'SessionBroker' object has no attribute 'headers'`.

- [ ] **Step 3: Implement**

`driver.py`: in `_context`, after connecting, register on the context `context.on("request", self._saw)` where `_saw(request)` appends `(origin_of(request.url), dict(await request.all_headers()))` to `self._requests[session_id]` (a bounded `collections.deque(maxlen=200)`) and sets an `asyncio.Event` per session. Then:

```python
    async def headers_for(self, session: SessionRef, origin: str, deadline_s: float) -> dict[str, str]:
        await self._context(session)
        ends = asyncio.get_running_loop().time() + deadline_s
        while True:
            for seen_origin, headers in reversed(self._requests[session.steel_session_id]):
                if seen_origin != origin:
                    continue
                kept = {
                    name.lower(): value
                    for name, value in headers.items()
                    if classify_header(name) in (Sensitivity.AUTH, Sensitivity.CSRF)
                    and name.lower() != "cookie"
                }
                if kept:
                    return kept
            left = ends - asyncio.get_running_loop().time()
            if left <= 0:
                return {}
            seen = self._seen[session.steel_session_id]
            seen.clear()
            try:
                await asyncio.wait_for(seen.wait(), timeout=left)
            except TimeoutError:
                return {}

    async def cookies_for(self, session: SessionRef, origin: str) -> str:
        cookies = await (await self._context(session)).cookies(origin)
        return "; ".join(f"{one['name']}={one['value']}" for one in cookies)
```

`broker.py`:

```python
K_HEADERS_WAIT_S = 20.0

    async def headers(
        self, ctx: RequestContext, held: Held, origin: str, *, fresh: bool = False
    ) -> dict[str, str]:
        if fresh:
            await self._driver.goto(
                held.session, held.target_id, await self._driver.url_of(held.session, held.target_id)
            )
        said = await self._driver.headers_for(held.session, origin, K_HEADERS_WAIT_S)
        cookie = await self._driver.cookies_for(held.session, origin)
        return {"cookie": cookie, **said} if cookie else said
```

Code notes: no path filter and no sleep; the page's own requests, classified by name and role; the header values never logged (Global Constraint 10).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/application/runtime tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/ports/page.py backend/src/sro/infrastructure/steel/driver.py backend/src/sro/application/runtime/broker.py backend/tests docs/code-notes
git commit -m "feat(sessions): cookies and CSRF for the API lane from the page's own requests

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

# Stream X — executors, lanes and page code (spec §3, §6)

## X1: One page-code file, loaded by the extension and by the backend image (§6.4)

`new-chrome-extension/src/background/in-page.js` is an ES module whose functions are handed to `executeScript` as `func` (each must be self-contained), and the backend image is built from `backend/` alone (`Makefile:114`, `backend/Dockerfile`), so Steel cannot load it. The code moves, verbatim, into one classic script exposing `globalThis.sroPage`; the extension injects it with `executeScript({files})`, Steel with `add_init_script(path=…)`, and the image receives it through a BuildKit named context.

**Files:**
- Create: `new-chrome-extension/src/page/page-code.js`
- Create: `new-chrome-extension/src/page/page-code.test.mjs` (the cases of `in-page.test.mjs`, `injected.test.mjs`, `viewport.test.mjs` and `call.test.mjs` that exercise the moved functions, calling `globalThis.sroPage.<name>`)
- Delete: `new-chrome-extension/src/background/in-page.js`, `new-chrome-extension/src/background/in-page.test.mjs`, `new-chrome-extension/src/background/injected.test.mjs`
- Modify: `new-chrome-extension/src/background/commands.js:15-24, 345-415, 530, 800-852, 873-895, 1043-1100, 1447, 1490, 1528` (every injection of a moved function)
- Modify: `new-chrome-extension/src/background/viewport.test.mjs:52`, `new-chrome-extension/src/background/call.test.mjs:19`
- Modify: `backend/Dockerfile` (runtime stage: `COPY --from=page page-code.js /app/page-code/page-code.js`; `ENV SRO_PAGE_CODE_PATH=/app/page-code/page-code.js`)
- Modify: `Makefile:108-119` (`images`: `docker build --build-context page=new-chrome-extension/src/page …`)
- Modify: `backend/src/sro/config.py` (`page_code_path`)
- Modify: `backend/src/sro/interface/http/v1/routers/health.py` (`Health.page_code`)
- Modify: `backend/scripts/smoke.py` (compare the deployed hash with the repository file's)
- Modify: `.github/workflows/ci.yml` (job "Image — the page code is the repository's")
- Test: `backend/tests/unit/interface/test_health_names_its_page_code.py`
- Run: `make types`

**Interfaces:**
- Produces: `globalThis.sroPage` with `perform(payload)`, `performAt(payload)`, `screenSize()`, `viewport()`, `csrfToken()`, `requestedWith()`, `send(payload)` — the bodies of `performInPage`, `performAtInPage`, `screenSizeInPage`, `viewportInPage`, `csrfTokenInPage`, `requestedWithInPage`, `sendInPage`, unchanged. `Settings.page_code_path: str` (default: the repository file, `Path(__file__).resolve().parents[3] / "new-chrome-extension/src/page/page-code.js"`). `GET /health` answers `page_code: <sha256 hex>`.
- The extension's behaviour is unchanged.

- [ ] **Step 1: Write the failing tests**

```js
// new-chrome-extension/src/page/page-code.test.mjs  (head; the moved cases follow)
// Run with `node src/page/page-code.test.mjs`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const source = readFileSync(fileURLToPath(new URL("./page-code.js", import.meta.url)), "utf8");

test("the file is a classic script: no import, no export", () => {
  assert.doesNotMatch(source, /^\s*(import|export)\s/m);
});

test("evaluated alone, it defines every function the worker calls", () => {
  const realm = {};
  new Function("globalThis", source)(realm);
  for (const name of ["perform", "performAt", "screenSize", "viewport", "csrfToken", "requestedWith", "send"]) {
    assert.equal(typeof realm.sroPage[name], "function", name);
  }
});
```

```python
# backend/tests/unit/interface/test_health_names_its_page_code.py
import hashlib
from pathlib import Path

import httpx
from httpx import ASGITransport

from sro.config import get_settings
from sro.interface.http.app import create_app


async def test_health_says_which_page_code_this_process_loaded() -> None:
    expected = hashlib.sha256(Path(get_settings().page_code_path).read_bytes()).hexdigest()
    async with httpx.AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://t") as http:
        said = (await http.get("/health")).json()

    assert said["page_code"] == expected
```

- [ ] **Step 2: Run them and see them fail**

Run: `make test-extension` — Expected: FAIL, `ENOENT … src/page/page-code.js`.
Run: `cd backend && uv run pytest tests/unit/interface/test_health_names_its_page_code.py -q -o faulthandler_timeout=120` — Expected: FAIL, `AttributeError: 'Settings' object has no attribute 'page_code_path'`.

- [ ] **Step 3: Implement**

`page-code.js`:

```js
(() => {
  const sroPage = {
    perform(payload) { /* moved: in-page.js performInPage body (lines 26-487) */ },
    performAt(payload) { /* moved: performAtInPage body (lines 493-669) */ },
    screenSize() { /* moved: screenSizeInPage body (lines 686-693) */ },
    viewport() { /* moved: viewportInPage body (lines 695-849) */ },
    csrfToken() { /* moved: csrfTokenInPage body (lines 857-859) */ },
    requestedWith() { /* moved: requestedWithInPage body (lines 877-881) */ },
    async send(payload) { /* moved: sendInPage body (lines 890-1020) */ },
  };
  globalThis.sroPage = sroPage;
})();
```

(Move each body unchanged; move their inline comments to `docs/code-notes/new-chrome-extension/src/page/page-code.js.md`, keyed by method.)

`commands.js`: remove the `./in-page.js` import and add

```js
const PAGE_CODE = "src/page/page-code.js";

async function sroCall(target, name, args, world = "MAIN") {
  await chrome.scripting.executeScript({ target, world, files: [PAGE_CODE] });
  return chrome.scripting.executeScript({
    target,
    world,
    func: (called, given) => globalThis.sroPage[called](...given),
    args: [name, args],
  });
}
```

Every `chrome.scripting.executeScript({…, func: <moved>, args})` becomes `sroCall(target, "<name>", args, world)`, and `inPage(tabId, <moved>, args, world)` / `inFrame(tabId, frameId, <moved>, args, world)` take the name instead of the function (`performInPage`→`"perform"`, `performAtInPage`→`"performAt"`, `screenSizeInPage`→`"screenSize"`, `viewportInPage`→`"viewport"`, `csrfTokenInPage`→`"csrfToken"`, `requestedWithInPage`→`"requestedWith"`, `sendInPage`→`"send"`, the latter keeping `world: "ISOLATED"`). Find them all with `grep -nE "InPage\b|InPage," new-chrome-extension/src/background/commands.js` until it prints nothing.

`config.py`: `page_code_path: str = str(Path(__file__).resolve().parents[3] / "new-chrome-extension" / "src" / "page" / "page-code.js")`.

`health.py`:

```python
@functools.cache
def _page_code() -> str:
    return hashlib.sha256(Path(get_settings().page_code_path).read_bytes()).hexdigest()


class Health(BaseModel):
    status: str
    revision: str
    page_code: str = ""
    """The sha256 of the page code this process injects into Steel. CI and
    `make smoke` compare it with the repository's file."""
    checks: dict[str, bool]
```

and `health()` returns `page_code=_page_code()` (`ready()` too).

`Dockerfile` runtime stage, after the scripts copy: `COPY --from=page --chown=sro:sro page-code.js /app/page-code/page-code.js` and `SRO_PAGE_CODE_PATH=/app/page-code/page-code.js` in the `ENV`. `Makefile` `images`: `docker build --build-context page=new-chrome-extension/src/page -t ai-sro-backend:$$rev --build-arg REVISION=$$rev backend/`. `smoke.py`: fetch `/health`, compare `page_code` with the sha256 of the file baked at `SRO_PAGE_CODE_PATH`, fail loudly on a difference. CI:

```yaml
  page-code-image:
    name: Image — the page code is the repository's
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build --build-context page=new-chrome-extension/src/page -t sro-ci backend/
      - run: |
          want=$(sha256sum new-chrome-extension/src/page/page-code.js | cut -d' ' -f1)
          got=$(docker run --rm sro-ci sha256sum /app/page-code/page-code.js | cut -d' ' -f1)
          test "$want" = "$got"
```

- [ ] **Step 4: Run them and see them pass**

Run: `make test-extension && make lint-extension`
Run: `cd backend && uv run pytest tests/unit/interface -q -o faulthandler_timeout=120 && uv run pytest tests/browser/test_the_extension_in_a_real_chrome.py -q -o faulthandler_timeout=120 && cd .. && make types && cd backend && uv run pytest tests/contract -q`
Expected: all pass. Update the comment in `state.js:102` to name `page-code.js`; `grep -rn "in-page" new-chrome-extension/src` then prints nothing.

- [ ] **Step 5: Commit**

```bash
git add new-chrome-extension/src/page new-chrome-extension/src/background backend/Dockerfile Makefile backend/src/sro/config.py backend/src/sro/interface/http/v1/routers/health.py backend/scripts/smoke.py .github/workflows/ci.yml backend/tests/unit/interface/test_health_names_its_page_code.py frontend/openapi.json frontend/src/lib/api/generated.ts docs/code-notes
git commit -m "refactor(page): one page-code file for the extension and the Steel runner

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X2: The strategy order, bounds, snapshot repair — and the parity suite (§6.4, §8.2)

Depends on: X1, E1–E5 (the evidence it reads).

The page code resolves a control from the recorded evidence in one order: a locator learned by a verified run (§6.3), then (1) component chain, (2) component query, (3) `within` plus role and name, (4) test id, (5) attributes (`name`, `autocomplete`, input type, stable ids), (6) text, (7) xpath, (8) `css_path`. Several matches are disambiguated by the recorded bounds. When every strategy misses, snapshot repair scores live controls against the evidence and acts only above a threshold.

**Files:**
- Modify: `new-chrome-extension/src/page/page-code.js` (module-scope helpers; `resolve`, `act`, `holds`, `hitTest`; `perform`'s acting half extracted to `actOn(el, payload)` and reused)
- Modify: `new-chrome-extension/src/page/page-code.test.mjs`
- Create: `backend/tests/browser/test_page_code_parity.py`
- Modify: `docs/code-notes/new-chrome-extension/src/page/page-code.js.md` (the threshold and weights, with their reasoning)

**Interfaces:**
- Payload (built by X4's `ui_payload`): `{action, value, target: {tag, role, name, text, test_id, css_path, xpath, bounds, attributes, landmarks: [{role, name}], component: {query, item_id, chain}}, learned: {strategy, query} | null, frame_path, expect?: {value, visible, enabled}}`.
- Produces:
  - `sroPage.resolve(payload) -> {found, strategy, candidates, score, xpath}` (probe, no act; `strategy` ∈ `learned`, `component_chain`, `component`, `within_role_name`, `test_id`, `attributes`, `text`, `xpath`, `css_path`, `repair`).
  - `sroPage.act(payload) -> {ok, matched_by, candidates, short, state: {value, visible, enabled}, error?: {kind, detail}}` (`kind` `control_not_found` when nothing and no repair matched).
  - `sroPage.holds(payload) -> boolean` — the resolved control's state equals `payload.expect` (for condition waits).
  - `sroPage.hitTest(x, y) -> {strategy, query} | null` — the strongest locator that finds exactly the element at a point (for sight → UI teaching).
  - Constants: `REPAIR_THRESHOLD = 6`, `NEAR_PX = 50`, `GENERATED_ID = /^(ext-|gen)|\d{3,}/`.

- [ ] **Step 1: Write the failing tests**

`page-code.test.mjs` — a minimal fake DOM (the style of the moved `in-page` cases) proving: (a) a component chain wins over a css path when both match different elements; (b) two elements matching role and name are told apart by the recorded bounds; (c) a stale `css_path` with a surviving `name` attribute resolves by `attributes`; (d) a control renamed and moved still resolves by `repair` when its role, attributes and landmarks match (score ≥ 6); (e) a lone weak resemblance (score < 6) resolves nothing; (f) the recorder's `roleOf` and page code's role function agree on the table in `src/content/roles.test.mjs` (lift the recorder's with the `lift` helper from `src/content/evidence.test.mjs`).

```js
test("the recorded bounds pick between two controls of one name", () => {
  const left = button("Save", { x: 10, y: 10, width: 60, height: 20 });
  const right = button("Save", { x: 400, y: 10, width: 60, height: 20 });
  page([left, right]);

  const found = sroPage.resolve({
    target: { role: "button", name: "Save", bounds: { x: 395, y: 12, width: 60, height: 20 } },
  });

  assert.equal(found.strategy, "within_role_name");
  assert.equal(found.candidates, 2);
  assert.equal(found.xpath, xpathOf(right));
});
```

`test_page_code_parity.py` — served pages: an ExtJS-style grid (a fake `window.Ext` with `ComponentQuery`/`getCmp`, as `tests/browser/conftest.py` `PAGE` builds one), a page whose control sits in an iframe, a page whose ids changed since recording, and a page with two matching controls. For each case, resolve the same payload (a) in real Chrome through the extension's injection — the `browser` fixture, then from the service worker: `chrome.scripting.executeScript({target: {tabId, frameIds: [frameId]}, world: "MAIN", files: ["src/page/page-code.js"]})` followed by `executeScript({…, func: (p) => globalThis.sroPage.resolve(p), args: [payload]})` — and (b) in plain Playwright Chromium with `context.add_init_script(path=get_settings().page_code_path)` and `frame.evaluate("p => globalThis.sroPage.resolve(p)", payload)`; assert equal `(strategy, candidates, xpath)`.

- [ ] **Step 2: Run them and see them fail**

Run: `make test-extension` — Expected: FAIL, `sroPage.resolve is not a function`.
Run: `cd backend && uv run pytest tests/browser/test_page_code_parity.py -q -o faulthandler_timeout=120` — Expected: FAIL for the same reason in both realms.

- [ ] **Step 3: Implement**

In `page-code.js`, above `const sroPage = {`:

```js
  const REPAIR_THRESHOLD = 6;
  const NEAR_PX = 50;
  const GENERATED_ID = /^(ext-|gen)|\d{3,}/;
  const CANDIDATES = "input, select, textarea, button, a, [role], [tabindex]";
  const LANDMARKS = ["region", "dialog", "alertdialog", "grid", "treegrid", "form"];

  const shown = (el) => {
    const box = el.getBoundingClientRect();
    if (box.width < 1 || box.height < 1) return false;
    const style = getComputedStyle(el);
    return style.visibility !== "hidden" && style.display !== "none";
  };
  const qsa = (selector, root = document) => {
    try { return [...root.querySelectorAll(selector)]; } catch { return []; }
  };
  const roleOf = (el) => { /* copied from recorder.js roleOf (lines 188-209); test (f) keeps the two equal */ };
  const nameOf = (el) => {
    const aria = el.getAttribute("aria-label");
    if (aria) return aria.trim();
    const by = el.getAttribute("aria-labelledby");
    if (by) return by.split(/\s+/).map((id) => document.getElementById(id)?.innerText || "").join(" ").trim();
    if (el.labels && el.labels.length) return (el.labels[0].innerText || "").trim();
    return (el.getAttribute("placeholder") || el.getAttribute("title") || el.innerText || "").trim().slice(0, 200);
  };
  const landmarkRole = (el) => {
    const written = el.getAttribute("role");
    if (written) return LANDMARKS.includes(written) ? written : null;
    const tag = el.tagName.toLowerCase();
    return tag === "form" ? "form" : tag === "dialog" ? "dialog" : tag === "section" ? "region" : null;
  };
  const landmarksOf = (el) => {
    const found = [];
    for (let node = el.parentElement; node; node = node.parentElement) {
      const role = landmarkRole(node);
      const name = role ? node.getAttribute("aria-label") || null : null;
      if (role && name) found.unshift({ role, name });
    }
    return found;
  };
  const ext = (query) =>
    (window.Ext?.ComponentQuery?.query(query) || [])
      .filter((c) => c.isVisible?.(true))
      .map((c) => (c.inputEl || c.btnEl || c.el)?.dom)
      .filter(Boolean);
  const chainOf = (el) => { /* copied from recorder.js component() (lines 211-250), returning its `chain` */ };
  const ownText = (text) =>
    qsa("button, a, label, td, th, li, span, div, option").filter(
      (el) => [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim() === text,
    );
  const scopes = (landmarks) => {
    const inner = (landmarks || []).at(-1);
    if (!inner) return [document];
    return qsa("*").filter((el) => landmarkRole(el) === inner.role && nameOf(el) === inner.name);
  };
  const attributeSelector = (t) => {
    const a = t.attributes || {};
    const parts = [];
    if (a.name) parts.push(`[name="${CSS.escape(a.name)}"]`);
    if (a.autocomplete) parts.push(`[autocomplete="${CSS.escape(a.autocomplete)}"]`);
    if (a.id && !GENERATED_ID.test(a.id)) parts.push(`#${CSS.escape(a.id)}`);
    if (!parts.length) return null;
    if (a.type) parts.push(`[type="${CSS.escape(a.type)}"]`);
    return `${t.tag || ""}${parts.join("")}`;
  };
  const byXpath = (xpath) => {
    try {
      const got = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      return Array.from({ length: got.snapshotLength }, (_, i) => got.snapshotItem(i));
    } catch { return []; }
  };
  const byLearned = ({ strategy, query }) => {
    if (strategy === "component") return ext(query.startsWith("#") || query.includes(" ") ? query : `#${query}`);
    if (strategy === "role_and_name") {
      const [role, name] = query.split("|");
      return qsa("*").filter((el) => roleOf(el) === role && nameOf(el) === name);
    }
    if (strategy === "test_id") return qsa(`[data-testid="${CSS.escape(query)}"]`);
    if (strategy === "text") return ownText(query);
    if (strategy === "xpath") return byXpath(query);
    return qsa(query);
  };
  const STRATEGIES = [
    ["learned", (t, p) => (p.learned ? byLearned(p.learned) : [])],
    ["component_chain", (t) => (t.component?.chain?.length > 1 ? ext(t.component.chain.join(" ")) : [])],
    ["component", (t) => (t.component?.query ? ext(t.component.query) : t.component?.item_id ? ext(`#${t.component.item_id}`) : [])],
    ["within_role_name", (t) => (t.role && t.name
      ? scopes(t.landmarks).flatMap((scope) => qsa("*", scope).filter((el) => roleOf(el) === t.role && nameOf(el) === t.name))
      : [])],
    ["test_id", (t) => (t.test_id
      ? qsa(["data-testid", "data-test-id", "data-test"].map((n) => `[${n}="${CSS.escape(t.test_id)}"]`).join(","))
      : [])],
    ["attributes", (t) => { const selector = attributeSelector(t); return selector ? qsa(selector) : []; }],
    ["text", (t) => (t.text ? ownText(t.text) : [])],
    ["xpath", (t) => (t.xpath ? byXpath(t.xpath) : [])],
    ["css_path", (t) => (t.css_path ? qsa(t.css_path) : [])],
  ];
  const centre = (b) => ({ x: b.x + b.width / 2, y: b.y + b.height / 2 });
  const distance = (el, c) => {
    const here = centre(el.getBoundingClientRect());
    return Math.hypot(here.x - c.x, here.y - c.y);
  };
  const nearest = (found, bounds) => {
    if (!bounds || bounds.width === undefined) return found[0];
    const c = centre(bounds);
    return found.slice().sort((a, b) => distance(a, c) - distance(b, c))[0];
  };
  const score = (el, t) => {
    let total = 0;
    if (t.role && roleOf(el) === t.role) total += 3;
    const name = nameOf(el);
    if (t.name && name === t.name) total += 3;
    else if (t.name && name && name.includes(t.name)) total += 1;
    for (const key of ["name", "autocomplete", "type", "placeholder"]) {
      if (t.attributes?.[key] && el.getAttribute(key) === t.attributes[key]) total += 1;
    }
    const chain = t.component?.chain || [];
    if (chain.length && chainOf(el).join(" ") === chain.join(" ")) total += 2;
    const marks = t.landmarks || [];
    if (marks.length && JSON.stringify(landmarksOf(el)) === JSON.stringify(marks)) total += 2;
    if (t.bounds?.width !== undefined && distance(el, centre(t.bounds)) <= NEAR_PX) total += 1;
    return total;
  };
  const repair = (t) => {
    const ranked = qsa(CANDIDATES).filter(shown).map((el) => [score(el, t), el]).sort((a, b) => b[0] - a[0]);
    const [best, next] = ranked;
    if (!best || best[0] < REPAIR_THRESHOLD || (next && next[0] === best[0])) return null;
    return { el: best[1], score: best[0] };
  };
  const find = (payload) => {
    const t = payload.target || {};
    for (const [strategy, run] of STRATEGIES) {
      const found = run(t, payload).filter(shown);
      if (found.length) return { el: nearest(found, t.bounds), strategy, candidates: found.length, score: null };
    }
    const fixed = repair(t);
    return fixed
      ? { el: fixed.el, strategy: "repair", candidates: 1, score: fixed.score }
      : { el: null, strategy: null, candidates: 0, score: null };
  };
  const stateOf = (el) => {
    const secret = (el.type || "").toLowerCase() === "password";
    return {
      value: secret || el.value === undefined || el.value === null ? null : String(el.value),
      visible: shown(el),
      enabled: !(el.disabled === true || el.getAttribute("aria-disabled") === "true"),
    };
  };
  const xpathOf = (el) => { /* copied from recorder.js xpath (lines 122-134) */ };
  const actOn = (el, payload) => { /* moved out of perform unchanged: its triggerOf, partOf, landed, type and act helpers; answers {ok, short} */ };
```

and in `sroPage`:

```js
    resolve(payload) {
      const f = find(payload);
      return { found: Boolean(f.el), strategy: f.strategy, candidates: f.candidates, score: f.score, xpath: f.el ? xpathOf(f.el) : null };
    },
    act(payload) {
      const f = find(payload);
      if (!f.el) return { ok: false, candidates: 0, error: { kind: "control_not_found", detail: "no strategy and no repair matched" } };
      const done = actOn(f.el, payload);
      return { ...done, matched_by: f.strategy, candidates: f.candidates, state: stateOf(f.el) };
    },
    holds(payload) {
      const f = find(payload);
      if (!f.el) return false;
      const seen = stateOf(f.el);
      const want = payload.expect || {};
      return ["value", "visible", "enabled"].every((key) => want[key] === undefined || want[key] === null || seen[key] === want[key]);
    },
    hitTest(x, y) {
      let el = document.elementFromPoint(x, y);
      let doc = document;
      while (el && el.tagName === "IFRAME" && el.contentDocument) {
        const box = el.getBoundingClientRect();
        doc = el.contentDocument;
        el = doc.elementFromPoint(x - box.left, y - box.top);
      }
      if (!el) return null;
      const only = (found) => found.length === 1 && found[0] === el;
      const item = window.Ext?.getCmp?.(el.id)?.itemId;
      if (item && only(ext(`#${item}`))) return { strategy: "component", query: `#${item}` };
      const role = roleOf(el), name = nameOf(el);
      if (role && name && only(qsa("*", doc).filter((one) => roleOf(one) === role && nameOf(one) === name))) {
        return { strategy: "role_and_name", query: `${role}|${name}` };
      }
      const testId = el.getAttribute("data-testid");
      if (testId) return { strategy: "test_id", query: testId };
      return { strategy: "xpath", query: xpathOf(el) };
    },
```

`hitTest` and `byLearned` speak the same strategy names (`component`, `role_and_name`, `test_id`, `text`, `xpath`, and a CSS selector otherwise). `perform` keeps its locator-list resolution for the extension until R2 deletes it, and now calls `actOn`.

Code notes: each constant and weight, why learned comes first (a locator a verified run proved), why repair refuses a tie, why `GENERATED_ID` is a shape and not a list.

- [ ] **Step 4: Run them and see them pass**

Run: `make test-extension && make lint-extension && cd backend && uv run pytest tests/browser/test_page_code_parity.py tests/browser/test_the_extension_in_a_real_chrome.py -q -o faulthandler_timeout=120`
Expected: all pass; both realms choose the same element in every case.

- [ ] **Step 5: Commit**

```bash
git add new-chrome-extension/src/page backend/tests/browser/test_page_code_parity.py docs/code-notes/new-chrome-extension
git commit -m "feat(page): one strategy order, bounds, snapshot repair, and the parity suite

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X3: The ladder, verdicts and the lane contract (§3, §6.1, §6.2)

Depends on: S1, S5 (`Lease`, `SessionRef` in `Held`).

**Files:**
- Create: `backend/src/sro/domain/execution/lanes.py`
- Create: `backend/src/sro/application/runtime/step.py`
- Create: `backend/tests/unit/domain/test_the_ladder.py`

**Interfaces:**
- Produces (domain, `lanes.py`):
  - `Lane` (`tool`, `api`, `ui`, `sight`); `Verdict = Literal["done", "read", "failed", "unknown"]`; `K_SIGHT_ACTIONS = 6`.
  - `SeenCall(method: str, url: str, status: int | None, body: str | None = None)`.
  - `StepResult(verdict, lane, reason="", read={}, calls=(), learned={}, fingerprint="", expired=False)`.
  - `Broken(step: int, lane: Lane, fingerprint: str)`; `cites_key(step: Step) -> str`; `fingerprint_of(lane: Lane, kind: str, evidence: str = "") -> str`.
  - `lanes_for(order: int, *, tool: bool, api: bool, browser: bool, broken: Collection[Broken]) -> tuple[Lane, ...]`.
  - `write_confirmed(*, recorded: Call | None, wanted: Collection[int], calls: Collection[SeenCall]) -> Verdict | None` — the page's own call matching the recorded one (method and `path_shape`): `failed` on ≥ 400, `done` on an expected (or any 2xx when none was recorded) status, `None` when not seen.
  - `after_matches(expected: AfterState | None, seen: AfterState | None, *, value: str | None) -> bool`.
- Produces (application, `step.py`): `Held(lease: Lease, target_id: str, session: SessionRef)`; `NeedsAPerson(question: str, *, kind: Literal["password", "value", "step"] = "step")` (a `DomainError`, `code = "needs_a_person"`); `Stopped` (`code = "stopped"`); `LaneContext` (frozen: `tenant_id, principal_id, run_id, workflow, by_id, learned: Mapping[int, LearnedStep], ledger: tuple[VerifiedWrite, ...], held: Held | None, live: bool = True, stop: asyncio.Event, secret: str | None = None, thread: str = "", about_to_write: Callable[[], Awaitable[None]]`; `.ctx -> RequestContext`; `.check_stop()`; `LaneContext.for_sign_in(ctx, job, by_id, held, *, secret)`); `StepLane` protocol: `lane: Lane`, `async execute(step, values, ctx) -> StepResult`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/domain/test_the_ladder.py
from sro.domain.execution.lanes import (
    Broken, Lane, SeenCall, after_matches, fingerprint_of, lanes_for, write_confirmed,
)
from sro.domain.observation.gesture import AfterState, Call


def test_a_browser_step_with_a_proven_call_starts_on_the_api_lane() -> None:
    assert lanes_for(2, tool=False, api=True, browser=True, broken=()) == (Lane.API, Lane.UI, Lane.SIGHT)


def test_a_mail_step_is_a_tool_call_and_never_a_tab() -> None:
    assert lanes_for(0, tool=True, api=False, browser=False, broken=()) == (Lane.TOOL,)


def test_a_step_starts_on_the_first_lane_still_trusted() -> None:
    broken = (Broken(2, Lane.API, "f1"), Broken(3, Lane.UI, "f2"))
    assert lanes_for(2, tool=False, api=True, browser=True, broken=broken) == (Lane.UI, Lane.SIGHT)


def test_the_page_s_own_call_confirms_a_write() -> None:
    recorded = Call(method="POST", url="https://wms.example/api/customer-types")
    seen = [SeenCall("POST", "https://wms.example/api/customer-types", 201)]
    rejected = [SeenCall("POST", "https://wms.example/api/customer-types", 409)]

    assert write_confirmed(recorded=recorded, wanted={201}, calls=seen) == "done"
    assert write_confirmed(recorded=recorded, wanted={201}, calls=rejected) == "failed"
    assert write_confirmed(recorded=recorded, wanted={201}, calls=[]) is None


def test_the_after_state_is_checked_against_this_run_s_value() -> None:
    recorded = AfterState(value="GT1", visible=True, enabled=True)

    assert after_matches(recorded, AfterState("GT2", True, True), value="GT2")
    assert not after_matches(recorded, AfterState("GT1", True, True), value="GT2")
    assert not after_matches(None, AfterState("GT2", True, True), value="GT2")


def test_a_fingerprint_is_stable_and_names_its_lane() -> None:
    assert fingerprint_of(Lane.UI, "control_not_found", "css") == fingerprint_of(Lane.UI, "control_not_found", "css")
    assert fingerprint_of(Lane.UI, "x") != fingerprint_of(Lane.API, "x")
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_the_ladder.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.domain.execution.lanes'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/domain/execution/lanes.py
from __future__ import annotations

import hashlib
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from sro.domain.observation.gesture import AfterState, Call
from sro.domain.observation.trim import path_shape
from sro.domain.skill.workflow import Step

K_SIGHT_ACTIONS = 6


class Lane(StrEnum):
    TOOL = "tool"
    API = "api"
    UI = "ui"
    SIGHT = "sight"


Verdict = Literal["done", "read", "failed", "unknown"]


@dataclass(frozen=True, slots=True)
class SeenCall:
    method: str
    url: str
    status: int | None
    body: str | None = None


@dataclass(frozen=True, slots=True)
class StepResult:
    verdict: Verdict
    lane: Lane
    reason: str = ""
    read: Mapping[str, str] = field(default_factory=dict)
    calls: tuple[SeenCall, ...] = ()
    learned: Mapping[str, str] = field(default_factory=dict)
    fingerprint: str = ""
    expired: bool = False


@dataclass(frozen=True, slots=True)
class Broken:
    step: int
    lane: Lane
    fingerprint: str


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def cites_key(step: Step) -> str:
    return _digest("\n".join(step.cites))


def fingerprint_of(lane: Lane, kind: str, evidence: str = "") -> str:
    return _digest(f"{lane}|{kind}|{evidence}")


def lanes_for(
    order: int, *, tool: bool, api: bool, browser: bool, broken: Collection[Broken]
) -> tuple[Lane, ...]:
    ladder = (
        (Lane.TOOL,)
        if tool
        else ((Lane.API,) if api else ()) + ((Lane.UI, Lane.SIGHT) if browser else ())
    )
    dead = {one.lane for one in broken if one.step == order}
    return tuple(lane for lane in ladder if lane not in dead)


def write_confirmed(
    *, recorded: Call | None, wanted: Collection[int], calls: Collection[SeenCall]
) -> Verdict | None:
    if recorded is None:
        return None
    method, shape = recorded.method.upper(), path_shape(recorded.url)
    for call in reversed(tuple(calls)):
        if call.status is None or call.method.upper() != method or path_shape(call.url) != shape:
            continue
        if call.status >= 400:
            return "failed"
        if call.status in wanted or (not wanted and 200 <= call.status < 300):
            return "done"
    return None


def after_matches(
    expected: AfterState | None, seen: AfterState | None, *, value: str | None
) -> bool:
    if expected is None or seen is None:
        return False
    want = value if value is not None else expected.value
    return (
        (expected.visible is None or seen.visible == expected.visible)
        and (expected.enabled is None or seen.enabled == expected.enabled)
        and (want is None or seen.value == want)
    )
```

`step.py` as in **Interfaces**, with `about_to_write` defaulting to an `async def _nothing() -> None` and `check_stop` raising `Stopped("stopped by the operator")` when `stop.is_set()`.

Code notes: the ladder rule (§3), why a fingerprint carries its evidence (a new doing is a new entry), `K_SIGHT_ACTIONS`.

- [ ] **Step 4: Run it and see it pass**

Run: `cd backend && uv run pytest tests/unit/domain/test_the_ladder.py -q -o faulthandler_timeout=120 && uv run lint-imports`
Expected: `6 passed`; 4 contracts kept.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/domain/execution/lanes.py backend/src/sro/application/runtime/step.py backend/tests/unit/domain/test_the_ladder.py docs/code-notes
git commit -m "feat(runtime): the lane ladder, verdicts and the lane contract

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X4: The UI lane — page code in the recorded frame, condition waits, verification (§6.1 UI, §6.2)

Depends on: X2, X3, S5, S6.

`ui_driver.py` resolves with its own Python rules and sleeps `wait_for_timeout(1200)` after every action (lines 80, 140). The UI lane uses the shared page code in the run's tab, enters the recorded frame (E3), and waits on conditions only.

**Files:**
- Create: `backend/src/sro/application/runtime/ui_lane.py`
- Modify: `backend/src/sro/application/ports/page.py` (`PageAnswer`; `act`, `mark`, `calls_since`, `wait_for_call`, `wait_for`)
- Modify: `backend/src/sro/infrastructure/steel/driver.py` (frame choice; response log; the five methods)
- Modify: `backend/tests/unit/fakes.py` (`FakePageDriver` scripted answers and calls)
- Create: `backend/tests/unit/application/runtime/test_the_ui_lane.py`
- Create: `backend/tests/unit/runtime_support.py` (shared by the runtime's unit tests: `scripted_driver(**answers)` — a `FakePageDriver` configured by keyword: `answer`, `calls`, `holds`, `sign_in`, `url`, `hit`; it records `acted`, `waited_for`, `pointed`; `lane_context(by_id, **fields)`; `save_step(status=…)`, `type_step(after=…)`)
- Modify: `backend/tests/browser/test_the_steel_driver.py`
- Modify: `backend/src/sro/container.py` (`ui_lane()`)

**Interfaces:**
- Consumes: `primary_gesture`, `recorded_call`, `writes` (`domain/execution/evidence.py`); `expected_statuses` (`belts.py`); `value_for` (`planning.py`); `needs_a_secret` (`secrets.py`); `made_by`, `names_in` (`records.py`); `write_confirmed`, `after_matches`, `fingerprint_of` (X3); `a_sign_in_page` (S6).
- Produces:
  - `PageAnswer(ok: bool, matched_by: str | None = None, candidates: int = 0, detail: str = "", error_kind: str | None = None, state: AfterState | None = None)`.
  - `PageDriver.act(session, target_id, payload) -> PageAnswer`; `.mark(session, target_id) -> int`; `.calls_since(session, target_id, mark) -> tuple[SeenCall, ...]`; `.wait_for_call(session, target_id, *, method: str, shape: str, since: int, deadline_s: float) -> bool`; `.wait_for(session, target_id, payload, deadline_s) -> bool` (Playwright `wait_for_function` on `sroPage.holds`).
  - `ui_payload(step, gesture, value, learned) -> dict[str, object]`; `UiLane(driver, *, wait_s: float = K_UI_WAIT_S)` with `K_UI_WAIT_S = 15.0`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/application/runtime/test_the_ui_lane.py
from sro.application.ports.page import PageAnswer
from sro.application.runtime.ui_lane import UiLane
from sro.domain.execution.lanes import SeenCall
from sro.domain.observation.gesture import AfterState
from tests.unit.runtime_support import lane_context, save_step, type_step

async def test_a_write_the_page_confirms_is_done_with_no_model_and_no_sleep() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"),
                             calls=[SeenCall("POST", "https://wms.example/api/customer-types", 201, '{"id": "ct-9"}')])
    step, by_id = save_step(status=201)
    written: list[int] = []

    async def wrote() -> None:
        written.append(step.order)

    ctx = lane_context(by_id, about_to_write=wrote)

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, ctx)

    assert (result.verdict, result.lane.value) == ("done", "ui")
    assert result.read == {"id": "ct-9"}
    assert written == [step.order]


async def test_a_write_nothing_confirms_is_unknown_never_done() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="css_path"), calls=[])
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "unknown"


async def test_a_typed_value_is_confirmed_by_the_state_it_left() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="attributes"), holds=True)
    step, by_id = type_step(after=AfterState(value="GT1", visible=True, enabled=True))

    result = await UiLane(driver).execute(step, {"Customer Type": "GT2"}, lane_context(by_id))

    assert result.verdict == "done"
    assert driver.waited_for[-1]["expect"] == {"value": "GT2", "visible": True, "enabled": True}


async def test_a_missing_control_on_a_sign_in_page_is_an_expired_session() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"), sign_in=True)
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.expired and result.verdict == "failed"


async def test_a_missing_control_is_fingerprinted_for_the_known_broken_list() -> None:
    driver = scripted_driver(answer=PageAnswer(ok=False, error_kind="control_not_found"))
    step, by_id = save_step(status=201)

    result = await UiLane(driver).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and result.fingerprint
```

(`scripted_driver` is a `FakePageDriver` configured by keyword; `save_step`/`type_step`/`lane_context` build a `Step`, its cited `Gesture`s and a `LaneContext` in `tests/unit/runtime_support.py`.) Browser test: against `rig.url("/app")` (signed in), `act` types into the Customer Type input found by `attributes` inside the `form[aria-label="Customer Type"]` landmark, clicks Save, `wait_for_call(method="POST", shape="/api/customer-types")` returns `True`, `calls_since(mark)` holds the 201; one `connect_over_cdp` for all of it (assert through a counter on the driver); and `grep -n "wait_for_timeout\|asyncio.sleep" backend/src/sro/infrastructure/steel/driver.py backend/src/sro/application/runtime/ui_lane.py` prints nothing.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_ui_lane.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.application.runtime.ui_lane'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/ui_lane.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from sro.application.ports.page import PageDriver
from sro.application.runtime.step import Held, LaneContext
from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.evidence import READ_METHODS, primary_gesture, recorded_call, writes
from sro.domain.execution.lanes import (
    Lane, StepResult, after_matches, fingerprint_of, write_confirmed,
)
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.planning import value_for
from sro.domain.execution.records import made_by, names_in
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.observation.gesture import AfterState, Gesture
from sro.domain.observation.trim import path_shape
from sro.domain.skill.signing_in import a_sign_in_page
from sro.domain.skill.workflow import Step

K_UI_WAIT_S = 15.0


def ui_payload(
    gesture: Gesture, value: str | None, learned: LearnedStep | None
) -> dict[str, object]:
    target = gesture.action.target
    return {
        "action": gesture.action.kind,
        "value": value,
        "target": {} if target is None else asdict(target),
        "learned": None if learned is None or not learned.usable
        else {"strategy": learned.strategy, "query": learned.query},
        "frame_path": None if gesture.action.frame_path is None
        else [asdict(hop) for hop in gesture.action.frame_path],
    }


class UiLane:
    lane = Lane.UI

    def __init__(self, driver: PageDriver, *, wait_s: float = K_UI_WAIT_S) -> None:
        self._driver = driver
        self._wait_s = wait_s

    async def execute(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> StepResult:
        held = ctx.held
        given = {name for name, value in values.items() if value.strip()}
        primary = primary_gesture(step, ctx.by_id, given)
        if held is None or primary is None or primary.action.target is None:
            return StepResult("failed", Lane.UI, "no recorded control to act on",
                              fingerprint=fingerprint_of(Lane.UI, "no_evidence"))
        value = ctx.secret if needs_a_secret(primary) else value_for(step, primary, values, None)
        payload = ui_payload(primary, value, ctx.learned.get(step.order))
        writing = writes(step, ctx.by_id)
        recorded = recorded_call(step, ctx.by_id)
        ctx.check_stop()
        if writing:
            await ctx.about_to_write()
        mark = await self._driver.mark(held.session, held.target_id)
        answer = await self._driver.act(held.session, held.target_id, payload)
        if not answer.ok:
            expired = a_sign_in_page(await self._driver.signals(held.session, held.target_id))
            return StepResult(
                "failed", Lane.UI, answer.detail or str(answer.error_kind), expired=expired,
                fingerprint=fingerprint_of(Lane.UI, str(answer.error_kind), str(payload["target"])),
            )
        if recorded is not None:
            await self._driver.wait_for_call(
                held.session, held.target_id, method=recorded.method.upper(),
                shape=path_shape(recorded.url), since=mark, deadline_s=self._wait_s,
            )
        calls = await self._driver.calls_since(held.session, held.target_id, mark)
        after = primary.action.after
        if writing:
            verdict = write_confirmed(
                recorded=recorded, wanted=expected_statuses(step, ctx.by_id), calls=calls
            )
            if verdict is None and after is not None:
                verdict = "done" if await self._holds(held, payload, after, value) else None
            if verdict == "failed":
                return StepResult("failed", Lane.UI, "the system rejected the write", calls=calls,
                                  fingerprint=fingerprint_of(Lane.UI, "rejected", str(recorded)))
            made = next((made_by({"status": one.status, "body": one.body}) for one in calls
                         if one.status == 201), {})
            return StepResult(verdict or "unknown", Lane.UI, read=made, calls=calls)
        if recorded is not None and recorded.method.upper() in READ_METHODS:
            got = next((one for one in reversed(calls)
                        if one.status is not None and 200 <= one.status < 300), None)
            if got is not None:
                return StepResult("read", Lane.UI, read=names_in(got.body), calls=calls)
        if after is not None and not await self._holds(held, payload, after, value):
            return StepResult("failed", Lane.UI, "the control did not end up as recorded",
                              fingerprint=fingerprint_of(Lane.UI, "after_state", str(after)))
        return StepResult("done", Lane.UI, calls=calls)

    async def _holds(
        self, held: Held, payload: dict[str, object], after: AfterState, value: str | None
    ) -> bool:
        expect = {"value": value if value is not None else after.value,
                  "visible": after.visible, "enabled": after.enabled}
        return await self._driver.wait_for(
            held.session, held.target_id, {**payload, "expect": expect}, self._wait_s
        )
```

`driver.py`:
- `_frame(page, payload)`: `frame_path is None` → probe every frame with `sroPage.resolve(payload)` and take the one that finds it (the extension's `frameHolding` rule), else the main frame; otherwise walk `frame_path` from `page.main_frame`: at each hop take the only child whose `path_shape(url)` equals the hop's, else the child at `hop.index`, else fall back to the probe.
- `act`: `answer = await frame.evaluate("p => globalThis.sroPage.act(p)", payload)` → `PageAnswer(ok, matched_by, candidates, detail, error_kind, AfterState(**state) if state else None)`.
- A response log per page: `context.on("response", …)` appends `SeenCall(method, url, status, body)` (body read for a 201 only, first 4096 characters) to `self._calls[target_id]` and sets that target's event; `mark` returns the log's length; `calls_since` slices from it; `wait_for_call` waits on the event until a call with that method and `path_shape` appears after `since`, bounded by `deadline_s`.
- `wait_for`: `await frame.wait_for_function("p => globalThis.sroPage.holds(p)", arg=payload, timeout=deadline_s * 1000)`; a Playwright `TimeoutError` answers `False`.

Code notes: frame choice (§4.3), why every wait is a condition, what each confirmation proves (§6.2).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/application/runtime tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/ui_lane.py backend/src/sro/application/ports/page.py backend/src/sro/infrastructure/steel/driver.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runtime): the UI lane acts through the page code and verifies without sleeping

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X5: The API lane — verified replay through httpx with the broker's headers (§6.1 API, §3 API lane failures)

Depends on: X3, S10.

**Files:**
- Create: `backend/src/sro/application/runtime/api_lane.py`
- Create: `backend/tests/unit/application/runtime/test_the_api_lane.py`
- Modify: `backend/tests/unit/runtime_support.py` (`proven_write_step(read_back=…) -> (Step, by_id, ledger)`; `headers_broker(headers)`, a broker double answering `headers`)
- Modify: `backend/src/sro/container.py` (`api_lane()`)

**Interfaces:**
- Consumes: `replay_without_asking` (`application/execution/plan_step.py:84`), `seen_values` (`write_plan.py`), `confirming_read`, `expected_statuses`, `carries_every` (`belts.py`), `HttpCaller` (`ports/http.py`), `SessionBroker.headers` (S10).
- Produces: `ApiLane(http, broker)`: a 401, 403 or 419 answers `StepResult(failed, api, expired=True)` (the executor re-signs in and retries once); any other rejection answers `failed` with a fingerprint (the executor moves to the UI lane for this run); a 2xx is `done` only when a confirming read-back carries the values written, else `unknown`. `ApiLane.read_back(step, values, ctx) -> Verdict | None` (used to settle an unknown write). `K_AUTH_REFUSED = frozenset({401, 403, 419})`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/application/runtime/test_the_api_lane.py
async def test_a_replayed_write_confirmed_by_its_read_back_is_done() -> None:
    http = FakeHttpCaller()
    http.answer(201, '{"id": "ct-9"}')
    http.answer(200, '{"name": "GT2"}')
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types/GT2")
    ctx = lane_context(by_id, ledger=ledger)

    result = await ApiLane(http, headers_broker({"cookie": "sid=1", "x-csrf-token": "t"})).execute(
        step, {"Customer Type": "GT2"}, ctx
    )

    assert result.verdict == "done"
    assert http.sent[0]["headers"]["x-csrf-token"] == "t"


async def test_a_refused_token_asks_for_a_fresh_session() -> None:
    http = FakeHttpCaller()
    http.answer(419, "")
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types/GT2")

    result = await ApiLane(http, headers_broker({})).execute(step, {"Customer Type": "GT2"}, lane_context(by_id, ledger=ledger))

    assert result.expired and result.verdict == "failed"


async def test_a_rejected_replay_hands_the_step_to_the_ui_lane() -> None:
    http = FakeHttpCaller()
    http.answer(400, '{"error": "bad"}')
    step, by_id, ledger = proven_write_step(read_back="/api/customer-types/GT2")

    result = await ApiLane(http, headers_broker({})).execute(step, {"Customer Type": "GT2"}, lane_context(by_id, ledger=ledger))

    assert result.verdict == "failed" and not result.expired and result.fingerprint


async def test_a_write_with_no_read_back_is_unknown() -> None:
    http = FakeHttpCaller()
    http.answer(201, "{}")
    step, by_id, ledger = proven_write_step(read_back=None)

    result = await ApiLane(http, headers_broker({})).execute(step, {"Customer Type": "GT2"}, lane_context(by_id, ledger=ledger))

    assert result.verdict == "unknown"
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_api_lane.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.application.runtime.api_lane'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/api_lane.py
from __future__ import annotations

from collections.abc import Mapping

from sro.application.execution.plan_step import replay_without_asking
from sro.application.ports.http import HttpCaller, HttpResponse, TargetUnreachable
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import LaneContext
from sro.domain.execution.belts import carries_every, confirming_read
from sro.domain.execution.lanes import Lane, StepResult, Verdict, fingerprint_of
from sro.domain.execution.records import made_by
from sro.domain.execution.write_plan import seen_values
from sro.domain.observation.trim import path_shape
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step

K_AUTH_REFUSED = frozenset({401, 403, 419})


class ApiLane:
    lane = Lane.API

    def __init__(self, http: HttpCaller, broker: SessionBroker) -> None:
        self._http = http
        self._broker = broker

    async def execute(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> StepResult:
        cited = [ctx.by_id[one] for one in step.cites if one in ctx.by_id]
        planned = replay_without_asking(
            step=step, cited=cited, values=values, verified_writes=ctx.ledger,
            seen=seen_values(ctx.workflow),
        )
        if planned is None or ctx.held is None:
            return StepResult("failed", Lane.API, "no verified replay for this step")
        payload = planned.payload
        method, url = str(payload["method"]), str(payload["url"])
        headers = {**dict(payload.get("headers") or {}),
                   **await self._broker.headers(ctx.ctx, ctx.held, origin_of(url))}
        ctx.check_stop()
        await ctx.about_to_write()
        try:
            answered = await self._http.send(method, url, headers=headers,
                                             body=payload.get("body"))
        except TargetUnreachable as gone:
            return StepResult("unknown", Lane.API, f"the call may not have arrived: {gone}")
        if answered.status_code in K_AUTH_REFUSED:
            return StepResult("failed", Lane.API, f"the session was refused ({answered.status_code})",
                              expired=True)
        if not answered.succeeded:
            return StepResult("failed", Lane.API, f"the system answered {answered.status_code}",
                              fingerprint=fingerprint_of(Lane.API, str(answered.status_code), path_shape(url)))
        made = made_by({"status": answered.status_code, "body": answered.text})
        confirmed = await self._read(step, planned.confirm or values, ctx, headers)
        return StepResult("done" if confirmed else "unknown", Lane.API, read=made)

    async def read_back(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> Verdict | None:
        if ctx.held is None:
            return None
        probe = confirming_read(step, ctx.by_id)
        if probe is None:
            return None
        headers = await self._broker.headers(ctx.ctx, ctx.held, origin_of(probe.url))
        return "done" if await self._read(step, values, ctx, headers) else None

    async def _read(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext, headers: Mapping[str, str]
    ) -> bool:
        probe = confirming_read(step, ctx.by_id)
        if probe is None:
            return False
        got: HttpResponse = await self._http.send("GET", probe.url, headers=headers)
        distinctive = {name: value for name, value in values.items() if value and value not in probe.url}
        return got.succeeded and bool(distinctive) and carries_every(got.text, distinctive)
```

Code notes: why 401/403/419 are the session and everything else is the step (§3); why a 2xx without a read-back is not proof (§6.2; parent spec §4.3 "Unconfirmed write").

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/application/runtime -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/api_lane.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runtime): the API lane replays proven writes with the session's headers

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X6: The tool lane — mailbox steps through the MCP Gmail connector (§6.1 Tool)

Depends on: X3.

A step that sends mail (`domain/execution/mail_job.py:30` `sends_mail`) is a tool call through the connector (`application/execution/mail_job.py:106` `send_the_mail`, `MailHand`); a mailbox step that only reads (`domain/chat/asked_by.py:50` `only_reads_the_mail`) is the mail this run came from and is already read. Neither takes a tab.

**Files:**
- Create: `backend/src/sro/application/runtime/tool_lane.py`
- Create: `backend/tests/unit/application/runtime/test_the_tool_lane.py`
- Modify: `backend/tests/unit/runtime_support.py` (`mail_send_step()`, `write_ok`, `_sent`, `_answer`)
- Modify: `backend/src/sro/container.py` (`tool_lane()` builds a `MailHand` per `RequestContext` from `write_the_mail`/`send_the_mail`, as `StartWorkflowRun._mail_hand` does at `application/execution/workflow_runs.py:372-388`)

**Interfaces:**
- Produces: `ToolLane(hand: Callable[[RequestContext], MailHand])`: `done` with `read={"message": <sent id>}` when Gmail answers an id; `unknown` when the send answered no id (it may have gone); `failed` when the mail could not be written (nothing sent).

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_send_step_is_one_connector_call_and_no_tab() -> None:
    sent: list[Written] = []
    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=lambda m: _sent(sent, m, "msg-1")))
    step, by_id = mail_send_step()

    result = await lane.execute(step, {"Order": "42"}, lane_context(by_id, held=None, thread="t-1"))

    assert (result.verdict, dict(result.read)) == ("done", {"message": "msg-1"})
    assert [one.thread for one in sent] == ["t-1"]


async def test_a_send_that_answered_no_id_is_never_sent_again_blindly() -> None:
    lane = ToolLane(lambda ctx: MailHand(write=write_ok, send=lambda m: _answer("", "Gmail did not say")))
    step, by_id = mail_send_step()

    result = await lane.execute(step, {}, lane_context(by_id, held=None))

    assert result.verdict == "unknown"
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_tool_lane.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/tool_lane.py
from __future__ import annotations

from collections.abc import Callable, Mapping

from sro.application.context import RequestContext
from sro.application.execution.mail_job import MailHand
from sro.application.runtime.step import LaneContext
from sro.domain.execution.lanes import Lane, StepResult, fingerprint_of
from sro.domain.execution.mail_job import sends_mail
from sro.domain.skill.workflow import Step


class ToolLane:
    lane = Lane.TOOL

    def __init__(self, hand: Callable[[RequestContext], MailHand]) -> None:
        self._hand = hand

    async def execute(
        self, step: Step, values: Mapping[str, str], ctx: LaneContext
    ) -> StepResult:
        if not sends_mail(step, ctx.by_id):
            return StepResult("failed", Lane.TOOL, "this mailbox step sends nothing")
        hand = self._hand(ctx.ctx)
        written = await hand.write(ctx.workflow, values, ctx.thread)
        if isinstance(written, str):
            return StepResult("failed", Lane.TOOL, written,
                              fingerprint=fingerprint_of(Lane.TOOL, "unwritten"))
        ctx.check_stop()
        await ctx.about_to_write()
        sent_id, why = await hand.send(written)
        if not sent_id:
            return StepResult("unknown", Lane.TOOL, why)
        return StepResult("done", Lane.TOOL, f"Gmail took the mail to {written.to}",
                          read={"message": sent_id})
```

Code notes: the mail body is written by the mail agent (`write_the_mail`), whose prompt is design 2's; the tool lane itself calls no model beyond it and reads no screen.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/application/runtime -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/tool_lane.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runtime): mailbox steps are connector calls, never tabs

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X7: The sight lane — Gemini computer use on a Steel screenshot (§6.1 Sight)

Depends on: X3, X4.

**Files:**
- Create: `backend/src/sro/application/runtime/sight_lane.py`
- Modify: `backend/src/sro/application/ports/page.py` (`screenshot`, `hit_test`, `point`)
- Modify: `backend/src/sro/infrastructure/steel/driver.py` (the three methods; `point` through `page.mouse`/`page.keyboard`, which Playwright sends as CDP `Input` events)
- Modify: `backend/src/sro/container.py` (`sight_lane()`: `container.vision` for `gemini-3.8-flash`, and a second `GeminiVisionDriver(settings.gemini_rescue_model, client=metered_client(...))` for the one escalation; both metered and cap-checked by `Meter`)
- Create: `backend/tests/unit/application/runtime/test_the_sight_lane.py`
- Modify: `backend/tests/browser/test_the_steel_driver.py`

**Interfaces:**
- Consumes: `VisionDriver.propose(goal, screen, allowed, history)` (`ports/vision.py`), `FakeVisionDriver` (`fakes.py:644`).
- Produces: `PageDriver.screenshot(session, target_id) -> Screen`; `.hit_test(session, target_id, x, y) -> dict[str, str]` (`sroPage.hitTest`); `.point(session, target_id, action: ActionKind, x: int, y: int, value: str | None) -> None`. `SightLane(driver, flash: VisionDriver | None, pro: VisionDriver | None)`: at most `K_SIGHT_ACTIONS` actions per model, flash first and pro once after it; every action is refused once the tab has left the step's system origin; a step that needs a secret is refused; `StepResult.learned = {"strategy", "query"}` from the hit test of the last acted point.

- [ ] **Step 1: Write the failing tests**

```python
async def test_sight_acts_by_points_and_teaches_the_control_it_hit() -> None:
    driver = scripted_driver(url="https://wms.example/app", hit={"strategy": "component", "query": "#saveButton"},
                             calls=[SeenCall("POST", "https://wms.example/api/customer-types", 201)])
    flash = FakeVisionDriver(ProposedGesture(ActionKind.CLICK, x=400, y=20), ProposedGesture(ActionKind.HOVER, done=True))
    step, by_id = save_step(status=201)

    result = await SightLane(driver, flash, None).execute(step, {}, lane_context(by_id))

    assert result.verdict == "done"
    assert dict(result.learned) == {"strategy": "component", "query": "#saveButton"}
    assert driver.pointed == [("click", 400, 20, None)]


async def test_sight_escalates_once_and_then_gives_up() -> None:
    flash = FakeVisionDriver(ProposedGesture(ActionKind.HOVER, refusal="cannot see it"))
    pro = FakeVisionDriver(ProposedGesture(ActionKind.HOVER, refusal="nor can I"))
    step, by_id = save_step(status=201)

    result = await SightLane(scripted_driver(url="https://wms.example/app"), flash, pro).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed"
    assert (len(flash.asked), len(pro.asked)) == (1, 1)


async def test_sight_never_acts_off_the_system() -> None:
    flash = FakeVisionDriver(ProposedGesture(ActionKind.CLICK, x=1, y=1))
    step, by_id = save_step(status=201)
    driver = scripted_driver(url="https://evil.example/")

    result = await SightLane(driver, flash, None).execute(step, {}, lane_context(by_id))

    assert result.verdict == "failed" and driver.pointed == []
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_sight_lane.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/sight_lane.py
from __future__ import annotations

from collections.abc import Mapping

from sro.application.ports.page import PageDriver
from sro.application.ports.vision import VisionDriver
from sro.application.runtime.step import LaneContext
from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.evidence import primary_gesture, recorded_call, writes
from sro.domain.execution.lanes import (
    K_SIGHT_ACTIONS, Lane, StepResult, fingerprint_of, write_confirmed,
)
from sro.domain.execution.secrets import needs_a_secret
from sro.domain.observation.gesture import Gesture
from sro.domain.recording.events import ActionKind
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step

ALLOWED = (ActionKind.CLICK, ActionKind.TYPE, ActionKind.PRESS, ActionKind.SCROLL, ActionKind.HOVER)


class SightLane:
    lane = Lane.SIGHT

    def __init__(self, driver: PageDriver, flash: VisionDriver | None, pro: VisionDriver | None) -> None:
        self._driver = driver
        self._models = tuple(model for model in (flash, pro) if model is not None)

    async def execute(self, step: Step, values: Mapping[str, str], ctx: LaneContext) -> StepResult:
        held = ctx.held
        primary = primary_gesture(step, ctx.by_id)
        if held is None or primary is None or not self._models:
            return StepResult("failed", Lane.SIGHT, "sight has no page or no model")
        if needs_a_secret(primary):
            return StepResult("failed", Lane.SIGHT, "sight never types a credential")
        home = origin_of(primary.url or primary.system or "")
        goal = _goal(step, values, primary)
        writing = writes(step, ctx.by_id)
        mark = await self._driver.mark(held.session, held.target_id)
        learned: dict[str, str] = {}
        for model in self._models:
            history: list[str] = []
            for _ in range(K_SIGHT_ACTIONS):
                ctx.check_stop()
                if origin_of(await self._driver.url_of(held.session, held.target_id)) != home:
                    return StepResult("failed", Lane.SIGHT, "the page left the system",
                                      fingerprint=fingerprint_of(Lane.SIGHT, "left_origin"))
                screen = await self._driver.screenshot(held.session, held.target_id)
                proposed = await model.propose(goal=goal, screen=screen, allowed=ALLOWED,
                                               history=tuple(history))
                if proposed.done:
                    return await self._finished(step, ctx, writing, mark, learned)
                if proposed.refusal or proposed.x is None or proposed.y is None:
                    break
                learned = dict(await self._driver.hit_test(held.session, held.target_id,
                                                           proposed.x, proposed.y) or {})
                if writing:
                    await ctx.about_to_write()
                await self._driver.point(held.session, held.target_id, proposed.action,
                                         proposed.x, proposed.y, proposed.value)
                history.append(f"{proposed.action.value} at {proposed.x},{proposed.y}")
        return StepResult("failed", Lane.SIGHT, "sight could not finish the step",
                          fingerprint=fingerprint_of(Lane.SIGHT, "gave_up", step.says))

    async def _finished(
        self, step: Step, ctx: LaneContext, writing: bool, mark: int, learned: dict[str, str]
    ) -> StepResult:
        held = ctx.held
        assert held is not None
        calls = await self._driver.calls_since(held.session, held.target_id, mark)
        if not writing:
            return StepResult("done", Lane.SIGHT, calls=calls, learned=learned)
        verdict = write_confirmed(recorded=recorded_call(step, ctx.by_id),
                                  wanted=expected_statuses(step, ctx.by_id), calls=calls)
        return StepResult(verdict or "unknown", Lane.SIGHT, calls=calls, learned=learned)


def _goal(step: Step, values: Mapping[str, str], primary: Gesture) -> str:
    after = primary.action.after
    shown = f" Afterwards the control should show {after.value!r}." if after and after.value else ""
    given = ", ".join(f"{name} = {value}" for name, value in values.items())
    return f"{step.says}.{shown}" + (f" Values: {given}." if given else "")
```

`driver.py`: `screenshot` returns `Screen(image=await page.screenshot(type="png"), mime_type="image/png", width, height)` with the viewport's CSS size (`page.viewport_size`, else `window.innerWidth/innerHeight`); `hit_test` evaluates `sroPage.hitTest(x, y)` in the main frame; `point` moves and clicks with `page.mouse`, types with `page.keyboard.type(value)`, presses `value or "Enter"`, scrolls with `page.mouse.wheel(0, int(value or 400))`.

Code notes: the action cap, the one escalation, the origin rule, and that the model is metered and cap-checked through `Meter` (`infrastructure/gemini/metered.py`).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit/application/runtime tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/sight_lane.py backend/src/sro/application/ports/page.py backend/src/sro/infrastructure/steel/driver.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runtime): the sight lane, capped, origin-bound, escalating once

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X8: The step executor walks the ladder; the known-broken list is stored (§3, §6.3 "A lane failed")

Depends on: X4, X5, X6, X7.

**Files:**
- Create: `backend/src/sro/application/runtime/executor.py`
- Modify: `backend/src/sro/infrastructure/db/models.py` (`KnownBrokenRow`)
- Create: `backend/migrations/versions/2026xxxx_0076_a_lane_known_broken.py`
- Modify: `backend/src/sro/application/ports/repositories.py:414-482` (`WorkflowRepository.break_lane`, `broken_for`, `mend_lane`)
- Modify: `backend/src/sro/infrastructure/db/workflows.py`, `backend/tests/unit/fakes.py:1911` (`FakeWorkflowRepository`)
- Create: `backend/tests/unit/application/runtime/test_the_executor.py`
- Modify: `backend/tests/unit/runtime_support.py` (`RecordingLane(lane, *results)` counting `calls`; `FakeBroker` counting `reauths`; `no_tool()`, `no_api()`, `never()`; `APP`)
- Modify: `backend/tests/integration/test_workflow_repositories.py`
- Modify: `backend/src/sro/container.py` (`step_executor()`)

**Interfaces:**
- Produces:
  - `WorkflowRepository.break_lane(tenant_id, workflow_id, broken: Broken, *, cites: str, at: datetime) -> None`; `.broken_for(tenant_id, workflow_id, cites: Mapping[int, str]) -> tuple[Broken, ...]` (only entries whose stored `cites` equals the step's current `cites_key` — a new doing of the job clears them); `.mend_lane(tenant_id, workflow_id, step: int, lane: Lane) -> None`.
  - `StepExecutor(tool, api, ui, sight, broker).run(step, values, ctx, *, broken: Collection[Broken], start_url: str) -> tuple[StepResult, ...]` — every lane tried, in order; stops at the first result that is not `failed`; an `expired` result re-signs in through `broker.reauth` and retries that lane once. A mailbox read-only step answers `read` without a lane.

- [ ] **Step 1: Write the failing tests**

```python
async def test_the_first_trusted_lane_goes_first_and_the_first_success_ends_it() -> None:
    api = RecordingLane(Lane.API, StepResult("failed", Lane.API, fingerprint="f"))
    ui = RecordingLane(Lane.UI, StepResult("done", Lane.UI))
    sight = RecordingLane(Lane.SIGHT, StepResult("done", Lane.SIGHT))
    step, by_id, ledger = proven_write_step(read_back="/api/x/GT2")

    tried = await StepExecutor(no_tool(), api, ui, sight, FakeBroker()).run(
        step, {}, lane_context(by_id, ledger=ledger), broken=(), start_url=APP)

    assert [one.lane for one in tried] == [Lane.API, Lane.UI]
    assert sight.calls == 0


async def test_an_expired_session_is_signed_back_in_and_the_lane_retried_once() -> None:
    ui = RecordingLane(Lane.UI, StepResult("failed", Lane.UI, expired=True), StepResult("done", Lane.UI))
    broker = FakeBroker()
    step, by_id = save_step(status=201)

    tried = await StepExecutor(no_tool(), no_api(), ui, never(), broker).run(
        step, {}, lane_context(by_id), broken=(), start_url=APP)

    assert tried[-1].verdict == "done" and broker.reauths == 1


async def test_a_known_broken_lane_is_skipped() -> None:
    ui = RecordingLane(Lane.UI, StepResult("done", Lane.UI))
    sight = RecordingLane(Lane.SIGHT, StepResult("done", Lane.SIGHT))
    step, by_id = save_step(status=201)

    await StepExecutor(no_tool(), no_api(), ui, sight, FakeBroker()).run(
        step, {}, lane_context(by_id), broken=(Broken(step.order, Lane.UI, "f"),), start_url=APP)

    assert (ui.calls, sight.calls) == (0, 1)
```

Integration: `break_lane` then `broken_for` with the same cites answers it, with different cites answers nothing, and `mend_lane` removes it.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_the_executor.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/executor.py
from __future__ import annotations

from collections.abc import Collection, Mapping

from sro.application.execution.plan_step import replay_without_asking
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.step import LaneContext, StepLane
from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.evidence import primary_gesture
from sro.domain.execution.lanes import Broken, Lane, StepResult, lanes_for
from sro.domain.execution.mail_job import sends_mail
from sro.domain.execution.write_plan import seen_values
from sro.domain.skill.workflow import Step


class StepExecutor:
    def __init__(self, tool: StepLane, api: StepLane, ui: StepLane, sight: StepLane,
                 broker: SessionBroker) -> None:
        self._lanes = {Lane.TOOL: tool, Lane.API: api, Lane.UI: ui, Lane.SIGHT: sight}
        self._broker = broker

    async def run(self, step: Step, values: Mapping[str, str], ctx: LaneContext, *,
                  broken: Collection[Broken], start_url: str) -> tuple[StepResult, ...]:
        if only_reads_the_mail(step, ctx.by_id):
            return (StepResult("read", Lane.TOOL, "the mail this run came from is already read"),)
        tool = sends_mail(step, ctx.by_id)
        cited = [ctx.by_id[one] for one in step.cites if one in ctx.by_id]
        api = not tool and replay_without_asking(
            step=step, cited=cited, values=values, verified_writes=ctx.ledger,
            seen=seen_values(ctx.workflow),
        ) is not None
        browser = not tool and primary_gesture(step, ctx.by_id) is not None
        tried: list[StepResult] = []
        for lane in lanes_for(step.order, tool=tool, api=api, browser=browser, broken=broken):
            result = await self._lanes[lane].execute(step, values, ctx)
            if result.expired and ctx.held is not None:
                await self._broker.reauth(ctx.ctx, ctx.held, start_url)
                result = await self._lanes[lane].execute(step, values, ctx)
            tried.append(result)
            if result.verdict != "failed" or result.expired:
                break
        return tuple(tried)
```

`KnownBrokenRow`: `tenant_id` (String 64), `workflow_id` (String 64, pk), `ord` (Integer, pk), `lane` (String 8, pk), `fingerprint` (String 32, pk), `cites` (String 32), `at` (DateTime tz). Migration `0076` creates the table with an index on `(tenant_id, workflow_id)`. SQL in `workflows.py`: insert-on-conflict-do-nothing, select by tenant and workflow filtered in Python on `cites`, delete by `(workflow_id, ord, lane)`.

Code notes: why a lane still broken after re-sign-in stops the walk (the session, not the step, is wrong), and the `cites` rule.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_workflow_repositories.py tests/integration/test_the_migrations_run.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/executor.py backend/src/sro/infrastructure/db backend/migrations/versions/*_0076_a_lane_known_broken.py backend/src/sro/application/ports/repositories.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runtime): walk the ladder per step and keep a known-broken list

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## X9: Each lane teaches the one above (§6.3)

Depends on: X8.

**Files:**
- Create: `backend/src/sro/application/runtime/teach.py`
- Create: `backend/tests/unit/application/runtime/test_teaching.py`
- Modify: `backend/tests/unit/runtime_support.py` (`TENANT`, `CTX`, `NOW`, `WORKFLOW`)
- Modify: `backend/src/sro/container.py` (`teach()`)

**Interfaces:**
- Consumes: `remember_locator(workflow_id, LearnedStep, *, by_run)`, `remember_write(tenant_id, *, method, path_pattern, origin, run_id, workflow_id, verified_by, at)` (`WorkflowRepository`); `learned_pattern` (`verified_writes.py`); `confirming_read` (`belts.py`); X8's `break_lane`/`mend_lane`.
- Produces: `Teach(uow, clock).learn(ctx, workflow, by_id, step, tried, *, run_id, values) -> None`:
  - every `failed` result with a fingerprint joins the known-broken list;
  - the lane that succeeded is mended;
  - **sight succeeded** → its hit-test locator is saved (`found_by="sight"`) and the UI lane is mended (the repair);
  - **UI succeeded on a write confirmed by the page's own call**, and the step has a confirming read → the call joins the verified-write ledger (`verified_by="status"`) and the API lane is mended, so the next run starts on the API lane (promotion).

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_sight_success_is_learned_into_the_ui_lane() -> None:
    uow = FakeUnitOfWork()
    step, by_id = save_step(status=201)
    await uow.workflows.break_lane(TENANT, WORKFLOW.id, Broken(step.order, Lane.UI, "f"), cites=cites_key(step), at=NOW)
    tried = (StepResult("failed", Lane.UI, fingerprint="f"),
             StepResult("done", Lane.SIGHT, learned={"strategy": "component", "query": "#saveButton"}))

    await Teach(uow, FakeClock()).learn(CTX, WORKFLOW, by_id, step, tried, run_id="run_1", values={})

    learned = await uow.workflows.learned_for(WORKFLOW.id)
    assert [(one.strategy, one.query, one.found_by) for one in learned] == [("component", "#saveButton", "sight")]
    assert await uow.workflows.broken_for(TENANT, WORKFLOW.id, {step.order: cites_key(step)}) == ()


async def test_a_ui_write_the_page_confirmed_promotes_the_step_to_the_api_lane() -> None:
    uow = FakeUnitOfWork()
    step, by_id, _ = proven_write_step(read_back="/api/customer-types/GT2")
    call = SeenCall("POST", "https://wms.example/api/customer-types", 201)

    await Teach(uow, FakeClock()).learn(CTX, WORKFLOW, by_id, step, (StepResult("done", Lane.UI, calls=(call,)),),
                                        run_id="run_1", values={"Customer Type": "GT2"})

    ledger = await uow.workflows.learned_writes(TENANT)
    assert ("POST", "/api/customer-types") in {(one.method, one.path_pattern) for one in ledger}


async def test_a_ui_write_with_no_read_back_is_not_promoted() -> None:
    uow = FakeUnitOfWork()
    step, by_id, _ = proven_write_step(read_back=None)
    call = SeenCall("POST", "https://wms.example/api/customer-types", 201)

    await Teach(uow, FakeClock()).learn(CTX, WORKFLOW, by_id, step, (StepResult("done", Lane.UI, calls=(call,)),),
                                        run_id="run_1", values={})

    assert await uow.workflows.learned_writes(TENANT) == ()
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_teaching.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/teach.py
from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.belts import confirming_read, expected_statuses
from sro.domain.execution.evidence import recorded_call
from sro.domain.execution.lanes import Broken, Lane, StepResult, cites_key, write_confirmed
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.verified_writes import learned_pattern
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Step, Workflow


class Teach:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def learn(self, ctx: RequestContext, workflow: Workflow, by_id: Mapping[str, Gesture],
                    step: Step, tried: Sequence[StepResult], *, run_id: str,
                    values: Mapping[str, str]) -> None:
        now = self._clock.now()
        async with self._uow as uow:
            for result in tried:
                if result.verdict == "failed" and result.fingerprint:
                    await uow.workflows.break_lane(
                        ctx.tenant_id, workflow.id, Broken(step.order, result.lane, result.fingerprint),
                        cites=cites_key(step), at=now,
                    )
            won = tried[-1] if tried and tried[-1].verdict != "failed" else None
            if won is not None:
                await uow.workflows.mend_lane(ctx.tenant_id, workflow.id, step.order, won.lane)
            if won is not None and won.lane is Lane.SIGHT and won.learned:
                await uow.workflows.remember_locator(
                    workflow.id,
                    LearnedStep(step.order, won.learned["strategy"], won.learned["query"], "sight"),
                    by_run=run_id,
                )
                await uow.workflows.mend_lane(ctx.tenant_id, workflow.id, step.order, Lane.UI)
            recorded = recorded_call(step, by_id)
            if (
                won is not None and won.lane is Lane.UI and recorded is not None
                and confirming_read(step, by_id) is not None
                and write_confirmed(recorded=recorded, wanted=expected_statuses(step, by_id),
                                    calls=won.calls) == "done"
            ):
                await uow.workflows.remember_write(
                    ctx.tenant_id, method=recorded.method.upper(),
                    path_pattern=learned_pattern(recorded.url, values), origin=origin_of(recorded.url),
                    run_id=run_id, workflow_id=workflow.id, verified_by="status", at=now.isoformat(),
                )
                await uow.workflows.mend_lane(ctx.tenant_id, workflow.id, step.order, Lane.API)
            await uow.commit()
```

Code notes: the three rules of §6.3 and why promotion needs a read-back (the API lane cannot confirm a write without one, §6.2).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120`
Expected: all pass. **LIVE QA: QA-2** runs after D3 is deployed (see Proof points).

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/teach.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runtime): sight teaches the UI lane, the UI lane promotes to the API lane

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

# Stream D — durable runs (spec §7)

## D1: A run keeps its progress on its row; an API restart loses nothing (§7.3, §7.4 "Restart", §7.5)

`workflow_runs` holds no loop state, `uq_workflow_runs_one_running_per_device` (`models.py:611-617`) allows one running run per device, and `fail_orphans` (`infrastructure/db/workflow_runs.py:366-387`, called at API start from `interface/http/app.py:96`) fails every running run. A Steel run has no device, may run beside others on one account, and lives in the worker.

**Files:**
- Create: `backend/src/sro/domain/execution/progress.py`
- Modify: `backend/src/sro/domain/execution/workflow_run.py:59-102` (`WorkflowRun.progress`, `WorkflowRun.executor`)
- Modify: `backend/src/sro/infrastructure/db/models.py:554-626` (`progress`, `executor`; the per-device index narrowed)
- Create: `backend/migrations/versions/2026xxxx_0077_a_run_keeps_its_progress.py`
- Modify: `backend/src/sro/infrastructure/db/workflow_runs.py:22-156, 366-387` (map the two fields; `fail_orphans` only for `executor = 'extension'`)
- Modify: `backend/tests/unit/fakes.py:1679` (`FakeWorkflowRunRepository.save` and `fail_orphans` follow the same rules)
- Create: `backend/tests/unit/domain/test_a_run_s_progress.py`
- Modify: `backend/tests/integration/test_workflow_run_repositories.py`

**Interfaces:**
- Produces:
  - `MAIN = "main"`; `StepMark(lane: str = "", verdict: str = "", wrote: Literal["", "sending", "done", "unknown"] = "")`; `Progress(step: int = 0, marks: dict[int, StepMark], read: dict[str, str], tabs: dict[str, str], lease: str = "", account: dict[str, str], start_url: str = "", asking: dict[str, str])`; `Progress.of(raw: Mapping[str, object] | None) -> Progress`; `.as_json() -> dict[str, object]`; `.sending(order)`; `.written(order) -> bool`; `.in_doubt(order) -> bool`; `.settle(order, *, lane, verdict)`.
  - `K_STEP_HEARTBEAT_S = 30`, `K_STEP_LIMIT_S = 300`, `K_BEAT_EVERY_S = 10`, `K_BUDGET_FLOOR_S = 120`, `K_BUDGET_PER_STEP_S = 60`, `K_BUDGET_FACTOR = 4`; `run_budget(workflow: Workflow, by_id: Mapping[str, Gesture]) -> float` — seconds: `max(K_BUDGET_FLOOR_S, K_BUDGET_FACTOR * demonstrated_span + K_BUDGET_PER_STEP_S * len(steps))`.
  - `WorkflowRun.progress: dict[str, object] = {}`, `WorkflowRun.executor: str = "extension"`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/domain/test_a_run_s_progress.py
from sro.domain.execution.progress import K_BUDGET_FLOOR_S, Progress, run_budget
from sro.domain.observation.gesture import Action, Gesture
from sro.domain.skill.workflow import Step, Workflow


def timed_job(*, seconds: float, steps: int) -> tuple[Workflow, dict[str, Gesture]]:
    gestures = {
        f"g{n}": Gesture(id=f"g{n}", tenant="t", stream_id="s", batch_id="b",
                         at=n * seconds / max(steps - 1, 1), url=None, system=None, tab_id=1,
                         frame_url=None, action=Action(kind="click", at=0.0))
        for n in range(steps)
    }
    job = Workflow(id="wfl_t", tenant="t", title="t", narrative="n",
                   steps=[Step(order=n, says=f"s{n}", system=None, cites=[f"g{n}"]) for n in range(steps)])
    return job, gestures


def test_progress_survives_its_row() -> None:
    progress = Progress(step=2, read={"id": "ct-9"}, tabs={"main": "T1"}, lease="lse_1")
    progress.sending(1)
    progress.settle(0, lane="ui", verdict="done")

    again = Progress.of(progress.as_json())

    assert again == progress


def test_a_write_in_flight_is_in_doubt_and_never_written() -> None:
    progress = Progress()
    progress.sending(3)

    assert progress.in_doubt(3) and not progress.written(3)


def test_a_settled_write_is_written_once() -> None:
    progress = Progress()
    progress.sending(3)
    progress.settle(3, lane="api", verdict="done")

    assert progress.written(3) and not progress.in_doubt(3)


def test_the_budget_grows_with_what_the_operator_took() -> None:
    slow, quick = timed_job(seconds=600, steps=5), timed_job(seconds=20, steps=5)

    assert run_budget(*slow) > run_budget(*quick) >= K_BUDGET_FLOOR_S
```

Integration (`test_workflow_run_repositories.py`): two runs with `executor="steel"`, `device_id=""`, both `running`, save without a conflict and read back with their `progress`; `fail_orphans` fails an extension run and leaves the Steel run `running`.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_a_run_s_progress.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.domain.execution.progress'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/domain/execution/progress.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Literal

from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Workflow, ordered_cites

MAIN = "main"

K_STEP_HEARTBEAT_S = 30
K_STEP_LIMIT_S = 300
K_BEAT_EVERY_S = 10
K_BUDGET_FLOOR_S = 120
K_BUDGET_PER_STEP_S = 60
K_BUDGET_FACTOR = 4

Wrote = Literal["", "sending", "done", "unknown"]


@dataclass
class StepMark:
    lane: str = ""
    verdict: str = ""
    wrote: Wrote = ""


@dataclass
class Progress:
    step: int = 0
    marks: dict[int, StepMark] = field(default_factory=dict)
    read: dict[str, str] = field(default_factory=dict)
    tabs: dict[str, str] = field(default_factory=dict)
    lease: str = ""
    account: dict[str, str] = field(default_factory=dict)
    start_url: str = ""
    asking: dict[str, str] = field(default_factory=dict)

    @classmethod
    def of(cls, raw: Mapping[str, object] | None) -> Progress:
        if not raw:
            return cls()
        return cls(
            step=int(str(raw.get("step") or 0)),
            marks=_marks(raw.get("marks")),
            read=_strings(raw.get("read")),
            tabs=_strings(raw.get("tabs")),
            lease=str(raw.get("lease") or ""),
            account=_strings(raw.get("account")),
            start_url=str(raw.get("start_url") or ""),
            asking=_strings(raw.get("asking")),
        )

    def as_json(self) -> dict[str, object]:
        out = asdict(self)
        out["marks"] = {str(k): v for k, v in out["marks"].items()}
        return out

    def sending(self, order: int) -> None:
        self.marks.setdefault(order, StepMark()).wrote = "sending"

    def written(self, order: int) -> bool:
        return self.marks.get(order, StepMark()).wrote == "done"

    def in_doubt(self, order: int) -> bool:
        return self.marks.get(order, StepMark()).wrote in ("sending", "unknown")

    def settle(self, order: int, *, lane: str, verdict: str) -> None:
        mark = self.marks.setdefault(order, StepMark())
        mark.lane, mark.verdict = lane, verdict
        if mark.wrote:
            mark.wrote = "done" if verdict == "done" else "unknown" if verdict == "unknown" else ""


_WROTE: dict[str, Wrote] = {"": "", "sending": "sending", "done": "done", "unknown": "unknown"}


def _strings(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): str(one) for key, one in value.items()}


def _marks(value: object) -> dict[int, StepMark]:
    if not isinstance(value, Mapping):
        return {}
    return {
        int(key): StepMark(
            lane=str(one.get("lane") or ""),
            verdict=str(one.get("verdict") or ""),
            wrote=_WROTE.get(str(one.get("wrote") or ""), ""),
        )
        for key, one in value.items()
        if isinstance(one, Mapping)
    }


def run_budget(workflow: Workflow, by_id: Mapping[str, Gesture]) -> float:
    times = [by_id[one].at for one in ordered_cites(workflow) if one in by_id]
    shown = max(times) - min(times) if len(times) > 1 else 0.0
    return max(
        float(K_BUDGET_FLOOR_S),
        K_BUDGET_FACTOR * shown + K_BUDGET_PER_STEP_S * len(workflow.steps),
    )
```

`_strings` and `_marks` parse the JSONB at the boundary, so a malformed row reads as empty rather than crashing a retried activity. A `failed` step clears `wrote`: the system refused it, so nothing was written.

`models.py` `WorkflowRunRow`: `progress: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")`, `executor: Mapped[str] = mapped_column(String(16), nullable=False, default="extension", server_default="extension")`; the per-device index's `postgresql_where` becomes `text("outcome = 'running' AND executor = 'extension'")`. Migration `0077`: `add_column` ×2, `drop_index("uq_workflow_runs_one_running_per_device")` and re-create it with the narrowed predicate (an index is replaced; no table or column is dropped). `workflow_runs.py`: `"progress": dict(run.progress), "executor": run.executor` in `_run_values`; `progress=dict(row.progress or {}), executor=row.executor` in `_row_to_run`; `fail_orphans` adds `WorkflowRunRow.executor == "extension"`.

Code notes: each constant (spec §7.5), why the budget is derived from the demonstration, why the API's startup sweep must never touch a Steel run (§7.4 "API restarts lose nothing").

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_workflow_run_repositories.py tests/integration/test_workflow_runs_against_postgres.py tests/integration/test_the_migrations_run.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/domain/execution/progress.py backend/src/sro/domain/execution/workflow_run.py backend/src/sro/infrastructure/db backend/migrations/versions/*_0077_a_run_keeps_its_progress.py backend/tests docs/code-notes
git commit -m "feat(runs): a run's progress lives on its row; Steel runs survive an API restart

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## D2: `RunWorkflow` — prepare, acquire, each step, finish, release (§7.1, §7.2, §5.4)

Depends on: D1, S7, S8, X8, X9.

Runs are spawned in the API process today (`interface/http/v1/routers/workflow_runs.py:138` `container.pursuits.spawn`), and the old engine's `ExecutionWorkflow` (`infrastructure/temporal/workflows.py:27-72`) already shows the shape: a workflow looping activities. `RunWorkflow` holds only ids; every activity loads the run and its `progress`.

**Files:**
- Create: `backend/src/sro/application/runtime/run_steps.py`
- Modify: `backend/src/sro/infrastructure/temporal/queues.py` (`RUNS_QUEUE = "runs"`)
- Modify: `backend/src/sro/infrastructure/temporal/activities.py` (`RunRef`, `Prepared`, `StepOutcome`, `RunAnswer`; `RunActivities`)
- Modify: `backend/src/sro/infrastructure/temporal/workflows.py` (`RunWorkflow`)
- Modify: `backend/src/sro/infrastructure/temporal/worker.py:120-150` (a second `Worker` on `RUNS_QUEUE`)
- Modify: `backend/src/sro/application/ports/durable.py` (`start_run`)
- Modify: `backend/src/sro/infrastructure/temporal/durable.py` (`start_run`)
- Modify: `backend/src/sro/container.py` (`run_steps()`)
- Modify: `backend/tests/unit/fakes.py:377, 1679` (`FakeDurableExecution.start_run` appends `(run_id, budget_s)` to `runs_started`; `FakeWorkflowRunRepository.on_save: Callable[[WorkflowRun], None] | None`, called with each saved copy)
- Modify: `backend/tests/unit/runtime_support.py` (`steel_run(steps=…)` builds the world: fake unit of work with a `WorkflowRun(executor="steel")`, its job and gestures, a `SessionBroker` over the fakes, `ScriptedLane`s for the four lanes (`answers(*results)`, `on_execute(fn)`, `calls`), and `RunSteps`; helpers `type_step_evidence`, `save_step_evidence`, `mail_send_evidence`, `saved_run()`, `mark_sending(order)`, `forget_every_connection()`)
- Create: `backend/tests/unit/application/runtime/test_run_steps.py`
- Create: `backend/tests/integration/test_run_workflow.py` (Temporal from `make up` at `localhost:7233`; skipped when it does not answer)
- Modify: `backend/tests/integration/test_runs_on_local_steel.py` (scenario: two runs as tabs on one account)

**Interfaces:**
- Produces:
  - `RunSteps(uow, broker, executor, teach, api, clock)`: `prepare(ctx, run_id) -> Prepared(browser: bool)`; `acquire(ctx, run_id)`; `step(ctx, run_id, *, stop: asyncio.Event) -> StepOutcome(more: bool, asking: str = "", failed: bool = False)`; `finish(ctx, run_id) -> str` (outcome); `release(ctx, run_id)`; `beat(ctx, run_id)`.
  - Activities (names are the contract): `run.prepare`, `run.acquire`, `run.step`, `run.finish`, `run.release`; `RunRef(tenant_id: str, principal_id: str, run_id: str)`.
  - `RunWorkflow.run(ref: RunRef) -> str` on `RUNS_QUEUE`; step activities have `heartbeat_timeout = K_STEP_HEARTBEAT_S`, `start_to_close_timeout = K_STEP_LIMIT_S`, and retry (a retry is safe: `progress` guards every write); `NeedsAPerson` and `Stopped` are not retried; `run.acquire` retries without limit on `PoolFull` with backoff, so a run beyond capacity waits (D8) inside its budget.
  - `DurableExecution.start_run(ctx, *, run_id: str, budget_s: float) -> None` — workflow id `workflow-run-{run_id}`, `execution_timeout = budget_s`.
  - Step results are also written as `RunStep` rows (`verdict`: done/read→`held`, failed→`failed`, unknown→`unclear`; `verdict_by` and `planned_by` = the lane), so the console and panel read them unchanged.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/application/runtime/test_run_steps.py
async def test_a_run_advances_one_step_per_call_and_says_when_it_is_done() -> None:
    world = await steel_run(steps=[type_step_evidence(), save_step_evidence(status=201)])
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))

    first = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    second = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert (first.more, second.more) == (True, False)
    run = await world.saved_run()
    assert [one.verdict for one in run.steps] == ["held", "held"]
    assert Progress.of(run.progress).step == 2


async def test_a_mail_only_job_takes_no_browser() -> None:
    world = await steel_run(steps=[mail_send_evidence()])

    prepared = await world.run_steps.prepare(CTX, world.run_id)

    assert prepared.browser is False


async def test_a_write_is_marked_before_it_is_sent() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201)])
    world.lanes.ui.on_execute(lambda ctx: ctx.about_to_write())
    world.lanes.ui.answers(StepResult("done", Lane.UI))
    seen: list[str] = []
    world.uow.workflow_runs.on_save = lambda run: seen.append(Progress.of(run.progress).marks.get(0, StepMark()).wrote)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert seen[:2] == ["sending", "done"]


async def test_a_step_no_lane_could_do_asks_a_person() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201)])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    assert Progress.of((await world.saved_run()).progress).asking["kind"] == "step"
```

(`steel_run` in `tests/unit/runtime_support.py` saves a `WorkflowRun(executor="steel")`, its job and gestures into a `FakeUnitOfWork`, and builds `RunSteps` with a `SessionBroker` over the fakes and an executor over scriptable lanes.)

`test_run_workflow.py` registers `RunWorkflow` with stub activities named `run.prepare` … `run.release` on a unique task queue and proves: the step activity loops until `more` is false; `run.release` runs after `run.finish`; an activity raising `NeedsAPerson` is not retried.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_run_steps.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.application.runtime.run_steps'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/runtime/run_steps.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace

from sro.application.context import RequestContext
from sro.application.ports.page import PageGone
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.runtime.api_lane import ApiLane
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.executor import StepExecutor
from sro.application.runtime.step import Held, LaneContext, NeedsAPerson, Stopped
from sro.application.runtime.teach import Teach
from sro.domain.chat.asked_by import only_reads_the_mail
from sro.domain.execution.account import Account
from sro.domain.execution.evidence import primary_gesture, writes
from sro.domain.execution.lanes import Lane, StepResult, cites_key
from sro.domain.execution.mail_job import sends_mail
from sro.domain.execution.progress import MAIN, Progress
from sro.domain.execution.waiting import read_wait
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step, Workflow, cited_ids

_RUN_VERDICT = {"done": "held", "read": "held", "failed": "failed", "unknown": "unclear"}


@dataclass(frozen=True, slots=True)
class Prepared:
    browser: bool


@dataclass(frozen=True, slots=True)
class StepOutcome:
    more: bool
    asking: str = ""
    failed: bool = False


class RunSteps:
    def __init__(self, uow: UnitOfWork, broker: SessionBroker, executor: StepExecutor,
                 teach: Teach, api: ApiLane, clock: Clock) -> None:
        self._uow, self._broker, self._executor = uow, broker, executor
        self._teach, self._api, self._clock = teach, api, clock

    async def prepare(self, ctx: RequestContext, run_id: str) -> Prepared:
        run, workflow, by_id = await self._load(ctx, run_id)
        ordered = _ordered(workflow)
        browser = [s for s in ordered if not sends_mail(s, by_id) and not only_reads_the_mail(s, by_id)]
        progress = Progress.of(run.progress)
        if browser and not progress.start_url:
            first = primary_gesture(browser[0], by_id)
            progress.start_url = (first.page_url or first.url or "") if first else ""
            account = await self._broker.account_for(ctx, progress.start_url)
            progress.account = {"origin": account.origin, "username": account.username}
            await self._save(run, progress)
        return Prepared(browser=bool(browser))

    async def acquire(self, ctx: RequestContext, run_id: str) -> None:
        run, _, _ = await self._load(ctx, run_id)
        progress = Progress.of(run.progress)
        if progress.lease and progress.tabs.get(MAIN):
            try:
                await self._broker.reattach(ctx, progress.lease, progress.tabs[MAIN])
                return
            except PageGone:
                pass
        account = Account(ctx.tenant_id.value, progress.account["origin"], progress.account["username"])
        held = await self._broker.acquire(ctx, account, progress.start_url, holder=run_id)
        progress.lease, progress.tabs = held.lease.id, {MAIN: held.target_id}
        await self._save(run, progress)

    async def step(self, ctx: RequestContext, run_id: str, *, stop: asyncio.Event) -> StepOutcome:
        run, workflow, by_id = await self._load(ctx, run_id)
        progress = Progress.of(run.progress)
        ordered = _ordered(workflow)
        if progress.step >= len(ordered):
            return StepOutcome(more=False)
        step = ordered[progress.step]
        held = await self._held(ctx, run_id, progress)
        values = {**run.values, **progress.read}
        lane_ctx = await self._lane_context(ctx, run, workflow, by_id, held, stop, step)
        if progress.written(step.order):
            done_by = Lane(progress.marks[step.order].lane or Lane.UI.value)
            return await self._advance(run, progress, step, StepResult("done", done_by, "already done"), ordered)
        if progress.in_doubt(step.order):
            settled = await self._api.read_back(step, values, lane_ctx)
            if settled is None:
                return await self._ask(ctx, run, progress, step, NeedsAPerson(
                    f"'{step.says}' may already have been done and no read-back can tell; "
                    "check it and answer done or redo", kind="step"))
            return await self._advance(run, progress, step, StepResult(settled, Lane.API, "settled by read-back"), ordered)
        if not run.live and writes(step, by_id):
            return await self._advance(run, progress, step, StepResult("read", Lane.UI, "a dry run: withheld"), ordered, withheld=True)
        try:
            async with self._uow as uow:
                broken = await uow.workflows.broken_for(
                    ctx.tenant_id, workflow.id, {one.order: cites_key(one) for one in ordered})
            tried = await self._executor.run(step, values, lane_ctx, broken=broken,
                                             start_url=progress.start_url)
        except Stopped:
            return await self._stopped(run, step)
        except NeedsAPerson as asked:
            return await self._ask(ctx, run, progress, step, asked)
        await self._teach.learn(ctx, workflow, by_id, step, tried, run_id=run.id, values=values)
        run, _, _ = await self._load(ctx, run_id)
        progress = Progress.of(run.progress)
        last = tried[-1] if tried else StepResult("failed", Lane.UI, "no lane could act on this step")
        if last.verdict == "unknown":
            settled = await self._api.read_back(step, values, lane_ctx)
            if settled is None:
                return await self._ask(ctx, run, progress, step, NeedsAPerson(
                    f"'{step.says}' was sent and nothing confirms it; check it and answer", kind="step"))
            last = replace(last, verdict=settled)
        if last.verdict == "failed":
            return await self._ask(ctx, run, progress, step, NeedsAPerson(
                f"'{step.says}' could not be done: {last.reason}", kind="step"))
        return await self._advance(run, progress, step, last, ordered)
```

plus these methods (full bodies in the implementation, each a few lines):
- `_held(ctx, run_id, progress) -> Held | None` — `None` without a tab; `broker.reattach`; on `PageGone`, `broker.recover(ctx, progress.lease, progress.start_url, holder=run_id)` and save the new lease and tab id.
- `_lane_context(...)` — `learned_for`, `learned_writes` read in one unit of work; `about_to_write` = `lambda: self._sending(ctx, run.id, step.order)`; `thread = read_wait(run.awaiting).thread if run.awaiting else ""`.
- `_sending(ctx, run_id, order)` — load, `progress.sending(order)`, save, commit: durable before the write goes out.
- `_advance(run, progress, step, result, ordered, *, withheld=False)` — `progress.settle(...)`, `progress.read.update(result.read)`, `progress.step += 1`, append `RunStep(order=len(run.steps), of_step=step.order, says=step.says, verdict="withheld" if withheld else _RUN_VERDICT[result.verdict], verdict_by=result.lane.value, planned_by=result.lane.value, reason=result.reason, made=dict(result.read))`, save, `StepOutcome(more=progress.step < len(ordered))`.
- `_ask(ctx, run, progress, step, asked)` — `progress.asking = {"id": f"q-{run.id}-{step.order}-{len(run.steps)}", "kind": asked.kind, "text": asked.question}`, save, `StepOutcome(more=True, asking=<id>)` (D5 adds telling the operator).
- `_stopped(run, step)` — outcome `aborted`, a `RunStep` saying the step stopped, save, `StepOutcome(more=False, failed=True)`.
- `finish` — outcome `held` when every step is `held`/`read`/`withheld`, else `failed`; `finished_at`; save.
- `release` — `broker.release(Held(...))` for the saved tab (ignoring `PageGone`), then `progress.tabs = {}`; save.
- `beat` — `broker.beat(ctx, progress.lease, holder=run_id)` when a lease is held.
- `_load` (run, job, cited gestures), `_save` (run with `progress.as_json()`), `_ordered(workflow)` (steps by `order`).

`workflows.py`:

```python
_STEP_RETRY = RetryPolicy(maximum_attempts=3, non_retryable_error_types=["NeedsAPerson", "Stopped"])
_QUEUE_RETRY = RetryPolicy(initial_interval=timedelta(seconds=5), maximum_interval=timedelta(seconds=60),
                           maximum_attempts=0, non_retryable_error_types=["NeedsAPerson"])
_SHORT = timedelta(seconds=60)


@workflow.defn
class RunWorkflow:
    @workflow.run
    async def run(self, ref: RunRef) -> str:
        prepared: Prepared = await workflow.execute_activity(
            "run.prepare", ref, result_type=Prepared, start_to_close_timeout=_SHORT, retry_policy=_READ_RETRY)
        try:
            if prepared.browser:
                await workflow.execute_activity(
                    "run.acquire", ref, start_to_close_timeout=timedelta(seconds=K_STEP_LIMIT_S),
                    retry_policy=_QUEUE_RETRY)
            while (await self._step(ref)).more:
                pass
            await workflow.execute_activity("run.finish", ref, start_to_close_timeout=_SHORT,
                                            retry_policy=_READ_RETRY)
        finally:
            await workflow.execute_activity("run.release", ref, start_to_close_timeout=_SHORT,
                                            retry_policy=_READ_RETRY)
        return ref.run_id

    async def _step(self, ref: RunRef) -> StepOutcome:
        return await workflow.execute_activity(
            "run.step", ref, result_type=StepOutcome,
            start_to_close_timeout=timedelta(seconds=K_STEP_LIMIT_S),
            heartbeat_timeout=timedelta(seconds=K_STEP_HEARTBEAT_S),
            retry_policy=_STEP_RETRY,
            cancellation_type=workflow.ActivityCancellationType.WAIT_CANCELLATION_COMPLETED,
        )
```

`activities.py` `RunActivities(container)`:

```python
    @activity.defn(name="run.step")
    async def run_step(self, ref: RunRef) -> StepOutcome:
        ctx = _context(ref.tenant_id, ref.principal_id)
        steps = self._container.run_steps()
        stop = asyncio.Event()
        work = asyncio.create_task(steps.step(ctx, ref.run_id, stop=stop))
        try:
            while not work.done():
                activity.heartbeat()
                await steps.beat(ctx, ref.run_id)
                await asyncio.wait({work}, timeout=K_BEAT_EVERY_S)
        except asyncio.CancelledError:
            stop.set()
            await asyncio.shield(work)
            raise
        return work.result()
```

and one-liners for `run.prepare`, `run.acquire`, `run.finish`, `run.release`. `worker.py`: `runs = Worker(client, identity=me, task_queue=RUNS_QUEUE, workflows=[RunWorkflow], activities=[…the five…])`, run with `default` under `asyncio.gather`. `durable.py`:

```python
    async def start_run(self, ctx: RequestContext, *, run_id: str, budget_s: float) -> None:
        client = await self._connect()
        await client.start_workflow(
            RunWorkflow.run,
            RunRef(tenant_id=ctx.tenant_id.value, principal_id=ctx.principal_id.value, run_id=run_id),
            id=f"workflow-run-{run_id}",
            task_queue=RUNS_QUEUE,
            execution_timeout=timedelta(seconds=budget_s),
        )
```

Code notes: why the workflow holds only ids (determinism, §7.2), why a step retry is safe (`progress`), why acquire retries without limit (a queue, D8), and that **a code change is live only after the worker restarts** (AGENTS.md).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && uv run lint-imports`
Run (with `make up`): `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_run_workflow.py tests/integration/test_runs_on_local_steel.py -q -o faulthandler_timeout=120`
Expected: all pass; the two-tabs scenario shows two `RunWorkflow`s on one account sharing one lease with two target ids.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application/runtime/run_steps.py backend/src/sro/infrastructure/temporal backend/src/sro/application/ports/durable.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runs): every Steel run is a Temporal workflow of idempotent activities

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## D3: The server starts the run; the rollout setting routes tenants to Steel (§7.1, §9)

Depends on: D2.

Every door that starts a mined job — the press (`routers/workflow_runs.py:123`), triggers (`fire_trigger.py:184`), confirmations (`answer_confirmation.py:66`) — goes through `StartWorkflowRun` (`application/execution/workflow_runs.py:90`). The switch is made there, once. A mail that names one job with certainty and all its required values starts the run with no panel press (D3 of the parent spec).

**Files:**
- Modify: `backend/src/sro/config.py` (`steel_tenants: tuple[str, ...] = ()`)
- Modify: `backend/src/sro/application/execution/workflow_runs.py:90-291` (`StartWorkflowRun.__init__`, `execute`, `perform`, new `runs_on_steel`)
- Modify: `backend/src/sro/application/chat/from_the_mail.py:92-291` (`FromTheMail.__init__` takes `start: StartWorkflowRun | None`; `execute` starts sure, complete requests)
- Modify: `backend/src/sro/container.py:698-712, 750-774` (`from_the_mail`, `start_workflow_run`)
- Modify: `backend/tests/unit/application/rig/test_start_workflow_run.py`, `backend/tests/unit/application/rig/test_from_the_mail.py`

**Interfaces:**
- Produces: `Settings.steel_tenants` (`SRO_STEEL_TENANTS='["greyorange"]'`) — the spec's per-tenant `executor: extension | steel`; `StartWorkflowRun.runs_on_steel(ctx) -> bool`. For a Steel tenant, `execute` stores `executor="steel"`, `device_id=""`, skips the device-online and one-run-per-device checks, and `perform` calls `durable.start_run(ctx, run_id=…, budget_s=run_budget(workflow, by_id))` and returns (no in-process run, no `draft_the_mail_job`, no approval). `Offered.started` is `True` for a mail whose run was started.

- [ ] **Step 1: Write the failing tests**

In `test_start_workflow_run.py`, `_starter` gains `durable: FakeDurableExecution | None = None` and `steel_tenants: frozenset[str] = frozenset()` and passes them through; in `test_from_the_mail.py`, `_look` gains `start: StartWorkflowRun | None = None`, and a helper `mail_world(*, sure, values, steel)` builds one sure request mail from the file's `_Mailbox`/`_Reads` doubles, a saved job, `_look(..., start=_starter(...))` and a `FakeDurableExecution` exposed as `world.durable`. `save_job(uow, workflow_id)` is added to `tests/unit/runtime_support.py`.

```python
async def test_a_steel_tenant_s_press_starts_a_durable_run_and_drives_no_browser() -> None:
    uow, durable, channel = FakeUnitOfWork(), FakeDurableExecution(), FakeChannel()
    await save_job(uow, "wfl_ct")
    starter = _starter(uow, channel=channel, durable=durable, steel_tenants=frozenset({TENANT.value}))

    run = await starter.execute(CTX, workflow_id="wfl_ct", device_id=DeviceId("offline"),
                                values={"Customer Type": "GT2"}, live=True, allow_focus=False)
    await starter.perform(CTX, run)

    assert (run.executor, run.device_id) == ("steel", "")
    assert [one for one, _ in durable.runs_started] == [run.id]
    assert channel.sent == []


async def test_a_sure_mail_with_every_value_starts_the_run_itself() -> None:
    world = mail_world(sure=True, values={"Customer Type": "GT2"}, steel=True)

    looked = await world.from_the_mail.execute(CTX)

    assert looked.offered[0].started
    assert len(world.durable.runs_started) == 1


async def test_an_extension_tenant_is_unchanged() -> None:
    world = mail_world(sure=True, values={"Customer Type": "GT2"}, steel=False)

    looked = await world.from_the_mail.execute(CTX)

    assert not looked.offered[0].started and world.durable.runs_started == []
```

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/rig/test_start_workflow_run.py tests/unit/application/rig/test_from_the_mail.py -q -o faulthandler_timeout=120`
Expected: FAIL, `TypeError: StartWorkflowRun.__init__() got an unexpected keyword argument 'durable'`.

- [ ] **Step 3: Implement**

`StartWorkflowRun.__init__` gains `durable: DurableExecution | None = None, steel_tenants: frozenset[str] = frozenset()`; add

```python
    def runs_on_steel(self, ctx: RequestContext) -> bool:
        return self._durable is not None and ctx.tenant_id.value in self._steel_tenants
```

In `execute`: `steel = self.runs_on_steel(ctx)`; the `device_id not in self._channel.online(...)` and `in_flight` refusals run only when `not steel`; the `WorkflowRun` is built with `device_id="" if steel else device_id.value` and `executor="steel" if steel else "extension"`. In `perform`, first:

```python
        if run.executor == "steel" and self._durable is not None:
            async with self._uow as uow:
                workflow = await uow.workflows.get(ctx.tenant_id, run.workflow_id)
                cited = await uow.gestures.gestures_for(ctx.tenant_id, ids=tuple(sorted(cited_ids(workflow))))
            await self._durable.start_run(
                ctx, run_id=run.id, budget_s=run_budget(workflow, {one.id: one for one in cited})
            )
            return
```

`FromTheMail`: before building the final `LookedInTheMail`, `offered = [await self._started(ctx, one) for one in offered]` with

```python
    async def _started(self, ctx: RequestContext, one: Offered) -> Offered:
        if one.missing or one.started or self._start is None or not self._start.runs_on_steel(ctx):
            return one
        run = await self._start.execute(
            ctx, workflow_id=one.workflow_id, device_id=DeviceId(""), values=dict(one.values),
            live=True, allow_focus=False, conversation=(SERVER, one.thread),
        )
        await self._start.perform(ctx, run)
        return replace(one, started=True)
```

`container.py`: `start_workflow_run` passes `durable=self.durable, steel_tenants=frozenset(self.settings.steel_tenants)`; `from_the_mail` passes `start=self.start_workflow_run()`. Deploy file: `SRO_STEEL_TENANTS` on api and worker, empty until rollout step 2 (R1).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit, then LIVE QA**

```bash
git add backend/src/sro/config.py backend/src/sro/application/execution/workflow_runs.py backend/src/sro/application/chat/from_the_mail.py backend/src/sro/container.py infra/docker-compose.deploy.yml backend/tests docs/code-notes
git commit -m "feat(runs): the server starts Steel tenants' runs, from a press, a trigger or a mail

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

**LIVE QA: QA-1** and **QA-3** follow (Proof points).

## D4: Stop — cancel the workflow; the step finishes its primitive and records itself stopped (§7.4 "Stop")

Depends on: D2.

**Files:**
- Modify: `backend/src/sro/application/ports/durable.py`, `backend/src/sro/infrastructure/temporal/durable.py` (`cancel_run`)
- Modify: `backend/src/sro/application/execution/workflow_runs.py:550-567` (`AbortWorkflowRun`)
- Modify: `backend/src/sro/infrastructure/temporal/workflows.py` (`RunWorkflow` catches cancellation: `run.stopped`, then the `finally` release)
- Modify: `backend/src/sro/infrastructure/temporal/activities.py` (`run.stopped`)
- Modify: `backend/src/sro/application/runtime/run_steps.py` (`stopped(ctx, run_id)`)
- Modify: `backend/src/sro/container.py:786-787`
- Modify: `backend/tests/unit/application/rig/test_start_workflow_run.py` (abort), `backend/tests/unit/application/runtime/test_run_steps.py`, `backend/tests/integration/test_run_workflow.py`, `backend/tests/integration/test_runs_on_local_steel.py` (scenario: a stop during a step)
- Modify: `backend/tests/unit/fakes.py` (`FakeDurableExecution.cancel_run` appends to `cancelled`), `backend/tests/unit/runtime_support.py` (`running_steel_run(uow)`; `ScriptedLane.really_acts` routes to the fake driver so `driver.acted` records what reached the page)

**Interfaces:**
- Produces: `DurableExecution.cancel_run(run_id: str) -> None` (cancels `workflow-run-{run_id}`); `AbortWorkflowRun` for a Steel run calls it and returns the row (still `running` until the step records itself); `RunSteps.stopped(ctx, run_id)` sets outcome `aborted` if the run is still `running`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_stopping_a_steel_run_cancels_its_workflow_and_touches_no_browser() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await running_steel_run(uow)

    await AbortWorkflowRun(uow, Stops(), Approvals(), durable=durable).execute(CTX, run_id=run.id)

    assert durable.cancelled == [run.id]


async def test_a_stop_is_seen_before_the_next_primitive() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201)])
    stop = asyncio.Event()
    stop.set()
    world.lanes.ui.really_acts = True

    outcome = await world.run_steps.step(CTX, world.run_id, stop=stop)

    assert outcome.failed and not outcome.more
    assert (await world.saved_run()).outcome == "aborted"
    assert world.driver.acted == []
```

`test_run_workflow.py`: a stub `run.step` that heartbeats forever; cancelling the workflow delivers the cancellation to it, `run.stopped` then `run.release` run, and the workflow ends cancelled. Local Steel: a real run is stopped while its UI step waits on a condition, and the rig's POST count is 0.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application -q -o faulthandler_timeout=120 -k "stop"`
Expected: FAIL, `TypeError: AbortWorkflowRun.__init__() got an unexpected keyword argument 'durable'`.

- [ ] **Step 3: Implement**

`AbortWorkflowRun.__init__(uow, stops, approvals, *, durable: DurableExecution | None = None)`; in `execute`, after the `running` check and before the `device_id` check:

```python
        if run.executor == "steel" and self._durable is not None:
            await self._durable.cancel_run(run.id)
            return run
```

`RunWorkflow.run` wraps its body:

```python
        try:
            ...
        except asyncio.CancelledError:
            await workflow.execute_activity("run.stopped", ref, start_to_close_timeout=_SHORT,
                                            retry_policy=_READ_RETRY)
            raise
        finally:
            await workflow.execute_activity("run.release", ref, start_to_close_timeout=_SHORT,
                                            retry_policy=_READ_RETRY)
```

`durable.py`: `await (await self._connect()).get_workflow_handle(f"workflow-run-{run_id}").cancel()`.

Code notes: why the step finishes its current primitive (a click already dispatched cannot be recalled) and why release always runs.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120` and the two integration files.
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro/application backend/src/sro/infrastructure/temporal backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(runs): stopping a Steel run cancels its workflow at the next heartbeat

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## D5: Ask and answer — a waiting run holds nothing (§7.4 "Ask", D4 of the parent spec)

Depends on: D2.

**Files:**
- Modify: `backend/src/sro/application/runtime/run_steps.py` (`_ask` tells the operator; `answered`)
- Create: `backend/src/sro/application/runtime/answer_run.py`
- Modify: `backend/src/sro/application/ports/durable.py`, `backend/src/sro/infrastructure/temporal/durable.py` (`answer_run`)
- Modify: `backend/src/sro/infrastructure/temporal/workflows.py` (`answer` signal; the wait), `activities.py` (`run.answered`)
- Modify: `backend/src/sro/interface/http/v1/routers/workflow_runs.py` (`POST /v1/workflow-runs/{run_id}/answer`), `backend/src/sro/interface/http/schemas.py` (`AnswerRunRequest`)
- Modify: `backend/src/sro/application/chat/from_the_mail.py:293-355` (a reply in the thread of a Steel run that is asking answers it)
- Modify: `backend/src/sro/container.py` (`answer_run()`; `RunSteps` gets `SayWhatHappened`'s `clock` and `ids`)
- Create: `backend/tests/unit/application/runtime/test_asking.py`; modify `backend/tests/integration/test_run_workflow.py`
- Modify: `backend/tests/unit/fakes.py` (`FakeDurableExecution.answer_run` appends `(run_id, question_id, value)` to `answered`), `backend/tests/unit/runtime_support.py` (`asking_steel_run(uow, kind=…)` with question id `QID`; `world.thread_says()` reads the operator's thread)
- Run: `make types`

**Interfaces:**
- Produces:
  - When a step asks: `progress.asking = {id, kind, text}`; the question is said in the operator's thread (`SayWhatHappened(uow, clock, ids).execute(ctx, for_operator=…, text=…, speaker=Speaker.ASSISTANT, decision={"kind": "run_asks", "run_id", "question_id", "asks": kind})`); the workflow runs `run.release` (the tab closes; the lease is left to its other runs or to expire), waits on the signal, runs `run.answered`, then `run.acquire` again and continues from the same step (never from step 0).
  - `RunWorkflow.answer(question_id: str, value: str)` signal.
  - `AnswerRun(uow, durable).execute(ctx, *, run_id, question_id, value) -> None`: the question must be the run's standing one; for `kind == "password"` the value must be empty (the password goes to `PUT /v1/secrets` with the username — S1 — never through a signal); refuses otherwise with `Conflict`.
  - `POST /v1/workflow-runs/{run_id}/answer` body `AnswerRunRequest(question_id: str, value: str = "")` → 202.
  - `RunSteps.answered(ctx, run_id, question_id, value)`: clears `asking`; for `kind == "value"` stores `run.values[asking["name"]] = value`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_question_is_said_to_the_operator_and_the_run_holds_nothing_while_it_waits() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201)])
    world.lanes.ui.answers(StepResult("failed", Lane.UI, fingerprint="f"))
    world.lanes.sight.answers(StepResult("failed", Lane.SIGHT, fingerprint="g"))
    await world.run_steps.acquire(CTX, world.run_id)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.run_steps.release(CTX, world.run_id)

    assert outcome.asking
    assert world.thread_says()[-1]["decision"]["question_id"] == outcome.asking
    assert world.driver.tabs == {}


async def test_a_password_never_travels_in_an_answer() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await asking_steel_run(uow, kind="password")

    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="hunter2")
    await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="")

    assert durable.answered == [(run.id, QID, "")]
```

`test_run_workflow.py`: a stub step that asks once; the workflow runs `run.release`, then after `handle.signal(RunWorkflow.answer, qid, "done")` runs `run.answered` and `run.acquire`, and the next step call finishes.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_asking.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.application.runtime.answer_run'`.

- [ ] **Step 3: Implement**

`RunWorkflow` keeps `self._answers: dict[str, str] = {}` in `__init__`; the step loop becomes:

```python
            while True:
                outcome = await self._step(ref)
                if outcome.asking:
                    await workflow.execute_activity("run.release", ref, start_to_close_timeout=_SHORT,
                                                    retry_policy=_READ_RETRY)
                    await workflow.wait_condition(lambda: outcome.asking in self._answers)
                    await workflow.execute_activity(
                        "run.answered",
                        RunAnswer(ref.tenant_id, ref.principal_id, ref.run_id, outcome.asking,
                                  self._answers[outcome.asking]),
                        start_to_close_timeout=_SHORT, retry_policy=_READ_RETRY)
                    if prepared.browser:
                        await workflow.execute_activity(
                            "run.acquire", ref, start_to_close_timeout=timedelta(seconds=K_STEP_LIMIT_S),
                            retry_policy=_QUEUE_RETRY)
                    continue
                if not outcome.more:
                    break

    @workflow.signal
    def answer(self, question_id: str, value: str) -> None:
        self._answers[question_id] = value
```

```python
# backend/src/sro/application/runtime/answer_run.py
from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.durable import DurableExecution
from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.progress import Progress
from sro.domain.shared.errors import Conflict, NotFound


class AnswerRun:
    def __init__(self, uow: UnitOfWork, durable: DurableExecution) -> None:
        self._uow = uow
        self._durable = durable

    async def execute(self, ctx: RequestContext, *, run_id: str, question_id: str, value: str) -> None:
        async with self._uow as uow:
            run = await uow.workflow_runs.get(ctx.tenant_id, run_id)
        if run is None:
            raise NotFound("no such run")
        asking = Progress.of(run.progress).asking
        if asking.get("id") != question_id:
            raise Conflict("that is not the question this run is waiting on")
        if asking.get("kind") == "password" and value:
            raise Conflict("a password is stored with PUT /v1/secrets, never sent as an answer")
        await self._durable.answer_run(run_id, question_id, value)
```

`durable.py`: `await (await self._connect()).get_workflow_handle(f"workflow-run-{run_id}").signal(RunWorkflow.answer, question_id, value)`. The route (docstring kept, it is under `interface/http`) calls `container.answer_run().execute(...)` and answers 202. `FromTheMail.execute`: when `_answering(ctx, thread)` returns a run with `executor == "steel"` whose progress is asking a `step` or `value` question, call `AnswerRun.execute(ctx, run_id=…, question_id=…, value=said[:K_ANSWER])` (`K_ANSWER = 500`) and `continue`; a password question is never answered from mail.

Code notes: why the lease and tab are released while waiting (a waiting run holds nothing, §7.4), why a password never rides a signal (Temporal history is not a vault).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && cd .. && make types && cd backend && uv run pytest tests/contract -q` and the Temporal integration file.
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/sro backend/tests frontend/openapi.json frontend/src/lib/api/generated.ts docs/code-notes
git commit -m "feat(runs): a run asks, waits holding nothing, and resumes from the same step

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

## D6: A worker restart resumes the run and repeats no write (§5.5 "Worker restart", §7.3, §7.4 "Restart")

Depends on: D2, S8.

Temporal re-dispatches a step whose worker died once its heartbeat times out. The new attempt loads `progress`: a write recorded `sending` is settled by a read-back or asked about, never re-sent; the tab is found again by the lease's session id and the saved target id.

**Files:**
- Modify: `backend/tests/unit/application/runtime/test_run_steps.py`
- Modify: `backend/tests/integration/test_runs_on_local_steel.py` (scenario: a worker restart mid-run with no repeated write)
- Modify: `backend/src/sro/application/runtime/run_steps.py` only if a test fails (the behaviour is D2's; this task proves it end to end)

**Interfaces:**
- Consumes: `Progress.in_doubt` (D1), `ApiLane.read_back` (X5), `SessionBroker.reattach`/`recover` (S7, S8).

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_retried_step_whose_write_went_out_is_settled_not_resent() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201, read_back="/api/customer-types/GT2")])
    await world.mark_sending(order=0)
    world.http.answer(200, '{"name": "GT2"}')

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False
    assert world.lanes.ui.calls == 0
    assert [one["method"] for one in world.http.sent] == ["GET"]


async def test_a_retried_step_with_no_read_back_asks_instead_of_guessing() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201, read_back=None)])
    await world.mark_sending(order=0)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking and world.lanes.ui.calls == 0


async def test_a_restarted_worker_finds_the_run_s_tab_by_its_target_id() -> None:
    world = await steel_run(steps=[type_step_evidence(), save_step_evidence(status=201)])
    await world.run_steps.acquire(CTX, world.run_id)
    tab = Progress.of((await world.saved_run()).progress).tabs["main"]
    world.forget_every_connection()

    await world.run_steps.acquire(CTX, world.run_id)

    assert Progress.of((await world.saved_run()).progress).tabs["main"] == tab
```

Local Steel + Temporal: start a `RunWorkflow` for the rig's two-step job with a worker task; cancel the worker task while the second step's POST is in flight (the rig delays its response on a flag); start a fresh worker; the workflow completes, and `rig.posts == 1`.

- [ ] **Step 2: Run them and see them fail or pass**

Run: `cd backend && uv run pytest tests/unit/application/runtime/test_run_steps.py -q -o faulthandler_timeout=120`
Expected: the tests pass if D2 is right; any failure is fixed in `run_steps.py` (never in the test).

- [ ] **Step 3: Run the end-to-end scenario**

Run (with `make up`): `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_runs_on_local_steel.py -q -o faulthandler_timeout=120 -k restart`
Expected: pass; `rig.posts == 1`.

- [ ] **Step 4: Commit, then LIVE QA**

```bash
git add backend/tests backend/src/sro/application/runtime/run_steps.py
git commit -m "test(runs): a worker restart resumes by target id and repeats no write

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

**LIVE QA: QA-4** and **QA-5** follow (Proof points).

---

# Stream R — rollout and removals (spec §9, §10)

## R1: Shadow on QA, then `greyorange` switches to Steel (§9 steps 1–2)

Depends on: D3.

**Files:**
- Create: `backend/scripts/shadow.py`
- Create: `backend/tests/unit/test_shadow_pairs_verdicts.py`
- Create: `docs/code-notes/backend/scripts/shadow.py.md`
- Modify: `infra/docker-compose.deploy.yml` (rollout step 2: `SRO_STEEL_TENANTS='["greyorange"]'` on api and worker — committed only when the user says to switch)

**Interfaces:**
- Produces: `pair(extension: Sequence[RunStep], steel: Sequence[RunStep]) -> list[tuple[int, str, str, str, bool]]` (step order, says, extension verdict, Steel verdict and lane, agree); the script picks a tenant's last N held extension runs, starts for each a **dry** Steel run (`live=False`: a write step is `withheld`, never sent) of the same job and values through a `StartWorkflowRun` built with that tenant in `steel_tenants`, waits for each, and prints the pairs and an agreement rate.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_shadow_pairs_verdicts.py
from scripts.shadow import pair
from sro.domain.execution.workflow_run import RunStep


def test_steps_pair_by_the_job_step_they_did() -> None:
    extension = [RunStep(order=0, of_step=0, says="Type", verdict="held"),
                 RunStep(order=1, of_step=1, says="Save", verdict="held")]
    steel = [RunStep(order=0, of_step=0, says="Type", verdict="held", verdict_by="ui"),
             RunStep(order=1, of_step=1, says="Save", verdict="withheld", verdict_by="ui")]

    assert pair(extension, steel) == [
        (0, "Type", "held", "held/ui", True),
        (1, "Save", "held", "withheld/ui", True),
    ]
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/unit/test_shadow_pairs_verdicts.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'scripts.shadow'`.

- [ ] **Step 3: Implement**

```python
def pair(
    extension: Sequence[RunStep], steel: Sequence[RunStep]
) -> list[tuple[int, str, str, str, bool]]:
    theirs = {one.of_step: one for one in steel}
    rows = []
    for mine in sorted(extension, key=lambda one: one.of_step):
        other = theirs.get(mine.of_step)
        said = f"{other.verdict}/{other.verdict_by}" if other else "absent"
        agree = other is not None and (other.verdict == mine.verdict or other.verdict == "withheld")
        rows.append((mine.of_step, mine.says, mine.verdict, said, agree))
    return rows
```

plus `main()` (argparse: `--tenant`, `--runs`; builds the container, starts and awaits the dry runs, prints the table). A withheld write agrees by construction: a dry run does not send it.

- [ ] **Step 4: Run it and see it pass**

Run: `cd backend && uv run pytest tests/unit/test_shadow_pairs_verdicts.py -q -o faulthandler_timeout=120`
Expected: `1 passed`.

- [ ] **Step 5: Commit, then LIVE QA (rollout steps 1–2)**

```bash
git add backend/scripts/shadow.py backend/tests/unit/test_shadow_pairs_verdicts.py docs/code-notes/backend/scripts/shadow.py.md
git commit -m "chore(rollout): shadow dry Steel runs beside extension runs and compare verdicts

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

The user runs `python scripts/shadow.py --tenant greyorange --runs 10` on QA and reads the table. On the user's word, set `SRO_STEEL_TENANTS='["greyorange"]'` in the deploy file (its own commit, `chore(rollout): greyorange runs on Steel`); the extension then receives no command for that tenant and keeps capturing.

## R2: Steel is the only executor; the extension stops executing (§9 step 3, §10) — after the POC milestone

Depends on: QA-1 … QA-5 passed (the POC milestone).

**Files:**
- Modify: `new-chrome-extension/src/background/commands.js` (delete the executing kinds: every `ui.*`, `navigate`, `screenshot`, `sign_in`, `tab.open`, `calls.since`, `http.send` handler and their helpers), `service-worker.js` (the command handler), `showing.js` (the in-page driving band) and their tests
- Modify: `new-chrome-extension/src/page/page-code.js` (delete `perform`, `performAt`, `screenSize`, `viewport`, `csrfToken`, `requestedWith`, `send` — extension-only; `resolve`/`act`/`holds`/`hitTest`/`signals` stay, Steel loads them)
- Modify: `backend/src/sro/application/execution/workflow_runs.py` (`StartWorkflowRun`: the extension path — `run_workflow`, `WatchingChannel`, the device checks, `Stops` — deleted; every run is Steel)
- Modify: `backend/src/sro/config.py` (`steel_tenants` deleted), `infra/docker-compose.deploy.yml`
- Modify: `backend/src/sro/interface/http/v1/routers/workflow_runs.py:99-150` (`await starter.perform(...)` instead of `container.pursuits.spawn(...)`), `application/trigger/fire_trigger.py:264-298`, `application/trigger/answer_confirmation.py` (same)
- Modify: `backend/src/sro/application/execution/workflow_runs.py:550-567` (`AbortWorkflowRun` only cancels; `Stops` and `Approvals` leave it)
- Modify: `docs/14-extension-protocol.md` (the command kinds are gone)
- Test: `backend/tests/unit/test_container_wiring.py` (no `SocketChannel` is built for runs), extension test that no command kind is handled, `make test-browser`

**Interfaces:**
- Removes: `Settings.steel_tenants`; the extension's executing command kinds; `StartWorkflowRun`'s extension branch; `pursuits.spawn` on the workflow-run path.
- Keeps: capture (`recorder.generated.js`, `upload.js`, `queue.js`), the panel, `page-code.js`.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/unit/test_container_wiring.py` (its `container` fixture):

```python
def test_no_run_is_ever_sent_to_a_browser_socket(container: Container) -> None:
    starter = container.start_workflow_run()

    assert not hasattr(starter, "_channel")
```

In `new-chrome-extension/src/background/offering-worker.test.mjs` (it already imports `perform` from `./commands.js`):

```js
test("the extension executes no command kind", async () => {
  for (const kind of ["ui.perform", "ui.perform_at", "navigate", "screenshot", "sign_in", "tab.open", "calls.since", "http.send"]) {
    const answer = await perform({ kind, payload: {} });
    assert.equal(answer.ok, false, kind);
    assert.equal(answer.error.kind, "not_actionable", kind);
  }
});
```

- [ ] **Step 2: Run them and see them fail**

Run: `make test-extension; cd backend && uv run pytest tests/unit/test_container_wiring.py -q -o faulthandler_timeout=120`
Expected: FAIL (the kinds are handled; the starter holds a channel).

- [ ] **Step 3: Delete the paths**

Delete, grep every caller first, and edit mixed tests rather than deleting them wholesale (audit wave 1 Task 6's method). `grep -rn "pursuits.spawn(starter" backend/src` and `grep -rn "steel_tenants" backend/src` print nothing afterwards.

- [ ] **Step 4: Run everything**

Run: `make test-extension && make lint-extension && cd backend && uv run pytest tests/unit tests/contract -q -o faulthandler_timeout=120 && uv run pytest tests/browser -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add -A new-chrome-extension/src backend/src backend/tests infra/docker-compose.deploy.yml docs/14-extension-protocol.md docs/code-notes
git commit -m "refactor(runs)!: Steel is the only executor; the extension only watches and asks

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

(`git add -A` on these paths only; never at the repository root — the untracked `designof-panel/` and `docs/21-*.md` are the user's.)

## R3: The old skill engine goes, after its use on QA is counted (§10 last bullet; steel-migration plan C14)

Depends on: R2.

It is still wired: `container.agents()` → `infrastructure/agent/drivers.py` `RemoteAgents`; `application/chat/converse.py` `_answer_now`; skill triggers in `application/trigger/fire_trigger.py`; `interface/http/v1/routers/threads.py:131-179` and `runs.py:73,114` through `Pursuits`; `application/execution/read_runs.py` `StopRun` through `Stops`; and `infrastructure/steel/ui_driver.py` (`container.ui`) with its own resolver (`_resolve`, `_resolve_component`, `_act`) and fixed waits (`wait_for_timeout(1200)` at lines 80 and 140).

**Files:**
- Measure first: `backend/scripts/count_old_engine.py` (new; read-only counts)
- Then, only if every count is zero: delete `application/execution/execute_skill.py`, `self_heal.py`, `pursue_goal.py`, `read_runs.py` (`StopRun`), `stops.py`, `pursuits.py`, `infrastructure/agent/drivers.py` `RemoteAgents`, `infrastructure/steel/ui_driver.py`, `infrastructure/gemini/{intent,interpreter}.py` and the intent resolver, their routes, container factories, tests and code-notes. `infrastructure/gemini/computer_use.py` **stays** — it is the sight lane's `VisionDriver`.

**Interfaces:**
- Produces: `count_old_engine.py` prints the number of `skills` rows, `triggers` rows with a `skill_id`, and old-engine `runs` in the last 30 days.

- [ ] **Step 1: Write the failing test**

```python
def test_the_counts_are_the_three_the_decision_needs() -> None:
    from scripts.count_old_engine import QUERIES

    assert set(QUERIES) == {"skills", "skill_triggers", "runs_30_days"}
```

- [ ] **Step 2: Run it and see it fail**

Run: `cd backend && uv run pytest tests/unit/test_count_old_engine.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement the counter; the user runs it on QA**

```python
QUERIES = {
    "skills": "SELECT count(*) FROM skills",
    "skill_triggers": "SELECT count(*) FROM triggers WHERE skill_id IS NOT NULL",
    "runs_30_days": "SELECT count(*) FROM runs WHERE started_at > now() - interval '30 days'",
}
```

with a `main()` that runs them on a read-only connection and prints JSON. **LIVE QA (user):** `sudo docker compose -f infra/docker-compose.deploy.yml exec -T api python scripts/count_old_engine.py`.

- [ ] **Step 4: Delete, or stop and report**

Any non-zero count: stop and report the counts to the user; nothing is deleted. All zero: delete the list above, grepping every caller first; `uv run lint-imports`, the unit, contract, integration and browser suites, and a container-wiring test asserting nothing constructs `RemoteAgents` or `PlaywrightUiDriver`, all pass.

- [ ] **Step 5: Commit**

```bash
git add backend docs/code-notes
git commit -m "refactor(engine)!: remove the old skill engine and its driver

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

# Proof points (spec §8.4)

Each live QA point is run once by the user on the QA box (`infra/docker-compose.deploy.yml` only). Implementers never drive them (Global Constraint 12).

| # | After | What the user does and sees | Proves |
|---|---|---|---|
| **QA-0** | C0 | Runs `scripts/steel_sessions.py` against the deployed Steel; reads the verdict JSON. | Sessions per container; fixes S4's shape. |
| **QA-1** | D3, R1's switch (`greyorange` in `SRO_STEEL_TENANTS`) | Stores the account password once with `PUT /v1/secrets` and `username` (S1). Presses a mined Blue Yonder job (Create a Customer Type). The run's `workflow_run_steps` show `verdict_by = ui`; the broker signed in through the real identity-provider chain with the vault password (one `ready` lease for the account); `docker compose logs api` shows no command sent to any extension socket. | A mined Blue Yonder job runs on Steel, signed in from the vault, UI lane. |
| **QA-2** | QA-1, X9 | Presses the same job again. The write step's row reads `verdict_by = api`; the run adds no row to `model_spend`. | The job is promoted to the API lane, with no model call. |
| **QA-3** | D3, X6 | Sends a request mail naming the job and its values to the operator's mailbox; touches nothing else. A run starts (`started_by` the operator, `awaiting.thread` the mail's thread); its mail step reads `verdict_by = tool`; the reply is in the Gmail thread. | A mail job replies by mail through the Gmail connector, with no UI. |
| **QA-4** | D2, S7, S8 | Presses two jobs on one account at once: one lease, two target ids, both runs `held`. Then `docker restart` of that account's Steel container and a third press: the lease is new, the state restored, and the identity provider shows no new sign-in. Notes the container's RSS with one and two tabs open. | Two parallel jobs on one account as tabs of one browser; a container restart restores saved state; memory per browser measured (spec §12). |
| **QA-5** | S8, D6 | During a run, signs the account out elsewhere (or lets the session lapse): the run signs back in once and finishes. During another run, `docker compose restart worker` mid-step: the run resumes and the Blue Yonder audit (or a read-back) shows the write once. | Expiry mid-run recovers; a worker restart repeats no write. |
| **POC milestone** | QA-1 … QA-5 all passed | The four acceptance lines of spec §1 hold. R2 may start. | Spec §1 accepted. |

Local proofs (implementer): §8.2 parity suite green (X2); §8.3 scenarios green on local Steel (S7: leases and restore, two tabs; S8: container crash, expiry then re-sign-in; D2: two runs as tabs; D4: stop during a step; D6: worker restart, no repeated write).

# Pre-flight conflict table

| Pair | Shared surface | Ruling |
|---|---|---|
| A0 × E1 × E2 × E3 × E4 × E5 × E6 | `domain/observation/gesture.py`, `application/observation/correlate.py`, `application/capture/rig_wire.py`, `tests/unit/application/test_correlate.py` | Serial in that order; each rebases on the last. |
| E2 × E3 × E4 × E5 | `infrastructure/steel/recorder.js`, `recorder.generated.js`, `src/content/evidence.test.mjs` | Serial. Never hand-merge the generated file: resolve `recorder.js`, then `make gen-recorder`. |
| E4 × S6 | `domain/skill/signing_in.py` | Different functions (`sign_in_chain` vs the new predicates). E4 first; rebase. |
| X1 × X2 × S6 × R2 | `new-chrome-extension/src/page/page-code.js`, `page-code.test.mjs` | X1, then X2, then S6 (`signals`), then R2 (deletes the extension-only methods). |
| X1 × R2 | `new-chrome-extension/src/background/commands.js` | X1 changes injection; R2 deletes the executing kinds. X1 first. |
| S5 × S6 × X4 × S10 × X7 | `infrastructure/steel/driver.py`, `application/ports/page.py`, `FakePageDriver`, `tests/browser/test_the_steel_driver.py` | Serial: S5, S6, X4, S10, X7. Each adds methods; none rewrites another's. |
| S7 × S8 × S10 | `application/runtime/broker.py`, `test_the_broker.py` | Serial. |
| S2 × S9 | `BrowserSessionRepository` (port, SQL, fake) | S2 owns the lease methods including `leased_sessions`; S9 only reads them. |
| S9 × R3 | `application/connection/release_strays.py`, `application/execution/pursuits.py` | S9 removes the `Pursuits` reader; R3 deletes `Pursuits`. |
| X3 → S7, X4 … X9, D2 | *interface:* `LaneContext`, `Held`, `NeedsAPerson`, `Stopped`, `StepLane`, `StepResult`, `Verdict`, `Broken` | Owned by X3; frozen in its review. |
| S5 → S6, S7, S10, X4, X7 | *interface:* `PageDriver`, `SessionRef`, `PageGone` | Owned by S5; later tasks only add methods. |
| S1 → S2, S7, D2 | *interface:* `Account`, `Lease`, `LeaseState`, vault keys | Owned by S1. |
| D1 → D2, D4, D5, D6 | *interface:* `Progress`, `StepMark`, `MAIN`, the step limits | Owned by D1. |
| D2 × D4 × D5 × D6 | `application/runtime/run_steps.py`, `infrastructure/temporal/{workflows,activities,durable}.py`, `ports/durable.py`, `tests/integration/test_run_workflow.py`, `test_run_steps.py` | Serial: D2, D4, D5, D6. |
| D3 × D4 × R2 | `application/execution/workflow_runs.py` (`StartWorkflowRun`, `AbortWorkflowRun`) | Serial: D3, D4, R2. |
| D3 × D5 | `application/chat/from_the_mail.py` | D3 (start) then D5 (answer from a reply). |
| E6 × E7 × S2 × X8 × D1 | `infrastructure/db/models.py`, the Alembic head (`backend/migrations/versions`, head `0072`) | Take the next number at merge, repoint `down_revision`, keep one head. |
| S1 × X1 × D5 | `interface/http/schemas.py`, `frontend/openapi.json`, `frontend/src/lib/api/generated.ts` | Each runs `make types`; regenerate on conflict, never hand-merge. |
| S3 × S4 × S5 × S7 × S9 × X4 … X9 × D2 … D5 × R2 × R3 | `backend/src/sro/container.py` and its code-notes | Each adds or removes one factory or field: merge by union; re-anchor the notes once after R3. |
| S2 … D6 | `backend/tests/unit/fakes.py`, `backend/tests/unit/runtime_support.py` | Additions only; merge by union. |
| S7 × S8 × D2 × D4 × D6 | `backend/tests/integration/test_runs_on_local_steel.py` | One scenario per task, appended; serial. |
| S4 × D3 × R1 × R2 | `infra/docker-compose.deploy.yml` | Different keys (Steel services, `SRO_STEEL_URLS`, `SRO_STEEL_TENANTS`); merge by union. |
| C0 → S4 | *interface:* QA-0's verdict | S4's capacity and variant follow it. |

# Spec coverage

| Spec section | Tasks |
|---|---|
| §1 Goal and acceptance | POC milestone (QA-1 … QA-5); D2, D3, S7, S8, D6 |
| §2 Architecture (worker runs activities; API only starts, stops, answers) | D2, D3, D4, D5 |
| §3 The ladder; API-lane failures; ask after sight; no blind repeats | X3, X8, X5, D2 (`_ask`, settle), D1 (`sending`) |
| §4.1 Keep what is captured | E1 |
| §4.2 Semantic path | E2 |
| §4.3 Frame identity | E3, X4 (`_frame`) |
| §4.4 Click `detail` and `isTrusted` | E4 |
| §4.5 After-state | E5, X3 (`after_matches`), X4 |
| §4.6 Snapshot events kept | E6 |
| §5.1 Layout (container per account; C0) | C0, S4 |
| §5.2 Leases; sweeper; grace timer and in-memory list go | S1, S2, S9 |
| §5.3 Acquire; vault keys with username; 64 KiB | S1, S7 |
| §5.4 Parallel runs as tabs; per-account lock | S3, S7, D2 |
| §5.5 Expiry, re-sign-in, refused credentials, container crash, worker restart | S7 (latch), S8, D5 (panel asks), D6 |
| §5.6 Structural sign-in detection; identity-provider pages captured | S6, E7, E4 (chain) |
| §5.7 Session headers | S10 |
| §6.1 Lanes (tool, API, UI, sight) | X6, X5, X4, X7 |
| §6.2 Verification; unknown writes | X3, X4, X5, X7, D2 |
| §6.3 Each lane teaches the one above; known-broken list | X8, X9 |
| §6.4 Shared page code; strategy order; snapshot repair | X1, X2, S6 |
| §7.1 Start | D3 |
| §7.2 Workflow | D2 |
| §7.3 Progress and idempotency | D1, D2, D6 |
| §7.4 Stop, ask, restart | D4, D5, D6, D1 |
| §7.5 Limits | D1, D2, X7 |
| §8.1 Unit | every task |
| §8.2 Page-code parity | X2 |
| §8.3 Integration on local Steel | S7, S8, D2, D4, D6 |
| §8.4 Live QA | C0 (QA-0), Proof points QA-1 … QA-5 |
| §9 Rollout | D3 (setting), R1 (shadow, switch), R2 (setting removed) |
| §10 Removed when live | X1 (`in-page.js`), S9 (grace timer), R2 (extension execution, `pursuits.spawn`, `Stops` on the run path), R3 (`ui_driver.py`, old engine) |
| §11 Out of scope | nothing planned (live view, service account, shadow DOM, more tenants, design 2/3 work) |
| §12 Risks | QA-0 (C0); QA-4 (restore, memory); X1 CI hash + X2 parity; X2 threshold + write verification (X4); X7 cap and metering; X2 falls back to existing strategies for older evidence |

# Deferred to design 2, "Learning and agents"

From the steel-migration plan's stream A (A0 stays here). No tasks are written for them:

- **A1** One file per prompt (`domain/prompts/`, the `Prompt` record).
- **A2** Evaluation harness, mining and request-reader suites (`backend/evals/`, `make eval`).
- **A3** Tab roles, learned in code (uses A0's `opener_tab_id`); the runtime keeps one tab per run (`MAIN`) until then.
- **A4** Recipe compiler, storage and YAML. Until it lands, "the compiled recipe" the runtime loads is the learned job with its cited evidence, its learned locators, the verified-write ledger and the known-broken list.
- **A5** Compile report, optional-field classes and field limits on the surfaces.
- **A6** Request reader: ranked candidates, the whole thread, untrusted mail.
- **A7** Miner prompt defects and fenced page text.
- **A8** Mail agent guards (the mail body the tool lane sends is written by this agent).
- **A9** Repair eval suite.

Superseded tasks of streams B and C not carried into this plan, and where they belong: B1, B2 (step timing and its console view) and B13–B16 (value sources, thread list, "Not a job", the per-job report) go to design 3 or its measurement work; B12 (a server-side mail poll) is the mail door, design 3 — until then the extension's beat keeps calling `POST /v1/chat/from-the-mail`, and D3 starts the run server-side; B8 (a lock for session-wide steps) is dropped by spec §5.4 (only session changes take the lock); C16 (a live view) is out of scope (§11). B3, B4, B5, B6, B7a/b, B9–B11 and C1–C15 are replaced by the tasks above (C9/C10's `SteelChannel` is not built: the lanes call `PageDriver` directly).
