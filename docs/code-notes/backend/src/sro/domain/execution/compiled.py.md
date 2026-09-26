# Notes for `backend/src/sro/domain/execution/compiled.py`

Notes for [`backend/src/sro/domain/execution/compiled.py`](../../../../../../../backend/src/sro/domain/execution/compiled.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/compiled.py#L1): Docstring

> The compile check (spec §3, A4): whether a job can run, and why not. A pure
> function over what the runtime already loads -- the job, its cited gestures,
> its learned locators, the tenant's verified-write ledger and its known-broken
> lanes. It never writes and keeps no copy of the job: there is no stored
> recipe (L1). The job is compiled again on every read, so what it says is
> what the evidence says today.

## `Reason`, [line 22](../../../../../../../backend/src/sro/domain/execution/compiled.py#L22): Docstring

> One reason a job cannot run, and the step it is about (`None` for the job
> as a whole). Each code enforces one line of spec §3:
>
> - `unbound_parameter` -- "every required parameter is bound to a step,
>   directly or through an alias". Required is `demanded`, the rule the
>   runner and the run's question already read.
> - `unproven_write` -- "every write step has a proof: a recorded call with an
>   expected status". A write whose recorded call carries no status (or only
>   failed ones) can never be settled by its status.
> - `no_locator` -- "every UI step has at least one locator, recorded or
>   learned". Only asked where the UI lane is on the step's ladder.
> - `no_lane` -- a step no lane can run at all (no mail tool, no replayable
>   call, no gesture a browser can act on). The start path refuses the same
>   job with "has no evidence a browser can act on"; this says so before a
>   request is ever offered it.
> - `every_lane_broken` -- "no step is in the known-broken list for its
>   current cites on every lane". One live lane is enough.

## `Compiled`, [line 29](../../../../../../../backend/src/sro/domain/execution/compiled.py#L29): Docstring

> `runnable` is "no reasons". `view` is plain data for reading
> (`make recipe`, the console): each step's lanes, the lanes known broken,
> its locators with the learned one first, and the proof of its write. It is
> never an import format (L1).

## `_ladder`, [line 35](../../../../../../../backend/src/sro/domain/execution/compiled.py#L35): Docstring

> The ladder the executor would climb, built with the executor's own
> `lanes_for` and the same three inputs: `sends_mail` for the tool lane, a
> recorded call the ledger has verified for the API lane, and a primary
> gesture for the browser lanes. The API lane at run time also needs the
> run's values to aim the call; values are not known when a job is compiled,
> so this asks only whether the call could ever be replayed.
>
> A learned locator does not give a step with no cited gesture a browser lane:
> the executor opens the browser lanes only on a primary gesture. Learned
> field steps (`field_key`, X10b) are not merged yet; when they are, this is
> the one line that learns about them.
>
> `broken` is passed empty so the ladder is the whole one; the known-broken
> lanes are compared against it in `compile_job`, because `lanes_for` never
> drops the last lane and so could never say "every lane is broken".

## `compile_job`, [line 45](../../../../../../../backend/src/sro/domain/execution/compiled.py#L45): Docstring

> A missing read-back is shown in the view and not refused. Spec §3 asks for a
> read-back "where one is known", so a write proven by its status alone
> compiles, and the view's `read_back: null` tells a reader which writes
> have no second witness.
>
> A step that only reads the mail the run came from has no ladder and is not
> a `no_lane`: the executor answers it as already read.
