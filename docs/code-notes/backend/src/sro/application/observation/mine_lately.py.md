# Notes for `backend/src/sro/application/observation/mine_lately.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/mine_lately.py`](../../../../../../../backend/src/sro/application/observation/mine_lately.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L1): Docstring

> Every tenant that has been recorded lately, read and mined without asking.
>
> Both halves of the rig's learning cycle had a person in them. `MinePass` was
> reachable from `POST /v1/mine` and from a script; `ReadGestures` from a route
> and from `sro.cli.read_cron`, whose own docstring offers a crontab line. So a
> deployment learned exactly as often as somebody remembered -- which is not what
> a tenant's own brain means. The promise is that the work is watched, the
> repetition is noticed and the job comes back, and none of that can wait on a
> human deciding to look.
>
> Read first, then mine, and the order is not arranged for tidiness. A mining
> pass packs its window out of gestures and their READINGS; an unread gesture
> carries no intent row, so mining ahead of the reader spends the most expensive
> call in the system on evidence nobody has understood yet.
>
> Not `MineEverything`, which is the pre-rig sweep: that one clusters
> `observations` into `task_candidates` with no model, and then teaches every
> candidate it has seen three times. This reads `gestures` and writes
> `workflows`. Neither reads the other's tables, and this deployment runs on this
> one.

## module, [line 19](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L19): Note on the line above

Code: `MAX_READS = 25`

> How many reading passes one tenant gets in one sweep.
>
> `ReadGestures` reads at most `READING_LIMIT` (200) gestures per call, so a
> sweep that made one pass would read 200 an hour however many were captured, and
> a busy tenant would fall further behind every hour with nothing anywhere saying
> so. Passes repeat until one finds nothing left, which is the honest end of the
> job.
>
> Bounded anyway, at 5,000 gestures for one tenant in one sweep. Not a budget --
> `daily_usd_cap` is the budget and `OverCap` is what stops a sweep that reaches
> it -- but a stop against a pass that keeps reporting progress it is not making,
> so a broken reader costs one sweep rather than every sweep at once. The same
> number and the same argument as `sro.cli.read_cron.MAX_PASSES`, which is the
> hand-run version of this.

## module, [line 32](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L32): Note on the line above

Code: `K_SETTLE_S = 120.0`

> How quiet a tenant's evidence has to go before a sweep reads it.
>
> The sweep runs every minute now rather than every hour, which is the whole
> point -- a task done at 10:00 was offered back at 11:00 and an operator
> reasonably asked why. What a minute-by-minute sweep introduces is the opposite
> failure: reading somebody mid-task, proposing the half of a job they had
> finished, and offering that half back forever.
>
> Two minutes, against what this store holds: a doing of a real task runs 35 to
> 180 seconds of continuous gestures, and uploads arrive a median 27 seconds
> after the moment they cover. So two minutes of silence is a person who has
> stopped, not a person thinking -- and the cost of being wrong is one more
> interval, because nothing is thrown away by waiting.

## `_when`, [line 24](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L24): Docstring

> A pass's `started_at`, which is an ISO string on the record and a real
> timestamp in the column. An unreadable one reads as the beginning of time,
> which makes the sweep pay for a pass it might not have needed -- the safe
> direction, since the other one is a tenant that silently stops learning.

## `MineLately`, [line 37](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L37): Docstring

> One pass for each tenant whose browsers uploaded in the window.
>
> Tenant-blind, like every scheduled sweep in this system and for the same
> reason: there is no request behind it and nobody to take a tenant from. It
> asks which tenants have evidence and then mines each one inside its own
> context.
>
> One tenant's refusal is one tenant's refusal. A spend cap reached, a model
> that will not answer, a pass that raised something nobody predicted -- each
> is caught per tenant, because a sweep that stops at the first one lets the
> tenant whose name sorts first decide whether anybody else learns today.
>
> What is NOT caught is the sweep's own read of who to mine: if that fails
> there is nothing to iterate and the caller's loop logs it and waits for the
> next interval.

## `MineLately._read`, [line 55](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L55): Docstring

> Everything unread, up to the bound. One `ReadGestures` call reads at
> most `READING_LIMIT` gestures, so a sweep that made one pass would leave
> a busy tenant falling further behind every hour with nothing saying so.
>
> A fresh door per pass: each opens, commits and closes its own unit of
> work, and re-entering a spent one is not a thing the container promises.

## `MineLately._worth_a_pass`, [line 64](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L64): Docstring

> Whether another pass over this tenant has anything new to read.
>
> A pass re-reads the tenant's whole history, so on evidence that has not
> changed it asks the same question and pays for the same answer. One
> measured pass over tenant `new` cost $0.34, proposed the two jobs it
> already knew and kept nothing -- and on an hourly sweep that is $8 a
> day to learn nothing.
>
> Two ways it IS worth paying. Evidence has arrived since the last pass
> started, which is the ordinary case. Or the last pass LEFT SOMETHING
> OUT: a day too big for one window is read across several passes, and
> the carry-over pool rotates which part -- ten simulated passes went 81%
> then 96% coverage, with nineteen gestures never shown. So a pass with
> evidence it could not hold has more to say about a day nobody added to,
> and a pass whose window held everything does not.
>
> **And the second way is bounded**, which it was not. A store bigger
> than one window leaves evidence out of EVERY pass -- 1,981 of 2,066 on
> this deployment, an average of 444 gestures against a window of 154 --
> so `left_out` was permanently true and the question below it was never
> reached. The sweep paid for a pass a minute over evidence nobody had
> added to: 463 passes on a day that captured 56 gestures, $220.95 of
> them, every captured gesture read about 352 times. Measured
> 2026-09-21, over 904 gestures and $937.46.
>
> The reasoning was right for ONE more pass and wrong for an unbounded
> sequence of them. The pool rotates which part of a day gets read, so
> enough passes to sweep the store once is exactly what "more to say"
> is worth -- and after that a pass sees what an earlier one already saw.
> So: as many extra passes as the store takes windows, counted since the
> last upload, and then quiet until somebody works again.
>
> A tenant that has never been mined is always worth a pass.

## `MineLately._worth_a_pass`, [line 68](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L68): Comment

Code: `last = passes[-1]`

> `passes` is oldest first, by `started_at` then id.

## `MineLately._worth_a_pass`, [line 70](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L70): Comment

Code: `if newest is not None and newest >= _when(last.started_at):`

> The pass's own clock, against the server's `received_at` on a batch.
> A pass that was refused before it read anything still wrote its row,
> so this is "since anything last looked", which is what it should be.
>
> `newest_arrival(tenant_id)`, not `tenants_since`. `tenants_since` answers
> for every tenant with a batch since the given time, so reading it here
> asked "has anybody's evidence changed" and answered it for THIS tenant --
> any tenant's new gestures made every other tenant worth a pass, and on a
> minute-by-minute sweep that is every tenant re-read on every other
> tenant's work. `newest_arrival` is the same `received_at` column, scoped
> to `tenant_id` the way the question actually is.

## `MineLately._worth_a_pass`, [line 73](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L73): Comment

Code: `return False`

> Evidence this tenant no longer has, or never had by this route.
> Nothing to sweep and nothing to count passes against.

## `MineLately._worth_a_pass`, [line 76](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L76): Comment

Code: `held = max(1, last.window_size)`

> How many windows this store takes, from what the last pass actually
> saw rather than from a count of the table: the window is what the
> budget allowed, and `left_out` is what would not fit beside it.

## `MineLately.execute`, [line 101](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L101): Comment

Code: `still_going = set(`

> Whoever is still uploading. Asked as "who has sent anything in the
> last `settle` seconds" rather than by reading a newest-upload
> column, because the port already answers that question and a
> second way to ask it is a second thing to keep true.

## `MineLately.execute`, [line 111](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L111): Comment

Code: `logger.info("%s: still working; leaving this one to settle", tenant_id.value)`

> Mid-task. This sweep runs every minute now, so the operator
> who is halfway through creating a supplier would otherwise be
> mined at the point they had filled two fields -- and half a
> job, proposed and kept, is a job that will be offered back
> half done. Waiting costs one interval and nothing else: the
> evidence does not go anywhere.

## `MineLately.execute`, [line 123](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L123): Comment

Code: `logger.info("%s: %s", tenant_id.value, reached)`

> Not an error and not a surprise: the cap is the deployment
> saying how much a day of learning may cost, and a sweep that
> logged an exception for it would cry wolf every hour after
> the budget was spent.

## module, [line 34](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L34): Note on the line above

Code: `_EVER = datetime(1970, 1, 1, tzinfo=UTC)`

> Every tenant that has ever recorded anything, not only those inside the
> mining window: deciding whether a job signs in costs no model call, and a
> tenant quiet for longer than the window is exactly the one whose jobs were
> left undecided.

## `MineLately._decide`, [line 81](../../../../../../../backend/src/sro/application/observation/mine_lately.py#L81): Note on the function

> Runs first on every sweep, before the "nothing new since the last pass"
> gate, so an undecided job is decided whether or not new gestures arrived.
> Under the tenant's mining lock, because it saves whole workflows the way
> the mining pass does. One tenant's failure is logged and the next tenant is
> still decided, like a failed pass.
