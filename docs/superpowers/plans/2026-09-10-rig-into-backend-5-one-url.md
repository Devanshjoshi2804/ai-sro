# Phase 5 — One URL

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The extension stops being a client of two systems. One base URL, one
socket, one credential — and the three calls that would break silently at the
switchover are fixed before they can.

**Architecture:** Six `api.js` calls move from `state.rigUrl()` to the backend
base and the backend's headers. `mirror.js`, `rig-channel.js` and the rig
settings are deleted. `channel.js` — the shared implementation both sockets were
built on — stays exactly as it is.

**Tech Stack:** Plain ES modules, no build step, no dependencies. eslint with
`no-undef`. 27 node suites run by `make test-extension`.

**Spec:** `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`,
*The extension* (`:215-224`) and phase 5 (`:287`).

**Base:** `main` at `fd89531` (the phase 4b merge).

---

## What the spec gets wrong about this phase, measured before planning

**Three of its claims are false and one is already done.** Corrected here so no
task inherits them.

1. **"The ten node suites."** There are **27**, and `make test-extension` runs
   all 27. All green at `fd89531`, eslint clean.
2. **"They speak to `/v1/shapes`, `/v1/offers`, `/v1/runs`, which the backend now
   hosts at the same paths."** `/v1/runs` means a **skill** run on the backend.
   Workflow runs are at **`/v1/workflow-runs`** — phase 4b moved four routes and
   the spec carries an amendment saying so. Four of the six calls repoint to a
   *different path*, not just a different base.
3. **"`channel.js` … carries the rig's command envelope now, including
   `ui.perform_at` and `screenshot`."** **Already true.** `UiDriver.perform_at`
   is at `ports/ui.py:69`, `vision_step.py:168` and `pursue_goal.py:294` call it,
   and `commands.js:414`/`:574` already handle both kinds. **No task needed.**
4. **"The browser's token is the device secret the backend already mints."**
   True, and it is the whole mechanism of Task 2 — but `rigHeaders()` sends the
   rig's bearer and *none* of the backend's headers, which is why three calls
   break.

## The three calls that break, and why one is worse than the other two

One defect wearing three faces: **`rigHeaders()` (`api.js:84-89`) sends the rig's
bearer and none of the backend's headers**, and `X-Device-Secret` is one.

| Call | Pointed at the backend | How loud |
|---|---|---|
| `shapes()` `api.js:255` | 404 from the half-pair rule → returns `[]` | silent, degrades |
| `reportOffer()` `api.js:275` | 403 | **visible** since `f7c00ca` returns whether the fate landed |
| `rigApprove()` `api.js:329` | **200, NULL approver, 403 check skipped** | **silent, and worst** |

**`rigApprove` is the one to fix first.** It sends neither `?device_id=` nor the
secret, so `asking_device` resolves **no browser at all** — which is not a
refusal. The route then records `approved_by = None` **and skips the
driving-browser check entirely**, because that check only binds a caller who
names a browser. A live warehouse write, authorised by nobody, on the door whose
whole purpose is recording who authorised it.

`api.js:254` is **not** a precedent to copy — it uses the same secret-less
`rigHeaders()`.

---

## Global Constraints

### The extension's own rules

- **No build step and no dependencies.** Plain ES modules. Do not introduce a
  bundler, a framework, or a package.
- **eslint with `no-undef`** is the only static check the extension has —
  `make lint-extension`. There is no type checker here.
- **`make test-extension` runs 27 node suites.** All 27 pass at `fd89531`.
  **Report the number you observe**, and note that `grep -c "fail"` over that
  output returns 14 on a fully green run, because `fail 0` and test names
  contain the word. Match `fail [1-9]` or read the summary lines.

### What must not change

- **`channel.js` stays.** Both sockets were built on `createChannel`; deleting
  `rig-channel.js` removes a *caller*, not the implementation.
- **`recognise.js`, `offering.js`, `nudge.js`, the run card, the approve flow and
  the five fates are unchanged** (spec `:220-222`). If a task finds itself
  editing those, it has gone wrong — say so rather than proceeding.
- **Never delete, move, rename or stage any untracked file.**
  `backend/.gmail-token.json.old-client` and `backend/old-client_secret_*.disabled`
  are the user's credentials; an agent on this project destroyed one before.

### The test rules this project has paid for

1. **Guard the caller, not only the rule.** Every task of phase 4b shipped a test
   that proved a rule and left the traffic unpinned — response fields
   replaceable with literals, a route that could pass `utterance=""` past 45
   tests, a route that could spawn **any coroutine at all** past 32. **Every
   value a call sends must have a test that dies when it is replaced by a
   constant.**
2. **A refusal test that makes no successful request proves nothing.** Seventeen
   backend tests passed with every route deleted. The extension's equivalent: a
   test asserting a call fails must also assert one that succeeds.
3. **Never date a fixture "today."**
4. **Where a comment records a decision that cost something, a test must fail
   when that decision stops being true.**

### Git

- **Stage only files you edited, by name.** Never `git add -A`, `.`, or `-u`.
- **`git stash` forbidden. No git config writes. Ordinary index — do NOT set
  `GIT_INDEX_FILE`.**
- **Prefer absolute paths over `cd`.**
- Identity per commit: `Devansh Joshi <devansh.j@GGN002963.local>`.
- Every commit ends with the `Co-Authored-By` and `Claude-Session` trailers.
- Subjects are sentences about what changed and why it mattered, lowercase after
  the type prefix, no trailing period.

---

## File Structure

| File | Change |
|---|---|
| `src/background/api.js` | six calls repointed; `rigHeaders` deleted |
| `src/background/state.js` | `rigUrl`/`rigToken` keys and four accessors deleted |
| `src/background/mirror.js` | **deleted** |
| `src/background/rig-channel.js` | **deleted** |
| `src/background/service-worker.js` | mirror and rig-channel wiring, the `"rig"` message case |
| `src/options/options.{html,js,css}` | the two rig fields |
| `src/panel/panel.js` | the `status.rigUrl` link (`:569-571`) |
| `src/background/mirror.test.mjs`, `rig-settings.test.mjs` | **deleted with their subjects** |
| `channel.test.mjs`, `finishing.test.mjs`, `offering-worker.test.mjs`, `panel.test.mjs` | rig references removed |

---

## Task 1: `rigApprove` — the silent one

**Files:** Modify `src/background/api.js`; `src/background/offering-worker.test.mjs`.

The only call whose breakage is invisible. Fix it first so that if this plan
stalls, the dangerous one is already closed.

- [ ] **Step 1: Write the failing test.** A fake `fetch` asserting the request
      carries **both** `X-Device-Secret` and `?device_id=`, and that a response
      with no browser resolved is treated as a failure rather than a success.
- [ ] **Step 2: Run it. Expect failure** — today it sends neither.
- [ ] **Step 3:** Repoint to the backend base, use the same header builder
      `call()` uses, add `?device_id=`, and check the status.
- [ ] **Step 4:** Run the test. **Then delete the `?device_id=` and confirm the
      test dies.** A test that passes with the parameter missing is the defect.
- [ ] **Step 5:** `make test-extension` and `make lint-extension`. Commit.

## Task 2: the other five calls, and `rigHeaders` goes

**Files:** `src/background/api.js`; `finishing.test.mjs`, `offering-worker.test.mjs`.

`rigRun`, `rigAbort`, `rigStart`, `shapes`, `reportOffer`.

**Four of them change path, not just base** — `/v1/runs*` → `/v1/workflow-runs*`.
Read the phase 4b amendment in the spec before writing.

- [ ] **Step 1:** For each call, a test pinning **path, method, headers and every
      body field**, each dying when the value is replaced by a constant.
- [ ] **Step 2:** Run them. Expect five failures.
- [ ] **Step 3:** Repoint all five. **Delete `rigHeaders()`** — with `rigApprove`
      done in Task 1 it has no callers.
- [ ] **Step 4:** Green. Then mutate each path to the old `/v1/runs` form and
      confirm each dies.
- [ ] **Step 5:** Gates. Commit.

> `rigRun` maps the rig's `outcome` to the panel's `status` and `{order, says,
> verdict}` to `{index, outcome}` (`api.js:196-210`). **The backend answers its
> own field names.** Decide whether the mapping layer goes or stays, and write
> the reason down — do not delete it silently.

## Task 3: the mirror

**Files:** Delete `src/background/mirror.js`, `mirror.test.mjs`; modify
`service-worker.js`, `upload.js` if it references `mirrorSafely`.

The mirror posts a copy of every upload to the rig — *"a second reader, not a
second source of truth"*. With one URL there is no second reader.

- [ ] **Step 1:** Grep every reference — `mirror`, `isMirrorable`,
      `mirrorSafely`, `MIRROR_TIMEOUT_MS`. List them before deleting anything.
- [ ] **Step 2:** Delete the module and its suite.
- [ ] **Step 3:** Remove each call site. **`upload.js` drops queued rows on a
      permanent 4xx from the backend and the mirror was deliberately unable to
      reach that decision** — confirm removing it cannot change which rows drop.
- [ ] **Step 4:** Gates. Commit.

## Task 4: the second socket and the rig settings

**Files:** Delete `rig-channel.js`, `rig-settings.test.mjs`; modify
`service-worker.js`, `state.js`, `options.{html,js,css}`, `panel.js`,
`channel.test.mjs`, `panel.test.mjs`.

- [ ] **Step 1:** Delete `rig-channel.js` and its dial from `service-worker.js`.
      **`channel.js` and `createChannel` stay** — this removes a caller.
- [ ] **Step 2:** Delete `rigUrl`/`rigToken` from `state.js` (2 keys, 4
      accessors) and the `"rig"` case from the message dispatcher.
- [ ] **Step 3:** Remove the two fields from the options page and the
      `status.rigUrl` link at `panel.js:569-571`.
- [ ] **Step 4:** `rig-settings.test.mjs` has **9 tests** about a blank token
      meaning "leave it alone". **Delete it with its subject** — do not leave a
      suite testing a deleted feature.
- [ ] **Step 5:** Gates. Grep for `rig` across `src/` and account for every
      remaining hit in the report. Commit.

## Task 5: the accounting

**Files:** this plan; the spec.

- [ ] Amend the spec's phase-5 line: **27 suites, not ten**; the envelope item
      was already satisfied; `/v1/runs` is not the same path.
- [ ] Grep `src/` for `rig`, `mirror`, `rigUrl`, `rigToken` and record what is
      left and why.
- [ ] Write what phase 6 and 7 inherit.

## Task 6: the live proof — **this one is the user's, not an agent's**

The spec's real acceptance: *"a browser signed in once registers, uploads, is
served shapes, is offered, runs, approves."*

**No agent can do this.** It needs a signed-in Chrome and a real WMS. The
deliverable here is a **scripted walkthrough** the user runs, with the exact
checks at each step and the SQL that proves it.

- [ ] Write `docs/new-agent-doc-arc/phase-5-walkthrough.md`: load the unpacked
      extension, paste one token, sign in to the WMS, demonstrate a job, watch
      the offer, press yes, approve the write.
- [ ] For each step, the query that proves it. **These four tables are empty
      today and are the whole point:** `workflow_runs`, `approvals`, `offers`,
      `chats`.
- [ ] State plainly that phase 5 is **not complete** until they hold rows.

---

## Self-Review

**Spec coverage.** *"One base URL"* → Tasks 1, 2, 4. *"`state.rigUrl`,
`state.rigToken`, `mirror.js`, the `rig-channel.js` dial and the rig-settings
page go"* → Tasks 3, 4. *"channel.js carries the envelope"* → **already done**,
recorded in Task 5 rather than given a task. Acceptance → Task 6.

**Ordering.** Task 1 before Task 2 so the silent defect closes first even if the
plan stalls. Task 3 before Task 4 because `rig-channel.js` imports
`isMirrorable` from `mirror.js` — deleting the mirror first makes that
dependency loud instead of leaving a dangling import.

**What this plan does not do.** It does not touch `recognise.js`, `offering.js`,
`nudge.js`, the run card, the approve flow or the five fates — the spec says
unchanged and phase 4b gave no reason to doubt it. It does not redesign the
panel; the trend research at `docs/new-agent-doc-arc/panel-trend-research.md` is
input to a later decision, not to this one.

**The risk I cannot close from here.** Every task's acceptance is the 27 node
suites, which use fake `fetch`. **They cannot prove the backend accepts what the
extension now sends** — the same gap that let two backend routes ship dead
against real Postgres with 2299 tests green. Task 6 is the only thing that
closes it, and it is the one task an agent cannot run.
