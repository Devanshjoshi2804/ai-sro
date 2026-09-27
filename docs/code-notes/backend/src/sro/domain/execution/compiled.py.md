# Notes for `backend/src/sro/domain/execution/compiled.py`

Notes for [`backend/src/sro/domain/execution/compiled.py`](../../../../../../../backend/src/sro/domain/execution/compiled.py). Each note names the code it explains (function or class, then the line in the current file) and says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/execution/compiled.py#L1): Docstring

> The compile check (spec §3, A4): whether a job can run, and why not. A pure
> function over what the runtime already loads -- the job, its cited gestures,
> its learned locators, the tenant's verified-write ledger and its known-broken
> lanes. It never writes and keeps no copy of the job: there is no stored
> recipe (L1). The job is compiled again on every read, so what it says is
> what the evidence says today.

## `Reason`, [line 27](../../../../../../../backend/src/sro/domain/execution/compiled.py#L27): Docstring

> One reason a job cannot run (or, in `Compiled.warnings`, something a reader
> should know although it runs), and the step it is about (`None` for the job).
> Each refusal enforces one line of spec §3:
>
> - `unbound_parameter` -- "every required parameter is bound to a step,
>   directly or through an alias". Required is `demanded`.
> - `unproven_write` -- "a recorded call with an expected status". Only a 2xx
>   proves a write: `expected_statuses` also collects 4xx and 5xx, and a job
>   "proven" by its recorded 400 would have the runtime's `accepts` call a
>   rejected write done.
> - `no_locator` -- "every UI step has at least one locator, recorded or
>   learned". Asked only where the UI lane is on the step's ladder.
> - `no_lane` -- a step with no primary gesture. This is exactly the rule the
>   start used to apply on its own (`unperformable`, now deleted), mail-read
>   steps included: a mail-read step cited only by a scroll was runnable here
>   and refused at the start. One rule, so the two cannot disagree.
> - `field_gone` -- X10b's value-aware rule, carried from `unperformable`. A
>   learned field step (`field_key`) has no gesture by design. It is refused
>   only when the run gives it a value and its label is no longer on its
>   write's latest outline (`field_of`). With no value it is passed over, and
>   the job-level view (`values=None`, no run yet) never asks.
>
> - `tab_role_unresolved` -- "every step's tab role resolves" (spec §5): a
>   step in `opened_from:R` with no earlier step in R, or a `tab_N` out of
>   sequence (`unresolved`).
>   Asked only of a decided job.
>
> Warnings, never refusals:
>
> - `tab_roles_undecided` -- a step stored before steps knew their tab (NULL
>   since 0086). It runs in the first tab, as every job did before, until the
>   mining sweep decides its roles; refusing it would take every stored job
>   offline for a column nothing had filled yet.
> - `every_lane_broken` -- every lane that could run the step failed lately.
>   A refusal here locked a job out for good: only a winning run mends a lane,
>   and a job no one is offered never runs. Broken lanes cool down instead
>   (`K_BROKEN_COOL_DOWN`), so after an outage the lane is tried again.
> - `fixed_values` -- user decision 2026-09-26: a job with no parameters whose
>   write sends a body of captured values runs, and the console says every run
>   writes the recorded values. A mining-quality case, not a runtime refusal.

## `Compiled`, [line 34](../../../../../../../backend/src/sro/domain/execution/compiled.py#L34): Docstring

> `runnable` is "no reasons"; warnings never change it. `view` is plain data for
> reading (`make recipe`, the console): each step's lanes, the lanes known
> broken, its locators with the learned one first, and the proof of its write.
> It is never an import format (L1). `fields` (C2) is every field the job
> could be given, classed `required`/`always`/`sometimes`/`never` with its
> limits -- computed by `field_classes` and mirrored into `view["fields"]`
> for a reader that only sees the wire shape.

## `why_not`, [line 42](../../../../../../../backend/src/sro/domain/execution/compiled.py#L42): Docstring

> The reasons as sentences, "Step N: ..." where a step is named, each said
> once. What the chat, the mail thread and the start's refusal all say.

## `_ladder`, [line 50](../../../../../../../backend/src/sro/domain/execution/compiled.py#L50): Docstring

> The ladder the executor would climb, built with the executor's own
> `lanes_for` and the same three inputs: `sends_mail` for the tool lane, a
> recorded call the ledger has verified for the API lane, and a primary
> gesture for the browser lanes. The API lane at run time also needs the
> run's values to aim the call; values are not known when a job is compiled,
> so this asks only whether the call could ever be replayed.
>
> A learned locator does not give a step with no cited gesture a browser lane:
> the executor opens the browser lanes only on a primary gesture. Learned
> field steps (`field_key`, X10b) are not merged yet; when they are, this and
> `no_lane` are the lines that learn about them.
>
> `broken` is passed empty so the ladder is the whole one; the known-broken
> lanes are compared against it in `compile_job`, because `lanes_for` never
> drops the last lane.

## `compile_job`, [line 60](../../../../../../../backend/src/sro/domain/execution/compiled.py#L60): Docstring

> `values` and `from_step` are the run's: the start passes its given values
> and D7's `check_from`, and reasons at steps before `from_step` are dropped,
> because those steps were done by the operator and are never sent. The offer
> view and the console compile with neither.
>
> A missing read-back is shown in the view and not refused. Spec §3 asks for a
> read-back "where one is known", so a write proven by its status alone
> compiles, and the view's `read_back: null` says which writes have no second
> witness.
>
> `declared` (C2) is the knowledge base's field limits, keyed by parameter
> name -- a caller with a unit of work in hand (`application.execution
> .declared.declared_limits`, already reading the KB's parsed recipe index)
> passes it here; a caller with none gets the page's own limits alone. It
> reaches `field_classes` unchanged: the stricter of page and knowledge base
> wins there, not in this function.

## `compile_job`, [line 74](../../../../../../../backend/src/sro/domain/execution/compiled.py#L74): Comment

Code: `filled = bindable(workflow, by_id)`

> Bound by what the run binds by. `value_for` fills a typed control from the
> value given under any name the control carries (its item id, field label or
> accessible name), and a parameter learned from the typing lives on the job,
> named by those names, with no step listing it. Reading only the steps'
> `parameters` called every such required parameter unbound, so the moment
> typed values became parameters (M3) the jobs that gained one stopped being
> runnable. `bindable` is the same set `undeliverable` checks a proposal
> against, so the miner and the compiler agree on what can be filled. Only
> the controls a step types into count (M3 round 1): a required "Customer
> Type" whose only match was a nav link of that name compiled as bound, and
> the run then had nowhere to type it.

## `compile_job`, [line 83](../../../../../../../backend/src/sro/domain/execution/compiled.py#L83): Comment

Code: `aliased = labelled(normal(said.get(normal(name), "")), fields)`

> A required parameter named by an alias is bound when the alias's label
> belongs to a parameter a step fills: the label is resolved to that
> parameter the way `field_of` resolves it, not compared by exact name.
