# The panel as a ledger — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the extension's side panel as one ledger of what happened in this operator's browser today — offers, mail matches, page nudges, runs with live step rows, questions, results and failures — with the composer alone at the bottom and the housekeeping under a profile menu at the top.

**Architecture:** The panel stays vanilla JS with no build step and no `innerHTML`. `panel.js` is split into five pure "thing to DOM" modules that node tests exercise against the same fake document `transcript.test.mjs` already uses. The thread on the server stays the source of truth for anything that must survive the panel closing; two things are deliberately browser-held and never stored: the values a mail was read for (the domain refuses to store mail content) and page nudges (a nudge per visit persisted server-side would be noise). Backend changes are four small, separately shippable additions.

**Tech Stack:** Chrome MV3 extension (ES modules, `chrome.storage`, `chrome.scripting`, `chrome.webNavigation`), node `assert` tests, FastAPI + pytest backend, `brand.generated.css` tokens.

**Spec:** `docs/superpowers/specs/2026-09-03-the-panel-as-a-ledger-design.md`. Two amendments made while planning, both narrower than the spec and both for reasons the domain already holds:

1. §6 — a `mail_match` message stores the task, the trigger, the browser's offer id and the *names* of values read. The values themselves, the sender and the subject are drawn from the offer the browser holds (`state.offers`) and are never written to the thread. `agents.py:watch_matched` says why: `ValueAt` exists to keep mail content out of storage. If the browser no longer holds the offer, the entry says so and asks for the mail to be opened again.
2. §7 — nudges are browser-held (`state.nudges`, `state.muted`). Only an answered nudge produces anything on the server, and that thing is a run. The "three mutes in a week" rule is `// ponytail:` deferred until the console has a place to un-mute.

## Global Constraints

- **No `innerHTML` anywhere in `panel/`.** Every module's test asserts the fake document saw no markup assignment. Words on this surface are typed by operators or written by models.
- **A message is a thing said; the press is the authorisation.** Drawing an entry starts nothing. Buttons hand the answer to `panel.js`, which makes the same worker call it makes today.
- **Nothing claims more than the evidence.** The today line shows only `SummaryModel` fields. A step is `✓` only when its assertions held; otherwise it is the warn glyph.
- **Every state survives at 360 px.** Long hostnames, long task names, long refusal sentences.
- **No modals, no toasts.** Nudges, questions and failures are ledger entries; the in-page pill is the one exception and it opens the panel.
- **Brand tokens only.** `panel.css` reads `--brand-*` from `brand.generated.css`. No hex literal is added.
- **A code change to the backend is not live until the worker and API restart.**
- Never `git add -A`; commit the paths each task names, then `git show --stat HEAD`.
- Backend gates before each backend commit: `cd backend && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy --strict src tests/unit/fakes.py && uv run lint-imports`. Extension gate: `make test-extension && make lint-extension`.

---

## File structure

**Extension, `new-chrome-extension/src/`**

| File | Responsibility |
|---|---|
| `panel/ledger.js` (from `transcript.js`) | A thread plus browser-held entries to DOM: time rail, one builder per `decision.kind`, answered state. Pure. |
| `panel/strip.js` | Brand row, status chip, profile menu, the four expand-yourself cases. Pure. |
| `panel/today.js` | Three numbers from a summary. Pure. |
| `panel/run-card.js` | A run's step rows, glyphs, `change`, notes, pause and stop. Pure. |
| `panel/nudge.js` | Fire, three ends, once per visit, mute. Pure over an injected clock. |
| `panel/panel.js` | Wiring only: status, thread, refresh, composer, the worker calls. |
| `panel/panel.css` | Rewritten to the §10 scale. |
| `panel/panel.html` | Four bands. |
| `background/api.js` | `summary`, `runValues`, `sayToRun`. |
| `background/state.js` | `nudges`, `muted`. |
| `background/service-worker.js` | `nudge-*` message kinds; a navigation hook that asks `nudge.js` whether to fire. |
| `background/showing.js` | `showNudge(tabId, text)` / `hideNudge(tabId)`, a pill in the same shadow root idiom as the band. |

**Backend, `backend/src/sro/`**

| File | Responsibility |
|---|---|
| `domain/observation/candidate.py` | `Episode.starts_on`, `TaskCandidate.starts_on`. |
| `application/observation/segment.py` | Sets `starts_on` from the first observed URL of the run. |
| `interface/http/schemas.py` | `CandidateModel.starts_on`, `SayRequest.run_id`, `RunValuesRequest`. |
| `domain/chat/thread.py` | `Said` enum naming every `decision.kind`. |
| `application/chat/converse.py` | `kind` on the run and result messages; a note on a run. |
| `domain/execution/run.py` | `Run.revise(values, at)`. |
| `interface/http/v1/routers/runs.py` | `POST /runs/{id}/values`. |
| `interface/http/v1/routers/agents.py` | `watch_matched` writes a `mail_match` message once per offer. |

---

# Track B — backend (four small tasks, any order, each its own commit)

### Task B1 — A candidate knows the page it starts on

**Files:**
- Modify: `backend/src/sro/domain/observation/candidate.py:41-58` (Episode), `:133-151` (TaskCandidate)
- Modify: `backend/src/sro/application/observation/segment.py:234-246`
- Modify: `backend/src/sro/application/observation/mine.py:109-116`
- Modify: `backend/src/sro/interface/http/schemas.py` (`CandidateModel`)
- Test: `backend/tests/unit/application/test_where_a_task_starts.py`

**Interfaces:**
- Produces: `Episode.starts_on: str` (host + path, no query, `""` when no URL was seen), `TaskCandidate.starts_on: str`, `CandidateModel.starts_on: str`.

- [ ] **Step 1: Write the failing test**

```python
"""A nudge fires when the operator lands on the page a task starts on, so the
candidate has to remember that page. It is the first URL seen in the first
episode, host and path only: the query string is where a WMS puts session ids
and timestamps, and a page that is never the same page twice never nudges."""

from datetime import UTC, datetime, timedelta

from sro.application.observation.segment import Observed, segment
from sro.domain.shared.identifiers import BatchId

AT = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)
BATCH = BatchId("bat_one")


def _gesture(seconds: int, url: str) -> Observed:
    return Observed(at=AT + timedelta(seconds=seconds), kind="gesture", host="wms.example", batch_id=BATCH, url=url)


def _call(seconds: int) -> Observed:
    return Observed(
        at=AT + timedelta(seconds=seconds), kind="request", host="wms.example", batch_id=BATCH,
        method="POST", url="https://wms.example/api/suppliers", mutating=True,
    )


def test_an_episode_starts_on_the_first_page_it_saw_without_its_query() -> None:
    [piece] = segment([_gesture(0, "https://wms.example/ui/suppliers/new?sid=abc&t=1"), _call(3)])
    assert piece.episode.starts_on == "wms.example/ui/suppliers/new"


def test_an_episode_with_no_url_starts_nowhere() -> None:
    [piece] = segment([_gesture(0, ""), _call(3)])
    assert piece.episode.starts_on == ""
```

- [ ] **Step 2: Run it**

Run: `cd backend && uv run pytest tests/unit/application/test_where_a_task_starts.py -q`
Expected: FAIL, `Episode` has no attribute `starts_on`.

- [ ] **Step 3: Add the field and set it**

In `candidate.py`, on `Episode` after `touched_until`:

```python
    starts_on: str = ""
    """Host and path of the first page this episode was seen on, no query. The
    page a nudge fires on; empty when no URL was observed."""
```

On `TaskCandidate` after `offered_at`:

```python
    starts_on: str = ""
    """Where the first episode started. Carried so the panel can ask "is this
    the page?" without loading episodes."""
```

In `segment.py`, above `Segment(...)` at `:234`:

```python
    first_url = next((one.url for one in run if one.url), "")
    parts = urlsplit(first_url)
    starts_on = f"{parts.netloc}{parts.path}".rstrip("/") if parts.netloc else ""
```

and `starts_on=starts_on,` inside `Episode(...)`.

In `mine.py:109`, where `TaskCandidate(` is built, add `starts_on=found.episode.starts_on,`.

In `schemas.py`, `CandidateModel` gains `starts_on: str = ""` and its `of()` passes `candidate.starts_on`.

- [ ] **Step 4: Run the test, then the whole unit suite**

Run: `cd backend && uv run pytest tests/unit/application/test_where_a_task_starts.py tests/unit -q`
Expected: PASS. The candidate mapper round-trips the new field because candidates are documents; if `test_noticing_what_somebody_keeps_doing.py` fails on an equality, extend its expected candidate with `starts_on=""`.

- [ ] **Step 5: Regenerate the wire types and commit**

```bash
make types
git add backend/src/sro/domain/observation/candidate.py backend/src/sro/application/observation/segment.py backend/src/sro/application/observation/mine.py backend/src/sro/interface/http/schemas.py backend/tests/unit/application/test_where_a_task_starts.py frontend/src/lib/api-types.ts
git commit -m "feat(observation): a candidate remembers the page it starts on"
```

### Task B2 — A run's remaining steps can be given new values

**Files:**
- Modify: `backend/src/sro/domain/execution/run.py` (after `called_wrong`, `:406`)
- Modify: `backend/src/sro/interface/http/schemas.py` (add `RunValuesRequest`)
- Modify: `backend/src/sro/interface/http/v1/routers/runs.py` (after `called_wrong`, `:146`)
- Test: `backend/tests/unit/domain/test_a_run_given_new_values.py`

**Interfaces:**
- Produces: `Run.revise(values: Mapping[str, str], at: datetime) -> None`; `POST /v1/runs/{run_id}/values` with body `{"values": {name: value}}` returning `RunModel`.

- [ ] **Step 1: Write the failing test**

```python
"""While a run is going, the operator may change a value the run has not used
yet. What has already been sent is sent; what is still to come uses the new
value. A finished run cannot be revised: there is nothing left for the value
to reach."""

import pytest

from sro.domain.execution.run import Medium, Run, RunId, StepDisposition, StepOutcome
from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f


def _running() -> Run:
    return Run(
        id=RunId("run-1"), tenant_id=f.TENANT, skill_id=SkillId("skill-1"), skill_version=1,
        stage=PromotionStage.ASSISTED, parameters={"address": "A000144886", "name": "Acme"},
        requested_by=f.OPERATOR, started_at=f.at(0), authorized_by=f.OPERATOR, target_system="blue_yonder",
    )


def test_a_running_run_takes_a_new_value_for_what_is_still_to_come() -> None:
    run = _running()
    run.revise({"address": "A000221"}, at=f.at(5))
    assert run.parameters["address"] == "A000221"
    assert run.parameters["name"] == "Acme"
    assert run.revisions == (("address", "A000221", f.at(5)),)


def test_a_name_the_run_never_had_is_refused() -> None:
    with pytest.raises(InvariantViolation, match="no parameter named colour"):
        _running().revise({"colour": "red"}, at=f.at(5))


def test_a_finished_run_cannot_be_revised() -> None:
    run = _running()
    run.record(StepOutcome(index=0, medium=Medium.NETWORK, disposition=StepDisposition.PERFORMED, intent="save", status_code=200))
    run.succeed(f.at(9))
    with pytest.raises(InvariantViolation, match="already finished"):
        run.revise({"address": "A000221"}, at=f.at(10))
```

If `Run.succeed` is named differently in `run.py`, use the method `execute_skill.py` calls when the last step lands; do not add one.

- [ ] **Step 2: Run it**

Run: `cd backend && uv run pytest tests/unit/domain/test_a_run_given_new_values.py -q`
Expected: FAIL, `Run` has no attribute `revise`.

- [ ] **Step 3: Implement**

In `run.py`, `Run` gains a field beside `wrong_because`:

```python
    revisions: tuple[tuple[str, str, datetime], ...] = ()
    """(name, value, when) for every value the operator changed mid-run. The
    record of who decided what the later steps ran with."""
```

and a method after `called_wrong`:

```python
    def revise(self, values: Mapping[str, str], *, at: datetime) -> None:
        """Change values for the steps still to come. Steps already recorded
        keep what they sent; the executor reads `parameters` fresh per step."""
        if self.status is not RunStatus.RUNNING:
            raise InvariantViolation("this run has already finished; nothing is left to revise")
        unknown = [name for name in values if name not in self.parameters]
        if unknown:
            raise InvariantViolation(f"no parameter named {', '.join(unknown)} on this run")
        self.parameters = {**self.parameters, **values}
        self.revisions += tuple((name, value, at) for name, value in values.items())
```

`parameters` is typed `Mapping[str, str]`; reassigning a new dict is fine. Persist `revisions` in the run mapper (`infrastructure/db/mappers`) as a JSON column the same way `wrong_because` was added in `e80960d`; write the migration with `make migration name=run_revisions`.

In `schemas.py`:

```python
class RunValuesRequest(BaseModel):
    values: dict[str, str] = Field(min_length=1)
```

In `runs.py`:

```python
@router.post("/runs/{run_id}/values", status_code=status.HTTP_202_ACCEPTED)
async def revise_run(run_id: str, body: RunValuesRequest, container: ContainerDep, ctx: ContextDep) -> RunModel:
    """The operator changed a value for the steps still to come. Recorded on
    the run as their decision, and read by the next step when it starts."""
    async with container.unit_of_work() as uow:
        run = await uow.runs.get(ctx.tenant_id, RunId(run_id))
        run.revise(body.values, at=container.clock.now())
        await uow.runs.save(run)
        await uow.commit()
    return RunModel.of(run)
```

`grep -rn "unit_of_work()" backend/src/sro/interface/` must return nothing (AGENTS.md), so this body goes into a use case `application/execution/revise_run.py` (`ReviseRun(uow, clock).execute(ctx, run_id, values) -> Run`) exposed as `container.revise_run()`, and the router calls that. Also post the operator message: after saving, `await container.converse().note(ctx, thread_id=..., text=f"changed {name} to {value}")` for the thread that carries this run — find it with `uow.threads.holding_run(ctx.tenant_id, run.id)`; if no such repository method exists, add it to the port and the fake (one method, one query on `decision->>'run_id'`).

- [ ] **Step 4: Run tests, gates, commit**

```bash
cd backend && uv run pytest tests/unit tests/contract -q && make types
git add backend/src/sro/domain/execution/run.py backend/src/sro/application/execution/revise_run.py backend/src/sro/container.py backend/src/sro/interface/http/schemas.py backend/src/sro/interface/http/v1/routers/runs.py backend/src/sro/infrastructure/db backend/tests/unit/domain/test_a_run_given_new_values.py frontend/src/lib/api-types.ts
git commit -m "feat(execution): a value changed mid-run reaches the steps still to come"
```

### Task B3 — Every message says what kind of thing it is

**Files:**
- Modify: `backend/src/sro/domain/chat/thread.py:25-30`
- Modify: `backend/src/sro/application/chat/converse.py:178-265` and `execute()` at `:100`
- Modify: `backend/src/sro/interface/http/schemas.py:1321` (`SayRequest`)
- Test: `backend/tests/unit/application/test_converse.py` (append)

**Interfaces:**
- Produces: `Said` StrEnum in `thread.py`: `OFFER = "offer"`, `MAIL_MATCH = "mail_match"`, `NOTE = "note"`, `RUN = "run"`, `RESULT = "result"`, `QUESTION = "question"`, `FAILURE = "failure"`. `Converse.started` writes `decision["kind"] = Said.RUN`; `performed` writes `Said.RESULT` when the run succeeded and `Said.FAILURE` otherwise. `SayRequest.run_id: str | None` — when set, the operator's message is stored with `decision={"kind": "note", "run_id": ...}` and nothing is resolved.

- [ ] **Step 1: Write the failing tests** (append to `test_converse.py`, using its `_chat(uow)` helper)

```python
async def test_a_run_message_says_it_is_a_run_and_its_result_says_it_is_a_result() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(f.ctx())
    skill = await uow.skills.get(f.TENANT, SkillId("skill-1"))
    thread = await converse.started(f.ctx(), thread_id=thread.id, run_id=RunId("run-1"), skill=skill)
    assert thread.messages[-1].decision["kind"] == "run"


async def test_a_note_to_a_run_is_kept_and_resolves_nothing() -> None:
    uow = FakeUnitOfWork()
    await _taught(uow)
    start, converse = _chat(uow)
    thread = await start.execute(f.ctx())
    thread = await converse.execute(f.ctx(), thread_id=thread.id, text="use the north yard address", run_id=RunId("run-1"))
    last = thread.messages[-1]
    assert last.speaker is Speaker.OPERATOR
    assert last.decision == {"kind": "note", "run_id": "run-1"}
    assert len(thread.messages) == 1, "a note is not a request; nothing answered it"
```

- [ ] **Step 2: Run them**

Run: `cd backend && uv run pytest tests/unit/application/test_converse.py -q`
Expected: FAIL on `decision["kind"]` and on the `run_id` keyword.

- [ ] **Step 3: Implement**

`thread.py`, after `Speaker`:

```python
class Said(StrEnum):
    """What a message's `decision["kind"]` may be. Named once so the panel and
    the console draw from one list and an unknown kind is an old client, not a
    typo."""

    OFFER = "offer"
    MAIL_MATCH = "mail_match"
    NOTE = "note"
    RUN = "run"
    RESULT = "result"
    QUESTION = "question"
    FAILURE = "failure"
```

`converse.py`: `started()` adds `"kind": Said.RUN` to its decision; `performed()` adds `"kind": Said.RESULT if run.status is RunStatus.SUCCEEDED else Said.FAILURE` and, for a failure, `"next": "retry" if run.can_escalate else "ask"` — where `can_escalate` is whether `next_medium(...)` in `domain/execution/escalation.py` answers for the failed step's medium and reason; expose that as a property on `Run` if it is not already one, and `"open"` when the failure reason is `StepOutcome.unreachable`; `execute()` gains `run_id: RunId | None = None` and, when set, appends `Message(speaker=OPERATOR, text=text, decision={"kind": Said.NOTE, "run_id": run_id.value})`, saves, commits, and returns before resolving intent. `propose.py:234` uses `Said.OFFER` in place of the literal. `SayRequest` gains `run_id: str | None = None` and `threads.py:say` passes `run_id=RunId(body.run_id) if body.run_id else None`.

- [ ] **Step 4: Run, gate, commit**

```bash
cd backend && uv run pytest tests/unit tests/contract -q && make types
git add backend/src/sro/domain/chat/thread.py backend/src/sro/application/chat/converse.py backend/src/sro/application/observation/propose.py backend/src/sro/interface/http/schemas.py backend/src/sro/interface/http/v1/routers/threads.py backend/tests/unit/application/test_converse.py frontend/src/lib/api-types.ts
git commit -m "feat(chat): every message says what kind of thing it is, and a run can be told something"
```

### Task B4 — A matched mail is written into the conversation, once

**Files:**
- Modify: `backend/src/sro/interface/http/v1/routers/agents.py:163-215`
- Modify: `backend/src/sro/application/chat/converse.py` (new method `matched`)
- Test: `backend/tests/unit/interface/test_the_mail_rules_a_browser_holds.py` (append)

**Interfaces:**
- Consumes: `Said.MAIL_MATCH` (B3).
- Produces: `POST /v1/agents/{device_id}/watches/{trigger_id}/matched?offer=<id>` also appends to the operator's current thread a `SYSTEM` message `text="A mail matched {skill name}"`, `decision={"kind": "mail_match", "offer_id", "trigger_id", "skill_id", "skill_name", "read": [names], "missing": [names]}`. Written once per `offer_id`.

- [ ] **Step 1: Write the failing test** (append; `_create_watch`, `_proving`, `LENA` exist in the file)

```python
async def test_a_match_is_said_in_the_thread_once_and_carries_names_not_values(client, uow) -> None:
    await _create_watch(client, uow, device_id=LENA)
    trigger_id = (await client.get(f"/v1/agents/{LENA.value}/watches", headers=_proving(LENA))).json()[0]["watch"]["id"]

    for _ in range(2):
        await client.post(
            f"/v1/agents/{LENA.value}/watches/{trigger_id}/matched?offer=off_1",
            json={"shipment_id": "SH-4471"}, headers=_proving(LENA),
        )

    thread = (await client.get("/v1/threads/current")).json()
    matches = [m for m in thread["messages"] if m["decision"].get("kind") == "mail_match"]
    assert len(matches) == 1, "the same offer was said twice"
    assert matches[0]["decision"]["read"] == ["shipment_id"]
    assert "SH-4471" not in json.dumps(thread), "a value read from a mail was written down"
```

- [ ] **Step 2: Run it**

Run: `cd backend && uv run pytest tests/unit/interface/test_the_mail_rules_a_browser_holds.py -q -k said_in_the_thread`
Expected: FAIL, zero `mail_match` messages.

- [ ] **Step 3: Implement**

`converse.py`:

```python
    async def matched(self, ctx: RequestContext, *, offer_id: str, trigger_id: str, skill: Skill, read: Sequence[str], missing: Sequence[str]) -> None:
        """A mail matched a task. Said once per offer, names only: the values
        stay in the browser that read them."""
        async with self._uow as uow:
            thread = await uow.threads.current(ctx.tenant_id, ctx.principal_id) or await self._open(uow, ctx)
            if any(m.decision.get("offer_id") == offer_id for m in thread.messages):
                return
            thread.say(Message(
                id=self._ids.new_message_id(), speaker=Speaker.SYSTEM,
                text=f"A mail matched {skill.name}", said_at=self._clock.now(),
                decision={"kind": Said.MAIL_MATCH, "offer_id": offer_id, "trigger_id": trigger_id,
                          "skill_id": skill.id.value, "skill_name": skill.name,
                          "read": list(read), "missing": list(missing)},
            ))
            await uow.threads.save(thread)
            await uow.commit()
```

`uow.threads.current(...)` is whatever `GET /v1/threads/current` uses; reuse it and its "make one if none" path (`_open` is that, factored out of `StartThread` if it lives there). `agents.py:watch_matched` gains `offer: str | None = None` as a query parameter and, when given, calls `container.converse().matched(...)` with `read=sorted(running_with)` before returning. The panel's own offer id is what `watch.js` already mints.

- [ ] **Step 4: Run, gate, commit**

```bash
cd backend && uv run pytest tests/unit tests/contract -q && make types
git add backend/src/sro/application/chat/converse.py backend/src/sro/interface/http/v1/routers/agents.py backend/tests/unit/interface/test_the_mail_rules_a_browser_holds.py frontend/src/lib/api-types.ts
git commit -m "feat(watch): a matched mail is said in the conversation, once, by name"
```

---

# Track A — extension

Order matters here: A1 first (everything draws through it), then A2 to A6 in any order, A7 last.

### Task A1 — `ledger.js`: a thread and the browser's own entries, drawn

**Files:**
- Create: `new-chrome-extension/src/panel/ledger.js` (move `transcript.js` here with `git mv`, then grow it)
- Test: `new-chrome-extension/src/panel/ledger.test.mjs` (move `transcript.test.mjs` with `git mv`, then grow it)
- Modify: `Makefile:150-163` (rename the test line)

**Interfaces:**
- Produces: `ledger(thread, local, { onPress, onChange, onSay }) -> HTMLElement`. `thread` is the server thread. `local` is `{ offers: [...], nudges: [...] }` from the worker's status, merged by time. `onPress(answer, entry, where, button)` for every button; `answer` is one of `"do" | "no" | "run" | "not-here" | "undo" | "wrong" | "retry" | "ask" | "open" | "pause" | "stop" | "choice:<value>"`. `composer(onSay, { placeholder })` exported as today.
- Produces: `KINDS` — the set of `decision.kind` values this file draws, exported for the test.

- [ ] **Step 1: Move and rename**

```bash
cd new-chrome-extension/src/panel && git mv transcript.js ledger.js && git mv transcript.test.mjs ledger.test.mjs
sed -i '' 's#panel/transcript.test.mjs#panel/ledger.test.mjs#' ../../../Makefile
sed -i '' 's#./transcript.js#./ledger.js#; s#transcript(#ledger(#g' ledger.test.mjs panel.js panel.test.mjs
```

Run: `make test-extension`. Expected: PASS, nothing changed but names.

- [ ] **Step 2: Write the failing tests** (append to `ledger.test.mjs`; `node()`, `words()`, `of()`, `messages()`, `WHEN` exist there)

```js
// A time rail: one time per minute, not per message.
{
  const drawn = ledger({ id: "t", messages: [
    { id: "1", speaker: "system", text: "a", said_at: "2026-09-03T12:04:10Z", decision: {} },
    { id: "2", speaker: "operator", text: "b", said_at: "2026-09-03T12:04:40Z", decision: {} },
    { id: "3", speaker: "system", text: "c", said_at: "2026-09-03T12:06:00Z", decision: {} },
  ] }, { offers: [], nudges: [] });
  const times = of(drawn, "time").map((t) => t.textContent);
  assert.deepStrictEqual(times, ["12:04", "", "12:06"]);
}

// Every kind draws its buttons; an unknown kind draws its words and nothing else.
{
  const one = (kind, extra = {}) => ({ id: kind, speaker: "system", text: kind, said_at: WHEN, decision: { kind, ...extra } });
  const drawn = ledger({ id: "t", messages: [
    one("offer", { candidate_id: "c1" }),
    one("result", { run_id: "r1", reversal: { skill_id: "s", parameters: {} } }),
    one("failure", { run_id: "r2", next: "retry" }),
    one("question", { run_id: "r3", choices: ["A000144886", "A000221"] }),
    one("somethingnew"),
  ] }, { offers: [], nudges: [] });
  const labels = (i) => of(messages(drawn)[i], "button").map((b) => b.textContent);
  assert.deepStrictEqual(labels(0), ["Do the next one", "Not now"]);
  assert.deepStrictEqual(labels(1), ["Undo that", "It's wrong — I'll fix it"]);
  assert.deepStrictEqual(labels(2), ["Try another way"]);
  assert.deepStrictEqual(labels(3), ["A000144886", "A000221"]);
  assert.strictEqual(of(messages(drawn)[3], "input").length, 1, "a question takes a typed answer too");
  assert.deepStrictEqual(labels(4), []);
}

// A browser-held nudge is merged into the thread by time and carries the accent.
{
  const drawn = ledger({ id: "t", messages: [
    { id: "1", speaker: "system", text: "a", said_at: "2026-09-03T12:04:10Z", decision: {} },
  ] }, { offers: [], nudges: [{ id: "n1", at: "2026-09-03T12:05:00Z", candidateId: "c1", title: "Create a supplier", state: "open" }] });
  const items = messages(drawn);
  assert.strictEqual(items.length, 2);
  assert.strictEqual(items[1].dataset.kind, "nudge");
  assert.deepStrictEqual(of(items[1], "button").map((b) => b.textContent), ["Do it", "Not for this page"]);
}

// A nudge that ended keeps one line and no buttons.
{
  const drawn = ledger({ id: "t", messages: [] }, { offers: [], nudges: [{ id: "n1", at: WHEN, title: "Create a supplier", state: "by-hand" }] });
  assert.deepStrictEqual(of(messages(drawn)[0], "button"), []);
  assert.match(words(drawn), /did it by hand/);
}

assert.deepStrictEqual(asMarkup, [], "ledger.js wrote markup");
console.log("ledger: ok");
```

Add `time` to the fake `node()`'s `querySelectorAll` matching: it matches on `tag`, so the rail element must be created with `document.createElement("time")`.

- [ ] **Step 3: Run**

Run: `node new-chrome-extension/src/panel/ledger.test.mjs`
Expected: FAIL, `ledger` does not accept a second argument / no `time` elements.

- [ ] **Step 4: Implement**

Replace `transcript()` with:

```js
/** The kinds this file knows how to draw, and the answers each offers. */
export const KINDS = {
  offer:      { buttons: [["do", "Do the next one"], ["no", "Not now"]] },
  mail_match: { buttons: [["run", "Run it"], ["no", "Not now"]] },
  nudge:      { buttons: [["do", "Do it"], ["not-here", "Not for this page"]] },
  run:        { buttons: [] },                       // drawn by run-card.js
  result:     { buttons: [["undo", "Undo that"], ["wrong", "It's wrong — I'll fix it"]] },
  failure:    { buttons: [] },                       // one button, chosen from decision.next
  question:   { buttons: [] },                       // one per choice, plus a field
  note:       { buttons: [] },
};

const NEXT = { retry: "Try another way", ask: "Ask me", open: "Open the page" };

export function ledger(thread, local = { offers: [], nudges: [] }, { onPress, onChange, onSay, runs = new Map() } = {}) {
  const root = document.createElement("div");
  root.className = "ledger";
  const said = document.createElement("ul");
  said.className = "said";
  const spent = alreadyAnswered(thread?.messages || []);
  const entries = [
    ...(thread?.messages || []).map((m) => ({ at: m.said_at, message: m })),
    ...(local.nudges || []).map((n) => ({ at: n.at, nudge: n })),
  ].sort((a, b) => String(a.at).localeCompare(String(b.at)));
  let lastMinute = "";
  for (const entry of entries) {
    const item = entry.message ? saying(entry.message, { onPress, onChange, spent, runs, offers: local.offers }) : nudging(entry.nudge, onPress);
    const minute = hhmm(entry.at);
    const time = document.createElement("time");
    time.textContent = minute === lastMinute ? "" : minute;
    lastMinute = minute;
    item.prepend(time);
    said.append(item);
  }
  root.append(said);
  return root;
}

function hhmm(iso) {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
```

`alreadyAnswered` becomes an export (A3 counts open offers with it). `saying()` keeps its shape and dispatches on `message.decision?.kind`: `offer`, `mail_match`, `nudge`, `result` draw the `KINDS` buttons (skipping when `spent` says answered); `failure` draws one button from `NEXT[decision.next]`; `question` draws one button per `decision.choices` with `answer = "choice:" + value` plus an `<input>` whose Enter calls `onPress("choice:" + input.value, ...)`; `run` calls `runCard(...)` from `run-card.js` (A4) when `runs.get(decision.run_id)` is present, otherwise draws the words; `mail_match` looks up `local.offers.find((o) => o.id === decision.offer_id)` and draws its fields (A5) or the sentence "the mail's values are no longer held here; open the mail again". Every item sets `item.dataset.kind`. `nudging()` draws title, the two buttons when `state === "open"`, or the single line `did it by hand` / `you were on {title}` for `by-hand` / `expired`.

- [ ] **Step 5: Run, lint, commit**

```bash
make test-extension && make lint-extension
git add new-chrome-extension/src/panel/ledger.js new-chrome-extension/src/panel/ledger.test.mjs new-chrome-extension/src/panel/panel.js new-chrome-extension/src/panel/panel.test.mjs Makefile
git commit -m "feat(panel): the thread is a ledger with a time rail, and every kind knows its buttons"
```

### Task A2 — `strip.js`: one line that expands only to be pressed

**Files:**
- Create: `new-chrome-extension/src/panel/strip.js`
- Test: `new-chrome-extension/src/panel/strip.test.mjs`
- Modify: `Makefile:150-163` (add the test)

**Interfaces:**
- Consumes: the worker's `status` as `render()` receives it today (`deviceId`, `capturing`, `paused`, `serverPaused`, `channel`, `teaching`, `watched`, `lastError`, `grantExpired` if present).
- Produces: `strip(status, here, { onMenu, onToggle }) -> HTMLElement`. `here` is `{ tabId, host }`. `onMenu(action)` with `action` one of `"pause" | "resume" | "purge" | "never" | "settings" | "disconnect"`. `needsAPress(status, here) -> string | null` exported: the reason the chip must expand, or `null`.

- [ ] **Step 1: Write the failing test**

```js
import assert from "node:assert";
// same fake document as ledger.test.mjs: copy the `node()` builder and `asMarkup`.
globalThis.document = { createElement: node };
const { strip, needsAPress } = await import("./strip.js");

const here = { tabId: 1, host: "bf56-kms-wms-web-np2.jdadelivers.com" };
const steady = { deviceId: "dev", capturing: true, channel: "open", watched: [{ tabId: 1 }] };

assert.strictEqual(needsAPress(steady, here), null);
assert.strictEqual(needsAPress({ ...steady, deviceId: "" }, here), "not-connected");
assert.strictEqual(needsAPress({ ...steady, grantExpired: true }, here), "grant");
assert.strictEqual(needsAPress({ ...steady, channel: "closed", performing: { runId: "r" } }, here), "channel");
assert.strictEqual(needsAPress({ ...steady, excludedHere: true }, here), "excluded");

{
  const drawn = strip(steady, here, {});
  const chip = drawn.kids.find((k) => k.className === "chip");
  assert.match(chip.textContent + chip.kids.map((k) => k.textContent).join(" "), /bf56-kms.*watching/);
  assert.strictEqual(chip.dataset.open, "false");
}
{
  const drawn = strip({ ...steady, grantExpired: true }, here, {});
  assert.strictEqual(drawn.kids.find((k) => k.className === "chip").dataset.open, "true");
}
{
  const pressed = [];
  const drawn = strip(steady, here, { onMenu: (a) => pressed.push(a) });
  const menu = drawn.kids.find((k) => k.className === "menu");
  const labels = menu.kids.map((b) => b.textContent);
  assert.deepStrictEqual(labels, ["Pause watching", "Delete the last hour", "Never watch this site", "Settings", "Disconnect this browser"]);
  menu.kids[1].listeners.click[0]();
  assert.deepStrictEqual(pressed, ["purge"]);
}
assert.deepStrictEqual(asMarkup, []);
console.log("strip: ok");
```

- [ ] **Step 2: Run** — `node new-chrome-extension/src/panel/strip.test.mjs`. Expected: FAIL, module missing.

- [ ] **Step 3: Implement**

```js
// The strip: who this is, which tab it is beside, and what state that tab is
// in -- as one line, because a line is what a person glances at. It expands
// itself only when there is something to press; every other state is a line.

export function needsAPress(status, here) {
  if (!status.deviceId) return "not-connected";
  if (status.grantExpired) return "grant";
  if (status.channel !== "open" && status.performing) return "channel";
  if (status.excludedHere) return "excluded";
  return null;
}

function stateOf(status, here) {
  if (status.teaching) return ["recording", `recording a demonstration ${status.teaching.elapsed || ""}`.trim()];
  if (status.paused || status.serverPaused) return ["paused", "paused"];
  const watched = (status.watched || []).some((t) => t.tabId === here.tabId);
  if (status.capturing && watched) return ["observing", `watching ${status.since ? sinceText(status.since) : ""}`.trim()];
  return ["idle", "not watched"];
}

export function strip(status, here, { onMenu, onToggle } = {}) {
  const root = document.createElement("header");
  root.className = "strip";
  const row = document.createElement("div"); row.className = "brand";
  const mark = document.createElement("span"); mark.className = "mark"; mark.textContent = "g";
  const name = document.createElement("span"); name.className = "name"; name.textContent = "AI-SRO";
  const consoleLink = document.createElement("button"); consoleLink.type = "button"; consoleLink.className = "link"; consoleLink.textContent = "Console ↗";
  consoleLink.addEventListener("click", () => onMenu?.("console"));
  const disc = document.createElement("button"); disc.type = "button"; disc.className = "disc"; disc.textContent = (status.principal || "?").slice(0, 1).toUpperCase();
  row.append(mark, name, consoleLink, disc);

  const menu = document.createElement("div"); menu.className = "menu"; menu.hidden = true;
  const paused = Boolean(status.paused);
  for (const [action, label] of [
    [paused ? "resume" : "pause", paused ? "Resume watching" : "Pause watching"],
    ["purge", "Delete the last hour"], ["never", "Never watch this site"],
    ["settings", "Settings"], ["disconnect", "Disconnect this browser"],
  ]) {
    const b = document.createElement("button"); b.type = "button"; b.textContent = label;
    b.addEventListener("click", () => { menu.hidden = true; onMenu?.(action); });
    menu.append(b);
  }
  disc.addEventListener("click", () => { menu.hidden = !menu.hidden; });

  const chip = document.createElement("button"); chip.type = "button"; chip.className = "chip";
  const [state, text] = stateOf(status, here);
  chip.dataset.state = state;
  const host = document.createElement("span"); host.className = "host"; host.textContent = here.host || "—";
  const says = document.createElement("span"); says.className = "says"; says.textContent = text;
  chip.append(host, says);
  const why = needsAPress(status, here);
  chip.dataset.open = String(why !== null);
  chip.dataset.why = why || "";
  chip.addEventListener("click", () => onToggle?.());

  root.append(row, menu, chip);
  return root;
}

function sinceText(iso) {
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.max(0, Math.round(ms / 60000));
  return m >= 90 ? `${Math.round(m / 60)} h` : `${m} min`;
}
```

The expanded card under the chip is `watching(status)` as `panel.js` builds it today; `panel.js` appends it after the strip when `chip.dataset.open === "true"` or the operator toggled it (A7).

- [ ] **Step 4: Add to Makefile, run, commit**

Add `node new-chrome-extension/src/panel/strip.test.mjs` to `test-extension`.

```bash
make test-extension && make lint-extension
git add new-chrome-extension/src/panel/strip.js new-chrome-extension/src/panel/strip.test.mjs Makefile
git commit -m "feat(panel): the strip is one line, and it expands only to be pressed"
```

### Task A3 — `today.js`: three numbers somebody measured

**Files:**
- Create: `new-chrome-extension/src/panel/today.js`
- Test: `new-chrome-extension/src/panel/today.test.mjs`
- Modify: `new-chrome-extension/src/background/api.js` (add `summary`), `service-worker.js` (case `"summary"`), `Makefile`

**Interfaces:**
- Consumes: `GET /v1/analytics/summary?since=<iso>` → `SummaryModel` (`doing.runs`, `doing.minutes_saved`, `noticing.worth_offering`).
- Produces: `today(summary, openOffers) -> HTMLElement | null` — `null` when all three are zero. `openOffers` is the count of `offer`/`mail_match` messages in today's thread with no answer, computed by `panel.js` from `ledger.js`'s `alreadyAnswered` (export it).

- [ ] **Step 1: Test**

```js
import assert from "node:assert";
globalThis.document = { createElement: node }; // same fake
const { today } = await import("./today.js");
assert.strictEqual(today({ doing: { runs: 0, minutes_saved: 0 }, noticing: { worth_offering: 0 } }, 0), null);
{
  const line = today({ doing: { runs: 3, minutes_saved: 4.2 }, noticing: { worth_offering: 5 } }, 2);
  assert.strictEqual(line.kids.map((k) => k.textContent).join("|"), "3 done|2 offers|4 min saved");
}
{
  const line = today({ doing: { runs: 1, minutes_saved: 0.5 }, noticing: {} }, 0);
  assert.strictEqual(line.kids.map((k) => k.textContent).join("|"), "1 done|0 offers|30 s saved");
}
console.log("today: ok");
```

- [ ] **Step 2: Implement**

```js
export function today(summary, openOffers = 0) {
  const done = summary?.doing?.runs || 0;
  const minutes = summary?.doing?.minutes_saved || 0;
  if (!done && !openOffers && !minutes) return null;
  const line = document.createElement("div");
  line.className = "today";
  const saved = minutes * 60 >= 90 ? `${Math.round(minutes)} min saved` : `${Math.round(minutes * 60)} s saved`;
  for (const text of [`${done} done`, `${openOffers} offers`, saved]) {
    const n = document.createElement("span"); n.textContent = text; line.append(n);
  }
  return line;
}
```

`api.js`: `summary: (since) => call(\`/v1/analytics/summary?since=${encodeURIComponent(since)}\`)`. `service-worker.js`: `case "summary": return api.summary(message.since);`. `panel.js` asks with `since` = local midnight as ISO.

- [ ] **Step 3: Makefile, run, commit**

```bash
make test-extension && make lint-extension
git add new-chrome-extension/src/panel/today.js new-chrome-extension/src/panel/today.test.mjs new-chrome-extension/src/background/api.js new-chrome-extension/src/background/service-worker.js Makefile
git commit -m "feat(panel): the day in three numbers the system measured"
```

### Task A4 — `run-card.js`: a run that changes while you watch

**Files:**
- Create: `new-chrome-extension/src/panel/run-card.js`
- Test: `new-chrome-extension/src/panel/run-card.test.mjs`
- Modify: `background/api.js` (`runValues`, `sayToRun`), `service-worker.js` (`case "run-values"`, `case "run-note"`), `Makefile`

**Interfaces:**
- Consumes: `RunModel` from `GET /v1/runs/{id}` (fields `status`, `steps[]` with `index`, `intent`, `disposition`, `medium`, `assertion_failures`, `plan_step`), `SkillModel.latest.steps[]` (for the not-yet rows: `intent`, `network_plan.body` parameter names) — `panel.js` already fetches both in `refresh()`. B2's `POST /runs/{id}/values`. B3's note.
- Produces: `runCard({ run, skill, message, notes }, { onPress, onChange }) -> HTMLElement`. `onChange(runId, name, value)`. `glyphFor(step) -> "○" | "●" | "✓" | "✓!" | "✗" | "⏸"` exported.

- [ ] **Step 1: Test**

```js
import assert from "node:assert";
globalThis.document = { createElement: node };
const { runCard, glyphFor } = await import("./run-card.js");

assert.strictEqual(glyphFor({ disposition: "performed", assertion_failures: [] , confirmed: true }), "✓");
assert.strictEqual(glyphFor({ disposition: "performed", assertion_failures: [], confirmed: false }), "✓!");
assert.strictEqual(glyphFor({ disposition: "failed" }), "✗");
assert.strictEqual(glyphFor({ disposition: "withheld" }), "⏸");
assert.strictEqual(glyphFor(null), "○");

const skill = { latest: { steps: [
  { index: 0, intent: "open the form", network_plan: null, ui_plan: {} },
  { index: 1, intent: "fill 4 fields", network_plan: { body: "{{address}}" } },
  { index: 2, intent: "save", network_plan: { body: "{{name}}" } },
] } };
const run = { id: "r1", status: "running", parameters: { address: "A000144886", name: "Acme" }, steps: [
  { index: 0, disposition: "performed", assertion_failures: [], confirmed: true },
] };
{
  const changes = [];
  const card = runCard({ run, skill, message: { text: "Running Create a supplier" }, notes: [] }, { onChange: (id, n, v) => changes.push([id, n, v]) });
  const rows = card.kids.filter((k) => k.className === "step");
  assert.strictEqual(rows.length, 3);
  assert.strictEqual(rows[0].kids[0].textContent, "✓");
  assert.strictEqual(rows[1].kids[0].textContent, "●");
  assert.strictEqual(rows[2].kids[0].textContent, "○");
  const change = rows[2].kids.find((k) => k.tag === "button" && k.textContent === "change");
  assert.ok(change, "a step not yet sent can be changed");
  assert.ok(!rows[0].kids.some((k) => k.textContent === "change"), "a sent step cannot");
  change.listeners.click[0]();
  const field = rows[2].kids.find((k) => k.tag === "input");
  field.value = "Acme Fasteners";
  field.listeners.change[0]();
  assert.deepStrictEqual(changes, [["r1", "name", "Acme Fasteners"]]);
}
{
  const card = runCard({ run: { ...run, status: "succeeded" }, skill, message: {}, notes: [] }, {});
  assert.deepStrictEqual(card.kids.filter((k) => k.tag === "button").map((b) => b.textContent), [], "a finished run has no controls");
}
assert.deepStrictEqual(asMarkup, []);
console.log("run-card: ok");
```

- [ ] **Step 2: Implement**

```js
export function glyphFor(outcome) {
  if (!outcome) return "○";
  if (outcome.disposition === "failed") return "✗";
  if (outcome.disposition === "withheld") return "⏸";
  if (outcome.disposition === "performed") return outcome.confirmed && !(outcome.assertion_failures || []).length ? "✓" : "✓!";
  return "●";
}

const NAMES = /\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g;
function namesIn(step) {
  const text = JSON.stringify(step?.network_plan || step?.ui_plan || step?.tool_plan || "");
  return [...new Set([...text.matchAll(NAMES)].map((m) => m[1]))];
}

export function runCard({ run, skill, message, notes = [] }, { onPress, onChange } = {}) {
  const card = document.createElement("div");
  card.className = "run";
  card.dataset.status = run.status;
  const title = document.createElement("p"); title.className = "what"; title.textContent = message?.text || `Running ${skill?.name || ""}`;
  card.append(title);

  const done = new Map((run.steps || []).map((s) => [s.index, s]));
  const live = run.status === "running";
  const nowAt = Math.max(-1, ...done.keys()) + 1;
  for (const step of skill?.latest?.steps || []) {
    const row = document.createElement("div"); row.className = "step";
    const outcome = done.get(step.index);
    const glyph = document.createElement("span"); glyph.className = "glyph";
    glyph.textContent = outcome ? glyphFor(outcome) : live && step.index === nowAt ? "●" : "○";
    const intent = document.createElement("span"); intent.className = "intent"; intent.textContent = step.intent;
    row.append(glyph, intent);
    const names = namesIn(step);
    if (live && !outcome && step.index > nowAt && names.length) {
      const change = document.createElement("button"); change.type = "button"; change.className = "quiet"; change.textContent = "change";
      change.addEventListener("click", () => {
        change.remove();
        for (const name of names) {
          const field = document.createElement("input"); field.type = "text"; field.value = run.parameters?.[name] ?? ""; field.placeholder = name;
          field.addEventListener("change", () => onChange?.(run.id, name, field.value));
          row.append(field);
        }
      });
      row.append(change);
    }
    for (const note of notes.filter((n) => n.at_step === step.index)) {
      const said = document.createElement("p"); said.className = "note"; said.textContent = note.text; row.append(said);
    }
    card.append(row);
  }
  if (live) {
    const controls = document.createElement("div"); controls.className = "row";
    for (const [answer, label] of [["pause", "Pause"], ["stop", "Stop"]]) {
      const b = document.createElement("button"); b.type = "button"; b.className = "quiet"; b.textContent = label;
      b.addEventListener("click", () => onPress?.(answer, run, card, b)); controls.append(b);
    }
    card.append(controls);
  }
  return card;
}
```

`confirmed` on a step outcome is whatever the backend exposes once sub-plan 1's Verifier lands; until then `panel.js` derives it as `medium === "network" && assertion_failures.length === 0`, which is exactly what `_CLEAN_MEDIA` says today, and the glyph shows `✓!` for every UI step. Honest, and it changes by itself when the Verifier ships.

`api.js`: `runValues: (runId, values) => call(\`/v1/runs/${encodeURIComponent(runId)}/values\`, { method: "POST", body: { values } })` and `sayToRun: (threadId, runId, text) => call(\`/v1/threads/${encodeURIComponent(threadId)}/messages\`, { method: "POST", body: { text, run_id: runId } })`. Two worker cases forward them. "Pause" posts `stop` with `after: "step"` only if the backend has it; otherwise the button says "Stop after this step" and calls the existing stop, and the plan notes it. Do not invent a pause the backend cannot honour.

- [ ] **Step 3: Makefile, run, commit**

```bash
make test-extension && make lint-extension
git add new-chrome-extension/src/panel/run-card.js new-chrome-extension/src/panel/run-card.test.mjs new-chrome-extension/src/background/api.js new-chrome-extension/src/background/service-worker.js Makefile
git commit -m "feat(panel): a run is a card that changes while you watch, and can be changed back"
```

### Task A5 — A matched mail, with its fields

**Files:**
- Modify: `new-chrome-extension/src/panel/ledger.js` (`mail_match` branch)
- Modify: `new-chrome-extension/src/content/watch.js` and `background/service-worker.js:"watch-matched"` to pass `?offer=<id>` (B4) and keep sender/subject on the browser-held offer as `offer.from`, `offer.subject` (already in the frame `watch.js` matched on; never uploaded)
- Test: `ledger.test.mjs` (append)

**Interfaces:**
- Consumes: B4's `mail_match` message; the browser-held offer `{ id, skill, skillId, values, read, missing, from, subject, host, at }`.
- Produces: in `ledger.js`, `mailMatch(message, offer, onPress)` drawing from, subject, one field per `Object.keys(offer.values)` plus one empty field per `offer.missing`, and "Run it" / "Not now". `onPress("run", message, where, button, values)` carries the fields' current values.

- [ ] **Step 1: Test** (append to `ledger.test.mjs`)

```js
{
  const message = { id: "m", speaker: "system", text: "A mail matched Create a supplier", said_at: WHEN,
    decision: { kind: "mail_match", offer_id: "off_1", skill_name: "Create a supplier", read: ["name"], missing: ["address"] } };
  const offer = { id: "off_1", from: "procurement@kenco.com", subject: "New supplier: Acme", values: { name: "Acme" }, missing: ["address"] };
  const pressed = [];
  const drawn = ledger({ id: "t", messages: [message] }, { offers: [offer], nudges: [] }, { onPress: (...a) => pressed.push(a) });
  const item = messages(drawn)[0];
  assert.match(words(item), /procurement@kenco.com.*New supplier: Acme/);
  const fields = of(item, "input");
  assert.deepStrictEqual(fields.map((f) => [f.placeholder, f.value]), [["name", "Acme"], ["address", ""]]);
  fields[1].value = "A000221";
  of(item, "button").find((b) => b.textContent === "Run it").listeners.click[0]();
  assert.strictEqual(pressed[0][0], "run");
  assert.deepStrictEqual(pressed[0][4], { name: "Acme", address: "A000221" });
}
{
  const message = { id: "m", speaker: "system", text: "A mail matched Create a supplier", said_at: WHEN, decision: { kind: "mail_match", offer_id: "gone" } };
  const drawn = ledger({ id: "t", messages: [message] }, { offers: [], nudges: [] });
  assert.match(words(messages(drawn)[0]), /no longer held here/);
  assert.deepStrictEqual(of(messages(drawn)[0], "button"), []);
}
```

- [ ] **Step 2: Implement** — `mailMatch()` in `ledger.js` per the interface; `panel.js`'s `answered()` gains the `values` argument and, for `"run"`, calls `ask({ kind: "watch-fire", offerId, values })`; `service-worker.js:"watch-fire"` passes `values` through to `api.watchFire` (which already posts a body of values). `watch.js` adds `from` and `subject` to the offer it hands the worker; `service-worker.js:"watch-matched"` adds `?offer=` to the call in `api.watchMatched`.

- [ ] **Step 3: Run, commit**

```bash
make test-extension && make lint-extension
git add new-chrome-extension/src/panel/ledger.js new-chrome-extension/src/panel/ledger.test.mjs new-chrome-extension/src/panel/panel.js new-chrome-extension/src/content/watch.js new-chrome-extension/src/background/service-worker.js new-chrome-extension/src/background/api.js
git commit -m "feat(panel): a matched mail is a card with fields, and its values never leave the browser"
```

### Task A6 — `nudge.js`: fires on the page, and ends three ways

**Files:**
- Create: `new-chrome-extension/src/panel/nudge.js`
- Test: `new-chrome-extension/src/panel/nudge.test.mjs`
- Modify: `background/state.js` (`nudges`, `muted`), `background/service-worker.js` (navigation hook, `"nudge-answer"`, `"nudge-mute"`, and the `request` handler marks `by-hand`), `background/showing.js` (`showNudge`, `hideNudge`), `Makefile`
- Test: `backend/tests/browser/test_a_page_the_task_starts_on.py`

**Interfaces:**
- Consumes: B1's `CandidateModel.starts_on`; `api.candidates(host)`.
- Produces, all pure over `{ now }`:
  - `shouldFire({ url, visit, candidates, nudges, muted, performing, now }) -> candidate | null` — `visit` is `${tabId}:${navigationId}` from `webNavigation.onCommitted`, so "once per visit" means once per navigation, not once forever
  - `fire(candidate, now, { tabId, visit }) -> nudge` = `{ id, at, candidateId, title, startsOn, tabId, visit, state: "open" }`
  - `onCall(nudges, { url, method }, now) -> nudges` — the first mutating call on the nudge's host marks it `by-hand`
  - `sweep(nudges, { url, now }) -> nudges` — `expired` after `LIFETIME_MS = 90_000` or when the tab left `startsOn`
  - `mute(muted, startsOn, now) -> muted` — until local midnight
  - `LIFETIME_MS` exported

- [ ] **Step 1: Test**

```js
import assert from "node:assert";
const { shouldFire, fire, onCall, sweep, mute, LIFETIME_MS } = await import("./nudge.js");

const T0 = Date.parse("2026-09-03T12:00:00Z");
const c = { id: "c1", title: "Create a supplier", starts_on: "wms.example/ui/suppliers/new", times_seen: 5, skill_id: "s1" };
const at = (url, visit = "1:100") => ({ url, visit, candidates: [c], nudges: [], muted: {}, performing: null, now: T0 });

assert.strictEqual(shouldFire(at("https://wms.example/ui/suppliers/new?sid=1")), c);
assert.strictEqual(shouldFire(at("https://wms.example/ui/suppliers")), null, "a different page");
assert.strictEqual(shouldFire({ ...at("https://wms.example/ui/suppliers/new"), performing: { runId: "r" } }), null, "not while a run is live");
assert.strictEqual(shouldFire({ ...at("https://wms.example/ui/suppliers/new"), candidates: [{ ...c, times_seen: 2, skill_id: null }] }), null, "not before it is worth offering");

const n = fire(c, T0, { tabId: 1, visit: "1:100" });
assert.strictEqual(shouldFire({ ...at("https://wms.example/ui/suppliers/new"), nudges: [n] }), null, "once per visit");
assert.strictEqual(shouldFire({ ...at("https://wms.example/ui/suppliers/new", "1:101"), nudges: [{ ...n, state: "expired" }] }), c, "a later visit may nudge again");

assert.strictEqual(onCall([n], { url: "https://wms.example/api/suppliers", method: "POST" }, T0 + 5000)[0].state, "by-hand");
assert.strictEqual(onCall([n], { url: "https://wms.example/api/suppliers", method: "GET" }, T0 + 5000)[0].state, "open", "a read is not the task");
assert.strictEqual(sweep([n], { url: "https://wms.example/ui/suppliers/new", now: T0 + LIFETIME_MS - 1 })[0].state, "open");
assert.strictEqual(sweep([n], { url: "https://wms.example/ui/suppliers/new", now: T0 + LIFETIME_MS })[0].state, "expired");
assert.strictEqual(sweep([n], { url: "https://wms.example/ui/orders", now: T0 + 1000 })[0].state, "expired", "navigating away ends it");

const muted = mute({}, c.starts_on, T0);
assert.strictEqual(shouldFire({ ...at("https://wms.example/ui/suppliers/new"), muted }), null);
assert.ok(muted[c.starts_on] > T0);
console.log("nudge: ok");
```

- [ ] **Step 2: Implement**

```js
// A nudge is the panel saying "you've done this here before" the moment the
// operator lands where a known task starts. Short-lived by design: a prompt
// that outlives the task is a prompt that was ignored. Browser-held; nothing
// here is stored on the server until somebody presses "Do it".

export const LIFETIME_MS = 90_000;

function page(url) {
  try { const u = new URL(url); return `${u.host}${u.pathname}`.replace(/\/$/, ""); } catch { return ""; }
}

export function shouldFire({ url, visit, candidates, nudges, muted, performing, now }) {
  if (performing) return null;
  const here = page(url);
  if (!here) return null;
  if (muted[here] && muted[here] > now) return null;
  if (nudges.some((n) => n.state === "open")) return null;
  if (nudges.some((n) => n.startsOn === here && n.visit === visit)) return null;
  return candidates.find((c) => c.starts_on === here && (c.skill_id || c.times_seen >= 3)) || null;
}

export function fire(candidate, now, { tabId = null, visit = "" } = {}) {
  return { id: `n_${now}_${candidate.id}`, at: new Date(now).toISOString(), candidateId: candidate.id, skillId: candidate.skill_id || null,
    title: candidate.title, startsOn: candidate.starts_on, tabId, visit, state: "open" };
}

export function onCall(nudges, { url, method }, now) {
  const host = page(url).split("/")[0];
  const mutating = /^(POST|PUT|PATCH|DELETE)$/i.test(method || "");
  return nudges.map((n) => n.state === "open" && mutating && n.startsOn.startsWith(host) ? { ...n, state: "by-hand", endedAt: now } : n);
}

export function sweep(nudges, { url, now }) {
  const here = page(url);
  return nudges.map((n) => {
    if (n.state !== "open") return n;
    const old = now - Date.parse(n.at) >= LIFETIME_MS;
    const left = here !== n.startsOn;
    return old || left ? { ...n, state: "expired", endedAt: now } : n;
  });
}

export function mute(muted, startsOn, now) {
  const midnight = new Date(now); midnight.setHours(24, 0, 0, 0);
  return { ...muted, [startsOn]: midnight.getTime() };
}
// ponytail: "three mutes in a week mutes until un-muted in the console" needs a
// place in the console to un-mute; add when that page exists.
```

`service-worker.js`: in `chrome.webNavigation.onCommitted` (`:70`), for a watched top-frame tab, `sweep` then `shouldFire` with `await api.candidates(host)` (cached per host for five minutes in memory); on fire, `state.setNudges([...])`, `showNudge(tabId, "AI-SRO · do this one?")` if the panel is not open (`chrome.sidePanel` has no "is open" — track `panel-open`/`panel-closed` messages sent by `panel.js` on load and `pagehide`); in the `"request"` case call `onCall`; a 15-second alarm calls `sweep` for every open nudge and `hideNudge` on the ones that ended. `"nudge-answer"` with `{ id, answer }`: `"do"` runs the candidate's skill through the existing `run-skill`/`teach-candidate` path (a candidate without a skill is taught first, exactly as `beginOffer` does today) and marks the nudge `answered`; `"not-here"` marks `answered` and `state.setMuted(mute(...))`. `showing.js`: `showNudge`/`hideNudge` paint a 28 px pill at `top:12px;right:12px` in the same shadow-root idiom as `paint()`, whose click sends `{ kind: "open-panel" }` (`chrome.sidePanel.open({ tabId })`).

- [ ] **Step 3: Browser test** — `backend/tests/browser/test_a_page_the_task_starts_on.py`, in the idiom of `test_a_mail_the_browser_recognises.py`: seed a candidate with `starts_on` for the stub host, navigate a watched tab to that path, assert the pill element `#sro-nudge` exists in the page, navigate to another path, assert it is gone.

- [ ] **Step 4: Makefile, run everything, commit**

```bash
make test-extension && make lint-extension && cd backend && uv run pytest tests/browser -q -k starts_on
git add new-chrome-extension/src/panel/nudge.js new-chrome-extension/src/panel/nudge.test.mjs new-chrome-extension/src/background/state.js new-chrome-extension/src/background/service-worker.js new-chrome-extension/src/background/showing.js backend/tests/browser/test_a_page_the_task_starts_on.py Makefile
git commit -m "feat(panel): a nudge on the page a task starts on, and the three ways it ends"
```

### Task A7 — The panel itself: four bands, one composer, `panel.js` under 500 lines

**Files:**
- Modify: `new-chrome-extension/src/panel/panel.html`, `panel.css` (rewrite), `panel.js` (shrink)
- Modify: `new-chrome-extension/src/panel/panel.test.mjs` (harness concatenates `ledger.js`, `strip.js`, `today.js`, `run-card.js` ahead of `panel.js`, as it did `transcript.js`)
- Modify: `docs/14-extension-protocol.md` (the panel section), `docs/design/panel/` (screenshots)

**Interfaces:**
- Consumes: everything above.
- Produces: the panel.

- [ ] **Step 1: `panel.html`**

```html
<body>
  <div id="strip"></div>
  <div id="expanded" hidden></div>
  <div id="today"></div>
  <div id="scroll"><main id="ledger"></main></div>
  <section id="ask-bar"></section>
  <script type="module" src="panel.js"></script>
</body>
```

The `#here` section, the `#console` iframe section and the `<footer>` are removed. "Console ↗" opens a tab, as `openConsole()` does today. Delete `frameTheConsole()`, `refused()`, `here()`, `row()`, `suggestion()`, `card()` and everything only they called, from `panel.js`.

- [ ] **Step 2: `panel.js` wiring** — `refresh()` becomes:

```js
async function refresh() {
  const status = await ask({ kind: "status" });
  const here = await beside();
  $("strip").replaceChildren(strip(status, here, { onMenu: menu, onToggle: () => { expanded = !expanded; refresh(); } }));
  const why = needsAPress(status, here);
  $("expanded").hidden = !(why || expanded);
  if (!$("expanded").hidden) $("expanded").replaceChildren(why === "not-connected" ? notConnected() : watching(status));
  if (!status.deviceId) { $("today").replaceChildren(); $("ledger").replaceChildren(); return; }
  const [thread, summary] = await Promise.all([ask({ kind: "thread" }), ask({ kind: "summary", since: midnight() })]);
  const runs = await runsIn(thread, status);           // Map run_id -> {run, skill}, fetched for `run` messages not finished
  const line = today(summary, openOffers(thread));
  $("today").replaceChildren(...(line ? [line] : []));
  const local = { offers: status.offers || [], nudges: (status.nudges || []).filter((n) => n.tabId === here.tabId || n.state !== "open") };
  $("ledger").replaceChildren(ledger(thread, local, { onPress: pressed, onChange: changed, runs }));
  if (!$("ask-bar").childElementCount) $("ask-bar").append(composer(say, { placeholder: status.performing ? "Say something to this run" : "Ask for a task, or describe it" }));
}
```

`pressed(answer, entry, where, button, values)` is one switch: `do`/`no` → today's `beginOffer`/dismiss; `run` → `watch-fire` with values; `not-here` → `nudge-answer`; `undo`/`wrong` → today's `undoRun`/`wasWrong`; `retry`/`ask`/`open` → `run-retry` (existing escalation via `run-skill` with `from: run.id`), a `question` composed into the thread, `chrome.tabs.create({ url })`; `pause`/`stop` → `abort-run`; `choice:<v>` → `thread-say` with the run's id. `menu(action)` maps to `set-paused`, `purge`, `unwatch-tab` plus policy exclusion, `chrome.runtime.openOptionsPage()`, `sign-out`. `say(text)` posts with `run_id` when a run is live. Keep `poll` at its current cadence; it calls `refresh()`.

- [ ] **Step 3: `panel.css`** — rewrite to §10: `:root` sets `--t-11/--t-12/--t-14/--t-17`, `--s-1..--s-5` (4/8/12/16/24), `--r-field: 6px; --r-card: 10px`. The ledger is `display:grid; grid-template-columns: 44px 1fr; column-gap: 12px` per `li.message`; `time` in mono at 11px, muted; the rail is a `::before` 1px line in `--brand-line` on the `ul`. `.message[data-kind="nudge"]` gets `border-left: 2px solid var(--brand-accent)` and, in its last fifteen seconds (`data-fading`), a `transition: border-color 15s linear` to transparent. `.run .glyph` transitions `color 180ms`. `@media (prefers-reduced-motion: reduce)` zeroes both. `.chip[data-open="true"]` shows the chevron rotated. Focus ring `outline: 2px solid var(--brand-accent); outline-offset: 2px` on every `button, input`. No hex literal anywhere; `grep -n '#[0-9a-f]\{3,6\}' panel.css` must return nothing.

- [ ] **Step 4: Sizes and states by eye** — `make dev-browser`, load the extension, open the panel at 360 and 420 px, and walk the brief's nine states plus the four new ones (live run with a question, mail match with an empty field, nudge in its last fifteen seconds, failed run with "Try another way"). Screenshot each into `docs/design/panel/<state>.png`.

- [ ] **Step 5: `panel.js` line count, tests, docs, commit**

```bash
wc -l new-chrome-extension/src/panel/panel.js   # must print < 500
make test-extension && make lint-extension && cd backend && uv run pytest tests/browser -q
git add new-chrome-extension/src/panel docs/14-extension-protocol.md docs/design/panel
git commit -m "feat(panel): four bands, one composer, and a ledger of the day"
```

---

## Verification of the whole

1. `make check` green.
2. Live, against Blue Yonder with the extension watching: create a work area three times, then land on the create page a fourth time. The nudge appears, the pill appears with the panel closed, both are gone after ninety seconds of doing nothing. Land again, do the task by hand: the nudge collapses to "did it by hand" at the POST.
3. Live, with a watched Gmail tab and a watch on "Create a supplier": send yourself a mail; the `mail_match` entry appears with fields; leave one empty; fill it; press "Run it"; the run card appears under it with step rows; press `change` on an unsent step; the run finishes with a `result` entry and "Undo that".
4. `GET /v1/threads/current` after (3) contains no value from the mail. `grep` the JSON for the supplier name you typed into the mail.
5. Reload the extension mid-run: the run card is still there, drawn from the thread and `GET /runs/{id}`.

## Out of scope

- The console. Next spec.
- "Pause" as a true pause. Until the backend has one, the button says "Stop after this step" and does that.
- The three-mutes-in-a-week rule (needs a console page to un-mute).
- Chains offered as one job (sub-plan 4).
- Posting `question` messages from a paused run. The ledger draws the kind (A1) so the console and panel agree on its shape; the backend writes one when the planner lands (sub-plan 3). Until then a run that needs a value stops before it starts, as today, and the mail-match fields (A5) are where the value is supplied.
