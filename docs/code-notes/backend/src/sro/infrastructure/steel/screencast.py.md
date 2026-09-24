# Notes for `backend/src/sro/infrastructure/steel/screencast.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/screencast.py`](../../../../../../../backend/src/sro/infrastructure/steel/screencast.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/screencast.py#L1): Docstring

> The session's own screen, as frames, straight off CDP.
>
> Steel's viewer is a single page for the whole deployment: self-hosted, every
> session reports the same ``debugUrl`` -- ``/v1/sessions/debug``, with no session
> in it -- and that page shows "Session connecting..." forever once the browser it
> means is gone. What an operator needs is this session's screen, so this takes it
> from the only place that has it: Chrome's own screencast.
>
> ``Page.startScreencast`` sends a JPEG whenever the page changes, and it sends
> the next one only after the last has been acknowledged. A viewer that forgets to
> ack gets about three frames and then a still image, which is the failure this is
> most likely to be blamed for.

## module, [line 14](../../../../../../../backend/src/sro/infrastructure/steel/screencast.py#L14): Note on the line above

Code: `_QUEUE = 2`

> Frames held for a viewer that is behind. A live view that buffers is not a
> live view: better to drop what the operator has already missed and show them
> the screen as it is now.

## `stream_frames`, [line 17](../../../../../../../backend/src/sro/infrastructure/steel/screencast.py#L17): Docstring

> JPEG frames until the caller stops reading or the browser goes away.

## `_visible_page`, [line 52](../../../../../../../backend/src/sro/infrastructure/steel/screencast.py#L52): Docstring

> The page the operator is looking at.
>
> The last page rather than the first: a sign-in that opened a tab leaves the
> original behind, and screencasting that one shows a screen nobody is on.

## `stream_frames`, [line 32](../../../../../../../backend/src/sro/infrastructure/steel/screencast.py#L32): Comment

Code: `task = asyncio.create_task(`

> Acked whether or not the frame was kept: Chrome sends the next
> one only after this, so a dropped frame must not stop the feed.
