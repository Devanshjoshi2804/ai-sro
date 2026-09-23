# Notes for `backend/scripts/verify_held.py`

Comments and docstrings moved out of [`backend/scripts/verify_held.py`](../../../../backend/scripts/verify_held.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/verify_held.py#L1): Docstring

> End to end: a person typing in their own browser reaches the console.
>
> Everything in this chain has a unit test and none of them proves the chain. It
> runs a real extension in a real Chromium, watches a real tab, makes a real
> gesture in it, and then reads the run stream the console reads:
>
>     real gesture -> content script -> worker -> `busy` on the socket
>                  -> DeviceSockets._busy -> AgentDrivers.held_for
>                  -> `waiting` on GET /v1/runs/{id}/stream
>
>     make verify-held
>
> Prints each link as it is proved, and says which one broke when one does.
> Nothing here is part of the product.

## module, [line 18](../../../../backend/scripts/verify_held.py#L18): Note on the line above

Code: `MAX_BUSY_WAIT = 0.5`

> Mirrors `infrastructure/agent/sockets.py`. Written out rather than imported so
> this asks the question from outside, the way a console would.

## `held_in_stream`, [line 36](../../../../backend/scripts/verify_held.py#L36): Docstring

> The `waiting` event, read the way the console reads it.

## `skill_to_run`, [line 167](../../../../backend/scripts/verify_held.py#L167): Docstring

> A shadow skill and the values it asks for.
>
> The rung matters: at shadow every write is produced and withheld, so a
> verification script cannot change anybody's data whatever it types into the
> parameters. Which skill does not matter -- the run only has to be running
> while the operator types.

## `call`, [line 22](../../../../backend/scripts/verify_held.py#L22): Comment

Code: `request = urllib.request.Request(  # noqa: S310`

> S310 below: every URL is built from this file's own constants.

## `call`, [line 32](../../../../backend/scripts/verify_held.py#L32): Comment

Code: `problem = refused.read().decode()`

> RFC 9457 all the way down, so the reason is readable rather than a
> traceback about a status code.

## `main`, [line 113](../../../../backend/scripts/verify_held.py#L113): Comment

Code: `work = context.new_page()`

> A tab to work in, and told to watch it -- `busy` is only ever sent
> from an operator's own gestures, so a tab nobody is observing
> produces nothing to prove.

## `main`, [line 127](../../../../backend/scripts/verify_held.py#L127): Comment

Code: `work.bring_to_front()`

> Typing first, and then the run -- which is both the order that can
> be observed and the realistic one. A run that starts against an
> idle browser is over in a step, and the stream sends `done` before
> it ever asks whether anybody is typing. A browser already busy
> holds the first command, which is what keeps the run running long
> enough for the console to be told about it.

## `main`, [line 154](../../../../backend/scripts/verify_held.py#L154): Comment

Code: `ceiling = DEADLINE_S * MAX_BUSY_WAIT * 1000`

> Never longer than the backend will actually wait. The browser asks
> for BUSY_FOR_MS; a command is held for at most half its own
> deadline, and a console counting down from the raw request would
> promise a pause nobody intends to take.
