# Notes for `backend/src/sro/infrastructure/steel/driver.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/driver.py`](../../../../../../../backend/src/sro/infrastructure/steel/driver.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `K_ATTACH_TIMEOUT_S`, [line 20](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L20): Note

> How long a tab `Target.createTarget` just made may take to surface as a
> Playwright `Page`, and the bound on attaching to a browser at all. Ten
> seconds is S4's `K_CONTEXT_PAGE_TIMEOUT_S` for the same wait; a healthy
> Steel surfaces a tab in well under one.

## `_SEED_STORAGE`, [line 22](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L22): Note

> Restored `localStorage` is seeded, never forced: `if (localStorage.getItem(name)
> === null)` only fills a key the context does not already hold. A context
> the application has already written to keeps the application's value.

## `_Link`, [line 30](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L30): Note

> Everything this process knows about one browser connection, and nothing
> that outlives it: the tabs it has seen (`pages`, by CDP target id), the
> browser context each one belongs to (`owners`), the `open_tab` calls
> waiting for their tab to surface (`waiting`), and the per-account
> listeners (`listeners`, by context id). Keyed by `cdp_url` in
> `SteelDriver._links`, so a Steel restart -- which hands out a new
> websocket url -- starts from nothing instead of trusting a cache built
> against a browser that is gone (S5 review M3).

## `SteelDriver`, [line 39](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L39): Docstring

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

## `SteelDriver._link`, [line 46](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L46): Docstring

> One connection per `cdp_url`, made under the lock so two first calls do
> not open two. The url goes through `client.websocket_debugger_url`, the
> same resolution S4's client uses, so an `http://` url and a hostname both
> work (Chrome refuses a named Host header, and its `webSocketDebuggerUrl`
> has no port). A browser that cannot be reached -- a stale websocket url
> after a Steel restart, a container that is down -- is `PageGone`, which
> is what S7's reattach acts on, never a raw Playwright or httpx error.
>
> The `page` listener is registered before this connection can make a
> single tab, and the tabs already open are snapshotted in the same
> synchronous step, so no tab can arrive unseen between the two (S5 review
> I2: a listener registered after the snapshot missed 4 of 6 concurrent
> tabs). Tabs that were open before the connection -- a worker that
> restarted -- are adopted once, here, not searched for on every lookup.

## `SteelDriver._arrived`, [line 71](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L71): Docstring

> Every tab the connection sees, once: which target and which browser
> context it is, the page code as an init script for its next documents,
> and the page code evaluated into the documents it already has.
>
> The evaluation is what a restarted worker needs. An init script belongs
> to the CDP session that registered it and dies with that connection, so a
> tab adopted by a new process had no page code in any later document (S5
> review I3: `typeof sroPage` was `"undefined"` after a reattach). A frame
> that is mid-navigation rejects the evaluation; the init script covers the
> document it is navigating to. The page code only assigns
> `globalThis.sroPage`, so a document that gets it twice is unchanged.
>
> Only then is the tab visible to lookups and its waiter resolved, so
> `open_tab` never navigates a tab whose init script is not yet in place.
> A tab that closes while this runs is dropped.

## `SteelDriver._context`, [line 105](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L105): Docstring

> The account's context must be open in this browser before anything is
> created or read in it -- the same check S4's `_require_context` makes. It
> is also what keeps a stale `SessionRef` from ever landing in Chrome's
> default context: that context is never in `Target.getBrowserContexts`.

## `SteelDriver._page`, [line 112](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L112): Docstring

> A tab is the account's only when its target belongs to the account's
> context. Playwright puts every foreign context's pages into one default
> context, so a bare target-id lookup found another account's tab and let a
> stale target id drive it (S5 review I1).

## `SteelDriver.open_tab`, [line 119](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L119): Docstring

> Tabs are addressed by their CDP target id, not by position in `pages[0]`,
> so a worker that restarts finds the tabs a previous process opened (spec
> §5.5).
>
> The target opens on `about:blank` and navigates to `url` only after
> `_arrived` has registered the page code, so the first real document
> already has it. A tab that does not surface in `K_ATTACH_TIMEOUT_S` is
> closed -- otherwise it would sit in the account's context forever -- and
> the call is `PageGone`, never a raw timeout.

## `SteelDriver.on`, [line 155](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L155): Docstring

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
> The listeners belong to this connection: a reconnect (Steel restart)
> starts without them, the same as it starts without its tabs.

## `SteelDriver.storage_state`, [line 162](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L162): Docstring

> Cookies come from the account's own jar (`Storage.getCookies` with its
> `browserContextId`). `localStorage` is read from the account's open
> tabs, which after a restart includes the tabs `_link` adopted; an origin
> with no open tab is not in the state. Sign-in reads the state with the
> signed-in tab open, the only place this plan calls it.

## `SteelDriver.restore_state`, [line 191](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L191): Docstring

> Cookies go into the account's jar directly. `localStorage` is written now,
> into the context itself, through a short-lived tab whose every request is
> answered with an empty page: the tab stands on each saved origin without
> loading the application, seeds its keys and closes. It used to be held in
> this process as an init script for later tabs, so a worker that restarted
> between restore and open lost it, and every later tab re-seeded it (S5
> review M5). This is how Playwright restores storage state into a context
> it made; here the context is Steel's, so it is done by hand.

## `SteelDriver.forget`, [line 221](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L221): Docstring

> Drops this account's listeners. It closes nothing: the connection is
> shared by every account on the container, and the context belongs to the
> pool (S4, S7's lease), which closes it.

## `SteelDriver.aclose`, [line 230](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L230): Docstring

> Closes every connection and stops Playwright; the API lifespan and the
> worker call it on the way down (S5 review I6). Closing a
> `connect_over_cdp` browser disconnects it and leaves Steel's contexts and
> tabs as they are.
