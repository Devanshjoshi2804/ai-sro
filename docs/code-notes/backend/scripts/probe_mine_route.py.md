# Notes for `backend/scripts/probe_mine_route.py`

Comments and docstrings moved out of [`backend/scripts/probe_mine_route.py`](../../../../backend/scripts/probe_mine_route.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../backend/scripts/probe_mine_route.py#L1): Docstring

> Does `POST /v1/mine` actually work, against the real store and a real model?
>
> Every mining measurement this project has quoted came from calling `mine()` from
> a script. Task 2 put a route in front of it. This asks the only question that
> matters about that route: does it work when nothing is faked?
>
> It goes through the real ASGI app -- routing, the auth dependency, the container,
> the response model, real Postgres -- and stops one layer short of uvicorn. The
> two defects this project has shipped that every unit test missed were both at
> that layer: `/v1/shapes` and `/v1/spend` were dead against real Postgres while
> 2299 tests were green, because `FakeUnitOfWork` exposes its repositories from
> `__init__` and the real one assigns them inside `__aenter__`.
>
> It reads the store before and after, so the answer is a diff and not a claim.
>
> The specific open question it exists to settle: `mining_passes.learned_parameters`
> was added by migration 0041 and backfilled to 0. **No pass has ever written a
> non-zero value into it** -- the pass that learnt three parameters ran before the
> column existed. The column, its mapper and its contract test are all in place and
> nothing has ever proved the figure survives a real pass.
>
> Run: cd backend && uv run python scripts/probe_mine_route.py

## `_snapshot`, [line 27](../../../../backend/scripts/probe_mine_route.py#L27): Docstring

> What the store holds, in the terms the acceptance criterion is written in.

## `main`, [line 47](../../../../backend/scripts/probe_mine_route.py#L47): Comment

Code: `from sro.interface.http.app import app`

> Imported here, not at module scope: a broken import should be reported as
> this probe's finding rather than as a traceback before it says what it is.

## `main`, [line 60](../../../../backend/scripts/probe_mine_route.py#L60): Comment

Code: `minted = await asyncio.create_subprocess_exec(`

> Shelled out rather than imported: `sro.cli.mint` exposes only `main(argv)`,
> which prints and returns an exit code. This is what the Makefile does at
> every one of its five call sites, and the module's own comment promises
> "the token itself on stdout and nothing else, so it can be piped".

## `main`, [line 78](../../../../backend/scripts/probe_mine_route.py#L78): Comment

Code: `transport = httpx.ASGITransport(app=app)`

> The lifespan, run for real. `ASGITransport` does not run startup events, so
> without this `app.state.container` is never set and every request dies in
> `deps.get_container` with `'State' object has no attribute 'container'`.
>
> Deliberately NOT `app.dependency_overrides[get_container]`, which is how the
> integration test wires its own container in. Overriding would hand the route
> a container this script built, and the thing being probed is whether the
> container the application builds for itself can serve this route -- settings,
> asker, session factory and all.

## `main`, [line 52](../../../../backend/scripts/probe_mine_route.py#L52): Comment

Code: `print(`

> The open item. The column has never held a non-zero value, because the
> only pass that learnt anything ran before migration 0041 created it.
