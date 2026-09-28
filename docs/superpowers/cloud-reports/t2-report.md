# T2 report: a run works across tabs inside its one lease

Base: `be57f38b` (branch `d2/t2` as handed over). `git merge-base --is-ancestor 9ee015aa HEAD` succeeds.

## Commits

- `19da615` feat(runs): a job runs across its tabs inside the run's one lease
- this report (docs)

## Files changed

Source:
- `backend/src/sro/application/ports/page.py`: `PageDriver.opened_by(session, opener, deadline_s) -> str`
- `backend/src/sro/infrastructure/steel/driver.py`: `_Link.openers/handed/arrived`, `_arrived` records `openerId`, `gone` drops it, `SteelDriver.opened_by`
- `backend/src/sro/application/runtime/broker.py`: `SessionBroker.open_tab`, `SessionBroker.opened_by`
- `backend/src/sro/domain/execution/progress.py`: `StepMark.tab` (additive JSON)
- `backend/src/sro/application/runtime/run_steps.py`: `_held(…, step, by_id)`, new `_role`, `_main` (the old `_held` body), `_holding` shared by `_keep_tab` and `_ask`, and `release` closes every tab with `main` last

Tests:
- `backend/tests/unit/fakes.py`: `FakePageDriver.popups`, `opened_by` (additive)
- `backend/tests/unit/runtime_support.py`: `steel_run(tabs=…)`, `SteelRun.page_of`, `SteelRun.rewind`
- `backend/tests/unit/application/runtime/test_a_run_across_tabs.py` (new)
- `backend/tests/browser/steel_rig.py`: `/opener` page (a `target="_blank"` link) and `/lookup` page
- `backend/tests/browser/test_the_steel_driver.py`: one new test

Code notes: `driver.py.md`, `broker.py.md`, `run_steps.py.md`, `progress.py.md`, plus line-number refreshes from `--fix` (including `page.py.md`).

## Tests added

Unit (`test_a_run_across_tabs.py`, all pass):
1. `test_a_step_in_a_popup_acts_in_the_tab_its_opener_opened`
2. `test_a_second_tab_opens_at_the_steps_own_page`
3. `test_a_popup_that_never_opens_asks_a_person_and_sends_nothing`
4. `test_release_closes_every_tab_of_the_run` (popup first, `main` last)
5. `test_a_resumed_run_returns_to_the_steps_own_tab` (`opened_by` asked exactly once)
6. `test_a_popup_whose_tab_was_lost_is_found_again_from_its_opener`
7. `test_a_new_lease_forgets_the_old_lease_s_tabs`
8. `test_a_code_asked_in_a_popup_keeps_both_of_the_run_s_tabs`
9. `test_a_tab_opened_by_an_attempt_another_one_superseded_is_closed`

Each test saw its failure first. As mutation checks I reverted single lines and watched tests fail:
- The old `_ask` tab assignment made test 8 fail.
- An unsorted `release` made test 4 fail.
- Dropping the `handed` filter in the driver made the browser test fail.
- Before the fix, test 9 failed on the leaked tab.

Browser: `test_a_popup_is_found_by_the_tab_that_opened_it_and_handed_out_once`
- **Ran here against local headless Chromium**, not Steel. `docker info` fails, so I did not run `make steel-up`.
- The pinned Playwright wants `chromium_headless_shell-1234`, but only `-1194` is installed, so the rig skips.
- To run it, I pointed `PLAYWRIGHT_BROWSERS_PATH` at a scratch directory that symlinks to the installed 1194 binary. No repo change.
- Result: passes. The whole `test_the_steel_driver.py` gives 60 passed, 1 failed. The failure is `test_the_default_context_id_never_reaches_a_default_tab` (KeyError), and it **fails identically on the base with my changes stashed**, so it comes from this older Chromium, not from T2.
- Controller: please re-run it on the pinned browser and on Steel.

Integration: none written. The brief asks for none, and T2 adds no SQL.

## Gate results (from `backend/`)

- `pytest tests/unit`: 5065 passed.
- `pytest tests/unit tests/contract`: 5171 passed, 86 errors. Every error is a `[sql]` parameter of `tests/contract/test_the_repositories_agree.py`, which needs Postgres; none is in a non-`[sql]` test.
- `mypy src tests`: no issues (842 files).
- `ruff check .`: clean. `ruff format --check .`: clean.
- `lint-imports`: 4 kept, 0 broken.
- `check_code_notes.py`: 0 stale, 0 dead.
- No wire schema change, so `make types` was not needed.

**Worker restart needed.** This touches `RunSteps`, the broker and the Steel driver.

## Rulings

- Ruling: the tests use `world.run_id` and `asyncio.Event()` where the brief wrote `world.run.id` and `world.stop`, and each test calls `prepare` and `acquire` first. — `SteelRun` has no `run` or `stop` field. Without `acquire` there is no main tab, so `_held` returns `None` and no step acts in any tab. Invariant 15: the code wins. — Cost if wrong: cosmetic.
- Ruling: the tests do not assume the main tab is `tab-1`, and the `open_tab` assertion reads the context id from the `Held` instead of hard-coding `"sess-1"`. — Acquire's own tab numbering belongs to the broker and the fake, and T2 does not own it. — Cost if wrong: none.
- Ruling: `steel_run(tabs=…)` builds real gestures (tab ids, a `popup_opened` mark carrying `opener_tab_id`) and sets each `step.tab` from `tab_roles`, the mining code, then asserts the roles are the ones asked for. — Invariant 16: input goes through the production path, not a hand-set `step.tab`. — Cost if wrong: none.
- Ruling: `reattach` is called with `holder=run.id`. — The brief's sketch left it out, but the real signature requires it, and every `Held` must name its run (see the `broker.py` note). — Cost if wrong: none.
- Ruling: the `_ask` path for `WaitingForAPerson` uses the same `_holding` rule as `_keep_tab`. The rule: a new lease forgets the old tabs; a held tab that is already one of the run's tabs keeps its role; any other tab becomes `main`. — Before, `_ask` replaced `tabs` with `{main: held}`. A one-time code asked while a step acts in a popup (`reauth` raises with the acting tab) would then make the popup `main` and drop the real main tab, which `release` would never close. That breaks "release closes every tab of the run". The brief did not name this line, but it is the same root as `_keep_tab`. — Cost if wrong: after such a code, `acquire`/`resume` checks for the code on the real main tab, not the popup (see Concerns).
- Ruling: a tab `_role` opened (`tab_N` or a popup) is closed when this attempt's progress write loses the compare-and-set. This mirrors `_keep_tab`. — Otherwise, two overlapping attempts leak a tab nobody records. — Cost if wrong: none.
- Ruling: the browser test adds `/opener` and `/lookup` routes to the rig (private `_POPUP_OPENER_PAGE` and `_LOOKUP_PAGE`, like their siblings), and uses the file's existing `rig`, `one` and `driver` fixtures for the brief's `steel_page` stand-in. It also asserts that a second tab in the same context gets no popup from `opened_by`. — Cost if wrong: none.
- Ruling: the commit trailer is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` plus a `Claude-Session` line, as this session's harness requires. The brief's sample has `(1M context)`. — Cost if wrong: the controller amends the trailer at merge.

## Concurrency story

- **Two attempts on one popup step:**
  - The first attempt takes the popup, and `handed` stops the second from taking the same tab.
  - The second attempt waits up to `K_UI_WAIT_S` and gets `PageUnsettled`, which becomes `NeedsAPerson`. Its `_ask` write then loses the compare-and-set and raises `Superseded`. No lane runs.
  - If the second attempt got a tab and lost the write, that tab is closed (test 9).
- **Crash between two steps:** tabs are in `progress.tabs` by role. A restarted worker reattaches by role, and a tab that is gone is found again by role (tests 5 and 6).
- **Stop mid-way:** `release` closes every tab, `main` last (test 4). A new lease forgets the old lease's tabs (test 7).
- **In-doubt writes:** unchanged. `_held` runs before the in-doubt check and only selects a tab. The own-call rule is per tab already (`calls_since(session, target_id, mark)`).

## Concerns

- Ceiling (noted in `run_steps.py.md`): D5 releases a run's tabs while it waits for an answer. A step in a popup after a question therefore finds no popup and asks again. The popup was opened by an earlier step that may have been a write, and a write is never repeated. Upgrade: re-run the opener step when it is a read.
- A one-time code asked inside a popup: `_holding` keeps both tabs, but `SessionBroker.resume` checks for the code on `tabs[main]`, not on the popup that asked. So the code is not re-detected on resume, and the next step's own sign-in check has to catch it. This is a rare corner, not changed here.
- `_held` now writes progress once per step, to record `mark.tab`: one extra compare-and-set per step.
- `handed` in the driver's `_Link` grows for the life of the connection (one string per popup). Small, but unbounded for a very long-lived worker.
