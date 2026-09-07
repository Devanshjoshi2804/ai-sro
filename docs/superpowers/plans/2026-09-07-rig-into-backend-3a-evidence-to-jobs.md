# The Rig Into The Backend — Plan 3a of 6: Evidence Into Jobs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The half of the application layer that turns a day of captured gestures
into jobs a person can be offered: the reading loop, the window, the mining
pass, the checks it survives, the shapes served to a browser, and the chat door.

**Architecture:** Plan 1 ported the pure domain; plan 2 gave it ports and
Postgres. This plan writes the use cases that stand between them — each one
file, each over the ports, none of them touching a driver or a session. What is
pure goes to `sro.domain` beside plan 1's work; what asks a model or a
repository goes to `sro.application`.

**Tech Stack:** Python 3.12, SQLAlchemy 2 async (behind repositories), pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`
(*Application → use cases*, *Sequence* step 3).

**Base:** branch `rig-into-backend-3a` off `main`, which now carries plans 1 and 2.

**Scope note:** the spec's phase 3 is one plan. It is split in two because it is
~260 tests, two to three times plan 2, and the runner alone is 66. This plan is
evidence → jobs; **plan 3b** is job → run (the planner, the verifier, the runner
loop, approvals, effects). They share only the repositories plan 2 landed.

## Global Constraints

- **Layering**, enforced by `uv run lint-imports` (**4 contracts kept**):
  `sro.domain` imports nothing of ours and no framework — no pydantic, no
  SQLAlchemy, no `typing.Any`, no bare generics. `sro.application` imports
  domain and its own ports, never `sro.infrastructure`. A use case takes ports
  as parameters; it never constructs one.
- **Baseline on main** (measured 2026-09-07, at `820cbb2`): `uv run mypy src tests`
  **312 errors in 68 files**; `uv run mypy src tests/unit/fakes.py` **clean**;
  `uv run ruff format --check .` **2 files**; `uv run pytest tests/unit -q`
  **1752**; `tests/integration` (minus `test_steel_capture.py`, which fails
  environmentally) **110**; `tests/contract` **102 passed and 1 pre-existing
  failure** (`test_observation_payloads.py::…[shape-identity]`, byte-identical
  to before this work — do not fix it). Green means none of these grows.
- **Formatting.** `ruff format` only the files you touched, by name. Never
  `ruff format .` — it rewrites the two pre-existing violations.
- **Untracked files.** Never delete, move, rename or stage one.
  `backend/.gmail-token.json.old-client`, `backend/old-client_secret_*.disabled`
  and every `rig.db*` stay exactly where they are. Stage only files you created
  or edited, by name.
- **Committing** uses a private index, because several agents share this
  worktree and three commits have already swallowed another's staged files.
  `$(mktemp)` seeds an EMPTY index and would delete the repository in your
  commit's tree, so the recipe is exactly:
  `export GIT_INDEX_FILE=$(mktemp -u /tmp/idx.XXXXXX)`, `git read-tree HEAD`,
  `git add -- <files by name>`, `git commit`, `unset GIT_INDEX_FILE`,
  `git reset`. Then `git ls-tree -r HEAD --name-only | wc -l` from the repo root
  must still be 2766.
- **The rig is the source of truth.** `new_agent_arch/src/rig/`. A port that
  changes behaviour is two changes. Where the rig's rule and the backend's
  convention disagree on anything but naming, the rig's rule wins and the
  disagreement is written down in the module.
- **Ported tests keep their names.** A rig test that travels keeps its name and
  the meaning of its assertions. One that does not travel is listed by name in
  this plan's ledger, with the plan that owns it.
- **A test must fail against a plausible wrong implementation.** Two reviews on
  plan 2 found tests passing against deliberately broken code. Where you assert
  an order, plant rows that tie on the sort key — and plant them in the order
  that *disagrees* with the answer you want, because at these row counts
  Postgres returns reverse-insertion order on a tie and a naive plant is
  satisfied by the bug.
- **Fakes are held to their stores.** `tests/contract/test_the_repositories_agree.py`
  runs one suite against both. If you add a repository method, add its contract
  body too.

## What plan 2 left you

- Ports: `Asker` (`application/ports/model.py`), `Channel`
  (`application/ports/channel.py`), and six repository protocols in
  `application/ports/repositories.py` — `GestureRepository`, `PoolRepository`,
  `WorkflowRepository`, `WorkflowRunRepository`, `OfferRepository`,
  `ChatRepository`, `SpendRepository` — all on `UnitOfWork`, with fakes in
  `tests/unit/fakes.py` and Postgres implementations under `infrastructure/db/`.
- Domain from plan 1: `observation/gesture.py`, `observation/identity.py`
  (`shape_key`, `resolve`, `Resolution`), `observation/values.py`,
  `observation/trim.py`, `observation/redaction.py`, `skill/workflow.py`,
  `skill/learned.py`, `skill/shape.py` (`shape_of`, `typed_at`, `walkable`),
  `skill/offers.py` (`counsel_over`, `fate_of`, `clamped`, `OfferRow`, `Offer`),
  `shared/prices.py` (`Answer`, `Effort`, `price`, `DaySpend`), and from plan 2
  `observation/pool.py`, `observation/mining.py`, `chat/reading.py`.
- **Carried forward and yours to honour:** `clamped`, `K_WINDOW` and `K_ENOUGH`
  have no production caller yet — counsel's "half or more diverged" rule
  depends on this plan passing `limit=K_WINDOW` and checking
  `len(newest) == K_ENOUGH`; and `record_offer` must call `fate_of` and
  `clamped` itself, because nothing enforces the fate vocabulary or the clock
  clamp at the storage boundary.

## File map

Created, domain (pure):

| File | Holds |
|---|---|
| `backend/src/sro/domain/observation/window.py` | `tokens`, `evidence_tokens`, `Packed`, `Window`, `as_evidence`, `strength`, `arrange`, `pack`, and `K_WINDOW_TOKENS` / `K_MIN_GESTURES` / `K_MAX_GESTURE_TOKENS` / `K_ENDS` / `K_POOL_WAIT` / `K_POOL_BONUS` / `K_MAX_TEXT_CHARS` / `K_MAX_ITEMS` |
| `backend/src/sro/domain/skill/checks.py` | `Rejection`, `Coverage`, `validate`, `coverage`, `K_MIN_COVERAGE`, `K_MAX_SKEW` |
| `backend/src/sro/domain/skill/umbrella.py` | `INSTRUCTIONS`, `WORKFLOW_SCHEMA`, `bounded_crossings`, `build_prompt`, `PROMPT_OVERHEAD_TOKENS`, `workflow_from`, `K_SAMPLES`, `K_EFFORT`, `K_MAX_CROSSING_TOKENS` |
| `backend/src/sro/domain/observation/reading.py` | `INSTRUCTIONS`, `INTENT_SCHEMA`, `CONFIDENCE_VALUES`, `one_line`, `intent_from`, `TAIL` |

Created, application (over ports):

| File | Holds |
|---|---|
| `backend/src/sro/application/observation/read_gesture.py` | `read_gesture`, `read_new_gestures` |
| `backend/src/sro/application/intent/spend.py` | `spent_today`, `over_cap`, `SPENT_IN` |
| `backend/src/sro/application/observation/mine.py` | `mine`, `MineResult`, `new_pass_id`, `learn_parameters`, `rekey_workflows` |
| `backend/src/sro/application/skill/serve_shapes.py` | `shapes_for` |
| `backend/src/sro/application/skill/counsel.py` | `counsel` |
| `backend/src/sro/application/skill/record_offer.py` | `record_offer` |
| `backend/src/sro/application/chat/understand.py` | `understand`, `Understood` |

Tests: `backend/tests/unit/domain/rig/` for the pure ones,
`backend/tests/unit/application/rig/` for the use cases, all against the fakes.

---

## Task 0: The branch and the baseline

- [ ] **Step 1: Branch from main**

```bash
git checkout main && git checkout -b rig-into-backend-3a
```

- [ ] **Step 2: Record every gate, including the two the last plan forgot**

```bash
cd backend
uv run mypy src tests | tail -1
uv run mypy src tests/unit/fakes.py | tail -1
uv run ruff format --check . | tail -1
uv run lint-imports | tail -1
uv run pytest tests/unit -q | tail -1
uv run pytest tests/contract -q | tail -1
uv run pytest tests/integration -q --ignore=tests/integration/test_steel_capture.py | tail -1
```

Expect the Global Constraints' numbers. Write all seven into the ledger.
`tests/contract` and `tests/integration` were missing from plan 2's baseline and
a pre-existing failure went unnoticed for the whole plan as a result.

**Done by the controller, not a subagent.**

---

## Task 1: The window

**Files:**
- Create: `backend/src/sro/domain/observation/window.py`
- Test: `backend/tests/unit/domain/rig/test_window.py`

**Interfaces:**
- Consumes: `Gesture`, `Intent` (`domain/observation/gesture.py`), `trim`
  (`domain/observation/trim.py`).
- Produces: `pack(gestures, intents, pool, known, kb, budget=K_WINDOW_TOKENS, linked=None) -> Window`,
  `as_evidence(gesture, intent) -> dict[str, object]`,
  `strength(gesture, intent, linked) -> float`, `arrange(items) -> list[Packed]`,
  `tokens(text) -> int`, `evidence_tokens(evidence) -> int`, and the frozen
  `Packed(gesture_id, at, evidence, strength, tokens)` and `Window`.

Source: `new_agent_arch/src/rig/window.py` in full. It is pure — it imports only
`Gesture`, `Intent` and `trim` — so it goes to the domain, not the application,
notwithstanding the spec's file list, which enumerates use cases and not their
pure helpers.

`dict[str, Any]` becomes `dict[str, object]` throughout. `_clip` keeps its
behaviour exactly: `K_MAX_TEXT_CHARS` and `K_MAX_ITEMS` are what stop one
enormous DOM label from eating a window.

- [ ] **Step 1: Port the tests first, and watch them fail**

All 19 from `new_agent_arch/tests/test_window.py`, names unchanged.

- [ ] **Step 2: Write the module** — verbatim but for the typing changes.

- [ ] **Step 3: Gates, then commit**

```bash
git commit -m "feat(domain): the window a mining pass is shown"
```

---

## Task 2: The checks a proposal survives

**Files:**
- Create: `backend/src/sro/domain/skill/checks.py`
- Test: `backend/tests/unit/domain/rig/test_checks.py`

**Interfaces:**
- Consumes: `Workflow` (`domain/skill/workflow.py`), `Window` (Task 1).
- Produces: `validate(workflow, evidence) -> Rejection | None`,
  `coverage(workflows, window) -> Coverage`, `Rejection`, `Coverage`,
  `K_MIN_COVERAGE = 0.5`, `K_MAX_SKEW = 0.4`.

Source: `new_agent_arch/src/rig/checks.py` in full, including `_gini`. This is
the module that throws out a proposal citing evidence that does not exist —
the single most important guard against a model inventing a job — so every
rejection reason keeps its exact text.

- [ ] **Step 1: Port all 20 tests from `test_checks.py`, red first.**
- [ ] **Step 2: Write the module.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 3: The umbrella prompt

**Files:**
- Create: `backend/src/sro/domain/skill/umbrella.py`
- Test: `backend/tests/unit/domain/rig/test_umbrella.py`

**Interfaces:**
- Consumes: `Packed`, `Window` (Task 1), `Workflow`, `Step`, `new_workflow_id`.
- Produces: `build_prompt(window, crossings, known, kb) -> str`,
  `bounded_crossings(crossings) -> dict[str, list[str]]`,
  `workflow_from(raw: object, tenant: str) -> Workflow | None` (the rig's
  `_as_workflow`, made public because the use case in Task 6 calls it),
  `INSTRUCTIONS`, `WORKFLOW_SCHEMA`, `PROMPT_OVERHEAD_TOKENS`, `K_SAMPLES`,
  `K_EFFORT`.

Source: `new_agent_arch/src/rig/umbrella.py`, **everything except
`async def propose`**, which asks a model and belongs to Task 6.

`K_EFFORT` travels as `"high"`, which is what the rig ships. Carry with it what
the bake-off measured, because the constant looks harmless and is not: thinking
is billed *inside* `max_output_tokens` on Gemini, and at `high` over a day of
evidence Gemini 3.8 Flash spent 62,913 of 65,536 tokens thinking and was
truncated with 2,609 left to answer in, three runs out of three. At `medium` the
same model mined the same day successfully. Say so in the docstring; the choice
belongs to whoever configures a model, and they cannot make it if the number is
not written down.

- [ ] **Step 1: Port the pure tests from `test_umbrella.py`** — every test that
  does not call `propose`. List the ones that do not travel in the ledger with
  "Task 6".
- [ ] **Step 2: Write the module.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 4: Reading one gesture

**Files:**
- Create: `backend/src/sro/domain/observation/reading.py`
- Create: `backend/src/sro/application/observation/read_gesture.py`
- Test: `backend/tests/unit/domain/rig/test_reading.py`,
  `backend/tests/unit/application/rig/test_read_gesture.py`

**Interfaces:**
- Consumes: `Asker` (`application/ports/model.py`), `GestureRepository`,
  `SpendRepository`, `trim`, `Intent`, `ValueSeen`.
- Produces (domain): `INSTRUCTIONS`, `INTENT_SCHEMA`, `CONFIDENCE_VALUES`,
  `one_line(intent) -> str`, `intent_from(data, gesture, answer) -> Intent`,
  `TAIL = 8`.
- Produces (application):
  `read_gesture(gesture, *, tail: list[Intent], asker: Asker, model: str, image: bytes | None = None) -> Intent`
  — the rig's signature exactly — and
  `read_new_gestures(uow, *, tenant_id, asker, model, limit=200) -> int`.

Source: `new_agent_arch/src/rig/intents.py` and `read_new_gestures` /
`_read_unread` in `new_agent_arch/src/rig/api.py`.

Three rules the rig learned and this must keep:

1. **An intent row means a reading happened, whatever came back in it.** An
   error, or an answer whose `act` was the wrong type and got nulled, is never
   retried: the model was asked, it answered, and it was billed. What such a row
   gets instead is to be visible.
2. **One reading loop at a time, per store and tenant.** Two concurrent callers
   select the same unread gestures before either writes an intent, so every
   gesture in the race window is asked and billed twice. Use `one_at_a_time`
   (`application/shared/locks.py`, landed in plan 2) keyed by tenant — **not**
   by the bare word "reading", which is a lock that also makes two different
   tenants take turns for no reason.
3. **`over_cap` is checked before the loop asks anything** (Task 5). Reading
   stops; capture does not.

- [ ] **Step 1: Port all 18 tests from `test_intents.py`**, splitting them
  between the two files by whether they ask a model.
- [ ] **Step 2: Write both modules.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 5: The day's cap

**Files:**
- Create: `backend/src/sro/application/intent/spend.py`
- Test: `backend/tests/unit/application/rig/test_spend.py`

**Interfaces:**
- Consumes: `SpendRepository` (plan 2), `DaySpend` (`domain/shared/prices.py`).
- Produces: `spent_today(uow, tenant_id, *, now) -> DaySpend`,
  `over_cap(uow, tenant_id, *, now, cap_usd) -> str | None`, `SPENT_IN`.

Source: `spent_today`, `SPENT_IN` and `over_cap` in `new_agent_arch/src/rig/api.py`.
Plan 2 landed the repository that produces the numbers; this is the rule that
judges them. `over_cap` returns a **reason** — the sentence a 429 carries — or
`None`, and a negative cap means no cap, which is what a deliberate one-off
measurement wants. Zero disables the asking entirely.

- [ ] **Step 1: Write the tests** — the cap not reached, reached exactly,
  exceeded; a negative cap; a zero cap; and a day whose cost cannot be trusted
  (`blind > 0`), which must say so in the reason rather than reading as cheap.
- [ ] **Step 2: Write the module.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 6: The mining pass

**Files:**
- Create: `backend/src/sro/application/observation/mine.py`
- Test: `backend/tests/unit/application/rig/test_mine.py`

**Interfaces:**
- Consumes: everything above, plus `GestureRepository`, `PoolRepository`,
  `WorkflowRepository`, `Asker`, `resolve`/`shape_key` (`domain/observation/identity.py`),
  `parameters_across` (`domain/skill/learned.py`).
- Produces: `mine(uow, *, tenant_id, asker, model, kb="") -> MineResult`,
  `MineResult`, `new_pass_id`, `learn_parameters`, `rekey_workflows`.

Source: `new_agent_arch/src/rig/mine.py` in full, plus `propose` from
`umbrella.py`. This is the largest use case in the plan and the one with the
most rules that are easy to lose:

- The pool is aged **only on a pass the model actually answered** — six refused
  calls once retired a whole pool having read nothing — and only for evidence
  the window actually showed.
- `add_unclaimed` clears every cited id, not only those inside this window,
  because a pooled gesture is packed into the window beside fresh ones.
- A proposal is resolved against known workflows by `resolve`; only genuinely
  new ones count as `kept`, and the resolution kind is recorded.
- One pass, one model call, one `mining_passes` row that carries the bill. A
  workflow names the pass that found it and never copies its cost — three
  workflows out of one $0.04 call summed to $0.12 when they each carried it.
- `rekey_workflows` runs once at startup and rewrites `shape_key` where the rule
  that makes a key has changed.

- [ ] **Step 1: Port all 26 tests from `test_mine.py`** and the `propose` tests
  left by Task 3, against `FakeAsker` and the fakes. No test here may reach
  Postgres.
- [ ] **Step 2: Write the module.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 7: The shapes a browser is served

**Files:**
- Create: `backend/src/sro/application/skill/serve_shapes.py`
- Test: `backend/tests/unit/application/rig/test_serve_shapes.py`

**Interfaces:**
- Consumes: `shape_of`, `typed_at`, `walkable` (`domain/skill/shape.py`, plan 1),
  `WorkflowRepository`, `WorkflowRunRepository`, `OfferRepository`, `counsel`
  (Task 8).
- Produces: `shapes_for(uow, *, tenant_id, device_id=None) -> list[Shape]`.

Source: `new_agent_arch/src/rig/shapes.py`. Plan 1 ported the pure `shape_of`
and 11 of the 17 tests; the six left are this task's, by name in plan 1's
ledger: `test_an_unproven_workflow_is_not_served`,
`test_the_held_gate_is_per_workflow_and_never_silences_one_that_never_ran`,
`test_a_workflow_that_cannot_be_served_never_withdraws_the_ones_behind_it`,
`test_a_stored_key_from_an_older_rule_is_recomputed_once`,
`test_a_workflow_whose_evidence_is_partly_gone_keeps_its_key`,
`test_a_workflow_that_cannot_be_rekeyed_does_not_stop_the_others`.

The held gate: a workflow that has run and never held is not served. One that
has never run is served — never silence a job for failing a test it has not sat.

- [ ] **Step 1: Port the six, red first.**
- [ ] **Step 2: Write the use case.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 8: Counsel, and recording an offer

**Files:**
- Create: `backend/src/sro/application/skill/counsel.py`
- Create: `backend/src/sro/application/skill/record_offer.py`
- Test: `backend/tests/unit/application/rig/test_offers.py`

**Interfaces:**
- Consumes: `OfferRepository`, and from `domain/skill/offers.py` (plan 1)
  `counsel_over`, `fate_of`, `clamped`, `K_WINDOW`, `K_ENOUGH`, `K_OFFER_AFTER`,
  `new_offer_id`.
- Produces: `counsel(uow, *, tenant_id, workflow_id, device_id, now) -> Counsel`,
  `record_offer(uow, *, tenant_id, workflow_id, device_id, k, fate, run_id, now) -> Offer`.

Source: `new_agent_arch/src/rig/offers.py`'s `counsel` and `record_offer`.
Plan 1 ported the rules; plan 2 ported the queries; **this is the caller that
makes them true**, and three things depend only on it:

- `counsel` passes `limit=K_WINDOW` and applies `len(newest) == K_ENOUGH` — the
  domain cannot enforce a window size it is handed.
- `record_offer` calls `fate_of` to validate the fate, and `clamped` to hold a
  browser's clock to the rig's own now. Nothing at the storage boundary does
  either, so a browser a year fast would otherwise own the window for a year.
- The four tests plan 1 and plan 2 both deferred land here by name:
  `test_an_offer_is_recorded_under_an_id_of_its_own`,
  `test_an_arrival_nudge_is_not_evidence_either_way`,
  `test_only_the_newest_ten_offers_are_read`,
  `test_offers_in_the_same_second_are_read_in_the_order_they_arrived`.

- [ ] **Step 1: Write the tests, red first.**
- [ ] **Step 2: Write both use cases.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 9: The chat door

**Files:**
- Create: `backend/src/sro/application/chat/understand.py`
- Test: `backend/tests/unit/application/rig/test_understand.py`

**Interfaces:**
- Consumes: `Asker`, `WorkflowRepository`, `ChatRepository`, `ChatReading`.
- Produces: `understand(utterance, workflows, asker, model) -> Understood`,
  `Understood`.

Source: `new_agent_arch/src/rig/entry.py`. Two rules with scars on them:

- **The schema is a list of name/value pairs, not a map.** An
  `additionalProperties` map is refused by the developer API with a 400, and the
  door was dead until it changed. There is a package-wide test that walks every
  schema for this; make sure yours is in its scope.
- **The instruction says a job is a kind of work, not the one time it was done.**
  Without that sentence the door named no job for real sentences; with it, five
  of five.
- The reading's cost is recorded and **the sentence is not**: it is an
  operator's words about a warehouse, and the bill is what the row is for.

- [ ] **Step 1: Port all 9 tests from `test_entry.py`.**
- [ ] **Step 2: Write the use case.**
- [ ] **Step 3: Gates, then commit.**

---

## Task 10: The count, and what is left

- [ ] **Step 1: Count.** Every test in `test_window.py` (19), `test_checks.py`
  (20), `test_umbrella.py` (27), `test_intents.py` (18), `test_mine.py` (26),
  `test_shapes.py` (6 remaining), `test_entry.py` (9) — 125 — accounted for as
  ported here, left to plan 3b or 4 by name, or dropped with a reason.
- [ ] **Step 2: Land every minor deferred by a task review.**
- [ ] **Step 3: Fill in the ledger below, and commit.**

---

## Ledger

Counted by exact test-function name, `comm` over sorted lists, rig side read
from `new_agent_arch/tests/` rather than from this plan's own arithmetic. Two
earlier plans' counts were wrong where nobody did that comparison.

| Rig test file | Rig / ported here | Left, and to which plan |
|---|---|---|
| `test_window.py` | 19 / 19 | — |
| `test_checks.py` | 20 / 20 | — |
| `test_umbrella.py` | 27 / 27 | — |
| `test_intents.py` | 18 / 18 | — |
| `test_mine.py` | 26 / 26 | — |
| `test_shapes.py` | 6 remaining of 17 / 6 | — |
| `test_entry.py` | 9 / 8 | 1 — `test_no_schema_in_the_package_uses_what_the_developer_api_refuses`, already ported by **plan 1** into `tests/unit/domain/rig/test_planning.py`. This plan's brief double-counted it. |
| **Total** | **125 / 124** | **1, and plan 1 had already taken it.** Nothing is left to plan 3b or 4, and nothing was dropped. |

**Two corrections to the brief's arithmetic**, both found by comparing against
the rig rather than trusting the count:

1. `test_entry.py` is 9 in the rig but **8** were in this plan's scope. The
   schema walker travelled with plan 1, exactly as 11 of `test_shapes.py`'s 17
   did. The in-scope total is 124, not 125.
2. **`test_offers.py` is a rig file the brief's list omits entirely.** Task 8
   ported 7 of its tests for `counsel` and `record_offer`:
   `test_a_job_nobody_has_answered_is_offered_at_the_default`,
   `test_an_arrival_nudge_is_not_evidence_either_way`,
   `test_an_offer_is_recorded_under_an_id_of_its_own`,
   `test_an_offer_the_operator_did_not_refuse_breaks_the_run`,
   `test_offers_in_the_same_second_are_read_in_the_order_they_arrived`,
   `test_offers_that_keep_diverging_move_the_job_past_where_they_diverged`,
   `test_only_the_newest_ten_offers_are_read`. Two of them were **rebuilt rather
   than copied**, because the rig's own versions are satisfied by the bugs they
   were named for.

**Where they landed.** No rig test file maps to one backend file; the
domain/application line cuts through four of them.

| Rig file | Backend destination(s) |
|---|---|
| `test_window.py` | 19 → `tests/unit/domain/rig/test_window.py` |
| `test_checks.py` | 20 → `tests/unit/domain/rig/test_checks.py` |
| `test_umbrella.py` | 20 → `tests/unit/domain/rig/test_umbrella.py`; 7 → `tests/unit/application/rig/test_mine.py` (the ones that call `propose`, which is the mining use case's) |
| `test_intents.py` | 16 → `tests/unit/application/rig/test_read_gesture.py`; 2 → `tests/unit/domain/rig/test_reading.py` |
| `test_mine.py` | 26 → `tests/unit/application/rig/test_mine.py` |
| `test_shapes.py` (6 in scope) | 3 → `tests/unit/application/rig/test_mine.py` (`rekey_workflows`); 3 → `tests/unit/application/rig/test_serve_shapes.py` |
| `test_entry.py` (8 in scope) | 8 → `tests/unit/application/rig/test_understand.py` |
| `test_offers.py` (7) | 7 → `tests/unit/application/rig/test_offers.py` |

One plan-1 name was ported a **second** time on purpose:
`test_a_resting_job_is_served_marked_for_the_browser_that_refused_it` exists in
plan 1's `domain/rig/test_shapes.py` against the pure rule and again in
`application/rig/test_serve_shapes.py` against the use case that reads it.

**Added by this plan:** 187 unit tests (1752 → 1939) and 1 integration test
(110 → 111).

- **132 are ports** — the 124 in scope, the 7 from `test_offers.py`, and the one
  deliberate second port above.
- **55 are new guards** with no rig test behind them, and the integration test is
  a 56th. They are what mutation testing bought: `K_MAX_SKEW`, the `_PROBE`
  window, `evidence_tokens`' shape, the gesture-tier boundary, the skew band, a
  swallowed `raise` on the billed path, an unscoped tail, `READING_LIMIT`, a
  global mining lock, `shapes_for` committing a read, the lost-duplicate case
  that kills the cite-order mutation on every hash seed, and the store-failure
  path that the fake cannot model.

**Method for that split, and its limits:** exact test-function-name match
against the union of all 699 test names under `new_agent_arch/tests/`. A port
that had been renamed would count as new — none was, because every one of the
136 rig names in the seven files is accounted for with no residue. A new guard
that coincidentally reused a rig name would count as a port — none did; the 7
matches outside the seven files were checked individually and are all genuine
`test_offers.py` ports.

**Gates at head** (all seven, re-measured; baseline in brackets):

| Gate | Result |
|---|---|
| `mypy src tests` | 312 errors in 68 files [312 in 68] |
| `mypy src tests/unit/fakes.py` | clean [clean] |
| `ruff format --check .` | 2 files would be reformatted [2] |
| `lint-imports` | 4 kept, 0 broken [4 kept] |
| `pytest tests/unit` | 1939 passed [1936 at task 9; +3 from this task's deferred minors] |
| `pytest tests/contract` | 102 passed, 1 pre-existing failure [same, untouched by this plan] |
| `pytest tests/integration` | 111 passed, `test_steel_capture.py` ignored [111] |

---

## What this plan carries forward

Plans 3b and 4 need all of this, and the working ledger it came from is in a
gitignored directory. It travels here instead.

**1. `shapes_for` must not be wired to a route in plan 4 until a batch tally
exists.** The held tally calls `for_workflow` per proven workflow, loading every
run of every one, because `WorkflowRunRepository` has no count method — where
the rig used two index `COUNT`s. Measured against the fakes it is flatly linear
in total run rows: 20 workflows × 100 runs = 0.069s, × 500 = 0.391s. It is
O(all history) on the hottest read in the product, and it gets worse exactly as
a tenant adopts it. A tenant with a year of use is ~100k run rows and ~500k step
rows fetched and mapped **per heartbeat per browser**. Recommended shape:
`tallies(tenant_id) -> Mapping[str, tuple[int, int]]` over a `GROUP BY
workflow_id`, which also collapses the N+1 rather than shrinking it.

**2. `read_utterance` checks no cap.** That is the rig's own split — the route
answers the 429, not the use case — so **plan 4's `/v1/chat` must call
`over_cap` before it**. Nothing at the application layer can fail if a route
forgets, so this belongs in that task's brief as an explicit requirement rather
than as a note.

**3. The reading loop holds the tenant's entire history in memory, not one
day.** `gestures_for` and `intents_for` have no time bound, so every reading
pass deserialises every stored gesture and intent for the tenant, request and
response bodies included, and it grows monotonically. The upgrade path is
`GestureRepository.tail_for(stream_id, before)` — a port change across four
files, which is why it is not a fix round's. It is named as the upgrade path in
the `ponytail:` comment on the tail.

**4. The package-wide schema walker now survives a file move.** It was scoped to
`sro.domain`, so the rule that no schema uses an `additionalProperties` map —
the shape the Gemini Developer API refuses with a 400, and which once shipped
the chat door dead — held only while a schema happened to sit in the domain.
Moving `UNDERSTAND_SCHEMA` into the application layer *in the refused shape*
passed the entire suite silently. Task 10 widened the walk to `sro`, which takes
it from 6 schemas to 13 and brings four that reach the real vendor API under
guard for the first time: `sro.infrastructure.gemini.interpreter._SCHEMA`,
`._NAME_SCHEMA`, `._JUDGEMENT_SCHEMA`, and
`sro.infrastructure.transcription.gemini._SCHEMA`. The widening is itself
pinned (`walked >= 13`), because narrowing it back still finds six and would
have passed a bare truthiness check.

**5. `FakeUnitOfWork`'s poisoned-session mode does not discard writes on
rollback.** It models the session becoming unusable and rollback reviving it,
but not the loss — `FakeUnitOfWork` does not simulate rollback at all, and
making it do so for one repository would be a second untested claim. So half of
the mining pass's failure guarantee (the bill lands, the workflows do not) is
proved **only** by `tests/integration/test_workflow_repositories.py::
test_the_bill_is_written_on_a_session_the_save_killed`. Do not read a green unit
suite as covering that path.

**6. A mutation on set or dict ordering is not killed until it is killed on
several hash seeds.** Task 7's cite-order mutation survived on 2 of 8
`PYTHONHASHSEED` values, so "14 killed, 0 survivors" was partly seed luck; Task
9's sorted-on-missing mutant survived 3 of 8 against a three-parameter fixture.
And a fixture that *happens* to catch something is not the fix — what kills the
cite-order mutation on every seed is a lost **duplicate**, not a reversed order.

**7. Four rig tests in this plan were proven satisfied by the bugs they were
named for**, and were rebuilt rather than inherited. Do not treat a rig test's
existence as coverage of the thing its name claims.

**8. `MineObservations` in `application/observation/mine.py` is still live** and
wired in `container.py`. The rig's pass landed beside it as `mining_pass.py`.
The spec deletes the old miner at phase 7; until then, both exist.

## Unowned, and named here so neither half assumes the other took it

The spec's phase-3 acceptance names `test_devices` (the use-case half, 13 rig
tests) and its Application list names `capture/devices.py` and
`analytics/audit.py`. This plan's scope note gave plan 3b "the planner, the
verifier, the runner loop, approvals, effects" — so **neither half claimed
devices or audit**, and the final review caught the gap. Whichever plan takes
them must say so in its own scope note; if 3b declines, plan 4 owns them.

`sro.config` also still has no `daily_usd_cap`. `read_new_gestures` and `mine`
both take `cap_usd` as a parameter because there is nowhere to read one from,
and the spec folds the rig's `config.py` into `sro.config` with the `RIG_`
prefix dropped. Every route that calls a paid loop needs that value to exist.
