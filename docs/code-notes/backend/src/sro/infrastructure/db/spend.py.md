# Notes for `backend/src/sro/infrastructure/db/spend.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/spend.py`](../../../../../../../backend/src/sro/infrastructure/db/spend.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/spend.py#L1): Docstring

> The day's bill: the `model_spend` ledger, summed since midnight UTC.
>
> It used to be four tables -- intents, mining passes, runs and chats -- each
> with its own clock column and its own idea of a blind row, and every model
> call that did not land in one of them was invisible to the cap. The metered
> client (`sro/infrastructure/gemini/metered.py`) now writes one row per call
> the model answered, whichever adapter made it, and this sums that alone. The
> four tables keep their own costs for their own screens; summing them here as
> well would bill every call twice.
>
> **The blind count is read beside the sum, not derived from it.** A model name
> the price table never heard of records ``cost_usd`` 0.0 with ``unpriced`` set,
> so a day read on ``cost_usd`` alone spends without limit while the guard reads
> zero. A call that never answered wrote no row, so every unpriced row is blind.
>
> What ``over_cap`` does with the pair is a pure rule and lives in the
> application layer. This produces the numbers; it judges none of them.

## `SqlSpendRepository.today`, [line 35](../../../../../../../backend/src/sro/infrastructure/db/spend.py#L35): Comment

Code: `aware = now if now.tzinfo is not None else now.replace(tzinfo=UTC)`

> UTC when the caller's clock said nothing, and midnight is UTC's
> either way: a naive `now` read as the server's local time moves the
> boundary by the machine's offset, which on a westward host bills
> yesterday evening to today and hands a fresh day a spent cap.

## `SqlSpendRepository.today`, [line 40](../../../../../../../backend/src/sro/infrastructure/db/spend.py#L40): Comment

Code: `func.coalesce(func.sum(ModelSpendRow.cost_usd), 0.0),`

> COALESCE because SUM over no rows is NULL, and a quiet morning
> must read as $0.00 rather than crash the guard that reads it.
> COUNT needs no such help; over no rows it is 0.
