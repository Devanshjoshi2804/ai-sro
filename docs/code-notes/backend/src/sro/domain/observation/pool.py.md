# Notes for `backend/src/sro/domain/observation/pool.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/pool.py`](../../../../../../../backend/src/sro/domain/observation/pool.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/pool.py#L1): Docstring

> A12 -- the carryover pool: what a pass could not place, kept for the next one.
>
> Load-bearing rather than decorative. Model abstraction over raw event streams was
> measured at roughly 74% recall -- against 17,165 ground-truth events a
> model-generated log held 15,420, of which 12,741 were correct. A quarter of every
> window is dropped or mislabelled on any given reading. Without a pool those
> gestures are gone; with one they are read again next to different neighbours.
>
> Keyed by tenant, not by stream. That is the whole mechanism by which one
> operator's Blue Yonder half meets another operator's SAP half.
>
> The ageing rule itself is not here: it is SQL, and it lives with the repository.

## module, [line 5](../../../../../../../backend/src/sro/domain/observation/pool.py#L5): Note on the line above

Code: `K_POOL_AGE = 6`

> Readings of patience. After six more, an entry has been mined.
>
> Retirement IS removal from the window (M1, 2026-09-26). It once was not: a
> retired gesture came back as fresh evidence at its own strength, so that a
> gesture the budget dropped six times would not be blind for good. But the
> age counts READINGS, never passes it was left out of (`waited` counts
> those), so a retired entry is one the model has already read seven times
> and never placed. Coming back, those were read on every pass. On the QA
> box, 1,287 of them kept `left_out` near 1,157 and ran the sweep up to eight
> passes after every arrival.
>
> The late cross-system join this pool exists for still has its seven
> readings. Since a pass with nothing unread no longer reads anything, those
> readings are spent only when new capture arrives, and not by idle passes.

## module, [line 14](../../../../../../../backend/src/sro/domain/observation/pool.py#L14): Note on the line above

Code: `K_MINE_ATTEMPTS = 3`

> Unusable answers a window may get before its entries retire as
> "unminable". An answer that breaks MINE's schema, or is truncated, does
> not mine its window (GC 10), so the window is read again. Without a bound,
> a window the model always truncates would be billed on every pass for
> ever. Three: one retry for a flake, one more for a second, and then it is
> the window.

## module, [line 7](../../../../../../../backend/src/sro/domain/observation/pool.py#L7): Note on the line above

Code: `K_POOL_DAYS = 7`

> How long an unplaced entry may sit before it retires as stale.
>
> The other cap, K_POOL_AGE, counts readings; this one counts days, so evidence
> in a pool nobody is mining still leaves rather than waiting forever for a
> reading that is never taken.
>
> Only an entry that has been read goes stale (`age > 0`). A retired entry is
> never mined again, so an unread one retired for its date would be lost
> without ever being read. Unread entries are packed first, so the next pass
> that runs reads them.

## `PoolEntry`, [line 18](../../../../../../../backend/src/sro/domain/observation/pool.py#L18): Docstring

> One gesture waiting for a better reading, and how long it has waited.
>
> Two clocks, because they measure opposite things and one counter cannot be
> both. `age` counts readings this entry was SHOWN and not cited, and runs
> out at K_POOL_AGE. `waited` counts passes it was PASSED OVER, and drives
> priority so the day rotates. Using age for both made an entry that had been
> read six times outrank one never seen at all.
>
> `reason` is why it retired, empty while it is still live. Evidence that
> leaves the prompt without a record is the failure this architecture exists
> to avoid.
>
> There is no `retired` field, and that is the rig's shape kept deliberately:
> `reason != ""` IS retirement, so the flag and its cause cannot drift apart.
> The row carries a boolean column as well, because the live and retired
> reads want an index to sit on, but it is written from the same decision and
> is never the record's own answer.
