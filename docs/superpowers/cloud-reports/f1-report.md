# F1 report: chat asks once for everything it needs, and "don't have X" is final

Branch `d2/f1`, cut from `origin/feat/execution-runtime` at **`1149c110`** (`1149c1102071a73fe402a119b2312572ca18d9e0`).
`git merge-base --is-ancestor 340136b4 HEAD` succeeds, so R2 is in the base.

## Commits

- `f9c4f60` feat(chat): ask once for every required field; "don't have X" is final
- (this report) docs: F1 report

## Files changed

- `backend/src/sro/domain/chat/asking.py`:
  - `Pending` gains `options`, `dropped`, `without` and `refused`. `ready` is now false while `without` names anything.
  - `question` puts every missing required field in one question, each with its limits and options. With one field it keeps the old wording. Two spellings of one field (`_twins`) are asked for once.
  - New `asks` returns the question's shape: `[{name, max_length, options}]`.
  - New `asking_state` holds what a NEEDS decision carries beyond the old keys: `asks`, plus `offered`, `dropped` and `options` when they are non-empty.
  - New `cannot_without` writes the note that ends the ask. New `turned_down` says why a value was refused.
  - New `still_to_ask(pending, messages)` applies what the thread already settled for this job: fields that were dropped, and fields that were already offered.
  - `answered` now:
    - takes every `Name: value` / `=` / `:-` in one reply, the offered fields included;
    - checks each value on its own with R1's `refusal` (quote, limits and options, logins);
    - drops "don't have X", "skip X", "leave out X", "without X" and "run with what we have";
    - still binds a bare reply to the first field the question listed.
  - New `named_in`. `too_long_for` now measures only a bare reply.
  - `pending_job` reads `options` and `dropped` back from the decision.
- `backend/src/sro/domain/chat/is_it_an_answer.py`: `said_as_the_value` and `K_SAID_AS` are deleted. `named_in` replaces them, and they had no other caller.
- `backend/src/sro/application/chat/converse.py` (kept minimal; no status or principal edits):
  - `_is_it_an_answer` uses `named_in`.
  - `_answer_the_question` ends with `cannot_without` when a required field is dropped. It says `turned_down` before the re-ask, and carries `dropped` and `asking_state` forward.
  - `_ask_it_again` carries `asking_state`.
- `backend/src/sro/application/execution/workflow_runs.py` (`_ask_for_values`):
  - options come from C2's `field_classes`;
  - `still_to_ask` runs against the operator's current thread, which is the one `SayWhatHappened` writes to;
  - a required field that was dropped gets a note instead of a question;
  - the decision carries `asking_state`.
- `backend/src/sro/application/chat/about_an_offer.py`:
  - `_also_settable` becomes `_only_required`. Optional names are taken out of `missing`, an optional value the box will not take is dropped from `values` (and then offered), and `offered` is computed there.
  - Then `still_to_ask` runs against the thread. A required field that was dropped ends with the note.
  - The decision carries `asking_state`.
- Code notes: `asking.py.md`, `is_it_an_answer.py.md`, `converse.py.md`, `workflow_runs.py.md`, `about_an_offer.py.md`. Two sections were reordered into source order so that duplicate `Code:` lines resolve. Anchors were fixed with `--fix`.

## Tests added

Unit (all run, all pass):
- `tests/unit/domain/chat/test_asking.py` (11 tests):
  - every required field in one question, with its limits and options;
  - an optional field is never asked for;
  - two required fields answered in one reply;
  - each value is read with its own checks (the bad one is refused, the good one kept);
  - an offered field can be filled in the same reply;
  - **the thr_c563 shape**: Department, then "Customer Type: RRF. i dont have manufature just run whatever we have", then no re-ask;
  - a misspelt name is still dropped ("manufature", "skip Manufacturer", "run without the manufacturer");
  - "skip the queue at dock 4" is a value, not a drop;
  - a required field the operator does not have ends with a note;
  - the drop and the offer ride the thread, scoped per job (`still_to_ask`);
  - `dropped` and `options` survive the stored decision.
- `tests/unit/application/test_converse.py` (5 tests):
  - thr_c563 end to end (a named answer never goes to the model reading);
  - two required fields answered in one reply;
  - what is still missing is asked again together, with `asks`;
  - a required field the operator does not have ends with a note, and `pending_job` is `None`;
  - invariant 4: a second press under a question the note closed is refused (`K_CLOSED`).
- `tests/unit/application/rig/test_start_workflow_run.py` (3 tests):
  - a run short of two values asks for both in one question;
  - fields already offered in the thread are not offered again;
  - a required field dropped in the thread ends with a note.
- `tests/unit/application/rig/test_a_job_declares_its_fields.py` (2 tests):
  - an optional field is never asked for, even when its value is too long for the box;
  - a required field dropped in this thread is not asked for again.

Existing tests changed, and why:
- `test_converse.py::test_the_answer_to_a_question_is_taken_as_the_answer`: the exact decision now includes `asks`.
- `test_reading_a_request.py::test_a_chat_answer_that_is_a_sign_in_name_is_not_taken`: `answered` now records `refused`, so the test checks values and missing plus the reason instead of whole-object equality.
- `test_is_it_an_answer.py`: the five `said_as_the_value` tests now make the same claims about `named_in` / `answered`.
- `test_a_job_declares_its_fields.py::test_the_question_carries_the_limit_before_anybody_has_overflowed_it`: the fixture's Customer Type is now marked required (`Customer Type*`). Unmarked, it is optional, so it is offered rather than asked.

Integration: none. This task touches no SQL.

## Gate results

- `uv run pytest tests/unit tests/contract -q`: **4861 passed, 83 errors**. The 83 errors are the `[sql]` contract params, which need Postgres. The base commit gives the same 83 errors (4840 passed there).
- `uv run mypy src tests evals`: no issues (837 files).
- `uv run ruff check .` and `uv run ruff format --check .`: clean.
- `uv run lint-imports`: 4 kept, 0 broken.
- `uv run python scripts/check_code_notes.py`: 0 stale, 0 dead.
- `grep -rn "unit_of_work()" backend/src/sro/interface/`: nothing.
- No wire schema change: decisions are free-form JSON, and `tests/contract` passes, including the committed-schema check.
- **Worker restart needed**: `StartWorkflowRun._ask_for_values` runs in the worker after a run.

## Rulings

- Ruling: a bare reply to a question for several fields fills the first field listed — this keeps the one-field behaviour every existing surface and the model reading (`IsItAnAnswer`, which is asked about `asking_for`) rely on, and the rest are asked again together — cost if wrong: an unlabelled value can land in the first field when the operator meant another. The question tells them to "Say them as Name: …", and named values are always placed by name.
- Ruling: "run with what we have" / "whatever we have" drops everything this ask still wants that the same reply did not fill, required fields included, so a required one ends the ask with the note — the brief says a refused required X ends with a note and never loops — cost if wrong: an operator who meant "only the optional ones" has to ask for the job again. Values named in the same reply are kept, because drops are read after them.
- Ruling: drops are scoped per thread **and per job** (`workflow_id`) — X is a field of a job, and another job's "Customer Type" is another field — cost if wrong: a field dropped for one job is asked again for a different job in the same thread.
- Ruling: "offered once" means offered once per thread per job. `still_to_ask` leaves out optional fields any earlier decision in the thread already offered. Offered fields stay on the NEEDS decision (`offered`) so a later reply can still fill them, but they are never offered in words again — cost if wrong: an operator who ignored the offer is not reminded later in the same thread.
- Ruling: a misspelt name counts as that field when `difflib.SequenceMatcher` ratio ≥ 0.8 (thr_c563's "manufature" scores 0.91), or when the normalised names are equal or one ends with the other. Stdlib only, no dependency — cost if wrong: two fields spelt within a letter or two of each other could both be dropped by one typo. The upgrade path is R2's per-job aliases (noted in `asking.py.md`).
- Ruling: `AskAboutTheOffer` treats a name as optional only when the job's own parameters say so (`offerable(..., {})`, i.e. not `demanded`). This is the same rule `Converse._still_wanted` already applies when it reads an answer. A job it cannot read keeps the card's `missing` unchanged — cost if wrong: none new, because the old path asked in exactly that way.
- Ruling: options are filled in wherever the data is at hand: the run's ask, from C2's `field_classes`, and any decision read back. `AskAboutTheOffer` carries only what its caller sends, because it loads no gestures — cost if wrong: a card-started ask shows limits but not options until the panel sends them. Design 3's form reads `asks`, whose `options` list is then empty.
- Ruling: the brief says `domain/chat/asking.py` `answered` (around :301) and `application/runtime/workflow_runs.py` (around :424-436). The code is at `application/execution/workflow_runs.py` (`_ask_for_values`, :424-466 on the base). The code wins (invariant 15).

## Invariants and concurrency

- Invariant 4 (an answer acts only on its own question, first answer wins): unchanged. `_answer_the_question` still re-reads under `get_for_answer` and compares `asked_under(..., answering)` with the asked id. The new note is an assistant decision like any other, so it closes its question. Tested: a second press under a closed question is refused.
- Invariant 5 (principal): not touched. `answering` by anyone other than the thread's opener is still `K_NOT_YOURS`.
- Invariant 9 (no read-modify-write of a whole JSON column): the asking state is appended as new message decisions through `thread.say`, never written back into an earlier message.
- Invariant 14 (validate by the natural unit): each value in a reply is checked on its own. Tested: `test_each_value_in_one_reply_is_read_with_its_own_checks`.
- Two presses or two panels: the first answer wins, and the second gets `K_CLOSED`, as before.
- A crash between steps: the drop lives on the committed decision, so it survives a restart and a second browser sees it.
- A stop mid-way: no run writes here. The note starts nothing.
- One narrow window: `_ask_for_values` and `AskAboutTheOffer` read the thread before `SayWhatHappened` appends. A drop committed in between could let a just-dropped optional field be offered once more. It writes nothing external, and the next ask sees the drop.

## Concerns

- F2 (on `d2/f2`) also edits `converse.py`. My edits there are confined to the `_is_it_an_answer` named check and the answer and re-ask decisions and text in `_answer_the_question` / `_ask_it_again`. Status handling and the principal check are untouched, so a merge conflict, if any, should be textual.
- `from_the_mail.py` still writes its own NEEDS decision without `asks` or `dropped`. It uses only `question()`, which now lists every required field. Mail cannot answer a field question (invariant 7), so this task leaves it alone. Design 3 may want `asks` there too.
- The drop wording is a fixed English pattern set (`K_NOT_HAD`, `K_WHAT_WE_HAVE`). A phrasing outside it goes to the existing model reading, as before, and is not dropped.

## Round 1

Fix round against the review findings as the controller listed them. `task-F1-review.md` itself is not in the repository, so the list in the controller's message was the source.

### Commits

- `f0b95bf` Merge origin/feat/execution-runtime (F2) into d2/f1. Base `0348e05d`.
  - `converse.py` imports: `named_in`, plus F2's `of_the_offer` and `from sro.domain.chat.standing import last_run, of_the_run, stands`. `said_as_the_value` and `K_A_LOGIN` stay dropped; `grep said_as_the_value` finds nothing.
  - `test_converse.py`: F2's file, plus F1's `asks` line, plus F1's whole section appended.
  - Code notes, hunk by hunk: hunks that differed only in line numbers took HEAD. F2's new `_what_stands` and `_carry_on` notes are kept, and its duplicate `if placed.cannot_run:` note was dropped. Then `--fix`.
  - All gates were green at the merge.
- (this commit) fix(chat): F1 round 1, covering C1–C3, I1–I4, M1 and M3, plus this report.

### What changed

- **C1** (`domain/chat/asking.py`: `K_DROP`, `K_WITH_WHAT_WE_HAVE`, `K_HOLDING`, `_read`):
  - Only four phrases drop a field: "don't have X", "skip X", "without X" and "run/go with what(ever) we have". The last one must start with a verb.
  - "don't know", "let me check", "not yet" and a bare "skip it" drop nothing and take nothing, so the field stays asked.
  - A question (`is_a_question`) is not parsed at all. Neither `named_in` nor a drop fires for another task or a lookup, so those go to the reader (`IsItAnAnswer`).
- **C2** (`_field`, `_score`, `K_LIKE`, `K_MARGIN`):
  - An R2 alias or a label of the job's own field classes wins outright, via `request.field_of`. After that, an exact normalised name wins.
  - Otherwise a fuzzy match counts only when it is word by word, with the same word count, and only when exactly one field scores ≥ 0.8 and beats the runner-up by ≥ 0.1.
  - Anything else asks which field was meant (`Pending.which`, rendered by `turned_down`).
  - The ends-with rule is gone everywhere: `_alike`, `_twins`, `_shares` and `_distinct` are deleted, so the twin fill is gone too.
- **C3**: with more than one field missing, a bare reply is not taken unless it is an allowed option of exactly one of those fields. Otherwise the ask is repeated with "I could not tell which field … is" and the "Name: …" form. With one field missing, a bare reply is taken as before.
- **I1** (`Converse._still_wanted`): the waiting ask now carries `known`, a `Candidate` built from `field_classes(job, {}, {})` and `alias_map(aliases_for(...))`. `known` is not persisted. The required set now comes from the same `FieldClass.kind`.
- **I2 / M3**: a value ends at a comma, semicolon, full stop or " and ". A drop phrase also ends it, but only when that phrase names a field. A "Name:" label counts only at a clause start.
- **I3**:
  - `AskAboutTheOffer` no longer reads the thread: every card, "yes" or new request is a fresh ask.
  - `still_to_ask` continues only the ask whose answer started this run. The structural link is that the thread's latest decision for the job is a `resume` decision whose values equal `run.values`. In that case the ask's drops hold and nothing is offered again.
  - The note says how to restart: "When you have it, ask for <job> again."
- **I4** (`workflow_runs._ask_for_values`, `_no_longer_waiting`): the run-side note now reads "<job> stopped — it needs X to run…", and the run's `needs` and `awaiting` are cleared so it is not counted as waiting on a person.
- **M1**: the note's decision keeps `values`.

### Tests

**Invariant 16:** every F1 converse and run-side test now builds its ask through the real writers. `AskAboutTheOffer.execute` writes the NEEDS decision, `Converse.execute` answers it, and the run carries the values from that answer's `resume` decision. The hand-built `_asked_for` helper, the hand-built thread decisions and the thread-wide-drop tests are deleted, since I3 replaces that behaviour.

**Test first:** the new tests were run against the pre-fix tree (`f0b95bf`), where 20 of them fail. All pass now.

Unit tests added or rewritten:
- `test_asking.py` (domain probes):
  - C1: "let me check what we have", "also check what I have in stock for SKU 12", "I don't know the department yet", "skip it" and "not yet" drop nothing and go to the reader;
  - C1: each explicit drop phrase works;
  - C2: exact name beats near name ("don't have customer tier"); "ship from code" is never Ship To Code; "don't have code" never drops Zip Code and asks which; "Code: 123" never fills Zip Code; a tie is never settled by guessing; "manufature" still drops Manufacturer;
  - C3: an unlabelled reply to two fields is not taken, unless it is an option of exactly one; one missing field is unchanged;
  - I1: a label and an alias resolve;
  - I2: "Customer Type: RRF i dont have manufacturer" and "Customer Type: RRF, create it without discount";
  - M3: a label inside a value stays part of the value;
  - M1: the note keeps its values;
  - I3: `still_to_ask` continues only its own ask.
- `test_converse.py`:
  - thr_c563;
  - two required fields in one reply;
  - still-missing fields asked together;
  - C3 re-ask with names;
  - C1 sentences go to the reading and the field stays asked;
  - I1 alias via `confirm_alias`;
  - a required drop ends with a note that keeps values, says how to restart, and does not loop;
  - I3: starting again is a fresh ask;
  - invariant 4: a second press after the note is refused.
- `test_start_workflow_run.py`:
  - one question for several values;
  - the run an answer started does not offer again;
  - I3: a run started another way is a fresh ask;
  - I4: stopped note, with `needs` and `awaiting` cleared.
- `test_is_it_an_answer.py`: "url: …" and "Name: …" under Address are not taken, and are asked about.

Existing tests changed:
- `test_the_answer_to_a_question_is_taken_as_the_answer` and `test_the_question_says_what_the_box_holds_when_anything_knows` now answer with "Customer Type: GPP". C3 stops a bare "GPP" from being guessed into the first of two fields.
- The twin test is deleted, because C2 removed the twin rule.

Integration (**written, not run**): `tests/integration/test_asking_once.py`
- `test_what_is_still_missing_rides_the_real_thread_row`: `asks` and the remaining `missing` survive the SQL thread mapper.
- `test_two_presses_where_the_first_ends_the_ask_give_one_note`: two concurrent presses, where one may be F1's note. Exactly one press is refused as closed, and a note, if any, keeps its values and closes the ask.

### Gates

- `uv run pytest tests/unit tests/contract -q`: **4924 passed, 83 errors**. The errors are the Postgres-only `[sql]` contract params, the same as on the base.
- mypy `src tests evals`: clean (840 files).
- ruff check and ruff format: clean.
- lint-imports: 4 kept, 0 broken.
- `check_code_notes.py`: 0 stale, 0 dead.
- **Worker restart needed**: `StartWorkflowRun._ask_for_values` runs in the worker.

### Rulings

- Ruling: "ask which field was meant" fires when a drop phrase or a label could be one of several fields (a tie, or a said word contained in more than one field name), or when a label names none of this ask's fields. A drop phrase whose object resembles no field at all drops nothing and asks nothing — "skip the queue at dock 4" is a description — cost if wrong: a real drop of a field typed beyond recognition is silently not a drop, and the field is simply asked again.
- Ruling: a bare pronoun object ("skip it", "without that") is a holding reply, so nothing is taken and nothing dropped — the reviewer's probe says "skip it" drops nothing and the field stays asked — cost if wrong: none; the question stands.
- Ruling: " and " is a clause boundary for named values only, as the finding says. A bare reply to one field is still taken whole — "One field missing: unchanged" — cost if wrong: a named value containing " and " ("Description: black and white") keeps only "black". The operator sees the value in the next turn.
- Ruling: I3's link from a run back to its ask is structural: the thread's latest decision for the job is a `resume` whose values equal `run.values`. The run row carries no offer id, and adding one would need a migration the brief does not allow — cost if wrong: another path that starts a run with byte-identical values, with no newer decision about the job in the thread, would inherit that ask's drops. The only effect is not re-offering the optional fields, or noting a dropped field.
- Ruling: I4's run-side note is reachable only when the job's field classes changed between the answer and the run, so a field that was dropped as optional is required by the run. The test builds exactly that through the real writers — cost if wrong: none; otherwise the branch is idle.
- Ruling: a label that names no field of this ask ("Name: SROCL01" under Address) is asked about rather than handed to the model reading. The C2 probe "Code: 123 never fills Zip Code" needs that for a single missing field too — cost if wrong: a free-text value that opens with "Word:" gets one extra question.

### Concerns

- The drop phrases are a fixed English set. Anything else goes to the model reading as before, which never drops.
- `from_the_mail.py` still writes its NEEDS decision without `asks` or `dropped`. Mail never answers a field question (invariant 7), so this round leaves it alone.

## Round 2

This round covers findings 9, 10, 12, 13, 14 and 16 of `task-F1-rereview-1.md`, as the controller listed them; the file is not in the repository. Every change was test first, and every test goes through the real code path (rule 16).

### What changed

- **9 (Critical): a named value is never cut silently.** `_read` in `domain/chat/asking.py` now works by position in the original text (`_clauses`, `_Value`).
  - A clause boundary (comma, semicolon, full stop, " and ") ends a value only when the next clause starts something of this ask (`_starts`): a label that `_field` resolves to one of its fields, a drop phrase naming one, or "with what we have".
  - Otherwise the clause is joined back onto the value, keeping its separator.
  - Inside a named value, only a first-person "don't have X" ends the value (`K_FIRST_PERSON`). So "sold without discount" stays whole and Discount is not dropped, while "Customer Type: RRF i dont have manufacturer" still splits. I2's second sentence also still splits, because "create it without discount" is its own clause.
- **10:** added a `ponytail:` note on `still_to_ask` about the limit of matching a run to its ask by values, and the upgrade path: carry the `resume` decision's `offer` id onto the run when a migration is next allowed.
- **12:** a label is asked about only when it is close to a field of this ask (a clear fuzzy match, or sharing at least half its words with the field's name) or names another field of the job (`_label_of`, via `field_of`). Any other "Word:" is plain text, so with one field open, "Name: SROCL01", "Attn: Bob, 5 Main St", "Note: fragile" and "Re: order 55" fill that field. "Code: 123" is still asked about under Zip Code, and "Ship From Code: SG1" under Ship To Code.
- **13:** "I don't have the department yet" and "… for now" are "not ready" (`K_NOT_READY`, and the extended `K_HOLDING`). Nothing is dropped, nothing is taken, and the field stays asked.
- **14:** the stale `said_as_the_value` mention in `converse.py.md` now names `asking.named_in`. `grep said_as_the_value docs/code-notes` finds nothing.
- **16:** `_short_of` in `test_start_workflow_run.py` now starts its run through the real press. The card asks, `Converse` answers, and `StartWorkflowRun.execute` (`_press`) starts the run with exactly the `values` and `from_step` of that answer's `resume` decision. "Pressed some other way" is a press with other values, so nothing is overwritten on the run. The fixture job fills each field with a step of its own, as a stored job must.

### Tests

These 7 fail on the round-1 code (`39be016`) and pass now:
- `test_asking.py`:
  - item 9: "black and white", "12 Main St, Springfield", "5 St. Louis Ave" and "Retail, wholesale and export" stay whole;
  - item 9: "sold without discount" stays whole and does not drop Discount;
  - item 9: the next label of this ask still ends a value ("Customer Type: GGD; Customer Type Description: black and white");
  - item 12: the four labels that name no field fill the one open field;
  - item 13: "yet" / "for now" is not a drop.
- `test_is_it_an_answer.py`: "url: …" and "Name: SROCL01" under Address go to the reading, per item 12.
- `test_converse.py`: in chat, "Customer Type: GGD; Customer Type Description: black and white" keeps both values whole.

Also added:
- `test_asking.py`: a label naming another field of the job is asked about. It already passed on the round-1 code, so it guards the item-12 exception rather than proving a fix.

Rebuilt:
- The four run-side tests now go through the real press (item 16).

The round-1 I2 probes still pass: "Customer Type: RRF i dont have manufacturer" and "Customer Type: RRF, create it without discount".

### Gates

- `uv run pytest tests/unit tests/contract -q`: **4931 passed, 83 errors**. The errors are the Postgres-only `[sql]` params, the same as on the base.
- mypy `src tests evals`: clean.
- ruff check and ruff format: clean.
- lint-imports: 4 kept, 0 broken.
- `check_code_notes.py`: 0 stale, 0 dead.
- Integration: `tests/integration/test_asking_once.py` is unchanged this round and still **written, not run**.
- **Worker restart needed.**

### Rulings

- Ruling: inside a named value, only a first-person "(I/we) don't have X" ends the value; "skip X" and "without X" there are words of the value. As a clause of their own, all drop phrases count — this is the only reading that keeps both "Customer Type: RRF i dont have manufacturer" (I2) and "Description: sold without discount" (item 9) — cost if wrong: "Customer Type: RRF skip manufacturer" in one clause makes "RRF skip manufacturer" the value. R1's limit or options check may refuse it, and the operator sees it before the run.
- Ruling: "close to a field of this ask" (item 12) means a clear fuzzy match, or sharing at least half its words with the field's name — so "Code" is close to Zip Code and "Ship From Code" to Ship To Code, but "Name", "Attn", "Note" and "Re" are close to nothing — cost if wrong: a one-word label that shares a word with a field (for example "Code: …" under Zip Code) gets one question instead of being taken as text.
- Ruling: "not ready" is "don't have X" followed, in the same clause, by "yet", "for now", "right now" or "at the moment" — cost if wrong: another "not yet" wording that uses "don't have" drops X for this ask only (I3). The operator can start the job again.

### Concerns

- **The browser press refuses optional values nobody gave.** Found by item 16's real press. `StartWorkflowRun.execute` refuses a browser run (one that is not Steel) whose job has optional parameters nobody gave, when the deployment cannot gather: `absent` counts every parameter unless the run is Steel (commit `099a47e`). So on a browser deployment with no mailbox, a chat answer that leaves optional fields out (F1's "the run goes without them") produces a `resume` the press refuses. The rebuilt tests press as a Steel tenant, which is the configuration where such a run really starts. Making the browser rule match `RunSteps`, where an absent optional value skips its step, belongs to the owner of that guard; this round does not widen into it.

## Round 3

This round covers items 7–11 and the nit from `task-F1-rereview-2.md`, as the controller listed them; the file is not in the repository. Every change was test first, and every test goes through the real code path (rule 16).

### What changed

- **7–9, one rule** (`_starts` in `domain/chat/asking.py`): `_starts` is now true whenever `_read` would act on the clause. That covers:
  - a label that `_label_of` resolves or finds near, not only a label `_field` resolves;
  - a drop phrase naming a field;
  - a holding or not-ready phrase such as "i don't have X yet" (`K_HOLDING`);
  - "with what we have".

  Such a clause is never joined onto the value before it. Nearness now also counts a said word of three or more letters that begins a word of the field's name (`_shared`), so "Desc" is near Description.
- **10(a):** inside a named value, a "skip X" or "without X" that names a field of this ask *exactly* (its name, a label, or an R2 alias, via `_exactly`) is asked about once: "Did you mean to skip X, or is it part of the value?" (`Pending.doubting`, rendered by `turned_down`).
  - The value is not written, and nothing is dropped.
  - X is remembered on the ask (`doubted`, carried in `asking_state` and read back by `pending_job`), so the same words sent again are taken as the value.
  - A "without Y" that names no field ("sold without labels") is still simply the value.
- **11 (controller ruling):** `workflow_runs.py` now has `and demanded(declared)` in place of `and (not steel or demanded(declared))`. An absent optional value never blocks a start, on Steel or browser runs. The blank-value and several-items refusals are unchanged. `_short_of` no longer presses as Steel.
- **Nit:** the `docs/code-notes/README.md` "Known shortcuts" row for `asking.py` pointed at the deleted twin rule. It now carries the run-to-ask `ponytail:` note (`still_to_ask`, line 193).

### Tests

These 11 fail on round 2 (`7ccfa7b`) and pass now:
- `test_asking.py`:
  - item 7: "Customer Type: RRF, i don't have manufacturer yet" gives Customer Type=RRF, and Manufacturer stays offered;
  - item 8: "Customer Type: GGD, Department: IN" with Department already given gives Customer Type=GGD, Department=IN;
  - item 9: "Customer Type: GGD, Code: 123" with Zip Code open, and "Customer Type: GGD, Desc: first", give Customer Type=GGD, and the second clause is asked about;
  - item 10(a): asked once, then taken.
- `test_converse.py`, through the card and `Converse`: item 7 in chat, and item 10(a) in chat (asked, then taken on the second send).
- `test_start_workflow_run.py`:
  - `test_a_browser_run_starts_without_an_optional_value_it_will_skip`: the browser twin of the Steel test;
  - the four `_short_of` tests, which now press as a browser.

Changed:
- `test_9_a_drop_word_inside_a_value_…`: its "sold without discount" now falls under 10(a), so the plain-value case is "sold without labels".
- `test_a_declared_parameter_with_no_value_at_all_is_refused`: its fixture's `clientCode` was optional by default, which item 11 now lets start. The test keeps its intent by declaring the parameter `required`.

### Gates

- `uv run pytest tests/unit tests/contract -q`: **4938 passed, 83 errors**. The errors are the Postgres-only `[sql]` params, the same as on the base.
- mypy `src tests evals`: clean.
- ruff check and ruff format: clean.
- lint-imports: 4 kept, 0 broken.
- `check_code_notes.py`: 0 stale, 0 dead.
- Integration: `tests/integration/test_asking_once.py` is still **written, not run**.
- **Worker restart needed:** the press and the run's own ask are in the worker path.

### Rulings

- Ruling: item 8's "Department: IN" for a field already given is a label `_label_of` names, so it ends the value, and it is asked about rather than overwriting the given value — item 12 (round 2) asks about a label naming a job field outside this ask — cost if wrong: an operator who re-states a given field gets one question. The value they gave before is kept.
- Ruling: item 10(a)'s "exactly" means the field's name, one of its labels, or an R2 alias, compared normalised; a fuzzy match never triggers the question — cost if wrong: "without discont" (misspelt) inside a value is taken as the value with no question.
- Ruling: item 11 — with every value absent, `_skippable`'s `declared and not any(values)` guard keeps the step and does not skip it. So a browser run started with nothing given for a job whose parameters are all optional performs those steps without typing a value (`value_for` never types the recording). That is the controller's ruling as written — cost if wrong: such a step may type nothing into its field and fail at the screen belt.

### Concerns

- Item 11 changes a guard from commit `099a47e` for browser runs. `test_runner.py` and `test_start_workflow_run.py` pass unchanged apart from the one fixture noted above, but the owner of that guard should see this round.
