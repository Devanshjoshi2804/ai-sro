# Notes for `backend/src/sro/application/connection/keep_open.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/keep_open.py`](../../../../../../../backend/src/sro/application/connection/keep_open.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/keep_open.py#L1): Docstring

> Sign systems back in before their sessions die, not after.
>
> Everything else here reacts: a run fails, a session is refreshed, the run is
> retried. That works and it is not enough -- the first batch of the morning
> should not be the thing that discovers the weekend expired the session, and an
> operator opening the console at 8am should not be looking at a login page.
>
> So a keeper wakes up, asks each connected system whether its session is working
> and how old it is, and replaces the ones that are past half their measured
> life. What "half their life" means is learned per system rather than set here.
>
> Two things it will not do. It never signs in while somebody is demonstrating,
> because this WMS permits one session and taking it would sign the operator out
> mid-task. And it never signs in during an outage, because burning credentials
> against a system that cannot answer is how an account gets locked.

## module, [line 22](../../../../../../../backend/src/sro/application/connection/keep_open.py#L22): Note on the line above

Code: `KEEPER = PrincipalId("session-keeper")`

> Whose name goes on a login nobody asked for. A refresh is not attributable
> to whoever happened to ask last, and an audit trail that says so is worth the
> one extra constant.

## `Swept`, [line 16](../../../../../../../backend/src/sro/application/connection/keep_open.py#L16): Note on the line above

Code: `left_alone: tuple[str, ...] = ()`

> Systems somebody is demonstrating against, and why nothing was touched.

## `Swept`, [line 19](../../../../../../../backend/src/sro/application/connection/keep_open.py#L19): Note on the line above

Code: `released: tuple[str, ...] = ()`

> Browsers given back because nothing claimed them. This deployment has
> one, and a session that outlived whatever opened it holds it forever.

## `KeepSessionsOpen.sweep`, [line 36](../../../../../../../backend/src/sro/application/connection/keep_open.py#L36): Docstring

> One pass over every connected system, in every tenant.
>
> Nobody is making this request, so there is no tenant to scope it to --
> the keeper reads the connection list itself and acts for each tenant in
> turn, which is the one place in this codebase that crosses that line.

## `KeepSessionsOpen._demonstrating`, [line 55](../../../../../../../backend/src/sro/application/connection/keep_open.py#L55): Docstring

> Whether anybody is teaching right now. Their browser holds the
> session this would otherwise replace.

## `KeepSessionsOpen.sweep`, [line 52](../../../../../../../backend/src/sro/application/connection/keep_open.py#L52): Comment

Code: `released = () if busy or self._strays is None else await self._strays.execute()`

> Last, and only when nobody is demonstrating: a sign-in opens a
> browser of its own, and reaping between opening and using it would
> take the slot out from under the thing that just asked for it.
