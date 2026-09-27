## Global Constraints

**Runtime rules that bind every task (verbatim):**

1. A write is done only by its own call. An in-doubt write is never sent again.
2. Repair never writes.
3. After-state never carries free text. `isSecretField` controls carry no value.
4. Mail and page text are untrusted, fenced data.
5. Root cause only: no allowlists, no sleeps where a structural signal exists, no tests shaped around bugs, and no caller-side special case where a shared function is wrong.
6. Never touch untracked files. Never print secrets. Never run alembic or DDL by hand against the shared sro_test.
7. Migrations take the next number after 0077. No in-flight branch holds a 0078 today (checked: `rt/e` and `rt/e6` carry stale `0075` files; `rt/d2` at `3936e312` adds none yet, but may). The numbers here are **provisional**: `0078_a_job_remembers_its_words` (R2) and `0079_a_step_knows_its_tab` (T1). Whoever merges takes the next free number at that moment, sets `down_revision` to the head then, and `alembic heads` must show one head.

**Design-2 rules:**

8. Real eval cases are gitignored and never leave the machine (`backend/evals/cases/`, `backend/evals/results/`, `backend/evals/candidates/`). Redacted CI cases replace values with their shapes, and a person reads every redacted file before it is committed to `backend/evals/ci/`.
9. A change to a prompt record's text, schema, model or thinking bumps its `version` and merges only with a `make eval` report in the PR: accuracy holds or improves, sure-but-wrong does not rise, cost per case does not rise (spec §2.2). `make eval` reads the local database and spends model money, so **the user runs it** (marked **LIVE EVAL**); implementers run `make eval-ci`, which is offline.
10. Code validates every model answer. An answer that breaks its schema, cites a quote that is not in its input, or carries a value not taken from the allowed input counts as unsure, never as an answer.
11. Only an operator's answer writes an alias. The model never writes one. Aliases are per job, never global.

**Carried from the runtime plan (Global Constraints 2–6, 11–13 there):**

12. **Backend source carries no comments or docstrings.** Exceptions: docstrings under `backend/src/sro/interface/http/`, docstrings on pydantic models, and tool directives (`# noqa`, `# type: ignore[...]`, `# pragma`, `# fmt:`). Every explanation goes to `docs/code-notes/<source path>.md` under `## \`<qualname>\`, [line N](…#LN): <Kind>`. The same holds for `backend/scripts/` and `backend/evals/`. Update or remove notes for code you change or delete; `make check-code-notes` must pass.
13. **Architecture.** `interface → application → domain`; infrastructure only through `container.py`. `uv run lint-imports` keeps its 4 contracts. This plan adds **no new port**; it adds one method to an existing port (`PageDriver.opened_by`, T2). `grep -rn "unit_of_work()" backend/src/sro/interface/` prints nothing.
14. **Tests first.** Failing test, see it fail, then code. Unit tests in `backend/tests/unit` (Steel, httpx, MCP and Gemini faked); SQL gets an integration test in `backend/tests/integration`; CDP behaviour gets a browser test in `backend/tests/browser`.
15. **Commands.**
    - backend tests: `cd backend && uv run pytest <path> -q -o faulthandler_timeout=120`
    - integration: `cd backend && SRO_INTEGRATION_DATABASE_URL="postgresql+asyncpg://sro:sro@localhost:5432/sro_test" uv run pytest <path> -q -o faulthandler_timeout=120` (the suite migrates its own database; never run alembic by hand against `sro_test`)
    - browser: `cd backend && uv run pytest tests/browser/<file> -q -o faulthandler_timeout=120`
    - frontend: `cd frontend && npx vitest run <file>`
16. **Gates before each commit** (from `backend/`): `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src tests evals` (from P3 on; before P3, `src tests`; exactly the 2 pre-existing errors in `tests/unit/application/test_converse.py` and `tests/unit/domain/chat/test_asking.py` allowed), `uv run lint-imports`, `uv run pytest tests/unit -q -o faulthandler_timeout=120`, plus the integration and browser tests you touched, plus `make check-code-notes` from the repo root. A wire schema change runs `make types` and commits `frontend/openapi.json` and `frontend/src/lib/api/generated.ts`; `uv run pytest tests/contract -q` passes.
17. **Schema changes are additive.** New tables, new defaulted columns. Never drop a table or column: a field this plan stops reading keeps its column and loses only its mapping.
18. **Mutation floors are ratchets.** `scripts/mutation_floor.py` floors never drop.
19. **A code change is not live until the worker restarts.** Every task that touches activities, the executor, lanes or `RunSteps` says so in its report. Implementers never drive live QA or live Steel against a customer system.
20. **Git.** One branch per task from the latest merged tip; merge to `main` only on the user's explicit "merge". Conventional commits ending `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`. Never push. Stage only the files the task names; never touch, move or delete an untracked file (`designof-panel/`, `docs/21-*.md` are the user's).

### Build discipline (ponytail) — binds every implementer and reviewer

Stop at the first rung that holds: (1) does it need to exist at all; (2) already in this codebase — reuse it; (3) stdlib; (4) native platform or database feature; (5) an installed dependency — never add one for a few lines; (6) one line; (7) only then the minimum code that works.

- Understand first: read the task and every file it touches, trace the real flow, grep every caller before editing a shared function. Root cause, fixed once where all callers route through.
- No unrequested abstractions, no scaffolding for later, no config for a constant. Deletion over addition; fewest files; shortest working diff.
- A deliberate corner with a known ceiling gets a note naming the ceiling and the upgrade path in the code-notes file.
- **No workarounds.** The shortest diff never means one. Forbidden, and ranked Important by reviewers: allowlists or exception sets; timing windows or sleeps where a structural signal exists; shaping data, notes or tests to fit around a bug; rewriting a test to keep a dead path green (delete the path); a caller-side special case where the shared function is wrong.

---


## Invariants learned in review (binding on every task; 2026-09-26)

Each rule below was broken at least once and caught only in review. A brief that touches any of these areas must state how it keeps each rule, and add a test that breaks the rule on purpose to prove the test catches it.

1. A write is done only by its own call (same_call with that step's own values), never by shape and order alone.
2. An in-doubt write is never sent again by any path: retry, takeover, answer, sight or refill. It is settled by read-back, or else the operator is asked done / not_done. HTTP 409 counts as in doubt; any other 4xx proves the write was not done.
3. One offer, one run. Starting an offer is idempotent under a unique constraint, and every start path goes through it.
4. An answer acts only on its own question, found by message id. It is a compare-and-set that closes the question, the first answer wins, and a press under a closed question is refused.
5. An action is scoped to the operator who took it (the principal), not only to the tenant's thread. A device must prove its secret and belong to that operator.
6. A claimed mail keeps its claim only once its outcome (run, question, answer, or genuine "not a request") is committed. A model error, a body failure or a restart releases the claim. No mail is dropped silently: an unstarted offer becomes a question.
7. Mail and page text are untrusted data, always fenced, and the fence cannot be closed from inside. Mail never answers a step, field, code or password question, never adds recipients, and never starts a run from a quoted reply.
8. An ended outcome is never rewritten. There is one progress writer, and it is a compare-and-set.
9. Shared rows are appended atomically (for example `messages = messages || new`) or changed under a locked read in the same unit of work. There is never a read-modify-write of a whole JSON column.
10. A stop belongs to the operator alone. Heartbeat timeouts and worker shutdowns are not stops. A stop never cancels its own cleanup, and cleanup (finish, release) always runs.
11. A secret never travels in a Temporal signal, a stored answer, a log line, a reason or an outline. `isSecretField` controls hold no value. Only the question id is signalled.
12. Concurrency story required: every task that touches a write, an answer, a claim or a lease states what happens with two attempts, two presses or panels, a crash between two steps, and a stop mid-way, and has a test for each.
13. Before merge, check that the rule holds across tasks, not only inside this task (for example D3 × D5 and D4 × D5), and run the other task's tests too.
14. Validate by the answer's natural unit: drop the bad item and keep the rest, never all-or-nothing.
15. A brief's signatures and library APIs are verified against the real code before dispatch. Where they disagree, the code wins, and the report says so.
