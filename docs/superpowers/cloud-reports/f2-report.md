# F2 report: "check now" is answered from the run and the thread, never explored

Base: `origin/feat/execution-runtime` at `76e3c88b4f098a33b2e9d76dfd1633ce38e8d634`.
`git merge-base --is-ancestor 6fa0ec92 HEAD` succeeds, so R1 is in the base.
Branch: `d2/f2`.

## Commits

- `c39766e` fix(chat): F2 -- "check now" is answered from the run and the thread, never explored
- this report (docs)

## What changed

**Root.** `ResolveIntent.execute` (`application/intent/resolve.py`) reached `_nothing_taught`, the explore fallback, whenever no skill ranked. It had no idea anything was standing in the thread. It now takes `standing: bool`. When no candidate ranks and something stands, it returns `Resolution(about_what_stands=True)`. The planner is never asked, and there is no proposal and no pursuit. A sentence that names a job is still that job, standing or not. With nothing standing, the fallback runs exactly as before.

**Classification by code.** `Converse._carry_on` (`application/chat/converse.py`) works out what stands in `_what_stands`, checking in this order:
1. The last run the thread named (`last_run`), read under this tenant, if it still `stands`. A run stands while it is running, while it is asking a person (`asks_a_person`), or while it is waiting on a reply within its deadline (`still_waiting`).
2. An offer waiting on a yes (`offered_job`).
3. A question that is still wanted (`_still_wanted(pending_job(...))`).

It passes `standing` to the resolver. The rig (R1's reader) is still asked first, so a sentence it places is heard as that job. "Names no job" means the rig placed nothing and no skill ranked. The model is never asked whether a sentence is a status question.

**The answer.**
- **Standing run:** `of_the_run` (`domain/chat/standing.py`) answers from the run's state. It gives:
  - progress (its `doing` line, or the step number) or its outcome;
  - the waiting reason (the run's own question, the mail reply it waits on, the values it still `needs`);
  - the values it holds, marked "(from the mail)" when they were gathered.

  A secret-named value is never said (`is_secret_field`).
- **Standing offer or question:** `of_the_question` (`domain/chat/asking.py`) says what it is waiting on and the values it already holds.

Either answer is written with no decision. Every reader of "what was last asked" (`asked_under`, `_awaiting`) skips a decision-less assistant message, so the offer or question stays standing under it.

**Under a question `execute` routed here** (the reading said `another_task`): what the operator said is kept, and `execute` asks the question again. That line ("I am still waiting on this one." / "Nothing back from … yet.") is the answer about the question.

The status check comes before the lookup door. Without that, "what did you fetch from mail" would be planned as a lookup.

## Files changed

- `backend/src/sro/application/intent/resolve.py`: `standing` parameter, `Resolution.about_what_stands`
- `backend/src/sro/application/chat/converse.py`: `_what_stands`; `_carry_on` answers about what stands. `_no_longer_open` is renamed `_only_said`, because it now also writes the status line and the old name would have lied.
- `backend/src/sro/domain/chat/standing.py` (new): `last_run`, `stands`, `of_the_run`
- `backend/src/sro/domain/chat/asking.py`: `of_the_question`, `NOTHING_NEW`
- `docs/code-notes/...`: notes for all of the above (`standing.py.md` is new). Anchors were refreshed by `check_code_notes.py --fix`. One note (`Converse._say_the_job`, "The run goes and looks") couldn't be resolved by the fixer and was re-anchored by hand to line 630.
- Tests: listed below.

## Tests added

Unit tests, all written first and all run:
- `tests/unit/domain/chat/test_what_stands.py` (7 tests):
  - the run a thread names;
  - running, finished, asking, waiting and expired-wait states;
  - the run's sentence, covering progress, question, mail wait and mail values;
  - a secret value is never said (the rule is broken on purpose: `Password: hunter2` is in the run's values);
  - the `doing` line;
  - question and offer sentences.
- `tests/unit/application/test_resolve_intent.py` (+2 tests):
  - a sentence naming no job while something stands never reaches the planner, even though the knowledge base would have proposed a screen;
  - a sentence that names a job is still that job.
- `tests/unit/application/test_converse.py` (+18 tests):
  - the four phrases (`check now`, `have you recived mail`, `what did you fetch from mail`, `i will type it here`), each under:
    - a **standing run**: status from the run, no explore, no run or skill started, no lookup, no secret;
    - a **standing question**, where the reading wrongly says `another_task`: the question is re-asked, it stays standing, no explore, no lookup;
    - a **standing offer**: status about the offer, and the offer still stands;
    - **nothing standing**: the reply is the resolver's, the same as today, and the fixture proves the explore is reachable;
  - a finished run is not standing;
  - another tenant's run is not this thread's.

Changed test: `test_asking_for_a_different_job_is_still_heard`. Its reader fake raised, so the sentence named no job. Under F2, that is a status question. The fake now places the job the sentence asks for (`wfl_1`, "Create a Warehouse Equipment Type"), which keeps what the test is about: asking for a different job is heard. See the Ruling below.

Integration: none. There is no SQL, no Temporal and no wire change.

## Gates (run from `backend/`)

- `uv run pytest tests/unit tests/contract -q`: **4717 passed, 79 errors**. All 79 errors are environmental: there is no Docker socket in this cloud session (`FileNotFoundError` on `/var/run/docker.sock`). 78 are the `[sql]` variants in `tests/contract/test_the_repositories_agree.py`, and 1 is `tests/contract/test_openapi.py::TestFuzz`. None of them touch F2 code. The controller should re-run them locally.
- `uv run ruff check .`: passed. `uv run ruff format --check .`: passed.
- `uv run mypy src tests evals`: no issues found in 819 source files.
- `uv run lint-imports`: 4 contracts kept, 0 broken.
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead.
- `grep -rn "unit_of_work()" backend/src/sro/interface/`: nothing.
- No wire type changed, so no `make types` was needed. No migration. No prompt record changed, so no eval was needed.

The worker does not need a restart for this change: it is API-side (`Converse`, `ResolveIntent`), and no activity, executor, lane or `RunSteps` was touched. Restart the API.

## Rulings

- Ruling: "names no job" means R1's rig placed nothing **and** no taught skill ranked. — These are the two readers chat asks. A sentence either one places is heard as that job. — Cost if wrong: a sentence that asks for work no job covers, typed while something stands, gets a status answer instead of "Nothing has been taught for that". The operator loses one sentence and can ask again once nothing stands.
- Ruling: under a standing run or question, lookups are not run for a sentence that names no job. — "what did you fetch from mail" is `is_a_question` and would otherwise be planned as a lookup. The brief asks for a status answer, and a lookup door that answers it is the model deciding again. — Cost if wrong: "is there a customer type KKYT", typed under a standing question, gets the status instead of the lookup until the question is answered or dropped.
- Ruling: the classification lives in `ResolveIntent.execute` (the one place the explore fallback is reached), and `Pursuit`/`compose` in `pursue.py` are unchanged. — `Pursuit.of` is only called from `_nothing_taught`, so closing the fallback where it is reached closes it for every caller. Editing the question text in `pursue.py` would only hide it. — Cost if wrong: none found. Nothing else calls `Pursuit.of` in chat (`application/execution/pursuits.py` is the operator-pressed pursuit and stays).
- Ruling: a standing run is the last run the thread names, looked up in `workflow_runs` (the runtime's runs). A skill `Run` from the older L1 path is not treated as standing. — Chat's skill runs are answered synchronously (`_answer_now`), so they never stand. — Cost if wrong: a long-running skill run's thread would still fall through to today's behaviour.
- Ruling: the status line is written with **no decision**. — A decision (even `kind: status`) would become the "last thing asked" for `asked_under` and `_awaiting`. That would take the offer or question away, so a following "yes" would start nothing. Teaching every reader to skip a new kind is an exception set. — Cost: the conversation route's attempt log records the turn as `nothing` ("nothing was made of what was said"), because it reads the last message's `kind`.
- Ruling: under a question `execute` routed here, the status answer is the question asked again, which is two messages, not three. — The re-asked question already says what is being waited on ("I am still waiting on this one." / "Nothing back from … yet."). A separate status line above it would say the same thing twice. — Cost if wrong: that answer doesn't list the values already held. `of_the_question` does, and could replace the re-ask later if wanted.
- Ruling: `test_asking_for_a_different_job_is_still_heard` changed its reader fake to place the named job instead of raising. — With a reader that names no job, the brief's rule makes the sentence a status question, and the old assertion (a third, "Nothing has been taught" message) is the behaviour F2 removes. The test's point, that a request for a different job is heard, is kept with a reader that names it. — Cost if wrong: none to behaviour. The status case is covered by the new tests.

## Concerns

1. **The console's explore card still appears under a status line.** `frontend/src/features/console/console.tsx` `ChatTurn` draws `PursuitCard` ("work it out on the screen") under **every** assistant message without `matched_skill_id` when a connection exists. That includes job offers, questions and now the status line. It only offers the button and never explores by itself, but the operator would still see an explore offer under "check now". It is out of F2's backend scope, and no frontend `node_modules` exist here to run vitest. Proposed patch: render `PursuitCard` only for the resolver's own nothing-taught decision, for example `!decision.matched_skill_id && !decision.kind && message.decision && Object.keys(message.decision).length > 0`, with a vitest. That is a UI decision for the controller.
2. A thread whose last run id belongs to a run that has since been deleted, or that is in another tenant, is simply not standing. This is tested for tenant.
3. The attempt log records a status turn as `nothing`; see the Ruling above.
4. Concurrency: this path writes nothing but thread messages, through the existing `_only_said` / `_also_said` (whole-thread save, the same as every other chat line). It starts no run, answers no question and claims nothing, so two presses produce two status lines and no side effect. A run that ends between `_what_stands` and the write gives a status line that is one beat stale. It is words only, and the run's own result message follows.
