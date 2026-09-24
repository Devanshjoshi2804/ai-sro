# Notes for `backend/scripts/steel_sessions.py`

Comments and docstrings moved out of [`backend/scripts/steel_sessions.py`](../../../../../backend/scripts/steel_sessions.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

Task C0 (spec §5.1, §12 risk 1): a throwaway probe, not product code. Its job is to answer one question before S4 is built — does one self-hosted Steel container hold more than one operator account's browser session? — and it is deleted once S4 has recorded that answer in `steel_sessions_per_container` / the broker's shape. Nothing in `sro.*` imports it.

## module, [line 1](../../../../../backend/scripts/steel_sessions.py#L1): Note

> Steel's REST API for `POST /v1/sessions`, `GET /v1/sessions/{id}` and `POST /v1/sessions/{id}/release` is `SteelClient`'s own shape (`infrastructure/steel/client.py:49-148`), called here directly with `httpx` instead of through `SteelClient` because `SteelClient.open` refuses a second session outright (`client.py:56-60`) — the one behaviour this probe exists to test around. The CDP surface (`/json/version`, `Target.createBrowserContext`, `Target.createTarget`, `Target.getTargets`) is Chrome's own DevTools Protocol, reached the same way `SteelClient._websocket_debugger_url` reaches it.

## `Seen`, [line 16](../../../../../backend/scripts/steel_sessions.py#L16): Note

> Five yes/no observations, one probe run each, because the three-way answer (`sessions` / `contexts` / `one-per-container`) is a fact about the container, not about any one signal:
>
> - `second_session_live` — did Steel hand back a second session that itself reports `live`, or does it reuse/queue behind the first?
> - `same_cdp_endpoint` — do the two sessions' `websocketUrl`s differ? Two sessions sharing one CDP endpoint are one browser wearing two accounting rows, not two isolated browsers.
> - `contexts_isolated` — a cookie set in one `BrowserContext` must not be visible from another; this is what "one browser, several isolated sessions via contexts" would look like if Steel doesn't expose true multi-session but Chrome's own context isolation still holds.
> - `context_survives_disconnect` — a context created with `disposeOnDetach: false` and then reconnected to (browser closed, driver reconnects) must still list the same target. If it doesn't, a context is only as durable as the connection that made it, which is useless as a session unit.
> - `other_survives_release` — releasing one session/account must not take the other one down with it. Without this, "several sessions" is really "one session that happens to answer several IDs."

## `verdict`, [line 24](../../../../../backend/scripts/steel_sessions.py#L24): Note

> `sessions` needs all three of: a live second session, a distinct CDP endpoint for it, and survival of the other side's release — that's Steel's own multi-session support working end to end, the best outcome (S4 needs nothing beyond what `SteelClient` already does per session).
>
> Short of that, `contexts` needs isolation *and* survival across a reconnect — a single Steel session can still host several accounts as separate, durable `BrowserContext`s, which is S4's fallback shape (one context per account, addressed by `browserContextId`).
>
> Anything less — no isolation, or a context that dies with the connection that made it — means the container holds exactly one account's browser at a time, the spec's stated baseline (§5.1): `steel_urls` maps one container per account and the broker changes nothing above it.

## module, [line 61](../../../../../backend/scripts/steel_sessions.py#L61): Note on the line above

Code: `made = await raw.send("Target.createBrowserContext", {"disposeOnDetach": False})`

> `disposeOnDetach: false` is the one CDP option worth calling out: without it, Chrome tears the context down the moment the CDP connection that created it closes, which is exactly what a worker restart does to a running session (spec §5.5, "Worker restart" — the broker has to reattach to work already in flight, not lose it). The probe recreates a fresh CDP connection (`again`) after closing the one that made the context, and checks the context's target is still listed — that reattach is the whole point of the option, so the probe has to actually exercise it, not just set the flag and trust it.
