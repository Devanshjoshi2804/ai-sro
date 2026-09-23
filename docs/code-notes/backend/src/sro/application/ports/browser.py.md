# Notes for `backend/src/sro/application/ports/browser.py`

Comments and docstrings moved out of [`backend/src/sro/application/ports/browser.py`](../../../../../../../backend/src/sro/application/ports/browser.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/ports/browser.py#L1): Docstring

> The browser a demonstration happens in. Backed by Steel; see docs/07-adr/003-steel.md.

## `BrowserSession`, [line 13](../../../../../../../backend/src/sro/application/ports/browser.py#L13): Note on the line above

Code: `live_view_url: str`

> Where a human points their browser to drive this session.

## `BrowserSession`, [line 15](../../../../../../../backend/src/sro/application/ports/browser.py#L15): Note on the line above

Code: `debugger_url: str`

> CDP endpoint for the capture adapter. Never sent to a client.

## `BrowserUnavailable`, [line 46](../../../../../../../backend/src/sro/application/ports/browser.py#L46): Docstring

> Provider is down. Not a ``DomainError``: the request was fine, we are not.

## `BrowserProvider.close`, [line 21](../../../../../../../backend/src/sro/application/ports/browser.py#L21): Docstring

> Idempotent -- crash recovery calls this on sessions already gone.

## `BrowserProvider.navigate`, [line 23](../../../../../../../backend/src/sro/application/ports/browser.py#L23): Docstring

> Put the session on a page.
>
> Steel accepts a start URL when a session is created and does not act on
> it, so opening a browser "at" somewhere is two steps rather than one.

## `BrowserProvider.session_cookies`, [line 25](../../../../../../../backend/src/sro/application/ports/browser.py#L25): Docstring

> Every cookie the session holds.
>
> The only place cookie values are read on purpose. They are a bearer
> credential, so the caller puts them in the vault and nowhere else.

## `BrowserProvider.forget_everything`, [line 29](../../../../../../../backend/src/sro/application/ports/browser.py#L29): Docstring

> Empty this browser of whoever used it last.
>
> Not a nicety. A provider that keeps one browser keeps one cookie jar, so
> a session opened for a second tenant arrived already signed in as the
> first -- the system under test said so, and the connect flow stored that
> session under the new tenant's name. Nobody typed a password and one
> tenant ended up holding another's warehouse session.

## `BrowserProvider.restore`, [line 31](../../../../../../../backend/src/sro/application/ports/browser.py#L31): Docstring

> Put a stored session into a fresh browser, before it navigates.
>
> A browser sent to the application with nothing in it lands on a login
> page, and everything read from that page belongs to nobody.

## `BrowserProvider.session_headers`, [line 35](../../../../../../../backend/src/sro/application/ports/browser.py#L35): Docstring

> The headers this session's own application sends, beyond its cookies.
>
> Some systems authenticate a call with more than a cookie -- Blue Yonder
> signs every request with a ``CSRF-ENCRYPT-TOKEN`` issued at login, held
> in the page rather than in a cookie or in storage. Without it the
> executor is refused while the browser beside it is signed in, which is
> the state a run cannot diagnose for itself.
>
> Observed from a request the application makes on its own, because that
> is the only place the value appears. Returns only the headers that
> authenticate; nothing about the transport, and never the cookie, which
> is kept separately and refreshed on its own schedule.

## `BrowserProvider.live_sessions`, [line 37](../../../../../../../backend/src/sro/application/ports/browser.py#L37): Docstring

> Browsers this deployment has open right now.
>
> So a login somebody completed in one of them is not lost because
> nothing happened to be watching that window.

## `BrowserProvider.debugger_url`, [line 39](../../../../../../../backend/src/sro/application/ports/browser.py#L39): Docstring

> Where to attach to this particular browser.

## `BrowserProvider.live_view_url`, [line 41](../../../../../../../backend/src/sro/application/ports/browser.py#L41): Docstring

> Where a human drives this session, asked for after the fact.
>
> The URL is not stored on the recording: it belongs to the provider, and
> a session that has ended has no live view. ``None`` says exactly that.

## `BrowserProvider.frames`, [line 43](../../../../../../../backend/src/sro/application/ports/browser.py#L43): Docstring

> This session's screen, as JPEG frames, for as long as it is read.
>
> Separate from ``live_view_url`` because a provider's own viewer is a web
> page we do not control: self-hosted Steel hands out one URL for the whole
> deployment with no session in it, which shows the wrong browser or none.
> Frames are the same picture with the provider's product taken out of it.
