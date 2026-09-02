# The panel is a conversation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The panel becomes one continuous conversation — the watching state collapses to a line, offers arrive as messages, and the operator answers in the same place.

**Architecture:** The panel becomes a client of the chat system the console already uses. `Thread`, `Message`, `Speaker.SYSTEM` and `Message.decision` exist and mean what this needs; nothing new is invented in the domain. Four of the five tasks are wiring and rendering; one adds a write from mining into chat.

**Tech Stack:** Python 3.14 / FastAPI backend, plain-DOM Chrome MV3 panel (`createElement`, never `innerHTML`), pytest, node `--test`, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-09-02-the-panel-is-a-conversation-design.md`

## Global Constraints

- **A message is a thing said; the press is the authorisation.** Nothing may run because a message says so. This separation is what an assisted run records as the operator's consent, and no task here weakens it.
- **The operator must always be able to tell whether this tab is evidence.** The collapsed row still says it in one line. There is an existing browser test asserting this and it must keep passing.
- **No `innerHTML` anywhere in the panel.** It builds DOM with `createElement`; message text is operator- and model-supplied and goes in via `textContent`. This is a security boundary, not a style preference.
- **No migration.** `offered_at` is a defaulted field on a candidate document, the same precedent as `skill_id`.
- **Task 5 conflicts with other work in flight.** `backend/src/sro/application/observation/propose.py` is being edited by the `work-that-spans-tabs` branch. Task 5 must not start until that branch's Task 4 is merged, or it must be rebased onto it. Every other task here is clear of it.
- Never `git add -A`; commit the paths each task names, then `git show --stat HEAD`.
- Backend gate: `cd backend && uv run pytest tests/unit -q`, then `make lint` and `make types`. Extension gate: `make test-extension` and `make lint-extension`. Panel behaviour: `make test-browser`.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `backend/src/sro/application/chat/read_threads.py` | Reading threads | gains `current()` |
| `backend/src/sro/interface/http/v1/routers/threads.py` | The chat wire | gains `GET /threads/current` |
| `new-chrome-extension/src/background/api.js` | What the worker calls | gains `currentThread`, `say` |
| `new-chrome-extension/src/background/service-worker.js` | The panel's only route to the backend | gains `thread` and `thread-say` cases |
| `new-chrome-extension/src/panel/transcript.js` | New — rendering a thread | the transcript and composer |
| `new-chrome-extension/src/panel/panel.js` | The panel | the watching row collapses; the console is replaced by the transcript |
| `backend/src/sro/application/observation/propose.py` | What is worth saying to an operator | posts an offer into the thread |
| `backend/src/sro/domain/observation/candidate.py` | What a candidate is | `offered_at` |

---

## Task 1: The operator's continuous thread

**Files:**
- Modify: `backend/src/sro/application/chat/read_threads.py`, `backend/src/sro/interface/http/v1/routers/threads.py`
- Test: `backend/tests/unit/application/test_the_panel_is_a_conversation.py` (create)

**Interfaces:**
- Produces: `ReadThreads.current(ctx) -> Thread` — the newest thread this operator opened, or a new one; `GET /v1/threads/current -> ThreadDetail`

- [ ] **Step 1: Write the failing test**

```python
async def test_the_current_thread_is_this_operator_s_most_recent() -> None:
    """One continuous conversation, not one per tab and not one per host: a job
    that spans a mailbox and the warehouse system belongs in one place."""
    ...  # build two threads for this principal and one for another
    found = await ReadThreads(uow).current(ctx)

    assert found.id == newest_of_this_principal.id


async def test_an_operator_with_no_thread_gets_one() -> None:
    found = await ReadThreads(uow).current(ctx)

    assert found.opened_by == ctx.principal_id


async def test_another_operator_s_thread_is_never_returned() -> None:
    ...  # only a thread opened by a different principal exists
    found = await ReadThreads(uow).current(ctx)

    assert found.opened_by == ctx.principal_id
    assert found.id != the_other_operator_s.id
```

**Read the existing chat tests first** and build threads the way they do — `backend/tests/factories.py` and the fakes under `backend/tests/` almost certainly have a thread builder and a fake uow. Reuse them; do not add a second way to build a `Thread`.

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && uv run pytest tests/unit/application/test_the_panel_is_a_conversation.py -q`
Expected: FAIL — `ReadThreads` has no `current`.

- [ ] **Step 3: Implement**

```python
    async def current(self, ctx: RequestContext) -> Thread:
        """This operator's running conversation, started if there is none.

        One continuous thread rather than one per host: a job that spans a
        mailbox and the warehouse system is one piece of work, and splitting the
        conversation by tab is the same mistake as splitting the work by tab.

        Filtered here rather than in the repository because `list_for_tenant` is
        what exists and a tenant's threads are few. When they are not, this
        wants its own query -- and the shape of that query is exactly this
        filter, so nothing is lost by waiting for the pressure.
        """
        async with self._uow as uow:
            threads = await uow.threads.list_for_tenant(ctx.tenant_id, limit=50)
        mine = [thread for thread in threads if thread.opened_by == ctx.principal_id]
        return max(mine, key=lambda thread: thread.opened_at) if mine else ...
```

Starting a thread is `StartThread` (`container.start_thread()`); `current` should not duplicate how a thread is made. Whether `current` calls it, or the ROUTER falls back to it when `current` finds none, is the implementer's call — pick the one that keeps `ReadThreads` a reader.

- [ ] **Step 4: The endpoint**

```python
@router.get("/current")
async def current_thread(container: ContainerDep, ctx: ContextDep) -> ThreadDetail:
    """The conversation this operator is in, made if they are not in one yet.

    The panel needs "the thread", not a list to guess from.
    """
```

**Declare it before `@router.get("/{thread_id}")`** or `current` is parsed as a thread id. Add a test that `GET /threads/current` does not 404 as a missing thread.

- [ ] **Step 5: Run the tests, then the gate**

Run: `cd backend && uv run pytest tests/unit -q`, then `make lint`, `make types`, and `make test-contract` — the wire changed, and the contract test is what proves the schema is still coherent.

- [ ] **Step 6: Prove the rules**

Two reverts: drop the `opened_by` filter and confirm the other-operator test fails; move the route below `/{thread_id}` and confirm the routing test fails.

- [ ] **Step 7: Commit**

```bash
git add backend/src/sro/application/chat/read_threads.py backend/src/sro/interface/http/v1/routers/threads.py backend/tests/unit/application/test_the_panel_is_a_conversation.py
git commit -m "feat(chat): the conversation this operator is in"
```

---

## Task 2: The worker can fetch and post

**Files:**
- Modify: `new-chrome-extension/src/background/api.js`, `new-chrome-extension/src/background/service-worker.js`

**Interfaces:**
- Consumes: `GET /v1/threads/current`, `POST /v1/threads/{id}/messages` from Task 1
- Produces: worker message kinds `thread` and `thread-say`

- [ ] **Step 1: Add the api methods**

Beside the existing ones in `api.js`, following their exact shape:

```javascript
  currentThread: () => call("/v1/threads/current"),
  say: (threadId, text) =>
    call(`/v1/threads/${encodeURIComponent(threadId)}/messages`, {
      method: "POST",
      body: { text },
    }),
```

Read `api.js` first: `call`'s signature, how a body is passed, and how other methods encode ids. Match them.

- [ ] **Step 2: Add the worker cases**

Beside `case "candidates"` and `case "resolve-intent"`, which are the closest analogues:

```javascript
    case "thread":
      return api.currentThread();
    case "thread-say":
      return api.say(message.threadId, message.text);
```

- [ ] **Step 3: Verify**

Run: `make lint-extension` and `make test-extension`. The worker has no unit test for passthrough cases; the browser test in Task 3 is what exercises these.

- [ ] **Step 4: Commit**

```bash
git add new-chrome-extension/src/background/api.js new-chrome-extension/src/background/service-worker.js
git commit -m "feat(extension): the panel can reach the conversation"
```

---

## Task 3: The transcript and the composer

**Files:**
- Create: `new-chrome-extension/src/panel/transcript.js`
- Modify: `new-chrome-extension/src/panel/panel.js`, `new-chrome-extension/src/panel/panel.css`
- Test: `new-chrome-extension/src/panel/transcript.test.mjs` (create), added to `test-extension` in the Makefile

**Interfaces:**
- Consumes: `ask({kind: "thread"})` and `ask({kind: "thread-say", threadId, text})` from Task 2
- Produces: `transcript(thread, {onSay, onPress})` returning a DOM node

- [ ] **Step 1: Write the failing test**

`transcript.js` must be a pure function of a thread to DOM so it can be tested in plain node, the way `showing.test.mjs` and `frames.test.mjs` are. Test with a minimal DOM stub or `linkedom` if the repo already uses one — **check `panel.test.mjs` for how it fakes the DOM and follow it.**

```javascript
test("each speaker renders as its own kind of thing", () => {
  const node = transcript({messages: [
    {id: "m1", speaker: "operator", text: "create a supplier", said_at: WHEN},
    {id: "m2", speaker: "assistant", text: "which client?", said_at: WHEN},
    {id: "m3", speaker: "system", text: "You've done this 3 times.", said_at: WHEN,
     decision: {kind: "offer", candidate_id: "cnd_1", times: 3}},
  ]}, {});
  // three messages, and only the system one carries buttons
});

test("an offer renders the two answers", () => { ... });

test("a decision this panel does not know renders its words and no buttons", () => {
  // forward compatibility: a newer backend must not blank the panel
});

test("message text is never parsed as markup", () => {
  const node = transcript({messages: [
    {id: "m1", speaker: "operator", text: "<img src=x onerror=alert(1)>", said_at: WHEN},
  ]}, {});
  assert.equal(node.querySelectorAll("img").length, 0);
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `node new-chrome-extension/src/panel/transcript.test.mjs`

- [ ] **Step 3: Implement `transcript.js`**

A function, not a class. Three speakers, three shapes. `textContent` for every piece of text. `decision.kind === "offer"` renders the two buttons the panel shows today; any other `kind` renders the prose and no buttons.

- [ ] **Step 4: Wire it into the panel**

`render(status)` gains the transcript below the watching row. The composer posts through `ask({kind: "thread-say"})` and re-renders from the thread that comes back, rather than appending locally.

The existing console (`openConsole`, and the "Ask for a task" affordance) is replaced by this. Its suggestion list becomes the composer's placeholder.

- [ ] **Step 5: Add the test to the Makefile**

```
	node new-chrome-extension/src/panel/transcript.test.mjs
```

- [ ] **Step 6: Verify**

Run: `make test-extension`, `make lint-extension`, and `make test-browser` — the panel's existing browser tests must still pass, especially the one asserting the operator can tell whether the tab is being recorded.

- [ ] **Step 7: Commit**

```bash
git add new-chrome-extension/src/panel/ Makefile
git commit -m "feat(panel): the panel is a conversation"
```

---

## Task 4: The watching card collapses

**Files:**
- Modify: `new-chrome-extension/src/panel/panel.js`, `new-chrome-extension/src/panel/panel.css`

- [ ] **Step 1: Write the failing test**

In `panel.test.mjs`, following how it already tests rendering:

```javascript
test("a steady watching state is one line", () => {
  // watching, nothing to answer -> collapsed: the host and the state, no buttons
});

test("a state with something to press expands itself", () => {
  // excluded host, expired grant, calls-not-recordable -> expanded, buttons visible
});

test("the collapsed row still says whether this tab is evidence", () => {
  // the words matter: an operator who cannot tell is the failure this guards
});
```

- [ ] **Step 2: Implement**

`watching(status)` gains a collapsed form: the dot, the host, and the state in one line, with a chevron that expands to today's card. The rule is that the row expands itself when there is an action to take and stays a line when there is not — not a remembered preference, because the reason to expand is about the state, not about what the operator last did.

- [ ] **Step 3: Verify**

Run: `make test-extension`, `make lint-extension`, `make test-browser`.

- [ ] **Step 4: Prove the rule**

Force the collapsed form for a state that needs an answer and confirm the expanding test fails.

- [ ] **Step 5: Commit**

```bash
git add new-chrome-extension/src/panel/
git commit -m "feat(panel): the watching state is a line until it needs an answer"
```

---

## Task 5: An offer is written into the thread

**BLOCKED until `work-that-spans-tabs` Task 4 is merged** — that branch is editing `propose.py`. Rebase onto it before starting.

**Files:**
- Modify: `backend/src/sro/domain/observation/candidate.py`, `backend/src/sro/application/observation/propose.py`
- Test: `backend/tests/unit/application/test_the_panel_is_a_conversation.py`

- [ ] **Step 1: Write the failing test**

```python
async def test_a_task_worth_offering_is_said_out_loud_once() -> None:
    """The offer is a message in the conversation, so it survives the panel
    closing and the console sees the same exchange."""
    # a candidate at WORTH_OFFERING, proposed twice
    assert len(offers_in(thread)) == 1


async def test_a_candidate_not_yet_worth_offering_says_nothing() -> None: ...


async def test_a_dismissed_candidate_is_not_offered() -> None: ...


def test_the_offer_carries_what_the_buttons_need() -> None:
    """The prose is for the operator; the decision is for the panel."""
    assert offer.decision["kind"] == "offer"
    assert offer.decision["candidate_id"] == candidate.id.value
```

- [ ] **Step 2: Implement `offered_at`**

On `TaskCandidate`, defaulted `None`, with a docstring saying it exists so a conversation does not repeat itself.

- [ ] **Step 3: Implement the posting**

In `ProposeAboutCandidates` — already the use case that decides what is worth saying to an operator. A `Speaker.SYSTEM` message, text as the panel words it today, `decision` carrying `kind`, `candidate_id`, `times`, `seconds_each`, `host`. Set `offered_at` in the same transaction that posts.

- [ ] **Step 4: Verify**

Run: `cd backend && uv run pytest tests/unit -q`, `make lint`, `make types`.

- [ ] **Step 5: Prove the rules**

Drop the `offered_at` check and confirm the once-only test fails; drop the `WORTH_OFFERING` check and confirm the not-yet test fails.

- [ ] **Step 6: Commit**

```bash
git add backend/src/sro/domain/observation/candidate.py backend/src/sro/application/observation/propose.py backend/tests/unit/application/test_the_panel_is_a_conversation.py
git commit -m "feat(observation): a task worth offering is said out loud, once"
```

---

## Verification by hand

Afterwards, with the extension loaded and the API running:

1. Open the panel on a watched tab. The watching state is one line.
2. Do a task three times. An offer appears **as a message**, not a card.
3. Close and reopen the panel. The offer is still there — that is the whole point of it being a message.
4. Open the console's Threads view. The same exchange is in it.
5. Press "Do the next one". The run starts, and the press — not the message — is what the run records as its authorisation.
