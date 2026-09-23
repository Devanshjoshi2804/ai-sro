# Notes for `backend/src/sro/interface/http/v1/routers/stream.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/stream.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/stream.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `stream_run`, [line 66](../../../../../../../../../backend/src/sro/interface/http/v1/routers/stream.py#L66): Comment

Code: `"X-Accel-Buffering": "no",`

> Nginx and friends buffer event streams into uselessness.

## `_events`, [line 87](../../../../../../../../../backend/src/sro/interface/http/v1/routers/stream.py#L87): Comment

Code: `await asyncio.sleep(LOOK_EVERY)`

> The workflow has been started but the row is a moment behind.

## `_events`, [line 100](../../../../../../../../../backend/src/sro/interface/http/v1/routers/stream.py#L100): Comment

Code: `if run.device_id is not None:`

> The operator is typing into the browser this run is driving, and the
> backend is holding its commands back. Nothing about that reaches the
> row -- it lives for a few seconds in the process holding the socket --
> so it is reported here or nowhere. On change only: at 0.4s a ticking
> countdown would be two and a half events a second saying the same
> thing, and the client can count down on its own.
