# Notes for `backend/src/sro/infrastructure/steel/driver.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/driver.py`](../../../../../../../backend/src/sro/infrastructure/steel/driver.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `SteelDriver`, [line 24](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L24): Docstring

> `ui_driver.py`'s `_AttachedPage.__aenter__` opened a new CDP connection for
> every call, measured at about 630 ms each (spec §2). `SteelDriver` connects
> once per Steel container (keyed by `cdp_url`, since a container's one Steel
> session is shared by every account's context on it -- QA-0's "contexts"
> verdict) and keeps that `Browser` for as long as it stays connected, so
> every call after the first `open_tab` pays no reconnect cost.

## `SteelDriver._scoped`, [line 47](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L47): Docstring

> Playwright's `connect_over_cdp` cannot see a browser context it did not
> create itself, so every driver call that must land in one account's
> isolated context goes through raw CDP (`Target.createTarget`,
> `Storage.getCookies`/`setCookies` with a `browserContextId`) rather than
> Playwright's `browser.contexts[0]` -- the same approach S4's `SteelClient`
> uses for the same reason.
>
> `Target.getBrowserContexts` empty means this connection has never had an
> account context created on it at all -- the driver's own browser tests,
> which run against a bare local Chromium with no Steel in front of it -- so
> `session.steel_session_id` is treated as an opaque connection key and every
> operation lands on the connection's one default context. A non-empty list
> that does not contain the session's id means the opposite: this container
> has real account contexts, and this one is gone -- released mid-call, the
> race a `createTarget` against a just-released lease crashed local Steel
> with once -- so the call raises `PageGone` instead of silently opening (or
> reading storage for) the wrong account's context.
>
> The ceiling this leaves: a container that has legitimately emptied out to
> zero live contexts is indistinguishable from the bare-Chromium test rig,
> and would be treated as unscoped instead of raising. Nothing in this plan
> calls `open_tab` for a lease whose context is not already live, so it has
> not been observed; the fix, if it ever is, is a boolean on `SessionRef`
> once S6/S7 can set one.

## `SteelDriver.open_tab`, [line 100](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L100): Docstring

> Tabs are addressed by their CDP target id, not by position in `pages[0]`,
> so a worker that restarts finds the tabs a previous process opened (spec
> §5.5) -- `_page` re-discovers a target id it has not cached by asking the
> connection for it again, the same way `open_tab` on a brand new
> `SteelDriver` does.
>
> The target opens on `about:blank` and only navigates to `url` after both
> init scripts are registered, so the very first document a script would see
> already has the page code and any restored `localStorage` -- registering
> them after a direct navigation to `url` would miss whichever race won.

## `SteelDriver._install`, [line 67](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L67): Docstring

> `add_init_script` covers every document this page navigates to *next*; it
> cannot retroactively run on the document already loaded when it is
> registered. This best-effort `evaluate` covers that one document. A
> `PlaywrightError` here means the frame navigated again between `goto`
> returning and this call running -- the init script already registered
> covers whatever it navigated to, so there is nothing to repair.

## module, [line 16](../../../../../../../backend/src/sro/infrastructure/steel/driver.py#L16): Note on the line above

Code: `_KEEP_STORAGE = """(() => {`

> Restored `localStorage` is seeded, never forced: `if (localStorage.getItem(name)
> === null)` only fills a key the page has not already written. A saved sign-in
> writes this once at restore time, before the application's own script has run
> on this origin at all -- if it ever ran after, it must not clobber a value the
> running application just set.
