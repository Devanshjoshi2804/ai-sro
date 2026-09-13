# Testing

## Where a test belongs

| Suite | Runs against | Proves | Speed |
|---|---|---|---|
| `tests/unit` | Fakes only | Domain invariants, use-case orchestration, all pure algorithms | < 1s |
| `tests/integration` | Testcontainers Postgres + MinIO | Mapping, SQL, tenant scoping, transactions | ~30s |
| `tests/contract` | The running API + its own OpenAPI | The schema does not lie | ~10s |

```bash
make test-unit          # what you run constantly
make test               # unit + integration
make test-contract
```

## What must never be mocked

- **The domain.** Entities are cheap to construct. A mocked entity proves nothing
  about the invariant you care about.
- **The database, in integration tests.** A mocked repository cannot catch a
  missing `tenant_id` in a `WHERE` clause, which is the failure that ends a pilot.
- **Pure functions.** `assemble_frames`, `parameterise`, `extract` take data and
  return data. Call them.

## Fakes, not mocks

Everything in `tests/unit/fakes.py` behaves — it stores, returns, and raises
`NotFound`. Tests assert on outcomes, not on which methods were called.

A test that asserts `repo.save.assert_called_once()` passes when the code saves
the wrong thing.

`FakeUnitOfWork` counts commits but does **not** simulate rollback: its
repositories hold the same objects the use case mutated. Transactional behaviour
is only provable in `tests/integration`, and claiming otherwise in a unit test
would be worse than not testing it.

## Determinism

`FakeClock` and `FakeIdFactory` mean no test depends on wall time or randomness.
Ids are sequential (`rec-1`, `rec-2`) so a failure message names something
readable.

`tests/factories.py` pins everything to a fixed epoch, `T0`. Use `f.at(seconds)`
for relative timestamps.

## Writing a good test here

- Name it as a sentence:
  `test_a_derived_parameter_cannot_be_used_before_it_is_produced`.
- One behaviour per test.
- Build fixtures with factories so the test names only the fields it is about.
- If a comment is warranted, say what would go wrong **in production** if the
  assertion failed. That is the one place in this codebase where a longer comment
  earns its space — see `tests/unit/domain/test_promotion.py`.

## Testing the architecture itself

The dependency rule is a test. Verify the guard is alive rather than assuming it:

```bash
echo "import sro.infrastructure" >> backend/src/sro/domain/shared/errors.py
make lint-backend    # expect: contract "Domain is pure" BROKEN
git checkout backend/src/sro/domain/shared/errors.py
```

## Testing a rule that lives on two sides of a wire

A rule split across the backend and the extension is a rule that can drift on
one side, and neither side's suite will see it: the backend's tests read the
backend, the extension's fake `fetch`, and both pass while a real browser does
nothing.

Where you find one, hold it with a test that reads **the other side's real
source** — the extension's `.js` as a file, the app's own OpenAPI, the Pydantic
model the route returns. `backend/tests/unit/interface/test_the_command_vocabulary.py`
is the worked example, and
[`docs/14-extension-protocol.md`](14-extension-protocol.md#the-seams-the-fixtures-do-not-cover)
lists the five that exist today and what each costs when it drifts.

Two habits, both learned the hard way:

- **Walk up to find the other side's file; never count parent directories.**
  A fixed `parents[N]` is the test file's own depth, so moving the test breaks
  it silently — and the mutation sweep runs the suite from a copy of the
  backend one level down, where a wrong count made *every* sweep fail to
  collect stats. The score was unmeasurable for weeks and nothing said so.
- **Do not expect the mutation floor to catch this class.** `shape.py` scored
  96.2% while serving a shape the matcher could never match. A sweep asks
  whether the tests notice the code changing; where both sides are wrong the
  same way, nothing changes when one of them moves.

## Local stack notes

- Steel needs `shm_size: 2gb`. Chrome crashes with Docker's 64 MB default, and
  the failure looks like a random disconnect rather than an out-of-memory error.
- `make reset` destroys all local data and re-migrates.

## Frontend

`npm test` — vitest, jsdom, Testing Library. Components only.

What is worth testing here is what the screens *refuse* to do, because those are
the rules a reviewer relies on and the ones a refactor quietly breaks:

- the review screen never renders a credential value, only its vault reference
- it offers one rung of the promotion ladder and stops at the highest permitted
  stage
- the list refuses to pair a recording that is still capturing, or two runs of
  different objectives

Not tested here: whether the API returns the right shape. That is the generated
client's job — `make types` regenerates it and the build fails if it drifted —
and the backend's own suite. A frontend test that mocks the API and then asserts
the mock proves nothing.
