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

## Round 1

I wrote the tests first and watched them fail: 16 failed before the fix, and every one passes now.

### What changed, by item

1. **Models are kept.** A new test, `test_a_record_keeps_the_model_its_prompt_ran_on_before_it_was_a_record`, pins the model on all 14 records. Each is the default of the setting it replaced:
   - flash: plan, checks, sentence, values, sight, transcription;
   - pro: rescue, see-step, sight escalation, interpret, name, the two judges.

   `SIGHT` stays on `gemini-3.8-flash` and `TRANSCRIBE` stays on `gemini-3.8-flash`. The Rulings below explain why neither takes the `.env.example` value.
2. **Retired keys fail loudly at load.** The six keys are listed in `config.RETIRED_MODEL_SETTINGS`. A settings source (`_RetiredModelSettings`) reads the environment and the `.env` file for them, and a `model_validator` refuses the load. Pydantic reports this as a `ValidationError`, and the message reads `SRO_GEMINI_PLAN_MODEL is retired: the model now lives on the prompt record in sro.domain.prompts. …`. A validator alone was not enough, because the environment source never passes on an undeclared key. `SRO_GEMINI_EMBEDDING_MODEL` still loads normally. There are 13 tests in `tests/unit/test_retired_model_settings.py`: each key set in the environment, each key set in a `.env` file, and the embedding key.
3. **Invariant 14 applies inside an answer.** The fix is in one shared place, `Prompt.kept`:
   - A top-level **nullable** field that is present and broken, or required and missing, becomes `null`, and the rest of the answer stands.
   - A plan with an invented `action` now falls back to the operator's recorded gesture, as it did before P2. The same happens for a non-string `value` (the recorded value stands) and a non-string `url` ("navigate with no url").
   - `CHECK_*.why` is now nullable, so a verdict with no `why` keeps its verdict and gets an empty reason.
   - Fields that may not be null still make the whole answer unsure: a plan's `kind` and a verdict's `held`.
   - An absent optional field stays absent.

   Tests: `test_a_bad_nullable_field_is_dropped_alone_and_the_answer_kept`, plus the updated planner and verify tests.
4. **Parameter names are fenced.** `EXTRACT_VALUES` now receives `parameters` as its own untrusted block, a JSON list, and the input contract says the names come from page labels. Test: `test_parameter_names_are_fenced_because_they_are_page_labels`. It checks that a label containing `</untrusted>` stays inside its fence and appears nowhere else.
5. **`found` is gone from `SEE_STEP`.** It is removed from the schema's properties, required list and ordering, and "found: true/false" is removed from the four bullets and the first case. The runner test now spots sight questions by `points_at`. Test: `test_the_sight_step_asks_only_for_what_is_read`.
6. **The judge is two records.** `JUDGE_VARIANT` and `JUDGE_WORKFLOW` each carry their own old `_JUDGING` text verbatim: first paragraph as role, second as task. `JUDGES` maps each kind to its record, and an unknown kind is never asked. `kind` is no longer sent. Tests: `test_each_judgement_is_its_own_record_with_its_own_words` and the adapter test, which asks both kinds plus one unknown kind.
7. **The guard is stronger.** It now also runs an AST scan of every `.py` outside `domain/prompts/`. It fails on any string literal longer than 200 characters that contains `You are`, `Answer with`, `Return` or `Say no unless`. The name check stays. `test_the_scan_sees_instructions_under_any_name_and_passes_short_ones` proves it catches instruction text inline and under any name. I also ran the scan against the base commit `384e609`: it flags the old constants in planning, belts, computer_use, interpreter and transcription. The name check covers the three it misses (`_READING`, `_JUDGING`, intent's `_INSTRUCTIONS`).
8. **The type shim is gone.** Rungs are now plain names (`"evidence"`, `"rescue"`, `"sight"`, `"look"`, `"route"`, `"replay"`). A module-level `_ASKS: Mapping[str, Prompt]` gives each asking rung its record. `plan_step(prompt=_ASKS[how])` receives a `Prompt`, and `planned_by` takes `_ASKS[how].model` only for a rung that asks. mypy is clean. The log now reads "evidence then rescue then sight" instead of "evidence then evidence then sight".

### Rulings, round 1

- Ruling: **`SIGHT` stays on `gemini-3.8-flash`, not `gemini-2.5-computer-use-preview-10-2025`** — Five sources say flash: the `gemini_vision_model` default, runtime GC 14, the P2 brief, the settings note (which records moving off the standalone computer-use model on purpose), and `test_the_sight_lane_escalates_from_flash_to_pro_and_both_are_metered`, which is newer than `.env.example` and pins flash → pro. That test failed when I made the switch the review asked for. The `.env.example` model is also missing from `prices.py`, so every sight call would be billed at $0 and the daily cap would not see it, the same failure the settings note records for `3.7-flash`. The review's own principle, that no model changes silently, holds either way: a deployment that set `SRO_GEMINI_VISION_MODEL` is now refused at load and told where the model lives. — Cost if wrong: change one line in `sight.py`, one row in the pin test and one expectation in the runtime test, add the model to `prices.py`, and run an eval.
- Ruling: **`TRANSCRIBE` stays on `gemini-3.8-flash`**, the `gemini_transcription_model` default at the base commit, for the same reason. `.env.example`'s `gemini-2.5-flash` was an override for a deployment that copied it, and item 2 now refuses such a deployment loudly. — Cost if wrong: one line and one row.
- Ruling: **item 3 is fixed in `Prompt.kept` for every record, not only in the planner and verifier** — Invariant 14 is about how answers are validated, and every `ask` goes through `kept`. So nullable fields on other records (`READ_REQUEST.workflow_id`, `GATHER.query`/`message_id`) also become `null` when broken, instead of voiding the whole answer. — Cost if wrong: add a per-record opt-in.
- Ruling: **`CHECK_*.why` becomes nullable in the schema sent to Gemini.** This is how the schema says "a verdict without one is still a verdict". Both records are new on this unmerged branch, so they stay at `version=1`. — Cost if wrong: if the model starts leaving `why` out, reasons get thinner. The eval would show it.
- Ruling: **`PLAN_STEP.why` stays required.** The review named only the verdict, and "decide, then explain" is how the plan asks. — Cost if wrong: one schema line.

### Gates, round 1 (from `backend/`)

- `pytest tests/unit`: **4593 passed**.
- `mypy src tests evals`: clean (823 files).
- ruff check and format: clean.
- `lint-imports`: 4 kept, 0 broken.
- `check_code_notes.py`: 0 stale, 0 dead.

### Concerns, round 1

- **Any local `.env` with one of the six retired keys now stops the API and the worker at startup.** That is the point of item 2, but developers will hit it; the error names the key to remove.
- **The runner's rung names changed** ("rescue" instead of the second "evidence"). This is only visible in the log line; `test_the_ladder_narrates` still passes.
- **Restart the worker.**
