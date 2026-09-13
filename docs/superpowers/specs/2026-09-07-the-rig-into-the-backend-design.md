# The rig into the backend: design

Date: 2026-09-07. Status: decided in conversation, this document is the shape
of it. Supersedes the mining half of `docs/17-agent-architecture.md`, which
goes to a backup branch and stays readable there.

## The decision

The backend (`backend/`, 48k lines, four layers under import-linter contracts,
strict mypy, Postgres, Temporal, its own auth, the console) is the product's
home. The rig (`new_agent_arch/`, 8.3k lines, one process, SQLite, 673 tests)
was built as the model-first prototype so the argument against the rule-based
pipeline could be settled on evidence. It has been: one real day of capture,
eight jobs mined, parameters learned across doings, the offer replay naming
every job as itself, a runner with its belts, and an afternoon on a real key
(`docs/new-agent-doc-arc/findings.md`, *A real key, one afternoon*).

So the rig's behaviour moves into the backend's layers, the rule-based
mining moves to a branch, and the extension talks to one place again. This is
a port, not a rewrite: most of the rig is pure arithmetic and prompts, which
drop into the inner layers as they are. The work is storage and the process
model.

Two things are not decided by this document and are named at the end: when
the runner becomes a Temporal workflow, and whether the rig's page becomes
console pages or stays a served page for a while.

## What goes where

| Rig today | Backend after | Fate |
|---|---|---|
| `POST /v1/observations`, artifacts | `application/observation/ingest.py`, `admit.py`, `artifacts.py` (exist) | kept, the rig's belts added: per-device batch ownership, `K_BATCH_EVENTS`, `K_ARTIFACT_BYTES` |
| `intents.read_gesture`, `read_new_gestures`, the daily cap | `application/intent/` (new use case), `application/ports/model.py` | ported |
| `pool.py`, `mine.py`, `identity.py`, `parameters.py`, `umbrella.py` | `application/observation/mine.py` rewritten; `domain/observation/identity.py`, `domain/skill/parameters.py` | ported; the old `mine.py`, `segment.py`, `propose.py` and the miner sweep are deleted |
| `workflows.py`, `shape.py`, `shapes.py` | `domain/skill/workflow.py`, `domain/skill/shape.py`; `application/skill/serve_shapes.py` | ported; `Skill` gains a workflow-born kind, `skill/from_rig.py` and `adopt_rig_workflow.py` retire |
| `runner.py`, `planner.py`, `verify.py`, `locators.py`, `effects.py` | `application/execution/run_workflow.py` and siblings; `domain/execution/` for verdicts, the earned rule, the weak-locator rule | ported; `execute_skill.py` stays as the fallback path for skills without evidence, behind a flag, until none remain |
| `channel.py` (device socket), `commands` protocol | `application/ports/agent.py::AgentDrivers` (exists: ui, http, online, held_for) | the rig's `send(kind, payload)` maps onto it; the sight command `ui.perform_at` and `screenshot` join the port |
| `offers.py`, `counsel` | `domain/skill/offers.py`, `application/skill/counsel.py` | ported |
| `devices.py`, tenant bearer, `caller`/`tenant_only` | `infrastructure/auth`, the device secrets the backend already issues | folded: a browser's secret is its token; the tenant-only route list is preserved as a dependency on the routers |
| `entry.py` (chat door) | `application/chat/` (exists) | the rig's `understand` becomes the chat's job reading; the schema fix and instruction travel |
| `store.py` (SQLite, ~20 tables) | `infrastructure/db/models.py`, `repositories.py`, alembic migrations | rewritten as repositories behind ports |
| `api.py` routes | `interface/http/v1/routers/`: `observations.py` extended; `shapes.py`, `offers.py`, `devices.py`, `audit.py`, `spend.py`, `mine.py`, `chat.py`, `workflow_runs.py`, `pool.py` added | ported route by route — **but not at the same paths, and the extension needs more than a base URL change. See the amendment below.** |
| `web/index.html` | console pages under `frontend/src/app/(console)/` | rebuilt, see *The console* |
| `scripts/dry_run.py`, `offer-replay`, `mutation_floor.py` | `backend/scripts/`, the backend's mutation step | ported; the replay stays the acceptance test for shapes |
| `config.py` settings | `sro.config` | folded, `RIG_` prefix dropped |

> **Amendment, 2026-09-10, after phase 4b shipped.** Two claims in the row above
> were false and are corrected here rather than left for a reader to trip over.
>
> **1. `runs.py` is not extended; workflow runs live at `/v1/workflow-runs`.**
> `/v1/runs` already means a *skill* run on this backend — `domain.execution.run.Run`,
> keyed on `RunId`. The rig's `/v1/runs` means a *workflow* run, keyed on a plain
> `str`. Two aggregates, two id spaces, one path. The extension is already living
> with the collision: `api.js:178` calls `/v1/runs/{id}` on the backend base and
> `api.js:192` calls the byte-identical path on the *rig* base, telling them apart
> by a mirrored `source` field — which stops being able to route anything the
> moment phase 7 puts both on one host. Four routes moved:
> `POST|GET /v1/runs`, `GET /v1/runs/{run_id}`, `.../abort`, `.../approve`.
>
> **2. "The extension changes only its base URL" is false for three calls**, and
> the reason is one line: `rigHeaders()` (`api.js:84-89`) sends the rig's bearer
> and **none of the backend's headers**, of which `X-Device-Secret` is one.
>
> | Call | Pointed at the backend | How loud |
> |---|---|---|
> | `shapes()` `api.js:255` | 404 → returns `[]` | silent, degrades |
> | `reportOffer()` `api.js:238` | 403 | **still silent in practice** — `f7c00ca` made it *return* whether the fate landed, but its only caller is `void api.reportOffer(...)` (`service-worker.js:414`), so the answer reaches nobody |
> | `rigApprove()` `api.js:329` | **200, NULL approver, 403 check skipped** | **silent, and worst** |
>
> `rigApprove` is the one to fix first: sending neither the secret nor
> `?device_id=` means `asking_device` resolves *no browser*, which is not a
> refusal — so the route records `approved_by = None` **and skips the
> driving-browser check entirely.** A live warehouse write authorised by nobody,
> on the door whose whole purpose is recording who authorised it.

Everything under `backend/src/sro/application/observation/{segment,mine,propose}.py`,
`application/induction/diff.py`'s signature, the `candidates` router and the
pairing judge are the rule-based architecture. They go to
`backup/rule-based-mining`, which is a branch pointer at today's `main`, and
are deleted from `main` in the last phase.

## The layers, module by module

### Domain (pure; imports nothing of ours, no Any)

- `domain/observation/gesture.py`: `Gesture`, `Intent`, `ValueSeen`, the
  `Request` the recorder captured. Today `rig/records.py` and `rig/wire.py`.
  The wire models stay pydantic in the interface layer; the domain holds
  frozen dataclasses.
- `domain/observation/identity.py`: `target_identity`, `shape_key`,
  `K_TEXT_IDENTITY_MAX`, and `resolve` (same occurrence, same job, new job by
  cited-gesture overlap). Today `rig/shape.py` and `rig/identity.py`.
- `domain/skill/workflow.py`: `Workflow`, `Step`, `unproven`, the parameter
  record with `seen_values`. Today `rig/workflows.py`'s dataclasses.
- `domain/skill/parameters.py`: `control_name`, `parameters_across`. Today
  `rig/parameters.py`.
- `domain/skill/shape.py`: the served `Shape`, `_typed_at`, the scroll rule,
  the cap on `offer_after`. Today the pure half of `rig/shapes.py`.
- `domain/skill/offers.py`: `FATES`, `REFUSED`, `Counsel`, the counsel rules
  over a list of offers (the query moves to the repository, the rule stays
  pure). Today `rig/offers.py`.
- `domain/execution/verdict.py`: `Verdict`, the verify decision over an
  artifact, a read and a screen answer; `K_WEAK_LOCATORS`; the earned rule
  (`K_EARNED_RUNS`, state belts only). Today `rig/verify.py`'s pure parts
  and `rig/effects.py`.
- `domain/execution/plan.py`: `PLAN_SCHEMA`, `SIGHT_SCHEMA`, `KINDS`,
  `SIGHT_ACTIONS`, the instructions, `Planned`, `Look`, `_value_for`,
  `_unreplayable`. Today `rig/planner.py` minus the model call.
- `domain/execution/locators.py`: the locator ladder, `allowlist`, `writes`,
  `recorded_call`, `origin_of`. Today `rig/locators.py`.
- `domain/shared/money.py`: `PRICES`, `price`, `is_priced`. Today
  `rig/models.py`'s pricing.

### Application (use cases over ports)

- `ports/model.py`: `Asker` protocol with `ask(model, instructions, evidence,
  schema, image, images, effort) -> Answer`, and `Answer` with its tokens,
  cost, `unpriced`, `error`. The backend's `IntentParser` stays for
  utterances; this is the structured-output port every rig call uses.
- `ports/agent.py`: `AgentDrivers` gains `screenshot` and `perform_at`, and
  `online`/`held_for` are what `channel.online()` and the busy check become.
  `DeviceUnreachable` already exists there.
- `ports/repositories.py`: new protocols: `GestureRepository` (batches,
  gestures, requests, page events, intents, the pool), `WorkflowRepository`
  (workflows, steps, stale marks, effects), `OfferRepository`,
  `DeviceTokenRepository` (or the existing device secrets), `SpendRepository`
  (the four billed tables by day), `ChatRepository`, and `RunRepository`
  extended with `awaiting` and approvals.
- `intent/read_gesture.py`: one gesture, the tail, one Flash call, the
  intent row. `read_new_gestures` with `over_cap` in front of it.
- `intent/spend.py`: `spent_today`, `over_cap`, the `SPENT_IN` table list.
- `observation/mine.py`: the pass: the pool, the umbrella prompt, the
  proposals, `resolve` against known workflows, parameters learned across
  doings, `rekey_workflows` at startup. Today `rig/mine.py` and `rig/pool.py`.
- `skill/serve_shapes.py`: `shapes_for(tenant, device)` with the held gate and
  the counsel.
- `skill/counsel.py`: reads the newest offers and applies the domain rule.
- `skill/record_offer.py`: `record_offer` with the clock clamp.
- `execution/run_workflow.py`: the loop: look, plan, refuse, withhold,
  perform, verify; the three rungs; `may_write`; the approval wait; the
  budget; `_fell_over`; `fail_orphans` at startup. Today `rig/runner.py`.
- `execution/approvals.py`: `Approvals` and `Aborts`. In-process events on
  one worker for now, see *The process model*.
- `chat/understand.py`: the rig's `understand`, with its list-of-pairs
  schema and the instruction that a job is a kind of work.
- `capture/devices.py`: register and revoke a browser, `drop` its socket.
- `analytics/audit.py`: the audit since a time, across runs, offers, chats
  and devices.

### Infrastructure

- `infrastructure/gemini/asker.py`: `GeminiAsker` with `build_config`
  (`max_output_tokens = K_MAX_OUTPUT_TOKENS`, thinking level, no tools),
  `truncated`, the usage arithmetic. Today `rig/models.py`.
- `infrastructure/db/`: SQLAlchemy models and repositories for every table
  in *Storage*; alembic migrations.
- `infrastructure/agent/`: the websocket channel behind `AgentDrivers`,
  carrying the rig's command envelope. Today `rig/channel.py::DeviceChannel`
  and the `agent_channel` router.

### Interface

- Routers under `interface/http/v1/routers/`, same paths as the rig:
  `observations` (extended), `shapes`, `offers`, `runs` (extended with
  `awaiting`, `approve`, `abort`), `devices`, `audit`, `spend`, `mine`,
  `chat`, `workflows` (with evidence). The bodies do not change, so the
  extension's `api.js` changes only its base.
- Authorisation as today's rules: the tenant's credential opens every
  door; a browser's opens ingest, its own socket, shapes for itself, the
  runs it drives, approve for those, offers; the money routes and every
  cross-device read are tenant-only. The rig's `caller`/`tenant_only`
  become dependencies on the backend's auth.

## Storage

Postgres, decided by the port. One alembic migration per group, in the order
the code needs them:

1. `batches`, `gestures`, `requests`, `page_events`, `intents`, `pool` (the
   evidence plane). Timestamps become `timestamptz`; the SQLite `rowid`
   tiebreaks become an `id bigserial`.
2. `workflows`, `workflow_steps`, `workflow_stale`, `workflow_effects`,
   `passes`.
3. `runs`, `run_steps`, `approvals`.
4. `offers`, `chats`, `device_tokens` (or a column on the device table).

Rules that move with the tables and must be tested again against Postgres:
the counsel ordering (`at desc, id desc`), the daily sum since midnight UTC
over four tables with the blind predicate per table, `INSERT OR IGNORE` on
approvals becoming `ON CONFLICT DO NOTHING`, and the `since` normalisation
on the audit.

What is dropped: `ADDED_COLUMNS` and the SQLite migration ladder, `rekey`
as a startup step becomes a one-off migration.

## The process model

The rig runs one uvicorn worker, and three things assume it: `Approvals`
and `Aborts` are in-process events, the device channel is an in-process
dict of sockets, and the busy check is a read-then-write. The backend runs
Temporal for execution and may run more than one API worker.

Phase one keeps the rig's model: one asyncio task per run on the worker that
holds the device's socket, `Approvals` in that process, and the routers for
approve and abort forwarded to that worker (one worker in deployment, stated
in the deployment notes). This is the model that has held a real write.

Phase two makes `run_workflow` a Temporal workflow: each rung an activity,
the approval wait a signal with the five-minute timeout, abort a signal,
`fail_orphans` unnecessary because Temporal owns the run's life. The device
socket stays on the API worker and the activity reaches it through
`AgentDrivers`. This is the change that lets the API scale out. It is not in
this port's acceptance; it is the first item after it.

## The extension

- One base URL. `state.rigUrl`, `state.rigToken`, `mirror.js`, the
  `rig-channel.js` dial and the rig-settings page go. `channel.js` already
  dials `/v1/agents/{device_id}/commands`; it carries the rig's command
  envelope now, including `ui.perform_at` and `screenshot`.
- `recognise.js`, `offering.js`, `nudge.js`, the run card, the approve flow,
  the five fates: unchanged. They speak to `/v1/shapes`, `/v1/offers`,
  `/v1/runs`, which the backend now hosts at the same paths.
- The browser's token is the device secret the backend already mints at
  sign-in; the rig's separate registration goes.
- The "rig refused the last copy" line becomes "the backend refused the last
  upload", same mechanism.
- `K_TAIL = 40` stays.

> **Amendment, 2026-09-10, after phase 5 shipped.** Four claims in the section
> above were wrong or stale. They are corrected here rather than edited away,
> and this amendment sits *after* the section it corrects — phase 4b's was first
> inserted into the middle of the table it amends and had to be moved.
>
> **1. "The ten node suites" (also in *Sequence*, phase 5's acceptance line).**
> There were **27** when phase 5 was planned. There are **25** now: phase 5
> deleted `mirror.test.mjs` and `rig-settings.test.mjs` with their subjects.
> More to the point, **the number is no longer a fact anyone has to maintain** —
> `make test-extension` named every suite by hand until `e3b24d3` and now
> discovers them with node's own glob, because the hand-written list failed in
> the direction nobody watches: a suite deleted without editing the `Makefile`
> aborted the run at file 11 of 27, and the grep watching for failures read that
> as green. At this amendment: 25 files, 95 tests, 0 failures, exit 0.
>
> **2. "They speak to `/v1/shapes`, `/v1/offers`, `/v1/runs`, which the backend
> now hosts at the same paths."** `/v1/runs` on this backend is a **skill** run.
> Workflow runs are at **`/v1/workflow-runs`** (see the phase-4b amendment
> above). **Four of the seven calls changed path, not just base** — `rigRun`,
> `rigStart`, `rigAbort`, `rigApprove`. Two more changed shape rather than path:
> `POST /v1/workflow-runs` answers `id` where the rig answered `run_id` (read as
> `run_id` the panel draws a run it can never poll or approve), `abort` takes no
> body at all, and `reportOffer` moves `device_id` from the body to the query,
> where `record_offer` 403s a request that names no browser.
>
> **3. "`channel.js` … carries the rig's command envelope now, including
> `ui.perform_at` and `screenshot`."** **This was already true before phase 5
> started.** `UiDriver.perform_at` is at `application/ports/ui.py:69`,
> `vision_step.py:168` and `pursue_goal.py:294` call it, and `commands.js:414`
> and `:574` already handled both kinds. It was listed as work and needed none.
>
> **4. "One base URL … and the rig-settings page go" understates the count.**
> There were **seven** rig-dialling calls in `api.js`, not six. The seventh was
> `rigRegister`, the rig's own device registration — the last reader of the
> scheme guard and, on a browser whose rig could not mint a device token, the
> holder of the **tenant's** bearer. Dropping the three `sro.rig*` keys from
> `KEYS` would have left that credential in `chrome.storage.local` forever with
> no sign-out that clears it; `RETIRED_KEYS` and `dropRetired()` exist for that.
>
> **What phase 5 deliberately did not do.** `rigRun`'s mapping layer **stays**.
> `WorkflowRunModel`'s docstring said phase 5 would delete it; `{status, index}`
> are not rig-shaped aliases but the *skill* run's own field names
> (`RunModel.status`, `StepOutcomeModel.index`), and `run-card.js` draws both
> kinds of run from that one shape. Deleting it means teaching the run card a
> second vocabulary, and the run card is a file this phase does not change. The
> `rig*` **vocabulary** therefore survives — `source: "rig"`, `start-rig-run`,
> `api.rigRun` — pointed at the backend since phase 5. It is a rename task, and
> it is not this one.

## The console

The rig's page has three views and two strips. They become pages under the
console's app router, reading the same routes:

- Jobs: the cards, `became`, the run form with prefilled parameters, past
  runs, the run view with approve and stop, evidence.
- Needs a person: the parked runs, approve and stop, from any browser.
- Browsers: registered, online, revoked, the two-press revoke.
- Audit: since a time, runs with approvals, offers, chat, browsers.
- Spend: the header line, the day against its cap.

Until those pages exist, the rig's `index.html` can be served by the backend
at `/rig` against the ported routes. That is the interim named in *Open*.

## Deletions, at the end

Nothing on this list goes until the shared-day measurement in *Verification*
has been made and read. The first bullet deletes the rule-based path, which is
the one currently producing more answers than its replacement.

- `application/observation/segment.py`, `mine.py` (old), `propose.py`, the
  miner sweep and its Temporal schedule, `induction/diff.py`'s signature and
  what only it feeds, the `candidates` router, the pairing judge in
  `infrastructure/gemini`.
- `application/skill/from_rig.py`, `adopt_rig_workflow.py`,
  `network_from_rig.py`, `backend/scripts/skill_from_rig.py`,
  `mirror_backfill.py`.
- `new_agent_arch/` in full, once *Verification* passes.
- `docs/17-agent-architecture.md` replaced by a page that points at the new
  architecture doc and at the backup branch.

## Sequence

Each phase is a plan of its own; each ends green on the backend's full
pipeline (lint, types, import contracts, unit, contract, integration,
mutation floor).

0. `git branch backup/rule-based-mining main`. Push it.
1. Domain. Port the pure modules with their tests, tightened to no-Any.
   Acceptance: the rig's `test_shape`, `test_identity`, `test_parameters`,
   `test_offers` (rule half), `test_verify` (pure half), `test_planner`
   (schema and value tests), `test_locators`, `test_effects` pass unchanged
   in meaning under `tests/unit`.
2. Ports and infrastructure. The `Asker` port and `GeminiAsker`; the
   repositories and migrations; the channel behind `AgentDrivers`.
   Acceptance: `test_models`, `test_store`-shaped tests against a Postgres
   testcontainer; the counsel, spend and audit ordering rules re-proven.
3. Application. The use cases, one file each, wired to the ports.
   Acceptance: `test_runner`, `test_mine`, `test_shapes`, `test_intents`,
   `test_entry`, `test_devices` (use-case half) under `tests/unit` with
   fakes; the runner suite is the largest and the last.
4. Interface. The routers, the auth dependencies, the composition root.
   Acceptance: `test_api` becomes contract tests; the extension's
   `offering-worker.test.mjs` against the backend's paths; the offer replay
   through `backend/scripts/dry_run.py`; `make offer-replay` names 8 of 8.
5. Extension. One URL, mirror and rig settings removed, channel carries the
   envelope. Acceptance: the ten node suites; a browser signed in once
   registers, uploads, is served shapes, is offered, runs, approves.
   **"The ten node suites" is wrong and the envelope was already carried before
   this phase began — see the amendment under *The extension*. The second half
   of this line is the part still owed: nothing has run against a live backend,
   every suite fakes `fetch`.**
6. Console. The five pages. Acceptance: the page tests move from the node
   harness to the frontend's suite; the two-press revoke and the audit walk
   in a real browser as they did on 2026-09-06.
7. Deletions and the live proof: a day on the real WMS through the backend
   alone, then `new_agent_arch/` goes.

Phases 1 and 2 can run in parallel; 3 needs both; 4 needs 3; 5 and 6 need
4 and can run in parallel; 7 needs everything.

> **Amendment, 2026-09-13.** Phase 5's owed half is mostly discharged, and the
> mutation-floor line above has been overtaken.
>
> **1. "Nothing has run against a live backend, every suite fakes `fetch`."**
> `backend/scripts/one_whole_run.py` runs a real Chromium with the real
> extension against the real API, and has done so repeatedly. Of the six links
> that line names -- registers, uploads, is served shapes, is offered, runs,
> approves -- **four are now proved live**: the browser registers and is given
> a device id, its gestures reach the backend over the socket, `run_workflow`
> drives that same browser back through them, and Approve is pressed **in the
> real panel, as the browser being driven** rather than with the tenant's bare
> credential.
>
> **Served shapes and the offer followed the same evening**, so phase 5's line
> is discharged in full. `one_whole_run.py --offer` does the job by hand a
> second time and reads what the panel says about it:
>
>     -- the panel offered it off this browser's own gestures: 'Create a client'
>        matched 2 gestures in, values {"clientCode": "OFFER-3"}
>
> The offer lands in the middle of the doing, which is the point of it: `change`
> fires on blur, so clicking Save emits the previous field's gesture first and
> the click second, and between those two the tail is exactly the shape's first
> two positions.
>
> It also found a defect nothing on the backend side could have caught. A job
> of exactly `K_OFFER_AFTER` steps was SERVED and could never be offered:
> `recognise.match` scans k down from `shape.length - 1` because an offer has
> to leave something to finish, so a two-position shape has no k at or above
> the floor. Every browser cached it and walked it on every gesture for
> nothing. The offer replay could not have seen it either -- it only ever fed
> the matcher real mined jobs, all longer -- and fifteen fixtures had encoded
> the same off-by-one. `shape_of` refuses one now, and the replay reads
> identically before and after: 5 served, 5 offered as themselves, 2 never.
>
> **2. The floor "the rig ended at (80.2%)"** is no longer the measurement. The
> backend scores areas apart, each with its own ratchet, because one number
> over all of them hides the small one: measured 2026-09-13 over 2,294 mutants
> and the 2,895-test unit suite, the bridge (`application/skill/`) reads 85.8%
> and the ladder (`domain/execution/`) 91.8%. The ladder's first sweep read
> 83.9% and found real holes -- `diagnosis` 49.2%, `safety` 60.6%, every
> boundary in the breaker unstood-on and `safe_for_writes` unasserted on three
> of five branches.
>
> **3. A trigger can start a mined job**, which nothing in this spec
> anticipated: `Trigger` named a `SkillId`, so the only thing that could ever
> start a rig workflow was a person accepting an offer in the panel. Proved end
> to end the same day -- four triggers, four live runs, four writes that landed,
> the fourth with nobody asked because the three before it had earned it.

## Verification

- The rig's 673 tests travel, module by module, and the count on the
  backend side must not be smaller when the rig package is deleted.
- The mutation floor: the backend's step runs over the ported packages with
  the floor the rig ended at (80.2%), separately from the backend's existing
  floor, until the two are one suite.
- The offer replay is the acceptance test for shapes and recognition at
  every phase after 4: 8 of 8 named as themselves, 10 of 11 values by the
  end.
- The findings' live measurements (*An offer lands*, *A real key*) are
  repeated once through the backend before the rig is deleted, and the
  numbers written beside the originals.
- **The model path is measured against the rule-based one on one shared day,
  before either is deleted.** Both miners run over the same batches and the
  two answers are written down side by side: how many jobs each named, how
  many a person agrees with, and what one found that the other missed.

  This is a precondition on *Deletions*, not a nice-to-have, because the two
  do not meet anywhere. `MineObservations` reads `observations` and writes
  `task_candidates`; `mining_pass.mine` reads `gestures` and the pool and
  writes `workflows`. Neither reads the other's tables. So "the model path
  works" and "the rule-based path is safe to delete" are two claims, and only
  the first has ever been tested.

  Measured on 2026-09-09, on the 266 real batches this backend holds: the
  rule-based miner named **53 candidates**, the model path **2 workflows**
  from 507 gestures. That gap is mostly evidence -- the rig mined 8 from a
  larger corpus -- but it is the whole of the case against deleting anything
  yet, and it is the number the shared-day run has to move.

## Out of scope

- Temporal for the runner (phase two of the process model).
- Chains, occurrences stored per doing, API-first execution: unchanged by
  the port and still open as they were.
- Multi-tenant scale-out of the device channel.
- Any change to what the runner does, what the miner reads, or what the
  extension recognises. A port that changes behaviour is two changes.

## Open

- **Runner on Temporal, when.** Recommended: after phase 7, as its own spec,
  once a real week has run on one worker.
- **Console pages or the served page.** Recommended: serve `index.html` at
  `/rig` in phase 4 so nothing is lost while the pages are built in phase 6;
  delete the served page when the pages exist.
- **Where the pool lives.** The rig's pool is a table; the backend has
  blob storage. Recommended: the table, it is small and it is queried.
- **The old executor as fallback.** Kept behind a flag for skills with no
  evidence. Recommended: measure how many such skills exist before deciding
  whether it is worth keeping at all.
- **What starts a mined job when the job starts in a mailbox.** The operator's
  own case: a mail arrives, they read it, and what it says decides what they
  then do in the WMS. The two halves live in different subsystems today and
  neither knows the other exists.

  The mail half is already designed and partly built, and it is not capture:
  `mail.google.com`, Outlook and Yahoo are in `DEFAULT_EXCLUSIONS`, so the
  recorder never sees a mailbox, and `TriggerKind.WATCH` is a rule the
  browser holds and evaluates locally. `Term` carries the comparison the
  operator wrote by pointing at an example; `ValueAt` carries only where the
  order number sits, read at match time and passed as a parameter, never
  stored. `Trigger.from_message` is the parameter that comes from whatever
  fired it. `watch.js` exists in the extension with its tests.

  The WMS half is a mined workflow with its shape, its parameters and its
  runner -- everything this port is moving.

  So the work is a join, not a new mechanism: a watch fires, and what it
  starts is a mined workflow rather than a recorded skill, with the mail's
  `ValueAt` values landing in the run's `values`. That join has no design and
  no owner, and it is the first thing after phase 4 that a real operator
  would notice the absence of.

  Beyond it sits `TriggerKind.INBOUND`, named in the domain and deliberately
  not built: a mail or chat arriving server-side, which is what a Gmail
  connector would be. It buys the two things a watch cannot -- firing when no
  browser is open, and seeing signals that are not page gestures at all (a
  mail labelled, archived, moved) -- at the cost that mail reaches a
  connector, which is exactly what ADR 008 and the `Term`/`ValueAt` split
  were built to prevent. That is a trade for the tenant to make, not a
  default to pick.

  Recommended: specify the watch-to-mined-workflow join as its own spec once
  phase 4 lands and the routes exist to hang it on; leave INBOUND named and
  unbuilt until a customer asks for the unattended case, and decide the mail
  data question then, once, rather than under time pressure.
