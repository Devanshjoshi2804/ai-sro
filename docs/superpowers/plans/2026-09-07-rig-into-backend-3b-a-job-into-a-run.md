# The Rig Into The Backend — Plan 3b of 6: A Job Into A Run

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The half of the application layer that takes a job somebody has been
offered and actually does it: the planner that turns one step into one command,
the verifier that decides whether it happened, the loop that walks the steps,
the approvals a person gives, and the register of verified writes that buys a
job the right to run unasked.

**Architecture:** Plan 1 ported the pure domain, plan 2 the ports and Postgres,
plan 3a the evidence-to-jobs half of the application layer — all merged. This
plan writes the use cases over the same ports. Nothing here drives a browser or
calls a vendor directly: the `Channel` and `Asker` ports do that, and every test
runs against fakes.

**Tech Stack:** Python 3.12, asyncio, pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`
(*Application → use cases*, *Sequence* step 3, *The process model*).

**Base:** branch `rig-into-backend-3b` off `main`, which carries plans 1, 2 and 3a.

**Scope, and the gap this plan closes.** Plan 3a took evidence to jobs. This
takes a job to a run. It also claims the pair the final review found unowned:
**`capture/devices.py` and `analytics/audit.py`**, with `test_devices.py`'s
use-case half. Routes remain phase 4.

## Global Constraints

- **Layering**, enforced by `uv run lint-imports` (**4 contracts kept**):
  `sro.domain` imports nothing of ours and no framework — no pydantic, no
  SQLAlchemy, no `typing.Any`, no bare generics. `sro.application` imports
  domain and its own ports, never `sro.infrastructure`. A use case takes ports
  as parameters and constructs none.
- **Baseline on main** (measured 2026-09-07 at `b062fb9`): `uv run mypy src tests`
  **312 errors in 68 files**, none in a file any of these plans touches;
  `uv run mypy src tests/unit/fakes.py` **clean**; `uv run ruff format --check .`
  **2 files**; `uv run lint-imports` **4 kept**; `uv run pytest tests/unit -q`
  **1942**; `tests/integration` minus `test_steel_capture.py` (which fails
  environmentally) **111**; `tests/contract` **102 passed and 1 pre-existing
  failure** (`test_observation_payloads.py::…[shape-identity]` — **do not fix
  it**). Green means none of these grows.
- **The rig is the source of truth**: `new_agent_arch/src/rig/`. A port that
  changes behaviour is two changes. Where the rig's rule and a backend
  convention disagree on anything but naming, the rig's rule wins and the
  disagreement is written into the module.
- **Ported tests keep their names**, and one that does not travel is listed by
  name in this plan's ledger with the plan that owns it.
- **Formatting**: `ruff format` only the files you touched, by name.
- **Untracked files**: never delete, move, rename or stage one.
- **Committing** uses a private index, because agents share this worktree and
  `$(mktemp)` alone seeds an EMPTY index whose commit deletes the repository:
  `export GIT_INDEX_FILE=$(mktemp -u /tmp/idx.XXXXXX)`, `git read-tree HEAD`,
  `git add -- <files by name>`, `git commit`, `unset GIT_INDEX_FILE`, `git reset`.
- **This machine cannot auto-detect a git identity** (the hostname resolves to
  `Mac.(none)`). Export `GIT_AUTHOR_NAME`/`GIT_COMMITTER_NAME` as
  `Devansh Joshi` and the matching `_EMAIL` as `devansh.j@GGN002963.local`.
  **Write nothing to any git config** — that is the user's machine.

## The four test rules this project has paid for

Each was learned by a review finding a green suite that proved nothing. They
are constraints, not advice.

1. **Guard the caller, not only the rule.** Plan 3a's final review found three
   blocking gaps of one shape: the domain half of a rule was well tested and
   *the caller passing it* was not — a shape key minted from a set instead of an
   ordered walk, a prompt block that stopped reaching the token budget, a
   cross-system bonus that stopped reaching the window. All three passed every
   test on every seed. **The runner has far more of these seams than the miner
   did**: every argument it threads into `plan_step`, `verify` and the channel
   is one. When you finish a use case, mutate each argument at the call site,
   not only the function that receives it.
2. **A mutation touching set or dict ordering must be re-run under several
   `PYTHONHASHSEED` values** before you call it killed. Two "kills" on this
   project were hash luck; a third survived all eight seeds and was missed
   because nobody looked.
3. **Never date a fixture "today".** One plan's whole suite passed only because
   its `NOW` was the day it was written; a mutant that ignored the caller's
   clock entirely went unnoticed until the date was moved.
4. **Where a comment records a measurement or a decision that cost something,
   there must be a test that fails when the thing it describes changes.** Ten
   such comments were found unguarded in plan 3a alone.

## What you inherit, and what is missing

Ported and merged, to be used and never re-implemented:
- `sro/domain/execution/planning.py` — `PLAN_SCHEMA`, `PLAN_INSTRUCTIONS`,
  `Look`, `Planned`, `value_for`, `unreplayable`, `SIGHT_SCHEMA`,
  `SIGHT_ACTIONS`, `SIGHT_INSTRUCTIONS`, `KINDS`
- `sro/domain/execution/belts.py` — `StepVerdict`, `expected_statuses`,
  `confirming_read`, `mentions`, `status_of`, `SCREEN_SCHEMA`,
  `SCREEN_INSTRUCTIONS`, `RunProof`, `earned_from`, `state_verified`,
  `K_WEAK_LOCATORS`, `K_EARNED_RUNS`, `STATE_BELTS`
- `sro/domain/execution/evidence.py` — `Locator`, `locators_for`, `origin_of`,
  `primary_gesture`, `recorded_call`, `writes`, `allowlist`, `READ_METHODS`
- `sro/domain/execution/workflow_run.py` — `WorkflowRun`, `RunStep`,
  `OUTCOMES`, `VERDICTS`, `new_run_id`
- Ports: `Asker`, `Channel` (with `Reply`), `WorkflowRunRepository`,
  `WorkflowRepository`, `GestureRepository`, `OfferRepository`, `SpendRepository`
- From plan 3a: `over_cap` (`application/intent/spend.py`), `counsel` and
  `record_offer`, `shapes_for`, the mining pass.

**Three things this plan must supply that nothing has yet:**
1. **`sro.config` has no `daily_usd_cap`.** `read_new_gestures` and `mine` take
   `cap_usd` as a parameter because there is nowhere to read one from. The
   runner is a third paid loop. The spec folds the rig's `config.py` into
   `sro.config` with the `RIG_` prefix dropped — **do that here** (Task 1), so
   phase 4's routes have a value to pass.
2. **`FakeUnitOfWork`'s poisoned-session mode does not discard writes on
   rollback.** Any guarantee shaped *"the bill lands even though the work did
   not"* — and the runner has several — is unprovable against the fake alone.
   Plan 3a lost one of these and only recovered it because a reviewer wrote a
   Postgres probe. **Where a task makes such a claim, it owes an integration
   test, not only a unit test.**
3. **`WorkflowRunRepository` has no batch tally.** Plan 3a's `shapes_for` loads
   every run of every proven workflow to count two integers, which is O(all
   history) on the hottest read in the system. It gates phase 4, and the
   `earned` register in Task 4 needs the same numbers — **add
   `tallies(tenant_id) -> Mapping[str, tuple[int, int]]` there** (port, Postgres
   implementation, fake, contract body) and let `shapes_for` use it.

---

## Task 0: The branch and the baseline

- [ ] **Step 1:** `git checkout main && git checkout -b rig-into-backend-3b`
- [ ] **Step 2:** Record all seven gates from *Global Constraints*, at the branch
      base, into the ledger. Plan 2 measured five of seven and a pre-existing
      failure hid behind the gap for ten tasks.

**Done by the controller, not a subagent.**

---

## Task 1: The cap's home, and the batch tally

**Files:** `backend/src/sro/config.py`, `application/ports/repositories.py`,
`infrastructure/db/workflow_runs.py`, `tests/unit/fakes.py`,
`tests/contract/test_the_repositories_agree.py`,
`application/skill/serve_shapes.py`, and the integration suite.

The two debts above, paid before anything depends on them.

- `daily_usd_cap: float` on the settings object, carrying the rig's docstring
  from `new_agent_arch/src/rig/config.py` verbatim — negative means no cap, zero
  disables the asking, and capture keeps running either way.
- `tallies(tenant_id) -> Mapping[str, tuple[int, int]]` — `(runs, held)` per
  workflow, one `GROUP BY`, with a contract body so the fake is held to it, and
  `shapes_for` rewritten to call it once instead of `for_workflow` per workflow.

- [ ] Tests first: the tally over a tenant with several workflows and mixed
      outcomes; a workflow with no runs absent or zero; another tenant's runs
      excluded. Then the contract body, then the Postgres implementation.
- [ ] Prove the N+1 is gone: assert the repository was called once, not once per
      workflow.

---

## Task 2: The planner

**Files:** `backend/src/sro/application/execution/plan_step.py`,
`tests/unit/application/rig/test_planner.py`

From `new_agent_arch/src/rig/planner.py`: `plan_step` and `plan_by_sight`, with
the rig's exact signatures. The pure half is already in
`sro/domain/execution/planning.py`; **import it, do not restate it**.

The 27 rig tests plan 1 deferred by name are this task's. Three rules to keep:
- **The evidence's locators are sent, never the model's.** The model chooses
  *which* control, the demonstration says *where* it is.
- **A replayed call whose url or headers carry a struck-out credential is
  downgraded to the interface**, because a request with `«redacted»` in it
  answers nothing.
- **The sight rung is asked only after both evidence rungs missed with
  `control_not_found`, and only with a picture.** It answers a point, and the
  step it produces is recorded as matched by sight and marks the job stale.

---

## Task 3: The verifier

**Files:** `backend/src/sro/application/execution/verify.py`,
`tests/unit/application/rig/test_verify.py`

From `new_agent_arch/src/rig/verify.py`: `async def verify` and its belt order.
The pure half is in `sro/domain/execution/belts.py`; import it.

The 24 rig tests plan 1 deferred are this task's. **The belt order is the
product**: status, then a confirming read, then — least and last — a picture. A
model reading a screenshot is not evidence anything was written, and
`state_verified` is what `earned` counts. Two specifics:
- A probe whose url carries a redaction marker is **never sent**.
- A read must have come back 2xx before its body means anything; a 404 with a
  body that matches nothing once marked a correct write failed.

---

## Task 4: Effects, and what a job earns

**Files:** `backend/src/sro/application/execution/effects.py`,
`tests/unit/application/rig/test_effects.py`

`record_effect`, `forget_effects`, and `earned` over the `RunProof` rows the
repository assembles — plan 2 landed `proofs()`, plan 1 landed `earned_from`.
Use Task 1's `tallies` where it fits.

**One failed write empties the register for that workflow.** Three runs whose
every write is state-verified is what buys a job the right to run unasked, and
a picture never counts.

---

## Task 5: The approvals register

**Files:** `backend/src/sro/application/execution/approvals.py`,
`tests/unit/application/rig/test_approvals.py`

`Approvals` and `Aborts` from `new_agent_arch/src/rig/runner.py:42-110`.
In-process events on one worker, per *The process model* — say so in the module
docstring, name Temporal as the upgrade, and note that the router forwards to
the worker holding the socket.

`K_APPROVAL_WAIT_S = 300.0`. A step waiting on a person is `awaiting`; the
first tap wins; a second is not a second authorisation.

---

## Task 6: The run loop

**Files:** `backend/src/sro/application/execution/run_workflow.py`,
`tests/unit/application/rig/test_runner.py`

The skeleton of `run_workflow`: the claimed row read back as the authority for
what was asked, look → plan → perform → verify → record per step, the step
budget (`K_STEP_SLACK`), `_fell_over`, and `fail_orphans` at startup.

**The largest suite in the port.** Split your work by rig test section and
commit as you go rather than in one landing.

---

## Task 7: The rungs and the gates

**Files:** the same module, extended; `tests/unit/application/rig/test_runner.py`

The Pro rescue after a first failure, the sight rung below it, `may_write` and
refusal, the withheld list a dry run produces, the approval wait, `from_step`,
and earned autonomy.

**`may_write` is the rule that decides whether a person is asked.** Every
mutation of it must kill a test, and the ones that matter are at the *call
site*: a step that writes, on a job that has not earned it, with no approval,
must not be sent.

---

## Task 8: Devices and the audit

**Files:** `backend/src/sro/application/capture/devices.py`,
`backend/src/sro/application/analytics/audit.py`, and their tests

The pair the final review found unowned. `test_devices.py`'s use-case half —
register, revoke, drop the socket — over the `revoked_at` column plan 2 added
and the `Channel.drop` plan 2 landed. The audit assembles the `since` reads plan
2 gave every repository. Its route-level tests stay for phase 4; list them.

---

## Task 9: The count, and what is left

Every rig test in `test_planner.py` (28), `test_verify.py` (30),
`test_runner.py` (66), `test_effects.py` (9), `test_devices.py` (13) — **146** —
accounted for as ported here, left to phase 4 by name, or dropped with a reason.
Compare against the rig's files; do not trust this arithmetic. Two counts in
this project were wrong in ways only a real comparison caught, and plan 3a's
brief was off by one *and* omitted a whole file.

Fill the ledger below, and write the carried items into the plan itself — a
ledger in a gitignored directory does not travel.

---

## Ledger

| Rig test file | Rig / ported here | Left, and to which plan |
|---|---|---|
| `test_planner.py` | 28 / | |
| `test_verify.py` | 30 / | |
| `test_runner.py` | 66 / | |
| `test_effects.py` | 9 / | |
| `test_devices.py` | 13 / | |
| **Total** | **146 /** | |

**Added by this plan:** (fill in)

**Gates at head:** (fill in all seven)
