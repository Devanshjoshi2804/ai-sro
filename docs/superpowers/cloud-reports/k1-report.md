# K1 report: a learned body key becomes a slot in the API lane's body template

Branch `d2/k1`, from `feat/execution-runtime` at `384e609`.

## Commits

- `06fd9bf` feat(api-lane): a key learned by a confirmed write becomes a slot in its body template
- (this report) docs: K1 cloud report

## Files changed

Source:
- `backend/src/sro/domain/execution/compose.py`: `with_field` writes `"body_key"`; adds `_fields`, `with_slots` and `without_slots`.
- `backend/src/sro/domain/skill/workflow.py`: `field_key` reads `"body_key"`. This is the single reader behind X10's `prepare` (`run_steps._fill_for` builds `Adding.known` through it), `_fields_for`, `compiled.py`, `shape.keeping_fields` and `compose.field_of`.
- `backend/src/sro/domain/execution/write_plan.py`: adds `learned_slots`, `write_plan_for(..., learned=)` and `_undemonstrated(..., learned=)`. A learned name counts as "has somewhere to go" only once its slot is filled.
- `backend/src/sro/application/execution/plan_step.py`: `_replay_of` and `replay_without_asking` pass `learned` through.
- `backend/src/sro/application/runtime/api_lane.py`: `replay_of` passes `learned=learned_slots(ctx.workflow, step)`. This covers both execute and read-back.
- `backend/src/sro/application/runtime/executor.py`: X10's rule is refined to `added_ok`.
- `backend/src/sro/application/runtime/teach.py`: an API break takes the slots out, and a keyed UI write puts them back. It saves under `_still`'s locked read.

Tests:
- New: `backend/tests/unit/domain/test_a_learned_key_is_a_slot.py` and `backend/tests/unit/application/runtime/test_the_api_lane_after_a_learned_field.py`.
- Modified: `test_teaching.py` (4 new tests, and one fixture moved to `body_key`), `test_mine.py` (1 new test), `test_composing_a_field.py` and `test_a_field_nobody_showed.py` (`body_key`).

Code notes: `compose.py.md`, `write_plan.py.md`, `executor.py.md`, `teach.py.md` and `workflow.py.md`. `plan_step.py.md` and `api_lane.py.md` changed only through anchor re-sync.

## Tests added (unit)

- `test_a_learned_key_is_a_slot.py`: slot of the write after its field; the write carries the key and its read-back confirms it; no learned key leaves no plan; a key the response never names is no slot; a slot is removed and put back (both are idempotent and return `None`); a removed slot leaves the field a field; only a learned field takes a slot.
- `test_the_api_lane_after_a_learned_field.py`: learned with slot → API; composed this run → UI; learned with slot removed → UI.
- `test_teaching.py`: an API break removes the slot (the field stays a field); an expired API failure keeps it; a keyed UI write puts it back; a UI write with no `keyed` leaves it out.
- `test_mine.py::test_a_learned_body_key_is_never_taken_for_a_control_key`: the miner's `_folded` keeps a learned field and a control whose id equals the body key apart. It failed before the change (they merged), which proves the root cause.

I saw the tests fail first: `ImportError` for `with_slots`/`without_slots`/`learned_slots`, the miner test (merge), and the `body_key` fixtures (`KeyError`).

Integration tests: none added (K1 adds no SQL). `Teach.learn` now calls `uow.workflows.save`, an existing, integration-tested method.

## Gate results (from `backend/`)

- `uv run pytest tests/unit tests/contract -q`: 4657 passed, 79 errors. All 79 errors are the `[sql]` contract parametrisations, which need Postgres. The base branch shows the same 79 without this change.
- `uv run mypy src tests evals`: no issues (815 files).
- `uv run ruff check .` and `uv run ruff format --check .`: clean.
- `uv run lint-imports`: 4 kept, 0 broken.
- `make check-code-notes`: 0 stale, 0 dead.

**Worker restart needed:** this touches the executor, the API lane and `Teach`.

## Rulings

- Ruling: the removed-slot state is `"slot": False` on the parameter, not dropping `body_key` as the brief's `without_slots` says. — Why: `body_key` is also what `field_key` reads to know a step is a learned field. It is also what `prepare` builds `Adding.known` from. With it dropped, the step stops being a field step (it would run as a no-cites step with no lane). And with no `Adding.known`, the UI lane's `keyed()` can never confirm the field, so the "put back on a keyed UI write" could never fire. `with_slots` clears the marker and sets `body_key`. — Cost if wrong: the parameter carries one extra key; nothing else reads it.
- Ruling: `field_key` itself reads `body_key` (not only `prepare`). — Why: every consumer of "is this a learned field and what key" routes through it, so this fixes it once at the root. — Cost if wrong: none found; all unit tests pass.
- Ruling: `test_with_no_learned_key_the_write_is_as_demonstrated` from the brief became `..._a_value_the_write_cannot_carry_leaves_no_plan` (`plan is None`). — Why: the code wins (Invariant 15). `_assigned` already refuses a plan when a given value has nowhere to go. A plan that sent the record without Department would silently drop the operator's value. — Cost if wrong: none; the executor closes the API lane in that case anyway.
- Ruling: `named` counts a learned name only when `_undemonstrated` actually filled its slot. This goes beyond the brief's `{**keys, **learned}`. — Why: the brief's form produced a plan without `department` when the recorded response did not name the key. That would silently save the record without the field, even though the executor had opened the lane because the slot existed. The test `test_a_learned_key_the_recorded_response_never_names_is_no_slot` caught it. — Cost if wrong: that write goes through the UI lane instead, which is safe.
- Ruling: `lane_context(workflow=...)` already existed in `runtime_support.py`, so it was left unchanged. — Why: the code wins. — Cost if wrong: none.
- Ruling: slots are removed on any non-expired, fingerprinted API failure of the write, the same condition that joins the known-broken list, as the brief's snippet says. — Cost if wrong: an API break unrelated to the learned key costs the slot until the next keyed UI write.

## Concerns

- **Legacy data:** workflows that X10 grew before this change store the learned key as `"key"`. After K1 they are no longer seen as learned field steps (`field_key` returns ""), so on the next run the compiler may report them as `no_lane` until they are re-learned. No migration was allowed. If any exist in a local database, a one-off rewrite of `key` to `body_key` on parameters whose step is a no-cites, single-parameter step would fix them. The controller should decide.
- Concurrency: `Teach.learn` saves the whole workflow under `_still`'s row lock (`lock=True`) in the same unit of work. Two runs learning at once serialise on the row, and the second sees the first's parameters. A crash before commit writes nothing. A stop mid-way doesn't change this path (it runs after the lanes).
- `run_workflow.py` (the legacy rig path) calls `replay_without_asking` and `write_plan_for` without `learned`, so it behaves as before.
