# F3 report: the sign-in verdict is re-decided when the evidence changes, and sign-out chores are flagged

Branch `d2/f3`, cut from `feat/execution-runtime` at `76e3c88`.

## Commits

1. `c51a1ef` `feat(mining): signs_in and signs_out re-decided whenever a job's steps change, by a column-only compare-and-set` holds the code, tests, migration 0087 and code notes.
2. `docs: F3 cloud report` is this file.

## What changed, and why

**Root.** A job's verdict was written in two ways, and both were wrong for a job whose steps change:

- The sweep wrote it through `decide_signs_in`, a compare-and-set that fired only while the column was NULL. It decided each job once and never again.
- Grow and heal carried it inside a whole-job save (`_grow` copied `proposal.signs_in`; `_healed` set it and saved). Every other whole-job save (`learn_parameters`, `Teach.learn_field`) wrote back whatever verdict it had read. Nothing decided again after a learn.

Nothing asked whether a job signs out.

**Now:**

- **Domain.** `checks.signs_out(workflow, gestures)` decides the second verdict by code:
  - the job's last cited sign-out control ("Log Out", "Logout", "Sign out", "Sign-off", whole words, by name);
  - nothing written back during the job;
  - nothing the job does afterwards is back in the signed-in system;
  - then a sign-in or signed-out page. That means the control's own navigation lands on another origin or on a path naming signing in or out, or the very next gesture is on such a page, on another origin, or on a credential.

  `Workflow.signs_out` is added (tri-state). `Workflow.chore` returns `signs_in or signs_out` and is the one place the chore rule lives.
- **Port.** `WorkflowRepository.decide_signs_in(tenant, id, bool)` is replaced by `decide(tenant, workflow, *, signs_in, signs_out) -> bool`. It is a compare-and-set over the job as it was read, meaning its steps and both verdicts, and it writes only the two columns. The SQL version locks the row, the same lock every step-changing writer already takes (X11), compares, then runs `UPDATE ... SET signs_in, signs_out`. The fake mirrors it, and the contract suite holds both to the same rules.
- **A whole-job save never writes a stored job's verdict.** `SqlWorkflowRepository.save` drops `signs_in` and `signs_out` from the upsert's `set_`, and the fake keeps them on a re-save. A new job is still inserted with its verdict. This makes `decide` the only thing that writes a stored verdict, so a learn that read the job before a decision landed cannot put the old verdict back.
- **Every step change decides again,** always through one decider (`mining_pass._judged`, which now returns both verdicts) and one writer (`mining_pass._decide`, which writes only when the verdict changes):
  - grow: `_grow` calls `_decide` after `grew`;
  - heal: `fill_in_passwords` → `_mend` heals the steps, saves them if they changed, then calls `_decide`;
  - learn: `Teach.learn_field` calls `decide_sign_ins(uow, tenant, [grown])` in the same transaction, under the same row lock;
  - new proposals: `_one_pass` sets both verdicts before the first save;
  - sweep: `decide_sign_ins` decides every undecided job, which is now `signs_in IS NULL OR signs_out IS NULL`.
- **R1.** `rank_jobs` and `chore_named` use `workflow.chore`, so a `signs_out` job is never a candidate, and a request naming only it is answered as a chore. `K_A_CHORE` now says "signing in and out is the session broker's work, never a request's". R1's value checks and `logins_of` are untouched.
- **Migration `0087_a_job_knows_whether_it_signs_out`** (down_revision `0085`) adds nullable `workflows.signs_out`. Every existing row starts NULL, so the next sweep decides every stored job both ways. That also decides `signs_in` again for every job. The downgrade drops the column and touches nothing else.

## Files changed

- `backend/src/sro/domain/skill/checks.py`: `signs_out` and its helpers.
- `backend/src/sro/domain/skill/workflow.py`: `signs_out` and `chore`.
- `backend/src/sro/application/ports/repositories.py`: `decide` replaces `decide_signs_in`.
- `backend/src/sro/infrastructure/db/workflows.py`: `decide`; `save` no longer writes a stored verdict; `undecided` includes `signs_out` NULL; the column is mapped.
- `backend/src/sro/infrastructure/db/models.py`: the `signs_out` column.
- `backend/migrations/versions/20260927_0087_a_job_knows_whether_it_signs_out.py`: new.
- `backend/src/sro/application/observation/mining_pass.py`: `_judged` returns both verdicts; new `_decide`, `_verdict` and `_mend`; `_healed` no longer touches the verdict; changes to `_grow`, `fill_in_passwords`, `decide_sign_ins` and `_one_pass`.
- `backend/src/sro/application/runtime/teach.py`: `learn_field` decides again.
- `backend/src/sro/application/chat/candidates.py`: `chore`.
- `backend/src/sro/application/chat/understand.py`: `K_A_CHORE` wording.
- `backend/tests/unit/fakes.py`: `decide`; `save` keeps the verdicts; `undecided`.
- Tests: listed below. Three existing tests were updated too:
  - `test_runner._classify` now writes through `decide`;
  - `test_mine_lately` saves decided jobs with `signs_out=False` and uses `decide` in the refusing double;
  - `test_the_repositories_agree` replaces the `decide_signs_in` contract.
- Code notes updated under `docs/code-notes/backend/src/sro/…` for `checks.py`, `workflow.py`, `mining_pass.py`, `repositories.py`, `workflows.py`, `models.py` (anchors only), `teach.py` and `candidates.py`.

## Tests added

Unit (run, green):

- `tests/unit/domain/test_a_job_that_signs_out.py`, 9 tests:
  - the real Log Out shape (user menu, then Log Out into Azure B2C's logout and sign-in page) signs out;
  - landing on its own `/login` signs out;
  - a credential page as the next gesture signs out;
  - no sign that the session ended does not sign out;
  - going on working afterwards does not sign out;
  - a write then a log out is work;
  - "Logoutput report" is not a sign-out control;
  - no evidence does not sign out;
  - `chore` counts both verdicts, and undecided is not a chore.
- `tests/unit/application/rig/test_a_verdict_follows_the_steps.py`, 4 tests:
  - **a job whose grow adds sign-in steps flips to `signs_in` true**;
  - a heal decides a stale verdict and counts the job once;
  - a learned field decides the verdict of the steps it made;
  - a learn that changed nothing reads no evidence.
- `tests/unit/application/rig/test_mine_lately.py`: an undecided `signs_out` is decided both ways by the sweep. **The Log Out job becomes `signs_out` true and a chore.**
- `tests/unit/application/test_request_candidates.py`:
  - **a sign-out is never a candidate**, and a request naming only it is that chore;
  - a "log out" request is answered as a chore without asking a model.
- `tests/contract/test_the_repositories_agree.py`, fake half run and green, SQL half **written, not run**:
  - the undecided are every live job missing either verdict;
  - `decide` writes both verdicts only over the job it was decided from;
  - a whole-job save never rewrites a stored verdict.

Integration (real Postgres), **written, not run**:

- `tests/integration/test_workflow_repositories.py::TestAVerdictFollowsTheSteps`:
  - `test_a_learn_that_lands_during_a_decision_is_not_overwritten`: the sweep reads the job, a real `Teach.learn_field` grows it and decides, then the sweep's stale decision is refused. The learn's steps, parameter and verdict stand. This is the brief's third test.
  - `test_a_learn_waits_for_a_decision_in_flight_and_keeps_both`
  - `test_a_whole_job_save_from_a_stale_read_keeps_the_decision`
- `tests/integration/test_the_migrations_run.py::test_0087_leaves_every_stored_job_undecided_about_signing_out_and_back`
- Updated, **written, not run**:
  - `test_a_job_that_signs_in_is_read_back_as_one`: a re-save no longer clears the verdict; `decide` does.
  - `test_a_mining_pass_holds_no_job_s_row_while_it_asks_the_model`: the healer now calls `_mend`, since `_healed` no longer covers the verdict.

  The fixture job in these tests judges as `signs_in` true: it cites the secret-typed gesture. I checked the expected verdicts against the unit fixture data with the fake stack: `(True, False)` after `learn_field`, with parameters `['region']`.

## Gate results (from `backend/`)

- `uv run pytest tests/unit tests/contract -q`: 4708 passed. The 81 errors are all setup errors for `postgres_url`: every `[sql]` contract case plus `test_openapi.py::TestFuzz`. There is no Postgres in this container. There were no failures.
- `uv run mypy src tests`: no issues in 810 files. The brief allows 2 existing errors; none remain.
- `uv run ruff check .` and `uv run ruff format --check .`: clean.
- `uv run lint-imports`: 4 kept, 0 broken.
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead.
- `grep -rn "unit_of_work()" backend/src/sro/interface/`: nothing.
- There is no wire change (`signs_in` and `signs_out` are not in `interface/http/schemas.py`), so `make types` was not needed.

## Rulings

- Ruling: "learn" means `Teach.learn_field` (the runtime learning that grows a job's steps), and `learn_parameters` does not trigger a new decision. `learn_parameters` changes parameters and title only, never steps or cites, and its whole-job save can no longer touch the verdict. Cost if wrong: a verdict that depends on parameters would go stale until the next heal. None does today.
- Ruling: the compare-and-set compares the job's steps and both verdicts under the row lock, rather than comparing only the old verdict in the `UPDATE`'s `WHERE`. A grow whose new verdict happened to equal the old one would otherwise let a decision made from the older steps win. Every step writer already takes this row lock (X11). Cost if wrong: the sweep briefly waits behind a run's learning on the same job.
- Ruling: `SqlWorkflowRepository.save` never writes `signs_in` or `signs_out` for an existing row. This makes `decide` their only writer, the "one writer, compare-and-set" invariant. Cost if wrong: any future caller that expects a whole-job save to change a verdict silently does nothing. `test_a_whole_job_save_never_rewrites_a_stored_verdict` pins the behaviour.
- Ruling: a sign-out control is recognised by an English whole-word vocabulary on the target's accessible name and text. A signed-out page is recognised by a path vocabulary (log/sign + in/on/out/off, logged/signed out, session ended/expired/timeout), or by a navigation to another origin. This is name-based, like credential detection, and nothing reads values. The code notes name the limit and the upgrade path: read the session-cookie clearing once the recorder keeps cookie names. Cost if wrong: a Log Out labelled only with an icon, or in another language, stays a candidate.
- Ruling: only the control's own navigation and the very next gesture in that stream count as "then a sign-in page or a session-ended page", not the whole sitting. Cost if wrong: a Log Out whose landing page was recorded only on a later gesture is missed.
- Ruling: a job that writes something and then logs out is work, not a chore. It follows `signs_in`'s "nothing written back" rule. A read-only job that goes on working after a Log Out is not a chore either. Cost if wrong: such jobs are offered, and running one logs the session out at its end.
- Ruling: `_decide` writes only when the judged verdict differs from the one read. Unchanged verdicts write nothing, so an ordinary pass stays write-free. Cost if wrong: none found.
- Ruling: `K_A_CHORE` is reworded to cover signing out. No test or frontend string matched the old text. Cost if wrong: a consumer matching the exact old string. I found none.
- Ruling: migration number 0087, down_revision 0085, as the brief says (T1 takes 0086; the controller re-chains at merge).

## Concerns

- **Azure B2C sign-in copies.** The brief says some were never flagged. This change decides every stored job again (0087 makes `signs_out` NULL, so the sweep decides both verdicts) and decides again on every later step change. So a copy that the current `signs_in` rule judges true will now be flagged. If a copy stays false after the first sweep, the `signs_in` rule itself misreads that shape. I had no real B2C copy in this container to check, and did not change `signs_in`.
- **The worker must restart.** The sweep, the mining pass and `Teach.learn_field` (an activity) all run in the worker.
- **The sweep now locks each undecided job's row briefly** (`decide` uses `FOR UPDATE`), where before it ran a bare `UPDATE`. That is one short lock per job; it runs under the tenant's mining lock, one transaction per tenant.
- **Cross-task.** Anything in P2, F1, F2, K1 or T1 that calls `decide_signs_in`, or relies on a whole-job save writing `signs_in`, has to move to `decide`. On this branch every caller has moved. F1's `domain/chat/asking.py` is not touched.

## Round 1

**Merge.** `origin/feat/execution-runtime` is still at `76e3c88`, the commit `d2/f3` was cut from. `git merge` answered "Already up to date", so there was no merge commit to make.

**Fixes, each test-first. Every new test was seen red before the code changed.**

- **I1: never write a verdict decided without evidence.** `chores.judged` returns `None` when any cited gesture is missing, and `chores.decide` then writes nothing.
  - A stored `signs_in = true` is never overwritten by a no-evidence judgement.
  - A job nobody has judged stays undecided.
  - Tests: `test_a_sign_in_job_missing_one_cited_gesture_keeps_its_verdict` (the probe: a `signs_in = True` job missing one cite keeps `True` after the sweep), and `test_a_job_whose_evidence_is_not_all_stored_is_never_decided`. That second test replaces `test_a_job_with_no_evidence_is_decided_false`, whose ruling this reverses.
  - Two sweep tests that relied on no-evidence jobs being decided (`busy`, `write fails`) now record the gesture they cite.
- **I2: "writes nothing" uses `evidence.writes`** (any non-read method, any status), not `_did_business`.
  - Every step up to and including the control is checked, with the control's own call left out of its step.
  - `_only_reaches` also refuses any mutating call on any host. That covers the API's own subdomain, which `writes` (same origin only) cannot see.
  - Test: `test_any_write_before_the_log_out_is_work_whatever_its_method_status_or_host` covers a DELETE 204, a form POST 302, a POST to `api.*` and a POST with no status.
- **I3: "sign off" is not a control name, and another origin alone is never proof.** A signed-out landing now means the control's own navigation, or the next gesture in the same stream **and tab**, is on a sign-in or signed-out path or is the credential.
  - Tests:
    - `test_a_sign_off_queue_is_not_a_sign_out` (Quality → Sign-Off Queue → Outlook);
    - `test_a_log_out_whose_next_gesture_is_merely_on_another_host_does_not_sign_out`;
    - `test_a_sign_in_page_in_another_tab_is_not_this_log_out_s_landing`.
- **M4 (product ruling): the only substantive step is the log-out control.** Every cited gesture before the control must be `_only_reaches`: a hover or scroll, or a click or press that opens a menu, menu item, tab, tree item or navigation, or that moves the page.
  - Test: `test_a_job_whose_only_substance_is_the_log_out_signs_out_and_one_that_exports_is_work` covers both sides.
- **M1: one gesture set for every path.** `chores._sitting` is the job's cites plus everything from its first cite to `K_SITTING_GAP_S` after its last, inclusive at both ends.
  - `judged` always judges against it, so grow and heal (whole store) and sweep and learn (`evidence_of`) see the same gestures.
  - `evidence_of` now asks from `math.nextafter(first, -inf)`, because the store's `after` is exclusive and missed a gesture at the first cite's own instant.
  - Test: `test_the_sweep_and_the_heal_judge_the_same_gestures_so_the_verdict_holds`, a password typed in the same burst as the first cite. It was red: the sweep said `(False, False)` and the heal said `True`.
- **M2: the log lines.**
  - `_mend` logs "healed N step(s)" only when steps were healed.
  - A decision logs its verdict in `chores.decide`.
  - The sweep says "sign in or out", in both its info line and its exception line.
- **M3: `teach.py` imports the decider from a small module.** It is now `application/observation/chores.py`, with `evidenced`, `judged`, `verdict`, `decide`, `evidence_of` and `decide_sign_ins`.
  - `mining_pass`, `mine_lately`, `teach` and `scripts/migrate_vault_keys.py` import from it.
  - `mining_pass` no longer exports `evidence_of` or `decide_sign_ins`.
- **M5: a log out that is itself a same-origin POST 200 is the control, not a write.**
  - Test: `test_a_log_out_that_is_itself_a_post_is_the_control_not_a_write`.
- **M6: the race test now needs the steps comparison.** `test_a_learn_that_lands_during_a_decision_is_not_overwritten` first decides the job `(True, False)` and re-reads it. The learn then changes the steps and leaves the verdict exactly as it was, so a `decide` that compared only the verdicts would write the stale `(False, True)`. It is still integration: **written, not run**.
  - The fake half of `test_deciding_writes_both_verdicts_only_over_the_job_it_was_decided_from` makes the same point: the grown copy with an equal verdict is refused. That half is run and green.

**Files (round 1):**

- `backend/src/sro/application/observation/chores.py` (new)
- `mining_pass.py`, `mine_lately.py`, `runtime/teach.py`
- `domain/skill/checks.py`
- `scripts/migrate_vault_keys.py`
- tests:
  - `test_a_job_that_signs_out.py`
  - `test_a_verdict_follows_the_steps.py`
  - `test_mine_lately.py`
  - `test_migrate_vault_keys.py` (import only)
  - `integration/test_workflow_repositories.py`
- notes:
  - `chores.py.md` (new; the decider's notes moved here from `mining_pass.py.md`)
  - `checks.py.md`
  - `mining_pass.py.md`

The migration stays 0087.

**Gates:**

- unit and contract: 4716 passed. The 81 errors are the same `postgres_url` setup errors as before (the `[sql]` half and the OpenAPI fuzz test), because there is no Postgres here.
- mypy: clean (811 files).
- ruff check and format: clean.
- lint-imports: 4 kept.
- code notes: 0 stale, 0 dead.

**Rulings (round 1):**

- Ruling: `auth` and `authorize` join the sign-in path words — Keycloak's `/protocol/openid-connect/auth` and OAuth's `/oauth2/v2.0/authorize` are sign-in pages, and without the other-origin fallback a Keycloak logout would otherwise never be seen — cost if wrong: a Log Out that lands on some other `/auth` page is still flagged.
- Ruling: "log off" stays a control name and only "sign off" is dropped, as I3 names — "log off" is an ending, "sign off" is an approval — cost if wrong: a "Log off" that is not a sign-out would need a signed-out landing too, so the risk is small.
- Ruling: "only reaches" is judged by declared roles (menu, menubar, menuitem, navigation, tab, treeitem; `aria-haspopup` or `aria-expanded`; a navigation landmark) or by a page move. Plain links without a page move count as substance — an export link is a read that moves nowhere — cost if wrong: a Log Out reached through bare, role-less divs stays a candidate, which is the safe side.
- Ruling: a job with incomplete evidence is left undecided and read again on each sweep — I1 forbids a no-evidence write — cost: one wasted judgement per such job per sweep.

## Round 2

Each fix was test-first, and every new test was seen red before the code changed.

- **M4: a reaching step must lead to the control.** `_only_reaches` now accepts a click or press only if:
  - it makes no call of its own (background traffic aside);
  - it does not move the page;
  - it opens something: a menu, menu item, tab, tree item or navigation role, or an `aria-haspopup` / `aria-expanded` control.

  A menu item that fetches `report.csv` itself is substance. So is any page move. The round-1 test that counted a page move as reaching is replaced.

  Tests:
  - `test_account_menu_then_log_out_is_a_chore` (Account ▾ → Log Out: chore);
  - `test_a_menu_item_that_makes_its_own_call_is_substance` (Actions ▾ → Export to CSV, GET `report.csv` → Log Out: work; red before);
  - `test_opening_a_report_page_and_then_logging_out_is_work` (red before);
  - `test_a_job_that_exports_a_report_before_logging_out_is_work` (the round-1 export case, kept).
- **Integration regression.** In `test_the_sweep_skips_a_busy_tenant.py`, each job now cites a stored click. The test proves what it was written for again: the busy tenant stays `None`, the free one is decided `False`. I checked that verdict with the fake stack, because the test itself needs Postgres: **written, not run** here.
- **M1 leftover.** `_one_pass` now keeps `everything`, the tenant's whole store including this browser's own driving:
  - a new proposal's first verdict is `judged(proposal, everything)`, through `chores.judged`;
  - `_grow` is given `everything`. Its other readers (`keeping_fields`, `shape_key`, `credentials_typed`) read cited gestures only, so only the judgement changes.
  - Only the model's window and the pool still lose our own driving.
  - Test: `test_a_new_job_is_first_judged_against_what_the_heal_will_judge_it_against`. The operator logs out, then this browser signs back in. Before the fix, the pass said `(False, False)` and the heal would say `(False, True)`.
  - The grow path has no test of its own. Building a contained grow through `mine` needs two recognised doings. The grow uses the same `everything` variable, and `_grow`'s own verdict behaviour is covered by `test_a_job_whose_grow_adds_sign_in_steps_flips_to_signing_in`.
- **Migration** not re-chained.

**Gates:**
- unit and contract: 4720 passed. The 81 errors are the same `postgres_url` setup errors as before.
- mypy: clean.
- ruff check and format: clean.
- lint-imports: 4 kept.
- code notes: 0 stale, 0 dead.

**Ruling:** a page move is never "reaching", because a log out sits in the user menu on every page. Cost if wrong: a Log Out that exists only on a page reached by a move stays a candidate, which is the safe side. A menu whose opener lazy-loads its items with a call is also read as substance, again the safe side.

## F3b

Branch `d2/f3b`, cut from `origin/feat/execution-runtime` at `1149c11`, which carries the F3 merge `f71327f`.

- **`_only_reaches`: a menu item, tab or tree item reaches the log-out control only if it opens what the control sits in.** `_opens` accepts one of two signals:
  - `aria-haspopup` or `aria-expanded` on the clicked target;
  - on ExtJS, the control's component chain starts with the opener's own chain and is longer.

  A role alone is no longer a signal, so a leaf item is substance: the recorder sees only fetch and XHR, so a download link, Print or a report in a new window makes no visible call. `_REACHING_ROLES` is deleted. The recorder's landmarks never carry menu roles, so they could not be used.
- **Tests (test-first; the three new ones were red):**
  - `test_a_download_link_in_a_menu_is_substance`: Actions ▾ → Export to CSV as `<a role=menuitem href download>` → Log Out is work.
  - `test_a_menu_item_that_declares_nothing_opened_is_a_leaf`.
  - `test_an_ext_menu_item_the_log_out_sits_inside_reaches_it`: a chain prefix is a chore; a menu whose chain the control is not in is work.
  - Kept and green: `test_account_menu_then_log_out_is_a_chore` (Account ▾ with `aria-haspopup` → Log Out).
  - The user-menu opener in the existing fixtures (domain test, `test_a_verdict_follows_the_steps.py`, `test_mine_lately.py`) now carries the `aria-haspopup` a real user-menu button declares. Without it, the fixtures were a bare leaf.
- **Gates:**
  - unit and contract: 4843 passed. The 83 errors are all Docker/Postgres setup: 82 `[sql]` cases and the OpenAPI fuzz test.
  - mypy: clean (828 files).
  - ruff check and format: clean.
  - lint-imports: 4 kept.
  - code notes: 0 stale, 0 dead.
- **Ruling:** a hand-built menu with neither aria nor an ExtJS chain is read as substance, so its Log Out stays a candidate. That is the safe side. The notes give the upgrade path: record `aria-controls` / `aria-owns` and match them to an ancestor of the control.
