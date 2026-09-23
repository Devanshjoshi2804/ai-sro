# Notes for `backend/scripts/smoke.py`

Comments and docstrings moved out of [`backend/scripts/smoke.py`](../../../../backend/scripts/smoke.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/smoke.py#L1): Docstring

> Does this deployment work from outside itself?
>
> Every defect found on the first day of deploying was on an edge that *leaves*
> the deployment, and every one of them looked correct in the code and worked on
> a laptop:
>
> - the trace pipeline had a provider and an exporter and never opened a span;
> - a presigned artifact url named `minio:9000`, which no browser can resolve;
> - `live_view_url` named `steel:3000`, the same mistake one service along;
> - the CDP endpoint named a host, and Chrome refuses a Host that is not an
>   address.
>
> They share a shape. A url or a connection that stays inside the compose network
> is exercised by everything, all the time. One that is handed to a browser is
> exercised by nobody until an operator opens a page -- and then it fails as a
> broken image, a frame that never loads, or a silence.
>
> So this asks the questions only an outside caller can ask. It runs *in* the API
> container, because it needs the app's own adapters to mint the urls under test,
> and then it uses those urls the way a browser would: over the public address,
> through the proxy, from end to end.
>
>     docker compose -f infra/docker-compose.deploy.yml --env-file infra/.env.qa         exec -T api python scripts/smoke.py http://10.11.9.25:8088
>
> Exits non-zero if anything is wrong, and says which thing. Safe to run against
> a live deployment: it writes one small blob and deletes it, opens one browser
> session and releases it, and touches nothing else.

## `_is_private_name`, [line 30](../../../../backend/scripts/smoke.py#L30): Docstring

> Whether this url names something only the compose network can resolve.
>
> A single label with no dot -- `minio`, `steel`, `api` -- is a container
> name. That is the whole bug class this script exists for.

## `check_addresses`, [line 41](../../../../backend/scripts/smoke.py#L41): Docstring

> What this deployment believes its own addresses are.
>
> `our_own_origins()` reads these to know which traffic is the system's own,
> and evidence is refused for them ahead of any tenant's policy. Left at
> their defaults, the console's own calls are captured and mined as
> warehouse work -- which has happened.

## `check_artifact`, [line 57](../../../../backend/scripts/smoke.py#L57): Docstring

> A presigned url, fetched the way the console fetches a screenshot.

## `check_browser`, [line 83](../../../../backend/scripts/smoke.py#L83): Docstring

> A real session, its live view, and the screencast socket behind it.

## `_check_cast`, [line 118](../../../../backend/scripts/smoke.py#L118): Docstring

> The screencast socket the live view opens. An iframe that loads and
> never paints is what a broken one looks like.

## `check_console`, [line 139](../../../../backend/scripts/smoke.py#L139): Docstring

> The console, and what its bundle was built to talk to.
>
> `NEXT_PUBLIC_API_URL` is inlined at build time. A bundle carrying an
> absolute hostname is one image that serves one environment, and a bundle
> carrying a private name is a console that loads and fails every request.

## `check_api`, [line 159](../../../../backend/scripts/smoke.py#L159): Docstring

> The API through whatever is in front of it, with and without a token.

## `check_worker`, [line 174](../../../../backend/scripts/smoke.py#L174): Docstring

> Whether a worker is polling. Its container status cannot say: one image
> serves the API and the worker, and the worker serves no HTTP.

## `check_ledger`, [line 200](../../../../backend/scripts/smoke.py#L200): Docstring

> Whether this deployment can tell a watched write from an unwatched one.
>
> The one question that decides whether a mined job replays its recorded call
> or drives the form: `verified_write_for` is membership in this ledger, and
> an empty ledger is a deployment where nothing is verified, every replay
> falls back to clicking, and `live_headers` is never asked for.
>
> It belongs here rather than in the suite for this module's whole reason. On
> a laptop the loader resolves its root five parents up from its own file and
> finds the repository's `knowledge-base/`; in the image those five parents
> are `/`, so it looks in `/knowledge-base` and finds nothing unless the
> compose file mounts it there. Every test passes either way. Measured on QA
> 2026-09-16, after a clean deploy and a green suite: `ledger rows: 0`.

## `check_artifact`, [line 74](../../../../backend/scripts/smoke.py#L74): Comment

Code: `tampered = await web.get(url + "X")`

> The signature covers the host and the path. If a proxy rewrote
> either, this would be a 200 and the deployment would be serving
> unsigned objects to anyone who guessed a key.
