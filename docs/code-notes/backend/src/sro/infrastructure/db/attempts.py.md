# Notes for `backend/src/sro/infrastructure/db/attempts.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/attempts.py`](../../../../../../../backend/src/sro/infrastructure/db/attempts.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/attempts.py#L1): Docstring

> Attempts, written and read back.
>
> The domain's own module says what an attempt is and why one exists. This is
> the half that touches a database, and the only thing it adds is a rule the
> port states and this has to keep: **recording an attempt never raises.**
>
> Every caller is a door in the middle of answering somebody, and most of them
> are in the middle of refusing somebody. A refusal that becomes a 500 because
> the recording of it failed is strictly worse than the silence this replaces --
> the operator loses the sentence that told them what was wrong, and gains an
> outage.

## `SqlAttemptRepository.record`, [line 39](../../../../../../../backend/src/sro/infrastructure/db/attempts.py#L39): Comment

Code: `logger.exception(`

> Broad on purpose, and said out loud rather than swallowed: the
> log is where this fact lives anyway, so a table that will not
> take it loses the durable copy and not the fact itself.

## `SqlAttemptRepository.since`, [line 53](../../../../../../../backend/src/sro/infrastructure/db/attempts.py#L53): Comment

Code: `.order_by(AttemptRow.at.desc(), AttemptRow.seq.desc())`

> `at` then arrival, which is `offers`' rule and for its
> reason: several attempts share a second, and a day read
> from the end needs "newest" to be a total order.
