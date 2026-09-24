# Codebase audit, 2026-09-23

Scope: the whole repository (backend `src` 57,750 lines, extension 20,291, console 28,818). Read-only audit by five parallel reviewers, then every finding marked **verified** was re-checked against the code by hand. Rule applied throughout: code that learns from what failed or was not captured and improves itself is legitimate. The target is one-off hardcoding, symptom patches, dead code and debt.

## 1. Verdict

The learning core and the evidence model are sound, but the run engine and the edges around it grew by incident. The two strongest signs:

- `run_workflow` in `application/execution/run_workflow.py` is **one function of 1,203 lines** (59% of the file), with 24 parameters, 9 levels of nesting and about 29 mutable flags. The next largest function in the file is 51 lines. Since 2026-09-10 the file took 103 commits, 46 of them `fix:`, including a fix, revert and re-fix on 09-20. Its notes cite 46 dated incidents and 14 run ids. **Verified.**
- The extension carries **110 dated incident rules** ("measured on the deployment 2026-09-1x"). `service-worker.js`'s `handle()` is 1,359 lines, a switch over about 60 message kinds.

The old skill engine is dead in production. The deployed QA database has **0 skills and 0 skill runs ever**, against **137 job runs in the last 7 days**. **Verified.** The local database's 47 skills and 175 runs date from August.

## 2. Critical: wrong results and security (fix first)

| # | Finding | Evidence | Why it matters | Root-cause fix |
| --- | --- | --- | --- | --- |
| C1 | **A job can be reported as succeeded with steps undone.** On a "control not found / no tab" error, if the job `is_a_way_in` and the browser is on another of our pages, the run is marked `held` and returns. | `run_workflow.py:1714-1724`; `domain/skill/signing_in.py:21` (`is_a_way_in` only checks that every cited gesture is on one origin) | Most Blue Yonder jobs happen entirely on one origin, so an ordinary job that loses its page mid-way reports success. **Verified.** | There is no "this job is a sign-in" fact. Tag sign-in jobs at mining time; delete this branch. |
| C2 | **Spliced sign-in steps skip every write rule.** `may_write = (not leg.rescue) and …` | `run_workflow.py:1521` | Steps spliced in to sign back in bypass the "state unknown after a write" rule. `signs_in_at` picks "the only other job entirely on that origin", which may be any portal job. **Verified.** | One `ensure_session(system)` driven by an explicitly tagged sign-in job, never exempt from write rules. |
| C3 | **The "tenant only" guard stops nothing.** It refuses only a request that also sends the device header; the extension holds the tenant's full bearer token and leaves that header off for exactly those routes. | `interface/http/asking.py:73-99`; `new-chrome-extension/src/background/api.js:39-51` | Any browser can do everything the tenant can: register/revoke devices, write vault secrets, spend model money. **Verified.** | Issue a device-scoped token at registration; tenant routes reject tokens that carry a device claim. |
| C4 | **Tokens are 30-day, unrevocable, minted by CLI, with no roles.** | `infrastructure/auth/signed_tokens.py:20`, `cli/mint.py:28` | Anyone holding a token can approve, revoke and write secrets until it expires. | Real login (Keycloak is wired), short-lived tokens with refresh, a role claim. |
| C5 | **An answer the model could not read is taken as the value.** No model, an exception, or an empty reply all return `answers=True` with the raw sentence. | `application/chat/reading_an_answer.py:36-53` | During a model outage, whatever the operator typed goes straight into run parameters. With full autonomy this becomes a direct write. **Verified.** | Return "unknown" and ask again. |
| C6 | **Mining sweeps every tenant when any tenant has new work.** `tenants_since` returns all tenants with new gestures; its truthiness decides this tenant's pass. | `application/observation/mine_lately.py:65`; `infrastructure/db/evidence.py:238` | Undoes the cost bound written after the measured $937 day. **Verified.** | A tenant-scoped check: `newest_arrival(tenant) > last pass`. |
| C7 | **Every mining pass re-reads the whole gesture store once per learned job**, before the spend cap is checked. | `mining_pass.py:567-571` (`gestures_for` inside `for workflow`); cap checked later | Cost and time grow as jobs × gestures. Its note claims "once per pass", which is false. **Verified.** | Read once, outside the loop; check the cap first. |
| C8 | **Model spend has no limit, and five kinds of call are never counted.** `daily_usd_cap=-1`; the interpreter (pro model), intent parser, vision driver, transcriber and embedder are unmetered; `from_the_mail`'s `understand` calls and `IsItAnAnswer` spend are discarded. | `config.py:152`; `infrastructure/db/spend.py:13-38`; `chat/converse.py:329` | Nothing stops a runaway loop. | One metering wrapper around every model port that writes a spend row and checks the cap. |
| C9 | **A second api process silently breaks runs.** Sockets, approvals, stops and run tasks live in one process; failing the advisory lock only logs a warning and keeps serving. | `container.py:233-260`, `interface/http/app.py:95-101` | Requests landing on the second process get "no socket"; startup `fail_orphans` fails live runs. | Fail readiness without the lock now; move this state to Postgres/Redis before scaling out. |
| C10 | **Single-use passwords sit in a module-level dict**, never swept, takeable by any run in the tenant. | `application/execution/one_time_secrets.py:15` | A password given for one run stays in memory until restart and can be used by another. | Key by run, sweep on expiry, hold in the container. |
| C11 | **Gmail connector is a local prototype**: refresh tokens as plaintext files, OAuth redirect fixed to `localhost:8933`, one global MCP session for every caller, token refreshed on every call, `SystemExit` on refresh failure. | `backend/gmail-connector/server.py:37,45,153,175-183,457` | Not safe or reliable for more than one operator. | OAuth callback in the backend, grants in the vault, cached access tokens, per-caller sessions. |

## 3. Hardcoded special cases (one situation baked into general code)

| Where | What | Proper home |
| --- | --- | --- |
| `domain/skill/signing_in.py:29` | Keycloak and Azure path fragments decide sign-in pages and exempt clicks from write rules | Sign-in tagged per job at mining time |
| `domain/execution/mail_job.py:11,42`; `run_workflow.py:1005`; `chat/from_the_mail.py:35,47`; `chat/ask_the_asker.py:21`; `execution/gather.py:24` | Gmail named as the mail server, a Gmail query syntax, two different mailbox host sets, an English "Send" button name | A mailbox-provider port with per-connector config |
| `domain/skill/shape.py:36-40` | Jobs are hidden from offers if they touch a mailbox host (Gmail/Outlook only) | Gate offers on whether the job does business, or learn it from dismissed offers |
| `domain/observation/identity.py:46` | Only dotted fragment segments (Blue Yonder's `#wm.config…`) count as a screen route | Keep the fragment path minus id-like segments, or learn per origin |
| `application/execution/plan_step.py:371`; `domain/execution/evidence.py:51`; `domain/execution/planning.py:19`; five places assume a `data` response envelope | ExtJS xtypes (`boundlist`, `view`), Blue Yonder live headers, BY response shape | One per-platform adapter, learned where possible |
| `new-chrome-extension/src/background/in-page.js:45-104,760,858`; `commands.js:330-337,1440`; `whats-on-screen.js:39-51` | `Ext.ComponentQuery`, `.x-grid-cell`, `CSRF-ENCRYPT-TOKEN`, ExtJS mask/dialog selectors inside the generic driver | Moves to the server adapter in the Steel migration |
| `new-chrome-extension/src/background/sign-in.js:34` | Azure B2C button ids | Per-system login recipe on the server |
| `domain/skill/repeats.py:33` (and `reversals.py:11`) | Only HTTP 201 counts as a create, so list jobs on backends answering 200 are never found | Any 2xx write with distinct bodies |
| `application/connection/connect_system.py:84-103` | Vendor domains and facility query keys | Per-connection configuration |
| `infrastructure/knowledge/ingest.py:44`, `seed_skills.py:53` | CLIs default to tenant `acme`, system `blue_yonder` | Required arguments |
| `new-chrome-extension/src/background/deployment.generated.js:9-12` | A committed plain-HTTP deployment IP that carries bearer tokens | HTTPS, set per build |

## 4. Symptom patches (fixing where it showed, not where it came from)

| Where | Patch | Real cause |
| --- | --- | --- |
| `run_workflow.py` session handling: `_let_in`, `_sign_in_here`, `_ask_for_the_password`, the itinerary splice, `_said_what_is_there` | Five overlapping answers to "the session expired" | No model of session state |
| `run_workflow.py:1519-1536` `may_write` | A write is inferred at run time from silence, with incident exceptions | A step's effect (reads, writes, navigates) should be classified once, at mining |
| `run_workflow.py` "join where the browser is": `_ahead_of_here` plus three copied blocks, including a B2C cross-host exception | Four copies, four commits on 09-23 alone | The run never locates itself before starting |
| `run_workflow.py` `collapsed` / `in_reserve` / `never_filled` | Switching between replay and UI inside the loop; four rung orders | Choose Replay or Drive per run, with an explicit fallback |
| `application/execution/workflow_runs.py:570` | Stop is delivered as an approval; four wait sites must each re-check "stopped" | A wait helper that returns approved, stopped or timed out |
| `verify.py:158` `effect_already_holds` | Skips a write if a read body contains all the values anywhere, so a list containing other records can match | Compare the record keyed by the write's identity |
| `domain/skill/passwords.py`, `presses.py` | Password and press steps re-added after mining | Redaction removes the secret's field label, so the model has nothing to cite; emit "typed a secret into <field>" instead |
| Triple redaction: `ingest.py:150` (recording rules), `rig_wire.py` validators (observation rules), `trim.py` (again) | Two separately maintained rule sets, kept in step by one test | Two capture paths merged without merging their rules; one rules module applied once at ingest |
| `evidence.py:7` `once_each` | Drops duplicate request ids on every blob read, for an extension bug already fixed | Migrate stored blobs once, then delete |
| `routers/stream.py:38-88` | Polls 3 s because the row appears after the id is returned | Create the row before returning the id |
| `converse.py:1006`, `connection/sign_in.py:179`, `check_session.py:179` | "timeout" found in error text; "auth" anywhere in a skill name; any cross-host redirect counts as login | Typed errors and explicit flags |
| Silent fallbacks: `intent/resolve.py:65`, `gemini/intent.py:152`, `gemini/interpreter.py:180`, `converse.py:468`, `worker.py:100`, `steel/capture.py:307,317,437` | Errors swallowed or logged at INFO | Fail loudly, or return a typed "unknown" |
| Extension `panel.js:1463,1622,3108` | UI behaviour decided by regex over server free text | The server sends a typed reason |

## 5. Dead and duplicate code

| What | Size | Status | Removal needs |
| --- | --- | --- | --- |
| Old skill engine end to end: `execute_skill`, `self_heal`, `vision_step`, `repair_drift`, `batch`, `run_from_preview`, `pursue_goal`, intent resolve, threads `pursue` | ~4,100 lines | Reachable, **never used in production** (0 skills on QA) | Decide first: remove converse's skill fallback, then delete |
| Induction (`InductionWorkflow`, `induce_skill`, seeding) | 2,079 | Dead | Remove workflow, activity, route, Makefile target |
| Old candidate miner (`mine`, `segment`, `propose`, `teach`, `learn`, `demonstrate`, `/v1/candidates`) | 1,688 | Dead (loop off, no client) | Drop routes, container methods, `task_candidates` table (after `analytics/summary.py`) |
| Skill-from-rig adoption | 619 | Dead (only a broken script) | Delete with its script and tests |
| Skill editing and promotion routes | 430 | Dead routes | Delete routes |
| Recordings/demonstrations routes, `RecordingSessionWorkflow`, extension `teach-start` (no sender) and `teaching.js`, console `features/recording` | ~1,200 | Partly dead | Keep the `recordings` table (used by browser sessions) |
| Two ingest decoders and element models (`capture/decode.py` + `recording/element.py` vs `rig_wire.py` + `correlate.py`) | — | Duplicate | One decoder into one model |
| Fields stored but never read: `Workflow.same_as`, `Intent.continues`, `Coverage.gini`; the tail-reading path | — | Dead, and still paid for in model output | Drop from schemas and storage |
| Routes with no client: `/mine`, `/intent/resolve`, `/skills/understand`, `/gestures/read`, `/spend`, `/pool`, `/workflows/{id}/taught`, `/connections/{id}/token`, `/resume`, `/session-headers`, `/workflow-runs/{id}/wrong`, `/triggers/{id}` GET | — | Dead | Delete, or give them a client (spend and resume are useful) |
| Extension handlers with no sender: `flush`, `teach-start`, `look-in-the-mail`, `nudge-answer`, `never-watch-site`, `revise-run`, `say-to-run`, `panel-open`; `api.readChat`, `reviseRun`, `sayToRun` | — | Dead | Delete |
| Console: `ConnectPanel` (~400 lines), `use-narration.ts`, `data-view.tsx`, four unused `components/ui` files, many unused API wrappers | ~900 | Dead | Delete |
| `ExpireConfirmations` | — | Zero callers, so expired confirmations stay listed | Wire it to a sweep or delete it |
| Duplicates: `LIFETIME_MS` twice, seven time formatters, outcome wording twice, locator resolver twice (`watch.js` vs `in-page.js`, which disagree on `within`), `_ACTIONS_NEEDING_TARGET`, write-method sets, two `_save` helpers | — | Duplicate | One copy each |
| Unit tests exercising only dead code | ~7,300 | Dead | Delete with their code |
| Scripts targeting the deleted rig (`mirror_backfill.py`, `skill_from_rig.py`) and one-offs (`backfill_gestures`, `probe_mine_route`, `redact_stored_evidence`, `stub_device`, `create_by_api`) | — | Broken or one-off | Delete |
| `knowledge-base/raw`, `images`, `md`, `recipes` (≈45 MB tracked) | — | Not read by code | Move out of the repo |
| Stale docs: `04-frontend-walkthrough.md`, `15-observation-to-tasks.md`, `17-agent-architecture.md` (cites missing scripts), `13-blue-yonder-knowledge-base.md` (cites a missing tool) | — | Wrong | Update or archive |

**Becomes dead with the Steel migration** (keep until phase 10 of the spec): extension `commands.js` (1,678), `in-page.js` (1,020), `pointing.js`, `sign-in.js`, `finishing.js`, `whats-on-screen.js`, most of `channel.js`, about 1,000 lines of `service-worker.js` and ~4,600 test lines. Must be **ported to the server first**: the locator ladder (`in-page.js:96+`, including combobox trigger selection), settle rules, finding the frame that holds live headers, the page-state digest, and the sign-in safety rules.

## 6. Magic numbers

Justified by a measurement in the notes: `K_SITTING_GAP_S=600`, `K_GESTURES_IN_A_DOING=2`, `K_POOL_WAIT=0.5`, `K_SETTLE_S=120`, `K_MIN_VALUE_LEN=4`, `K_MIN_LONE_WORD=6`, `K_CAP_EVERY=10`, `MAX_READS=25`, `K_MOST_ITEMS=25` (policy).

No measured basis: `K_SAME_JOB=0.5` and `K_SAME_EVIDENCE=0.5` (a pair passed "at exactly 0.5 by arithmetic coincidence"), `K_MIN_COVERAGE=0.5`, `K_MAX_SKEW=0.4`, `ATTRIBUTION_SECONDS=10`, `SOON_S=20`, `K_LEAD_UP_S=180`, `K_UBIQUITY=0.25`, window limits (`25`, `2000`, `40`, `400`), `K_TEXT_IDENTITY_MAX=40`, run-engine waits (`K_STEP_SLACK=3`, `K_LOOKS=4`, `K_OPENINGS=3`, `K_STILL_COMING_S=2.0`, `K_APPROVAL_WAIT_S=300` reused for four different waits, `K_SAME_WRITE_WINDOW=30min`, `K_HELD_FOR=15min`), and the extension's execution timeouts (`SETTLE_MS`, `OPENS_WITHIN_MS`, `REACTS_WITHIN_MS`, `LOADS_WITHIN_MS`, literal `hold(tab, 8000)` ×4). `K_EARNED_RUNS=3` claims "three different days' values" but only counts runs; it is removed by the autonomy decision anyway.

## 7. Fix plan, in order

Each item is its own branch and review; a behaviour fix comes with a failing test first.

1. **Wrong results:** C1 (false success) and C2 (spliced steps bypass write rules). Introduce an explicit sign-in tag on jobs at mining; delete the `is_a_way_in` success branch.
2. **Security:** C3 device-scoped tokens, C5 answer-on-failure, C10 single-use passwords. Then C4 real login and roles.
3. **Cost:** C6 tenant-scoped sweep check, C7 read once and check the cap first, C8 one metering wrapper and a real default cap.
4. **Delete the dead** (§5): old skill engine (after removing converse's skill fallback), induction, candidate miner, rig adoption, dead routes, handlers, console code, tests, scripts, stale docs.
5. **One of each:** one redaction rules module applied once; one ingest decoder; one locator resolver; one mailbox-provider port; one platform adapter for ExtJS/Blue Yonder specifics.
6. **Mining-time facts instead of run-time guesses:** step effect (reads/writes/navigates), sign-in jobs, screen routes, 2xx creates. This removes most of `may_write`, the session patches and `signing_in.py`'s paths.
7. **Split `run_workflow`** into a thin loop over step executors (replay, drive, mail) with shared `await_decision`, `locate_browser`, `ensure_session` and `observe_effect`. This lands together with the recipe runner in the VM-execution spec (`docs/superpowers/specs/2026-09-23-vm-execution-recipes-and-agents.md`), not before it.
8. **Process state out of memory** (C9) before more than one api process runs.
9. **Measure or justify** each unmeasured constant in §6 as the code around it is rewritten.

Items 1–3 are small and urgent. Item 4 removes roughly 10,000 lines of source and 7,000 of tests with no behaviour change in production.
