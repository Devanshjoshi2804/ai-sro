# Notes for `backend/src/sro/application/execution/pursuits.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/pursuits.py`](../../../../../../../backend/src/sro/application/execution/pursuits.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/pursuits.py#L1): Docstring

> Pursuits in flight, and what they have done so far.
>
> A pursuit is minutes long: twelve gestures, each one a screenshot to a hosted
> model and back. Run inside the HTTP request that asked for it, it held the
> whole API until it finished -- the console could not poll, could not answer
> another question, and could not even report health. That is not a slow
> endpoint, it is an outage with a good excuse.
>
> So the request starts it and returns. What it returns is an address to watch,
> and the gestures appear there as they happen, because a browser being driven on
> somebody's behalf with nothing on screen for two minutes is indistinguishable
> from a hang.
>
> Kept in memory on purpose. A pursuit does not survive a restart and should not
> pretend to: the browser it was driving does not survive one either, and a
> half-finished pursuit resumed against a screen nobody can see is worse than one
> that stopped. What survives is what it wrote to the thread when it finished.

## `PursuitState`, [line 15](../../../../../../../backend/src/sro/application/execution/pursuits.py#L15): Note on the line above

Code: `STOPPED = "stopped"`

> Ran out of budget, was refused, or the screen stopped responding. Not an
> error: a pursuit that stops with a reason is doing its job.

## `PursuitProgress`, [line 24](../../../../../../../backend/src/sro/application/execution/pursuits.py#L24): Note on the line above

Code: `tenant_id: str = ""`

> Whose pursuit this is. `id` is an unguessable uuid4, but every other
> resource in this system 404s across tenants rather than relying on that,
> and a pursuit is no different -- it drives a browser and writes to a
> thread, both scoped to one tenant.

## `PursuitProgress`, [line 31](../../../../../../../backend/src/sro/application/execution/pursuits.py#L31): Note on the line above

Code: `session_id: str = ""`

> The browser it is driving. Kept so the reaper can tell a session
> somebody is using from one that outlived whatever opened it.

## `PursuitProgress`, [line 33](../../../../../../../backend/src/sro/application/execution/pursuits.py#L33): Note on the line above

Code: `recording_id: str = ""`

> What it left behind. A pursuit is a demonstration nobody had to give.

## `PursuitProgress`, [line 35](../../../../../../../backend/src/sro/application/execution/pursuits.py#L35): Note on the line above

Code: `skill_id: str = ""`

> The skill induced from it, so the same request is answered over the API
> next time instead of by looking at a screen again.

## `Pursuits`, [line 42](../../../../../../../backend/src/sro/application/execution/pursuits.py#L42): Docstring

> Every pursuit this process is driving. One per browser, in practice.

## `Pursuits.working`, [line 54](../../../../../../../backend/src/sro/application/execution/pursuits.py#L54): Docstring

> The pursuit driving a screen right now, if one is.
>
> There is one browser behind a self-hosted provider, so a second pursuit
> does not get a second screen -- it gets the same one, mid-task, and both
> navigate it out from under each other. Two pursuits produced two runs of
> twelve gestures that each reported the screen would not respond.

## `Pursuits.sessions`, [line 60](../../../../../../../backend/src/sro/application/execution/pursuits.py#L60): Docstring

> Browsers pursuits are driving right now, so nothing releases one.

## `Pursuits.spawn`, [line 67](../../../../../../../backend/src/sro/application/execution/pursuits.py#L67): Docstring

> Run it detached, and keep a reference so it is not garbage collected.
>
> A task nobody holds is a task the loop may collect mid-gesture, which
> would leave a browser open on a half-filled form.
