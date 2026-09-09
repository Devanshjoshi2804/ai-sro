# Phase 4b — The Doors That Write

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the backend's model-driven half a caller. `container.asker`,
`mining_pass.mine`, `run_workflow` and `read_utterance` are all built, all
tested, and all unreachable from outside the process; this plan puts seven
routes in front of them and closes the resource holes the write path has been
carrying since it was ported.

**Architecture:** Each route follows the shape 4a settled: a router under
`interface/http/v1/routers/`, a use-case class or bare function in
`application/`, a factory on `Container`, a request and response model in
`interface/http/schemas.py`. Nothing new is invented at the domain layer except
one persisted field. Two model-calling routes (`/v1/mine`, `/v1/chat`) refuse
before spending when there is no `Asker` and when the day's cap is reached; the
run route claims its row before it answers.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Alembic, pydantic v2,
pytest, mypy --strict, ruff, import-linter.

**Spec:** `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`

**Predecessor:** `docs/superpowers/plans/2026-09-08-rig-into-backend-4a-the-doors-that-read.md`
— its *What phase 4b inherits* section is the source for every carried item
below, and its Task 10 table is the route accounting this plan closes.

**Base:** `main` at `f51e0b2` (the 4a merge).

---

## Global Constraints

Every task's requirements implicitly include this section.

### The layers

- `sro.domain` is pure: no framework import, no pydantic, no `typing.Any`, no
  I/O. `sro.application` may import `sro.domain` and `sro.application.ports`,
  never `sro.infrastructure` or `sro.interface`. `sro.infrastructure` is
  reachable only through `sro.container`. **Four import-linter contracts must
  stay kept.**
- A route never reads a clock and never unpacks a bare `tenant_id`. It passes
  `ctx: RequestContext` to a use case, and the use case takes `now` from the
  container's clock. The reason is written at `container.py:325-343` — the one
  seam where passing the wrong tenant is the failure stays out of the interface
  layer.

### Errors

- Domain failures raise a `DomainError` subclass and are mapped to a status in
  `interface/http/errors.py:_STATUS_BY_ERROR`. Anything not in that mapping is a
  500, which is what the mapping's MRO walk exists to prevent.
- A dependency that is absent rather than a request that is wrong raises a plain
  `Exception` subclass named `…Unavailable`, registered in
  `install_error_handlers` — see `BrowserUnavailable`
  (`application/ports/browser.py:110`), `VaultUnavailable`
  (`application/ports/vault.py:28`), `SchedulerUnavailable`
  (`application/ports/schedule.py:37`). All three map to **503**.

### Money

- `daily_usd_cap: float = 5.0` in `config.py:298`. Its docstring **already names
  this plan's routes**: *"Over the cap the rig's `/v1/mine`, `/v1/chat` …"*.
- `over_cap(uow, tenant_id, now=…, cap_usd=…)` at
  `application/intent/spend.py:56` returns the refusal sentence or `None`. Its
  docstring says *"the sentence a 429 carries"*. **429 is not currently in
  `_TITLES` or `_SLUGS`** — Task 1 adds it.
- A negative cap means no cap. `cap_usd >= 0` and a blind day both refuse.

### Model names

Copy these values verbatim. They are the rig's, at `new_agent_arch/src/rig/config.py`:

| Setting | Value | Rig line |
|---|---|---|
| `gemini_mine_model` | `"gemini-3.1-pro-preview"` | `config.py:20` |
| `gemini_plan_model` | `"gemini-3.8-flash"` | `config.py:41` |
| `gemini_rescue_model` | `"gemini-3.1-pro-preview"` | `config.py:45` |

The backend already carries `gemini_interpreter_model = "gemini-3.1-pro-preview"`
(`config.py:334`). **Do not reuse it for mining.** They are the same string today
and they answer different questions; one setting serving two purposes means the
next person to re-tune one silently re-tunes the other.

### The four test rules this project has paid for

1. **Guard the caller, not only the rule.** Mutate each argument at each call
   site and report every one. Twenty-nine findings across phase 4a's eight tasks
   came from this.

   **Restated, because it has now caught something in every single task of this
   plan and nothing else has.** Tasks 1, 2 and 3 each shipped tests that proved
   the rule and left the *traffic* unpinned:

   | Task | What survived | Why the suite could not see it |
   |---|---|---|
   | 1 | `_SLUGS[429]` deleted; the refusal sentence replaced with `"nope"` | the 503 test built its own exception instead of calling the guard |
   | 2 | `error`, `left_out`, `lost_pool`, `unpriced` each replaced with a literal | every assertion used the field's own **default** value |
   | 3 | the route passing `utterance=""` instead of `body.utterance` | 45 tests asserted the answer's shape, or that the sentence was *absent*; none that it was the one typed |

   So the rule as a **checklist you must be able to answer for every route**:
   - **Every value the caller supplies** — each request-body field, each path and
     query parameter — has a test that fails when the route passes a constant
     instead. Not "a test that sends it": a test that *dies* when it is ignored.
   - **Every value the caller receives** — each response-model field — has a test
     that gives it a **non-default** value. A field asserted only at its own
     default is indistinguishable from a constant, and that is not a hypothetical:
     `mining_passes` holds a real row whose `error` says *"truncated: the answer
     hit the 65536 output-token ceiling after 2610 tokens"*, a $2.00 call that
     returned nothing, which the route answered `200` with `error: null`.
   - **Write these red first.** Apply the constant, watch the test fail, revert,
     watch it pass. Task 2 wrote code before tests and this is precisely the gap
     that produced; Task 3 did the same and M13 survived 45 tests.

2. **Any test whose result depends on set or dict ordering must hold under
   several `PYTHONHASHSEED` values — and the only way to vary it is a fresh
   interpreter.** `PYTHONHASHSEED` is read **once at interpreter start**, so
   `monkeypatch.setenv("PYTHONHASHSEED", ...)` changes nothing: a parameterised
   test that only sets it asserts the same arrangement four times and proves
   nothing. Use `subprocess.run([sys.executable, ...], env={**os.environ,
   "PYTHONHASHSEED": seed})` — see `tests/unit/application/rig/test_read_chat.py:396`
   for the shape.

   **And there is no random-ordering pytest plugin in this repo.** `-p randomly`
   and `-p no:randomly` both do nothing here; neither proves nor disproves
   anything about ordering.

   This project has been bitten by a test that sorted two rows by a `FakeClock`
   returning the same instant every call, so the tie broke on an unplanted id —
   and twice more by *instruments that measured nothing*: `-p no:randomly`
   disabling a plugin that was never installed, and a `grep` for stale
   `type: ignore` comments that missed all eight because mypy capitalises
   "Unused". **Prove your instrument fires before you trust a zero from it.**
3. **Never date a fixture "today."**
4. **Where a comment records a measurement or a decision that cost something, a
   test must fail when that thing changes.**

### The mypy gate does not read the tests, and eight stale suppressions prove it

`make lint-backend` runs `uv run mypy src tests/unit/fakes.py`. **The rest of
`tests/` is unchecked.** Measured 2026-09-09:

```
uv run mypy src tests/unit/fakes.py   →  clean, 359 files      (the gate)
uv run mypy src tests                 →  325 errors in 71 files
uv run mypy --warn-unused-ignores src tests | grep '\[unused-ignore\]'  →  8
```

Widening the gate means fixing 325 errors and is not this plan's job. **The eight
are.** They are stale `# type: ignore` comments that suppress nothing, in
`test_vision_step.py`, `test_the_backend_stores_what_the_browser_sent.py` (three),
`test_running_what_the_operator_previewed.py`, `test_teaching_what_was_watched.py`
(two) and `test_teaching_two_candidates_as_one.py` — all pre-existing, none from
this phase.

**Why it is worth eight lines:** Task 1 put `# type: ignore[attr-defined]` on
`container.mine_pass()` and `container.read_chat()` because neither existed yet.
Tasks 2 and 3 added them, the suppressions went stale, and **nothing could see
it** — Task 3 found them by reading. A suppression that outlives its reason is a
silenced future error, and this is the file where the next one will be silenced.

Carried as an item for whoever has a free tree, not a task requirement.

### A fake more permissive than the thing it doubles manufactures confidence

`FakeUnitOfWork` exposes its repositories from `__init__`; the real one assigns
them inside `__aenter__`. Two routes shipped dead against real Postgres while
2299 unit tests were green because of exactly this. **Every route in this plan
gets an integration test against real Postgres, not only a unit test against the
fake.**

### The eight gates

Measured as a delta against the task's starting commit, from `backend/`:

```
uv run pytest tests/unit -q
uv run pytest tests/contract -q
uv run pytest tests/integration -q
uv run pytest tests/browser -q
uv run mypy src tests/unit/fakes.py
uv run ruff check .
uv run ruff format --check .
uv run lint-imports
```

**Baselines at `0d003ef`, the branch point before Task 1:** unit **2311**,
contract **109**, integration **130**, browser **86** (5m23s), mypy clean over
**354** files, ruff check clean, `ruff format --check` **652 formatted, 0 to
reformat**, lint-imports **4 kept, 0 broken**. Every one of these is green —
this branch starts from a clean board, which it has not been for weeks.
**Never adjust a baseline to match a prediction; record what you observe.**

**After Task 1 (`0169979`):** unit **2319 + 1 xfailed**, mypy **355** files,
ruff format **654**. Contract, integration and lint-imports unmoved. Measure your
own task's delta against *your* starting commit, not against this table.

> **Two corrections Task 1 paid for, which every later task inherits.**
>
> **`src/sro/application/ports/asking.py` does not exist and never did.** The
> `Asker` protocol lives in **`ports/model.py:16`** and nine modules import it
> from there. `AskerUnavailable` and `asker_or_refuse` are beside it in that
> file. Every reference in this plan has been corrected; if you find one that
> was missed, `ports/model.py` is the answer.
>
> **`Settings()` reads `backend/.env`, which overrides three `SRO_GEMINI_*_MODEL`
> values.** Any test asserting a `Settings` default must pass
> `Settings(_env_file=None)` or it becomes a function of the developer's
> dotfile. Twelve places in this repo already do this.

> **There is no random-ordering pytest plugin in this repo.** An earlier draft
> of this section listed `-p randomly --randomly-seed=…` as the eighth gate.
> `pytest-randomly` and `pytest-random-order` are both absent — the installed
> plugins are cov, asyncio, schemathesis, hypothesis and anyio — so that command
> would have configured nothing and passed by doing nothing. `-p no:randomly`
> likewise disables a plugin that was never there and **proves nothing about
> ordering**. Test rule 2 below is still correct and still binding: vary
> `PYTHONHASHSEED`, which is what actually moves set and dict iteration order.
>
> `tests/browser` takes the eighth slot instead, because it is a real gate:
> `make check` runs it, and it globs the extension's fixtures directory the same
> way the contract suite does. One fixture defect failed both suites for three
> days while only one of them was being watched.

### Git

- **Never delete, move, rename or stage any untracked file.**
  `backend/.gmail-token.json.old-client`, `backend/old-client_secret_*.disabled`
  and every `rig.db*` stay exactly where they are.
- **Stage only files you created or edited, by name.** Never `git add -A`,
  never `git add .`, never `git add -u`.
- **`git stash` is forbidden in any form.** **Do not write to any git config.**
- Private index for every commit: `export GIT_INDEX_FILE=$(mktemp -u /tmp/idx.XXXXXX)`
  — note `-u`; plain `$(mktemp)` seeds an empty index and the commit deletes the
  repository.
- Identity: `GIT_AUTHOR_NAME`/`GIT_COMMITTER_NAME` = `Devansh Joshi`,
  `GIT_AUTHOR_EMAIL`/`GIT_COMMITTER_EMAIL` = `devansh.j@GGN002963.local`.
- Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_013zJkLruANn5fw99AJZAHKu
  ```
- Commit subjects are sentences about what changed and why it mattered,
  lowercase after the type prefix, no trailing period. Real examples:
  `fix(rig): a call that never returned does not claim to be a free one` ·
  `test(devices): the roster had never once reported a connected browser`.

### Commands

Backend commands run from `backend/` and are prefixed `uv run`. **There is no
bare `python` on this machine.**

### Every module path in this plan is a guess until you check it

**This is the plan's dominant defect, measured rather than suspected.** Seven
module paths written into this plan turned out not to exist:

| The plan said | It actually is |
|---|---|
| `application/ports/asking.py` | **`ports/model.py:16`** (`Asker`, and now `AskerUnavailable`, `asker_or_refuse`) |
| `application/ports/clock.py` | **`ports/system.py:21`** (`Clock`) |
| `application/ports/unit_of_work.py` | **`ports/repositories.py:901`** (`UnitOfWork`) |
| `domain/skill/mine_result.py` | **`application/observation/mining_pass.py:76`** (`MineResult`) |

Four were caught before dispatch; `ports/asking.py` was not, and Task 1's
implementer had to work around it mid-task.

**Before you import anything this plan names, confirm the module exists.** The
cheapest check is to read how the code you are wrapping imports the same things
— `mining_pass.py`'s own import block is the authority for Task 2, not this
document. If a path here is wrong, **say so in your report**; the next task
inherits it otherwise.

The same applies to type and schema names. `ResolutionModel` and `MinedModel`
are already taken in `schemas.py`, and **two different classes are named
`Resolution`** (`intent/resolve.py:52` and `observation/identity.py:109`).

### Symbols the later tasks need, located and verified

All 56 module paths in this plan were resolved against disk on 2026-09-09; the
four wrong ones survive only in the table above. These are the symbols Tasks 3
to 10 name, with the lines this plan originally failed to give:

| Symbol | Where it is | Needed by |
|---|---|---|
| `Approvals` | `application/execution/approvals.py:49` | Task 8 |
| `Stops` | `application/execution/stops.py:22` | Tasks 5, 7 |
| `CannotStop` | `application/execution/read_runs.py:42` | Task 7 |
| `StopRun` | `application/execution/read_runs.py:54` — **do not extend it**, it is the skill-run half | Task 7 |
| `RunDispatcher` | `application/ports/dispatch.py:23` | Task 5 |
| `read_utterance` | `application/chat/understand.py:109` | Task 3 |
| `Understood` | `application/chat/understand.py:32` | Task 3 |
| `over_cap` | `application/intent/spend.py:56` | Tasks 3, 5 |
| `PoolEntry` | `domain/observation/pool.py:50` | Task 10a |
| `TenantOnly` | `interface/http/asking.py` — **one grep from the `ports/asking.py` that does not exist** | Tasks 3, 5–10 |

All eight repository methods these tasks call are present in
`application/ports/repositories.py`: `retired`, `waiting`, `in_flight`,
`awaiting`, `approve`, `approvals`, `for_workflow`, `fail_orphans`.

**`CannotStop` subclasses `Conflict`, so Task 7's status code is already
decided — 409, through the MRO walk in `errors._status_for`.** Do not invent
one, and do not add a `_STATUS_BY_ERROR` entry for it.

### Three more corrections, paid for by Task 2

1. **`FakeSpendRepository` holds no rows and has no `record`.** It sums the four
   billable repositories with the rig's predicates, and refuses by construction
   to be handed a total nobody spent. **Plant spend the way `test_spend.py`
   does** — `uow.chats.record(ChatReading(...))` — not with a fabricated total.
   Task 2's brief sketched `await uow.spend.record(..., cost_usd=5.01)`, which
   would not have run.
2. **`OverCap`'s wire body has no `code` key.** `errors._problem` renders
   `exc.code` into **`type`**, as `https://ai-sro.dev/problems/over_cap`. A test
   asserting `body["code"]` fails. Task 3 raises the same exception.
3. **`lopsided` is top-level on `MineResult`, not on the domain `Coverage`**
   (`domain/skill/checks.py:33` carries `coverage`, `skew`, `gini` and nothing
   else). A response model that groups them must take `lopsided` as a separate
   keyword rather than spreading the dataclass — and that join is where a
   swapped-field mutation hides.

---

## The one place this plan departs from the spec

The spec, at line 42, says the rig's routes are *"ported route by route, same
paths and bodies so the extension changes only its base URL."*

**That premise is false for the four run routes, and this plan deviates
deliberately.** The ruling, its evidence, and its cost:

`/v1/runs`, `/v1/runs/{run_id}`, `/v1/runs/{run_id}/stop` and
`/v1/runs/{run_id}/values` **already exist on the backend and already mean
something else** — `interface/http/v1/routers/runs.py:217`, `:234`, and the two
beside them answer about *skill* runs, `sro.domain.execution.run.Run`, keyed on
`RunId`. The rig's `/v1/runs` answers about *workflow* runs,
`sro.domain.execution.workflow_run.WorkflowRun`, keyed on a plain `str`. Two
aggregates, two id spaces, one path.

**The extension is already living with the collision, and it has a name for
it.** `new-chrome-extension/src/background/api.js:178` calls
`/v1/runs/{id}` on the backend base with backend headers; `api.js:192` calls
the byte-identical path on the *rig* base with the rig's bearer. What decides
which is a `source` field mirrored beside the run id, and
`finishing.test.mjs:291-301` states the consequence in as many words:

> a run the rig drove is a run the backend has never heard of: its id is the
> rig's, and `GET /v1/runs/{id}` there answers 404

Today two hosts keep them apart. **Phase 7 deletes the rig**, at which point
both calls resolve to one host and one router, and `source` stops being able to
route anything.

**Ruling: workflow runs get `/v1/workflow-runs`.** Not `/v1/workflows/runs`,
which would make `{workflow_id}` == `"runs"` a live ambiguity the day anyone
adds `GET /v1/workflows/{workflow_id}`. Hyphenated segments have precedent here
(`from-preview`, `teach-together`, `sign-in`, `live-view`).

**What it costs:** phase 5 must repoint four calls in `api.js` instead of
changing one base URL. That work was already unavoidable — review 2 established
that `rigHeaders()` sends none of the backend's headers, so `/v1/shapes` and
`/v1/offers` are already broken for the extension and `api.js` is being opened
in phase 5 regardless.

**What the alternative costs:** overloading `/v1/runs` with a `workflow_id`
query parameter means one route returning two incompatible body shapes, chosen
by a query string. That is not a port, it is a defect with a schema.

**Action required outside this plan:** the spec's line 42 needs an amendment
recording this. Task 11 writes it.

---

## File Structure

**New files**

| File | Responsibility |
|---|---|
| `src/sro/application/observation/mine_pass.py` | `MinePass` use case — cap check, asker check, one call to `mine()` |
| `src/sro/application/chat/read_chat.py` | `ReadChat` use case — same two checks, one call to `read_utterance()` |
| `src/sro/application/execution/workflow_runs.py` | `StartWorkflowRun`, `ListWorkflowRuns`, `GetWorkflowRun`, `AbortWorkflowRun`, `ApproveWorkflowStep` |
| `src/sro/application/observation/read_pool.py` | `ReadPool` — live and retired entries |
| `src/sro/interface/http/v1/routers/mine.py` | `POST /v1/mine` |
| `src/sro/interface/http/v1/routers/chat.py` | `POST /v1/chat` |
| `src/sro/interface/http/v1/routers/workflow_runs.py` | the four run routes |
| `src/sro/interface/http/v1/routers/pool.py` | `GET /v1/pool` |
| `migrations/versions/20260909_0042_where_a_run_got_to.py` | `workflow_runs.from_step` |

**Modified**

| File | Change |
|---|---|
| `src/sro/config.py` | three model settings, `observation_batch_events`, `observation_artifact_bytes` |
| `src/sro/application/ports/model.py` | `AskerUnavailable` |
| `src/sro/interface/http/errors.py` | register `AskerUnavailable` (503) and `OverCap` (429); add 429 to `_TITLES`/`_SLUGS` |
| `src/sro/container.py` | six factories, `asker_or_refuse()` |
| `src/sro/interface/http/app.py` | four `include_router` lines |
| `src/sro/interface/http/schemas.py` | request/response models |
| `src/sro/domain/execution/workflow_run.py` | `from_step: int = 0` |
| `src/sro/infrastructure/db/models.py`, `db/workflow_runs.py` | the column and its mapper |
| `tests/unit/fakes.py` | fake repository keeps `from_step` |
| `src/sro/interface/http/v1/routers/observations.py` | the two size belts |
| `src/sro/infrastructure/db/repositories.py:653` | `.id.desc()` tiebreak |
| `src/sro/interface/http/v1/routers/spend.py` | a test behind its own comment |

**Deliberately not in this plan**

`GET /v1/streams` and `GET /v1/gestures` (4a Task 10 rows 5 and 6) — read-only
debugging doors with no console screen to feed. `GET /` at `/rig` — still the
spec's open item, and phase 6's. Parameter learning from network bodies — the
ADR 005 violation is a `sro.domain` change with its own risks and gets its own
spec.

---

## Task 1: The three model names, the two refusals, and 429

**Files:**
- Modify: `src/sro/config.py`
- Modify: `src/sro/application/ports/model.py`
- Create: `src/sro/application/shared/refusals.py`
- Modify: `src/sro/interface/http/errors.py`
- Modify: `src/sro/container.py`
- Test: `tests/unit/test_container_wiring.py`, `tests/unit/interface/test_refusals.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `Settings.gemini_mine_model`, `Settings.gemini_plan_model`,
  `Settings.gemini_rescue_model` (all `str`); `AskerUnavailable(Exception)`;
  `OverCap(Exception)` with attribute `code = "over_cap"`;
  `asker_or_refuse(asker: Asker | None) -> Asker` — **a module-level function in
  `application/ports/model.py`, not a `Container` method.** Tasks 2, 3 and 5 all
  consume these.

> **Ruling R1, made by the pre-flight scan.** This was first written as
> `Container.asker_or_refuse()`. It would have had **no caller**: Tasks 2, 3 and
> 5 each take `Asker | None` and refuse inside `execute`, deliberately, so that a
> container with no model stays constructible. A method with no caller is the
> exact defect this plan exists to close — one file away from
> `container.asker`'s own no-caller docstring. As a module-level function it has
> three callers, the raise is written once, and no factory raises.

Three routes are about to spend money on a model. Each of them can fail in the
same two ways before it spends anything, and each of them needs a model name.
Doing this once means the three routes are three thin things rather than three
copies of the same guard.

- [ ] **Step 1: Write the failing tests**

`tests/unit/interface/test_refusals.py`:

```python
"""The two ways a model-backed route says no before it spends anything."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap
from sro.interface.http.errors import install_error_handlers


def _app_that_raises(exc: Exception) -> TestClient:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise exc

    return TestClient(app, raise_server_exceptions=False)


def test_no_asker_is_a_dependency_problem_and_not_the_callers_fault() -> None:
    response = _app_that_raises(AskerUnavailable("no model is configured")).get("/boom")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "no model is configured"


def test_the_cap_is_429_and_carries_the_sentence_that_says_which_number_stopped_it() -> None:
    said = "daily cap reached: $5.0100 of $5.00 spent today, 0 unpriced call(s)"

    response = _app_that_raises(OverCap(said)).get("/boom")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    # The title and slug matter as much as the status: a client that renders
    # `problem.title` showed "Error" for every 429 until 429 was in the table,
    # and `problem.type` is how the console tells one refusal from another.
    body = response.json()
    assert body["title"] == "Too many requests"
    assert body["type"] == "https://ai-sro.dev/problems/over_cap"
    assert body["detail"] == said


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("gemini_mine_model", "gemini-3.1-pro-preview"),
        ("gemini_plan_model", "gemini-3.8-flash"),
        ("gemini_rescue_model", "gemini-3.1-pro-preview"),
    ],
)
def test_the_three_model_names_are_the_rigs(name: str, expected: str) -> None:
    """Rule 4: `new_agent_arch/src/rig/config.py` lines 20, 41 and 45 are the
    measured choices -- the pro model truncates a plan and the flash model
    cannot rescue one. A drift here is a different system wearing the same
    numbers."""
    from sro.config import Settings

    assert getattr(Settings(), name) == expected


def test_the_mine_model_is_not_the_interpreters() -> None:
    """They hold the same string today and answer different questions. One
    setting serving two purposes means re-tuning one silently re-tunes the
    other."""
    from sro.config import Settings

    fields = Settings.model_fields
    assert "gemini_mine_model" in fields
    assert "gemini_interpreter_model" in fields
```

In `tests/unit/test_container_wiring.py`, add:

```python
def test_no_asker_refuses_rather_than_handing_back_none() -> None:
    """`container.asker` is `Asker | None` and three callers need an `Asker`.
    Returning None to them means the refusal happens somewhere downstream, in
    the middle of a pass, after the window has been packed."""
    from sro.application.ports.model import AskerUnavailable, asker_or_refuse

    with pytest.raises(AskerUnavailable):
        asker_or_refuse(None)


def test_an_asker_is_handed_back_as_that_exact_object() -> None:
    """Not 'an Asker' -- that one. A guard that built a second one would bill
    against a client the spend tests never see."""
    from sro.application.ports.model import asker_or_refuse

    asker = FakeAsker()

    assert asker_or_refuse(asker) is asker


async def test_a_container_with_no_model_still_builds_every_factory() -> None:
    """The reason the guard is not on the container. A factory that raised
    would make `container.mine_pass()` unbuildable, and every test that
    constructs a container without a model would fail at construction rather
    than at use."""
    container = a_container(asker=None)

    assert container.mine_pass() is not None
    assert container.read_chat() is not None
```

The third test cannot pass until Tasks 2 and 3 exist. **Write it in Task 1 and
mark it `xfail(strict=True)` with a reason naming those tasks**; Task 3 removes
the marker. `strict=True` matters: a non-strict xfail that starts passing says
nothing, and this one passing early would mean a factory got built somewhere it
was not planned.

Use whatever `a_container(...)` / `FakeAsker` helpers `tests/unit/test_container_wiring.py`
already has; read that file before writing, and follow its existing construction
helper rather than inventing a second one.

- [ ] **Step 2: Run them to verify they fail**

```
cd backend && uv run pytest tests/unit/interface/test_refusals.py tests/unit/test_container_wiring.py -q
```

Expected: import errors for `sro.application.shared.refusals` and
`AskerUnavailable`, `AttributeError` on the three settings, `AttributeError:
asker_or_refuse`.

- [ ] **Step 3: Add the three settings**

In `src/sro/config.py`, beside `gemini_interpreter_model` at `:334`:

```python
    gemini_mine_model: str = "gemini-3.1-pro-preview"
    """The model one mining pass asks. The rig's `mine_model`
    (`new_agent_arch/src/rig/config.py:20`), and the same string as
    `gemini_interpreter_model` above by coincidence rather than by design --
    they answer different questions and each is re-tunable without the other.

    Measured on 2026-09-09 against 507 real gestures: at `K_EFFORT="high"` this
    model billed 204,747 tokens in and 65,522 out, truncated its answer after
    2,610 tokens, cost $2.00 and kept nothing. The effort knob that fixed that
    lives at `domain/skill/umbrella.py:23`; this is only the name."""

    gemini_plan_model: str = "gemini-3.8-flash"
    """What plans each step of a workflow run. The rig's `plan_model`
    (`config.py:41`). Deliberately the fast model: a run plans once per step and
    a slow plan is felt by an operator standing at a screen."""

    gemini_rescue_model: str = "gemini-3.1-pro-preview"
    """What re-plans a step the plan model got wrong. The rig's `rescue_model`
    (`config.py:45`). The expensive model earns its price here and not above:
    it is asked once per failure, not once per step."""
```

- [ ] **Step 4: Add `AskerUnavailable`**

In `src/sro/application/ports/model.py`, beside the `Asker` protocol:

```python
class AskerUnavailable(Exception):
    """No model is configured. Not a ``DomainError``: the request was fine.

    Raised rather than handing a caller ``None`` or a no-op double, for the
    reason written on ``Container.asker``: a miner with nothing to ask must not
    run and quietly find nothing, because that reads exactly like a day with no
    work in it. Same shape and same reasoning as ``VaultUnavailable`` and
    ``SchedulerUnavailable`` -- a dependency that is absent, answered 503.
    """
```

- [ ] **Step 5: Add `OverCap`**

Create `src/sro/application/shared/refusals.py`:

```python
"""Refusals that are neither the caller's fault nor a dependency being down."""

from __future__ import annotations


class OverCap(Exception):
    """This tenant has spent what it may spend on models today.

    Not a ``DomainError``: nothing about the request is wrong, and it will be
    accepted again tomorrow or with a larger cap. 429 rather than 402 or 403 --
    the caller is being rate-limited by budget, and 429 is the one status whose
    meaning is "later, not never".

    Carries ``over_cap``'s own sentence unchanged. It names both numbers -- what
    was spent and what the cap is -- plus how many of the day's calls came back
    unpriced, because a day stopped by blindness and a day stopped by cost need
    different people to do different things.
    """

    code = "over_cap"
```

`code` is the attribute `_problem` reads to build `problem.type`
(`errors.py:159`).

- [ ] **Step 6: Register both, and teach the tables about 429**

In `src/sro/interface/http/errors.py`:

```python
_STATUS_BY_ERROR = {
    ...
    OverCap: status.HTTP_429_TOO_MANY_REQUESTS,
}

_TITLES = {
    ...
    status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests",
}

_SLUGS = {
    ...
    status.HTTP_429_TOO_MANY_REQUESTS: "too_many_requests",
}
```

and add `AskerUnavailable` and `OverCap` to the `for error_type in (...)` tuple
in `install_error_handlers`.

`AskerUnavailable` needs a `_STATUS_BY_ERROR` entry of
`status.HTTP_503_SERVICE_UNAVAILABLE`, exactly as `VaultUnavailable` has.
`_TITLES` already carries 503.

> `_SLUGS`'s docstring says it is *"only for the statuses FastAPI raises by
> itself; a domain error brings its own `code`."* `OverCap` brings `code =
> "over_cap"`, so its `type` comes from the code and not the slug. Add the 429
> slug anyway: FastAPI raises bare 429s from any future rate limiter, and a slug
> table with a hole in it is how `problem.type` became `undefined` for 401 —
> the defect `_http_problem`'s docstring records.

- [ ] **Step 7: Add `asker_or_refuse`**

In `src/sro/application/ports/model.py`, beside `AskerUnavailable`:

```python
def asker_or_refuse(asker: Asker | None) -> Asker:
    """The general model, or a 503 saying there is not one.

    A function and not a ``Container`` method, and the reason is the defect it
    avoids: the three callers each take ``Asker | None`` and refuse inside
    ``execute``, so that a deployment with no model can still build every
    factory. A container method would therefore have had no caller at all --
    one file away from ``container.asker``, whose docstring records having had
    no reader for a day.

    Refusing at the top of ``execute`` means the failure lands before a window
    is packed and before a run row is claimed, rather than somewhere in the
    middle of either.
    """
    if asker is None:
        raise AskerUnavailable(
            "no model is configured: set gemini_api_key and interpretation_enabled"
        )
    return asker
```

Update `container.asker`'s docstring: the sentence *"The caller that checks and
refuses arrives in 4b"* has arrived. Say so, and name this function and its three
callers.

- [ ] **Step 8: Run the tests**

```
cd backend && uv run pytest tests/unit/interface/test_refusals.py tests/unit/test_container_wiring.py -q
```

Expected: PASS.

- [ ] **Step 9: Mutation-check the guard**

Confirm each mutation is anchored where you think it is before you run it — a
mutation applied to the wrong function is indistinguishable from a survivor.
`grep -c` the anchor, apply, and confirm the patched hunk landed where intended.

| Mutation | Must kill |
|---|---|
| `if asker is None:` → `if asker is not None:` | the refusal test |
| `OverCap` mapped to 503 instead of 429 | the 429 test |
| `AskerUnavailable` removed from `install_error_handlers`'s tuple | the 503 test (it becomes a 500) |
| `_TITLES[429]` deleted | the title assertion |
| `gemini_plan_model` default changed to the pro model | the parametrised settings test |

Record which mutation killed which test in your report. A survivor is a missing
test, not an acceptable result.

- [ ] **Step 10: Gates, then commit**

```bash
export GIT_INDEX_FILE=$(mktemp -u /tmp/idx.XXXXXX)
export GIT_AUTHOR_NAME="Devansh Joshi" GIT_AUTHOR_EMAIL="devansh.j@GGN002963.local"
export GIT_COMMITTER_NAME="Devansh Joshi" GIT_COMMITTER_EMAIL="devansh.j@GGN002963.local"
git add src/sro/config.py src/sro/application/ports/model.py \
        src/sro/application/shared/refusals.py src/sro/interface/http/errors.py \
        src/sro/container.py tests/unit/interface/test_refusals.py \
        tests/unit/test_container_wiring.py
git commit -m "feat(asking): the refusal container.asker was built for, and had no caller

..."
```

---

## Task 2: `POST /v1/mine` — the model miner gets a caller

**Files:**
- Create: `src/sro/application/observation/mine_pass.py`
- Create: `src/sro/interface/http/v1/routers/mine.py`
- Modify: `src/sro/container.py`, `src/sro/interface/http/app.py`, `src/sro/interface/http/schemas.py`
- Test: `tests/unit/application/rig/test_mine_pass.py`, `tests/unit/interface/test_mine_route.py`, `tests/integration/test_mine_route_against_postgres.py`

**Interfaces:**
- Consumes: `Container.asker_or_refuse()`, `OverCap`, `Settings.gemini_mine_model` (Task 1).
- Produces: `Container.mine_pass() -> MinePass`; `MinePass.execute(ctx) -> MineResult`;
  `MinePassResponse` in `schemas.py`.

The rig's `POST /v1/mine` is `new_agent_arch/src/rig/api.py:739`. The ported pass
is `application/observation/mining_pass.py:164` and **grep finds no caller in
`src/`**. Every mining result this project has measured came from a script run by
hand.

**Do not confuse this with `POST /v1/candidates/mine`**
(`routers/candidates.py:51`). That is the heuristic candidate miner and it makes
no model call. Two routes, two miners, similar names — 4a's Task 10 flagged this
as the mistake most likely to send someone hunting a phantom.

- [ ] **Step 1: Write the failing tests**

`tests/unit/application/rig/test_mine_pass.py`:

```python
"""The pass refuses before it packs a window, or it makes exactly one call."""

from __future__ import annotations

import pytest

from sro.application.observation.mine_pass import MinePass
from sro.application.ports.model import AskerUnavailable
from sro.application.shared.refusals import OverCap


async def test_no_asker_refuses_before_anything_is_read() -> None:
    """The refusal is worth its own test because the alternative is not an
    exception, it is a pass that finds nothing -- which is what a quiet day
    looks like."""
    uow = FakeUnitOfWork()
    use_case = MinePass(uow, asker=None, model="m", clock=FakeClock(), cap_usd=5.0)

    with pytest.raises(AskerUnavailable):
        await use_case.execute(a_context())

    assert uow.workflows.passes == [], "a refused pass wrote a row"


async def test_over_the_cap_refuses_and_says_which_number_stopped_it() -> None:
    uow = FakeUnitOfWork()
    await uow.spend.record(..., cost_usd=5.01)  # follow the existing spend fake's API
    use_case = MinePass(uow, asker=FakeAsker(), model="m", clock=FakeClock(), cap_usd=5.0)

    with pytest.raises(OverCap) as refused:
        await use_case.execute(a_context())

    assert "5.0100" in str(refused.value)
    assert "5.00" in str(refused.value)


async def test_a_pass_that_runs_returns_every_figure_the_row_records() -> None:
    """Not `is not None`. Each counter answers a different question and the
    contract suite already has a sibling test that fails when the SQL mapper
    drops one of them."""
    use_case = MinePass(uow, asker=FakeAsker(...), model="m", clock=FakeClock(), cap_usd=5.0)

    result = await use_case.execute(a_context())

    assert result.proposed == ...
    assert result.kept == ...
    assert result.rejected == ...
    assert result.learned_parameters == ...


async def test_the_cap_is_checked_against_the_callers_clock_and_not_a_read_one() -> None:
    """Rule 4. `container.read_spend`'s docstring says which day is being asked
    about is a decision no route may make. Move the clock across midnight and
    the same spend stops refusing."""
```

Fill the `...` from the real fakes — read `tests/unit/fakes.py` and the existing
`tests/unit/application/rig/test_mine.py` first, and reuse their helpers rather
than writing new ones.

`tests/unit/interface/test_mine_route.py`: assert **503** with no asker, **429**
over the cap, **200** with the body below, and that the route passes
`ctx` through rather than a tenant read from the body.

- [ ] **Step 2: Run them to verify they fail**

```
cd backend && uv run pytest tests/unit/application/rig/test_mine_pass.py tests/unit/interface/test_mine_route.py -q
```

- [ ] **Step 3: Write `MinePass`**

```python
"""One mining pass, asked for from outside the process."""

from __future__ import annotations

from datetime import datetime

from sro.application.context import RequestContext
from sro.application.intent.spend import over_cap
from sro.application.observation.mining_pass import MineResult, mine
from sro.application.ports.model import Asker, asker_or_refuse
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.application.shared.refusals import OverCap


class MinePass:
    """Read this tenant's day, once, and bill it.

    A class where ``mine`` is a bare function, for the reason
    ``container.record_offer`` is one (``container.py:350-357``): ``mine`` takes
    a bare ``tenant_id``, and a route calling it would unpack the caller itself
    at the one seam where passing the wrong tenant is the failure.

    Both refusals happen here rather than inside ``mine``. ``mine`` takes an
    ``Asker`` and cannot be given ``None``; and its own cap check
    (``mining_pass.py:296``) writes a ``MiningPass`` row recording the refusal,
    which is right for a pass that got as far as trying and wrong for a request
    that should never have been admitted. Refusing at the door means a caller
    that hammers this route does not fill the spend table with rows about its
    own hammering.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        *,
        asker: Asker | None,
        model: str,
        clock: Clock,
        cap_usd: float,
    ) -> None:
        self._uow = uow
        self._asker = asker
        self._model = model
        self._clock = clock
        self._cap_usd = cap_usd

    async def execute(self, ctx: RequestContext) -> MineResult:
        asker = asker_or_refuse(self._asker)
        now: datetime = self._clock.now()
        async with self._uow as uow:
            why = await over_cap(uow, ctx.tenant_id, now=now, cap_usd=self._cap_usd)
            if why is not None:
                raise OverCap(why)
            return await mine(
                uow,
                tenant_id=ctx.tenant_id,
                asker=asker,
                model=self._model,
                now=now,
                cap_usd=self._cap_usd,
            )
```

> `mine`'s docstring says *"`uow` is already open: the pass commits its own
> writes and never enters or leaves the block, so the caller owns the session."*
> The `async with` above is that ownership. **Do not open a second session for
> the cap check** — 4a shipped two read-only doors that touched a repository the
> session had not made, and they were dead against real Postgres while every
> unit test passed (`50864cf`).

Take the container factory's `asker` as `Asker | None` rather than calling
`asker_or_refuse()` in the factory: a factory that raises makes
`container.mine_pass()` itself unbuildable, and every test that constructs a
container without a model then fails at construction rather than at use.

- [ ] **Step 4: Wire the container**

```python
    def mine_pass(self) -> MinePass:
        return MinePass(
            self.unit_of_work(),
            asker=self.asker,
            model=self.settings.gemini_mine_model,
            clock=self.clock,
            cap_usd=self.settings.daily_usd_cap,
        )
```

Match the surrounding factories' access to `self.settings` — read `container.py`
and follow whatever it already does rather than assuming the attribute name.

- [ ] **Step 5: The response models**

> **Five corrections to this task, found before dispatch by reading the code
> rather than trusting the plan. Do not re-derive them; do check them.**
>
> 1. **`MineResult` is not in `sro.domain.skill.mine_result`** — that module
>    does not exist. It is at **`sro/application/observation/mining_pass.py:76`**,
>    beside `mine` itself.
> 2. **The rig's route is `tenant_only`**, not `authorised` — `api.py:739`.
>    Match it.
> 3. **`MineResult` has far more on it than the draft response model listed.**
>    The real fields are `pass_id`, `proposed`, `kept`, `learned_parameters`,
>    `rejections`, `resolutions`, `coverage` (a nested `Coverage`, not a float),
>    `in_tokens`, `out_tokens`, `thought_tokens`, `cost_usd`, `unpriced`,
>    `error`, `window_size`, `left_out`, `lost_pool`, `lopsided`. **There is no
>    `rejected: int`** — the draft invented it; rejections are a list.
> 4. **`ResolutionModel` is already taken** in `schemas.py:1255` by the intent
>    resolver, and `MinedModel` at `:2514` by the heuristic candidate miner.
>    Prefix the new ones `Mine…`.
> 5. **Two different classes are named `Resolution`** — `intent/resolve.py:52`
>    and `observation/identity.py:109`. You want **`identity.Resolution`**
>    (`kind`, `workflow_id`, `score`, `contains`).

The supporting types, read off the files:

```python
# sro/domain/skill/checks.py:26
class Rejection:      workflow_title: str; reason: str; detail: str
# sro/domain/skill/checks.py:33
class Coverage:       coverage: float; skew: float; gini: float
# sro/domain/observation/identity.py:109
class Resolution:     kind: str; workflow_id: str | None; score: float; contains: bool
```

In `schemas.py`:

```python
class MineRejectionModel(BaseModel):
    workflow_title: str
    reason: str
    detail: str


class MineResolutionModel(BaseModel):
    """Where a proposed workflow went when it was not kept.

    `kind` is "new", "same_occurrence" or "same_job". Named `Mine…` because
    `ResolutionModel` at schemas.py:1255 already belongs to the intent
    resolver, over a different `Resolution` class entirely.
    """

    kind: str
    workflow_id: str | None
    score: float
    contains: bool


class MineCoverageModel(BaseModel):
    coverage: float
    skew: float
    gini: float
    lopsided: bool
    """Which of the two numbers beside it broke its threshold is readable from
    them; that one did is the verdict. Carried on this object rather than at the
    top level, matching the rig."""


class MinePassResponse(BaseModel):
    """What one reading of a day cost and found.

    `rejections` and `resolutions` are both here and neither is optional. The
    rig's reason, kept: without resolutions, `proposed: 3, kept: 0,
    rejections: []` is three jobs that vanished with no account of where they
    went.

    `learned_parameters` is the one figure that says whether parameter learning
    is getting better, and until migration 0041 every pass computed it and the
    persistence layer discarded it. A pass that recognises nothing new and
    widens two parameters did real work.

    `left_out` and `lost_pool` are counted rather than inferred: `left_out` did
    not fit the token budget and is offered again next pass, `lost_pool` is a
    pooled id with no gesture row that no pass can ever read. Neither is
    derivable from `window_size` alone.
    """

    pass_id: str
    error: str | None
    proposed: int
    kept: int
    learned_parameters: int
    window_size: int
    left_out: int
    lost_pool: list[str]
    rejections: list[MineRejectionModel]
    resolutions: list[MineResolutionModel]
    coverage: MineCoverageModel
    in_tokens: int
    out_tokens: int
    thought_tokens: int
    cost_usd: float
    unpriced: bool
```

**Two deliberate divergences from the rig, both to be written into the
docstring:** the rig names the window field `window` and this keeps
`window_size`, matching `MineResult`; and the rig rounds `cost_usd` to six
places in the route while this does not — rounding for display is the reader's
job, and a bill rounded on the way out cannot be summed against the row.

`thought_tokens` is **part of** `out_tokens`, not beside them
(`mining_pass.py:98`). Say so in the model, or a reader adds them and reports a
number no invoice will match.

- [ ] **Step 6: The route**

```python
@router.post("/mine", status_code=status.HTTP_200_OK)
async def mine_the_day(container: ContainerDep, ctx: ContextDep) -> MinePassResponse:
    """Read this tenant's day and keep what it recognises.

    No body: the tenant comes from the caller and the day comes from the
    server's clock. A body naming either would be a request to mine somebody
    else's evidence, or to mine a day the spend cap was not measured against.

    200 rather than 202: the pass is synchronous and the caller is billed for
    it, so answering "accepted" and hanging up would leave nobody holding the
    receipt.
    """
    result = await container.mine_pass().execute(ctx)
    return MinePassResponse.of(result)
```

**The auth dependency is `TenantOnly`.** The rig's route is
`@app.post("/v1/mine", dependencies=[Depends(tenant_only)])` at `api.py:739` —
verified, not inferred. A device token must not be able to spend a tenant's
model budget. Say so in the module docstring.

- [ ] **Step 7: Register the router** in `app.py`, alphabetically among the
  existing `include_router` calls, with `prefix="/v1", responses=PROBLEMS`.

- [ ] **Step 8: The integration test**

`tests/integration/test_mine_route_against_postgres.py` — the route through the
real container against real Postgres with a stub `Asker`. **This is the test
that would have caught the two dead 4a routes.** Assert a row lands in
`mining_passes` carrying `learned_parameters`.

- [ ] **Step 9: Run the gates**

- [ ] **Step 10: Commit**

---

## Task 3: `POST /v1/chat` — one sentence, read against this tenant's jobs

**Files:**
- Create: `src/sro/application/chat/read_chat.py`, `src/sro/interface/http/v1/routers/chat.py`
- Modify: `src/sro/container.py`, `src/sro/interface/http/app.py`, `src/sro/interface/http/schemas.py`
- Test: `tests/unit/application/chat/test_read_chat.py`, `tests/unit/interface/test_chat_route.py`, `tests/integration/test_chat_route_against_postgres.py`

**Interfaces:**
- Consumes: Task 1's three products.
- Produces: `Container.read_chat() -> ReadChat`; `ReadChat.execute(ctx, *, utterance: str) -> Understood`; `ChatRequest`, `ChatResponse`.

The rig's is `api.py:1495`. The ported reader is
`application/chat/understand.py:114` (`read_utterance`) and it has no caller.
**`POST /v1/intent/resolve` (`routers/intent.py:13`) is not this door** — it
resolves over skills, not mined workflows.

`ReadChat` is `MinePass`'s twin: same two refusals, same session ownership, one
call to `read_utterance` instead of `mine`. **Write it as its own class; do not
factor a shared base out of the two.** They will diverge — mining takes no input
from the caller and chat takes a sentence — and a base class holding two
refusals is an abstraction over a coincidence.

**Model name: `gemini_plan_model`.** Ruling R2, settled by reading the rig rather
than guessing: `api.py:1507` passes `settings().plan_model` to `understand`. The
flash model reading one sentence is a deliberate speed choice — a person is
waiting on this answer, and `gemini_intent_model`'s docstring records the same
trade measured at ~2.3s against ~4.8s for the pro model. Say so in the factory's
docstring, because the next reader will assume a chat door and a mining door use
the same model.

- [ ] **Step 1: Write the failing tests** — the same four shapes as Task 2, plus:

```python
async def test_a_sentence_naming_no_job_still_writes_the_bill() -> None:
    """`read_utterance`'s docstring: a row is written on every reading, a
    refusal included -- that is the case that matters, because it is then the
    only record left of a call that cost money and returned nothing."""


async def test_the_sentence_itself_is_not_stored() -> None:
    """`ChatReading` has no field for it and that is deliberate: there is no
    column for an operator's words about their own warehouse. A response model
    that echoed the utterance back into a log would undo that."""
```

- [ ] **Step 2: Run them to verify they fail**
- [ ] **Step 3: Write `ReadChat`**
- [ ] **Step 4: Wire the container**
- [ ] **Step 5: `ChatRequest` / `ChatResponse`** — the response carries
  `workflow_id`, `values`, `missing`, and the bill. `missing` is `sorted(...)`
  in `understand.py:106` because *"a form whose fields reorder between two
  identical sentences is a form nothing can screenshot"* — assert the order,
  under several `PYTHONHASHSEED` values (rule 2).
- [ ] **Step 6: The route**
- [ ] **Step 7: Register the router**
- [ ] **Step 8: The integration test**
- [ ] **Step 9: Gates**
- [ ] **Step 10: Commit**

---

## Task 4: A run remembers where it got to

**Files:**
- Create: `migrations/versions/20260909_0042_where_a_run_got_to.py`
- Modify: `src/sro/domain/execution/workflow_run.py`, `src/sro/infrastructure/db/models.py`, `src/sro/infrastructure/db/workflow_runs.py`, `tests/unit/fakes.py`
- Test: `tests/contract/test_the_repositories_agree.py`, `tests/integration/…`

**Interfaces:**
- Consumes: nothing.
- Produces: `WorkflowRun.from_step: int = 0`, persisted. Task 5 reads it.

**This task must land before Task 5, and here is why it is not YAGNI.**

> **Ruling R3.** This task was first written on a wrong premise — that
> `from_step` is a progress marker the runner advances. **It is not.** Read
> `run_workflow.py:337`, `:345` and `:355-368` before starting: `from_step` is a
> **request input** naming how many steps the operator already performed
> themselves before the offer was made. Those steps are recorded
> `done_by_operator` and never sent — *"the job is being finished, not redone."*
> The rig takes it from the request body (`api.py:1097`) and validates it. **No
> runner-loop writer is needed.** The corrected defect below is narrower and
> better evidenced than the one this task originally claimed.

`run_workflow` takes `from_step: int = 0` (`run_workflow.py:285`) and
`WorkflowRun` has no such field — confirmed by reading the dataclass at
`domain/execution/workflow_run.py:79-98`. Today that is harmless because nothing
calls `run_workflow`.

Task 5 changes that. `run_workflow.py:296-310` re-reads a claimed row as *"the
authority for what was asked for — read back here rather than rebuilt from the
arguments, so there is one answer to 'what is this run doing' and not two that
can drift"*, and **refuses** when the row's `device_id`, `workflow_id` or
`outcome` disagrees with the arguments.

`from_step` is part of what was asked for, and **it is not on that list** —
because there is no column to compare it against. So a re-press carrying a
different `from_step` performs a **different job under this run's id**: silently,
skipping steps the operator never did, or redoing steps they already performed
against a live warehouse. That is precisely the failure the other three checks
exist to prevent, and it is the only one of the four that cannot be checked.

The alternative — deleting the `from_step` parameter — throws away the
`done_by_operator` path, which is written, tested, and the whole mechanism by
which an offer finishes a job a person started.

**So this task is four layers plus one guard:** the column, the field, the
mapper, the fake, **and `from_step` added to the disagreement check at
`run_workflow.py:302-310`.**

- [ ] **Step 1: Write the failing contract test**

Add to `tests/contract/test_the_repositories_agree.py`, beside
`test_a_pass_carries_back_every_figure_it_was_written_with`:

```python
async def test_a_run_carries_back_the_step_it_was_saved_at(uow_factory) -> None:
    """Both repositories, one assertion. The fake keeps a dataclass and the SQL
    mapper copies column by column, so a field the mapper forgets round-trips as
    its default through every unit test and loses the operator's progress only
    against real Postgres.

    Non-default on purpose: `from_step=0` is what a dropped column returns.
    """
    run = a_workflow_run(from_step=4)

    async with uow_factory() as uow:
        await uow.workflow_runs.save(run)
    async with uow_factory() as uow:
        read = await uow.workflow_runs.get(TENANT, run.id)

    assert read is not None
    assert read.from_step == 4
```

Follow the file's existing parametrisation over `[fake]` and `[sql]`; the test
must **fail on `[sql]` alone** when the mapper drops the column. Verify that by
dropping it deliberately before you wire it.

- [ ] **Step 2: Run it — expect a failure on `[sql]`**

- [ ] **Step 3: The migration**

`0042`, revises `0041` (head is `20260909_0041_what_a_pass_learnt.py` — confirm
with `uv run alembic heads` before writing). Follow 0041's docstring form: what
the column is, what was measured, and why the backfill value is the honest one.

```python
def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("from_step", sa.Integer(), nullable=False, server_default="0"),
    )
```

Backfill to `0` and say why in the docstring: every existing row was written by
a system with no resume, so it started at step zero, and `0` is the true value
rather than a convenient one. **This is a different argument from 0041's**,
where `0` was the honest floor for an unknown — do not copy that sentence, it
would be false here.

- [ ] **Step 4: The field, the column, the mapper, the fake** — all four. A
  fake that keeps the field while the mapper drops it is exactly the permissive
  double this plan's constraints warn about.

- [ ] **Step 4b: Add `from_step` to the disagreement check**

In `run_workflow.py:302-310`, beside the three conditions already there:

```python
    if saved is not None and (
        saved.device_id != device_id.value
        or saved.workflow_id != workflow.id
        or saved.outcome != "running"
        or saved.from_step != from_step
    ):
```

and extend the `ValueError` message so it names the mismatch — the existing one
already names `outcome`, `workflow_id` and `device_id`, and a refusal that does
not say which field disagreed is a refusal nobody can act on.

Write a test first, and make it fail for the right reason:

```python
async def test_a_re_press_that_moves_from_step_is_refused_rather_than_performed() -> None:
    """The fourth thing the row is the authority for. Claim a run at
    `from_step=4`, re-enter it at `from_step=0`, and the operator's four steps
    are redone against a live warehouse -- silently, because the other three
    checks all pass.
    """
```

- [ ] **Step 5: Run the contract test — expect PASS on both `[fake]` and `[sql]`**

- [ ] **Step 6: Apply the migration and check both directions**

```
cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
```

`downgrade` must drop the column cleanly. A migration that only goes one way is
one nobody can back out of at 3am.

- [ ] **Step 7: Mutation-check** — delete `from_step` from the mapper's read;
  the contract test must fail on `[sql]` and pass on `[fake]`. If it fails on
  both, the test is not reaching the mapper and proves nothing.

- [ ] **Step 8: Gates, then commit**

---

## Task 5: `POST /v1/workflow-runs` — something starts a run

**Files:**
- Create: `src/sro/application/execution/workflow_runs.py`, `src/sro/interface/http/v1/routers/workflow_runs.py`
- Modify: `src/sro/container.py`, `src/sro/interface/http/app.py`, `src/sro/interface/http/schemas.py`
- Test: `tests/unit/application/rig/test_start_workflow_run.py`, `tests/unit/interface/test_workflow_runs_route.py`, `tests/integration/test_workflow_runs_against_postgres.py`

**Interfaces:**
- Consumes: Task 1's three products, Task 4's `from_step`.
- Produces: `Container.start_workflow_run() -> StartWorkflowRun`;
  `StartWorkflowRun.execute(ctx, *, workflow_id: str, device_id: DeviceId, values: Mapping[str, str], live: bool, allow_focus: bool, run_id: str | None = None) -> WorkflowRun`;
  `StartWorkflowRunRequest`, `WorkflowRunModel`. Tasks 6, 7 and 8 consume
  `WorkflowRunModel`.

The rig's is `api.py:1021`. This is the largest task in the plan and the one that
touches a live warehouse.

**Read `run_workflow.py:267-320` in full before writing anything.** It documents
the contract this route must keep, including a divergence from the rig that
exists *specifically* for this route: the `outcome != "running"` check, whose
comment reads *"The rig gets away with it because nothing re-presses a finished
run; phase 4's route will."*

### What the route must do, in order

> **Ruling R4.** This order is the rig's, at `api.py:1031-1110`, and **each
> position is reasoned there.** An earlier draft of this task put the workflow
> lookup before the device checks; the rig's ordering wins because it has an
> argument and the draft did not. Read those eighty lines before writing.

1. **Refuse with no asker** — 503, before anything is written.
2. **Refuse over the cap** — 429. *"Before the browser is asked anything: a run
   plans every step on a model, and a day that has spent its cap starts none."*
3. **Refuse a browser that is not connected** — 409. **Before the workflow
   lookup**, and the rig says why: *"'your browser is not connected' is the
   answer a person can act on, and it holds whatever they asked for."*
4. **Refuse a second hand on the same browser** — 409, also before the workflow
   lookup, *"for the same reason"*. `workflow_runs.in_flight(tenant, device)`
   returns the run this browser is already driving:
   *"One browser, one hand: two runs driving the same window interleave their
   clicks into a form neither of them can then read back."*
5. **Resolve the workflow.** A `workflow_id` naming nothing is a 404.
6. **Validate the values** — 400. **Omitted from the first draft of this task
   entirely; it is not optional.** They must be an object of strings:
   *"Coerced values, not checked ones, would turn `{"clientCode": {...}}` into
   the string `"{...}"` and type it into somebody's form."* Then trimmed, and a
   value blank once trimmed is no value: *"`required` on the page passes a
   space, and a job run with ' ' as its client code is a job run with somebody
   else's."*
7. **Validate `from_step`** — 400, range `0..len(workflow.steps) - 1`. **Check
   `isinstance(from_step, bool)` first**, exactly as the rig does at
   `api.py:1101`: `True` is an `int` in Python, so `{"from_step": true}`
   otherwise passes every range check and starts the run at step 1.
8. **Claim the row**, `outcome="running"`, carrying `from_step`, and commit it —
   *before* answering and *before* `create_task`. `run_workflow`'s comment says
   why: a second press for the same browser must be refused rather than landing
   in the window between `create_task` and the task's first slice.
9. **Start the work**, and answer with the claimed row.

> Steps 6 and 7 may be pydantic validators on `StartWorkflowRunRequest` rather
> than route code — pydantic answers 422 where the rig answers 400, and
> `_validation_problem` already turns that into a problem document. **Either is
> acceptable; choose one and write the reason down.** What is not acceptable is
> the bool trap surviving: pydantic will coerce `true` to `1` for an `int` field
> unless the model is in strict mode. **Test it either way.**

- [ ] **Step 1: Write the failing tests**

One test per numbered rule above, plus:

```python
async def test_a_second_press_on_a_busy_browser_is_refused_and_starts_nothing() -> None:
    """Not just "raises": assert the task count did not go up. A refusal that
    still spawns the work is the exact race the claim-before-answer exists to
    close, and an exception-only assertion cannot see it."""


async def test_the_row_is_committed_before_the_work_is_started() -> None:
    """Rule 1, and the ordering is the whole design. Assert against a unit of
    work that records the order of commit and task creation -- not against a
    sleep."""


async def test_a_run_re_entered_at_step_four_does_not_replan_step_zero() -> None:
    """Task 4's field, earning itself. Without `from_step` persisted this test
    passes for the wrong reason: `run_workflow` defaults it to 0 and the run
    redoes four steps against a live warehouse."""


async def test_a_finished_run_id_is_refused_rather_than_resumed() -> None:
    """The deliberate divergence at run_workflow.py:300-310. A row already
    `held`, `failed` or `aborted` picked up here plans step zero, pays for the
    model call, has the send blocked, saves the step `skipped` and breaks out
    carrying a stale outcome plus a step that never happened."""


async def test_from_step_true_does_not_become_step_one() -> None:
    """`True` is an `int` in Python and pydantic coerces it to 1 outside strict
    mode. `{"from_step": true}` would otherwise pass every range check and skip
    the operator's first step -- recorded `done_by_operator` and never sent --
    on a job nobody started. The rig checks `isinstance(bool)` first
    (api.py:1101) and that ordering is the whole guard."""


async def test_a_value_that_is_only_whitespace_is_no_value() -> None:
    """`required` on the page passes a space. A job run with ' ' as its client
    code is a job run with somebody else's."""


async def test_a_nested_object_in_values_is_refused_and_not_stringified() -> None:
    """Coerced values would turn `{"clientCode": {...}}` into the string
    `"{...}"` and type it into somebody's form."""


async def test_an_unplugged_browser_is_answered_before_the_workflow_is_looked_up() -> None:
    """Ruling R4's ordering, made to fail rather than asserted in prose. Ask for
    a workflow that does not exist, on a browser that is not connected: the
    answer must name the browser, because that is the one the operator can act
    on and it holds whatever they asked for."""
```

- [ ] **Step 2: Run them to verify they fail**

- [ ] **Step 3: Write `StartWorkflowRun`**

`run_workflow` needs `channel`, `stops`, `approvals`, `plan_model`,
`rescue_model` and `started_by`. All are on the container:
`agent_sockets` (channels to browsers), `stops` (`container.py:225`), and the
`Approvals` register (`application/execution/approvals.py:49`). **Read
`container.py:660-670`, which already builds something with `self.stops`, and
follow that construction rather than inventing a second path to the same
objects.**

`started_by` is the authenticated caller, never a name in a body — the reason is
written at `routers/runs.py:52-60`: *"A request that says who authorised it is a
signature nobody checked, and the audit trail on a warehouse write is worth more
than that."*

- [ ] **Step 4: How the work is driven**

The container has `dispatcher: RunDispatcher`. **Read how `routers/runs.py`'s
`_perform` (`runs.py:248`) drives a skill run whose caller has already been
answered, and follow that pattern.** Do not invent a second concurrency
mechanism; if `RunDispatcher` does not fit a workflow run, say so in your report
with the reason rather than working around it silently.

- [ ] **Step 5: `StartWorkflowRunRequest` and `WorkflowRunModel`**

The request carries `workflow_id`, `device_id`, `values`, `live`, `allow_focus`.
**It does not carry `started_by` or `tenant`.** Compare the rig's body at
`api.py:1021` and record every divergence in the model's docstring — the way
4a's `/v1/offers` recorded dropping the rig's `device_id` because the browser
proves itself with `X-Device-Secret` instead.

`WorkflowRunModel` maps `WorkflowRun` including `steps`, `withheld`, the four
token counters, `cost_usd`, `unpriced` and `from_step`. Note for phase 5: the
extension's `rigRun()` (`api.js:196-210`) maps the rig's `outcome` to the
panel's `status` and `{order, says, verdict}` to `{index, outcome}`. **Answer
the backend's own field names here** and let phase 5 delete its mapping layer;
inventing rig-shaped aliases now means two vocabularies to keep in step forever.

- [ ] **Step 6: The route, at `/workflow-runs`**

The module docstring must carry the ruling from *The one place this plan departs
from the spec* above, in short: why not `/v1/runs`, and what a reader should
grep for when they wonder where the rig's path went.

- [ ] **Step 7: Register the router**

- [ ] **Step 8: The integration test against real Postgres**

Including the `in_flight` refusal — that one reads an index and is precisely the
kind of thing the fake gets right by accident.

- [ ] **Step 9: Mutation-check the order**

| Mutation | Must kill |
|---|---|
| commit moved to after `create_task` | the ordering test |
| `in_flight` check deleted | the busy-browser test |
| `from_step` passed as `0` instead of the row's | the step-four test |
| `outcome != "running"` check relaxed | the finished-run test |
| `started_by` read from the body | the audit test |
| the `isinstance(bool)` check removed | the `from_step: true` test |
| `.strip()` dropped from the values check | the whitespace test |
| the workflow lookup moved above the device checks | the unplugged-browser test |

- [ ] **Step 10: Gates, then commit**

---

## Task 6: `GET /v1/workflow-runs` and `GET /v1/workflow-runs/{run_id}`

**Files:** Modify: `workflow_runs.py` (application, router), `container.py`, `schemas.py`. Test: unit + integration.

**Interfaces:**
- Consumes: `WorkflowRunModel` (Task 5).
- Produces: `ListWorkflowRuns.execute(ctx, *, workflow_id: str | None, awaiting: bool) -> tuple[WorkflowRun, ...]`, `GetWorkflowRun.execute(ctx, *, run_id: str) -> WorkflowRun`.

The rig's are `api.py:1152` and `api.py:1217`.

The repository already has what both need:
`for_workflow(tenant, workflow_id)` — *"Oldest first, as the rig listed them"*
(`ports/repositories.py:650`) — and `awaiting(tenant)`, which returns
`(run id, step ord, what the step says)` for every step waiting on a person.

`awaiting`'s docstring records **a stated divergence from the rig**: the rig
reported the deepest parked step of each run, this returns every one of them,
`ord` ascending, and *"Plan 3 owns the choice between deepest and shallowest."*
Plan 3 did not make it. **This plan makes it: return every parked step, ord
ascending, matching the repository.** Write the ruling into the route's
docstring and delete the "Plan 3 owns" sentence from the port, replacing it with
what was decided and where.

`get` returns `None` rather than raising — *"every caller answers 404 itself"*
(`:646`). So this route raises `NotFound`, which is already mapped.

- [ ] **Step 1: Write the failing tests**, including:

```python
async def test_a_run_of_another_tenant_is_a_404_and_not_a_403() -> None:
    """A 403 confirms the id exists. Run ids are unguessable and the answer to
    "is this yours" must not differ from the answer to "does this exist"."""


async def test_the_list_is_oldest_first_and_the_test_would_notice_the_reverse() -> None:
    """Rule 2: three rows, not two -- a set or a reversed pair agrees with a
    two-element ordering assertion once in two. Re-run under several
    PYTHONHASHSEED values. Phase 4a shipped exactly this defect twice."""


async def test_awaiting_returns_every_parked_step_and_not_only_the_deepest() -> None:
    """The divergence this plan settles. One run parked at two steps returns
    two rows, ord ascending."""
```

- [ ] **Step 2: Run them to verify they fail**
- [ ] **Step 3: The two use cases**
- [ ] **Step 4: The routes and their models**
- [ ] **Step 5: Update the port docstring** — replace *"Plan 3 owns the choice"* with the decision and this plan's name
- [ ] **Step 6: Integration test against real Postgres**
- [ ] **Step 7: Mutation-check** — reverse the list order; drop the tenant check; return only the deepest parked step
- [ ] **Step 8: Gates, then commit**

---

## Task 7: `POST /v1/workflow-runs/{run_id}/abort`

**Files:** Modify: `workflow_runs.py` (both), `container.py`, `schemas.py`. Test: unit + integration.

**Interfaces:**
- Consumes: `Container.stops` (`container.py:225`), Task 5's use-case module.
- Produces: `AbortWorkflowRun.execute(ctx, *, run_id: str) -> WorkflowRun`.

The rig's is `api.py:1237`. This closes **carried item 1**: *"No route can reach
a parked workflow run to stop it."*

`StopRun` (`application/execution/read_runs.py:68-79`) is the skill-run half and
resolves through `uow.runs`. **Do not extend it.** It takes a `RunId` and this
takes a `str`, and `new_run_id`'s docstring
(`domain/execution/workflow_run.py:34-45`) explains why the two id spaces stay
apart: *"a string that round-trips through the wrong repository will be looked
up, found missing, and read as a run that does not exist rather than as a type
error."*

Copy `StopRun`'s two refusals, which are correct for both:

- a run that is not `running` → `CannotStop(f"that run already {outcome}")`
- a run with no `device_id` → *"that run is not being performed in a browser
  this process is driving"*

and its `ponytail:` note about being in-process only.

- [ ] **Step 1: Write the failing tests**, including:

```python
async def test_a_skill_runs_id_is_not_found_here_rather_than_type_confused() -> None:
    """The two id spaces look alike -- `run_` plus 32 hex on both sides. Pass a
    real skill run's id and get a 404, not a 500 and not somebody else's run."""


async def test_aborting_an_already_aborted_run_says_so_rather_than_succeeding() -> None:
    """An idempotent-looking success here is a console reporting something that
    did not happen, which StopRun's docstring says is worse than not offering
    the button."""
```

- [ ] **Step 2: Run them to verify they fail**
- [ ] **Step 3: `AbortWorkflowRun`**
- [ ] **Step 4: Route, model, container factory**
- [ ] **Step 5: Integration test**
- [ ] **Step 6: Mutation-check** — drop the `running` check; drop the `device_id` check; call `stops.ask` with the wrong id (rule 1: guard the caller)
- [ ] **Step 7: Gates, then commit**

---

## Task 8: `POST /v1/workflow-runs/{run_id}/approve`

**Files:** Modify: `workflow_runs.py` (both), `container.py`, `schemas.py`. Test: unit + integration.

**Interfaces:**
- Consumes: `Approvals` (`application/execution/approvals.py:49`), `WorkflowRunRepository.approve`.
- Produces: `ApproveWorkflowStep.execute(ctx, *, run_id: str, ord_: int, device_id: DeviceId | None) -> bool`.

The rig's is `api.py:1270`. **`POST /v1/confirmations/{id}/approve`
(`routers/confirmations.py:38`) is not this door** — it approves a
*confirmation*, keyed on the confirmation and not the run.

Two halves must both happen and the order matters:

1. `workflow_runs.approve(run_id, ord_, at=…, device_id=…)` — the durable
   record. Returns **whether this tap was the one that authorised the step**;
   the first tap wins (`ports/repositories.py:700-707`).
2. `Approvals` — the in-process event the parked `run_workflow` task is waiting
   on. `approvals.py:30`: *"`run_workflow` asks `Stops` after `wait_for` returns
   and before …"*. Read that file before writing.

`approve` is **tenant-blind by design** (`:705`): *"the run id is the only thing
the panel has, and the route has already checked the browser is driving this
run."* **The route must actually do that check.** A tenant-blind repository
method whose route forgot to check is a cross-tenant write, and the docstring is
the only thing standing between the two.

- [ ] **Step 1: Write the failing tests**, including:

```python
async def test_a_browser_that_is_not_driving_this_run_cannot_release_its_write() -> None:
    """The check `approve`'s tenant-blindness is predicated on. Without it the
    docstring at ports/repositories.py:705 is describing a guarantee nothing
    provides."""


async def test_the_second_tap_does_not_overwrite_the_first_authorisation() -> None:
    """`approve` returns whether this tap was the one. A write rescued to the
    second rung parks at the same step and takes a second tap, and the first
    authorisation stands -- it is the one in the audit."""


async def test_a_step_that_is_not_awaiting_is_refused() -> None:
    """Approving a step nobody parked releases nothing and records a person
    authorising a write that was never withheld."""


async def test_the_waiting_task_is_released_and_not_only_the_row_written() -> None:
    """Both halves. A route that writes the row and never fires the event
    leaves the run parked forever with an audit trail saying it was approved --
    the worst of the three possible bugs here."""
```

- [ ] **Step 2: Run them to verify they fail**
- [ ] **Step 3: `ApproveWorkflowStep`**
- [ ] **Step 4: Route, model, container factory**
- [ ] **Step 5: Integration test** — including the two-tap case against real Postgres, where `approve`'s first-tap-wins is enforced by the store and not by the fake
- [ ] **Step 6: Mutation-check** — drop the driving-browser check; fire the event without writing the row; write the row without firing the event; ignore `approve`'s return value
- [ ] **Step 7: Gates, then commit**

---

## Task 9: The two size belts on the observation door

**Files:**
- Modify: `src/sro/config.py`, `src/sro/interface/http/v1/routers/observations.py`
- Test: `tests/unit/interface/test_observation_limits.py`, `tests/integration/…`

**Interfaces:**
- Consumes: nothing.
- Produces: `Settings.observation_batch_events: int = 5000`, `Settings.observation_artifact_bytes: int = 8_000_000`.

The spec's row 3 (`design.md:32`) says `POST /v1/observations` is *"kept, the
rig's belts added: per-device batch ownership, `K_BATCH_EVENTS`,
`K_ARTIFACT_BYTES`."* Per-device ownership is in place — the route takes
`X-Device-Secret` and the use case checks it. **The two limits are not:** grep
finds `K_BATCH_EVENTS` and `K_ARTIFACT_BYTES` in `new_agent_arch/src/rig/api.py`
(`:374`, `:379`, `:498`, `:575`) and **nowhere under `backend/src/`**.

This is not a YAGNI candidate. `store_artifact` takes an unbounded `UploadFile`
and `ingest_observations` an unbounded event list, from a browser extension on an
operator's machine. That is a resource hole on an authenticated but
operator-controlled path.

Rig values, verbatim:

```python
K_ARTIFACT_BYTES = 8_000_000   # api.py:374
K_BATCH_EVENTS = 5000          # api.py:379
```

The rig's refusals, matched:

```python
# api.py:498-501
if isinstance(sent, list) and len(sent) > K_BATCH_EVENTS:
    raise HTTPException(status_code=..., detail=f"{len(sent)} events in one batch; at most {K_BATCH_EVENTS}")

# api.py:575-581 -- reads ONE byte past the limit and refuses on the excess
data = await file.read(K_ARTIFACT_BYTES + 1)
if len(data) > K_ARTIFACT_BYTES:
    raise HTTPException(status_code=413, detail=f"an artifact is at most {K_ARTIFACT_BYTES} bytes")
```

**Read the rig's exact status codes at those lines and match them.** The `+ 1`
read is the point of the artifact belt: it bounds memory rather than measuring
after the fact, so a caller cannot make the process hold a gigabyte in order to
be told the file was too big. Copy the `+ 1` and write a comment saying what it
is for — a later reader will "simplify" it otherwise.

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_batch_one_event_over_the_limit_is_refused() -> None:
    """Exactly one over, not ten thousand: `>` and `>=` differ by one event and
    a test at 10x the limit passes under both."""


async def test_a_batch_exactly_at_the_limit_is_accepted() -> None:
    """The other side of the same boundary. Without it, `>=` passes the test
    above and silently costs every caller one event."""


async def test_an_oversized_artifact_is_refused_without_the_whole_file_in_memory() -> None:
    """Rule 4: the `+ 1` read is the decision this test exists to protect.
    Assert the number of bytes read, not only the status."""
```

- [ ] **Step 2: Run them to verify they fail** — currently both limits are absent, so all three fail
- [ ] **Step 3: Add the two settings**, each with a docstring naming the rig line it came from
- [ ] **Step 4: Add the two checks**
- [ ] **Step 5: Run the tests**
- [ ] **Step 6: Mutation-check** — `>` → `>=` on the batch check (must kill the at-the-limit test); `K_ARTIFACT_BYTES + 1` → `K_ARTIFACT_BYTES` (must kill the bytes-read test)
- [ ] **Step 7: Gates, then commit**

---

## Task 10: `GET /v1/pool`, and the two one-line carried defects

**Batched deliberately.** Three small independent edits, one dispatch, one
review surface. Do not split them into three tasks.

**Files:**
- Create: `src/sro/application/observation/read_pool.py`, `src/sro/interface/http/v1/routers/pool.py`
- Modify: `src/sro/container.py`, `src/sro/interface/http/app.py`, `src/sro/interface/http/schemas.py`, `src/sro/infrastructure/db/repositories.py`, `src/sro/interface/http/v1/routers/spend.py`
- Test: `tests/unit/interface/test_pool_route.py`, `tests/integration/…`, `tests/unit/application/test_audit_order.py`

### 10a — `GET /v1/pool`

The rig's is `api.py:794`. 4a Task 10 row 9 calls it *"the cheap one"*:
everything behind it exists — `domain/observation/pool.py` and
`PoolRepository.retired` (`ports/repositories.py:623`) — and **nothing over the
wire can read `retired`**, which is the exact blindness the rig's docstring says
the route exists to remove.

Worth doing now rather than in a later phase because it is the only way to check
the pool-rotation measurement from outside a script: ten simulated passes showed
pass 1 at 81%, pass 2 at 96%, and 19 gestures never shown, all `claimed`. That
number came from a simulation. This route makes it observable.

Two reads, live and retired — *"an entry is retired exactly when it has a
`reason`"* (`:587-590`). Tenant-only, read-only.

- [ ] Test: a retired entry appears under `retired` and not under `waiting`,
      **and carries its reason** — the reason is the whole difference between
      the two lists
- [ ] Test: live entries are oldest first (three of them, rule 2)
- [ ] `ReadPool`, route, model, container factory, `include_router`
- [ ] Integration test against real Postgres

### 10b — `SqlDeviceRepository.since` has no id tiebreak

Carried item 5. `infrastructure/db/repositories.py:653` orders on
`registered_at.desc()` alone. `ReadAudit` reads four collections
(`application/analytics/audit.py:75-86`) and **the other three all break their
tie**: `workflow_runs.since` on `id.desc()` (`db/workflow_runs.py:226`),
`offers.since` on `seq` (`db/offers.py:118`), `chats.since` on `id.desc()`
(`db/offers.py:180`).

**The fix is `.id.desc()`.**

- [ ] Test first: two devices registered at the **same instant** must come back
      in a stable order across repeated reads. This project's `FakeClock`
      returns the same instant on every call, which is what makes the collision
      easy to construct — and is also what made a phase-4a test agree with its
      own mutant. Assert the exact order, not a multiset.
- [ ] Run it — expect a failure, or a pass-by-luck. **If it passes before the
      fix, it is not testing the tie.** Re-run under several `PYTHONHASHSEED`
      values and against real Postgres before believing it.
- [ ] Apply `.id.desc()`; the test passes
- [ ] Mutation-check: remove the tiebreak; the test must fail

> `list_for_tenant` in the same class (`repositories.py:632`) has no tiebreak
> either. It is **not** one of the audit's four and is out of scope. Leave it,
> and say in your report that you left it.

### 10c — a comment with no test behind it

Carried item 9. `routers/spend.py:30-31` says *"nothing here catches a domain
error"*, inherited word for word from `routers/audit.py:22`. **The project's
fourth test rule says a comment recording a decision needs a test that fails
when the decision stops being true, and this one has none in either file.**

- [ ] Write a test asserting a domain error raised beneath `/v1/spend` reaches
      the installed handler and comes back as a problem document with the right
      status — rather than being swallowed into a 200 or a bare 500
- [ ] The same test for `/v1/audit`, since the comment is in both files
- [ ] Mutation-check: wrap the route body in `try/except DomainError: return
      <empty>`; both tests must fail

- [ ] **Gates, then commit** — one commit per lettered part is fine; three
      commits with one review is the point of batching, not one commit with
      three unrelated changes in it.

---

## Task 11: The count, the spec amendment, and what 5 inherits

**Files:** Modify: this plan file, `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`, `docs/new-agent-doc-arc/findings.md`

No code changes. Read every line number off the file rather than copying it from
a brief — 4a's equivalent task found **seven** things its own plan's table had
wrong, two of which would have sent this plan hunting phantoms.

- [ ] **Step 1: Re-count the rig's routes against the backend.**

4a's Task 10 counted **26** rig routes: 9 ported before 4a, 8 in 4a, **7 in
4b**, 3 not ported, 2 dropped. Verify the seven this plan claims are the seven
that table named — `POST /v1/mine`, `POST /v1/runs`, `GET /v1/runs`, `GET
/v1/runs/{run_id}`, `POST /v1/runs/{run_id}/abort`, `POST
/v1/runs/{run_id}/approve`, `POST /v1/chat` — and that each now has a backend
answer. Rebuild the totals. **If they do not sum to 26, the error is in this
plan and not in the arithmetic.**

- [ ] **Step 2: Amend the spec.**

`design.md:42` says the rig's routes are ported *"same paths and bodies so the
extension changes only its base URL."* Two things have falsified it and both
need writing into the spec, not only into a plan file nobody reads after the
branch lands:

1. **The four run routes moved to `/v1/workflow-runs`** — the collision
   documented at the head of this plan.
2. **`rigHeaders()` sends none of the backend's headers**, so `/v1/shapes` and
   `/v1/offers` were already unreachable from the extension before this plan
   started. Review 2 of phase 4a found it; `reportOffer()` has no status check
   at all and swallows its 403 silently.

- [ ] **Step 3: Re-measure the acceptance criterion.**

The spec asks for **8 of 8 workflows named as themselves and 10 of 11 values.**
The last honest measurement, 2026-09-09, was **4 of 8 and 3 of 11**.

Now that `POST /v1/mine` has a caller, run a real pass **through the route**
rather than through a script, and record what you get. **Quote the criterion's
denominator, never a shrinking one.** "2 of 2" was reported as a pass once on
this project and had to be retracted; do not let it happen twice.

- [ ] **Step 4: Write what phase 5 inherits**, in this plan file, in the shape
      4a used — every carried item with its file and line, and every decision
      with the reason it was made. `.superpowers/` is gitignored and does not
      travel; this section is the record.

  At minimum, carried forward and still open:
  - `RestoreDevice` erases the audit instant — needs a device-event table this
    codebase does not have (carried item 4; a plan of its own)
  - One response carries two spellings of UTC — a domain inconsistency at
    `domain/observation/device.py:29` and `:62` (carried item 6; judged
    acceptable, reason in the schema docstring)
  - `GET /v1/streams`, `GET /v1/gestures` — still unported
  - `GET /` at `/rig` — still the spec's open item
  - `K_MAX_GESTURE_TOKENS`, `K_MAX_CROSSING_TOKENS` and the `kb` subtraction are
    all tuned against an estimator measured to be **1.697× wrong**. Only the
    price-boundary cap was corrected. **Each of the others is the same bug in
    waiting**, and `K_MAX_GESTURE_TOKENS` has no docstring, so there is nothing
    to re-tune it against.
  - Parameter learning ignores `gesture.requests` entirely and takes parameters
    only from `typed_values` — an **ADR 005 violation**, evidenced by one
    workflow that learned zero parameters while its recorded POST body named
    every one of them. Its own spec.

- [ ] **Step 5: Update `docs/new-agent-doc-arc/findings.md`** — the nine open
      items recorded there on 2026-09-09 each carry a "settled by". Mark the
      ones this plan settled, and **add the ones it opened.** A plan that closes
      nine and opens four while reporting only the nine is the shrinking
      denominator wearing a different hat.

- [ ] **Step 6: Commit**

---

## Self-Review

**Spec coverage.** All seven of 4b's routes from 4a's Task 10 table have a task:
`/v1/mine` → Task 2; `/v1/chat` → Task 3; `POST /v1/runs` → Task 5; `GET
/v1/runs` and `GET /v1/runs/{run_id}` → Task 6; abort → Task 7; approve → Task
8. The spec's *observations extension* (`design.md:32`) → Task 9. Carried items
1, 3, 5 and 9 → Tasks 7, 4, 10b, 10c. Carried items 2 (`run_workflow` /
`container.asker` / `mine` with no caller) → Tasks 1, 2, 5.

**Not covered, and named as such:** carried item 4 (`RestoreDevice` erasing the
audit instant — needs a table this codebase does not have) and carried item 6
(two spellings of UTC — a domain fix, judged acceptable with the reason
recorded). Both are carried to Task 11's inheritance section rather than dropped.

**Type consistency.** `WorkflowRun.id` is a plain `str` throughout — Tasks 5, 6,
7 and 8 all take `run_id: str`, never `RunId`. `sro.domain.execution.run.RunId`
belongs to skill runs only. `ord_` is an `int` and matches
`WorkflowRunRepository.approve(run_id, ord_, ...)` at `ports/repositories.py:700`.
`MinePass` and `ReadChat` both take `asker: Asker | None` in their constructors
and refuse at `execute`, so `container.mine_pass()` stays buildable with no
model configured.

**Placeholder scan.** Tasks 3, 6, 7, 8 and 10 give test names and intent rather
than complete bodies, because each is structurally the twin of a task above it
that does carry full code — Task 3 of Task 2, Tasks 6–8 of Task 5. Every one
names the exact file, line and docstring the implementer must read first. The
`...` inside Task 2's test bodies is deliberate and marked: the fakes' APIs are
read from `tests/unit/fakes.py` rather than guessed at here, because guessing
them is how a plan produces a test that compiles against a fake that does not
exist.

**One thing this plan cannot check for itself.** Task 5 assumes `RunDispatcher`
can drive a workflow run the way it drives a skill run. That was inferred from
`routers/runs.py:248` and **not verified**. If it turns out to be wrong, Task 5
is bigger than it looks and its implementer should say so in the report rather
than working around it — that is a plan defect, and the ruling belongs to
whoever finds it.
