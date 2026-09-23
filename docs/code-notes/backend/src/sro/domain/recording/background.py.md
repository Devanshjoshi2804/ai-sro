# Notes for `backend/src/sro/domain/recording/background.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/background.py`](../../../../../../../backend/src/sro/domain/recording/background.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/background.py#L1): Docstring

> Traffic the browser makes on its own clock, not because anybody acted.
>
> A session keep-alive or a performance beacon fires on a timer. Whichever step
> happens to be open when it lands absorbs it, so the same demonstration performed
> twice produces two different evidence sets — and the diff, which compares runs
> step by step, reads that as "the demonstrations diverged" and refuses to induce.
> It happened on the first real pair of Blue Yonder runs: one run's search step
> carried a `webPerformanceEntries/batch` beacon and the other's did not.
>
> Dropping these at assembly keeps the Evidence plane about cause and effect. It
> is deliberately a small, literal list: a call wrongly classified as background
> is a call a skill can no longer replay, so the bar for adding a marker is that
> the endpoint exists to report on the client, never to change the system.

## `is_background_traffic`, [line 16](../../../../../../../backend/src/sro/domain/recording/background.py#L16): Docstring

> Whether this call reports on the client rather than acting for the user.

## module, [line 12](../../../../../../../backend/src/sro/domain/recording/background.py#L12): Comment

Code: `"perftrace",`

> Azure B2C's client performance trace, `…/client/perftrace`.
