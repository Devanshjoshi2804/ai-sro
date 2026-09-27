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
