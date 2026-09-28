# P4 report — the repair suite

Base: `43edfd24` (the brief commit on `d2/p4`). `git merge-base --is-ancestor 9ee015aa HEAD` succeeds.

## Commits

- `636ba5f` feat(evals): the repair suite, on a live page nothing acts on
- this report

## Files changed

- Created `backend/evals/suites/repair.py`: `Repair`, `broken`.
- Modified `backend/evals/run.py`: `SUITES` is now `dict[str, Callable[[Container | None], Suite]]`, with `repair-sight` and `repair-ui` added. `run_suite` builds its suite from the map. `reachable` splits off unreachable cases, and `run_suite` passes their count to `report`. `run_ci` builds only the suites that have a `ci/<name>` folder.
- Modified `backend/evals/model.py`: `Report.unreachable: int = 0`, `report(..., *, unreachable=0)`, and `as_markdown` prints an `unreachable` column.
- Modified `backend/src/sro/application/ports/page.py`: `PageAnswer.xpath: str | None = None`.
- Modified `backend/src/sro/infrastructure/steel/driver.py`: `resolve` passes `xpath=got.get("xpath")`. Page code's `resolve` already returned `xpath`.
- Modified `backend/src/sro/application/runtime/sight_lane.py`: `_goal` is now the public `sight_goal`, with its caller updated.
- Modified `backend/tests/unit/fakes.py` (additive): `FakePageDriver(resolved=...)` also takes a sequence of answers. They are handed out in order and the last one repeats. The single-answer form is unchanged.
- Modified `backend/tests/unit/runtime_support.py`: `scripted_driver(resolved=...)` accepts the same sequence.
- Created `backend/tests/unit/evals/test_the_repair_suite.py`.
- Code notes: created `docs/code-notes/backend/evals/suites/repair.py.md` and added `_repair` and `reachable` to `run.py.md`. `check_code_notes.py --fix` moved the anchors in `model.py.md`, `page.py.md` and `driver.py.md`. `sight_lane.py.md` had no `_goal` heading, so there was nothing to rename.

## Tests added (unit, all run and passing)

`tests/unit/evals/test_the_repair_suite.py`, 16 tests:
- The brief's three: UI repair passes on the held control with nothing acted; a page without the recorded control is unreachable; a sight point that resolves back to the held control passes.
- UI repair that names another control is sure and wrong.
- A control found by a surviving locator (`matched_by="text"`) is not a repair.
- The recorded control is resolved without `write: false`, so page code cannot repair it. The broken payload carries `write: false` and `learned: None`.
- `broken` keeps only what repair scores by. The test is built through the real `ui_payload`.
- A sight point is resolved back through the hit's own `{strategy, query}` and `frame_path`.
- A model that names no point is unsure, not unreachable.
- The lease is released even when the page goes (`PageGone`).
- `cases`: only held jobs count; a step needs an xpath and a `page_url`; `repair-ui` skips a writing step. Input is built through a `FakeUnitOfWork` with a real `WorkflowRun`, `Gesture` and `Call`.
- A case carries the lane's own `ui_payload` and `sight_goal`.
- Unreachable cases are counted and left out of the measure, and the markdown shows the count.
- The repair suites are registered by name, and a repair suite refuses to build without a container.
- CI skips a suite with no committed folder, so the repair factory is never called offline.

Mutation check: I broke each rule in `repair.py` in turn, and the matching test failed each time. The five mutations were: keep `text`, drop the `matched_by == "repair"` check, keep `write` on the recorded resolve, skip the unreachable check, and skip `release`.

Integration and browser tests: none written. The brief asks for none, and the live measurement is the controller's Step 5.

## Gates

- `uv run pytest tests/unit tests/contract -q`: **5179 passed, 86 errors**. All 86 errors are `tests/contract/test_the_repositories_agree.py::...[sql]` parametrizations, which need Postgres. No Postgres is available in the cloud.
- `uv run mypy src tests evals`: Success, no issues in 852 source files.
- `uv run ruff check .`: all checks passed. `uv run ruff format --check .`: 965 files already formatted.
- `uv run lint-imports`: 4 contracts kept, 0 broken.
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead.
- `docker info`: not available, so Steel and `tests/browser` were not run.

## Rulings

- Ruling: `broken` also drops `text` and the `name`/`autocomplete`/`id` attributes, beyond the brief's `css_path, xpath, test_id, component` — Why: page code's `find` tries those direct strategies (`text`, `attributes`) before repair. With them left in, a typical tab or button case is found by its text, `matched_by="text"`, and scores as sure-but-wrong. The suite would then be measuring that locator, not repair. Dropping them costs repair nothing, because repair runs only after every direct strategy found nothing, so any score it could have drawn from them is unreachable anyway. The other keys (`role`, `tag`, `landmarks`, `bounds`, other attributes) are kept — Cost if wrong: the UI numbers are lower than under the brief's version on pages where text would have "found" the control. Restoring the brief's list is a one-line change.
- Ruling: the recorded control is resolved with `write` removed, and the brief's `payload["write"] = False` in `cases` is gone. The case payload is exactly `ui_payload`'s — Why: page code repairs only when `payload.write === false`. Forcing `write: false` would let the "truth" resolve be a repair itself, and would mislabel writing steps in the sight suite. `repair-ui` keeps only reads, whose `ui_payload` already carries `write: false` for the broken resolve — Cost if wrong: none found. A case whose recorded control holds only by repair becomes unreachable, which is correct.
- Ruling: `SUITES` is `Callable[[Container | None], Suite]`, not `Callable[[Container], Suite]` — Why: `run_ci` offline has no container, and mining and reader need none. `_repair` raises `SystemExit` when given `None`, so the repair suites cannot be built without a live stack — Cost if wrong: one type annotation.
- Ruling: `Repair.asker` returns `Replayed(None)`, an inert asker — Why: `run_suite` refuses to run when a suite's asker is `None`. That refusal is right for mining and reader, but repair asks nothing: `repair-ui` needs no model, and `repair-sight` uses the `VisionDriver`. Making run_suite's check aware of each suite would widen the `Suite` protocol for one case — Cost if wrong: none at run time, because `Repair.run` never calls the asker. The `vision is None` refusal for `repair-sight` fires on the first case, after the case set is built.
- Ruling: `Scored.sure` for sight is True when the model named a point, even if `hit_test` found no locatable element there. It is False only when the model named no point — Why: the brief says sure means "the lane named a control at all", and a point is the model naming one — Cost if wrong: that edge moves between sure-but-wrong and unsure.
- Ruling (invariant 15, where brief and code disagree): the brief's `_goal` is at `sight_lane.py:391` and `resolve` is at `driver.py:548`. The code matched the brief's signatures (`acquire(..., *, holder, park=True)`, `propose(..., allowed: tuple, history: tuple)`, `ui_payload(step, gesture, value, learned, by_id)`).

## Concerns

- **Repair is unlikely to score well once the name changes.** `REPAIR_THRESHOLD = 3`, and a renamed control earns no name points: live `"Orders"` does not contain `"Orders (renamed)"`. The only points left are the chain (dropped with `component`), the placeholder and name attributes, and bounds. Expect a low `repair-ui` accuracy. That is a true reading of the heuristic under this breakage, not a suite bug, but whoever reads the numbers should know the rename is the hardest breakage for it.
- **Cost is reported as `0.0`.** `VisionDriver` does not return cost, so the metered client books it to `model_spend`, and the cost gate is inert for the repair suites.
- **Unreachable pages.** Any step whose page is reached only through earlier steps (a dialog, a row opened from a search) is unreachable, because the case opens `page_url` cold. The count may be high. The noted upgrade is to replay the job's reads up to the step on the eval lease.
- **The eval lease.** `run` holds the account's own lease (`holder=eval:<case>`) and always releases it, as the brief's Step 5 assumes ("worker stopped"). A run started with the worker up would compete for the same account's lease.
- **No unit test covers `SteelDriver.resolve` carrying `xpath`.** No unit test drives `SteelDriver` against a page. The one-line change is exercised only by the live eval.
