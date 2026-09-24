# Notes for `backend/src/sro/infrastructure/db/locks.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/locks.py`](../../../../../../../backend/src/sro/infrastructure/db/locks.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 14](../../../../../../../backend/src/sro/infrastructure/db/locks.py#L14): Note on the line above

Code: `K_LOCK_ATTEMPT_S = 10`

> How long one attempt blocks before `hold` comes back to call `on_wait` and
> check the overall deadline. A step activity heartbeats Temporal every
> `K_STEP_HEARTBEAT_S = 30` s or is presumed dead; a single attempt has to
> stay well under that so a caller waiting the full `K_LOCK_WAIT_S` still
> gets several chances to heartbeat in between, not one long block that
> outlives its own activity.

## module, [line 15](../../../../../../../backend/src/sro/infrastructure/db/locks.py#L15): Note on the line above

Code: `K_LOCK_WAIT_S = 120`

> §5.4's own margin: a measured sign-in takes about 50 s -- the form, the
> redirect chain, the app settling -- so a second holder waiting behind one
> is waiting behind a real sign-in, not a wedged one. 120 s gives that room
> to run twice over before a waiter gives up and is told so, rather than
> left blocked on a lock nobody is going to release soon. Reached only
> across several `K_LOCK_ATTEMPT_S`-sized attempts, each one short enough
> that the caller keeps heartbeating the whole time it waits.

## `PostgresAccountLocks.hold`, [line 39](../../../../../../../backend/src/sro/infrastructure/db/locks.py#L39): Comment

Code: `async with self._engine.begin() as connection:`

> A transaction-scoped lock (`pg_advisory_xact_lock`), on a connection this
> one attempt owns start to finish and nothing else touches -- private to
> this `hold`, so the usual argument against a transaction-scoped lock (a
> `commit` or `rollback` dropping it out from under a caller mid-restore)
> does not apply here: nothing else ever commits or rolls back this
> transaction. What it buys instead is a release with no failure mode to
> get wrong: `engine.begin()` commits on a clean exit, rolls back on any
> exception raised inside -- the caller's own error, a cancellation, a retry
> signal -- and either way releases the connection back to its pool, taking
> the lock with it. No `finally` and no explicit unlock exist to forget.
>
> The `NullPool` engine `container.py` builds this from matters as much as
> the transaction scope: `create_engine`'s default pool is small (5 plus 10
> overflow) and shared with every unit of work in the process, and a hold
> that pins one of those connections for up to `K_LOCK_WAIT_S` -- worse,
> several at once, since §5.4 lets parallel runs share one account -- starves
> the very sessions a sign-in needs to open. A dedicated `NullPool` engine
> opens one real Postgres backend per attempt instead, which counts against
> `max_connections` (100 by default) rather than against this process's own
> pool; worth naming now, before a caller holds enough accounts at once to
> approach it.

## `PostgresAccountLocks.hold`, [line 53](../../../../../../../backend/src/sro/infrastructure/db/locks.py#L53): Comment

Code: `except _Retry:`

> `_Retry` is raised from inside the `async with self._engine.begin()` block
> on purpose: raising is what makes that block roll back and release the
> connection before the next attempt opens a fresh one, rather than trying
> to reuse a connection whose transaction a failed statement has already
> aborted. `on_wait` is the contract this port makes with a caller like
> Temporal activity code: called between attempts, never during one, so a
> caller that heartbeats from it stays alive for the whole `K_LOCK_WAIT_S`
> wait without needing to know how the wait is actually broken up.
