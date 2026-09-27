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
