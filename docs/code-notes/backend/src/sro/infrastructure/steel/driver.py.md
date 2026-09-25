# Notes for `backend/src/sro/infrastructure/steel/driver.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/driver.py`](../../../../../../../backend/src/sro/infrastructure/steel/driver.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_ATTACH_TIMEOUT_S`, [line 33](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L33): Note

> How long a tab `Target.createTarget` just made may take to surface as a
> Playwright `Page`, and the bound on attaching to a browser at all. Ten
> seconds is S4's `K_CONTEXT_PAGE_TIMEOUT_S` for the same wait; a healthy
> Steel surfaces a tab in well under one.

## `K_ACTION_TIMEOUT_S`, [line 34](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L34): Note

> The bound passed to `goto`'s own `timeout`, in place of Playwright's
> 30 s default. A context disposed mid-navigation left `goto` hanging the
> full default and then raising a raw `TimeoutError` (S5 re-review N1).
> Fifteen seconds is generous for the same page-load work `open_tab`
> already does without a custom bound; the bound only exists so a dead
> context surfaces as `PageGone` in bounded time, not to police a live
> page's load time.

## `K_CALL_BODY_CHARS`, [line 35](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L35): Note

> How much of a 2xx fetch/XHR body the call log keeps. X4's brief caps it at
> 4096 characters. The UI lane reads the body for two things only: the ids a
> 201 created (`made_by`) and the names a read returned (`names_in`); both sit
> at the front of a JSON answer. The brief said "201 only"; a read step needs
> its 2xx body too, so every 2xx is read.

## `K_CALL_TYPES`, [line 36](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L36): Note

> Only `fetch` and `xhr` are calls. The UI lane takes the last 2xx call as the
> answer to a read step; logging documents, scripts and images would hand it
> a stylesheet's 200 instead of the data the screen asked for.

## `_SEED_STORAGE`, [line 38](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L38): Note

> Restored `localStorage` is seeded, never forced: `if (localStorage.getItem(name)
> === null)` only fills a key the context does not already hold. A context
> the application has already written to keeps the application's value.

## `_Link`, [line 48](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L48): Note

> Everything this process knows about one browser connection, and nothing
> that outlives it: the tabs it has seen (`pages`, by CDP target id) and the
> browser context each one belongs to (`owners`), plus the `open_tab` calls
> waiting for their tab to surface (`waiting`). Keyed by `cdp_url` in
> `SteelDriver._links`, so a Steel restart -- which hands out a new
> websocket url -- starts from nothing instead of trusting a cache built
> against a browser that is gone (S5 review M3). `authority` is the
> resolved host:port behind that url, kept so a later reconnect for the
> same container (a new `cdp_url`, since the browser's GUID changed) can
> find and evict this now-dead entry (S5 re-review N4).
>
> Listeners are not here: a reconnect can find the same account contexts
> still open (Steel's contexts survive a CDP disconnect), and a `_Link`
> rebuilt from scratch would silently drop them (S5 re-review N2). They
> live on `SteelDriver._listeners` instead, which outlives any one
> connection.

## `_Calls`, [line 59](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L59): Note

> One tab's network call log. `count` is handed out when a response arrives,
> synchronously, before the body is read, so `mark` (which returns `count`)
> splits calls by when they happened, not by when their bodies finished
> reading: a call answered before the mark never counts as the act's, even if
> its body lands after. `seen` holds `(sequence, call)`; `changed` is set on
> every append and when the tab closes, so every waiter wakes on a real event.
> `reading` keeps the body-reading tasks referenced until they finish.

## `SteelDriver`, [line 66](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L66): Docstring

> `ui_driver.py`'s `_AttachedPage.__aenter__` opened a new CDP connection for
> every call, measured at about 630 ms each (spec §2). `SteelDriver` connects
> once per Steel container (keyed by `cdp_url`, since a container's one Steel
> session is shared by every account's context on it -- QA-0's "contexts"
> verdict) and keeps that connection for as long as it stays up.
>
> Every account is a browser context (`SessionRef.context_id`) and every
> call is scoped to it. There is no "no contexts" mode: the first version
> treated an empty `Target.getBrowserContexts` as a test rig and fell back to
> Chrome's default context, which is exactly what production sees after a
> Steel restart or once the last lease closes -- and it restored one
> account's cookies into, and read another sign-in's cookies out of, that
> shared default jar (S5 review C1). An unknown context is `PageGone`, always.
>
> The page code is read once, here: it is the same file for the life of the
> process.

## `SteelDriver._lock_for`, [line 76](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L76): Docstring

> One `asyncio.Lock` per `cdp_url`, not one for the whole driver: `_link`
> holds its lock for every page in the container while it reattaches
> (`_arrived`'s CDP session, init script and per-frame evaluate), so a
> driver-wide lock made one container's reconnect block tab calls on every
> other container (S5 re-review N4). The dict of locks itself is guarded
> by a second, tiny lock held only long enough to look up or create the
> entry, never across an await that talks to a browser.

## `SteelDriver._link`, [line 83](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L83): Docstring

> One connection per `cdp_url`, made under that url's own lock so two
> first calls do not open two. The url goes through
> `client.websocket_debugger_url`, the same resolution S4's client uses,
> so an `http://` url and a hostname both work (Chrome refuses a named
> Host header, and its `webSocketDebuggerUrl` has no port). A browser that
> cannot be reached -- a stale websocket url after a Steel restart, a
> container that is down -- is `PageGone`, which is what S7's reattach
> acts on, never a raw Playwright or httpx error.
>
> A Steel restart changes the browser's GUID, so a new `cdp_url` earns its
> own `_Link` while the old one -- keyed by the now-dead GUID -- is never
> looked up again and would otherwise sit in `_links` forever. Once the
> new connection is up, any old entry that resolves to the same `authority`
> (host:port -- the same container) is evicted and its browser handle
> closed (S5 re-review N4).
>
> The `page` listener is registered before this connection can make a
> single tab, and the tabs already open are snapshotted in the same
> synchronous step, so no tab can arrive unseen between the two (S5 review
> I2: a listener registered after the snapshot missed 4 of 6 concurrent
> tabs). Tabs that were open before the connection -- a worker that
> restarted -- are adopted once, here, not searched for on every lookup.

## `SteelDriver._arrived`, [line 116](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L116): Docstring

> Every tab the connection sees, once: which target and which browser
> context it is, the account's listeners for that context (if any are
> registered), the page code as an init script for its next documents, and
> the page code evaluated into the documents it already has.
>
> The listeners are attached as soon as the target and its context are
> known, before the init-script and per-frame-evaluate awaits below: those
> awaits used to run first, so a popup's first requests -- an OAuth
> authorize call, say -- could fire and be missed before any handler was
> on the page (S5 re-review N5).
>
> The evaluation is what a restarted worker needs. An init script belongs
> to the CDP session that registered it and dies with that connection, so a
> tab adopted by a new process had no page code in any later document (S5
> review I3: `typeof sroPage` was `"undefined"` after a reattach). A frame
> that is mid-navigation rejects the evaluation; the init script covers the
> document it is navigating to. The page code only assigns
> `globalThis.sroPage`, so a document that gets it twice is unchanged.
>
> Only once that succeeds is the tab visible to lookups (`link.pages`) and
> its `open_tab` waiter resolved, so `open_tab` never navigates a tab whose
> init script is not yet in place. A tab that closes while any of this runs
> is dropped, including the owner entry set just for it.

## `SteelDriver._context`, [line 156](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L156): Docstring

> The account's context must be open in this browser before anything is
> created or read in it -- the same check S4's `_require_context` makes. It
> is also what keeps a stale `SessionRef` from ever landing in Chrome's
> default context: that context is never in `Target.getBrowserContexts`.

## `SteelDriver._page`, [line 163](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L163): Docstring

> A tab is the account's only when its target belongs to the account's
> context, and that context is one this browser still lists: every lookup
> goes through `_context` first, so a `SessionRef` carrying the id of
> Chrome's own default context -- never created, never disposed, never in
> `Target.getBrowserContexts` -- cannot reach the default tab through
> `url_of`, `goto`, `evaluate` or `close_tab` (S5 re-review N3). Playwright
> also puts every foreign context's pages into one default context, so a
> bare target-id lookup found another account's tab and let a stale target
> id drive it (S5 review I1).

## `SteelDriver._target_alive`, [line 170](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L170): Docstring

> Whether Chrome still lists this target, asked over CDP
> (`Target.getTargetInfo`) rather than inferred from how long a call took.
> `_call` uses this, alongside `page.is_closed()`, to decide whether a
> Playwright error means the tab is gone or means something else went
> wrong on a page that is still there (S5 re-review N1).

## `SteelDriver._call`, [line 180](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L180): Docstring

> The one place every call made on a tab -- `close_tab`, `goto`,
> `evaluate` -- routes through to turn "the tab is gone" into `PageGone`.
> A tab closing or crashing mid-call, or Steel's Node exiting under it,
> used to surface as a raw Playwright `TargetClosedError`; a context
> disposed during a hanging `goto` used to surface as a raw `TimeoutError`
> after Playwright's 30 s default (S5 re-review N1). Both are structural,
> not timing, questions: after any `PlaywrightError`, `page.is_closed()`
> and then `_target_alive` (a fresh CDP round trip) decide whether the
> target is actually gone. Only then is it `PageGone`; a real error on a
> tab that is still there is re-raised as-is, so a genuinely slow live
> page is never mistaken for a dead one.

## `SteelDriver.open_tab`, [line 192](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L192): Docstring

> Tabs are addressed by their CDP target id, not by position in `pages[0]`,
> so a worker that restarts finds the tabs a previous process opened (spec
> §5.5).
>
> The target opens on `about:blank` and navigates to `url` only after
> `_arrived` has registered the page code, so the first real document
> already has it. A tab that does not surface in `K_ATTACH_TIMEOUT_S` is
> closed -- otherwise it would sit in the account's context forever -- and
> the call is `PageGone`, never a raw timeout.

## `SteelDriver.on`, [line 250](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L250): Docstring

> A listener for one account: attached to each tab of that account's
> context -- the tabs it has now and every tab `_arrived` sees for it later,
> popups included -- and never to the Playwright context, which with
> `connect_over_cdp` holds every account's tabs in the container. A
> listener there heard account B's requests in account A's handler (S5
> review I7). Page events are carried by each tab's own CDP target
> session, so this is the per-context scope S10's headers, X4's responses
> and S6's navigations build on. `event` and `handler` are Playwright's
> page event names and callbacks.
>
> The registration itself lives on the driver, keyed by `(cdp_url,
> context_id)`, not on the connection: Steel's contexts routinely survive
> a CDP disconnect (`disposeOnDetach: false`), so a reconnect re-adopts the
> same tabs while a listener kept on the old, discarded connection would
> silently stop firing with no error and no reattach to trigger (S5
> re-review N2). `_arrived` re-applies this account's listeners to every
> tab it (re)adopts.

## `SteelDriver._log`, [line 258](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L258): Docstring

> The tab's call log, keyed by its Playwright `Page`, created on first use.
> Closing the tab drops the log and wakes any waiter, which then answers
> `PageGone`. Keyed by `Page`, so a reconnect (a new `Page` for the same
> target) starts a fresh log: a `mark` taken before a reconnect reads nothing
> after it. ponytail: a long-lived tab's log grows with every fetch/XHR until
> the tab closes; trim below the oldest outstanding mark if a tab ever lives
> long enough for that to matter.

## `SteelDriver._heard`, [line 270](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L270): Docstring

> The `response` listener, registered through `on`, so it is attached only to
> the account's own tabs (S5 ruling 8) and never to the shared Playwright
> context: account B's traffic cannot reach account A's log, because A's
> listener is never on B's pages. It is one bound method, so `mark` can see it
> is already registered and `forget` can remove it. Sequencing happens here,
> synchronously; reading the body is a task.

## `SteelDriver._record`, [line 284](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L284): Docstring

> Reads a 2xx body (first `K_CALL_BODY_CHARS`) and appends the call under the
> sequence `_heard` gave it. A body that cannot be read (a redirect, a tab
> that closed) is `None`; the call itself still counts.

## `SteelDriver._frame`, [line 293](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L293): Docstring

> Where the page code runs (spec §4.3, E3). With a recorded `frame_path`,
> walk it from the main frame: at each hop, the only child whose
> `path_shape(url)` equals the hop's; else the child at the hop's index; else
> give up on the path and probe. The probe is the extension's `frameHolding`
> rule: ask every frame `sroPage.resolve`, and take the frame only when exactly
> one claims the control, else the main frame, where the same
> `control_not_found` comes back. Acting in every matching frame would click
> twice on a page that carries the same form twice.

## `SteelDriver.act`, [line 317](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L317): Docstring

> Runs `sroPage.act` in the chosen frame through `_call`, so a closed tab is
> `PageGone`. The pin and the repaired flag are passed back exactly as the
> page code answered; the UI lane threads the pin into `holds` and never
> treats a repaired match as done on its own.

## `SteelDriver.mark`, [line 340](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L340): Docstring

> Registers the call listener for the account on first use, then returns the
> tab's next call sequence number.

## `SteelDriver.calls_since`, [line 348](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L348): Docstring

> The tab's calls from `mark` on, in the order they happened.

## `SteelDriver.wait_for_call`, [line 356](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L356): Docstring

> Waits on the log's `changed` event until a call with that method and path
> shape arrives after `since`. No sleep, no polling: it wakes on a new call or
> the tab closing. `deadline_s` bounds the wait. At the deadline it asks
> whether the tab is still there: gone is `PageGone`, alive is `False` (the
> page is fine; the call never came).

## `SteelDriver.wait_for`, [line 390](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L390): Docstring

> Playwright's `wait_for_function` on `sroPage.holds(payload)` in the same
> frame `act` used: the condition is the pinned element's state, never a
> fixed wait. A Playwright timeout on a live tab is `False`, the port's answer
> for "the page is there and the control did not end up as recorded"; `_call`
> turns a closed tab into `PageGone` first. The port returns `bool`, so the
> not-met case is `False`, not an exception: the UI lane reads `False` as a
> failed verdict.

## `SteelDriver.storage_state`, [line 408](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L408): Docstring

> Cookies come from the account's own jar (`Storage.getCookies` with its
> `browserContextId`). `localStorage` is read from the account's open
> tabs, which after a restart includes the tabs `_link` adopted; an origin
> with no open tab is not in the state. Sign-in reads the state with the
> signed-in tab open, the only place this plan calls it.

## `SteelDriver.restore_state`, [line 437](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L437): Docstring

> Cookies go into the account's jar directly. `localStorage` is written now,
> into the context itself, through a short-lived tab whose every request is
> answered with an empty page: the tab stands on each saved origin without
> loading the application, seeds its keys and closes. It used to be held in
> this process as an init script for later tabs, so a worker that restarted
> between restore and open lost it, and every later tab re-seeded it (S5
> review M5). This is how Playwright restores storage state into a context
> it made; here the context is Steel's, so it is done by hand.

## `SteelDriver.forget`, [line 467](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L467): Docstring

> Drops this account's listeners from `SteelDriver._listeners` and from
> every tab of theirs the driver currently knows about. It closes nothing:
> the connection is shared by every account on the container, and the
> context belongs to the pool (S4, S7's lease), which closes it.

## `SteelDriver.aclose`, [line 478](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L478): Docstring

> Closes every connection and stops Playwright; the API lifespan and the
> worker call it on the way down (S5 review I6). Closing a
> `connect_over_cdp` browser disconnects it and leaves Steel's contexts and
> tabs as they are.
