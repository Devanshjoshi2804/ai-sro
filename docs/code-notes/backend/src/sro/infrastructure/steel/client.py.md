# Notes for `backend/src/sro/infrastructure/steel/client.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/client.py`](../../../../../../../backend/src/sro/infrastructure/steel/client.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L1): Docstring

> Steel sessions API. Implements ``BrowserProvider``. See docs/07-adr/003-steel.md.

## module, [line 24](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L24): Note on the line above

Code: `_CONTEXT = frozenset({"referer"})`

> Not a credential, and not replayable from the demonstration either.
>
> Blue Yonder's auth filter reads a per-session ``libraryContext`` out of the
> Referer and redirects to the login page without it. The executor sent a live
> cookie and a live token and still got a 302 -- which looks exactly like being
> signed out. The page the application itself calls from is part of the session,
> so it is kept with the session.

## module, [line 26](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L26): Note on the line above

Code: `_WANTED = frozenset({Sensitivity.AUTH, Sensitivity.CSRF})`

> What authenticates a call, and nothing else. The cookie is kept separately
> and refreshed on its own schedule; the transport headers belong to the request
> being made, not to the one being replayed.

## module, [line 31](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L31): Note on the line above

Code: `_LIVE_POLL_SECONDS = 0.5`

> Chrome takes a moment to attach, so `idle` is only a failure once it has had
> a few seconds to stop being one.

## module, [line 33](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L33): Note on the line above

Code: `K_MAX_CONTEXTS_PER_CONTAINER = 20`

> S4 (spec §5.1, "add-a-container threshold"), measured against local Steel
> (`ai-sro-steel-1`) with a Chromium already connected over CDP: `docker
> stats --no-stream ai-sro-steel-1` read 813 MiB with one live session and no
> extra contexts. Five `Target.createBrowserContext` calls, each opened with
> one blank tab, cost roughly 30-45 MiB apiece (813 -> 1002 MiB); three more
> blank tabs added to an existing context cost roughly 25-30 MiB apiece
> (noisy -- one reading dropped after a GC pass). Local Steel's container
> limit is 7.8 GiB; the QA box carries 23 GB total, ~6 GB free with Steel
> *stopped* (`progress.md`, QA-0 finding 3) -- a figure that excludes
> whatever Steel itself needs once it is the thing running.
>
> 20 contexts at ~45 MiB each is under 1 GiB of context growth on top of an
> ~800 MiB baseline -- comfortable headroom on either box, and generous for
> a POC where `greyorange` has one tenant and no measured account count yet.
> Raise it (`SRO_STEEL_SESSIONS_PER_CONTAINER`) once a real account count and
> a real memory budget exist; the alternative -- add another container URL
> to `steel_urls` and restart -- is the ruling's intended scaling path and
> costs nothing in code.

## module, [line 35](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L35): Note on the line above

Code: `K_CONTEXT_PAGE_TIMEOUT_S = 10`

> A bound on `_own_page` waiting for the "page" event that says the target
> just created for a context is visible to this connection -- 10s is many
> multiples of what that took against local Steel in practice (well under
> 1s). A container under real load, or a Steel restart mid-call, is the
> failure this exists for; raise it with a measurement behind the new
> number, not a guess, if it ever fires against a healthy container.

## `SteelClient`, [line 40](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L40): Docstring

> Talks to a self-hosted Steel instance.
>
> Steel's REST shape is confined to this module. The application only knows
> ``BrowserProvider``, so replacing Steel is an adapter change.

## `_held_by`, [line 424](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L424): Docstring

> Which sessions are holding the only browser, and since when.
>
> One sentence, two callers: refusing to take the browser from somebody, and
> reporting that nothing attached to the session we were given. An operator
> needs the same three facts either way -- who has it, how long they have had
> it, and that a stuck one outlives its own Chrome.

## `_path_of`, [line 457](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L457): Docstring

> Path and query of a URL, or "/" when there is nothing useful.

## `SteelClient._require_browser`, [line 146](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L146): Docstring

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

## `SteelClient._live_sessions`, [line 176](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L176): Docstring

> Sessions Steel currently believes are using the browser.

## `cdp_origin`, [line 436](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L436): Docstring

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

## `SteelClient._websocket_debugger_url`, [line 189](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L189): Docstring

> Chrome's own websocket endpoint, with the host put back.
>
> Chrome derives ``webSocketDebuggerUrl`` from the request Host header and
> drops the port, so what it returns is ``ws://localhost/devtools/...``.
> Following that verbatim dials port 80. The path is right; the authority
> has to come from configuration.

## `SteelClient.close`, [line 198](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L198): Docstring

> Release the session. A 404 is success -- crash recovery calls this on
> sessions the provider already reaped.
>
> The release is checked rather than assumed. Steel answers 200 to
> releasing a session whose Chrome has already died and leaves it marked
> live, which reads as success and holds the only browser forever.

## `SteelClient._attached`, [line 274](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L274): Docstring

> A short-lived CDP attachment.
>
> Deliberately not held open: these run against a browser a human is
> using, and an idle connection to it is a way to lose their session
> rather than keep it.

## `SteelClient.session_cookies`, [line 283](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L283): Docstring

> Read the cookies through a short-lived CDP attachment.
>
> Deliberately not held open: this runs once, when a human has just
> finished logging in, and an idle connection to the browser they are
> using is a way to lose their session rather than keep it.

## `SteelClient.forget_everything`, [line 297](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L297): Docstring

> Clear the cookie jar this deployment's one browser carries between
> sessions, so what a session is signed into is only what it restored.

## `SteelClient.restore`, [line 313](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L313): Docstring

> Set stored cookies, addressed so the browser will accept them.
>
> ``Network.setCookies`` derives the source scheme from the URL, and drops
> a cookie marked secure without one -- silently, in a batch it still
> reports as successful. The identity provider's cookies are exactly the
> secure ones.

## `SteelClient.session_headers`, [line 334](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L334): Docstring

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

## `SteelClient.live_sessions`, [line 375](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L375): Docstring

> Every session Steel currently has a browser for.

## `SteelClient.debugger_url`, [line 378](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L378): Docstring

> A self-hosted Steel has one browser, so this is the same endpoint for
> every session it reports. Asked per session anyway, because that is what
> the port promises and what a pool would have to honour.

## `SteelClient.frames`, [line 381](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L381): Docstring

> The session's screen off CDP, rather than Steel's own viewer page.

## `SteelClient.live_view_url`, [line 385](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L385): Docstring

> Ask Steel where the session can be driven.
>
> A released session still answers, but with a status that says it is over;
> there is nothing to point an operator at, so that is ``None``.

## `SteelClient._viewer`, [line 399](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L399): Docstring

> Steel's bare session player rather than its own console.
>
> `sessionViewerUrl` is Steel's product UI — its header, its Docs and
> Discord links, a details panel and a Release Session button sitting
> inside our teaching screen, offering an operator a way to end the
> recording that we would never hear about. `debugUrl` is the same
> screencast with none of it.

## `SteelClient.__init__`, [line 54](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L54): Comment

Code: `self._viewer_base = (public_base_url or base_url).rstrip("/")`

> Everything this client does itself goes to `_base_url`. The one
> string it builds for somebody else's browser uses this.

## `SteelClient.open_context`, [line 74](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L74): Note

> The client holds no ownership state (S7 review, C1). It adopts the
> container's live Steel session from `/v1/sessions`, or starts one when
> none is live, and makes a context in it. How many contexts a container
> may hold is counted from live leases in the database, by the pool's
> caller; a restarted process and the API beside the worker read the same
> count. Earlier an in-memory map did this: a restarted client refused to
> open ("all in use") and closed a context id it did not know by releasing
> the Steel session, which ended every sibling account.
>
> `capacity == 1` (the legacy recording client) never makes a context:
> `open` hands back the session itself, and `navigate`, `session_cookies`,
> `forget_everything`, `restore` and `session_headers` use Steel's default
> context. For the pool's client (`capacity > 1`) those five work by
> `browserContextId` over raw CDP (`_require_context`, `_own_page`): a
> fresh `connect_over_cdp` only tracks the contexts it created itself, so
> a bare `Target.createBrowserContext` context never appears in
> `browser.contexts`, and its page would silently fold into another one.
>
> Ceiling: two processes that both find no live session both start one;
> on self-hosted Steel the second takes the one browser. The lease each
> context was claimed for then meets `PageGone` and is recovered onto a
> fresh context (C2). A cross-process lock on session start would close it.

## `SteelClient.dispose`, [line 83](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L83): Note

> Disposes one context and nothing else; it never releases the Steel
> session. A dispose that fails for a context Chrome no longer lists has
> already happened (the context was closed, or its browser restarted), so
> the check is Chrome's own list rather than the wording of the error.

## `K_BROWSER_REPLY_S`, [line 37](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L37): Note

> How long one browser-level CDP call waits for its reply. The connect
> alone was bounded before; a wedged Chrome that accepts the socket and
> never answers held `open` forever, under the account lock (S7 review,
> I2). A healthy reply takes about 0.01-0.04 s here, so ten seconds is
> only for a browser that has stopped; past it the call is
> `BrowserUnavailable`.

## `SteelClient.open`, [line 60](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L60): Note

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
> QA-0 (the live Blue Yonder QA box, run by the controller on the user's go,
> 2026-09-24) printed the identical verdict: `"contexts"`,
> `second_session_live`/`same_cdp_endpoint`/`contexts_isolated`/
> `context_survives_disconnect` all `true`, `other_survives_release` `false`
> (`progress.md`). The container-per-tenant, context-per-account ruling
> stands, and S4 (this function, plus `SteelPool` and `BrowserPool`) is that
> implementation: one real Steel session per container, opened once and
> never released by the broker; every account gets its own
> `Target.createBrowserContext {disposeOnDetach: false}` (`open_context`),
> listed and disposed by `browserContextId` alone (`contexts`, `dispose`),
> never by releasing the session that all of a container's accounts share.

## `SteelClient._holding`, [line 93](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L93): Comment

Code: `return [`

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

## `SteelClient._start`, [line 104](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L104): Comment

Code: `"skipFingerprintInjection": True,`

> Steel's fingerprint injector attaches to every new tab
> (`CDPService.handleNewTarget` -> `injectFingerprintSafely` ->
> `FingerprintInjector.attachFingerprintToPuppeteer`). When the tab has
> already closed, `Target.attachToTarget` rejects with "No target with
> given id found", nothing catches it, and Steel's Node process exits --
> taking Chrome and every account context in the container with it.
> Closing a tab right after opening it did this 3 times out of 3 in the S5
> review, and every time again with this flag stripped in the S5 fix
> round; with it, five open-then-close cycles and ten raw
> create-then-close cycles left the sibling context alive. The option is
> Steel's own session schema (`sessions.schema.js`,
> `skipFingerprintInjection`), which gates exactly that call. Nothing here
> wants a disguised browser: it drives the tenant's own WMS as the
> tenant's own account.

## `SteelClient._start`, [line 105](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L105): Comment

Code: `"dimensions": {"width": self._dimensions[0], "height": self._dimensions[1]},`

> Sized deliberately. The operator has to be able to read the screen
> they are demonstrating on, and the accessibility tree that gets
> captured is the one this viewport produced -- a cramped layout
> teaches a skill about a layout nobody uses.

## `SteelClient.open`, [line 70](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L70): Comment

Code: `live_view_url=self._viewer(body),`

> Steel reports its own URLs as seen from inside its container
> (0.0.0.0:3000). Only the path is usable from out here; the host
> comes from configuration, which knows the published ports.

## `cdp_origin`, [line 445](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L445): Comment

Code: `return f"{found[0][4][0]!s}:{port}"`

> `sockaddr[0]` for AF_INET is the dotted address. `str()` rather than
> a cast because the annotation admits shapes this family never has.

## `SteelClient.session_headers.observe`, [line 355](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L355): Comment

Code: `if "/data/" not in str(request.get("url", "")):`

> Data calls only: the document request carries no token, and
> its Referer is whatever the operator came from.

## `SteelClient.session_headers`, [line 367](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L367): Comment

Code: `await page.wait_for_timeout(6000)`

> The data calls follow the document, not the other way round.

## `SteelClient.live_view_url`, [line 395](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L395): Comment

Code: `if str(body.get("status", "")).lower() in {"released", "failed", "idle"}:`

> `idle` too: a viewer pointed at a session with no browser behind it
> renders an empty frame that reads as "the operator's work vanished".

## `SteelClient._browser_call`, [line 124](../../../../../../../backend/src/sro/infrastructure/steel/client.py#L124): Note

> Making, listing and disposing of an account's browser context goes over
> one raw CDP websocket, not Playwright's `connect_over_cdp`. Playwright
> attaches to every target in the browser when it connects, and a sibling
> account's page with a navigation in flight holds that attach until the
> navigation ends: measured on local Steel (S7, 2026-09-25), with one
> account's tab waiting on a server that never answered, a context create
> through `_attached` took 30.2 s -- the whole hang -- and a dispose timed
> out; the same two commands over a raw websocket took 0.04 s and 0.01 s.
> `tests/integration/test_runs_on_local_steel.py` holds a sibling's page
> mid-navigation and takes an account over within the broker's close
> deadline.
