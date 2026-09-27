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

---

## Round 1

First merged `origin/feat/execution-runtime` (`659aa6d`) into `d2/f2` with a merge commit (`5e85238`). There were no conflicts.

Every fix below had its test written first, and each test was seen failing before the code changed.

### Fixes

- **I1: an ended run never stands.** `stands` (`domain/chat/standing.py`) is now `outcome == "running"` or a mail wait still inside its deadline. `asks_a_person` is gone from it, because an ended run's question is already the thread's `needs_values` question.
  - Tests: `test_a_run_that_ended_stands_only_while_its_mail_wait_runs` (domain), and `test_a_run_that_stopped_to_ask_is_not_standing`, where a stopped run with `needs` and a later "create a warehouse zone called Z1" gives the resolver's reply, not a status line.
- **I2: a ready lookup answers before the status line.** In `Converse._carry_on`, `_look_it_up` now runs before the `about_what_stands` branches.
  - Test: `test_a_ready_lookup_under_a_standing_question_is_answered_as_before`. It checks the `looked` decision, KKYT in the answers, and that the question is re-asked and still standing.
  - The F2 fixtures now use `_Plans(ready=False)` for the four mail and status phrases.
- **I4: the reader's own intent.** A sentence the reading confidently says "acts on a thing" (`_work_on_a_thing`: at or above the floor, `wants == "act"`, with a verb and an entity) is never a status line. It falls through to `_nothing_taught`.
  - Tests: `test_a_reading_sure_it_is_work_on_a_thing_is_never_a_status_question` (the probe) and `test_a_reading_that_is_not_sure_or_names_no_thing_is_about_what_stands` (low confidence, no entity, `ask`).
- **I3: the original fixture is back.** `test_a_sentence_nothing_places_under_a_question_is_about_the_question` uses the reader that places nothing. It asserts the decided outcome: the sentence is kept, and the question is re-asked (`needs_values`, "I am still waiting on this one. What should Customer Type…") as two messages. `test_asking_for_a_different_job_is_still_heard` keeps the placed-job case and asserts the offer text. Both docstrings are fixed.
- **M1: dead branch removed.** The unreachable question branch of `_what_stands` is deleted. `of_the_question(offered=False)` was unused, so the function is now `of_the_offer(pending)`.
- **M3: only a principal who may see the run is told about it.** The run status is read only for the thread's opener or the run's starter.
  - Tests: `test_somebody_else_asking_in_the_thread_is_not_told_the_run` (B in A's thread gets the resolver's reply, with no run values) and `test_the_starter_of_the_run_is_told_it_in_a_thread_somebody_else_opened`.
- **M5: absence tests now assert the decided reply.** The finished-run and other-tenant tests check that the reply equals the resolver's own reply for the same sentence. The finished-run test also checks `pursuable`.
- **M6: what stands is computed only when nothing was named.** `ResolveIntent.execute` now takes `standing: Callable[[], Awaitable[bool]] | None` and awaits it last: after no candidate ranked and after the reading check. `Converse` passes a closure that answers `True` at once under a question routed from `execute`, and otherwise reads the run and offer.
  - Tests: `test_what_stands_is_not_read_for_a_sentence_that_names_a_job` (zero `workflow_runs.get` calls) and `test_a_sentence_that_names_a_job_is_that_job_even_while_something_stands` (the callable is never awaited).
- **UI (controller ruling): the explore card appears only under `pursuable`.** `Resolution.pursuable` is set only in `_nothing_taught` (both returns). `_decision` then adds `"pursuable": true` to the chat decision, and only then.
  - `console.tsx` draws `PursuitCard` only when `offersToExplore(message.decision)` is true. `offersToExplore` is exported from `pursuit-card.tsx` and returns true only for `pursuable === true`.
  - `frontend/src/features/console/pursuit-card.test.tsx` covers it as a table: true for pursuable; false for a status line, an offer, `needs_values`, `run_asks`, a matched skill, which-did-you-mean, a resolver decision with no match, and no decision.
  - Backend: `test_only_the_nothing_taught_reply_offers_to_explore`, plus `decision["pursuable"] is True` in the nothing-standing tests.
- **`make types`:** run. `frontend/openapi.json` and `generated.ts` are unchanged, because `decision` is `dict[str, Any]` on the wire.

### Gates (round 1)

- Backend: `pytest tests/unit tests/contract` gave **4748 passed, 79 errors**. The errors are the same Docker-less `[sql]` and `TestFuzz` ones as round 0.
- ruff check and ruff format: clean. `mypy src tests evals`: clean (821 files). `lint-imports`: 4 kept. `check_code_notes.py`: 0 stale, 0 dead. The `_say_the_job` note that the fixer can't disambiguate was re-anchored by hand to line 640. `grep unit_of_work() interface/`: nothing.
- Frontend: `npx vitest run`, 117 passed. `npx tsc --noEmit`, eslint and prettier on the touched files: clean.

### Rulings (round 1)

- Ruling: `pursuable` is set on every `_nothing_taught` reply, including the "asks" variants ("Nobody has demonstrated reading that…" and "Show me once where you would look"). — These are the same nothing-taught fallback as the proposal and "teach me" replies. — Cost if wrong: the explore card appears under the read-only nothing-taught reply too, which is where it appeared before F2.
- Ruling: I4 does not pass through the model's `another_task`. Only the reader's `Reading` (`wants`, `verb`, `entity`, `confidence`) can move a sentence off the status line. — The brief forbids trusting the model's status call, and `Reading` is the reader's intent that controller item I4 names. — Cost if wrong: with no intent parser configured, every sentence that names no job under something standing gets the status answer.
- Ruling: M3 lets the thread's opener **or** the run's starter see the run. — This is the controller's wording. — Cost if wrong: a thread opener is told the status of a run somebody else started from their thread, which the thread already announces.

### Concerns (round 1)

- Round 0's concern 1 (the explore card) is resolved by the UI ruling.
- A thread reads its run only through the opener/starter check. A third person on the same tenant who types in the thread gets today's fallback, with the explore card offered under it (`pursuable`).

---

## Round 2

This round covers invariant 5: only the principal a question belongs to may act on it. Each change had its test written first and seen failing. For item 2 the failure was the live bug itself: B's "GGD" under A's question came back as "Running Create a Customer Type now."

### Fixes

1. **The offer is told only to the thread's opener.** In `Converse._what_stands`, the offer branch reads the offer only when the asker opened the thread. This is the same rule as the run branch.
   - Test: `test_what_stands_is_never_the_offer_for_somebody_who_did_not_open_the_thread`. For B it returns None; for A it returns the offer with its values.
2. **A standing question or offer is acted on only by the thread's opener. This bug predates F2 and is live.** `Converse.execute` used to refuse only a *press* (`answering` set) from anyone but the opener. A typed sentence with no `answering` was read against the newest question, so a colleague's value became the answer and started the opener's job, and a colleague's "yes" ran the opener's offer.
   - The check now covers every path. While `answering` is set, or a `needs_values` question or a job offer stands, anybody but the thread's opener gets `K_NOT_YOURS` ("That question was asked of somebody else, so nothing was done.") as words with no decision. Nothing reads what they said: not the answer reader, the rig or the resolver. The question or offer still stands, unchanged, for its opener.
   - Tests:
     - `test_somebody_else_under_the_opener_s_question_is_never_its_answer` covers "check now", "yes" and "GGD". The answer reader is never asked, the question still wants `Customer Type`, there is no `job` decision and no run.
     - `test_somebody_else_under_the_opener_s_offer_does_nothing_to_it` covers the same three phrases. It asserts no values in the reply, the offer still stands with its values, and no run.
     - `test_the_opener_s_own_answer_is_still_the_answer` is the guard: A's "GGD" still becomes the answer and the job decision.

### Gates (round 2)

- `pytest tests/unit tests/contract`: **4756 passed, 79 errors**. The errors are the same Docker-less `[sql]` and `TestFuzz` ones as before.
- ruff check and ruff format: clean. `mypy src tests evals`: clean (821 files). `lint-imports`: 4 kept.
- `check_code_notes.py`: 0 stale, 0 dead. The `_say_the_job` "The run goes and looks" note is ambiguous to the fixer and was re-anchored by hand to line 644 again.
- `grep unit_of_work() interface/`: nothing. No frontend change.

### Rulings (round 2)

- Ruling: for chat, the principal who may answer is the **thread's opener**, and the "run's starter" rule has no path to apply to here. — Converse never answers a run's own question (`run_asks`); that goes through the workflow-runs route, which checks its own principal. The questions that stand in chat (`needs_values` and the job offer) belong to the thread, and neither carries a run id or starter. — Cost if wrong: if a `needs_values` question in a thread opened by A was raised by a run B started, B cannot answer it in A's thread; B would answer in their own thread or through the run.
- Ruling: while a question or offer stands, the gate uses the raw `pending_job` / `offered_job`, not `_still_wanted`. — For a principal check, refusing on a question the job no longer wants is the safe direction. — Cost if wrong: in that narrow window, a colleague's unrelated request in someone else's thread is refused with `K_NOT_YOURS` instead of being handled.
- Ruling: with nothing standing, a colleague's sentence in another's thread is still handled as an ordinary request. — The item scopes the rule to "under a standing question". — Cost if wrong: see concerns.

### Concerns (round 2)

- With nothing standing, a colleague's sentence in someone else's thread still goes through `_carry_on`. Two things there come from the opener's own earlier messages: `pinned=_awaiting(thread)`, which carries on a skill the resolver was asking values for, and `_gathered`, which reuses the values already given for it. So a colleague's request can be resolved against the opener's pinned skill and values. It never runs a write (`_answer_now` refuses writes), but it is the same invariant-5 shape. If the controller wants it closed, both should key on `thread.opened_by == ctx.principal_id`. It is not changed here because it is outside the item.
