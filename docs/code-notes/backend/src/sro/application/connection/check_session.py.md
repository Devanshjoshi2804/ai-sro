# Notes for `backend/src/sro/application/connection/check_session.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/check_session.py`](../../../../../../../backend/src/sro/application/connection/check_session.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/check_session.py#L1): Docstring

> Ask the system whether the session we hold still works.
>
> A stored session goes stale silently. The vault still has cookies, the
> connection still says "connected", and the first thing that notices is an
> operator halfway into a demonstration looking at a login page.
>
> So this asks. One unauthenticated-if-stale GET at the system's own address,
> with the header the executor would send: a login page or a redirect to the
> identity provider means the session is gone, and the app can say so before
> anybody wastes a demonstration on it.

## module, [line 18](../../../../../../../backend/src/sro/application/connection/check_session.py#L18): Note on the line above

Code: `_LOGIN_SCAN_CHARS = 200_000`

> Enough of a page to find its form in. A login page is small; a data
> response this size is not one, and scanning all of it costs nothing useful.

## module, [line 20](../../../../../../../backend/src/sro/application/connection/check_session.py#L20): Note on the line above

Code: `_LIBRARY_PAGE = 200`

> How many skills to look through for something to probe with. A tenant with
> more than this has plenty to choose from in the first page.

## `SessionHealth`, [line 27](../../../../../../../backend/src/sro/application/connection/check_session.py#L27): Note on the line above

Code: `UNREACHABLE = "unreachable"`

> The system did not answer. Says nothing about the session, and must not
> be reported as a bad one -- signing in again would not fix an outage.

## `is_login`, [line 174](../../../../../../../backend/src/sro/application/connection/check_session.py#L174): Docstring

> Whether the system answered with its login rather than with the thing.
>
> Two shapes, and this only ever detected one of them. A redirect off the
> system's own host is the identity provider taking over -- judged by host
> rather than by any word in the URL, because "login", "auth" and "signin" are
> all absent from at least one identity provider we work with and present in
> plenty of pages that are not one.
>
> The other shape is a 200 that *is* the login page, served in place of what
> was asked for. That read as "the session works", so a connection whose every
> call came back as a sign-in form could never self-heal: the check it depends
> on reported it healthy.

## `CheckSession.for_system`, [line 60](../../../../../../../backend/src/sro/application/connection/check_session.py#L60): Docstring

> None when the tenant has no such connection at all.

## `CheckSession._works`, [line 116](../../../../../../../backend/src/sro/application/connection/check_session.py#L116): Docstring

> Whether the session just adopted actually answers the probe.
>
> Adoption used to be taken as proof on its own. It is not: a browser
> keeps its cookie jar in a profile that outlives the session in it, so an
> expired cookie for the right host reads as a completed login. That
> reported "the session works" over a connection whose every call was
> redirected to the identity provider -- and wrote the dead cookies back
> into the vault on the way past.

## `CheckSession._proved_read`, [line 139](../../../../../../../backend/src/sro/application/connection/check_session.py#L139): Docstring

> A GET some demonstration of this system made and got 200 from.
>
> Evidence, not a guess at a health endpoint: whatever this deployment
> answers to is what a taught skill already calls, and if that call needs
> a session then so does everything the operator will ask for.

## `CheckSession._adopt`, [line 156](../../../../../../../backend/src/sro/application/connection/check_session.py#L156): Docstring

> Take a session from a browser that is signed in, if one is open.
>
> Nothing here signs anybody in: it looks at browsers **this tenant**
> already has open and keeps what an operator has already done. A live
> browser holding a cookie for this system is a completed login that
> nobody wrote down.
>
> It used to look at every browser in the deployment. Since the write is
> into the caller's vault and the only remaining check was a host name,
> one tenant's health check could take another tenant's live session and
> act as their operator from then on.

## `CheckSession._check`, [line 74](../../../../../../../backend/src/sro/application/connection/check_session.py#L74): Comment

Code: `proved = await self._proved_read(ctx, system)`

> A read this system has actually proved, rather than its front page --
> and sent the way a run sends it. The portal answered 200 to a session
> whose data calls all redirected to the identity provider, and a bare
> cookie was not enough for those calls either: the site parameters and
> the anti-forgery header are part of what makes a request authentic
> here, so a probe without them tests something nobody does.

## `CheckSession._check`, [line 86](../../../../../../../backend/src/sro/application/connection/check_session.py#L86): Comment

Code: `headers = {`

> The cookie first, and kept: rebuilding this dict without it sent
> the probe unauthenticated, so every check redirected to the
> identity provider no matter how good the session was -- and the
> verdict came to rest entirely on the browser adoption below.

## `CheckSession._check`, [line 102](../../../../../../../backend/src/sro/application/connection/check_session.py#L102): Comment

Code: `if await self._adopt(ctx, connection) and await self._works(`

> Before saying so: is somebody signed in right now in a browser we
> opened? An operator who signs in and closes the tab has done the
> whole job, and three times today a good session was thrown away
> because the console happened not to be watching that window.

## `CheckSession._proved_read`, [line 151](../../../../../../../backend/src/sro/application/connection/check_session.py#L151): Comment

Code: `if "${" not in str(plan.url):`

> Only a call with nothing to fill in: a probe that needs a
> parameter is a probe nobody can run unattended.

## `CheckSession._adopt`, [line 169](../../../../../../../backend/src/sro/application/connection/check_session.py#L169): Comment

Code: `if await self._refresh.execute(ctx, cookies=cookies, trusted=True):`

> Trusted: the browser is open and holds the application's own
> cookie, which is what signing in produces and what an identity
> provider's cookies alone are not.

## `is_login`, [line 179](../../../../../../../backend/src/sro/application/connection/check_session.py#L179): Comment

Code: `lowered = body[:_LOGIN_SCAN_CHARS].lower()`

> A password field is the page saying what it is. Any heuristic on words
> would fire on a warehouse screen that happens to mention a password
> policy; a control the browser will autofill a credential into does not.
