# Notes for `backend/src/sro/application/connection/release_strays.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/release_strays.py`](../../../../../../../backend/src/sro/application/connection/release_strays.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/release_strays.py#L1): Docstring

> Give the browser back when nobody is using it.
>
> This deployment has one browser. A session that outlives whatever opened it --
> a sign-in that failed halfway, a demonstration nobody finished, a process that
> restarted -- keeps holding it, and everything afterwards fails with "no browser
> available" for a reason nobody can see. One was found holding the slot with no
> Chrome behind it at all.
>
> What makes a session stray is not its age: it is that nothing in this system
> claims it. A demonstration that is still open claims one. A pursuit driving a
> screen claims one. Every browser this system opens now claims one durably, in
> ``browser_sessions``, which is what makes the rest of this honest -- age used to
> be measured from the first sweep that happened to notice a session, per process,
> so a worker restart reset every clock and a browser could hold the slot forever.

## module, [line 12](../../../../../../../backend/src/sro/application/connection/release_strays.py#L12): Note on the line above

Code: `GRACE = timedelta(minutes=15)`

> How long a claimed browser nobody is using is left alone.
>
> A claim says whose it is, not that anything is still doing something with it:
> the pursuit that opened it registers in memory, in one process, and this sweep
> runs in the other. So a claim young enough to belong to work in flight is left
> alone, and one that has been idle for a quarter of an hour is the case that
> actually holds the slot -- a sign-in window abandoned mid-login, a process that
> restarted underneath its browser.
>
> A session with no claim at all gets no grace. Nothing this system runs opened
> it, and after the ownership record nothing ever will.

## `ReleaseStrayBrowsers.execute`, [line 30](../../../../../../../backend/src/sro/application/connection/release_strays.py#L30): Docstring

> Release what nothing claims. Returns what was given back.

## `ReleaseStrayBrowsers._in_use`, [line 57](../../../../../../../backend/src/sro/application/connection/release_strays.py#L57): Docstring

> Sessions something is doing something with: demonstrations, pursuits,
> and the Steel session every live lease's context lives in. Without the
> leases the sweep released the runtime's shared session after its grace,
> ending every account on the container (S7 round 1, I3).

## `ReleaseStrayBrowsers.execute`, [line 43](../../../../../../../backend/src/sro/application/connection/release_strays.py#L43): Comment

Code: `claimed = opened_at.get(browser.session_id)`

> This used to skip anything with a viewer, on the reading that a
> viewer means somebody is watching. It does not: self-hosted Steel
> answers with one deployment-wide debug URL for every live session,
> so the guard was true of all of them and nothing was ever
> released -- which is how an orphaned Chrome came to hold the only
> browser for six hours.

## `ReleaseStrayBrowsers.execute`, [line 53](../../../../../../../backend/src/sro/application/connection/release_strays.py#L53): Comment

Code: `live = {browser.session_id for browser in open_now}`

> Claims whose session the provider no longer has. Unreachable either
> way -- every read intersects with what is live -- but a row kept
> forever is a row a recycled id one day collides with.
