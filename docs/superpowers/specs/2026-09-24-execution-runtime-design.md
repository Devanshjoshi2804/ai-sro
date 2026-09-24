# Execution runtime on Steel — design

Date: 2026-09-24. Status: approved in conversation, section by section.
Parent spec: `2026-09-23-vm-execution-recipes-and-agents.md` (decisions D1–D9 bind this design).

This is the first of three designs the parent spec decomposes into:

1. **Execution runtime** — this document. Runs execute on our VM, never in the operator's Chrome.
2. Learning and agents — prompts, eval harness, recipe compilation, repair. Separate design.
3. Operator surface — panel P1–P5. Separate design.

Designs 2 and 3 plug into the interfaces defined here.

## 1. Goal and acceptance

Any job the miner learned from the extension's monitored capture runs end to end on
a Steel browser on our VM. The operator sees only the result, and is asked only when
a person is genuinely needed (D4). Nothing in the runtime is specific to one job,
system or identity provider.

The runtime covers three ways a run begins: a press, trigger or mail starts a job
from its first step; the server reads each operator's mailbox itself (§2, "Mail
poll"); and a job the operator started by hand in their own tab is finished on Steel
from where they stopped (mid-job takeover, §7.6). Lookups, the questions answered by
reading a system (`/v1/ask`, `/v1/lookups`, chat), read through Steel too, never through
the operator's browser (§6.5).

The POC is accepted when all of these hold, and each is proven by a live QA run (§8):

- a mined Blue Yonder job runs on Steel, signed in from the vault;
- a job that arrives by mail replies by mail through the Gmail MCP connector, with no UI;
- two jobs run in parallel on one account as tabs of one browser;
- a run recovers when its session expires mid-job, and a worker restart repeats no write;
- a job the operator started by hand finishes on Steel from where they stopped, and no
  write they already made is sent again;
- a request mail is read and its run started by the server, with the extension closed;
- a lookup answers with the operator's Chrome closed.

Scale: one tenant, a few operator accounts (2–5), each with its own browser. Deployed
with one account first.

## 2. Architecture

```
 mail poll (worker) / panel / trigger / takeover (§7.6)
          │  start_run(job, values, account[, from step k, carried values])
          ▼
  Temporal RunWorkflow (one per run; progress on the run row)
          │  for each step of the compiled recipe
          ▼
     StepExecutor ── walks the ladder, first trusted lane first
       1 tool lane  ─► MCP client                         no browser
       2 API lane   ─► ServerCaller (httpx)               cookies + CSRF from the broker
       3 UI lane    ─► SteelDriver (Playwright over CDP)  shared page code + snapshot repair
       4 sight lane ─► Gemini computer use on a Steel screenshot
       then ask the operator
                                 │
                   SessionBroker (one lease per account, in Postgres)
                                 │  restore saved state, else sign in from the vault
                                 ▼
               Steel containers per tenant ── a browser context per account; runs are tabs
```

The worker process runs every activity and the mail poll. The API process only
starts, stops and answers runs; no run lives in it. A lookup is not a run: it reads
through Steel inside the request that asked (§6.5).

**Mail poll.** Today a mailbox is read only when the extension's heartbeat calls the
mail door (`POST /v1/chat/from-the-mail`, from `lookInTheMail` in
`service-worker.js`). The server reads it itself instead:

- **Where.** A loop in the worker beside the session keeper, the rig miner and the
  retention sweep (`infrastructure/temporal/worker.py`). That is the repository's
  pattern for recurring platform work; Temporal schedules are kept for operators'
  own triggers (`infrastructure/temporal/schedules.py`).
- **Whose mailbox.** For each tenant on Steel (§9), each operator with a registered,
  unrevoked browser. The door runs as that operator, because the Gmail grant and the
  claim on each message are per operator (`connector_key`, `_mail_key`). An operator
  who never connected Gmail answers "not connected" and costs nothing.
- **What it feeds.** The existing door and use case (`FromTheMail`), unchanged in what
  it decides. A sure request carrying every value starts its run through §7.1. A
  request missing values becomes a question in the operator's thread
  (`AskAboutTheOffer`, the `needs_values` decision the panel already draws). A reply
  on a thread a run is waiting on answers that run (§7.4).
- **Once per message.** The door claims each message before reading it
  (`tool_calls.remember`, an insert that does nothing on conflict). Whichever caller
  claims a message first reads it; the other skips it. So the heartbeat look and the
  poll run side by side during rollout without reading any mail twice. The heartbeat
  call is removed in §9 step 3, not before.
- **Metered and capped.** The tenant's cap is checked before any model call. A cap
  refusal, including one raised while starting a run, releases the message's claim,
  so the mail is read again once the cap allows. Every model call runs inside the
  tenant's and operator's attribution (`whose.about`), which the metered client
  requires.

## 3. The ladder

Every step walks the same ladder. The lane a step starts on is the first lane not on
its known-broken list (§6.3), decided per step, per run.

| Lane | When it is tried | Model call | Screenshot |
|---|---|---|---|
| 1. Tool | the step uses a tool (e.g. Gmail) | no | no |
| 2. API | the step has learned requests whose replay was verified before | no | no |
| 3. UI | always available for browser steps | no | no |
| 4. Sight | the UI lane, including snapshot repair, failed | yes | yes |

- **API lane failures.** An authentication failure (401, 403, a refused CSRF token)
  makes the broker refresh the session once (§5.5) and the step is retried once. Any
  other rejection drops the step to the UI lane for this run.
- **After sight fails**, the run asks the operator (D4).
- **Writes are never repeated blindly** on any lane (§6.2).

## 4. Evidence contract (what the capture must record)

The UI lane is only as good as the evidence. Today the recorder captures more than the
backend keeps. These changes are part of this design. They are made in the backend
recorder source and generated with `make gen-recorder`; the extension JS is never
hand-edited.

1. **Keep what is captured.** `correlate.py:as_action` stops dropping `bounds`,
   `attributes` (redacted as today), `component.chain` and `modifiers`. The domain
   `Target` and the stored gesture carry them.
2. **Semantic path, no debugger.** The recorder records the element's labelled
   ancestors: the role and accessible name of each region, dialog, grid and form above
   it, up to the document. This gives a real `within` scope without
   `chrome.debugger`, its banner, or a 4,000-node tree.
3. **Frame identity.** The recorder records the iframe path (the index chain from the
   top document plus each frame's URL). The driver acts in that frame; it no longer
   guesses.
4. **Click `detail` and `isTrusted`.** An Enter-triggered click is recognised
   structurally (`detail == 0`). This replaces the 50 ms `K_ONE_SUBMIT_S` window for
   evidence recorded after this change; the window stays only for older evidence.
5. **After-state.** After each gesture, the recorder records the target's value,
   visibility and enabled state. With the network calls already joined, the runner has
   a recorded expected result to verify against.
6. **Snapshot events stop being discarded at ingest.** The accessibility graph stays
   off by default (the debugger banner). Where a tenant turns it on, the tree taken
   before a gesture is stored with that gesture, so it is not silently counted and
   dropped as today.

## 5. Session broker and Steel pool

### 5.1 Layout

Measured by C0 (local Steel, 2026-09-24): one self-hosted Steel container runs one
Chrome that holds many isolated browser contexts; a context survives a dropped CDP
connection; releasing a Steel session kills the whole browser. So:

- **Steel containers per tenant (N ≥ 1), one browser context per account.** Tenants
  never share a container. Each account is pinned to one container of its tenant
  (recorded on the lease, sticky); a new account goes to the tenant's least-loaded
  container. Scaling adds a container to the tenant's list. The POC runs one.
- **The broker never releases the Steel session.** It closes an account's context
  only, and closing one context must leave its siblings alive (tested).
- A container crash restores every account of that tenant from saved state (§5.5).

QA-0 confirms the same on the QA box; if it answers "sessions", the broker uses Steel's
own session API instead. Nothing above the broker changes either way.

### 5.2 Leases

`browser_sessions` gains the following fields:

- account: tenant, system origin, username;
- `container_url` and `steel_session_id`;
- `holder`: a run id or the keeper;
- `heartbeat_at` and `expires_at`;
- `state`: `signing_in`, `ready`, `expired` or `broken`.

A unique partial index allows one live lease per account. Holders heartbeat. The
sweeper releases only expired leases; the 15-minute grace timer and the in-memory
session list go.

### 5.3 Acquire

1. If a `ready` lease exists for the account, attach to it and open a new tab for this
   run. The run saves the tab's target id in its progress.
2. Otherwise claim the lease, open a session in the account's container, and restore
   the account's saved state (cookies and localStorage) from the vault.
3. Probe: open the system's start page. If it lands on a sign-in page (§5.6), sign in.
4. Sign in by running the recorded sign-in chain with the job's username and the vault
   password. On success, save the state back to the vault.

Vault keys include the username: `{tenant}/{origin}/{username}/password` and
`…/state`. This fixes the collision where two systems behind one identity provider
shared a password key. The state's size is checked against the vault's 64 KiB limit.

### 5.4 Parallel runs (D8)

Runs on one account share one browser, as separate tabs. Anything that changes the
session (restore, sign-in, re-sign-in) takes the per-account lock, a Postgres advisory
lock keyed by account. Ordinary steps never take it. Tool steps take no tab.

### 5.5 Expiry and recovery

- **Detection.** The API lane sees a 401, a 403 or a refused CSRF token, or a UI step
  lands on a sign-in page.
- **Recovery.** The step pauses and the broker re-signs in under the account lock. The
  step is retried once. Other runs on the account wait on the lock, then continue.
- **Credentials refused.** The existing refusal latch trips, and the panel asks the
  operator for the new password once (D9, POC).
- **Container crash.** Its leases expire. The next acquire opens a new session and
  restores the saved state.
- **Worker restart.** Temporal resumes the run, which re-attaches by the lease's
  session id and the saved target ids.

### 5.6 Sign-in detection is structural

`_SIGN_IN_PATHS` and `is_sign_in_page` are already gone (audit wave 1). A page is a
sign-in page by its structure:

- **HTML signals:** a password input, and `autocomplete` values of `current-password`,
  `username` or `one-time-code`;
- **Protocol signals:** an OAuth/OIDC authorize request carrying `response_type`,
  `client_id`, `redirect_uri` and `state`, returning with `code` and `state`.

The chain ends at the submit that leaves the host (Task 10). The landing is
`signs_in_to(...)[1]` (Task 7). The observation policy stops excluding identity
provider hosts, but a sign-in page is captured **structure-only**: the elements acted
on, redacted URLs, page marks, and each request's method, URL and status. No typed
value at all, no screenshot, no accessibility tree, no request or response body. A
page is a sign-in page when it holds a password or one-time-code field, or lies inside
an OAuth/OIDC flow (between the authorize request and the return with `code`). This
applies to the extension and to Steel's own capture. Fixtures, screenshots included,
prove no credential is stored.

### 5.7 Session headers for the API lane

- **Cookies** are taken from the context for the system origin.
- **CSRF and auth headers** are taken from the page's own recent requests, classified
  by name and role. There is no path filter and no fixed sleep; the broker returns as
  soon as one is seen.

## 6. Executors

### 6.1 Lanes

Each lane implements `execute(step, values, ctx) -> StepResult`, where `StepResult`
carries a verdict (§6.2), what was read, and what was learned.

- **Tool lane.** Makes the MCP call with the step's values. The tool's response is the
  verification.
- **API lane.** Replays the learned request (method, path, and a body template filled
  with the run's values) through httpx with the broker's headers.
- **UI lane.** Uses Playwright over CDP in the run's tab. It enters the recorded frame,
  then resolves and acts through the shared page code. It holds one CDP connection per
  session, keyed by session id, and has no fixed waits: it waits on conditions.
- **Sight lane.** `gemini-3.8-flash` with the Computer Use tool.
  - **Inputs:** a Steel screenshot, the step's intent (`says`), the values, and the
    recorded after-state as the goal.
  - **Execution:** actions are carried out by CDP mouse and keys.
  - **Limits:** metered and cap-checked, with a fixed number of actions per step. The
    safety policy blocks acting outside the system's origin.
  - **Escalation:** one escalation to `gemini-3.1-pro-preview` is allowed.

### 6.2 Verification

Every lane returns a verdict: `done`, `read`, `failed` or `unknown`. There is no bare
success.

- **Reads** are `read` once the value was obtained.
- **Writes** are confirmed by one of: the response status plus a read-back; the page's
  own calls matching the recorded ones; or the target's after-state matching the
  evidence (§4.5).
- **A write with no confirmation is `unknown`.** It is never retried blindly. The run
  settles it by a read-back, or asks the operator.

### 6.3 Each lane teaches the one above

- **Sight succeeded.** Hit-test the acted point to find its DOM element, build its
  locator bundle, and save it on the step's recipe. The next run succeeds on the UI
  lane.
- **UI succeeded.** The network calls made during the step are captured. Once a replay
  is verified, the step is promoted to the API lane.
- **A lane failed.** `(step, lane, failure fingerprint)` joins the known-broken list.
  The next run starts at the first lane still trusted.
- **Clearing the list.** A known-broken entry clears when that lane later succeeds for
  the step: repair, or a new doing of the job.

All of this is per step, in data. Nothing is hardcoded per job.

### 6.4 Shared page code

There is one file, `new-chrome-extension/src/page/page-code.js`, a classic script
exposing `globalThis.sroPage`. `in-page.js` is removed after the move.

- **The extension** injects it with `executeScript({files})`.
- **Steel runs** inject it with `add_init_script(path=…)`.
- **The backend image** receives the same file through a BuildKit named context.
  `/health` reports its sha256, and CI compares it with the repository file.

The strategy order, implemented once:

1. component chain;
2. component query;
3. `within` plus role and name;
4. test id;
5. attributes (`name`, `autocomplete`, input type, stable ids);
6. text;
7. xpath;
8. `css_path`.

Several matches are disambiguated by the recorded bounds.

**Snapshot repair.** When every strategy misses, the page code scores live elements
against the recorded evidence: role, name, attributes, component chain, semantic path
and bounds. It acts only when the best score clears a threshold; otherwise the step
drops to sight. The threshold is a named constant, with its reasoning in the code
notes.

### 6.5 Lookups

A lookup answers a question by reading a system. `PlanLookups` chooses where to look;
`RunLookups` reads there. Today it sends `http.send`, `navigate`, `screenshot` and
`tab.open` to the operator's browser through `SocketChannel`. It moves onto the broker
and the lanes, like a run:

- **Account.** The lookup finds the account the way a run does (`account_for` on the
  page the read was seen from), reuses that account's lease, and opens its own tab. The
  tab is closed when the lookup ends, whatever happened. A lookup is not a durable run:
  it lives inside the request that asked, bounded by the caller's deadline.
- **API lane first.** A `call` lookup is the GET this deployment saw answer 2xx
  (`address_for`), replayed through httpx with the session's cookies and headers
  (§5.7). A 401, 403 or refused CSRF token re-signs the account in once (§5.5), and the
  read is tried once more.
- **Then a Steel tab.** A `screen` lookup, or a `call` that failed for any other reason,
  is answered from the Steel tab on the page the read was seen from: the page is put up
  and photographed, as the operator's browser did before. A lookup never clicks, types
  or runs the sight model's actions; it only navigates and looks.
- **Never the operator's browser.** `RunLookups` holds no channel to any device.
- **Only reads.** A lookup can reach nothing that writes. `address_for` addresses only
  GETs that answered 2xx. The API lane sends the literal method `GET`. The tab path uses
  only navigation and a screenshot. So there is no write to verify. A lookup whose
  target was seen only as a write gets no address, and it is refused by name ("nothing
  here has been to …") before anything is sent.
- **Gaps are per system.** A sign-in that needs a person, a full pool or a timeout makes
  that one lookup a named gap. The rest of the plan still answers. A lookup never waits
  on a person.

## 7. Durable runs

### 7.1 Start

`start_run` writes a `workflow_runs` row with an empty `progress` and starts
`RunWorkflow(run_id)`. The server starts runs itself (D3); the extension never
executes. A takeover (§7.6) is the one start whose `progress` is not empty: it holds
the operator's writes and the step the run begins at.

### 7.2 Workflow

The workflow is deterministic and holds only ids.

```
prepare   load the compiled recipe, resolve values, choose the account
acquire   SessionBroker.acquire(account) -> lease id, tab target id
each step execute: StepExecutor.run(step)  (heartbeats; saves progress)
          session expired -> reauth (account lock) -> retry the step once
          write unknown   -> settle by read-back, or ask
finish    verdicts -> outcome; learning updates (§6.3)
release   close the tab, release the lease (always)
```

### 7.3 Progress

`workflow_runs.progress` (JSONB) records:

- the step index;
- the lane used and the verdict, per step;
- the values read;
- the tab target ids;
- the writes made.

Activities are idempotent from it: a write already recorded as done is never sent
again, even when Temporal retries.

### 7.4 Stop, ask, restart

- **Stop.** A stop cancels the workflow. The running step sees it at its next
  heartbeat, finishes its current primitive action, and records itself as stopped.
  `release` still runs. This replaces `pursuits.spawn` and the in-memory `Stops`.
- **Ask.** The workflow waits on the signal `answer(question_id, value)`, which the
  panel or a mail reply sends. The lease and tab are released while it waits and taken
  again after the answer arrives, so a waiting run holds nothing.
- **Restart.** Worker restarts resume as in §5.5. API restarts lose nothing.

### 7.5 Limits

- **Step activity:** heartbeat timeout 30 s; start-to-close 5 min.
- **Run:** bounded by a per-job budget derived from the job's recorded durations.
- **Sight:** a fixed number of actions per step.

All are named constants.

### 7.6 Mid-job takeover

**The case.** The operator is partway through a known job in their own tab, and the
panel offers to finish it. Steel cannot see the operator's tab.

**What already exists.** The extension recognises the job from the shape of the
operator's last gestures (`recognise.js` `match`, over shapes served by
`ServeShapes`). It knows how far in the operator is (`k`, shape entries matched) and
what they typed (`valuesFrom`). The offer's press sends both
(`StartWorkflowRunRequest.matched` and `values`). `StartWorkflowRun.execute` turns
`matched` into a step with `resumes_at`. Today the extension's own run then carries on
in the operator's tab, where the state already is.

**On Steel.**

1. **Start.** The press also names the operator's tab and the time span its matched
   gestures cover (`took_over`: tab id, first and last gesture time). The press flushes
   the capture queue before it is sent. `start_run` is called with
   `from_step = resumes_at(k)` and the carried values.
2. **The operator's writes.** At start, the server reads that tab's uploaded gestures
   in that span and their captured network calls. For each write step whose recorded
   call is made by a gesture the operator has reached (shape entry `< k`), it matches
   their calls against the recorded write with the same rule the runtime uses for its
   own writes (`write_confirmed`: method and path shape, expected status):
   - **Seen and confirmed:** the step is recorded `done` in `Progress`, lane
     `operator`. A `done` mark is immutable, so it is never sent again.
   - **Anything else** (no matching call, a refusal, no status yet, or uploads not yet
     reaching the last matched gesture): the step is recorded in doubt (`sending`).
3. **Bring the tab to step k.** The run starts after the last confirmed write that
   comes before any doubt, or at step 0 if there is none. Steps before that point are
   the operator's. From there Steel replays only the non-write steps up to `k`
   (navigation, opening the form, filling the carried values) on the ordinary ladder.
   A write marked `done` is skipped.
4. **Continue.** From step `k` the run is an ordinary run: same ladder, same
   verification.
5. **Never guess.** A write in doubt is settled as §7.3 settles any write in doubt:
   by a read-back, or by asking the operator in the panel (§7.4, D5), who answers
   `done` or `redo`. No write is sent while its status is unknown.

The operator's own tab is left alone. Their unsaved form is theirs to discard; the
panel says so (design 3).

## 8. Testing

1. **Unit.** Each lane, the ladder, the broker, promotion and the known-broken list,
   progress and idempotency. Steel, httpx, MCP and Gemini are faked.
2. **Page-code parity.** One suite for `page-code.js` runs against the same local pages
   in two places: real Chrome through the extension's injection, and Playwright
   through `add_init_script`. Both must choose the same element. The pages include an
   ExtJS-style grid, an iframe, stale ids, and several matching elements.
3. **Integration on local Steel.** Run against a local identity-provider chain (form,
   redirect, app). The scenarios:
   - leases and restore;
   - a container crash;
   - a worker restart mid-run with no repeated write;
   - a stop during a step;
   - two runs as tabs on one account;
   - expiry mid-step followed by re-sign-in;
   - a takeover after the operator's own save, which sends that save no second time;
   - a lookup read through the account's session, then from a Steel tab when the call is refused.
4. **Live QA proofs.** Each is run once by the operator.

| # | Proves |
|---|---|
| QA-0 | sessions per container (C0) |
| QA-1 | a mined Blue Yonder job on Steel, signed in from the vault, UI lane |
| QA-2 | the same job promoted to the API lane, no model call |
| QA-3 | a mail job replying through the Gmail connector (tool lane) |
| QA-4 | two parallel jobs on one account; a container restart restores saved state |
| QA-5 | expiry mid-run recovers; a worker restart mid-run repeats no write |
| QA-6 | a job the operator started by hand is finished on Steel from their step; their save is not repeated |
| QA-7 | the server reads the mailbox with the extension closed; a request mail starts its run; no mail is read twice |
| QA-8 | a lookup answers with the operator's Chrome closed, read through the account's Steel session |

## 9. Rollout

A per-tenant setting, `executor: extension | steel`, controls the rollout:

1. Shadow on QA: Steel runs alongside the extension, and the verdicts are compared.
2. `greyorange` switches to `steel`. The extension stops executing but keeps capturing.
   The server mail poll (§2) starts reading that tenant's mailboxes. The extension's
   heartbeat look keeps running beside it; the per-message claim keeps them from
   reading any mail twice.
3. After QA-1 to QA-8 pass, `steel` becomes the only executor and the setting is
   removed. The extension becomes watch-only (§10): it captures, recognises and asks,
   and it can no longer act on a page or send a request for a run.

## 10. Removed when live

- Extension execution: every executing command kind in `commands.js` (`ui.*`,
  `navigate`, `screenshot`, `sign_in`, `tab.open`, `calls.since`), and the execution
  in `in-page.js` (which moves into `page-code.js`).
- `httpSend`: the `http.send` command, which sends a request from the operator's
  browser with their cookies, and the page code's `send`, `csrfToken` and
  `requestedWith` that serve it.
- The command socket (`channel.js`), whose only job is to carry commands to
  `commands.perform`, and the in-page driving band (`showing.js`).
- The heartbeat's mail call: `lookInTheMail` and `api.fromTheMail`, with the throttle
  in `looking.js` and `offerFromMail`. The server poll (§2) replaces them.
- A test proves the extension is watch-only: no code the extension can load acts on a
  page or sends a request for a run.
- The backend's command socket (`agent_channel.py`, `SocketChannel`), once lookups read
  through Steel (§6.5) and nothing sends a command any more.
- `pursuits.spawn` and the in-memory `Stops`.
- The grace timer in `release_strays.py`.
- The resolution and fixed waits in `ui_driver.py`.
- The old skill engine, after its use on QA is counted (plan C14).

## 11. Out of scope

- A live view: Steel's session viewer is enough for debugging.
- The service account: after the POC (D9).
- Shadow-DOM paths.
- More than one tenant deployed: the design is tenant-scoped, but only `greyorange`
  runs it.
- Learning-side prompt work and panel UI: designs 2 and 3.

## 12. Risks

| Risk | How it is measured or contained |
|---|---|
| Self-hosted Steel holds one session per container | QA-0 first; the broker hides the answer |
| Saved state does not restore (IP or fingerprint binding) | QA-4. Fallback: a fresh sign-in, which is already the path |
| VM memory per browser (~300–500 MB) | QA-4 measures it; accounts are capped by `steel_urls` |
| Page-code parity drift | CI hash check plus the parity suite |
| Snapshot repair acts on the wrong element | Confidence threshold; only a write verified by after-state counts as done |
| Sight cost | Metered, capped and bounded per step; every success is learned into the UI lane |
| Evidence recorded before §4 lacks the new fields | Older gestures use the existing strategies; new doings add the fields |
| A takeover reads the operator's evidence before it is uploaded | The press flushes the capture queue; a write not proven by an uploaded call is in doubt and settled by read-back or asked (§7.6) |
| The operator saves their own form after a takeover | The panel says the form is theirs to discard (design 3); the run's own write is still verified (§6.2) |
| A lookup competes with runs for an account's browser | It takes a tab, never the account lock unless it must sign in, and closes the tab in `finally`; a full pool or a sign-in that needs a person is a named gap for that system, not a wait |
| A lookup could reach a write | Structurally impossible: only 2xx GETs are addressed, the API lane sends `GET`, the tab path only navigates and photographs; tested |
| The mail poll and the heartbeat look read one mail twice | One claim per message, an insert that does nothing on conflict; proven by a concurrent test on Postgres |
