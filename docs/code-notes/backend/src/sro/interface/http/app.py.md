# Notes for `backend/src/sro/interface/http/app.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/app.py`](../../../../../../../backend/src/sro/interface/http/app.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `on_start`, [line 84](../../../../../../../backend/src/sro/interface/http/app.py#L84): Comment

Code: `logging.getLogger(__name__).warning(`

> Said once, loudly, at the one moment somebody is watching a boot.
>
> A model name absent from `prices.py` records `cost_usd = 0.0` on
> every call it makes, so the day's spend reads lower than it was and
> the cap -- which is summed from those rows -- never trips. That is
> the failure `prices.py` opens by describing, and it was live again:
> three settings ran on `gemini-3.7-flash`, which the table has never
> held, and the tenant that spent $62.89 in a day had 60 of its passes
> recorded as free.
>
> A warning and not a refusal to start. A deployment mid-incident that
> points a setting at whatever model is answering today needs to run,
> and a boot that refuses over a price is a boot that refuses over
> bookkeeping.

## `on_start`, [line 89](../../../../../../../backend/src/sro/interface/http/app.py#L89): Comment

Code: `if not await container.claim_the_runs():`

> Every claim in the docstring above rests on there being one process, and
> until this line nothing checked. A second one starting -- a rolling
> deploy, `--scale backend=2`, a restarted pod -- swept the first's live
> runs to `failed`, which also cleared the partial unique index on running
> runs and freed the browser for a second run to claim while the first was
> still driving it. `Dockerfile` pins `--workers 1`; nothing enforced it.

## `lifespan`, [line 123](../../../../../../../backend/src/sro/interface/http/app.py#L123): Comment

Code: `configure_logging(`

> JSON off a laptop and on everywhere else: a deployment's logs are
> collected and queried, and a developer's are read.

## `lifespan`, [line 135](../../../../../../../backend/src/sro/interface/http/app.py#L135): Comment

Code: `async with mcp_server.session_manager.run():`

> streamable_http_app() wires its own lifespan into the sub-app Starlette
> returns, but FastAPI's custom `lifespan=` here replaces the default
> walk that would trigger it -- so its session manager's task group is
> started explicitly, in this one instead.

## `lifespan`, [line 141](../../../../../../../backend/src/sro/interface/http/app.py#L141): Comment

Code: `if container.driving_runs is not None:`

> The pool this process opened, closed. Left open, every app start
> kept its connections: a reloading dev server and a suite that
> drives the ASGI app per request both walk the database out of
> them, and the failure lands somewhere else entirely as
> `TooManyConnectionsError`.
> The runs lock first, and explicitly: `dispose()` does not close
> a connection that is still checked out, so a process that shut
> down cleanly and started again -- a dev reload -- would find its
> own lock still held and skip the sweep it exists to do.

## `create_app`, [line 235](../../../../../../../backend/src/sro/interface/http/app.py#L235): Comment

Code: `origins = list(settings.cors_origins)`

> The console in local development, plus whatever a deployment names --
> the extension's ``chrome-extension://<id>`` is the reason this is
> configurable at all, and it cannot be defaulted because the id is per
> build.

## `create_app`, [line 247](../../../../../../../backend/src/sro/interface/http/app.py#L247): Comment

Code: `app.add_middleware(Attributing)`

> Added LAST, which is what makes it outermost: Starlette inserts each
> addition at the front of the list and wraps the list in reverse. The
> attribution used to be added FIRST and was therefore INSIDE CORS -- so a
> preflight refused there wrote an unattributed line, and the access line
> below would have timed the handler rather than the request.
