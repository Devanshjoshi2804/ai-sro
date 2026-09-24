# Notes for `backend/src/sro/cli/read_cron.py`

Comments and docstrings moved out of [`backend/src/sro/cli/read_cron.py`](../../../../../../backend/src/sro/cli/read_cron.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../backend/src/sro/cli/read_cron.py#L1): Docstring

> Read every named tenant's unread gestures, once. Named tenants, by hand.
>
> **The worker now does this on its own.** `worker.mine_the_rig_lately` reads
> every tenant whose browsers uploaded in the window and then mines it, on
> `rig_sweep_seconds`. This stays for the two things that loop cannot be: a
> deliberate pass over one named tenant, and a way to read without a worker
> running at all.
>
> Same reason `observe.py` calls the use case directly instead of `POST
> /v1/gestures/read` over HTTP: that route exists for an operator's own
> browser session (`TenantOnly`, a bearer token minted for a person), and a
> cron job is not a person. Nothing here mints or stores a token -- it builds
> the container and calls `ReadGestures.execute` the way the router does,
> one tenant at a time.
>
> There is one "every tenant" query now -- `GestureRepository.tenants_since`,
> which the worker's sweep uses -- and this does not reach for it: what a person
> runs by hand should say whose evidence it is about. Name the tenants on the
> command line, the same way `observe.py` and `mint.py` both take one tenant at
> a time:
>
>     python -m sro.cli.read_cron acme new
>
> A crontab line for a nightly run:
>
>     0 3 * * * cd /path/to/backend && .venv/bin/python -m sro.cli.read_cron acme new >> cron.log 2>&1

## module, [line 13](../../../../../../backend/src/sro/cli/read_cron.py#L13): Note on the line above

Code: `MAX_PASSES = 25`

> How many times one tenant is read in a single run.
>
> `read_new_gestures` reads at most `READING_LIMIT` (200) gestures per pass, so
> a nightly run that made one pass would read 200 gestures a night however many
> were captured -- and a tenant capturing more than that would fall further
> behind every day, with nothing anywhere saying so. Passes repeat until a pass
> finds nothing left, which is the honest end of the job.
>
> Bounded anyway, at 25 passes -- 5,000 gestures for one tenant in one night.
> Not a budget (`daily_usd_cap` is the budget, and `OverCap` below is what
> stops a run that reaches it): a stop against a pass that keeps reporting
> progress it is not making, so a broken pass costs one night rather than
> every night at once.

## `_run`, [line 23](../../../../../../backend/src/sro/cli/read_cron.py#L23): Docstring

> Every tenant gets its own reading, whatever the tenant before it did.
>
> One tenant over its budget, or a tenant whose evidence trips a bug, used
> to end the whole run: the exception left the loop and every tenant after
> it went unread that night, and the night after, with the traceback going
> wherever cron sends output. So each tenant is caught on its own, the run
> reports what happened per tenant, and the exit code is non-zero only if
> something actually broke.
>
> `OverCap` is not a break. It means the budget did its job, so it is
> reported beside whatever was read before the budget ran out, and the run
> still ends 0.

## `_run`, [line 34](../../../../../../backend/src/sro/cli/read_cron.py#L34): Comment

Code: `got = await container.read_gestures().execute(ctx)`

> A fresh door per pass: each one opens, commits and closes its
> own unit of work, and re-entering a spent one is not a thing
> this container promises.

## `_run`, [line 40](../../../../../../backend/src/sro/cli/read_cron.py#L40): Comment

Code: `except Exception as problem:`

> Broad on purpose, and the same reasoning as the asker's: one tenant's
> failure is this tenant's failure, and the next tenant is still owed
> its reading.
