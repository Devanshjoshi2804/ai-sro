# P2 report: the remaining prompts become records

Branch `d2/p2`, cut from `feat/execution-runtime` at `384e609`.

## Commits

- `7767a4d` feat(prompts): plan, sight, check, intent, interpret and transcribe prompts are records
- (this report) docs: P2 cloud report

## Files changed

**New records** (`backend/src/sro/domain/prompts/`):
- `plan_step.py`: `PLAN_STEP`, `PLAN_STEP_ESCALATED`
- `see_step.py`: `SEE_STEP`
- `check_step.py`: `CHECK_SCREEN`, `CHECK_WAY_THROUGH`
- `read_sentence.py`: `READ_SENTENCE`, `EXTRACT_VALUES`
- `sight.py`: `SIGHT`, `SIGHT_ESCALATED`
- `interpret.py`: `INTERPRET`, `NAME_SKILL`, `JUDGE_SKILL` (plus `JUDGED`, the two kinds it answers)
- `transcribe.py`: `TRANSCRIBE`

**Source changes:**
- `domain/execution/planning.py`: `PLAN_SCHEMA`, `PLAN_INSTRUCTIONS`, `SIGHT_SCHEMA`, `SIGHT_INSTRUCTIONS` and `SIGHT_ACTIONS` deleted.
- `domain/execution/belts.py`: `SCREEN_SCHEMA`, `SCREEN_INSTRUCTIONS` and `WAY_THROUGH_INSTRUCTIONS` deleted.
- `application/execution/plan_step.py`: `plan_step` and `plan_by_sight` ask through `ask`, with the evidence JSON as one untrusted block. `plan_step` swaps `model`/`effort` for `prompt: Prompt = PLAN_STEP`, and `plan_by_sight` loses `model`. The checks the schema now makes are deleted: kind not in `KINDS`, action not in `SIGHT_ACTIONS`, and the `found`-only fallback.
- `application/execution/verify.py`: asks `CHECK_SCREEN` or `CHECK_WAY_THROUGH` through `ask`. The `model` parameter is gone.
- `application/execution/run_workflow.py`: loses `plan_model`/`rescue_model`. Rungs are now `(how, Prompt | None)`: evidence `PLAN_STEP` → evidence `PLAN_STEP_ESCALATED` → sight `SEE_STEP`, and the looks use `SEE_STEP`.
- `application/execution/workflow_runs.py`: `StartWorkflowRun` loses `plan_model`/`rescue_model`.
- Adapters: `GeminiVisionDriver(prompt, *, client)`, `GeminiIntentParser(*, client)`, `GeminiInterpreter(*, client)` and `GeminiTranscriber(*, client)` all build their request from `record.instructions`, `record.evidence(...)`, `record.model` and `record.output_schema`. `destination` is now `f"gemini:{self._prompt.model}"`.
- `container.py`: `sight_lane` uses `GeminiVisionDriver(SIGHT_ESCALATED, …)` and `_build_vision` uses `GeminiVisionDriver(SIGHT, …)`. `perform_with_vision` and `pursue_goal` take `SIGHT.model`. `start_workflow_run` and the three builders no longer pass models.
- `config.py`: deleted the six model settings. `gemini_embedding_model` stays.
- `backend/.env.example`: deleted the three model variables.
- Renamed three constants that are not prompt text, so the guard test sees them correctly (see Rulings): `domain/skill/signing_in.py` `_PROMPT` → `_ASKS_FOR` (named in the brief), `application/chat/from_the_mail.py` `K_READING` → `K_READ_TOOL`, `application/intent/pursue.py` `_READING` → `_ASKING_OPENINGS`.

**Tests:**
- New files: `tests/unit/test_no_prompt_text_outside_the_records.py` and `tests/unit/infrastructure/test_the_adapters_ask_from_their_records.py`.
- Edited: `test_prompt_records.py`, `test_planner.py`, `test_runner.py`, `test_verify.py`, `test_planning.py`, `test_start_workflow_run.py`, `test_a_mail_job_is_written_not_clicked.py`, `test_a_job_on_a_clock.py`, `test_every_model_call_is_metered.py`, `test_refusals.py`, `test_workflow_runs_route.py`, `test_lookups_route.py`, `fakes.py`, and two integration tests.
- `fakes.py` gains `fenced_block` and `fenced_json`, which read the fenced evidence the planner and verifier now send.

**Code notes:**
- Seven new notes files, one per new record module.
- The notes on deleted constants and settings moved into the notes for their records.
- `computer_use.py.md` says why the escalation is a second record.
- Updated stale references in `run_workflow`, `workflow_runs`, `container`, `verify`, `plan_step`, `planning`, `config`, `mine` and `read_gesture`.

## Tests added

Unit tests (all run, all pass):
- `test_no_prompt_text_lives_outside_the_prompt_records`: the brief's test. It failed first with 9 offenders: the brief's 7 plus `from_the_mail.py` and `pursue.py`, see Rulings.
- `test_prompt_records.py`: all 13 new records join `RECORDS`, so `test_every_prompt_is_a_whole_record` and the unique-name test cover them.
- `test_the_adapters_ask_from_their_records.py`, 4 tests. They check that each adapter asks on its record's model with its record's instructions, and that untrusted text gets a fence it cannot close:
  - the vision driver's goal and history;
  - the intent parser's sentence and request;
  - the interpreter's evidence, first and second.

  They also check that `extract` adds one property per parameter to a copy and never changes the record, and that the judge never asks for an unknown kind. I proved the fence test catches a break by removing the fence from the vision driver's goal on purpose. The test went red, and I then restored the code.
- `test_refusals.py::test_the_model_names_are_the_rigs` now pins the flash and pro models on `PLAN_STEP` and `PLAN_STEP_ESCALATED`, not on settings.
- Existing tests that recorded a behaviour the schema now decides were updated to assert the new outcome, which is an unsure answer (kind `none` or verdict `unclear`). This covers a kind outside the enum, an action a point cannot take, a non-string value or url, and a missing `why` or `points_at`.
- Deleted `test_an_older_answer_with_no_enum_still_means_what_it_meant`. It tested the `found`-only fallback, which was removed because it could no longer be reached.

Integration: I wrote none. The two integration files I touched only lost their `plan_model=`/`rescue_model=` lines. **Written, not run:** `tests/integration/test_workflow_run_repositories.py` and `tests/integration/test_runs_on_local_steel.py`.

## Gate results (from `backend/`)

- `uv run pytest tests/unit -q`: **4559 passed**.
- `uv run pytest tests/unit tests/contract -q`: 4655 passed and 79 errors. Every error is a contract `[sql]` variant that needs Docker, and there is no Docker daemon here. None is a failure. They fail the same way on the base.
- `uv run mypy src tests evals`: no issues in 822 files.
- `uv run ruff check .` and `uv run ruff format --check .`: clean.
- `uv run lint-imports`: 4 contracts kept, 0 broken.
- `uv run python scripts/check_code_notes.py`: 0 stale anchors, 0 dead notes.
- `uv run python -m evals ci`: "no committed cases under evals/ci", so the offline set guards nothing yet.

## Rulings

- Ruling: **`SEE_STEP.model` is `gemini-3.1-pro-preview`, not the `gemini-3.8-flash` the brief lists** — The brief also says each record's model is "the defaults of the settings they replace". The runner asked the sight rung and its looks on `rescue_model`, whose default is pro. Global invariant 15 says the code wins when a brief and the code disagree. Moving to flash is also a model change, which rule 9 says needs its own `make eval`. — Cost if wrong: one line and a version bump on `see_step.py`, plus an eval.
- Ruling: **the evidence rescue survives as a record, `PLAN_STEP_ESCALATED = replace(PLAN_STEP, name="plan_step_escalated", model="gemini-3.1-pro-preview")`, and `plan_step` takes `prompt: Prompt = PLAN_STEP`** — The brief drops `plan_model`/`rescue_model`, but the runner climbs flash → pro → sight. `test_runner.py` pins that climb (for example `[FLASH, PRO]` and "Pro was never asked"). Losing it would silently change which model rescues a live warehouse step. I followed the same pattern as `SIGHT_ESCALATED`. — Cost if wrong: if the controller wanted the escalation gone, delete the record and the middle rung. The escalation tests in `test_runner.py` then say what changed.
- Ruling: **`K_READING` → `K_READ_TOOL` and `_READING` → `_ASKING_OPENINGS` were renamed as well as `_PROMPT`** — The brief's regex also matches them, and neither is prompt text: one is a lease tool name, the other a tuple of sentence openings. The brief's own principle for `_PROMPT` applies: "the name was wrong, not the test". — Cost if wrong: two private renames to revert.
- Ruling: **the checks the schema now makes were deleted, not kept as dead code** — `ask` validates every answer against the record's schema (rule 10), so the following could no longer be reached: `kind not in KINDS` in `plan_step`, `action not in SIGHT_ACTIONS` and the `found`-only fallback in `plan_by_sight`, and the `SIGHT_ACTIONS` constant. The no-workarounds rule says to delete a dead path, not keep a test green around it. `ACTIONS` stays, because `action` is nullable and `None` still falls back to the recorded gesture. — Cost if wrong: three small guards to restore.
- Ruling: **`JUDGE_SKILL` is one record holding both `_JUDGING` texts verbatim, each labelled by its `kind`, with `kind` passed as trusted JSON** — The brief names one record, but the source is a dict of two texts that share no first paragraph. So the role is one new sentence, and the task holds the two texts under "When `kind` is …". `JUDGED = ("variant", "workflow")` keeps the old rule that an unknown kind is never asked. — Cost if wrong: split into `JUDGE_VARIANT` and `JUDGE_WORKFLOW`, about 20 lines.
- Ruling: **`SIGHT`'s task also takes the adapter's closing line "Answer with one gesture. Coordinates are 0-1000…"** — That line was prompt text sitting in the adapter, and the spec says "no prompt text lives in an adapter". — Cost if wrong: none in practice; it is one sentence.
- Ruling: **the adapters send `[record.instructions, record.evidence(trusted, untrusted), …]`**, the same envelope `ask` uses — This fences the untrusted parts: goal, history, visible controls, sentence, request, context, evidence, and the first and second task. The interpreter's old `EVIDENCE` / `FIRST` / `SECOND` labels became fence names. — Cost if wrong: the wording each model sees changes, which the first live eval measures.
- Ruling: **the adapters do not run `conforms` on their answers** — The brief did not ask for it, and each adapter already parses defensively and turns a bad shape into an empty reading. — Cost if wrong: rule 10 is not yet enforced at those four adapters. See Concerns.
- Ruling: **the commit trailer is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` plus a session line**, from the session's attribution instruction rather than the brief's `(1M context)` form. — Cost if wrong: the trailer text.

## Concerns

- **The words sent to the model changed for every moved prompt, not only its location.** `Prompt.instructions` adds the input contract, the rules (including the untrusted rule) and the cases. `evidence()` fences the JSON and repeats the task after it. The brief asked for this shape, and every record is at `version=1`. However, rule 9 treats a text change as needing a `make eval` report. **LIVE EVAL:** the user should run `make eval` before merge, above all the repair suite for `PLAN_STEP`, `SEE_STEP` and `CHECK_*`.
- **The schema now rejects answers that used to be tolerated.** Examples: a verdict with no `why`, a sight answer with no `points_at`, and a plan whose `value` is a number. Each is now unsure, not acted on. This is rule 10 working, but a model that often leaves out an optional-looking required field will now fail steps that used to pass. Watch `unclear` and `none` rates after deploying.
- **Rule 10 is not yet enforced at the four adapters** (vision, intent, interpreter, transcriber), because they call the SDK directly rather than through `Asker`/`ask`. Routing them through `ask` needs the `Asker` port to carry computer-use and audio parts, which is a port change and out of scope.
- **Behaviour removed:** the `effort` parameter on `plan_step`, which no caller set, and the `found`-only fallback in `plan_by_sight`.
- **Deployments must drop the old variables:** `SRO_GEMINI_{PLAN,RESCUE,VISION,INTENT,INTERPRETER,TRANSCRIPTION}_MODEL` in a local `.env` are now ignored (`extra="ignore"`), not errors. A deployment that pinned one of them will silently run on the record's model instead.
- **The worker must restart:** this touches the runner, the planner, the verifier and the sight lane's drivers, which all run in the worker.
- No migration and no new dependency.
