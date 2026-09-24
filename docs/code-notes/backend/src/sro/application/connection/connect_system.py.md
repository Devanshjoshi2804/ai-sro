# Notes for `backend/src/sro/application/connection/connect_system.py`

Comments and docstrings moved out of [`backend/src/sro/application/connection/connect_system.py`](../../../../../../../backend/src/sro/application/connection/connect_system.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/connection/connect_system.py#L1): Docstring

> Connecting a system: open a browser at it, let a human log in, keep the session.
>
> The credentials are typed by the operator into the system's own login page, in a
> browser we opened for them. They never pass through this application, are never
> in a request body we handle, and are never in a recording — the capture recorder
> drops credential values where they are typed.
>
> What we keep is the *session* the login produced, encrypted in the vault. That is
> what lets the executor replay a call tomorrow without a human, and what lets the
> next capture start already logged in.

## module, [line 84](../../../../../../../backend/src/sro/application/connection/connect_system.py#L84): Note on the line above

Code: `_KNOWN_SYSTEMS = {`

> Vendors whose hostnames say nothing useful. ``bf56-kms-wms-web-np2`` is an
> environment, not a system, and two environments of one WMS must land on one
> system key or a skill taught in QA is a skill about a different system.

## `NotAuthenticated`, [line 19](../../../../../../../backend/src/sro/application/connection/connect_system.py#L19): Docstring

> The browser was opened but nobody completed the login.

## `OpenedConnection`, [line 28](../../../../../../../backend/src/sro/application/connection/connect_system.py#L28): Note on the line above

Code: `debugger_url: str`

> For the capture adapter. Never put on the wire.

## `OpenedConnection`, [line 31](../../../../../../../backend/src/sro/application/connection/connect_system.py#L31): Note on the line above

Code: `name: str`

> Derived from the address when the operator did not name them.

## `_system_from`, [line 92](../../../../../../../backend/src/sro/application/connection/connect_system.py#L92): Docstring

> A stable key for the system this address belongs to.
>
> Derived rather than asked for. Two operators naming one system produce two
> keys, and everything that pairs -- sessions, skills, knowledge -- pairs on
> that key being identical.

## `_facility_of`, [line 101](../../../../../../../backend/src/sro/application/connection/connect_system.py#L101): Docstring

> Which site this login covers, from the address it was made at.
>
> Session headers are stored per facility because that is how the executor
> looks them up -- ``<system>/<facility>/<header>``. Blue Yonder names it in
> the portal URL, and a connection made without one covers the default site.

## `_name_from`, [line 109](../../../../../../../backend/src/sro/application/connection/connect_system.py#L109): Docstring

> Something a human recognises in a sidebar, from the same one field.

## `_cookie_header`, [line 113](../../../../../../../backend/src/sro/application/connection/connect_system.py#L113): Docstring

> The cookies this system's own host would receive, as one header.
>
> Scoped by host on purpose: the identity-provider cookies belong to the login
> domain and sending them to the application proves nothing, while the
> application's own session cookie is the thing being kept.

## `StoreSession`, [line 118](../../../../../../../backend/src/sro/application/connection/connect_system.py#L118): Docstring

> Keep the session a human just created, so nothing has to ask them again.

## `RefreshSession`, [line 165](../../../../../../../backend/src/sro/application/connection/connect_system.py#L165): Docstring

> Keep the stored session current, every time a browser proves it is signed in.
>
> Written once at connect, a session is stale by the following week: the
> application rotates its session cookie, the identity provider issues a new
> one, and the blob in the vault names a session the server has forgotten.
> Restoring it puts the operator back on the login page -- which is the thing
> connecting once was supposed to prevent.
>
> So every capture that ends signed in refreshes it. Connect once means
> connect once only if what was connected is kept alive.

## `_still_signed_in`, [line 201](../../../../../../../backend/src/sro/application/connection/connect_system.py#L201): Docstring

> Whether this browser ended the session logged in, judged by what it kept.
>
> A capture that finished on the identity provider still holds cookies -- the
> routing and anti-forgery ones survive being signed out -- so "has cookies"
> is not the question. What a logged-out browser has *lost* is the
> application's own session cookie. Refreshing from it would replace a working
> session with a logged-out one, which is worse than never refreshing at all.

## `_keep`, [line 205](../../../../../../../backend/src/sro/application/connection/connect_system.py#L205): Docstring

> Both forms of the session, written together.
>
> Cookies are bearer credentials: whoever holds them is the operator until
> they expire. They go to the vault, never to a recording.
>
> The blob is what a browser restores; the header is what the executor sends.
> Keeping only the blob meant a skill kept replaying a cookie header written
> weeks earlier: two places held "the session", they aged apart, and every
> call came back 302 to the login page while the browser was happily signed
> in. One store, refreshed together.

## `LoadSession`, [line 224](../../../../../../../backend/src/sro/application/connection/connect_system.py#L224): Docstring

> The stored session, for a browser that needs to start already logged in.

## `AcknowledgeFailures`, [line 246](../../../../../../../backend/src/sro/application/connection/connect_system.py#L246): Docstring

> Close a tripped breaker by a named decision rather than by waiting.
>
> The breaker's own message asks for a person to look. This is what that
> person does afterwards, and it is recorded -- who, when, why -- because a
> breaker anybody can clear anonymously is a breaker that stops meaning
> anything.

## `ConnectSystem.execute`, [line 47](../../../../../../../backend/src/sro/application/connection/connect_system.py#L47): Docstring

> Create or reuse the connection, and open a browser at its login page.

## `RefreshSession.execute`, [line 171](../../../../../../../backend/src/sro/application/connection/connect_system.py#L171): Docstring

> Refresh every connection these cookies can speak for. Returns how many.

## `ConnectSystem.execute`, [line 72](../../../../../../../backend/src/sro/application/connection/connect_system.py#L72): Comment

Code: `await self._browser.forget_everything(session.id)`

> Empty first. This is the flow that decides who the system thinks we
> are, and a provider with one browser hands over the last tenant's
> cookie jar: a second tenant opened a browser, the WMS showed it
> already signed in as the first, and this flow stored that session
> under the second tenant's name. Nobody typed a password, and one
> tenant held another's warehouse session.

## `ConnectSystem.execute`, [line 73](../../../../../../../backend/src/sro/application/connection/connect_system.py#L73): Comment

Code: `await self._browser.navigate(session.id, connection.base_url)`

> Opening "at" a URL is two steps: the provider ignores the start URL
> for an attached browser, so an unnavigated session would show the
> operator a blank page to sign into.

## `_system_from`, [line 97](../../../../../../../backend/src/sro/application/connection/connect_system.py#L97): Comment

Code: `parts = [part for part in host.split(".") if part not in {"www", "com", "co", "uk", "net"}]`

> Otherwise the registrable-looking part, without the environment prefix:
> wms.acme.com and wms.acme.co.uk both become "acme".

## `StoreSession.execute`, [line 140](../../../../../../../backend/src/sro/application/connection/connect_system.py#L140): Comment

Code: `await self._browsers.session(ctx, browser_session_id)`

> Whose browser this is, before a single cookie is read out of it. The
> id arrives as a query parameter, so without this any operator could
> name another tenant's browser and have its live session encrypted into
> their own vault -- and every run afterwards would authenticate as that
> tenant's operator while the audit trail named this one.

## `StoreSession.execute`, [line 144](../../../../../../../backend/src/sro/application/connection/connect_system.py#L144): Comment

Code: `if not _cookie_header(cookies, connection.base_url):`

> Cookies alone prove nothing: an identity provider sets its own before
> anybody types a password, so "has cookies" said signed-in while the
> login page was still on screen. What signing in produces is a cookie
> for the system's own host, and that is what is waited for -- which is
> also what lets the console watch instead of asking.

## `StoreSession.execute`, [line 149](../../../../../../../backend/src/sro/application/connection/connect_system.py#L149): Comment

Code: `headers = await self._browser.session_headers(browser_session_id, connection.base_url)`

> Some systems authenticate a call with more than a cookie. Blue Yonder
> signs every request with a token minted by the portal page, so the
> executor was refused while the browser beside it was signed in -- and
> a run cannot diagnose that for itself. Taken here, from the browser
> that just proved it is signed in, because that is where it exists.

## `RefreshSession.execute`, [line 184](../../../../../../../backend/src/sro/application/connection/connect_system.py#L184): Comment

Code: `header = _cookie_header(cookies, connection.base_url)`

> A cookie header with nothing in it means these cookies are not
> this system's -- a second connection open in another tab, say.
> Overwriting a good session with it would be the bug we are here
> to fix, pointed the other way.

## `RefreshSession.execute`, [line 185](../../../../../../../backend/src/sro/application/connection/connect_system.py#L185): Comment

Code: `if not header or not (`

> `trusted` means the caller has just watched this browser make
> an authenticated call, which is better evidence than the name
> comparison below -- and the comparison rejects a good session
> for holding one cookie fewer, which is how a healer took a
> fresh token and left the stale cookie beside it.

## `_keep`, [line 211](../../../../../../../backend/src/sro/application/connection/connect_system.py#L211): Comment

Code: `await vault.store(`

> And the site-scoped copy, which a skill's credential reference names first.
> Left behind, it shadows the system-scoped one forever: the executor sent a
> cookie from a session that ended hours earlier while every check on the
> fresh one passed, and the run failed in a way nothing could explain.
