# Execution Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every mined job runs end to end on a Steel browser on our VM, as a durable Temporal run that walks the tool → API → UI → sight ladder per step; the server reads each operator's mailbox and can take over a job the operator started by hand; and the extension becomes watch-only.

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
| `backend/src/sro/domain/execution/takeover.py` | `Took`, `Takeover`, `take_over`: which of the job's writes the operator's own captured calls prove, and where a takeover run begins | D7 |
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
| `backend/src/sro/application/runtime/teach.py` | `Teach`: known-broken list, mending, sight → locator, UI → API promotion; a confirmed composed field learned into the job | X9, X10 |
| `backend/src/sro/domain/observation/outline.py` | The server's outline rule `outline_kept` (shape, caps, no echo, redaction), `last_outline`, `K_OUTLINE_*`, `K_ECHO_MIN` | E6 |
| `backend/src/sro/domain/execution/compose.py` | `Composed`, `Unplaced`, `Adding`; `compose` (a run value to a field on the write's outline), `keyed` (the save's new body keys to fields), `with_field` (the learned step and optional parameter) | X10 |
| `backend/src/sro/application/runtime/fill_field.py` | `FillField`: a composed or learned field filled on the live page by label, asked when not exactly one, sight as fallback | X10 |
| `backend/src/sro/application/runtime/run_steps.py` | `RunSteps`: the activity bodies (prepare, acquire, step, finish, release, stopped, answered) | D2, D4, D5, D6 |
| `backend/src/sro/application/runtime/answer_run.py` | `AnswerRun` use case: validate an answer and signal the workflow | D5 |
| `backend/src/sro/application/chat/look_lately.py` | `LookInTheMailLately`: the server mail poll, each Steel tenant's operators through the existing mail door | D8 |
| `backend/src/sro/infrastructure/db/locks.py` | `PostgresAccountLocks`: `pg_advisory_lock` on a dedicated connection | S3 |
| `backend/src/sro/infrastructure/steel/pool.py` | `SteelPool`: containers from `steel_urls`, capacity from QA-0 | S4 |
| `backend/src/sro/infrastructure/steel/driver.py` | `SteelDriver`: one CDP connection per session, tabs by target id, page code injected, network log | S5 (grown by S6, S10, X4, X7) |
| `new-chrome-extension/src/page/page-code.js` | The one page-code file, a classic script exposing `globalThis.sroPage` | X1 (grown by S6, X2, E6: `outlineOf`, `sroPage.outline`) |
| `new-chrome-extension/src/page/page-code.test.mjs` | Node self-checks of `page-code.js` (moved from `in-page.test.mjs`) | X1, X2 |
| `backend/tests/unit/runtime_support.py` | Shared builders and doubles for the runtime's unit tests (steps with evidence, scripted drivers and lanes, a run world) | X4 (grown by S7–D6) |
| `backend/tests/browser/steel_rig.py` | Local identity-provider chain (form, redirect, app) and served pages shared by runtime browser/integration tests | S5 |
| `backend/tests/browser/test_the_steel_driver.py` | SteelDriver against served pages over local Chromium CDP | S5, S6, S10, X4, X7 |
| `backend/tests/browser/test_page_code_parity.py` | §8.2 parity suite: extension injection vs `add_init_script` choose the same element | X2 |
| `backend/tests/browser/test_the_screen_outline.py` | Real Chrome: no typed value in any outline sent or kept (show-password, a code box labelled "Verify", mirror div, status mirror, contenteditable, textarea) | E6 |
| `backend/tests/unit/domain/test_composing_a_field.py`, `backend/tests/unit/application/runtime/test_a_field_nobody_showed.py` | Composing, keying, asking, learning a field nobody demonstrated | X10 |
| `backend/tests/integration/test_leases.py` | Lease SQL: unique live lease, beat, expiry | S2 |
| `backend/tests/integration/test_account_locks.py` | Advisory lock excludes a second holder across connections | S3 |
| `backend/tests/integration/test_runs_on_local_steel.py` | §8.3 scenarios against local Steel + Temporal test server | S7, S8, D2, D4, D6, D7 |
| `backend/tests/unit/domain/test_a_takeover.py` | The operator's writes, proven or in doubt; where a takeover begins | D7 |
| `backend/tests/integration/test_mail_is_read_once.py` | The heartbeat look and the server poll, concurrently on Postgres, read one mail once | D8 |
| `new-chrome-extension/src/watch-only.test.mjs` | The extension can load no code that acts on a page or sends a request for a run | R2 |
| `backend/scripts/shadow.py` | Rollout step 1: dry Steel runs beside extension runs, verdicts compared | R1 |
| `backend/migrations/versions/2026xxxx_0074_sign_in_pages_are_watched.py` | Heal stored policies whose `exclude_hosts` is exactly the old default | E7 |
| `backend/migrations/versions/2026xxxx_0075_a_session_is_leased.py` | Lease columns and the one-live-lease index on `browser_sessions` | S2 |
| `backend/migrations/versions/2026xxxx_0076_a_lane_known_broken.py` | `known_broken` table | X8 |
| `backend/migrations/versions/2026xxxx_0077_a_run_keeps_its_progress.py` | `workflow_runs.progress`, `workflow_runs.executor`, the per-device index narrowed to extension runs | D1 |

### Modified

| File | Change | Task |
|---|---|---|
| `new-chrome-extension/src/background/service-worker.js` | `popupEvent`/`pageEvent` carry `opener_tab_id` | A0 |
| `backend/src/sro/application/capture/rig_wire.py` | Wire fields: `opener_tab_id`, `landmarks`, `frame_path`, `detail`, `trusted`, `prior`, `outlines` (`Outline`, `OutlineField`, `OutlineMessage`) | A0, E2–E6 |
| `backend/src/sro/domain/observation/gesture.py` | `PageMark.opener_tab_id`; `Target.bounds/attributes/landmarks`; `Component.chain`; `Action.modifiers/detail/trusted/frame_path/after/outlines`; `Landmark`, `FrameHop`, `AfterState`, `Outline`, `OutlineField`, `OutlineMessage` | A0, E1–E6 |
| `backend/src/sro/application/observation/correlate.py` | `as_action`/`as_mark` keep every captured field; after-state join; outlines carried on their own gesture | A0, E1–E6 |
| `backend/src/sro/infrastructure/steel/recorder.js` (+ generated copy) | `landmarksOf`, `framePathOf`, click `detail`/`isTrusted`, `stateOf` + `prior`; `requiredOf`/`outlineOf` from the readers, `takeOutline`, the `MutationObserver`, `outlines` on each record | E2–E6 |
| `backend/src/sro/domain/skill/signing_in.py` | Enter-submit by `detail == 0`; `PageSignals` and the structural sign-in predicates | E4, S6 |
| `backend/src/sro/application/observation/redact.py` | Outlines kept only through `outline_kept` against the batch's typed values; a `snapshot` event's tree discarded; `_shapes_only` gone | E6 |
| `backend/src/sro/infrastructure/db/evidence.py`, `models.py` | lease columns; `known_broken`; run `progress`/`executor` (E6's outline rides in `gestures.gesture` JSONB: no schema change) | S2, X8, D1 |
| `backend/src/sro/domain/observation/policy.py` | `DEFAULT_EXCLUSIONS = ()` (E7); `capture_snapshots`, `snapshot_max_per_minute`, `reading_structure` deleted (E6; the stored JSONB key is kept and ignored) | E6, E7 |
| `backend/src/sro/interface/http/schemas.py` (policy response), `backend/src/sro/cli/observe.py` | The two snapshot policy fields and `--snapshots`/`--no-snapshots` deleted | E6 |
| `new-chrome-extension/src/background/trees.js`, `trees.test.mjs` | Deleted: tree capture and its `chrome.debugger` attach | E6 |
| `new-chrome-extension/src/background/service-worker.js`, `state.js`, `panel.js`, `pointing.js` (comments), `README.md` | `takeTree`/`takeTreeSoon`/`releaseAll`, `treeTimes` and the tree wording removed | E6 |
| `backend/src/sro/application/ports/repositories.py` | `BrowserSessionRepository` lease methods; `WorkflowRepository` known-broken methods | S2, X8 |
| `backend/src/sro/infrastructure/db/repositories.py`, `workflows.py`, `workflow_runs.py` | SQL for leases, known-broken, progress/executor, `fail_orphans` narrowed | S2, X8, D1 |
| `backend/tests/unit/fakes.py` | Fakes for leases, locks, pool, page driver, known-broken, durable runs | S2–S5, X8, D2, X10 |
| `backend/src/sro/interface/http/v1/routers/secrets.py`, `schemas.py` | Password stored under the account key when a username is given | S1 |
| `backend/src/sro/config.py` | `steel_urls`, `steel_sessions_per_container`, `page_code_path`, `steel_tenants`, `mail_sweep_seconds` | S4, X1, D3, D8 |
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
| `backend/src/sro/application/execution/workflow_runs.py` | `StartWorkflowRun` starts Steel tenants' runs durably, and a takeover with the operator's writes in its first `progress`; `AbortWorkflowRun` cancels them | D3, D4, D7 |
| `backend/src/sro/application/chat/from_the_mail.py` | A sure mail with all required values starts the run (Steel tenants); a cap refusal while starting releases the message's claim; an asked-for aside value rides into the run, and a reply answers a `field` question | D3, D8, X10 |
| `backend/src/sro/infrastructure/temporal/worker.py` | `look_in_the_mail_lately` loop beside the session keeper | D8 |
| `backend/src/sro/application/lookup/run_lookups.py`, `domain/lookup/address.py` (`Address.page`), `routers/ask.py`, `routers/lookups.py`, `application/chat/converse.py`, `schemas.py` (`allow_focus` gone from `LookupRequest`/`AskRequest`) | Lookups read through the broker: the account's session first, then a Steel tab; no `SocketChannel` | L1 |
| `backend/src/sro/interface/http/schemas.py` (`StartWorkflowRunRequest.took_over`), `routers/workflow_runs.py` (pass-through) | The press names the operator's tab and the span its matched gestures cover | D7 |
| `new-chrome-extension/src/background/recognise.js`, `service-worker.js` | `match` returns `since`/`through`; the press flushes the capture queue, then sends `took_over` | D7 |
| `backend/src/sro/interface/http/v1/routers/workflow_runs.py` | `POST /v1/workflow-runs/{id}/answer` | D5 |
| `backend/src/sro/container.py` | Factories for everything above | S3–D5, D8, X10 |
| `backend/src/sro/application/ports/page.py`, `infrastructure/steel/driver.py` | `PageDriver.resolve`, `PageDriver.outline` | X10 |
| `backend/src/sro/application/runtime/ui_lane.py`, `sight_lane.py`, `executor.py`, `step.py`, `domain/execution/lanes.py` | `_same_call` accepts the keys of fields filled this run (`Adding`) and reports them (`StepResult.keyed`); `SightLane.fill`; no API lane for a write that follows a new field; `LaneContext.adding` | X10 |
| `backend/src/sro/domain/execution/progress.py`, `application/runtime/run_steps.py`, `answer_run.py`, `teach.py` | `Progress.composed`; compose at prepare, ask `field` questions, fill before the write, settle by `keyed`, learn at finish | X10 |
| `backend/src/sro/infrastructure/db/workflows.py` (`grew`) | Also moves `known_broken` rows | X10 |
| `backend/tests/browser/steel_rig.py` | A Department select on the Customer Type form, sent only when chosen | X10 |
| `backend/src/sro/interface/http/app.py` | Startup sweep leaves Steel runs alone | D1 |
| `new-chrome-extension/src/background/commands.js`, `channel.js`, `showing.js`, `pointing.js`, `sign-in.js`, `whats-on-screen.js` | Deleted: every executing kind including `http.send` (`httpSend`), the command socket, the driving band | R2 |
| `new-chrome-extension/src/background/service-worker.js`, `api.js`, `looking.js` | The heartbeat's mail call (`lookInTheMail`, `api.fromTheMail`, `offerFromMail`, the throttle) and the command handler removed | R2 |
| `backend/src/sro/infrastructure/steel/ui_driver.py` and the old skill engine | Removed after measurement | R3 |

---

## Streams and order

Six streams, one implementer each, plus the probe that comes first. Within a stream, tasks run in the order listed; a task starts from the latest merged tip.

| Stream | Spec | Tasks |
|---|---|---|
| **—** probe | §5.1, §8 QA-0 | C0 |
| **E** evidence contract | §4, §5.6 (capture), parent §5.4 | A0, E1, E2, E3, E4, E5, E6 (screen outline; replaces the abandoned tree task), E7 |
| **S** session broker and pool | §5 | S1, S2, S3, S4, S5, S6, S7, S8, S9, S10 |
| **X** executors, lanes, page code | §3, §6 | X1, X2, X3, X4, X5, X6, X7, X8, X9, X10 (after D5) |
| **D** durable runs | §7, §2 (mail poll) | D1, D2, D3, D4, D5, D6, D7, D8 |
| **L** lookups | §6.5 | L1 |
| **R** rollout and removals | §9, §10 | R1, R2, R3 |

### Dependency graph

```
C0 (QA-0) ──────────────────────────────► S4
A0 ─┐ (independent)
E1 → E2 → E3 → E4 → E5 → E6 (+X2, S6: page-code readers)        E7 (independent)
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
X3, D3, D5, D6 ──► D7 (takeover) ──► QA-6
D3 ──► D8 (server mail poll) ──► QA-7
S7, S8, S10, X5, X7 ──► L1 (lookups on Steel) ──► QA-8
E6, X4, X7, X8, X9, D5 ──► X10 (a field nobody demonstrated) ──► QA-9 (with D8 for the mail)
X5 + X9 on QA ──► QA-2
D3 → R1 (shadow) ;  QA-1…QA-9 = POC ──► R2 (also after D7, D8, L1, X10) ; R3 measure-first after R2
```

Parallel start (no shared files): **C0, A0, E1, E7, S1, S3, X1, X3, D1**. C0 blocks only S4.

**Interfaces frozen in review** (their owners' reviews are the gate for the consumers):
- `Lease`, `Account` (S1) → S2, S7, D2.
- `PageDriver` + `SessionRef` (S5) → S6, S7, S10, X4, X7.
- `Held`, `NeedsAPerson`, `SessionBroker.acquire/reattach/reauth/headers/release` (S7, S10) → X4, X5, X7, D2.
- `Lane`, `Verdict`, `StepResult`, `Broken`, `LaneContext`, `StepLane` (X3) → X4–X9, D2.
- `Progress`, `StepMark` (D1) → D2, D4–D7.
- `page-code.js` `sroPage` API (X1, X2, S6, E6 `outline`) → S5, X4, X7, X10, parity suite.
- `Outline`, `OutlineField`, `last_outline` (E6) → X10.
- `Adding`, `StepResult.keyed`, `Progress.composed` (X10): additive to the X3 and D1 types.

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

## E6: A screen outline — labels, roles and messages, never a value, no debugger (§4.6)

Depends on: E5 (the `ref`/`prior_of` identity, and `sro:dropped`), and X2 and S6 as merged (`page-code.js` `readers`, spliced into the recorder by `_recorder_script`, `infrastructure/steel/capture.py:44-64`).

**Replaces the first E6.** That task stored the whole accessibility tree (`rt/e6`, 8954f324; the review is in `.superpowers/sdd/2026-09-24-execution-runtime/task-E6-review.md`). The branch is abandoned and never merged. The new task keeps the id E6.

Today the extension attaches `chrome.debugger` to take the tree (`new-chrome-extension/src/background/trees.js`, `takeTreeSoon`), gated by `ObservationPolicy.capture_snapshots` (`domain/observation/policy.py:27`). The service worker enqueues the tree as a separate `snapshot` event after the gesture (`service-worker.js:1692-1699`). The server counts and drops it (`correlate.py:54-55`), after `redact.py:61` `_shapes_only` has already put it in the blob.

This task makes these changes:
- All of that goes.
- The recorder builds a compact outline in the page, with the same reader code that builds labelled ancestors (E2).
- The outline rides on the gesture record it was taken for, so nothing joins by batch position.
- The server enforces the rule itself: shape, caps, no echo of a typed value, and URL and credential-shape redaction.

**Files:**
- Modify: `new-chrome-extension/src/page/page-code.js`. In `readers` (lines 10-141), add `labelOf`, `requiredOf` (moved from `recorder.js:115-124`), `typedOn` and `outlineOf`, and the constants `OUTLINE_OPTIONS`, `OUTLINE_FIELDS`, `OUTLINE_TEXT`, `OUTLINE_MESSAGES` and `ECHO_MIN`. Add them to the returned object and to the destructuring at line 139. On `sroPage` (line 402), add `outline()`.
- Modify: `new-chrome-extension/src/page/page-code.test.mjs`
- Modify: `backend/src/sro/infrastructure/steel/recorder.js`:
  - destructure `requiredOf` and `outlineOf` from `__PAGE_READERS__` (line 47), and delete the local `requiredOf` (lines 115-124);
  - add `takeOutline`, a `MutationObserver`, and `OUTLINES_PER_GESTURE`;
  - `emit` (line 248) adds `outlines`;
  - `sro:dropped` (line 273) also resets `seenOutline`.
- Regenerate: `new-chrome-extension/src/content/recorder.generated.js` with `make gen-recorder`.
- Create: `backend/src/sro/domain/observation/outline.py`. It holds the `K_OUTLINE_*` constants and `K_ECHO_MIN`, `FIELD_ROLES` and `MESSAGE_ROLES`, `outline_kept` and `last_outline`.
- Modify: `backend/src/sro/domain/observation/gesture.py`: add `OutlineField`, `OutlineMessage` and `Outline`, and `Action.outlines`.
- Modify: `backend/src/sro/application/capture/rig_wire.py`: add the `OutlineField`, `OutlineMessage` and `Outline` models, and `Gesture.outlines`.
- Modify: `backend/src/sro/application/observation/correlate.py`: `as_action` carries `outlines`.
- Modify: `backend/src/sro/application/observation/redact.py`:
  - `redact_events` collects the batch's typed values;
  - `_gesture` keeps `outlines` only through `outline_kept`;
  - `_event` drops a `snapshot` event's tree;
  - `_shapes_only` is deleted.
- Modify: `backend/src/sro/domain/observation/policy.py`: delete `capture_snapshots`, `snapshot_max_per_minute` (and its `__post_init__` check) and `reading_structure`.
- Modify: `backend/src/sro/interface/http/schemas.py:1154-1171`: delete the two policy fields. Then run `make types`.
- Modify: `backend/src/sro/cli/observe.py:65,89-91`: delete the `--snapshots` and `--no-snapshots` flags and their output line.
- Delete: `new-chrome-extension/src/background/trees.js` and `trees.test.mjs`.
- Modify: `new-chrome-extension/src/background/service-worker.js`:
  - the `trees.js` import (lines 57-59);
  - `takeTree` and `takeTreeSoon` in the gesture handler (lines 1692-1699, including the comment above them);
  - `releaseAll` on a policy change (lines 3255-3257).
- Modify: `state.js` (`treeTimes`, lines 45 and 325-330).
- Modify: `panel.js` (the `capture_snapshots` wording, lines 835 and 866).
- Modify: `pointing.js` (its comments that name `trees.js`, lines 40-44, 55, 95 and 105). The code is unchanged: R2 deletes the file.
- Modify: `new-chrome-extension/README.md:98`.
- Test:
  - `backend/tests/unit/application/test_correlate.py`;
  - `backend/tests/unit/application/test_the_backend_stores_what_the_browser_sent.py`. The two snapshot-tree tests (lines 267-284 and 337-352) are replaced by the hostile-outline test and the discarded-tree test;
  - `backend/tests/unit/application/test_a_mined_skill_gets_the_same_locators.py:56-80`. The snapshot-policy assertions go, and a stored-policy test comes in;
  - Create: `backend/tests/browser/test_the_screen_outline.py`;
  - `backend/tests/browser/conftest.py:545`, `test_a_gesture_in_a_real_iframe_finds_its_frame_path.py:81` and `test_the_extension_in_a_real_chrome.py`. In each, drop the `capture_snapshots` policy key. Also delete the tree-timing helper at lines 109-120 of the last file and its caller, and reword the docstring at line 1710;
  - `backend/tests/integration/test_evidence_repositories.py`: an outline round trip. The outline is stored inside `gestures.gesture` (JSONB), like every E1–E5 field. There is no migration.

**Interfaces:**
- Produces, in the page, `outlineOf(doc)` and `sroPage.outline()`:

  ```
  {headings: string[], landmarks: [{role, name}], fields: [{role, label, required, options}],
   buttons: string[], messages: [{role, text}]}
  ```

  - `options` is a list of option labels only when the control has at most `OUTLINE_OPTIONS` options. Otherwise it is `null`.
  - `messages[].role` is `alert`, `status` or `invalid`.
  - Every string is dropped when it contains the current value of a text control on the page (`ECHO_MIN` characters or more).
- Produces, on the recorder record: `outlines: Outline[]`. These are the screens outlined since this frame's previous gesture, at most `OUTLINES_PER_GESTURE`. The last one is the screen this gesture was made on, read in the capture phase: the settled state of the previous gesture, the same instant E5 reads `prior`. A screen equal to the last one sent from this frame is not sent again.
- Wire (`rig_wire.py`):
  - `OutlineField(role: str, label: str, required: bool | None = None, options: list[str] | None = None)`;
  - `OutlineMessage(role: str, text: str)`;
  - `Outline(headings, landmarks: list[Landmark], fields, buttons, messages)`;
  - `Gesture.outlines: list[Outline] = []`.
- Domain (`gesture.py`, frozen and slotted):
  - `OutlineField(role: str, label: str, required: bool | None = None, options: tuple[str, ...] | None = None)`;
  - `OutlineMessage(role: str, text: str)`;
  - `Outline(headings: tuple[str, ...] = (), landmarks: tuple[Landmark, ...] = (), fields: tuple[OutlineField, ...] = (), buttons: tuple[str, ...] = (), messages: tuple[OutlineMessage, ...] = ())`;
  - `Action.outlines: tuple[Outline, ...] = ()`.
- Domain (`outline.py`):
  - `outline_kept(raw: object, typed: Collection[str]) -> dict[str, object] | None`. It is the one server rule, applied in `redact_events` before the blob is written and before the batch is parsed, so it holds for both stores.
  - `last_outline(gesture: Gesture, earlier: Sequence[Gesture]) -> Outline | None`. It returns the gesture's own last outline, else the latest outline among earlier gestures on the same `tab_id` and `frame_path`.
- Removes: `ObservationPolicy.capture_snapshots`, `.snapshot_max_per_minute` and `.reading_structure`; the policy response fields; the CLI flags; `trees.js`.
  - **The stored flag.** It is not a column: it is a key inside `observation_policies.policy` (JSONB, `models.py:353-358`). Stored rows keep it, and there is no migration (Global Constraint 7). `load_policy` (`infrastructure/db/codec.py:102`, a `TypeAdapter` over the dataclass) ignores the unknown key. The next `save` writes the policy without it.
  - **An older extension.** It reads `capture_snapshots` as absent, so it takes no tree. If one sends a `snapshot` event anyway, the event is still counted in `snapshots_ignored`, and its tree is removed before the blob is written.
- Consumed by: X10 (`last_outline`, `sroPage.outline()`).

- [ ] **Step 1: Write the failing tests**

Append to `new-chrome-extension/src/page/page-code.test.mjs`. Its loader (`load-sro-page.mjs`) evaluates the file with fake elements and no DOM. So this test pins only the API; the outline's content is proven in real Chrome below:

```js
test("the page code can outline the live screen", () => {
  assert.equal(typeof loadSroPage().outline, "function");
});
```

In `test_correlate.py`:

```python
def test_the_screen_a_gesture_was_made_on_is_stored_with_it() -> None:
    event = copy.deepcopy(GESTURE_TYPE)
    event["gesture"]["outlines"] = [
        {
            "headings": ["New Customer Type"],
            "fields": [{"role": "combobox", "label": "Department", "options": ["Finance"]}],
            "buttons": ["Save"],
        }
    ]

    gestures, _, _, _ = correlate(_batch([event]), TENANT)

    (outline,) = gestures[0].action.outlines
    assert outline.headings == ("New Customer Type",)
    assert outline.fields[0] == OutlineField("combobox", "Department", None, ("Finance",))


def test_a_gesture_without_an_outline_was_made_on_the_last_outlined_screen() -> None:
    first, second, elsewhere = (copy.deepcopy(GESTURE_TYPE) for _ in range(3))
    first["gesture"]["outlines"] = [{"buttons": ["Save"]}]
    second["gesture"]["at"] = first["gesture"]["at"] + 1
    elsewhere["gesture"]["at"] = first["gesture"]["at"] + 2
    elsewhere["gesture"]["frame_path"] = [{"index": 0, "url": "https://wms.example/other"}]

    gestures, _, _, _ = correlate(_batch([first, second, elsewhere]), TENANT)

    assert last_outline(gestures[1], gestures[:1]) == Outline(buttons=("Save",))
    assert last_outline(gestures[2], gestures[:2]) is None
```

The hostile client, in `test_the_backend_stores_what_the_browser_sent.py`. It goes through `IngestObservation`, like the other boundary tests:

```python
_TYPED = "ACME-7731-QX"
_OTP = "483920"


def _hostile_outline() -> list[dict[str, object]]:
    events = _events()
    typed, click = copy.deepcopy(events[1]), copy.deepcopy(events[3])
    typed["gesture"].update(kind="type", value=_TYPED, secret=False)
    typed["gesture"]["target"] = {**typed["gesture"]["target"], "secret": False}
    code = copy.deepcopy(typed)
    code["gesture"].update(value=_OTP, at=typed["gesture"]["at"] + 0.5)
    click["gesture"]["outlines"] = [
        {
            "headings": [f"Editing {_TYPED}", "Customer Types"],
            "landmarks": [{"role": "dialog", "name": f"Code {_OTP}"}, {"role": "form", "name": "New"}],
            "fields": [
                {"role": "textbox", "label": "Verify", "value": _OTP, "required": True},
                {"role": "textbox", "label": f"Note: {_TYPED}"},
                {"role": "gridcell", "label": "Row 4"},
                {"role": "combobox", "label": "Department", "options": ["Finance", _A_JWT]},
                {"role": "combobox", "label": "Carrier", "options": [f"c{i}" for i in range(26)]},
            ],
            "buttons": ["Save", f"Save {_TYPED}"],
            "messages": [
                {"role": "status", "text": "https://wms.example/cb?access_token=live-token"},
                {"role": "alert", "text": "Required field"},
                {"role": "banner", "text": "free page text"},
            ],
            "value": _OTP,
            "text": f"all page text {_TYPED}",
        }
    ]
    return [typed, code, click]


async def test_a_client_that_sends_values_in_an_outline_stores_none_of_them() -> None:
    uow = FakeUnitOfWork()
    blobs = FakeBlobStore()
    await SetObservationPolicy(uow).execute(ACME, policy=ObservationPolicy().enabled())
    registered = await RegisterDevice(uow, FakeClock(), FakeIdFactory()).execute(
        ACME, label="laptop", extension_version="0.1.0"
    )

    stored = await IngestObservation(uow, blobs, FakeClock()).execute(
        ACME,
        device_id=registered.device_id,
        secret=registered.secret,
        batch_id=BatchId("bat_hostile_outline"),
        started_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        ended_at=datetime(2026, 3, 1, 9, 5, tzinfo=UTC),
        mode=CaptureMode.PASSIVE,
        events=_hostile_outline(),
    )

    assert stored.stored_at is not None
    lines = (await blobs.read(stored.stored_at)).decode("utf-8").splitlines()
    written = json.dumps([json.loads(one).get("gesture", {}).get("outlines") for one in lines if one])
    (outline,) = next(
        one.action.outlines for one in uow.gestures.rows.values() if one.action.outlines
    )
    kept = repr(outline)
    for said in (_TYPED, _OTP, _A_JWT, "live-token", "free page text", "all page text", "Row 4"):
        assert said not in written, f"{said!r} reached an outline in the evidence blob"
        assert said not in kept, f"{said!r} reached an outline in the gesture store"
    assert outline.headings == ("Customer Types",)
    assert outline.landmarks == (Landmark("form", "New"),)
    assert [(one.role, one.label, one.options) for one in outline.fields] == [
        ("textbox", "Verify", None),
        ("combobox", "Department", ("Finance",)),
        ("combobox", "Carrier", None),
    ]
    assert outline.buttons == ("Save",)
    assert [one.role for one in outline.messages] == ["alert"]


def test_a_tree_from_an_older_extension_is_discarded_unread() -> None:
    event = {"kind": "snapshot", "snapshot": {"nodes": [{"name": "Service Level"}]}}

    (out,) = redact_events([event])

    assert "snapshot" not in out
```

In `test_a_mined_skill_gets_the_same_locators.py`, the policy tests at lines 56-80 are replaced by:

```python
def test_a_stored_policy_with_the_old_tree_keys_still_loads() -> None:
    stored = {"capture_enabled": True, "capture_snapshots": True, "snapshot_max_per_minute": 20}

    assert load_policy(stored) == ObservationPolicy(capture_enabled=True)
```

The real-Chrome proof. It has the shape of `test_the_state_a_gesture_left.py`: the generated recorder plus `page-code.js` as init scripts, and then the server's own `redact_events` over what the recorder sent:

```python
# backend/tests/browser/test_the_screen_outline.py
"""The screen outline, in a real Chrome: after the operator types, no typed
string is anywhere in an outline the recorder sends or the server keeps."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from sro.application.observation.redact import redact_events
from sro.config import get_settings
from sro.infrastructure.steel.capture import _recorder_script

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><html><body>
<form aria-label="Sign in">
  <h1>Verify it's you</h1>
  <label for="pw">Password</label><input id="pw" type="password">
  <button id="show" type="button" onclick="pw.type = pw.type === 'text' ? 'password' : 'text'">Show</button>
  <label for="code">Verify</label><input id="code" autocomplete="off">
  <div id="mirror"></div>
  <div id="said" role="status"></div>
  <div contenteditable="true" role="textbox" id="note" aria-label="Note"></div>
  <label for="memo">Memo</label><textarea id="memo"></textarea>
  <label for="dept">Department</label>
  <select id="dept"><option>Finance</option><option>Operations</option></select>
  <button id="go" type="button">Save</button>
</form>
<script>
  code.addEventListener("input", () => {
    mirror.textContent = "Code: " + code.value;
    said.textContent = "Checking " + code.value;
  });
</script>
</body></html>"""

PASSWORD = "hunter2-correct-horse"
OTP = "483920"
NOTE = "call the dentist at four"
MEMO = "pallet 77 goes to dock B"


@pytest.fixture
def page() -> Iterator[Any]:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as why:  # pragma: no cover - environment, not logic
            pytest.skip(f"no chromium here: {why}")
        try:
            context = browser.new_context()
            context.add_init_script(
                "window.__sroRecord = (j) => (window.__got = window.__got || []).push(j);"
            )
            context.add_init_script(_recorder_script())
            context.add_init_script(path=get_settings().page_code_path)
            context.route(
                "http://sro.test/**",
                lambda route: route.fulfill(body=PAGE, content_type="text/html"),
            )
            one = context.new_page()
            one.goto("http://sro.test/")
            yield one
        finally:
            browser.close()


def _typed_everything(page: Any) -> list[dict[str, Any]]:
    page.fill("#pw", PASSWORD)
    page.click("#show")
    page.click("#code")
    page.keyboard.type(OTP)
    page.click("#note")
    page.keyboard.type(NOTE)
    page.fill("#memo", MEMO)
    page.select_option("#dept", label="Operations")
    page.click("#go")
    return [json.loads(raw) for raw in page.evaluate("window.__got || []")]


def test_no_typed_value_is_in_any_outline_the_recorder_sends(page: Any) -> None:
    records = _typed_everything(page)

    sent = json.dumps([one.get("outlines") for one in records])
    for typed in (PASSWORD, OTP, NOTE, MEMO):
        assert typed not in sent, f"{typed!r} left the page in an outline"
    assert "Code: " not in sent, "the mirror div is free page text and is never kept"


def test_no_typed_value_is_in_any_outline_the_server_keeps(page: Any) -> None:
    records = _typed_everything(page)
    events = [{"kind": "gesture", "tab_id": 1, "gesture": one} for one in records]

    kept = json.dumps([one["gesture"].get("outlines") for one in redact_events(events)])

    for typed in (PASSWORD, OTP, NOTE, MEMO):
        assert typed not in kept, f"{typed!r} reached the server's copy of an outline"


def test_the_outline_still_says_what_the_screen_asks_for(page: Any) -> None:
    records = _typed_everything(page)

    last = records[-1]["outlines"][-1] if records[-1]["outlines"] else None
    screen = last or next(one["outlines"][-1] for one in reversed(records) if one["outlines"])
    labels = {(one["role"], one["label"]) for one in screen["fields"]}
    assert {("textbox", "Password"), ("textbox", "Verify"), ("textbox", "Memo")} <= labels
    assert ("textbox", "Note") in labels
    dept = next(one for one in screen["fields"] if one["label"] == "Department")
    assert dept["options"] == ["Finance", "Operations"]
    assert screen["headings"] == ["Verify it's you"]
    assert "Save" in screen["buttons"]


def test_a_screen_already_sent_from_this_frame_is_not_sent_again(page: Any) -> None:
    page.click("#go")
    page.click("#go")

    records = [json.loads(raw) for raw in page.evaluate("window.__got || []")]

    assert records[-2]["outlines"] and records[-1]["outlines"] == []


def test_a_dialog_that_appears_is_outlined_before_anyone_acts_on_it(page: Any) -> None:
    page.evaluate(
        """async () => {
          const d = document.createElement('div');
          d.setAttribute('role', 'dialog');
          d.setAttribute('aria-label', 'Confirm delete');
          d.innerHTML = '<button>Delete</button>';
          document.body.append(d);
          await new Promise((settled) => setTimeout(settled, 0));
          d.remove();
        }"""
    )
    page.click("#go")

    records = [json.loads(raw) for raw in page.evaluate("window.__got || []")]
    seen = [screen for screen in records[-1]["outlines"]]
    assert any({"role": "dialog", "name": "Confirm delete"} in one["landmarks"] for one in seen)


def test_steel_reads_the_same_outline_from_the_live_page(page: Any) -> None:
    page.click("#code")
    page.keyboard.type(OTP)

    outline = page.evaluate("globalThis.sroPage.outline()")

    assert {"role": "form", "name": "Sign in"} in outline["landmarks"]
    assert [one for one in outline["fields"] if one["label"] == "Department"] == [
        {"role": "combobox", "label": "Department", "required": None, "options": ["Finance", "Operations"]}
    ]
    assert outline["messages"] == [], "the status only echoes the typed code"
    assert OTP not in json.dumps(outline)
```

The show-password case is the first field: after `#show` the password box is `type=text`, and its value is still never in the outline. The code box labelled "Verify" has `autocomplete="off"` and no credential name, so no name rule could catch it. Only the outline's construction and the echo rule keep its value out. The mirror div and the `role=status` mirror both echo the code.

- [ ] **Step 2: Run them and see them fail**

Run: `cd new-chrome-extension && node --test src/page/page-code.test.mjs`. Expected: FAIL, `'undefined' !== 'function'`.
Run: `cd backend && uv run pytest tests/unit/application/test_correlate.py tests/unit/application/test_the_backend_stores_what_the_browser_sent.py tests/unit/application/test_a_mined_skill_gets_the_same_locators.py -q -o faulthandler_timeout=120`. Expected: FAIL, `ImportError: cannot import name 'OutlineField'`.
Run: `cd backend && uv run pytest tests/browser/test_the_screen_outline.py -q -o faulthandler_timeout=120`. Expected: FAIL, `KeyError: 'outlines'`.

- [ ] **Step 3: Implement**

`page-code.js`, inside `readers` after `settingOf`:

```js
    const OUTLINE_OPTIONS = 25;
    const OUTLINE_FIELDS = 80;
    const OUTLINE_TEXT = 120;
    const OUTLINE_MESSAGES = 10;
    const ECHO_MIN = 3;
    const FIELD_ROLES = ["textbox", "searchbox", "combobox", "listbox", "checkbox", "radio", "switch", "spinbutton", "slider"];
    const labelOf = (el) => {
      const own = ownName(el);
      if (own) return own;
      if (el.labels && el.labels.length) return (el.labels[0].innerText || "").trim().slice(0, MAX_TEXT);
      return (el.getAttribute("placeholder") || el.getAttribute("title") || "").trim().slice(0, MAX_TEXT);
    };
    const requiredOf = (el) => {
      const said = el.getAttribute("aria-required");
      if (said === "true") return true;
      if (said === "false") return false;
      if (el.required === true || el.hasAttribute("required")) return true;
      return /\*\s*$/.test(labelOf(el)) ? true : null;
    };
    const typedOn = (doc) =>
      [...doc.querySelectorAll("input, textarea, [contenteditable]")]
        .map((el) => (el.isContentEditable ? el.innerText : roleOf(el) === "textbox" ? el.value : ""))
        .map((text) => String(text || "").trim().toLowerCase())
        .filter((text) => text.length >= ECHO_MIN);
    const outlineOf = (doc) => {
      const typed = typedOn(doc);
      const say = (text) => {
        const plain = String(text || "").replace(/\s+/g, " ").trim();
        const lower = plain.toLowerCase();
        return plain && !typed.some((one) => lower.includes(one)) ? plain.slice(0, OUTLINE_TEXT) : null;
      };
      const shownIn = (selector) => [...doc.querySelectorAll(selector)].filter((el) => el.getClientRects().length > 0);
      const unique = (texts, cap) => [...new Set(texts.map(say).filter(Boolean))].slice(0, cap);
      const optionsOf = (el) => {
        const owned = el.getAttribute("aria-controls") || el.getAttribute("aria-owns");
        const list = el.tagName === "SELECT" ? [...el.options].map((one) => one.label)
          : roleOf(el) === "listbox" ? [...el.querySelectorAll("[role=option]")].map((one) => one.innerText)
          : owned && doc.getElementById(owned) ? [...doc.getElementById(owned).querySelectorAll("[role=option]")].map((one) => one.innerText)
          : null;
        return list && list.length <= OUTLINE_OPTIONS ? list.map(say).filter(Boolean) : null;
      };
      const fields = shownIn("input, select, textarea, [role]")
        .filter((el) => FIELD_ROLES.includes(roleOf(el)))
        .map((el) => ({ role: roleOf(el), label: say(labelOf(el)), required: requiredOf(el), options: optionsOf(el) }))
        .filter((one) => one.label)
        .slice(0, OUTLINE_FIELDS);
      const invalid = shownIn("[aria-invalid=true]").flatMap((el) =>
        (el.getAttribute("aria-errormessage") || el.getAttribute("aria-describedby") || "")
          .split(/\s+/).map((id) => id && doc.getElementById(id)).filter(Boolean)
          .map((said) => ({ role: "invalid", text: said.innerText })));
      const messages = [
        ...shownIn("[role=alert], [role=status]").map((el) => ({ role: el.getAttribute("role"), text: el.innerText })),
        ...invalid,
      ].map((one) => ({ role: one.role, text: say(one.text) })).filter((one) => one.text).slice(0, OUTLINE_MESSAGES);
      return {
        headings: unique(shownIn("h1, h2, h3, h4, h5, h6, [role=heading]").map((el) => el.innerText), OUTLINE_FIELDS),
        landmarks: shownIn("form, dialog, [role=dialog], [role=alertdialog], [role=form]")
          .map((el) => ({ role: landmarkRole(el), name: say(ownName(el)) }))
          .filter((one) => one.role && one.name),
        fields,
        buttons: unique(shownIn("button, [role=button], input[type=submit], input[type=button]").map(nameOf), OUTLINE_FIELDS),
        messages,
      };
    };
```

Add `labelOf`, `requiredOf` and `outlineOf` to the returned `readers` object and to the destructuring. On `sroPage`, add `outline() { return outlineOf(document); },`.

`recorder.js`:
- Add `requiredOf` and `outlineOf` to the `__PAGE_READERS__` destructuring, and delete the local `requiredOf`. `describe`'s `required: requiredOf(el)` is unchanged.
- After `let lastRef = null;`:

```js
  const OUTLINES_PER_GESTURE = 3;
  const OUTLINED = 'form, dialog, [role=dialog], [role=alertdialog], [role=form], [role=alert], [role=status]';
  let seenOutline = null;
  let outlines = [];
  const takeOutline = () => {
    const taken = JSON.stringify(outlineOf(document));
    if (taken === seenOutline) return;
    seenOutline = taken;
    outlines = [...outlines, JSON.parse(taken)].slice(-OUTLINES_PER_GESTURE);
  };
  const appeared = (change) => {
    const inside = change.target.nodeType === 1 ? change.target : change.target.parentElement;
    if (inside && inside.closest('[role=alert], [role=status]')) return true;
    return [...change.addedNodes].some(
      (node) => node.nodeType === 1 && (node.matches(OUTLINED) || node.querySelector(OUTLINED)),
    );
  };
  new MutationObserver((changes) => {
    if (changes.some(appeared)) takeOutline();
  }).observe(document, { childList: true, subtree: true, characterData: true });
```

- `emit` calls `takeOutline()` first, then sends `outlines` and resets it: `takeOutline(); const sent = outlines; outlines = [];` Then add `outlines: sent,` to the record beside `prior`.
- In the `sro:dropped` listener, beside `last = null;`, add `seenOutline = null;`. When the worker drops a gesture, the outlines it carried are lost. So the next gesture must send its screen again, or the server's last outline for that frame would be stale.

Code notes go in `docs/code-notes/new-chrome-extension/src/page/page-code.js.md` and `…/recorder.js.md`. Cover:
- why labels never come from the control's own text (`innerText` of a contenteditable is the typed text);
- the echo rule, and why `ECHO_MIN` is 3 (shorter values would drop ordinary words). **Ceiling:** a typed value shorter than that is not echo-checked;
- why options are kept only for small lists: a list over the cap is data, not a control's vocabulary;
- why the outline rides on the gesture record. The first E6 joined a separate event by batch position, and that mis-attached it;
- the trigger rules, and the ceiling: the screen after a demonstration's last gesture is not sent.

Then run `make gen-recorder`.

`outline.py`:

```python
# backend/src/sro/domain/observation/outline.py
from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from sro.domain.observation.gesture import Gesture, Outline
from sro.domain.recording.sensitivity import redact_shapes, redact_url

K_OUTLINE_OPTIONS = 25
K_OUTLINE_FIELDS = 80
K_OUTLINE_TEXT = 120
K_OUTLINE_MESSAGES = 10
K_OUTLINES_PER_GESTURE = 3
K_ECHO_MIN = 3

FIELD_ROLES = frozenset(
    {"textbox", "searchbox", "combobox", "listbox", "checkbox", "radio", "switch", "spinbutton", "slider"}
)
MESSAGE_ROLES = frozenset({"alert", "status", "invalid"})
LANDMARK_ROLES = frozenset({"form", "dialog", "alertdialog"})


def _said(raw: object, echoes: Collection[str]) -> str | None:
    if not isinstance(raw, str):
        return None
    plain = " ".join(raw.split())
    lower = plain.lower()
    if not plain or any(one in lower for one in echoes):
        return None
    if redact_shapes(redact_url(plain)) != plain:
        return None
    return plain[:K_OUTLINE_TEXT]


def _items(raw: object) -> list[Mapping[str, object]]:
    return [one for one in raw if isinstance(one, Mapping)] if isinstance(raw, list) else []


def _texts(raw: object, echoes: Collection[str], cap: int) -> list[str]:
    items = raw if isinstance(raw, list) else []
    return [said for one in items[:cap] if (said := _said(one, echoes)) is not None]


def outline_kept(raw: object, typed: Collection[str]) -> dict[str, object] | None:
    if not isinstance(raw, Mapping):
        return None
    echoes = {one.lower() for one in typed if len(one) >= K_ECHO_MIN}
    fields = []
    for one in _items(raw.get("fields"))[:K_OUTLINE_FIELDS]:
        label = _said(one.get("label"), echoes)
        if one.get("role") not in FIELD_ROLES or label is None:
            continue
        options = one.get("options")
        required = one.get("required")
        fields.append(
            {
                "role": one["role"],
                "label": label,
                "required": required if isinstance(required, bool) else None,
                "options": _texts(options, echoes, K_OUTLINE_OPTIONS)
                if isinstance(options, list) and len(options) <= K_OUTLINE_OPTIONS
                else None,
            }
        )
    return {
        "headings": _texts(raw.get("headings"), echoes, K_OUTLINE_FIELDS),
        "landmarks": [
            {"role": one["role"], "name": name}
            for one in _items(raw.get("landmarks"))
            if one.get("role") in LANDMARK_ROLES
            and (name := _said(one.get("name"), echoes)) is not None
        ],
        "fields": fields,
        "buttons": _texts(raw.get("buttons"), echoes, K_OUTLINE_FIELDS),
        "messages": [
            {"role": one["role"], "text": text}
            for one in _items(raw.get("messages"))[:K_OUTLINE_MESSAGES]
            if one.get("role") in MESSAGE_ROLES
            and (text := _said(one.get("text"), echoes)) is not None
        ],
    }


def last_outline(gesture: Gesture, earlier: Sequence[Gesture]) -> Outline | None:
    if gesture.action.outlines:
        return gesture.action.outlines[-1]
    here = (gesture.tab_id, gesture.action.frame_path)
    for one in sorted(earlier, key=lambda one: one.at, reverse=True):
        if (one.tab_id, one.action.frame_path) == here and one.action.outlines:
            return one.action.outlines[-1]
    return None
```

Only the keys above are written out. A `value`, a `text` or any other key the client sent is not copied, so no rule has to name it. A string that URL or credential-shape redaction would change is dropped whole, not kept with a marker. An outline string is vocabulary, and a redacted token carries none.

`redact.py`:

```python
def redact_events(events: Sequence[Event]) -> tuple[Event, ...]:
    made: dict[str, Mapping[str, object]] = {}
    typed: set[str] = set()
    for event in events:
        gesture = event.get("gesture")
        if isinstance(gesture, Mapping):
            if isinstance(gesture.get("ref"), str):
                made[_made(event, gesture, gesture["ref"])] = gesture
            if gesture.get("kind") == "type" and isinstance(gesture.get("value"), str):
                typed.add(gesture["value"])
    return tuple(_event(event, made, typed) for event in events)
```

- `_event` passes `typed` to `_gesture`, and replaces the `snapshot` branch with `out.pop("snapshot", None)`.
- `_gesture` adds:

  ```python
  if "outlines" in out:
      raw = out["outlines"]
      out["outlines"] = [kept for one in (raw if isinstance(raw, list) else [])[-K_OUTLINES_PER_GESTURE:] if (kept := outline_kept(one, typed)) is not None]
  ```

- Delete `_shapes_only`.
- `select` gestures are not in `typed`. A chosen option is the page's own vocabulary, and dropping it would empty the dropdown the outline exists to describe.

`rig_wire.py`: `OutlineField`, `OutlineMessage` and `Outline` as in Interfaces (plain `BaseModel`s; `redact_events` already enforced the content), and `Gesture.outlines: list[Outline] = Field(default_factory=list)`. `gesture.py`: the three frozen dataclasses and `Action.outlines`. `correlate.as_action`:

```python
outlines=tuple(
    Outline(
        headings=tuple(one.headings),
        landmarks=tuple(Landmark(role=mark.role, name=mark.name) for mark in one.landmarks),
        fields=tuple(
            OutlineField(field.role, field.label, field.required,
                         None if field.options is None else tuple(field.options))
            for field in one.fields
        ),
        buttons=tuple(one.buttons),
        messages=tuple(OutlineMessage(said.role, said.text) for said in one.messages),
    )
    for one in wire.outlines
),
```

Deletions:
- Delete `trees.js` and `trees.test.mjs`.
- In `service-worker.js`:
  - delete the import at lines 57-59;
  - delete the block at lines 1692-1698, `const before = takeTree(...)` through `takeTreeSoon(...)`;
  - delete line 3257, `if (!policy?.capture_snapshots) await releaseAll();`, with its comment.
- `state.js`: delete the `treeTimes` key and its two accessors.
- `panel.js:835,866`: delete the tree clause from the capture summary.
- `pointing.js`: delete the sentences that describe sharing the debugger with `trees.js`.
- `README.md:98`: delete the paragraph.
- `policy.py`: delete the two fields, their `__post_init__` entry and `reading_structure`.
- `schemas.py:1154-1155,1170-1171`: delete the fields.
- `cli/observe.py`: delete the flags, the `_apply` branches and line 65.
- Run `make types`.

`test_evidence_repositories.py`: save a gesture whose `action.outlines` holds one `Outline` with a field that has options, then read the same value back from `gestures_for`.

- [ ] **Step 4: Run them and see them pass**

Run: `make gen-recorder && make test-extension && make lint-extension && make types`. Expected: exit 0.
Run: `cd backend && uv run pytest tests/unit tests/contract -q -o faulthandler_timeout=120`. Expected: all pass.
Run: `cd backend && uv run pytest tests/browser/test_the_screen_outline.py tests/browser/test_the_state_a_gesture_left.py tests/browser/test_the_extension_in_a_real_chrome.py tests/browser/test_a_gesture_in_a_real_iframe_finds_its_frame_path.py -q -o faulthandler_timeout=120`. Expected: all pass, 3 runs in a row for `test_the_screen_outline.py` (no flake).
Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_evidence_repositories.py -q -o faulthandler_timeout=120`. Expected: all pass.
Run: `grep -rn "trees.js\|takeTree\|capture_snapshots\|snapshot_max_per_minute\|getFullAXTree" new-chrome-extension/src backend/src/sro/interface backend/src/sro/domain/observation backend/src/sro/application/observation frontend/src --include=*.js --include=*.mjs --include=*.py --include=*.ts --include=*.tsx`. Expected: nothing printed.

- [ ] **Step 5: Commit**

```bash
git add new-chrome-extension backend/src/sro backend/tests frontend/openapi.json frontend/src/lib/api/generated.ts docs/code-notes
git commit -m "feat(evidence): a screen outline replaces tree capture; no value, no debugger

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

## X10: A field nobody demonstrated — composed from the outline, filled on Steel, confirmed by the save's body key, learned (§6.6) — **LIVE QA: QA-9**

Depends on:
- **E6:** the stored outline, `last_outline` and `sroPage.outline()`.
- **X4:** the UI lane and its own-call rule `_same_call`.
- **X7:** the sight lane.
- **X8:** the executor's API-lane offer, and the `known_broken` table that `grew` must move.
- **X9:** `Teach`.
- **D5:** asking and answering. It brings D2's `RunSteps` with it.

**What exists.** Today a name the operator asked for that the job has no parameter for is only recorded:
- `WorkflowRun.unasked` (`domain/execution/workflow_run.py:95`) keeps the names, never the values.
- A mail's value for such a name is `Offered.aside` (`application/chat/from_the_mail.py:71`). It reaches the run's values only when a declared form key places it: `declared_keys` in `application/execution/declared.py:38`, applied in `_told` (`from_the_mail.py:634-651`).

**What this task adds.** A name that no step fills, with a value, is composed into a step from the outline of the form the job saves (E6). It is filled on the live Steel page by its label through the page code, and asked about when the page does not answer it exactly. It counts only when the save's own call carries a new body key for it. On success it is learned into the job as an optional parameter.

**Files:**
- Create: `backend/src/sro/domain/execution/compose.py` (`Composed`, `Unplaced`, `Adding`, `SELECTS`, `normal`, `compose`, `keyed`, `with_field`)
- Create: `backend/src/sro/application/runtime/fill_field.py` (`Filled`, `FillField`)
- Modify: `backend/src/sro/application/ports/page.py` (`PageDriver.resolve`, `PageDriver.outline`)
- Modify: `backend/src/sro/infrastructure/steel/driver.py` (the two methods, through `_frame` and the `_call` wrapper like X4's; `resolve` evaluates `sroPage.resolve`, `outline` evaluates `sroPage.outline`)
- Modify: `backend/src/sro/application/runtime/ui_lane.py`:
  - `_same_call` (line 195) takes an `Adding` and answers `dict[str, str] | None`. The dict maps each parameter name to the key found for it; `None` means the call is not this write's own;
  - `_perform` passes `ctx.adding.get(step.order, Adding())` and puts the keys found on the result.
- Modify: `backend/src/sro/domain/execution/lanes.py` (`StepResult.keyed: Mapping[str, str]`, default empty — additive to X3's frozen type)
- Modify: `backend/src/sro/application/runtime/step.py` (`LaneContext.adding: Mapping[int, Adding]`, default empty)
- Modify: `backend/src/sro/application/runtime/sight_lane.py` (`SightLane.fill(says, write, ctx) -> StepResult`: the same capped, origin-bound loop, for a step that is not a write, whose goal is `says`)
- Modify: `backend/src/sro/application/runtime/executor.py` (a write with `ctx.adding[step.order]` is not offered the API lane)
- Modify: `backend/src/sro/domain/execution/progress.py` (`Progress.composed: list[dict[str, object]]`, additive; `Progress.of` reads it, and a malformed entry raises like every other field)
- Modify: `backend/src/sro/application/runtime/run_steps.py`:
  - `prepare` composes;
  - `step` asks for each unplaced name before step 0, fills a write's composed fields before the write, fills a learned field step by its locator or passes over it when it has no value, and settles each filled field by the write's `keyed`;
  - `finish` learns;
  - `answered` handles `kind == "field"`.
- Modify: `backend/src/sro/application/runtime/answer_run.py` (a `field` answer must be `""` or one of `asking["choices"]`)
- Modify: `backend/src/sro/application/runtime/teach.py` (`Teach.learn_field`)
- Modify: `backend/src/sro/infrastructure/db/workflows.py:472` (`grew` also moves `KnownBrokenRow`, which is keyed by `ord` like the three tables it already moves)
- Modify: `backend/src/sro/application/chat/from_the_mail.py`:
  - the start of a sure mail's run (D3's `_started`) carries `{name: offer.aside[name] for name in offer.unasked if name in offer.aside}` into the run's values; the offer's own `values` win on a clash;
  - a reply may answer a `field` question (D5's reply path).
- Modify: `backend/src/sro/container.py` (`fill_field()`; `run_steps()` gets it)
- Modify: `backend/tests/unit/fakes.py`:
  - `FakePageDriver(resolved=…, outline=…)`, which records `resolved`;
  - `FakeWorkflowRepository.grew` moves known-broken entries.
- Modify: `backend/tests/unit/runtime_support.py`:
  - `scripted_driver(resolved=…, outline=…)`;
  - `lane_context(adding=…)`;
  - `save_step_evidence(outline=…)`;
  - `steel_run(values=…)`, whose world gains `fill` (a `ScriptedFill` with `answers(*filled)`), `progress()`, `job()` and `learned()`.
- Create: `backend/tests/unit/domain/test_composing_a_field.py`
- Create: `backend/tests/unit/application/runtime/test_a_field_nobody_showed.py`
- Modify: `backend/tests/unit/application/runtime/test_the_ui_lane.py`
- Modify: `backend/tests/browser/steel_rig.py`. `_APP_PAGE` (line 36) gains `<label for="dept">Department</label><select id="dept" name="department"><option value=""></option><option>Finance</option><option>Operations</option></select>`, and its save sends `department` only when one is chosen. So a job recorded without touching it records the body keys `{name}`.
- Modify: `backend/tests/browser/test_the_steel_driver.py`, `backend/tests/integration/test_runs_on_local_steel.py`
- Run: `make types` (`AnswerRunRequest` is unchanged; the `asking` payload the panel reads gains `name` and `choices`)

**Interfaces:**
- Consumes: `last_outline`, `Outline`, `OutlineField` (E6); `primary_gesture`, `writes` (`domain/execution/evidence.py`); `is_secret_field` (`domain/recording/sensitivity.py:236`); `body_key_set` and `_parsed` shapes (`domain/observation/trim.py`); `PageDriver.act`/`mark`/`calls_since`/`wait_for` (X4); `SightLane` (X7); `Teach` and `remember_locator` (X9); `WorkflowRepository.grew` (`application/ports/repositories.py:489`); D5's asking and `answered`.
- Produces:
  - `Composed(name: str, label: str, role: str, before: int, options: tuple[str, ...] | None = None)`, whose `.action` is `"select"` for a role in `SELECTS = {"combobox", "listbox"}` and `"type"` otherwise.
  - `Unplaced(name: str, why: Literal["no_field", "ambiguous"], labels: tuple[str, ...] = ())`.
  - `Adding(known: Mapping[str, str] = {}, fresh: Mapping[str, str] = {})`. `known` maps a body key to a parameter, for learned field steps filled this run. `fresh` maps a parameter to its value, for fields composed this run.
  - `compose(workflow, by_id, values) -> tuple[tuple[Composed, ...], tuple[Unplaced, ...]]`. A name is composed when it has a value, no step's `parameters` names it, it is not a credential name, and it equals, after `normal`, exactly one field label on the last outline of exactly one write step's primary gesture.
  - `keyed(extra: Mapping[str, str], adding: Adding) -> dict[str, str] | None`. `extra` is the save's body keys that the recorded body lacks, each with its value as sent. Known keys are named first. Then each fresh field takes the key whose value equals its own, compared with `casefold`. One field and one key left over pair up. More extra keys than `known` plus `fresh` can explain means the call is not this write's own: `None`.
  - `with_field(workflow, field, *, key, value) -> tuple[Workflow, dict[int, int]]`. It inserts `Step(order=field.before, says=f"Fill {label}", system=<the write's>, parameters=[name])`, and shifts each later step's `order`, its `uses` and the `repeat` bounds by one. It appends `{"name", "required": False, "seen_values": [value], "names": [label], "key": key}` to `parameters`.
  - `PageDriver.resolve(session, target_id, payload) -> PageAnswer`, where `candidates` is the count found. `PageDriver.outline(session, target_id, frame_path) -> Mapping[str, object] | None`.
  - `Filled(lane: Lane | None, asks: Literal["", "no_field", "ambiguous", "no_option"] = "", options: tuple[str, ...] = (), learned: Mapping[str, str] = {}, detail: str = "")`.
  - `FillField(driver, sight: SightLane | None, *, wait_s=K_UI_WAIT_S).fill(field, value, write, ctx, *, learned: LearnedStep | None = None) -> Filled`. The payload is `{action, value, write: False, target: {role, name: label, landmarks: <the write's primary target landmarks>}, frame_path: <the write's>, learned}`. The steps:
    1. `resolve`: 0 found → `no_field`; more than 1 → `ambiguous`.
    2. For a select, the live outline's options for that label. When it lists options and none equals the value after `normal` → `no_option`, with those options.
    3. `act`, then `wait_for` its pin with `expect.value`.
    4. If the act is refused or the value does not hold → `sight.fill(f"Set {label} to {value}", write, ctx)`.
    5. It never acts on a resolve that is not exactly one control.
  - `StepResult.keyed`; `LaneContext.adding`; `Progress.composed` entries `{name, label, role, before, options, lane, verdict, key}`.
  - A `field` question: `asking = {id, kind: "field", name, text, choices}`. `choices` are the labels (`no_field`, `ambiguous`) or the options (`no_option`). The answer is one of `choices`, or `""` to leave the value out.
  - `Teach.learn_field(ctx, workflow, field, *, key, value, learned, run_id) -> None`: `grew` with `with_field`'s result, then `remember_locator(LearnedStep(field.before, strategy, query, found_by))`. `found_by` is `"composed"` from the UI lane and `"sight"` from sight.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/domain/test_composing_a_field.py
from dataclasses import replace

from sro.domain.execution.compose import Adding, Composed, compose, keyed, with_field
from sro.domain.observation.gesture import Gesture, Outline, OutlineField
from sro.domain.skill.workflow import Workflow
from tests.unit.runtime_support import save_step


def _job(*fields: OutlineField) -> tuple[Workflow, dict[str, Gesture]]:
    step, by_id = save_step(status=201)
    save = by_id["ges_save"]
    by_id["ges_save"] = replace(save, action=replace(save.action, outlines=(Outline(fields=fields),)))
    job = Workflow(id="wf_ct", tenant="acme", title="Create Customer Type", narrative="", steps=[step])
    return job, by_id


def test_a_value_the_job_never_filled_is_composed_before_the_write_whose_screen_names_it() -> None:
    job, by_id = _job(
        OutlineField("textbox", "Customer Type *", True),
        OutlineField("combobox", "Department", None, ("Finance", "Operations")),
    )

    composed, unplaced = compose(job, by_id, {"department": "Finance"})

    assert composed == (
        Composed("department", "Department", "combobox", job.steps[0].order, ("Finance", "Operations")),
    )
    assert unplaced == ()
    assert composed[0].action == "select"


def test_a_name_no_field_has_or_two_fields_have_is_asked_never_guessed() -> None:
    job, by_id = _job(OutlineField("combobox", "Department"), OutlineField("textbox", "Department"))

    _, twice = compose(job, by_id, {"Department": "Finance"})
    _, nowhere = compose(job, by_id, {"Cost centre": "CC-9"})

    assert [one.why for one in twice] == ["ambiguous"]
    assert [one.why for one in nowhere] == ["no_field"]
    assert nowhere[0].labels == ("Department",)


def test_a_credential_or_a_name_a_step_already_fills_is_never_composed() -> None:
    job, by_id = _job(OutlineField("textbox", "Password"), OutlineField("textbox", "Customer Type"))
    job.steps[0].parameters = ["Customer Type"]

    assert compose(job, by_id, {"Password": "hunter2", "Customer Type": "GT2"}) == ((), ())


def test_the_new_key_is_found_by_its_value_or_as_the_only_one_left() -> None:
    two = Adding(fresh={"Department": "Finance", "Region": "North"})

    assert keyed({"department": "Finance", "regionId": "7"}, two) == {
        "Department": "department",
        "Region": "regionId",
    }
    assert keyed({"deptId": "3", "regionId": "7"}, two) == {}
    assert keyed({"a": "1", "b": "2", "c": "3"}, two) is None
    assert keyed({"department": "3"}, Adding(known={"department": "Department"})) == {
        "Department": "department"
    }
    assert keyed({}, Adding()) == {}


def test_learning_the_field_puts_its_step_before_the_write_and_keeps_it_optional() -> None:
    job, _ = _job(OutlineField("combobox", "Department"))
    write = job.steps[0].order

    grown, moved = with_field(
        job, Composed("department", "Department", "combobox", write), key="department", value="Finance"
    )

    assert [(one.order, one.parameters, one.cites) for one in grown.steps] == [
        (write, ["department"], []),
        (write + 1, [], ["ges_save"]),
    ]
    assert moved == {write: write + 1}
    assert grown.parameters[-1] == {
        "name": "department",
        "required": False,
        "seen_values": ["Finance"],
        "names": ["Department"],
        "key": "department",
    }
```

In `test_the_ui_lane.py`:

```python
def _saved(body: str) -> SeenCall:
    return SeenCall("POST", "https://wms.example/api/customer-types", 201,
                    request_body=body, request_content_type="application/json")


async def test_the_save_call_that_carries_the_new_field_keys_it() -> None:
    step, by_id = save_step(status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json"))
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"),
                             calls=[_saved('{"name": "GT9", "department": "Operations"}')])
    ctx = lane_context(by_id, adding={step.order: Adding(fresh={"department": "Operations"})})

    result = await UiLane(driver).execute(step, {}, ctx)

    assert result.verdict == "done"
    assert dict(result.keyed) == {"department": "department"}


async def test_a_save_call_without_the_new_field_is_done_and_keys_nothing() -> None:
    step, by_id = save_step(status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json"))
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"),
                             calls=[_saved('{"name": "GT9"}')])
    ctx = lane_context(by_id, adding={step.order: Adding(fresh={"department": "Operations"})})

    result = await UiLane(driver).execute(step, {}, ctx)

    assert (result.verdict, dict(result.keyed)) == ("done", {})


async def test_more_new_keys_than_fields_filled_is_not_this_writes_own_call() -> None:
    step, by_id = save_step(status=201, body=Body(text='{"name": "GT1"}', mime_type="application/json"))
    driver = scripted_driver(answer=PageAnswer(ok=True, matched_by="component"),
                             calls=[_saved('{"name": "GT9", "department": "Operations", "owner": "x"}')])
    ctx = lane_context(by_id, adding={step.order: Adding(fresh={"department": "Operations"})})

    result = await UiLane(driver).execute(step, {}, ctx)

    assert result.verdict == "unknown"
```

`test_the_ui_lane.py` imports `Adding` from `sro.domain.execution.compose` and `Body` from `sro.domain.observation.gesture`.

```python
# backend/tests/unit/application/runtime/test_a_field_nobody_showed.py
import asyncio

import pytest

from sro.application.ports.page import PageAnswer
from sro.application.runtime.fill_field import Filled, FillField
from sro.domain.execution.compose import Composed
from sro.domain.execution.lanes import Lane, StepResult
from sro.domain.observation.gesture import Outline, OutlineField
from tests.unit.runtime_support import (
    CTX, lane_context, save_step, save_step_evidence, scripted_driver, steel_run,
)

DEPARTMENT = OutlineField("combobox", "Department", None, ("Finance", "Operations"))


class RecordingSight:
    def __init__(self, result: StepResult) -> None:
        self.result = result
        self.said: list[str] = []

    async def fill(self, says, write, ctx) -> StepResult:  # type: ignore[no-untyped-def]
        self.said.append(says)
        return self.result


def _field(write_order: int) -> Composed:
    return Composed("department", "Department", "combobox", write_order, ("Finance", "Operations"))


async def test_a_field_found_once_by_its_label_is_selected_and_holds() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1),
        answer=PageAnswer(ok=True, matched_by="within_role_name", pin="p1"),
        outline={"fields": [{"role": "combobox", "label": "Department", "options": ["Finance", "Operations"]}]},
        holds=True,
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(_field(write.order), "Operations", write, lane_context(by_id))

    assert (filled.lane, filled.asks) == (Lane.UI, "")
    assert dict(filled.learned) == {"strategy": "role_and_name", "query": "combobox|Department"}
    assert driver.acted[-1]["action"] == "select"
    assert driver.acted[-1]["write"] is False
    assert driver.acted[-1]["target"]["name"] == "Department"


@pytest.mark.parametrize(("found", "asks"), [(0, "no_field"), (2, "ambiguous")])
async def test_a_label_missing_or_twice_on_the_live_page_is_asked(found: int, asks: str) -> None:
    driver = scripted_driver(resolved=PageAnswer(ok=found > 0, candidates=found))
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(_field(write.order), "Finance", write, lane_context(by_id))

    assert filled.asks == asks
    assert driver.acted == []


async def test_a_dropdown_without_the_option_is_asked_with_the_options_it_has() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1),
        outline={"fields": [{"role": "combobox", "label": "Department", "options": ["Finance", "Operations"]}]},
    )
    write, by_id = save_step(status=201)

    filled = await FillField(driver, None).fill(_field(write.order), "Legal", write, lane_context(by_id))

    assert (filled.asks, filled.options) == ("no_option", ("Finance", "Operations"))
    assert driver.acted == []


async def test_a_control_that_will_not_take_the_value_falls_back_to_sight() -> None:
    driver = scripted_driver(
        resolved=PageAnswer(ok=True, candidates=1),
        answer=PageAnswer(ok=False, error_kind="not_actionable"),
        outline={"fields": []},
    )
    sight = RecordingSight(StepResult("done", Lane.SIGHT, learned={"strategy": "xpath", "query": "/html/body/select[1]"}))
    write, by_id = save_step(status=201)

    filled = await FillField(driver, sight).fill(_field(write.order), "Finance", write, lane_context(by_id))

    assert (filled.lane, dict(filled.learned)) == (Lane.SIGHT, {"strategy": "xpath", "query": "/html/body/select[1]"})
    assert sight.said == ["Set Department to Finance"]


async def test_a_value_with_no_field_on_the_form_is_asked_before_any_step_runs() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201, outline=Outline())], values={"department": "Finance"})
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.asking
    asking = world.progress().asking
    assert (asking["kind"], asking["name"]) == ("field", "department")
    assert world.lanes.ui.calls == 0


async def test_leaving_the_field_out_drops_the_value_and_names_it_unasked() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201, outline=Outline())], values={"department": "Finance"})
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)
    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    await world.run_steps.answered(CTX, world.run_id, outcome.asking, "")

    run = await world.saved_run()
    assert "department" not in run.values
    assert run.unasked == ["department"]


async def test_a_field_the_save_call_carried_is_done_and_learned_into_the_job() -> None:
    world = await steel_run(
        steps=[save_step_evidence(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "Finance"},
    )
    world.fill.answers(Filled(Lane.UI, learned={"strategy": "role_and_name", "query": "combobox|Department"}))
    world.lanes.ui.answers(StepResult("done", Lane.UI, keyed={"department": "department"}))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.run_steps.finish(CTX, world.run_id)

    (field,) = world.progress().composed
    assert (field["lane"], field["verdict"], field["key"]) == ("ui", "done", "department")
    job = await world.job()
    assert job.steps[0].parameters == ["department"]
    assert job.parameters[-1]["key"] == "department"
    assert [(one.strategy, one.found_by) for one in await world.learned()] == [("role_and_name", "composed")]


async def test_a_field_the_save_call_did_not_carry_is_unknown_and_not_learned() -> None:
    world = await steel_run(
        steps=[save_step_evidence(status=201, outline=Outline(fields=(DEPARTMENT,)))],
        values={"department": "Finance"},
    )
    world.fill.answers(Filled(Lane.UI, learned={"strategy": "role_and_name", "query": "combobox|Department"}))
    world.lanes.ui.answers(StepResult("done", Lane.UI))
    await world.run_steps.prepare(CTX, world.run_id)
    await world.run_steps.acquire(CTX, world.run_id)

    await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())
    await world.run_steps.finish(CTX, world.run_id)

    (field,) = world.progress().composed
    assert field["verdict"] == "unknown"
    assert [one.parameters for one in (await world.job()).steps] == [[]]
```

Browser (`test_the_steel_driver.py`, against `rig.url("/app")` signed in): `resolve` with `{"target": {"role": "combobox", "name": "Department", "landmarks": [{"role": "form", "name": "Customer Type"}]}}` answers `candidates == 1`; `outline(session, tab, [])` lists `Department` with options `["Finance", "Operations"]` (the empty option has no label and is dropped); one `connect_over_cdp` for both.

Integration (`test_runs_on_local_steel.py`, scenario "a field nobody demonstrated"):
1. A job recorded on the rig by typing a Customer Type and pressing Save. It never touches Department, so its recorded body keys are `{name}`.
2. It runs with `{"Customer Type": "GT9", "department": "Operations"}`. `rig.saved[-1] == {"name": "GT9", "department": "Operations"}`. The run's `progress.composed[0]` is `lane = ui, verdict = done, key = department`. The job now has the step "Fill Department" and the optional parameter.
3. A second run with `{"Customer Type": "GT10", "department": "Finance"}` fills Department from the learned locator, composes nothing, and `rig.saved[-1]["department"] == "Finance"`.
4. A third run with `{"Customer Type": "GT11"}` passes over the learned step, and `"department" not in rig.saved[-1]`.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_composing_a_field.py tests/unit/application/runtime/test_a_field_nobody_showed.py tests/unit/application/runtime/test_the_ui_lane.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.domain.execution.compose'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/domain/execution/compose.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Literal

from sro.domain.execution.evidence import primary_gesture, writes
from sro.domain.observation.gesture import Gesture, OutlineField
from sro.domain.observation.outline import last_outline
from sro.domain.recording.sensitivity import is_secret_field
from sro.domain.skill.repeats import Repeat
from sro.domain.skill.workflow import Step, Workflow

SELECTS = frozenset({"combobox", "listbox"})


@dataclass(frozen=True, slots=True)
class Composed:
    name: str
    label: str
    role: str
    before: int
    options: tuple[str, ...] | None = None

    @property
    def action(self) -> str:
        return "select" if self.role in SELECTS else "type"


@dataclass(frozen=True, slots=True)
class Unplaced:
    name: str
    why: Literal["no_field", "ambiguous"]
    labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Adding:
    known: Mapping[str, str] = field(default_factory=dict)
    fresh: Mapping[str, str] = field(default_factory=dict)


def normal(label: str) -> str:
    return " ".join(label.replace("*", " ").split()).casefold()


def _screens(
    workflow: Workflow, by_id: Mapping[str, Gesture]
) -> list[tuple[Step, tuple[OutlineField, ...]]]:
    gestures = sorted(by_id.values(), key=lambda one: one.at)
    found: list[tuple[Step, tuple[OutlineField, ...]]] = []
    for step in sorted(workflow.steps, key=lambda one: one.order):
        primary = primary_gesture(step, by_id)
        if primary is None or not writes(step, by_id):
            continue
        outline = last_outline(primary, [one for one in gestures if one.at < primary.at])
        if outline is not None:
            found.append((step, outline.fields))
    return found


def compose(
    workflow: Workflow, by_id: Mapping[str, Gesture], values: Mapping[str, str]
) -> tuple[tuple[Composed, ...], tuple[Unplaced, ...]]:
    filled = {name for step in workflow.steps for name in step.parameters}
    screens = _screens(workflow, by_id)
    labels = tuple(dict.fromkeys(one.label for _, fields in screens for one in fields))
    composed: list[Composed] = []
    unplaced: list[Unplaced] = []
    for name, value in values.items():
        if name in filled or not value.strip() or is_secret_field(name):
            continue
        hits = [
            (step, one) for step, fields in screens for one in fields if normal(one.label) == normal(name)
        ]
        if len(hits) == 1:
            step, one = hits[0]
            composed.append(Composed(name, one.label, one.role, step.order, one.options))
        else:
            unplaced.append(Unplaced(name, "ambiguous" if hits else "no_field", labels))
    return tuple(composed), tuple(unplaced)


def keyed(extra: Mapping[str, str], adding: Adding) -> dict[str, str] | None:
    found = {adding.known[key]: key for key in extra if key in adding.known}
    rest = {key: said for key, said in extra.items() if key not in adding.known}
    if len(rest) > len(adding.fresh):
        return None
    for name, value in adding.fresh.items():
        key = next((key for key, said in rest.items() if said.casefold() == value.casefold()), None)
        if key is not None:
            found[name] = key
            del rest[key]
    left = [name for name in adding.fresh if name not in found]
    if len(left) == 1 and len(rest) == 1:
        found[left[0]] = next(iter(rest))
    return found


def with_field(
    workflow: Workflow, composed: Composed, *, key: str, value: str
) -> tuple[Workflow, dict[int, int]]:
    moved = {
        step.order: step.order + 1 if step.order >= composed.before else step.order
        for step in workflow.steps
    }
    system = next((one.system for one in workflow.steps if one.order == composed.before), None)
    steps = [
        replace(step, order=moved[step.order], uses=[moved.get(one, one) for one in step.uses])
        for step in workflow.steps
    ]
    steps.append(
        Step(order=composed.before, says=f"Fill {composed.label}", system=system, parameters=[composed.name])
    )
    repeat = workflow.repeat
    if repeat is not None:
        repeat = Repeat(moved.get(repeat.first_step, repeat.first_step), moved.get(repeat.last_step, repeat.last_step))
    parameter: dict[str, object] = {
        "name": composed.name,
        "required": False,
        "seen_values": [value],
        "names": [composed.label],
        "key": key,
    }
    grown = replace(
        workflow,
        steps=sorted(steps, key=lambda one: one.order),
        parameters=[*workflow.parameters, parameter],
        repeat=repeat,
    )
    return grown, moved
```

The rest, in order:

- **`ui_lane.py`.**
  - `_same_call(seen, recorded, adding) -> dict[str, str] | None`. It keeps the frame, method, path-shape and host checks. Then:
    - `wanted is None`: answer `{}` (own call, no key knowable);
    - the seen key set is missing any wanted key: `None`;
    - otherwise the extra keys, with their values from the parsed body, go to `keyed(extra, adding)`.
  - In `_perform`, `own` becomes the calls whose `_same_call` is not `None`, and the first own call's mapping becomes `StepResult.keyed` on the write's result.
  - Existing tests pass `Adding()` implicitly, through `ctx.adding`'s empty default.
- **`fill_field.py`.** `FillField.fill` builds the payload in Interfaces from the write's `primary_gesture`, with its `target.landmarks` and `frame_path`. Then:
  1. `resolve`; answer `Filled(None, asks=…)` unless `candidates == 1`.
  2. For `field.action == "select"`, read `outline` and find the entry whose `normal(label)` matches. If it has an `options` list and none matches the value after `normal`, answer `Filled(None, "no_option", options=tuple(options))`.
  3. `act`, then `wait_for` with `{**payload, "pin": answer.pin, "expect": {"value": value}}`.
  4. If it holds, answer `Filled(Lane.UI, learned={"strategy": "role_and_name", "query": f"{field.role}|{field.label}"})`, or the given `learned` locator when one was passed. A learned field step passes its `LearnedStep` as `payload["learned"]`, the way X4 does.
  5. If the act is refused or the value does not hold, and a sight lane exists, call `sight.fill(f"Set {field.label} to {value}", write, ctx)`. A non-failed result answers `Filled(Lane.SIGHT, learned=result.learned)`.
  6. Otherwise answer `Filled(None, detail=…)`.
  - A failed fill (lane `None`, no `asks`) asks the operator as D5's ordinary step question.
- **`sight_lane.py`.** Factor the loop out of `execute` into `_drive(goal, home, writing, ctx)`. `fill` calls it with `goal=says`, `home` taken from the write's primary gesture, and `writing=False`.
- **`executor.py`.** `api = api and not ctx.adding.get(step.order)`.
- **`run_steps.py`.**
  - `prepare` runs `compose(job, by_id, run.values)`. It stores the composed fields in `progress.composed`, with `lane`, `verdict` and `key` empty, and the unplaced ones as pending questions.
  - `step`, while any unplaced name is unanswered: before step 0 runs, ask one `field` question per name (D5's `_ask`, `choices = labels`).
  - `step`, at a write step `k`:
    1. Fill every `progress.composed` entry with `before == k` through `FillField` before the write's lanes run. A fill that `asks` becomes the question, with `choices = options` or `labels`, and the write is not started.
    2. Record the fill as `lane = <lane>, verdict = "unknown"`.
    3. Pass `ctx.adding[k] = Adding(known=…, fresh={name: value})`.
    4. After the write, each field filled for it takes `verdict = "done"` and `key = result.keyed[name]` when the write is `done` and its name is in `keyed`. Otherwise it stays `unknown`, or becomes `failed` when the write failed.
  - `step`, at a learned field step (no `cites`, one parameter): with no value, pass over it with no mark and no `RunStep` row. With a value, fill it through `FillField` with its learned locator, record it `unknown`, and add its parameter's `key` to the next write's `Adding.known`. That write's `keyed` settles it the same way.
  - `finish` calls `Teach.learn_field` for each composed field that is `done`.
  - `answered` handles `kind == "field"`. `""` drops the value from `run.values` and appends the name to `run.unasked`. A label re-runs `compose` for that name against that label only. An option replaces the value.
- **`answer_run.py`.** A `field` answer is refused with `Conflict` unless it is `""` or in `asking["choices"]`.
- **`teach.py`.** `learn_field` as in Interfaces, in one unit of work.
- **`workflows.py`.** `grew`'s `keyed_by_ord` adds `KnownBrokenRow`.
- **`from_the_mail.py`.** Carry the asked-for aside values into the started run, as in Files. A `field` question can be answered from a reply the way D5 answers `value`: `said[:K_ANSWER]`, validated by `AnswerRun`.

Code notes cover:
- the exact-label rule and why wording is design 2's;
- why a write that follows a new field skips the API lane (the replay template cannot carry the key; design 2's recipe compiler). **Ceiling**, with the upgrade path;
- the `keyed` pairing rules;
- why a fill alone never confirms anything (§6.2);
- **Ceiling:** a later mining pass that grows the job re-derives its steps from demonstrations. `where_steps_moved` gives a step with no cites no place, so the learned step is dropped. Its parameter stays, and the next run with that value composes it again from the outline.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit tests/contract -q -o faulthandler_timeout=120`
Run: `cd backend && uv run pytest tests/browser/test_the_steel_driver.py -q -o faulthandler_timeout=120`
Run: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_runs_on_local_steel.py tests/integration/test_workflow_repositories.py -q -o faulthandler_timeout=120`
Expected: all pass. The worker must restart for this to be live: `run_steps` is an activity.

- [ ] **Step 5: LIVE QA (QA-9, the user runs it)** — see Proof points.

- [ ] **Step 6: Commit**

```bash
git add backend/src/sro backend/tests frontend/openapi.json frontend/src/lib/api/generated.ts docs/code-notes
git commit -m "feat(runtime): fill a field nobody demonstrated, confirm it by the save's key, learn it

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

## D7: Mid-job takeover — Steel finishes a job the operator started, and sends none of their writes again (§7.6)

Depends on: X3 (`SeenCall`, `write_confirmed`), D3, D5, D6.

The recognition half exists and stays in the extension. `recognise.js` `match` finds the one job the operator's last gestures are a unique prefix of, `covered` says how far in they are (`k`), and `valuesFrom` reads what they typed. The press (`service-worker.js` `start-rig-run`, ~line 2141) sends `matched: nudge.k` and the values to `POST /v1/workflow-runs` (`routers/workflow_runs.py:123-137`), and `StartWorkflowRun.execute` turns `matched` into a step with `resumes_at` (`application/execution/workflow_runs.py:189-190`; `domain/skill/shape.py:52,89,93` — `cited_pairs`, `walkable`, `resumes_at`). The extension's run then carries on in the operator's own tab. A Steel tab is fresh, so what the operator already did must be read from evidence.

The evidence half has no seam today: nothing on the server reads an operator's progress inside a job. What exists: uploaded gestures carry `stream_id` = the device (`correlate.py:54`), `tab_id`, `at` and their joined network calls (`domain/observation/gesture.py:72-110`), stored at upload (`ingest.py:162-177`) and read by time (`GestureRepository.gestures_for(tenant, after=, before=)`, `ports/repositories.py:308`). The recorded writes are `recorded_call`/`writes` (`domain/execution/evidence.py:137,164`) with `expected_statuses` (`domain/execution/belts.py:73`), and X3's `write_confirmed` is the one rule for "the page's own call matches the recorded write" (the rule `verify.py:211` `by_what_the_page_called` applies today). Only the extension's tail knows which gestures belong to this doing, so the press sends their span (`took_over`).

A write the evidence cannot prove is recorded in doubt, and D2's `step` already settles doubt: a read-back (X5 `ApiLane.read_back`), else a question (D5). D5 as written clears a `step` question without settling the mark it asked about, so `step` would ask again forever; this task closes that for D6's doubts too.

**Files:**
- Create: `backend/src/sro/domain/execution/takeover.py`
- Create: `backend/tests/unit/domain/test_a_takeover.py`
- Modify: `backend/src/sro/application/execution/workflow_runs.py:128-230` (`StartWorkflowRun.execute(took_over=…)`: a Steel takeover is inserted with its first `progress`)
- Modify: `backend/src/sro/interface/http/schemas.py` (`TookOverModel`; `StartWorkflowRunRequest.took_over`), `backend/src/sro/interface/http/v1/routers/workflow_runs.py:123-137` (pass it through)
- Modify: `backend/src/sro/application/runtime/run_steps.py` (`prepare`: the start page is the first browser step at or after `progress.step`; `step`: the already-written branch keeps the mark's lane as text, because `operator` is not a `Lane`; `answered`: a `step` answer settles the mark it was about)
- Modify: `backend/src/sro/application/runtime/answer_run.py` (a `step` answer is `done` or `redo`)
- Modify: `backend/tests/unit/runtime_support.py` (`SAVE_URL`; `two_writes_job(uow, workflow_id)` — type, save, type, save, each save citing a gesture with `POST SAVE_URL` → 201; `operator_did(uow, *, device, tab, at, calls)` saves one uploaded gesture from that browser tab carrying those calls; `steel_run(..., progress=None)` seeds the run's first `progress`; `type_step_evidence(page=…)`)
- Modify: `backend/tests/unit/application/rig/test_start_workflow_run.py`, `backend/tests/unit/application/runtime/test_run_steps.py`, `backend/tests/unit/application/runtime/test_asking.py`
- Modify: `backend/tests/integration/test_runs_on_local_steel.py` (scenario: a takeover after the operator's own save)
- Modify: `new-chrome-extension/src/background/recognise.js` (`match` returns `since`, `through`), `recognise.test.mjs`
- Modify: `new-chrome-extension/src/background/service-worker.js` (a nudge made from a match keeps `since` and `through`; `start-rig-run` awaits `flushQueue()`, then sends `took_over`)
- Run: `make types`

**Interfaces:**
- Consumes: `SeenCall`, `write_confirmed` (X3); `Progress.sending/settle/written/in_doubt`, `record_progress` (D1 as merged: a `done` mark is immutable; `settle(..., never_left=True)` clears a `sending` mark); `cited_pairs`, `walkable`, `resumes_at`, `recorded_call`, `writes`, `expected_statuses` (existing); D2's in-doubt branch; D5's `answer` signal.
- Produces:
  - `OPERATOR = "operator"` — the lane recorded for a write the operator made.
  - `Took(tab_id: int, since: float, through: float)` — the operator's tab and the recorder times of the first and last gesture the match used; `InvariantViolation` when `since > through`.
  - `Takeover(replay_from: int, done: tuple[int, ...] = (), in_doubt: tuple[int, ...] = ())` — `replay_from` indexes the job's steps ordered by `order`; `.progress() -> Progress` (`step = replay_from`; each `done` order `sending` then `settle(lane=OPERATOR, verdict="done")`; each `in_doubt` order `sending`).
  - `take_over(workflow, by_id, *, matched: int, took: Took, seen: Sequence[Gesture]) -> Takeover`. A write step counts only when the gesture that made its recorded call is among the first `matched` walkable entries (what the operator has reached). It is `done` when uploads reach `took.through` on that tab and `write_confirmed` over that tab's calls in `[since, …]` says `done`; otherwise it is in doubt. `replay_from` is one past the last `done` write that precedes every doubt, else 0.
  - `StartWorkflowRun.execute(..., took_over: Took | None = None)`: for a Steel run with `matched` and `took_over`, it reads the gestures after `took.since` whose `stream_id` is the pressing device, inserts the run with `progress = take_over(...).progress().as_json()`, and checks `unperformable` from the replay step. Extension runs ignore it.
  - Wire: `StartWorkflowRunRequest.took_over: TookOverModel | None = None`; `TookOverModel(tab_id: StrictInt = Field(ge=0), since: float = Field(ge=0), through: float = Field(ge=0))`.
  - Extension: `match(...)` also returns `since` and `through`.
  - `AnswerRun`: a `step` question's value is `done` or `redo`, else `Conflict`. `RunSteps.answered` for it: `done` → `settle(order, lane=OPERATOR, verdict="done")`; `redo` → `settle(order, lane=OPERATOR, verdict="failed", never_left=True)`, so the step runs.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/domain/test_a_takeover.py
from sro.domain.execution.takeover import OPERATOR, Takeover, Took, take_over
from sro.domain.observation.gesture import Action, Call, Gesture
from sro.domain.skill.workflow import Step, Workflow

APP = "https://wms.example/app"
SAVE = "https://wms.example/api/customer-types"
TOOK = Took(tab_id=7, since=90.0, through=100.0)


def gesture(gid: str, at: float, kind: str, *, calls: tuple[Call, ...] = (),
            stream: str = "rec", tab: int = 1) -> Gesture:
    return Gesture(id=gid, tenant="t", stream_id=stream, batch_id="b", at=at, url=APP, system=APP,
                   tab_id=tab, frame_url=None, action=Action(kind=kind, at=at), requests=list(calls))


def job() -> tuple[Workflow, dict[str, Gesture]]:
    recorded = [
        gesture("g0", 1.0, "input"),
        gesture("g1", 2.0, "click", calls=(Call("POST", SAVE, started_at=2.0, status=201),)),
        gesture("g2", 3.0, "input"),
        gesture("g3", 4.0, "click", calls=(Call("POST", SAVE, started_at=4.0, status=201),)),
    ]
    steps = [Step(order=n, says=f"s{n}", system=APP, cites=[f"g{n}"]) for n in range(4)]
    return Workflow(id="wfl", tenant="t", title="Two saves", narrative="n", steps=steps), {
        one.id: one for one in recorded
    }


def operator_saved(at: float, *, status: int | None = 201, tab: int = 7) -> Gesture:
    return gesture(f"op{at}", at, "click", stream="dev-1", tab=tab,
                   calls=(Call("POST", SAVE, started_at=at, status=status),))


def test_a_save_the_operator_s_own_call_confirms_is_done_and_the_run_begins_after_it() -> None:
    workflow, by_id = job()

    took = take_over(workflow, by_id, matched=3, took=TOOK, seen=[operator_saved(100.0)])

    assert took == Takeover(replay_from=2, done=(1,), in_doubt=())


def test_a_form_the_operator_only_filled_is_replayed_from_the_start() -> None:
    workflow, by_id = job()
    typed = gesture("t", 95.0, "input", stream="dev-1", tab=7)

    took = take_over(workflow, by_id, matched=1, took=Took(7, 90.0, 95.0), seen=[typed])

    assert took == Takeover(replay_from=0)


def test_a_save_not_yet_uploaded_is_in_doubt_never_assumed() -> None:
    workflow, by_id = job()

    took = take_over(workflow, by_id, matched=3, took=Took(7, 90.0, 105.0), seen=[operator_saved(100.0)])

    assert took == Takeover(replay_from=0, in_doubt=(1,))


def test_a_refused_or_unanswered_save_is_in_doubt() -> None:
    workflow, by_id = job()

    for status in (409, None):
        took = take_over(workflow, by_id, matched=3, took=TOOK, seen=[operator_saved(100.0, status=status)])
        assert (took.done, took.in_doubt) == ((), (1,)), status


def test_another_tab_s_save_proves_nothing() -> None:
    workflow, by_id = job()

    took = take_over(workflow, by_id, matched=3, took=TOOK, seen=[operator_saved(100.0, tab=8)])

    assert took.in_doubt == (1,)


def test_a_takeover_s_progress_never_sends_the_operator_s_write_again() -> None:
    progress = Takeover(replay_from=2, done=(1,), in_doubt=(3,)).progress()

    assert progress.step == 2
    assert progress.written(1) and progress.marks[1].lane == OPERATOR
    assert progress.in_doubt(3)
    progress.settle(1, lane="ui", verdict="failed")
    assert progress.written(1)
```

In `test_start_workflow_run.py`:

```python
async def test_a_takeover_starts_after_the_operator_s_own_save() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await two_writes_job(uow, "wfl_two")
    await operator_did(uow, device="dev-1", tab=7, at=100.0, calls=[("POST", SAVE_URL, 201)])
    starter = _starter(uow, durable=durable, steel_tenants=frozenset({TENANT.value}))

    run = await starter.execute(
        CTX, workflow_id="wfl_two", device_id=DeviceId("dev-1"), values={"Customer Type": "GT2"},
        live=True, allow_focus=False, matched=3, took_over=Took(tab_id=7, since=90.0, through=100.0),
    )

    progress = Progress.of(run.progress)
    assert progress.step == 2 and progress.written(1)


async def test_another_browser_s_save_is_not_the_operator_s() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    await two_writes_job(uow, "wfl_two")
    await operator_did(uow, device="dev-2", tab=7, at=100.0, calls=[("POST", SAVE_URL, 201)])
    starter = _starter(uow, durable=durable, steel_tenants=frozenset({TENANT.value}))

    run = await starter.execute(
        CTX, workflow_id="wfl_two", device_id=DeviceId("dev-1"), values={"Customer Type": "GT2"},
        live=True, allow_focus=False, matched=3, took_over=Took(tab_id=7, since=90.0, through=100.0),
    )

    assert Progress.of(run.progress).in_doubt(1)
```

In `test_run_steps.py`:

```python
FORM = "https://wms.example/app/customer-types/new"


async def test_a_taken_over_run_skips_the_operator_s_save_and_replays_only_what_leads_on() -> None:
    world = await steel_run(
        steps=[type_step_evidence(), save_step_evidence(status=201),
               type_step_evidence(page=FORM), save_step_evidence(status=201)],
        progress=Takeover(replay_from=2, done=(1,)).progress(),
    )
    world.lanes.ui.answers(StepResult("done", Lane.UI), StepResult("done", Lane.UI))

    while (await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())).more:
        pass

    assert world.lanes.ui.calls == 2
    assert Progress.of((await world.saved_run()).progress).marks[1].lane == OPERATOR


async def test_a_write_the_operator_made_is_passed_over_as_theirs() -> None:
    world = await steel_run(steps=[save_step_evidence(status=201)],
                            progress=Takeover(replay_from=0, done=(0,)).progress())

    outcome = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

    assert outcome.more is False and world.lanes.ui.calls == 0
    assert (await world.saved_run()).steps[-1].verdict_by == OPERATOR


async def test_a_takeover_opens_steel_on_the_page_of_its_first_replayed_step() -> None:
    world = await steel_run(
        steps=[type_step_evidence(), save_step_evidence(status=201),
               type_step_evidence(page=FORM), save_step_evidence(status=201)],
        progress=Takeover(replay_from=2, done=(1,)).progress(),
    )

    await world.run_steps.prepare(CTX, world.run_id)

    assert Progress.of((await world.saved_run()).progress).start_url == FORM
```

In `test_asking.py`:

```python
async def test_a_step_question_is_answered_done_or_redo() -> None:
    uow, durable = FakeUnitOfWork(), FakeDurableExecution()
    run = await asking_steel_run(uow, kind="step")

    with pytest.raises(Conflict):
        await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="maybe")
    await AnswerRun(uow, durable).execute(CTX, run_id=run.id, question_id=QID, value="redo")

    assert durable.answered == [(run.id, QID, "redo")]


async def test_done_settles_a_doubt_and_redo_lets_the_write_run() -> None:
    for value, written in (("done", True), ("redo", False)):
        world = await steel_run(steps=[save_step_evidence(status=201, read_back=None)])
        await world.mark_sending(order=0)
        asked = await world.run_steps.step(CTX, world.run_id, stop=asyncio.Event())

        await world.run_steps.answered(CTX, world.run_id, asked.asking, value)

        progress = Progress.of((await world.saved_run()).progress)
        assert (progress.written(0), progress.in_doubt(0)) == (written, False), value
```

In `recognise.test.mjs`:

```js
test("a match says when the gestures it used began and ended, so a takeover reads only this doing", () => {
  let tail = tailWith([], typed("wm.workAreas.code", "NEWTESTS", { at: 100 }));
  tail = tailWith(tail, { triple: [H, "grid|Customers", "click"], value: null, secret: false, at: 101 });
  tail = tailWith(tail, typed("wm.workAreas.desc", "north dock", { at: 102 }));

  const got = match(tail, [workArea]);

  assert.equal(got.since, 100);
  assert.equal(got.through, 102);
});
```

Local Steel (`test_runs_on_local_steel.py`): the rig's two-save job; the test makes the first save itself (`rig.posts == 1`) and stores the gesture carrying that POST on device `dev-1`, tab 7; a Steel run is started with `matched` past that save and `took_over` spanning it; the run completes, `rig.posts == 2`, and the run's first `workflow_run_steps` row is the second form's typing.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_a_takeover.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.domain.execution.takeover'`.
Run: `make test-extension`
Expected: FAIL in `recognise.test.mjs`: `undefined !== 100`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/domain/execution/takeover.py
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sro.domain.execution.belts import expected_statuses
from sro.domain.execution.evidence import recorded_call, writes
from sro.domain.execution.lanes import SeenCall, write_confirmed
from sro.domain.execution.progress import Progress
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.shape import cited_pairs, walkable
from sro.domain.skill.workflow import Step, Workflow

OPERATOR = "operator"


@dataclass(frozen=True, slots=True)
class Took:
    tab_id: int
    since: float
    through: float

    def __post_init__(self) -> None:
        if self.since > self.through:
            raise InvariantViolation("a takeover's gestures cannot end before they begin")


@dataclass(frozen=True, slots=True)
class Takeover:
    replay_from: int
    done: tuple[int, ...] = ()
    in_doubt: tuple[int, ...] = ()

    def progress(self) -> Progress:
        progress = Progress(step=self.replay_from)
        for order in self.done:
            progress.sending(order)
            progress.settle(order, lane=OPERATOR, verdict="done")
        for order in self.in_doubt:
            progress.sending(order)
        return progress


def take_over(
    workflow: Workflow, by_id: Mapping[str, Gesture], *, matched: int, took: Took,
    seen: Sequence[Gesture],
) -> Takeover:
    reached = {gesture.id for gesture, _ in walkable(cited_pairs(workflow, by_id))[:matched]}
    theirs = [one for one in seen if one.tab_id == took.tab_id and one.at >= took.since]
    uploaded = any(one.at >= took.through for one in theirs)
    calls = [SeenCall(call.method, call.url, call.status) for one in theirs for call in one.requests]
    ordered = sorted(workflow.steps, key=lambda step: step.order)
    done: list[int] = []
    doubt: list[int] = []
    for step in ordered:
        writer = _writer(step, by_id)
        if writer is None or writer.id not in reached:
            continue
        verdict = (
            write_confirmed(recorded=recorded_call(step, by_id),
                            wanted=expected_statuses(step, by_id), calls=calls)
            if uploaded else None
        )
        (done if verdict == "done" else doubt).append(step.order)
    before_doubt = [order for order in done if all(order < one for one in doubt)]
    replay_from = (
        1 + next(n for n, step in enumerate(ordered) if step.order == max(before_doubt))
        if before_doubt else 0
    )
    return Takeover(replay_from, tuple(done), tuple(doubt))


def _writer(step: Step, by_id: Mapping[str, Gesture]) -> Gesture | None:
    if not writes(step, by_id):
        return None
    call = recorded_call(step, by_id)
    return next(
        (by_id[one] for one in step.cites if one in by_id and call in by_id[one].requests), None
    )
```

`StartWorkflowRun.execute`, after `from_step` is resolved and only when `steel and took_over is not None and matched`:

```python
            seen = [one for one in await uow.gestures.gestures_for(ctx.tenant_id, after=took_over.since)
                    if one.stream_id == device_id.value]
            took = take_over(workflow, by_id, matched=matched, took=took_over, seen=seen)
            first_progress = took.progress().as_json()
            check_from = sorted(workflow.steps, key=lambda s: s.order)[took.replay_from].order
```

`unperformable(workflow, by_id, from_step=check_from)` replaces the `from_step` check for a takeover (the replayed steps must be performable too), and the `WorkflowRun` is built with `progress=first_progress`. The router passes `took_over=Took(**body.took_over.model_dump()) if body.took_over else None`.

`RunSteps.prepare`: `browser = [s for s in ordered[progress.step:] if …]` in place of the whole job, so the start page and the account are those of the first step still to run. `RunSteps.step`, already-written branch: `StepResult` is built with the lane only when the mark's lane is a `Lane` value; otherwise the `RunStep` row is written with `verdict="held"`, `verdict_by=planned_by=` the mark's lane (`operator`) and reason "done by the operator before the takeover". `RunSteps.answered` and `AnswerRun` as in the interfaces; the step order comes from the standing question D5 records.

`recognise.js` `match`, in the returned object: `const used = [...best.at.values()];` then `since: tail[Math.min(...used)].at, through: tail[Math.max(...used)].at`. `service-worker.js`: the nudge made from a match keeps `since` and `through`; in `start-rig-run`, before `api.rigStart`, `await flushQueue();` and the body gains
`took_over: nudge.tabId != null && nudge.since != null ? { tab_id: nudge.tabId, since: nudge.since, through: nudge.through } : undefined`.
A mail offer has no `since`, so it sends none.

Code notes: why a write counts only when its recorded call's gesture was reached (a typed-but-unsaved form is not a save); why the uploads must reach `through` before anything is `done` (an upload still on its way is not evidence of absence); why a refusal is doubt and not "not written" (a 409 can mean the record exists); why the replay starts after the last proven write (the steps before it fed that write, and replaying them would leave a second unsaved form); why the operator's tab is never touched.

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && cd .. && make types && make test-extension && make lint-extension && cd backend && uv run pytest tests/contract -q`
Run (with `make up`): `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_runs_on_local_steel.py -q -o faulthandler_timeout=120 -k takeover`
Expected: all pass; the takeover scenario ends with `rig.posts == 2`.

- [ ] **Step 5: Commit, then LIVE QA**

```bash
git add backend/src/sro backend/tests new-chrome-extension/src/background/recognise.js new-chrome-extension/src/background/recognise.test.mjs new-chrome-extension/src/background/service-worker.js frontend/openapi.json frontend/src/lib/api/generated.ts docs/code-notes
git commit -m "feat(runs): Steel takes over a job mid-way and never repeats the operator's own writes

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

A code change is live only after the worker restarts (the activities changed). **LIVE QA: QA-6** follows (Proof points).

## D8: The server reads each operator's mailbox; with the heartbeat look beside it, no mail is read twice (§2 "Mail poll", §9 step 2)

Depends on: D3.

Today a mailbox is read only when the extension's `sro-heartbeat` alarm (`service-worker.js:158-200`) calls `lookInTheMail` (`:2808`) → `api.fromTheMail` (`api.js:230`) → `POST /v1/chat/from-the-mail` (`routers/chat.py:86-104`) → `FromTheMail.execute` (`application/chat/from_the_mail.py:112`). The pieces the poll needs are already there:

- **Once per message.** `_first_time` (`from_the_mail.py:592-603`) claims `mail:{principal}:{message}` through `uow.tool_calls.remember`, an insert with `on_conflict_do_nothing` on `(tenant_id, idempotency_key)` (`infrastructure/db/repositories.py:844-870`). Two callers racing on one message get one `True`.
- **Cap.** `over_cap` runs before the mailbox or the model is touched (`:118-126`); an `OverCap` inside the loop releases the current claim (`_forget`, `:260-270`). The asker is `Metered` (`infrastructure/gemini/metered.py`, audit wave Task 5): it checks the cap per call, records spend, and refuses a call with no tenant in `whose()` (`Unattributed`).
- **Recurring work.** Platform sweeps are worker loops — `keep_sessions_open`, `mine_the_rig_lately`, `retain_lately` (`infrastructure/temporal/worker.py:31-95`) — each tenant run under `whose.about` (`mine_lately.py:99`, `keep_open.py:47`). Temporal schedules exist only for operators' triggers (`temporal/schedules.py`); `cli/read_cron.py` is a one-shot CLI. The poll is a loop.
- **Whose mailbox.** The Gmail grant is per operator (`connector_key`, `domain/execution/secrets.py:39`, read by `McpToolCaller._bearer`), and nothing lists who holds one. The operators with a registered, unrevoked browser (`uow.devices.list_for_tenant`) are the ones whose heartbeat reads mail today; one who never connected Gmail answers `NotConnected`, which the door turns into a sentence at no model cost.

Two gaps close here:

1. A request missing values reaches the operator today only as a card the extension builds from the look's answer (`offerFromMail`, `service-worker.js:725`). With no browser asking, the poll turns it into a `needs_values` question in the operator's thread with `AskAboutTheOffer` (`application/chat/about_an_offer.py:65`). The panel draws that question, and the heartbeat's `lookForAQuestion` finds it.
2. D3's `_started` runs after the loop, outside its `except OverCap`. A cap refusal from `StartWorkflowRun.execute` (`workflow_runs.py:148`) would leave the message claimed and the request lost. Each offer whose start the cap refuses now has its claim released and is dropped from the answer.

Only tenants on Steel are polled. For an extension tenant, `_started` returns a sure, complete request unchanged, and only the extension turns it into a card. A poll that claimed it would lose it. R2 removes the gate together with the setting.

**Files:**
- Create: `backend/src/sro/application/chat/look_lately.py`
- Modify: `backend/src/sro/application/chat/from_the_mail.py` (the `_started` pass: an `OverCap` releases that message's claim and drops the offer)
- Modify: `backend/src/sro/infrastructure/temporal/worker.py` (`look_in_the_mail_lately`, started and cancelled beside `keeper`)
- Modify: `backend/src/sro/config.py` (`mail_sweep_seconds: float = 60.0`; `0` turns the poll off)
- Modify: `backend/src/sro/container.py` (`look_in_the_mail_lately()`)
- Modify: `backend/tests/unit/application/rig/test_from_the_mail.py` (`_Reads.tenants` records `whose().get("tenant")` on each call; D3's `mail_world` gains a registered browser for `CTX.principal_id`, a capture batch for the tenant, `start_refuses: Exception | None = None`, `world.start` and `world.poll`; `EVERY_VALUE`)
- Create: `backend/tests/integration/test_mail_is_read_once.py`

**Interfaces:**
- Consumes: `FromTheMail.execute`; `StartWorkflowRun.runs_on_steel` and `FromTheMail._started` (D3); `AskAboutTheOffer.execute(ctx, pending, *, about, mail_thread)`; `uow.gestures.tenants_since`; `uow.devices.list_for_tenant`; `whose.about`.
- Produces: `LookInTheMailLately(uow, look: FromTheMail, asks: AskAboutTheOffer, start: StartWorkflowRun).execute() -> dict[str, LookedInTheMail]`, keyed `"{tenant}/{principal}"`; `Settings.mail_sweep_seconds`; `worker.look_in_the_mail_lately(container, every_seconds)`.

- [ ] **Step 1: Write the failing tests**

In `test_from_the_mail.py`:

```python
EVERY_VALUE = {"Customer Type": "GT2", "Customer Type Description": "north dock"}


async def test_the_poll_reads_as_each_operator_and_starts_a_sure_complete_request() -> None:
    world = mail_world(sure=True, values=EVERY_VALUE, steel=True)

    await world.poll.execute()

    assert {who for who, _, _ in world.mailbox.asked} == {CTX.principal_id.value}
    assert len(world.durable.runs_started) == 1


async def test_a_mail_the_heartbeat_already_read_is_not_read_again_by_the_poll() -> None:
    world = mail_world(sure=True, values=EVERY_VALUE, steel=True)

    await world.from_the_mail.execute(CTX)
    await world.poll.execute()

    assert len(world.reads.saw) == 1
    assert len(world.durable.runs_started) == 1


async def test_a_request_missing_a_value_becomes_a_question_in_the_operator_s_thread() -> None:
    world = mail_world(sure=True, values={"Customer Type": "GT2"}, steel=True)

    await world.poll.execute()

    last = (await _thread(world.uow)).messages[-1]
    assert last.decision["kind"] == NEEDS
    assert last.decision["missing"] == ["Customer Type Description"]
    assert world.durable.runs_started == []


async def test_the_poll_leaves_an_extension_tenant_s_mail_to_its_browser() -> None:
    world = mail_world(sure=True, values=EVERY_VALUE, steel=False)

    await world.poll.execute()

    assert world.mailbox.asked == [] and world.uow.tool_calls.claimed == {}


async def test_every_model_call_the_poll_makes_is_the_tenant_s() -> None:
    world = mail_world(sure=True, values=EVERY_VALUE, steel=True)

    await world.poll.execute()

    assert world.reads.tenants == [f.TENANT.value]


async def test_a_cap_reached_while_starting_the_run_leaves_the_mail_unread() -> None:
    world = mail_world(sure=True, values=EVERY_VALUE, steel=True,
                       start_refuses=OverCap("today's model budget is spent"))

    await world.poll.execute()

    assert world.uow.tool_calls.claimed == {}
    assert world.durable.runs_started == []
```

```python
# backend/tests/integration/test_mail_is_read_once.py
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sro.application.chat.from_the_mail import FromTheMail
from sro.infrastructure.db.repositories import SqlUnitOfWork
from tests.unit.application.rig.test_from_the_mail import (
    CTX, JOB, _found, _held_in, _Mailbox, _mail, _Reads, _reading,
)
from tests.unit.fakes import FakeClock, FakeIdFactory


async def test_the_heartbeat_look_and_the_poll_racing_read_one_mail_once(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _held_in(SqlUnitOfWork(session_factory))
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please create customer type GT2")})
    reads = _Reads(_reading(JOB), _reading(JOB))
    heartbeat, poll = (
        FromTheMail(SqlUnitOfWork(session_factory), mailbox, reads, model="m",
                    clock=FakeClock(), ids=FakeIdFactory())
        for _ in range(2)
    )

    one, other = await asyncio.gather(heartbeat.execute(CTX), poll.execute(CTX))

    assert one.read + other.read == 1
    assert len(reads.saw) == 1
```

(`_held_in(uow)` is `_held()`'s body taking the unit of work, saving inside `async with uow` and committing, so the integration test saves the same job into Postgres; `_held()` becomes `return await _held_in(FakeUnitOfWork())`.)

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/rig/test_from_the_mail.py -q -o faulthandler_timeout=120 -k "poll or cap_reached_while_starting"`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.application.chat.look_lately'`.

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/chat/look_lately.py
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sro.application.chat.about_an_offer import AskAboutTheOffer
from sro.application.chat.from_the_mail import FromTheMail, LookedInTheMail
from sro.application.context import RequestContext
from sro.application.execution.workflow_runs import StartWorkflowRun
from sro.application.ports.repositories import UnitOfWork
from sro.application.shared.refusals import OverCap
from sro.domain.chat.asking import Pending
from sro.domain.shared.identifiers import PrincipalId
from sro.whose import about

logger = logging.getLogger(__name__)

K_EVER = datetime(1970, 1, 1, tzinfo=UTC)


class LookInTheMailLately:
    def __init__(self, uow: UnitOfWork, look: FromTheMail, asks: AskAboutTheOffer,
                 start: StartWorkflowRun) -> None:
        self._uow, self._look, self._asks, self._start = uow, look, asks, start

    async def execute(self) -> dict[str, LookedInTheMail]:
        async with self._uow as uow:
            tenants = await uow.gestures.tenants_since(K_EVER)
            operators = {
                tenant: sorted({
                    one.principal_id.value
                    for one in await uow.devices.list_for_tenant(tenant)
                    if not one.revoked
                })
                for tenant in tenants
            }
        looked: dict[str, LookedInTheMail] = {}
        for tenant, principals in operators.items():
            for principal in principals:
                ctx = RequestContext(tenant_id=tenant, principal_id=PrincipalId(principal))
                if not self._start.runs_on_steel(ctx):
                    break
                with about(tenant=tenant.value, principal=principal):
                    try:
                        found = await self._look.execute(ctx)
                    except OverCap as reached:
                        logger.info("%s: the mail poll stopped at the cap -- %s", tenant.value, reached)
                        break
                    for one in found.offered:
                        if one.missing and not one.started:
                            await self._asks.execute(
                                ctx,
                                Pending(workflow_id=one.workflow_id, title=one.title,
                                        values=dict(one.values), missing=tuple(one.missing),
                                        mail_thread=one.thread),
                                about=one.subject,
                                mail_thread=one.thread,
                            )
                looked[f"{tenant.value}/{principal}"] = found
        return looked
```

`FromTheMail.execute`, D3's start pass becomes:

```python
        started: list[Offered] = []
        for one in offered:
            try:
                started.append(await self._started(ctx, one))
            except OverCap as reached:
                await self._forget(ctx, one.message)
                logger.info("%s: %s left unread -- %s", tenant, one.message, reached)
        offered = started
```

`worker.py`:

```python
async def look_in_the_mail_lately(container: Container, every_seconds: float) -> None:
    if every_seconds <= 0:
        logger.info("the mail poll is off (mail_sweep_seconds=0)")
        return
    while True:
        await asyncio.sleep(every_seconds)
        try:
            looked = await container.look_in_the_mail_lately().execute()
        except Exception:
            logger.exception("the mail poll could not finish")
            continue
        for who, one in looked.items():
            if one.read:
                logger.info("%s: %s mail(s) read -- %s", who, one.read, one.why)
```

started in `run()` as `mailer = asyncio.create_task(look_in_the_mail_lately(container, settings.mail_sweep_seconds))` and cancelled in the `finally` with the others. `container.py`: `LookInTheMailLately(self.unit_of_work(), self.from_the_mail(), self.ask_about_the_offer(), self.start_workflow_run())`.

Code notes: why a loop and not a Temporal schedule (the repository's pattern for platform sweeps; schedules are operators' triggers); why each operator and not each tenant (grant and claim are per operator); why only Steel tenants until R2 (an extension tenant's complete request becomes a card only in its browser); why the claim alone keeps the two callers apart (one insert wins, no lock and no timing window); why a refused start releases the claim (a cap refusal must not cost a request); `mail_sweep_seconds` and why 60 (the heartbeat's own look is once a minute, so the operator sees no change in latency).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_mail_is_read_once.py -q -o faulthandler_timeout=120`
Expected: all pass.

- [ ] **Step 5: Commit, then LIVE QA**

```bash
git add backend/src/sro/application/chat backend/src/sro/infrastructure/temporal/worker.py backend/src/sro/config.py backend/src/sro/container.py backend/tests docs/code-notes
git commit -m "feat(mail): the worker reads each operator's mailbox; one claim per message keeps the heartbeat look and the poll apart

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

A code change is live only after the worker restarts (the poll is a worker loop). **LIVE QA: QA-7** follows (Proof points).

---

# Stream L — lookups (spec §6.5)

## L1: Lookups run on Steel — the account's session first, then a Steel tab, never the operator's browser (§6.5)

Depends on: S7 (`account_for`, `acquire`, `release`), S8 (`reauth`), S10 (`headers`), X5 (`K_AUTH_REFUSED`, the API lane's refusal rule), X7 (`PageDriver.screenshot`, `Screen`). It does not need X4. A lookup has no recorded gesture to act on and never acts: it navigates to an address and looks, which S7's `acquire` (a tab opened on the page) and X7's `screenshot` cover.

Today `RunLookups` (`application/lookup/run_lookups.py:47-160`) serves three doors: `/v1/ask` (`routers/ask.py:56`), `/v1/lookups` (`routers/lookups.py:53`) and chat (`application/chat/converse.py:785-801`, `K_WHILE_TALKING`). It picks any online device (`:66`) and sends it commands through `SocketChannel` (`container.py:359-360`):
- a `call` goes out as `http.send` (`:106`), which is a GET in the operator's own browser with their cookies;
- a `screen` is `navigate` then `screenshot` (`:118-125`);
- a shut system gets `tab.open` and one retry (`:128-141`).

The address half stays unchanged. `address_for` (`domain/lookup/address.py:24-70`) turns a plan's knowledge key into a place this deployment has already been: the newest GET to that path that answered 2xx, with its recorded headers and the names of the ones to fetch live, or the page somebody was on for a screen route. It already refuses a write: a path seen only as a POST addresses nothing (`tests/unit/application/test_going_and_looking.py:112-130`, id "a write").

**Files:**
- Modify: `backend/src/sro/domain/lookup/address.py`: `Address.page`, the page the addressed GET was made from, taken from its gesture's `page_url` or else `url`. `_call_address` keeps the gesture beside the call it chooses.
- Modify: `backend/src/sro/application/lookup/run_lookups.py`:
  - `RunLookups(uow, broker, http)` replaces `RunLookups(uow, channel)`;
  - `execute(ctx, *, plan, within)` no longer takes `device_id` or `allow_focus`;
  - `_reopened`, `_send`, `_shut`, `NO_TAB` and `_call_payload` are deleted.
- Modify: `backend/src/sro/container.py:359-360`: `run_lookups()` builds `RunLookups(self.unit_of_work(), self.session_broker(), self.http)`.
- Modify: `backend/src/sro/application/runtime/broker.py`: `SessionBroker.screenshot(ctx, held) -> Screen`, one line over `driver.screenshot`.
- Modify: `backend/src/sro/interface/http/v1/routers/ask.py:56-58`, `routers/lookups.py:53-55` and `application/chat/converse.py:799-801`: stop passing `allow_focus`.
- Modify: `backend/src/sro/interface/http/schemas.py`: delete `LookupRequest.allow_focus` and `AskRequest.allow_focus`, which meant "bring the operator's tab forward", after `grep -rn allow_focus new-chrome-extension/src frontend/src` shows their senders; the senders are edited in the same commit.
- Modify: `application/chat/converse.py` `_what_was_found`: "I could not reach your browser in time" becomes "I could not read that in time".
- Modify: `backend/tests/unit/application/test_going_and_looking.py`. The address tests (`:77-170`) stay. The run tests (`:173-460`) are rewritten against `lookup_world`; the ones about a shut tab, `tab.open` and "no browser connected" are deleted with the path they tested.
- Modify: `backend/tests/unit/runtime_support.py`: `lookup_world(*gestures) -> LookupWorld`, which saves the gestures and a recorded sign-in for the system (`with_a_recorded_sign_in(uow, lands_on=WMS, username="lena")`, from S7) into a `FakeUnitOfWork` and builds `SessionBroker` over the fakes (S7's `_broker` shape) with a `FakeHttpCaller` and a `FakePageDriver`; `world.reauths` counts `reauth` calls.
- Modify: `backend/tests/unit/test_container_wiring.py`.
- Modify: `backend/tests/integration/test_runs_on_local_steel.py` (scenario: a lookup on local Steel).
- Run: `make types`.

**Interfaces:**
- Consumes: `SessionBroker.account_for/acquire/release/reauth/headers` (S7, S8, S10); `K_AUTH_REFUSED` (X5); `PageDriver.screenshot -> Screen(image, mime_type, width, height)` (X7); `HttpCaller` (`ports/http.py`); `address_for`, `read_answer` (existing).
- Produces:
  - `Address.page: str = ""`.
  - `RunLookups(uow: UnitOfWork, broker: SessionBroker, http: HttpCaller)`.
  - `.execute(ctx, *, plan: Plan, within: float = K_DEADLINE_S) -> Answers`. `Answers` and `Looked` are unchanged on the wire. A `call` answer is `{"status", "body"}`, as before. A `screen` answer is `{"image_base64", "mime_type", "width", "height"}`, as the extension's `screenshot` answered, without `text_digest`.
  - The lease holder for a lookup is `lookup-<hex>`.
- Refusal: a lookup can reach nothing that writes.
  - `address_for` returns only GETs that answered 2xx.
  - The API lane sends the literal method `"GET"`.
  - The tab path calls only `acquire` (open a tab on the page), `screenshot` and `release`. Never `act`, `point` or the sight model.
  - A target seen only as a write gets `Looked(ok=False, detail="nothing here has been to <target>")`, and nothing is sent.
- Gaps: a `DomainError` (`NeedsAPerson` for a sign-in that needs a password; an account with no recorded username), `PoolFull`, `PageGone`, `TargetUnreachable` and running out of `within` each make that one lookup `Looked(ok=False, detail=…)`. The rest of the plan still runs. A lookup never waits on a person.

- [ ] **Step 1: Write the failing tests**

In `test_going_and_looking.py` (`CALL`, `SCREEN`, `SCREEN_URL`, `_call`, `_gesture` are the file's own):

```python
async def test_a_call_goes_out_as_a_get_with_the_account_s_steel_session() -> None:
    world = await lookup_world(_gesture(_call(headers={"X-Requested-With": REDACTED})))
    world.driver.cookie = "sid=abc"
    world.driver.headers = {"x-requested-with": "XMLHttpRequest"}
    world.http.answer(200, '{"rows": 5}')

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    (sent,) = world.http.sent
    assert sent["method"] == "GET"
    assert sent["headers"]["cookie"] == "sid=abc"
    assert sent["headers"]["x-requested-with"] == "XMLHttpRequest"
    assert answers.any_answered
    assert world.driver.tabs == {}


async def test_an_expired_session_signs_in_again_once_and_the_read_is_tried_again() -> None:
    world = await lookup_world(_gesture(_call()))
    world.http.answer(401, "")
    world.http.answer(200, '{"rows": 1}')

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.reauths == 1 and len(world.http.sent) == 2 and answers.any_answered


async def test_a_call_refused_otherwise_is_read_off_the_page_it_was_seen_on() -> None:
    world = await lookup_world(_gesture(_call(), url=SCREEN_URL))
    world.http.answer(500, "")

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert answers.looked[0].ok and answers.looked[0].answer["mime_type"] == "image/png"
    assert ("open_tab", SCREEN_URL) in {call[:2] for call in world.driver.calls}


async def test_a_screen_is_put_up_in_a_steel_tab_and_nothing_on_it_is_pressed() -> None:
    world = await lookup_world(_gesture(url=SCREEN_URL))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(SCREEN,)))

    assert answers.looked[0].ok
    assert not {call[0] for call in world.driver.calls} & {"act", "point", "type", "press"}
    assert world.http.sent == []


async def test_an_endpoint_seen_only_as_a_write_is_refused_before_anything_is_sent() -> None:
    world = await lookup_world(_gesture(_call(method="POST")))

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL,)))

    assert world.http.sent == [] and world.driver.calls == []
    assert answers.looked[0].detail.startswith("nothing here has been to")


async def test_a_system_that_needs_a_person_is_one_named_gap() -> None:
    world = await lookup_world(_gesture(_call()), _gesture(url=SCREEN_URL, at=200.0))
    world.driver.refuses = True

    answers = await world.run_lookups.execute(CTX, plan=Plan(question="q", lookups=(CALL, SCREEN)))

    assert [one.ok for one in answers.looked] == [False, False]
    assert all(one.detail for one in answers.looked)
```

In `test_container_wiring.py`:

```python
def test_a_lookup_reaches_no_browser_socket(container: Container) -> None:
    assert not any(isinstance(one, SocketChannel) for one in vars(container.run_lookups()).values())
```

Local Steel (`test_runs_on_local_steel.py`): the rig serves `GET /api/customer-types` (JSON rows) behind its identity-provider chain; a gesture recording that GET from `/app` is saved; `RunLookups` over the real broker answers the plan with the rig's rows, the rig saw one sign-in, and the account's tab count is back to what it was.

- [ ] **Step 2: Run them and see them fail**

Run: `cd backend && uv run pytest tests/unit/application/test_going_and_looking.py tests/unit/test_container_wiring.py -q -o faulthandler_timeout=120`
Expected: FAIL, `ImportError: cannot import name 'lookup_world'` (and the wiring test: the lookup holds a `SocketChannel`).

- [ ] **Step 3: Implement**

```python
# backend/src/sro/application/lookup/run_lookups.py (the class; Looked, Answers, K_DEADLINE_S, K_WHILE_TALKING unchanged)
class RunLookups:
    def __init__(self, uow: UnitOfWork, broker: SessionBroker, http: HttpCaller) -> None:
        self._uow, self._broker, self._http = uow, broker, http

    async def execute(self, ctx: RequestContext, *, plan: Plan, within: float = K_DEADLINE_S) -> Answers:
        if not plan.lookups:
            return Answers(plan=plan)
        async with self._uow as uow:
            gestures = list(await uow.gestures.gestures_for(ctx.tenant_id))
        looked: list[Looked] = []
        for lookup in plan.lookups:
            address = address_for(lookup, gestures)
            if address is None:
                looked.append(Looked(lookup=lookup, ok=False,
                                     detail=f"nothing here has been to {lookup.target}"))
                continue
            try:
                async with asyncio.timeout(within):
                    looked.append(await self._one(ctx, lookup, address))
            except TimeoutError:
                looked.append(Looked(lookup=lookup, ok=False, url=address.url,
                                     detail=f"timed out after {within:.0f} s"))
            except (DomainError, PoolFull, PageGone, TargetUnreachable) as gap:
                looked.append(Looked(lookup=lookup, ok=False, url=address.url, detail=str(gap)))
        return Answers(plan=plan, looked=tuple(looked))

    async def _one(self, ctx: RequestContext, lookup: Lookup, address: Address) -> Looked:
        page = address.page or address.url
        account = await self._broker.account_for(ctx, page)
        held = await self._broker.acquire(ctx, account, page, holder=f"lookup-{uuid4().hex}")
        try:
            if lookup.how == "call":
                got = await self._get(ctx, held, address, page)
                if got.succeeded:
                    return _looked(lookup, address, {"status": got.status_code, "body": got.text})
            shot = await self._broker.screenshot(ctx, held)
            return _looked(lookup, address, {
                "image_base64": b64encode(shot.image).decode(), "mime_type": shot.mime_type,
                "width": shot.width, "height": shot.height,
            })
        finally:
            await self._broker.release(ctx, held)

    async def _get(self, ctx: RequestContext, held: Held, address: Address, page: str) -> HttpResponse:
        got = await self._send(ctx, held, address)
        if got.status_code in K_AUTH_REFUSED:
            await self._broker.reauth(ctx, held, page)
            got = await self._send(ctx, held, address)
        return got

    async def _send(self, ctx: RequestContext, held: Held, address: Address) -> HttpResponse:
        session = await self._broker.headers(ctx, held, system_of(address.url))
        return await self._http.send("GET", address.url, headers={**address.headers, **session})
```

`_looked(lookup, address, result: Mapping[str, object])` is the existing helper, taking the result instead of a `Reply`. `SessionBroker.screenshot(ctx, held) -> Screen` is one line over `driver.screenshot(held.session, held.target_id)`, so `RunLookups` needs the broker and no driver of its own. The screenshot needs no navigation, because `acquire` opened the tab on `page` and `reauth` returns it there.

Code notes: why a lookup takes a tab and not a durable run (it lives inside the request that asked, bounded by the caller's deadline); why an auth refusal re-signs in and anything else falls to the screen (§3's rule, applied to a read); why nothing here can write (the three structural facts under Interfaces, one test each); why a sign-in that needs a person is a gap and not a question (nothing is waiting to resume a lookup).

- [ ] **Step 4: Run them and see them pass**

Run: `cd backend && uv run pytest tests/unit -q -o faulthandler_timeout=120 && uv run lint-imports && cd .. && make types && cd backend && uv run pytest tests/contract -q`
Run (with `make up`): `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest tests/integration/test_runs_on_local_steel.py -q -o faulthandler_timeout=120 -k lookup`
Expected: all pass; `grep -n "SocketChannel\|channel" backend/src/sro/application/lookup/run_lookups.py` prints nothing.

- [ ] **Step 5: Commit, then LIVE QA**

```bash
git add backend/src/sro backend/tests frontend/openapi.json frontend/src/lib/api/generated.ts new-chrome-extension/src frontend/src docs/code-notes
git commit -m "feat(lookups): a lookup reads through the account's Steel session, never the operator's browser

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

`RunLookups` runs in the API process (lookups answer inside a request), so this is live after the API restarts. **LIVE QA: QA-8** follows (Proof points).

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

## R2: Steel is the only executor; the extension becomes watch-only (§9 step 3, §10) — after the POC milestone

**What R2 is, plainly: the step that makes the extension watch-only.** After it, the extension captures what the operator does, recognises the jobs they start, and asks and answers in the panel. It can no longer act on a page. It can no longer send a request for a run — including `httpSend`, which today sends a request from the operator's own browser with their cookies. Its heartbeat no longer calls the mail door; the server reads the mailbox (D8).

Depends on:
- QA-1 … QA-9 passed (the POC milestone): takeover (QA-6) because after R2 no run can carry on in the operator's tab, the server mail poll (QA-7) because R2 removes the only other reader, and lookups on Steel (QA-8) because R2 deletes the kinds lookups used to send. QA-9 is an acceptance line of spec §1, not something R2 removes.
- D7, D8, L1, X10.

**Files:**
- Delete: `new-chrome-extension/src/background/commands.js` — every executing kind: `ui.perform`, `ui.perform_at`, `ui.url`, `screenshot`, `navigate`, `sign_in`, `tab.open`, `calls.since`, `http.send` (`httpSend`, `commands.js:1451`) and `abort`.
- Delete: `channel.js`. Its only job is to carry backend commands to `commands.perform` (`channel.js:12,61`).
- Delete: `showing.js` (the in-page driving band), and `pointing.js`, `sign-in.js`, `whats-on-screen.js` (imported only by `commands.js`).
- Modify: `new-chrome-extension/manifest.json`: drop the `debugger` permission. `pointing.js` was its last user after E6 removed `trees.js`, and the watch-only test asserts it is absent.
- Delete: every test file whose only subject is one of the deleted files. Grep each `*.test.mjs`'s imports first; a mixed file is edited, not deleted.
- Modify: `new-chrome-extension/src/background/service-worker.js`:
  - the command handler, and the `channel.*` calls (`:206, 1641, 1722, 1750, 1818, 3258, 3360-3362`);
  - the band;
  - the heartbeat's mail call: `void lookInTheMail()` on the `sro-heartbeat` alarm (`:200`), `lookInTheMail` (`:2808`), `readingTheMail` and `offerFromMail` (`:725`).
- Modify: `api.js`: delete `fromTheMail` (`:230`).
- Delete: `looking.js` and `looking.test.mjs`, the look's throttle.
- Modify: the panel strip's "reading your mailbox" state, which only the look fed. The server's "checked N s ago" (P5) is design 3.
- Modify: `new-chrome-extension/src/page/page-code.js`: delete `perform`, `performAt`, `screenSize`, `viewport`, `csrfToken`, `requestedWith` and `send`, which are extension-only. `resolve`, `act`, `holds`, `hitTest` and `signals` stay: Steel loads them, and after R2 nothing in the extension injects this file.
- Create: `new-chrome-extension/src/watch-only.test.mjs`.
- Modify: `new-chrome-extension/src/background/offering-worker.test.mjs`: drop its import of `perform`.
- Modify: `backend/src/sro/application/execution/workflow_runs.py`. In `StartWorkflowRun`, delete the extension path: `run_workflow`, `WatchingChannel`, the device checks and `Stops`; every run is Steel. `AbortWorkflowRun` (`:550-567`) only cancels; `Stops` and `Approvals` leave it.
- Modify: `backend/src/sro/config.py` (delete `steel_tenants`) and `infra/docker-compose.deploy.yml`. Also delete the `runs_on_steel` gate in `LookInTheMailLately` (D8) and `FromTheMail._started` (D3); every tenant is polled.
- Modify: `backend/src/sro/interface/http/v1/routers/workflow_runs.py:99-150`: `await starter.perform(...)` instead of `container.pursuits.spawn(...)`. The same change goes in `application/trigger/fire_trigger.py:264-298` and `application/trigger/answer_confirmation.py`.
- Delete: the backend's command socket (`interface/http/v1/routers/agent_channel.py`, `infrastructure/agent/channel.py` `SocketChannel`, `container.agent_sockets`). L1 moved lookups off it, and this task removes its last sender, `StartWorkflowRun`'s extension branch (`container.py:753`).
- Modify: `docs/14-extension-protocol.md` (the command kinds are gone).
- Test: `backend/tests/unit/test_container_wiring.py`, `new-chrome-extension/src/watch-only.test.mjs`, `make test-browser`.

**Interfaces:**
- Removes: `Settings.steel_tenants`; every executing command kind, `httpSend` among them; the command socket, on both ends; the heartbeat's mail call; `StartWorkflowRun`'s extension branch; `pursuits.spawn` on the workflow-run path.
- Keeps: capture (`recorder.generated.js`, `network*.js`, `observe.js`, `upload.js`, `queue.js`, `shots.js`; `trees.js` is already gone, E6); recognition (`recognise.js`, served shapes) and the offer press, which calls the backend and acts on no page; the panel; `api.js` requests to the deployment; `page-code.js` as Steel's file.

- [ ] **Step 1: Write the failing tests**

In `backend/tests/unit/test_container_wiring.py` (its `container` fixture):

```python
def test_no_run_is_ever_sent_to_a_browser_socket(container: Container) -> None:
    starter = container.start_workflow_run()

    assert not hasattr(starter, "_channel")
```

The extension test. It is AST-based and uses the parser `make lint-extension` already runs (espree, from the frontend's `node_modules`):

```js
// new-chrome-extension/src/watch-only.test.mjs
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, relative, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const espree = createRequire(import.meta.url)("../../frontend/node_modules/espree");
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(readFileSync(join(ROOT, "manifest.json"), "utf8"));

const UI_EVENTS = new Set(["MouseEvent", "PointerEvent", "KeyboardEvent", "InputEvent", "FocusEvent",
  "TouchEvent", "SubmitEvent", "DragEvent", "ClipboardEvent"]);
const UI_EVENT_NAMES = new Set(["click", "input", "change", "submit", "keydown", "keyup", "mousedown", "mouseup"]);
const ELEMENT_ACTS = new Set(["click", "submit", "requestSubmit", "execCommand", "setRangeText"]);
const CONTROL_WRITES = new Set(["value", "checked", "selectedIndex"]);
const SAVED_ORIGINALS = new Set(["fetch", "open", "send", "setRequestHeader"]);
const NO_WAY_IN = new Set(["chrome.runtime.connectNative", "chrome.runtime.onMessageExternal.addListener",
  "chrome.runtime.onConnectExternal.addListener"]);

const name = (n) =>
  n?.type === "Identifier" ? n.name
    : n?.type === "MemberExpression" ? `${name(n.object)}.${n.property.name ?? n.property.value}` : "";

function parse(file) {
  const code = readFileSync(file, "utf8");
  for (const sourceType of ["module", "script"]) {
    try { return espree.parse(code, { ecmaVersion: "latest", sourceType, loc: true }); } catch {}
  }
  throw new Error(`${relative(ROOT, file)} does not parse`);
}

function* nodes(node, parents = []) {
  yield [node, parents];
  for (const value of Object.values(node))
    for (const child of Array.isArray(value) ? value : [value])
      if (child && typeof child.type === "string") yield* nodes(child, [...parents, node]);
}

// Everything Chrome can load for this extension, and the realm it runs in: modules reachable by
// static import from the manifest's entry points ("extension"), and files it names for
// injection or registration ("page").
function loadable() {
  const pages = [manifest.side_panel?.default_path, manifest.options_page].filter(Boolean);
  const queue = [
    [resolve(ROOT, manifest.background.service_worker), "extension"],
    ...pages.flatMap((page) =>
      [...readFileSync(join(ROOT, page), "utf8").matchAll(/<script[^>]*\ssrc="([^"]+)"/g)]
        .map((m) => [resolve(ROOT, dirname(page), m[1]), "extension"])),
    ...(manifest.content_scripts || []).flatMap((one) => one.js.map((js) => [resolve(ROOT, js), "page"])),
  ];
  const seen = new Map();
  while (queue.length) {
    const [file, realm] = queue.pop();
    if (seen.has(file)) continue;
    const ast = parse(file);
    seen.set(file, { file: relative(ROOT, file), realm, ast });
    for (const [node] of nodes(ast)) {
      if (["ImportDeclaration", "ExportNamedDeclaration", "ExportAllDeclaration"].includes(node.type) && node.source)
        queue.push([resolve(dirname(file), node.source.value), realm]);
      if (node.type === "Literal" && typeof node.value === "string" && node.value.endsWith(".js")
          && existsSync(join(ROOT, node.value)))
        queue.push([resolve(ROOT, node.value), "page"]);
    }
  }
  return [...seen.values()];
}

const loaded = loadable();
const everyNode = (realm) =>
  loaded.filter((one) => !realm || one.realm === realm).flatMap(({ file, ast }) =>
    [...nodes(ast)].map(([node, parents]) => ({ file, node, parents })));
const at = ({ file, node }) => `${file}:${node.loc.start.line}`;

test("the extension loads no code this test cannot see", () => {
  for (const one of everyNode()) {
    const { node } = one;
    const hidden = node.type === "ImportExpression"
      || (node.type === "CallExpression" && ["eval", "importScripts", "Function"].includes(name(node.callee)))
      || (node.type === "NewExpression" && name(node.callee) === "Function")
      || (node.type === "CallExpression" && ["setTimeout", "setInterval"].includes(name(node.callee))
          && node.arguments[0]?.type === "Literal");
    assert.ok(!hidden, `${at(one)} loads code at run time`);
  }
});

test("nothing outside the extension can reach it: no socket, no external message", () => {
  for (const one of everyNode()) {
    const { node } = one;
    const door = (node.type === "NewExpression" && ["WebSocket", "EventSource"].includes(name(node.callee)))
      || (node.type === "CallExpression" && NO_WAY_IN.has(name(node.callee)));
    assert.ok(!door, `${at(one)} opens a way in`);
  }
});

test("code enters a page only as a named file, never as a function", () => {
  for (const one of everyNode("extension")) {
    const { node } = one;
    if (node.type !== "CallExpression" || name(node.callee) !== "chrome.scripting.executeScript") continue;
    const keys = (node.arguments[0]?.properties || []).map((p) => p.key?.name);
    assert.ok(keys.includes("files") && !keys.includes("func"), `${at(one)} injects a function`);
  }
});

test("the debugger is only read through", () => {
  for (const one of everyNode("extension")) {
    const { node } = one;
    if (node.type !== "CallExpression" || name(node.callee) !== "chrome.debugger.sendCommand") continue;
    const method = node.arguments[1];
    assert.ok(method?.type === "Literal" && /^Accessibility\./.test(method.value), `${at(one)} sends ${method?.value}`);
  }
});

test("the extension's own requests go to the deployment and nowhere else", () => {
  for (const one of everyNode("extension")) {
    const { node, parents } = one;
    assert.ok(!(node.type === "NewExpression" && name(node.callee) === "XMLHttpRequest"), `${at(one)} opens an XHR`);
    if (node.type !== "CallExpression" || !["fetch", "self.fetch", "globalThis.fetch", "navigator.sendBeacon"].includes(name(node.callee))) continue;
    const url = node.arguments[0];
    const base = url?.type === "TemplateLiteral" && url.quasis[0].value.cooked === "" ? url.expressions[0] : null;
    const fn = parents.findLast((p) => p.type.includes("Function"));
    const fromTheSettings = base?.type === "Identifier" && fn
      && [...nodes(fn)].some(([n]) => n.type === "CallExpression" && name(n.callee) === "state.apiUrl");
    assert.ok(fromTheSettings, `${at(one)} sends a request whose address is not the deployment's`);
  }
});

test("page code dispatches no input, presses nothing and writes no control", () => {
  for (const one of everyNode("page")) {
    const { node } = one;
    const acts =
      (node.type === "NewExpression" && UI_EVENTS.has(name(node.callee)))
      || (node.type === "NewExpression" && name(node.callee) === "Event" && UI_EVENT_NAMES.has(node.arguments[0]?.value))
      || (node.type === "CallExpression" && node.callee.type === "MemberExpression" && ELEMENT_ACTS.has(node.callee.property.name))
      || (node.type === "AssignmentExpression" && node.left.type === "MemberExpression" && CONTROL_WRITES.has(node.left.property.name))
      || (node.type === "CallExpression" && ["fetch", "window.fetch", "navigator.sendBeacon"].includes(name(node.callee)))
      || (node.type === "NewExpression" && ["XMLHttpRequest", "WebSocket", "EventSource"].includes(name(node.callee)));
    assert.ok(!acts, `${at(one)} acts on the page`);
  }
});

test("the page's network wrapper only passes on the page's own calls", () => {
  for (const { file, ast } of loaded.filter((one) => one.realm === "page")) {
    const saved = new Set([...nodes(ast)].filter(([n]) => n.type === "VariableDeclarator"
      && n.id.type === "Identifier" && SAVED_ORIGINALS.has(n.init?.property?.name)).map(([n]) => n.id.name));
    for (const [node, parents] of nodes(ast)) {
      if (node.type !== "CallExpression") continue;
      const forwarding = node.callee.type === "MemberExpression" && ["call", "apply"].includes(node.callee.property.name);
      const target = forwarding ? node.callee.object : node.callee;
      if (target.type !== "Identifier" || !saved.has(target.name)) continue;
      const fn = parents.findLast((p) => p.type.includes("Function"));
      const own = new Set((fn?.params || []).map((p) => (p.type === "RestElement" ? p.argument.name : p.name)));
      const passed = forwarding ? node.arguments.slice(1) : node.arguments;
      assert.ok(passed.every((a) => own.has(a.type === "SpreadElement" ? a.argument.name : a.name)),
        `${file}:${node.loc.start.line} calls the page's ${target.name} with arguments the page did not pass`);
    }
  }
});
```

**What this test proves, precisely.** It takes the set of code Chrome can load for this extension: every module statically imported from `manifest.json`'s service worker, side panel and options page ("extension" realm), and every `.js` file under the extension that any of that code names as a string, which is how capture files are injected and registered ("page" realm). The first check forbids the ways to load code outside that set (dynamic `import()`, `eval`, `importScripts`, `new Function`, string timers), so the set is complete. Over that set it proves:

1. No way in: no socket, no `EventSource`, no external message or native port. No backend or foreign message can start anything.
2. Code enters a page only as one of those named files, never as a function.
3. The debugger is used only for `Accessibility.*` reads.
4. Every request the extension makes is `fetch` to a template that starts with a value, in a function that reads `state.apiUrl()`; no XHR and no beacon.
5. Code in the page constructs no UI event, calls no `click`/`submit`/`requestSubmit`/`execCommand`/`setRangeText`, writes no form control's `value`/`checked`/`selectedIndex`, and originates no request.
6. The network wrapper calls the page's saved `fetch` and XHR methods only with the arguments the page's own call gave it.

It does not prove:
- that `state.apiUrl()` holds the deployment's address. That is a setting, and the test proves only that every request goes through it;
- anything about `chrome.tabs.create`, `update` and `reload`, which stay: the panel's "open the console" and the reload that repairs a half-deaf tab navigate or reload a tab, but carry no run, and by check 1 no message from outside can reach them;
- anything about the backend. There, `grep -rn "SocketChannel(" backend/src` printing nothing, `test_no_run_is_ever_sent_to_a_browser_socket` and L1's `test_a_lookup_reaches_no_browser_socket` are the proof.

- [ ] **Step 2: Run them and see them fail**

Run: `make test-extension; cd backend && uv run pytest tests/unit/test_container_wiring.py -q -o faulthandler_timeout=120`
Expected: FAIL.
- `watch-only.test.mjs` names `background/channel.js` (a `WebSocket`), `background/commands.js` (`executeScript` with `func`), `background/pointing.js` (`Input.dispatchMouseEvent`) and the injected `src/page/page-code.js` (`.click()`, `send`).
- The container test fails because the starter holds a channel.

- [ ] **Step 3: Delete the paths**

Grep every caller first, and edit mixed tests rather than deleting them wholesale (audit wave 1 Task 6's method). Afterwards each of these prints nothing:
- `grep -rn "pursuits.spawn(starter" backend/src`
- `grep -rn "steel_tenants" backend/src`
- `grep -rn "fromTheMail\|lookInTheMail\|http.send\|httpSend" new-chrome-extension/src`

A failure of the watch-only test is fixed by deleting the path it names, never by narrowing the test.

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

# Proof points (spec §8.5)

Each live QA point is run once by the user on the QA box (`infra/docker-compose.deploy.yml` only). Implementers never drive them (Global Constraint 12).

| # | After | What the user does and sees | Proves |
|---|---|---|---|
| **QA-0** | C0 | Runs `scripts/steel_sessions.py` against the deployed Steel; reads the verdict JSON. | Sessions per container; fixes S4's shape. |
| **QA-1** | D3, R1's switch (`greyorange` in `SRO_STEEL_TENANTS`) | Stores the account password once with `PUT /v1/secrets` and `username` (S1). Presses a mined Blue Yonder job (Create a Customer Type). The run's `workflow_run_steps` show `verdict_by = ui`; the broker signed in through the real identity-provider chain with the vault password (one `ready` lease for the account); `docker compose logs api` shows no command sent to any extension socket. | A mined Blue Yonder job runs on Steel, signed in from the vault, UI lane. |
| **QA-2** | QA-1, X9 | Presses the same job again. The write step's row reads `verdict_by = api`; the run adds no row to `model_spend`. | The job is promoted to the API lane, with no model call. |
| **QA-3** | D3, X6 | Sends a request mail naming the job and its values to the operator's mailbox; touches nothing else. A run starts (`started_by` the operator, `awaiting.thread` the mail's thread); its mail step reads `verdict_by = tool`; the reply is in the Gmail thread. | A mail job replies by mail through the Gmail connector, with no UI. |
| **QA-4** | D2, S7, S8 | Presses two jobs on one account at once: one lease, two target ids, both runs `held`. Then `docker restart` of that account's Steel container and a third press: the lease is new, the state restored, and the identity provider shows no new sign-in. Notes the container's RSS with one and two tabs open. | Two parallel jobs on one account as tabs of one browser; a container restart restores saved state; memory per browser measured (spec §12). |
| **QA-5** | S8, D6 | During a run, signs the account out elsewhere (or lets the session lapse): the run signs back in once and finishes. During another run, `docker compose restart worker` mid-step: the run resumes and the Blue Yonder audit (or a read-back) shows the write once. | Expiry mid-run recovers; a worker restart repeats no write. |
| **QA-6** | D7, R1's switch | (a) In their own tab the user starts a mined Blue Yonder job by hand (Create a Customer Type): opens the screen, presses Add, types the code, and stops before saving. The offer appears; they press it. The run's `workflow_run_steps` begin with the replayed typing on Steel (`verdict_by = ui`), the save is the run's own, and Blue Yonder holds one new customer type. (b) On a mined job with two saves, they make the first save by hand and press the offer. The run's `progress.marks` show that save `wrote = done`, `lane = operator`; the run starts after it; the Blue Yonder audit shows the first record once. If QA holds no two-save job, (b) is proven only by D7's local Steel scenario, and the report says so. (c) They press an offer within a second of their own save: the run either shows that save `done` by `operator` or asks in the panel "may already have been done". It never sends it again. | A job the operator started by hand finishes on Steel from their step; their writes are never repeated; doubt is asked, never guessed. |
| **QA-7** | D8, R1's switch | With the operator's Chrome closed, the user sends two request mails to the operator's mailbox: one with every value, one missing a value. Within one `mail_sweep_seconds` the first has a run (`started_by` the operator, `awaiting.thread` the mail's thread) with no press, and the second is a `needs_values` question in the operator's thread. `docker compose logs worker` shows the poll's lines under the tenant, and the reading's `model_spend` rows carry the tenant. They open Chrome and wait for a heartbeat: no card and no second run for either mail, and `tool_calls` holds one `mail:` row per message id. | The server reads the mailbox with the extension closed; the poll and the heartbeat look never read one mail twice; tenant-attributed and metered. |
| **QA-8** | L1, R1's switch | With the operator's Chrome closed, the user asks in the console (`/v1/ask`) and in chat a question a recorded read answers (which suppliers site SG has). The answer comes back with the records. `docker compose logs api` shows no command sent to any extension socket, the account's lease is the one runs use (or a new `ready` one, signed in from the vault), and after the answer the account's browser has no extra tab. Then a `screen` question returns a picture taken on Steel. | A lookup answers with the operator's Chrome closed, through the account's Steel session. |
| **QA-9** | X10, D8, R1's switch | On Blue Yonder the user picks a field on the Create Customer Type form that the mined job never filled: a dropdown with a short list if the form has one (Department is the spec's example), else a text field. The report names the field used. With the operator's Chrome closed, they mail the operator's mailbox: "Create customer type GT-QA9, Department: Finance", naming the field by its on-screen label. The run starts with no press. In its `progress.composed`, the field shows `lane = ui`, `verdict = done` and a `key`. The save step reads `verdict_by = ui`. Blue Yonder's new customer type holds Finance. The job now has a step "Fill Department" before the save, and an optional parameter with that `key`. The reply is in the mail thread. A second mail with another department and another code runs with no composing: the learned step fills it, and the save's body carries the key. A third mail naming an option the dropdown lacks gets a question in the thread listing the options, and the run sends no save until it is answered. | A field nobody demonstrated is filled on Steel, confirmed by the save call, and learned; a missing option is asked, never guessed. |
| **POC milestone** | QA-1 … QA-9 all passed | The eight acceptance lines of spec §1 hold. R2 may start. | Spec §1 accepted. |

Local proofs (implementer): the outline's real-Chrome and hostile-client proofs green (E6); X10's local Steel scenario (filled, keyed, learned, reused, passed over); §8.2 parity suite green (X2); §8.3 scenarios green on local Steel (S7: leases and restore, two tabs; S8: container crash, expiry then re-sign-in; D2: two runs as tabs; D4: stop during a step; D6: worker restart, no repeated write; D7: a takeover after the operator's own save, `rig.posts == 2`); D8's concurrent read-once test on Postgres; L1: a lookup read on local Steel; R2's watch-only test.

# Pre-flight conflict table

| Pair | Shared surface | Ruling |
|---|---|---|
| A0 × E1 × E2 × E3 × E4 × E5 × E6 | `domain/observation/gesture.py`, `application/observation/correlate.py`, `application/capture/rig_wire.py`, `tests/unit/application/test_correlate.py` | Serial in that order; each rebases on the last. E6 is cut fresh from the integration tip; nothing from `rt/e6` (8954f324) is merged or cherry-picked. |
| E2 × E3 × E4 × E5 × E6 | `infrastructure/steel/recorder.js`, `recorder.generated.js`, `src/content/evidence.test.mjs` | Serial. Never hand-merge the generated file: resolve `recorder.js`, then `make gen-recorder`. |
| E6 × E7 | `application/observation/redact.py`, `domain/observation/policy.py`, `tests/unit/application/test_the_backend_stores_what_the_browser_sent.py` | E7 is parked; whichever lands second rebases. E6 deletes the snapshot fields and `_shapes_only`; E7's structure-only rule must not reintroduce a tree path. |
| E6 × R2 | `new-chrome-extension/src/background/service-worker.js`, `pointing.js`, `state.js` | E6 first (tree code and comments); R2 then deletes `pointing.js` and the manifest's `debugger` permission. |
| E6 × X10 | *interface:* `Outline`, `OutlineField`, `last_outline`, `sroPage.outline` | Owned by E6; X10 only reads them. |
| E4 × S6 | `domain/skill/signing_in.py` | Different functions (`sign_in_chain` vs the new predicates). E4 first; rebase. |
| X1 × X2 × S6 × E6 × R2 | `new-chrome-extension/src/page/page-code.js`, `page-code.test.mjs` | X1, then X2, then S6 (`signals`), then E6 (`readers` gain `labelOf`/`requiredOf`/`outlineOf`; `sroPage.outline`), then R2 (deletes the extension-only methods; `outline` stays). |
| X1 × R2 | `new-chrome-extension/src/background/commands.js` | X1 changes injection; R2 deletes the executing kinds. X1 first. |
| S5 × S6 × X4 × S10 × X7 × X10 | `infrastructure/steel/driver.py`, `application/ports/page.py`, `FakePageDriver`, `tests/browser/test_the_steel_driver.py` | Serial: S5, S6, X4, S10, X7, X10. Each adds methods; none rewrites another's. |
| X4 × X7 × X8 × X9 × X10 | `application/runtime/ui_lane.py` (`_same_call`), `sight_lane.py`, `executor.py`, `teach.py`, `tests/unit/application/runtime/test_the_ui_lane.py` | X10 last; it widens `_same_call` (an `Adding` argument, same checks) and adds `SightLane.fill` and `Teach.learn_field`, rewriting none of the earlier rules. |
| X3 × D1 → X10 | *interface:* `StepResult.keyed`, `LaneContext.adding`, `Progress.composed` | Additive fields with empty defaults on the frozen types; no existing reader changes. |
| S7 × S8 × S10 | `application/runtime/broker.py`, `test_the_broker.py` | Serial. |
| S2 × S9 | `BrowserSessionRepository` (port, SQL, fake) | S2 owns the lease methods including `leased_sessions`; S9 only reads them. |
| S9 × R3 | `application/connection/release_strays.py`, `application/execution/pursuits.py` | S9 removes the `Pursuits` reader; R3 deletes `Pursuits`. |
| X3 → S7, X4 … X9, D2 | *interface:* `LaneContext`, `Held`, `NeedsAPerson`, `Stopped`, `StepLane`, `StepResult`, `Verdict`, `Broken` | Owned by X3; frozen in its review. |
| S5 → S6, S7, S10, X4, X7 | *interface:* `PageDriver`, `SessionRef`, `PageGone` | Owned by S5; later tasks only add methods. |
| S1 → S2, S7, D2 | *interface:* `Account`, `Lease`, `LeaseState`, vault keys | Owned by S1. |
| D1 → D2, D4, D5, D6 | *interface:* `Progress`, `StepMark`, `MAIN`, the step limits | Owned by D1. |
| D2 × D4 × D5 × D6 × D7 × X10 | `application/runtime/run_steps.py`, `infrastructure/temporal/{workflows,activities,durable}.py`, `ports/durable.py`, `tests/integration/test_run_workflow.py`, `test_run_steps.py` | Serial: D2, D4, D5, D6, D7, then X10 (`run_steps.py`, `answer_run.py` only). |
| D5 × D7 | `application/runtime/answer_run.py`, `tests/unit/application/runtime/test_asking.py` | D5 then D7 (`step` answers are `done`/`redo`). |
| D1 → D7 | *interface:* `Progress.sending/settle(never_left)/written/in_doubt`, `done` immutable, `record_progress` | D7 codes against D1 as merged (rt/d `9a0fb66c`), not the plan's first D1 text: no `Progress.asking`, `account` is an `Account`. |
| X3 → D7 | *interface:* `SeenCall`, `write_confirmed` | Owned by X3; D7 only calls them. |
| D3 × D4 × D7 × R2 | `application/execution/workflow_runs.py` (`StartWorkflowRun`, `AbortWorkflowRun`) | Serial: D3, D4, D7, R2. D8 only reads `runs_on_steel`. |
| D3 × D5 × D8 × X10 × R2 | `application/chat/from_the_mail.py`, `tests/unit/application/rig/test_from_the_mail.py` (`mail_world`) | Serial: D3 (start), D5 (answer from a reply), D8 (claim released on a refused start; poll), X10 (asked-for aside values into the run; `field` answers), R2 (gate removed). |
| D2 × D8 | `infrastructure/temporal/worker.py` | D2 adds the `runs` `Worker`; D8 adds a loop beside the keeper. Merge by union. |
| L1 × R2 | `backend/src/sro/container.py` (`run_lookups`, `SocketChannel`), `tests/unit/test_container_wiring.py` | L1 moves lookups off the socket; R2 deletes the socket. L1 first. |
| S7 × S8 × S10 × L1 | `application/runtime/broker.py` | L1 adds one method (`screenshot`) after S10; merge by union. |
| L1 × D2 … D8 | `backend/src/sro/interface/http/schemas.py` / `make types` | Regenerate on conflict. |
| D7 × R2 | `new-chrome-extension/src/background/service-worker.js`, `recognise.js` | D7 adds `took_over` to the offer press; R2 deletes the command handler, the band and the mail look around it. D7 first. |
| D8 → R2 | the heartbeat's mail call | R2 deletes it only after QA-7; before that the two callers run side by side, kept apart by the claim (D8's tests). |
| E7 × S2 × X8 × D1 | `infrastructure/db/models.py`, the Alembic head (`backend/migrations/versions`, head `0072`) | Take the next number at merge, repoint `down_revision`, keep one head. E6 adds no migration (the outline rides in `gestures.gesture`; the old policy key stays in `observation_policies.policy`). |
| X8 × X10 | `infrastructure/db/workflows.py` (`grew`), `KnownBrokenRow` | X8 creates the table; X10 adds it to `grew`'s moved tables. |
| S1 × X1 × E6 × D5 × D7 × L1 × X10 | `interface/http/schemas.py`, `frontend/openapi.json`, `frontend/src/lib/api/generated.ts` | Each runs `make types`; regenerate on conflict, never hand-merge. |
| S3 × S4 × S5 × S7 × S9 × X4 … X9 × D2 … D5 × D8 × L1 × R2 × R3 | `backend/src/sro/container.py` and its code-notes | Each adds or removes one factory or field: merge by union; re-anchor the notes once after R3. |
| S2 … D7, L1, X10 | `backend/tests/unit/fakes.py`, `backend/tests/unit/runtime_support.py` | Additions only; merge by union. |
| S7 × S8 × D2 × D4 × D6 × D7 × L1 × X10 | `backend/tests/integration/test_runs_on_local_steel.py`, `backend/tests/browser/steel_rig.py` | One scenario per task, appended; serial. X10's Department select is sent only when chosen, so every earlier scenario's saved body is unchanged. |
| D3 × D8 × R2 | `backend/src/sro/config.py` | Different keys (`steel_tenants`, `mail_sweep_seconds`); R2 deletes `steel_tenants` only. Merge by union. |
| S4 × D3 × R1 × R2 | `infra/docker-compose.deploy.yml` | Different keys (Steel services, `SRO_STEEL_URLS`, `SRO_STEEL_TENANTS`); merge by union. |
| C0 → S4 | *interface:* QA-0's verdict | S4's capacity and variant follow it. |

# Spec coverage

| Spec section | Tasks |
|---|---|
| §1 Goal and acceptance | POC milestone (QA-1 … QA-9); D2, D3, S7, S8, D6, D7 (takeover), D8 (server mail poll), L1 (lookups), X10 (a field nobody demonstrated) |
| §2 Architecture (worker runs activities; API only starts, stops, answers) | D2, D3, D4, D5 |
| §2 Mail poll (worker loop, per operator, once per message, metered, tenant-attributed, side by side with the heartbeat) | D8; R2 removes the heartbeat call |
| §3 The ladder; API-lane failures; ask after sight; no blind repeats | X3, X8, X5, D2 (`_ask`, settle), D1 (`sending`) |
| §4.1 Keep what is captured | E1 |
| §4.2 Semantic path | E2 |
| §4.3 Frame identity | E3, X4 (`_frame`) |
| §4.4 Click `detail` and `isTrusted` | E4 |
| §4.5 After-state | E5, X3 (`after_matches`), X4 |
| §4.6 Screen outline (no tree, no debugger; kept/never-kept lists; no echo; structural trigger; joined on its own gesture; `capture_snapshots` removed, its JSONB key kept and ignored) | E6 |
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
| §6.5 Lookups (account's session first, then a Steel tab; reads only; gaps per system) | L1 |
| §6.6 A field nobody demonstrated (compose from the outline, fill by label, ask, verify by the save's body key, sight fallback, learn; API lane withheld) | X10 (with E6, X4, X7, X9, D5) |
| §7.1 Start | D3 |
| §7.2 Workflow | D2 |
| §7.3 Progress and idempotency | D1, D2, D6 |
| §7.4 Stop, ask, restart | D4, D5, D6, D1 |
| §7.5 Limits | D1, D2, X7 |
| §7.6 Mid-job takeover | D7 (and D5's `done`/`redo` for a doubt) |
| §8.1 Unit | every task |
| §8.2 Page-code parity | X2 |
| §8.3 Integration on local Steel | S7, S8, D2, D4, D6, D7, L1, X10 |
| §8.4 The outline keeps no typed value (real Chrome; hostile client) | E6 |
| §8.5 Live QA | C0 (QA-0), Proof points QA-1 … QA-9 |
| §9 Rollout | D3 (setting), R1 (shadow, switch), D8 (poll beside the heartbeat from step 2), R2 (setting removed; watch-only) |
| §10 Removed when live | E6 (`trees.js`, the tree debugger attach, `capture_snapshots`/`snapshot_max_per_minute`/`reading_structure`, `_shapes_only`), X1 (`in-page.js`), S9 (grace timer), R2 (`pointing.js` and the manifest's `debugger` permission), R2 (every executing kind including `httpSend`, the command socket, the heartbeat mail call, `pursuits.spawn`, `Stops` on the run path; the watch-only test), R3 (`ui_driver.py`, old engine). the backend command socket after L1 |
| §11 Out of scope | nothing planned (live view, service account, shadow DOM, more tenants, design 2/3 work: wording-to-field matching, the learned key in the replay template, offering optional fields) |
| §12 Risks | QA-0 (C0); QA-4 (restore, memory); X1 CI hash + X2 parity; X2 threshold + write verification (X4); X7 cap and metering; X2 falls back to existing strategies for older evidence; D7 (flush before the press, doubt when uploads lag); D8 (concurrent read-once test); L1 (tab per lookup, closed in `finally`; reads only, tested); E6 (outline echo rule, real-Chrome and hostile tests); X10 (exact label, one live match, key in the save's own call) |

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
- **Wording to fields.** A mail's wording matched to the outline's fields when it is not the exact on-screen label: "dept" or "cost center" for "Department", or a value that names its field only by context. X10 matches exact labels only and asks otherwise. This is the request reader's work (A6), and it feeds X10's `compose` a label.
- **A learned key in the replay template.** The key X10 learned is folded into the API lane's body template, so a write that follows a learned field can be promoted to the API lane. Until then X10 withholds the API lane from that write (A4).

Superseded tasks of streams B and C not carried into this plan, and where they belong: B1, B2 (step timing and its console view) and B13–B16 (value sources, thread list, "Not a job", the per-job report) go to design 3 or its measurement work; B12 (a server-side mail poll) is D8 here — the worker reads each operator's mailbox, beside the extension's heartbeat look until R2 removes it — and only its panel half, "checked N s ago" (P5), stays with design 3; B8 (a lock for session-wide steps) is dropped by spec §5.4 (only session changes take the lock); C16 (a live view) is out of scope (§11). B3, B4, B5, B6, B7a/b, B9–B11 and C1–C15 are replaced by the tasks above (C9/C10's `SteelChannel` is not built: the lanes call `PageDriver` directly).

# Deferred to design 3, "Operator surface"

- **Offering optional fields.** The panel offers a job's optional fields, including the ones X10 learned (`required: false`, `names`, `seen_values`; `offerable` in `domain/skill/learned.py` already lists them), so the operator can give a value before a run.
- **Answering a `field` question in the panel.** The question lists `choices` (labels or options) and has a "leave it out" button. X10 defines the question and its answer (`POST /v1/workflow-runs/{id}/answer`); the panel's drawing of it is design 3's.
