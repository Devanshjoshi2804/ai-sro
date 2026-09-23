# Notes for `backend/src/sro/domain/trigger/cron.py`

Comments and docstrings moved out of [`backend/src/sro/domain/trigger/cron.py`](../../../../../../../backend/src/sro/domain/trigger/cron.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/trigger/cron.py#L1): Docstring

> Enough of cron to refuse the expressions that are wrong.
>
> Not an implementation: the scheduler that runs these owns the meaning, and a
> second parser here would be a second opinion about when a warehouse gets
> written to. This checks the shape, so a typed mistake is caught by the person
> who typed it rather than by silence at three in the morning.

## `why_not`, [line 17](../../../../../../../backend/src/sro/domain/trigger/cron.py#L17): Docstring

> The reason this is not a cron expression, or ``None`` when it is one.
