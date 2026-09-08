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

**The count above is one short, and the brief said not to trust it.** Counted
against the rig's own files: 146 is the number of `def test_` *functions*, but
`test_runner.py::test_a_claimed_run_that_disagrees_with_its_arguments_is_refused`
is `@pytest.mark.parametrize`d over two fields, so pytest collects **147 cases**
from those five files. The decorator travelled with the port, so both cases are
here; the file is 66 functions and 67 cases in the rig, and the same in the
backend. Every other file's function count in the brief was right.

| Rig test file | Rig | Ported by this plan | Landed in an earlier plan | Dropped | Left, and to which plan |
|---|---|---|---|---|---|
| `test_planner.py` | 28 | 27 | 1 (plan 1) | 0 | 0 |
| `test_verify.py` | 30 | 24 | 6 (plan 1) | 0 | 0 |
| `test_runner.py` | 66 fns / 67 cases | 66 / 67 | 0 | 0 | 0 |
| `test_effects.py` | 9 | 8 | 1 (plan 1) | 0 | 0 |
| `test_devices.py` | 13 | 2 whole + 1 half | 0 | 1 | 9 whole + 1 half (phase 4) |
| **Total** | **146 fns / 147 cases** | **127.5 / 128.5** | **8** | **1** | **9.5** |

Verified by name, not by tallying the task reports: every one of the rig's 146
test names was matched against every `def test_` in `backend/tests/`. Only two
rig runner names had no exact twin, and both are renames, not gaps (below).

**Where the ones that are not in the same-named backend file went:**

- `test_planner.py::test_the_schema_puts_why_last_and_kind_first` — plan 1, as
  `tests/unit/domain/rig/test_planning.py`. It asks the schema, not the rung.
- `test_verify.py` × 6 — plan 1, as `tests/unit/domain/rig/test_belts.py`:
  `test_expected_statuses_and_the_confirming_read_come_from_the_evidence`,
  `test_a_read_the_evidence_made_is_never_an_expected_write_status`,
  `test_a_call_that_never_returned_names_no_status_the_warehouse_gave`,
  `test_a_cited_gesture_the_store_lost_does_not_hide_the_evidence_behind_it`,
  `test_the_confirming_read_comes_after_the_write_and_came_back`,
  `test_a_step_whose_recorded_call_is_itself_a_read_has_nothing_to_confirm`.
  They ask only the pure belts.
- `test_effects.py::test_the_number_of_runs_autonomy_costs_is_the_one_a_person_agreed_to`
  — plan 1, also in `test_belts.py`.
- `test_runner.py::test_a_run_stopped_by_the_flag_is_forgotten_by_the_registers_when_it_ends`
  → `…_by_the_register_when_it_ends`, singular. Task 6 threads one register, not
  two: `Stops` is the rig's `Aborts` already in this codebase.
- `test_runner.py::test_an_approved_wait_leaves_nothing_waiting` →
  `tests/unit/application/rig/test_approvals.py::test_the_wait_is_popped_on_the_way_out_so_a_later_tap_finds_nothing`,
  strengthened: it also asserts the second tap returns `False`. It is a register
  test, and Task 5 owns the register.

**`test_devices.py`, the only file with anything left.** Its use-case half is
here; its route half cannot be written before the routes are.

- Ported: `test_revoking_a_browser_takes_it_offline_at_once` (own name);
  `test_a_token_is_issued_held_as_a_hash_and_revocable` (split three ways —
  issue and hash were already covered by
  `tests/unit/application/test_an_extension_uploads_what_it_saw.py`, the revoke
  half is `test_a_browser_is_revoked_once_and_the_second_press_moves_nothing`,
  and "a revoked token belongs to nobody" is
  `test_a_revoked_browser_is_refused_the_moment_it_speaks_again`); the roster
  half of `test_a_browser_sees_who_is_online_and_not_who_is_registered`, as
  `test_a_revoked_browser_stays_on_the_roster_carrying_when_it_ended` and
  `test_the_roster_is_this_tenants_browsers_most_recently_seen_first`.
- **Dropped, with its reason:** `test_a_fresh_issue_retires_the_earlier_token`.
  Backend registration is idempotent on `(tenant, principal, label)` and hands
  back the **same** secret, per `Registered.secret`: a reinstall that could not
  get its secret back is a device somebody has to delete by hand. Porting the
  rig's rule would break that deliberately-chosen behaviour.
- **Left to phase 4, by name (9 whole and 1 half).** Each is a status code on a
  route that does not exist yet — 401 for a forged bearer, 403 for a device
  reaching a tenant door, 400 for a register with no body, and the websocket
  handshake:
  1. `test_the_tenant_registers_a_browser_and_the_browser_then_speaks_for_itself`
  2. `test_a_devices_token_opens_its_own_socket_and_no_other`
  3. `test_an_approval_by_a_registered_browser_names_that_browser_whatever_the_body_says`
  4. `test_a_browser_approves_only_the_run_it_is_driving`
  5. `test_the_tenants_purse_and_the_other_browsers_days_are_not_a_devices`
  6. `test_an_empty_tenant_token_admits_nobody`
  7. `test_a_browser_with_a_token_of_its_own_reads_its_own_rest_whatever_it_asks_for`
  8. `test_a_browser_sees_who_is_online_and_not_who_is_registered` — the
     authorisation half only (a device token gets the online list and nothing more)
  9. `test_a_browser_posts_its_own_day_and_not_a_siblings`
  10. `test_a_browser_illustrates_its_own_batches_and_not_a_siblings`

The rig has **no** test file for the audit. Its route's rules are already here
as `tests/integration/test_spend_and_audit_reads.py`, at the repository level;
Task 8 added the caller's half as `tests/unit/application/rig/test_audit.py`.

**Added by this plan:** **231 collected test cases** — 228 unit, 2 contract, 1
integration. That reconciles exactly with this plan's recorded main baseline:
1942 + 228 = 2170, 102 + 2 = 104, 111 + 1 = 112. Seven new unit files (224
cases: `test_planner.py` 31, `test_verify.py` 32, `test_runner.py` 104,
`test_effects.py` 21, `test_approvals.py` 16, `test_audit.py` 10,
`test_devices.py` 10), plus `test_spend.py` +3 and `test_serve_shapes.py` +1,
the tally's contract body (`[fake]` and `[sql]`) and its one integration guard
that the tally is a single `GROUP BY`. The excess over the 128.5 ported cases is
guards written during the port, most of them to kill a mutation that a ported
test as written let live.

**Gates at head** (`976301c`, measured for this ledger):

| Gate | Expected | Measured |
|---|---|---|
| `uv run pytest tests/unit -q` | 2170 | **2170 passed** |
| `uv run pytest tests/contract -q` | 104 + 1 pre-existing failure | **104 passed, 1 failed** (`test_observation_payloads.py::…[shape-identity]` — not to be fixed) |
| `uv run pytest tests/integration -q --ignore=tests/integration/test_steel_capture.py` | 112 | **112 passed** |
| `uv run mypy src tests \| tail -1` | 312 in 68 | **312 errors in 68 files** |
| `uv run mypy src tests/unit/fakes.py` | clean | **Success, 345 files** |
| `uv run ruff format --check .` | 2 | **2 would be reformatted** |
| `uv run lint-imports \| tail -1` | 4 kept | **4 kept, 0 broken** |

One correction to the gate's own wording: the two unformatted files are
`src/sro/infrastructure/mcp/client.py` **and**
`tests/unit/application/test_teaching_two_candidates_as_one.py`, not two hunks in
`client.py`. Both are untouched by this branch (`git diff 07a6cd6..HEAD` names
neither), so both are pre-existing as claimed.

---

## Carried to phase 4

Seven things this plan built, proved and deliberately left half-wired. They are
here rather than only in a task report because a report in `.superpowers/` is
gitignored and does not travel.

1. **No route can reach a parked workflow run to stop it.** `Stops` is set only
   by `StopRun` (`application/execution/read_runs.py`), which resolves a *skill*
   run through `uow.runs`; nothing sets it for a `WorkflowRun`. The loop's half
   is built and proved — `run_workflow` asks `Stops` between steps and again
   after `Approvals.wait_for` returns, so a released wait is not read as a yes —
   but until a route sets the flag for a workflow run, **that check is dead in
   production**. Phase 4 owns the route's half.
2. **`run_workflow` has no production caller at all.** Grepping `src/` finds
   only its own definition and two docstrings; the sole caller is
   `tests/unit/application/rig/test_runner.py`. Phase 4 wires it.
3. **A run re-entered from a claimed row does not remember its `from_step`.**
   It is a parameter of `run_workflow` and is on no persisted field of
   `WorkflowRun`, so a resume route built without adding one would redo the
   steps the operator already did by hand.
4. **There is no un-revoke.** Now that revocation actually enforces — a revoked
   browser is refused the moment it speaks again — an administrator who revokes
   the wrong browser has no path back short of a hand-edited row.
   `DeviceRepository` has only `revoke`, `save` never writes `revoked_at` back,
   and `RegisterDevice` returns the *same* secret rather than a fresh one.
   Whoever designs that lifecycle owns the choice between clearing the row and
   issuing a second registration.
5. **Delete `ReadDevices` from `application/observation/register.py`.**
   `capture/devices.py::ReadRoster` is a strict superset over the identical
   repository call (`uow.devices.list_for_tenant`), and the wired route at
   `interface/http/v1/routers/agents.py:294-298` should point at `ReadRoster`
   with `online` added to `DeviceModel`. Two use cases over one `list_for_tenant`
   in two packages is how they drift.
6. **A parked step's `sent` holds a command that was never sent.** Deliberate:
   what `sent` carries is exactly what the person is being asked to approve, and
   `verdict == "awaiting"` is the real distinguisher. Anything downstream that
   reads `sent` as "this went out" — a panel, an audit line, a report — needs to
   know that and check the verdict.
7. **A dry run still performs a click whose demonstrated traffic the recorder
   never saw.** The withholding gate is `if not live and mutates`, on the narrow
   `writes()`, while the approval gate below it uses the wider `may_write`. This
   is the rig's documented asymmetry, ported deliberately and asserted on
   purpose — withholding every silent click would leave a dry run performing
   almost none of the job — and it is the one live write that escapes the gate by
   design.
