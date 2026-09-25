# Notes for `backend/src/sro/application/ports/locks.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/locks.py`](../../../../../../../backend/src/sro/application/ports/locks.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `AccountBusy`, [line 11](../../../../../../../backend/src/sro/application/ports/locks.py#L11): Docstring

> `hold` raises this, never a raw driver error, when it gives up waiting.
> A caller in the application layer -- S7's broker, D2's step runner --
> cannot catch `sqlalchemy`'s or `asyncpg`'s own exceptions without
> importing them, which `lint-imports` forbids from this layer. This is the
> one shape "this account is busy, try later" ever takes, whichever
> implementation of `AccountLocks` raised it.

## `AccountLocks.hold`, [line 17](../../../../../../../backend/src/sro/application/ports/locks.py#L17): Docstring

> `on_wait` is a contract, not a convenience: an implementation that waits
> at all must call it between attempts, at intervals short enough that a
> caller heartbeating a Temporal activity from it stays alive for the
> whole wait. A caller that does not need to heartbeat -- most tests --
> passes nothing and gets a no-op.
