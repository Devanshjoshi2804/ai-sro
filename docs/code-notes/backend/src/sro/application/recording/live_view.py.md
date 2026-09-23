# Notes for `backend/src/sro/application/recording/live_view.py`

Comments and docstrings moved out of [`backend/src/sro/application/recording/live_view.py`](../../../../../../../backend/src/sro/application/recording/live_view.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/recording/live_view.py#L1): Docstring

> Where to point an operator at a demonstration in progress.

## `GetLiveView`, [line 9](../../../../../../../backend/src/sro/application/recording/live_view.py#L9): Docstring

> Asks the provider rather than reading a stored URL.
>
> A live view belongs to a browser session, not to a recording: it stops
> existing when the session ends, and a URL kept on the row would go stale
> without anything noticing.

## `GetLiveView.execute`, [line 19](../../../../../../../backend/src/sro/application/recording/live_view.py#L19): Comment

Code: `return None`

> The demonstration is still valid; only the window into it is gone.
