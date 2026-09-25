# Notes for `backend/src/sro/infrastructure/temporal/worker.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/temporal/worker.py`](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L1): Docstring

> Worker process. ``make worker`` runs this.

## `identity`, [line 28](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L28): Docstring

> How this worker names itself to Temporal: ``pid@host@revision``.
>
> Temporal's default is ``pid@host``; the revision is appended because that is
> the field the server already keeps for every process polling a queue and
> hands back from DescribeTaskQueue. So the worker reports which code it is
> running without a new table, a new endpoint, or a log file to tail -- and it
> reports it live, which a row written at startup by a process since killed
> would not. `make status` reads the last ``@``-separated field.

## `keep_sessions_open`, [line 52](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L52): Docstring

> Sign systems back in before they expire, for as long as this runs.
>
> A loop in the worker rather than a scheduled workflow: it holds no state
> worth replaying, a missed sweep is corrected by the next one, and the
> cheapest thing that keeps a connection alive over a weekend is the right
> amount of machinery for it.

## `keep_sessions_open`, [line 56](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L56): Note

Code: `expired = await container.expire_confirmations().execute()`

> Confirmations nobody answered inside their window are expired here, once a
> pass, for every tenant. Before this `ExpireConfirmations` had no caller and
> an expired card stayed in the waiting list for good. It rides on this loop
> because the loop already wakes every few minutes for the whole deployment;
> a failure is logged and the session sweep still runs.

## `mine_the_rig_lately`, [line 77](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L77): Docstring

> Read each recorded tenant's day, for as long as this runs.
>
> The rig's whole learning cycle. Both halves had a person in them: `mine_pass` was reachable from a
> door and a script, `read_gestures` from a door and the crontab line in
> `sro.cli.read_cron`'s own docstring. Every mining result this project has
> measured came from somebody running a script.
>
> A loop for the same reasons as the keeper: nothing worth replaying, and a
> missed sweep is corrected by the next one reading the same window. What one
> pass costs is bounded by `daily_usd_cap`, checked before the window is
> packed, and a tenant over it is logged by `MineLately` and skipped rather
> than raised.
>
> Sleeps first. A worker restarting in a crash loop would otherwise fire the
> most expensive call in the system on every start.

## `retain_lately`, [line 103](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L103): Docstring

> Delete evidence that has aged out of its tenant's own window.
>
> A loop for the same reason as the keeper and the miner: nothing here needs
> replaying, and a missed sweep costs one more day of storage rather than a
> broken promise -- the next sweep finds the same rows and removes them.

## `rekey_everything`, [line 118](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L118): Docstring

> Recompute every stored workflow's shape key, once, at startup.
>
>     `rekey_workflows` has said "run once at startup" since it was written and
>     nothing ran it. The rule that makes a shape key changed on 2026-09-15 --
>     an accessible name that is a paragraph is page copy, not an identifier --
>     and the keys mined before that change were never rewritten, so they still
>     carry the words of one mail:
>
>         name|a customer type :- GGD
> description :- leaning new SRO type 01
>
>     A key like that matches nothing, ever. Measured on the deployment,
>     2026-09-18: `Create a Customer Type` held nineteen shape entries, most of
>     them one mail's text, so a fresh demonstration shared ONE entry with it --
>     under `K_MIN_SHARED_STEPS` -- and was mined as a second job with the same
>     name. The mail path then went silent for both, because a request that
>     names a job this tenant holds twice is a request nothing can act on: it
>     was deleted by hand at 21:20 and mined again by 01:13.
>
>     A fix that ships without its migration is a fix for new rows only.
>     

## module, [line 23](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L23): Comment

Code: `logger = logging.getLogger("sro.infrastructure.temporal.worker")`

> Not `__name__`. This module is started as `python -m`, which names it
> `__main__` -- outside the `sro` hierarchy, so it inherits the root level
> `configure_logging` sets, which is WARNING. Every `logger.info` below was
> being dropped: the worker ran with a zero-byte log while polling Temporal
> perfectly well, and "silent" and "dead" looked identical from outside.
> Errors still came through, which is what made it so quiet a failure.

## `keep_sessions_open`, [line 65](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L65): Comment

Code: `logger.exception("the session keeper could not finish its sweep")`

> A keeper that dies quietly is worse than no keeper: the sessions
> look fine until the morning somebody needs one.

## `run`, [line 169](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L169): Comment

Code: `try:`

> Before anything mines, because a pass that runs against stale keys is a
> pass that proposes a duplicate of a job the rig already holds.

## `run`, [line 158](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L158): Note

Code: `graceful_shutdown_timeout=timedelta(seconds=K_STEP_HEARTBEAT_S),`

> Steel runs have a queue of their own, so a long run never waits behind the
> default queue's work. On shutdown a step gets this long to finish before
> it is cancelled -- as a shutdown, never as a stop, so the run is picked up
> again. A code change is live only after this worker restarts.

## `until_signalled`, [line 40](../../../../../../../backend/src/sro/infrastructure/temporal/worker.py#L40): Note

Code: `loop.add_signal_handler(one, stopping.set)`

> SIGTERM (`docker stop`) or SIGINT leaves the workers' `async with`, which
> is their graceful shutdown: no new work is polled, and a running step gets
> `graceful_shutdown_timeout` to finish before it is cancelled. Without a
> handler, Python as PID 1 ignored SIGTERM and Docker killed it mid-write.
> The handlers are removed afterwards, so the signal's default comes back.
