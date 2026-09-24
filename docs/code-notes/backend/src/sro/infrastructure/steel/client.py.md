# Notes for `backend/src/sro/infrastructure/steel/client.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/client.py`](../../../../../../../backend/src/sro/infrastructure/steel/client.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L1): Docstring

> Steel sessions API. Implements ``BrowserProvider``. See docs/07-adr/003-steel.md.

## module, [line 21](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L21): Note on the line above

Code: `_CONTEXT = frozenset({"referer"})`

> Not a credential, and not replayable from the demonstration either.
>
> Blue Yonder's auth filter reads a per-session ``libraryContext`` out of the
> Referer and redirects to the login page without it. The executor sent a live
> cookie and a live token and still got a 302 -- which looks exactly like being
> signed out. The page the application itself calls from is part of the session,
> so it is kept with the session.

## module, [line 23](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L23): Note on the line above

Code: `_WANTED = frozenset({Sensitivity.AUTH, Sensitivity.CSRF})`

> What authenticates a call, and nothing else. The cookie is kept separately
> and refreshed on its own schedule; the transport headers belong to the request
> being made, not to the one being replayed.

## module, [line 28](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L28): Note on the line above

Code: `_LIVE_POLL_SECONDS = 0.5`

> Chrome takes a moment to attach, so `idle` is only a failure once it has had
> a few seconds to stop being one.

## `SteelClient`, [line 31](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L31): Docstring

> Talks to a self-hosted Steel instance.
>
> Steel's REST shape is confined to this module. The application only knows
> ``BrowserProvider``, so replacing Steel is an adapter change.

## `_held_by`, [line 292](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L292): Docstring

> Which sessions are holding the only browser, and since when.
>
> One sentence, two callers: refusing to take the browser from somebody, and
> reporting that nothing attached to the session we were given. An operator
> needs the same three facts either way -- who has it, how long they have had
> it, and that a stuck one outlives its own Chrome.

## `_path_of`, [line 303](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L303): Docstring

> Path and query of a URL, or "/" when there is nothing useful.

## `SteelClient._require_browser`, [line 85](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L85): Docstring

> Refuse a session that has no browser behind it.
>
> Steel answers 201 whether or not Chrome came up: a session with nothing
> attached is reported as `idle`, and a self-hosted Steel has exactly one
> browser to give. Handing that back produced a teaching session that
> looked like it was recording and showed "the browser session has ended"
> -- half an hour of a demonstration going nowhere.
>
> A brief `idle` is normal while Chrome starts, so this waits before
> deciding, and then says which session is holding the browser.

## `SteelClient._live_sessions`, [line 115](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L115): Docstring

> Sessions Steel currently believes are using the browser.

## `SteelClient._cdp_origin`, [line 128](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L128): Docstring

> The CDP endpoint with its host resolved to an address.
>
> Chrome refuses every `/json/*` request and every devtools websocket
> whose Host header is a name:
>
>     500 Host header is specified and is not an IP address or localhost.
>
> It is a DNS-rebinding guard, and on a compose network the host IS a
> name -- `steel`. So this deployment could reach Chrome's port and could
> not use it, and nothing noticed until a browser session was opened for
> the first time. `localhost:9223` on a laptop has an IP for a host and
> walks straight past the check.
>
> Resolved rather than overridden with a `Host: localhost` header,
> because the header would have to be right on the websocket dial too --
> and that dial belongs to Playwright, which takes a url and not headers.
> An address in the url is the one thing both halves obey.
>
> `*.localhost` does not work either: the C library answers it from
> RFC 6761 before Docker's DNS is asked, so the name resolves to
> 127.0.0.1 and the connection is refused by nothing at all.
>
> Re-resolved per call, not cached: a restarted Steel comes back on a
> different address, and a cached one turns that into a connection
> refused that outlives the restart.
>
> A host that does not resolve is handed back as it was written. The
> connection that follows fails on its own and says what it could not
> reach, which is a better error than one about DNS -- and it keeps a
> made-up hostname in a test from depending on a resolver.

## `SteelClient._websocket_debugger_url`, [line 139](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L139): Docstring

> Chrome's own websocket endpoint, with the host put back.
>
> Chrome derives ``webSocketDebuggerUrl`` from the request Host header and
> drops the port, so what it returns is ``ws://localhost/devtools/...``.
> Following that verbatim dials port 80. The path is right; the authority
> has to come from configuration.

## `SteelClient.close`, [line 150](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L150): Docstring

> Release the session. A 404 is success -- crash recovery calls this on
> sessions the provider already reaped.
>
> The release is checked rather than assumed. Steel answers 200 to
> releasing a session whose Chrome has already died and leaves it marked
> live, which reads as success and holds the only browser forever.

## `SteelClient._attached`, [line 177](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L177): Docstring

> A short-lived CDP attachment.
>
> Deliberately not held open: these run against a browser a human is
> using, and an idle connection to it is a way to lose their session
> rather than keep it.

## `SteelClient.session_cookies`, [line 186](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L186): Docstring

> Read the cookies through a short-lived CDP attachment.
>
> Deliberately not held open: this runs once, when a human has just
> finished logging in, and an idle connection to the browser they are
> using is a way to lose their session rather than keep it.

## `SteelClient.forget_everything`, [line 192](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L192): Docstring

> Clear the cookie jar this deployment's one browser carries between
> sessions, so what a session is signed into is only what it restored.

## `SteelClient.restore`, [line 200](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L200): Docstring

> Set stored cookies, addressed so the browser will accept them.
>
> ``Network.setCookies`` derives the source scheme from the URL, and drops
> a cookie marked secure without one -- silently, in a batch it still
> reports as successful. The identity provider's cookies are exactly the
> secure ones.

## `SteelClient.session_headers`, [line 210](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L210): Docstring

> Watch the application make one request, and keep what authenticates it.
>
> The page is reloaded rather than merely observed: the tokens wanted are
> sent on the application's own data calls, and a browser sitting idle on
> a screen makes none. Reloading the address the connection names is the
> cheapest way to provoke exactly the traffic the executor will imitate.
>
> Only same-origin requests are read. A third party's bearer token is
> theirs, is useless against this system, and has no business in a vault
> keyed by it.

## `SteelClient.live_sessions`, [line 243](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L243): Docstring

> Every session Steel currently has a browser for.

## `SteelClient.debugger_url`, [line 246](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L246): Docstring

> A self-hosted Steel has one browser, so this is the same endpoint for
> every session it reports. Asked per session anyway, because that is what
> the port promises and what a pool would have to honour.

## `SteelClient.frames`, [line 249](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L249): Docstring

> The session's screen off CDP, rather than Steel's own viewer page.

## `SteelClient.live_view_url`, [line 253](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L253): Docstring

> Ask Steel where the session can be driven.
>
> A released session still answers, but with a status that says it is over;
> there is nothing to point an operator at, so that is ``None``.

## `SteelClient._viewer`, [line 267](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L267): Docstring

> Steel's bare session player rather than its own console.
>
> `sessionViewerUrl` is Steel's product UI — its header, its Docs and
> Discord links, a details panel and a Release Session button sitting
> inside our teaching screen, offering an operator a way to end the
> recording that we would never hear about. `debugUrl` is the same
> screencast with none of it.

## `SteelClient.__init__`, [line 44](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L44): Comment

Code: `self._viewer_base = (public_base_url or base_url).rstrip("/")`

> Everything this client does itself goes to `_base_url`. The one
> string it builds for somebody else's browser uses this.

## `SteelClient.open`, [line 49](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L49): Note

> Task C0 (spec §5.1, §12 risk 1), measured against local Steel
> (`ai-sro-steel-1`, `docker ps` mapped `3010->3000` and `9223->9223`) with
> `backend/scripts/steel_sessions.py http://localhost:3010 http://localhost:9223`,
> run twice for repeatability, both times identical:
>
> ```json
> {
>   "verdict": "contexts",
>   "second_session_live": true,
>   "same_cdp_endpoint": true,
>   "contexts_isolated": true,
>   "context_survives_disconnect": true,
>   "other_survives_release": false
> }
> ```
>
> One shared Chrome process backs every Steel session in this container:
> both sessions' `websocketUrl` (and the `/json/version` debugger URL) are
> identical, and releasing the first session took the second one's
> liveness down with it (`other_survives_release: false`) -- confirming,
> from the CDP side, the same fact this function's own refusal below is
> written against ("does not add a browser, it *takes* the one there
> is"). Steel's own `/v1/sessions` bookkeeping does not multiply past
> one; the refusal in `open` stays correct and nothing about it changes.
>
> But a `Target.createBrowserContext` with `disposeOnDetach: false`,
> dialled directly over CDP rather than through another `/v1/sessions`
> call, produces a context that is cookie-isolated from another one
> (`contexts_isolated: true`) and survives the CDP connection that made
> it being closed and reconnected (`context_survives_disconnect: true`)
> -- which is what a worker restart does. `verdict()`
> (`backend/scripts/steel_sessions.py`) reads this as `"contexts"`: the
> container holds several accounts, not as several Steel sessions, but as
> several browser contexts inside the one session/browser Steel gives
> out. S4's broker should hand out contexts, addressed by
> `browserContextId`, within one Steel session per container -- not
> `steel_urls` = one container per account (spec §5.1's stated baseline),
> and not a naive "ask Steel for N sessions".
>
> QA-0 (the live Blue Yonder QA box) had not been run as of this note;
> its JSON goes here once it has, per
> `.superpowers/sdd/2026-09-24-execution-runtime/task-C0-report.md`.

## `SteelClient.open`, [line 50](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L50): Comment

Code: `holding = [`

> Measured against this deployment: creating a session while another is
> `live` does not add a browser, it *takes* the one there is -- the
> previous session vanishes from the list mid-task. So a sign-in, a
> session check or a second pursuit silently killed whatever was already
> on screen, and the thing that lost its browser reported, truthfully,
> that the screen stopped responding to it.
>
> Refusing says which session holds it, which is something an operator
> can act on. An `idle` session has no browser behind it and is not
> holding anything, so it does not count.

## `SteelClient.open`, [line 64](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L64): Comment

Code: `"dimensions": {"width": self._dimensions[0], "height": self._dimensions[1]},`

> Sized deliberately. The operator has to be able to read the screen
> they are demonstrating on, and the accessibility tree that gets
> captured is the one this viewport produced -- a cramped layout
> teaches a skill about a layout nobody uses.

## `SteelClient.open`, [line 81](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L81): Comment

Code: `live_view_url=self._viewer(body),`

> Steel reports its own URLs as seen from inside its container
> (0.0.0.0:3000). Only the path is usable from out here; the host
> comes from configuration, which knows the published ports.

## `SteelClient._cdp_origin`, [line 137](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L137): Comment

Code: `return f"{found[0][4][0]!s}:{port}"`

> `sockaddr[0]` for AF_INET is the dotted address. `str()` rather than
> a cast because the annotation admits shapes this family never has.

## `SteelClient.session_headers.observe`, [line 223](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L223): Comment

Code: `if "/data/" not in str(request.get("url", "")):`

> Data calls only: the document request carries no token, and
> its Referer is whatever the operator came from.

## `SteelClient.session_headers`, [line 235](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L235): Comment

Code: `await page.wait_for_timeout(6000)`

> The data calls follow the document, not the other way round.

## `SteelClient.live_view_url`, [line 263](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L263): Comment

Code: `if str(body.get("status", "")).lower() in {"released", "failed", "idle"}:`

> `idle` too: a viewer pointed at a session with no browser behind it
> renders an empty frame that reads as "the operator's work vanished".
