# Notes for `backend/src/sro/application/skill/serve_shapes.py`

Comments and docstrings moved out of [`backend/src/sro/application/skill/serve_shapes.py`](../../../../../../../backend/src/sro/application/skill/serve_shapes.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/skill/serve_shapes.py#L1): Docstring

> Every proven workflow of a tenant, as the extension needs it.
>
> Ported from `shapes_for` in `new_agent_arch/src/rig/shapes.py`. The arithmetic
> -- given a workflow's cited pairs, its held tally and its counsel, what shape
> comes out -- is `sro.domain.skill.shape.shape_of`, which plan 1 took whole.
> What is here is the half that needed a store: the loop over a tenant's
> workflows, the gate each one has to pass, and the three reads behind every
> shape that is served.
>
> `rekey_workflows` was landed here by Task 7 and has since moved to
> `sro.application.observation.mining_pass`, where the plan's file map and the
> rig both put it. It walks the same evidence, but it WRITES, and this module's
> promise is that nothing in it does -- two session contracts in one file is a
> docstring that is false twelve lines below where it is made.

## module, [line 29](../../../../../../../backend/src/sro/application/skill/serve_shapes.py#L29): Note on the line above

Code: `K_ONLY_EVER_FAILED = 3`

> How many times a job must fail on its own account before it stops being
> offered.
>
> One is a slow page, a modal that was still open, a browser that went away
> mid-step -- and one was enough to take a job off every browser this tenant has,
> permanently, because a job nobody is offered is a job nobody runs. Three is the
> same shape as every other streak in this system: enough to be a pattern rather
> than a bad night.

## `ServeShapes`, [line 14](../../../../../../../backend/src/sro/application/skill/serve_shapes.py#L14): Docstring

> The extension's list, with this container's clock.
>
> Beside `shapes_for` rather than in a module of its own: it is the same
> read, under the same promise that nothing here writes, and four lines
> wrapping the function directly below them do not need a file.
>
> A class and not a container method, which is what plan 4a's task 2 wrote.
> The clock is kept just as far from the route either way -- it is supplied
> here, and `RevokeDevice` does exactly this three lines away in the same
> container. What the method could not do is take a `RequestContext`: handed
> a bare `tenant_id`, the route unpacks the caller itself, which puts the
> tenant boundary in the interface layer at the one seam where passing the
> wrong tenant is the failure.
>
> `device_id` is the asking browser and is passed through rather than
> defaulted: it decides whose refusals earned the rest, so dropping it serves
> one browser the rest another browser earned. Keyword-only for the same
> reason -- `(ctx, device_id)` has no other argument to be swapped with
> today, and this is the call site that must not gain one.

## `shapes_for`, [line 32](../../../../../../../backend/src/sro/application/skill/serve_shapes.py#L32): Docstring

> Every proven workflow, as the extension needs it. `device_id` is the
> asking browser, for the rest its own refusals earned it.
>
> **What counts as failing, and how often.** The gate was "ran and never
> held", and that emptied this deployment's panel: twelve runs of the sign-in
> job, eleven of them `stopped` -- the job asking for a password it did not
> have -- and the job disappeared from the browser that was trying to finish
> it. Every job an operator actually does was in that state, and the rule
> feeds itself: a job that is not served is never offered, is never run, and
> can never hold. So a run that stopped to ask is not a failure, nor is one a
> person aborted, and `K_ONLY_EVER_FAILED` real failures are needed before a
> job goes quiet.
>
> A workflow that has been run is asked a harder question -- has it ever
> held -- because an offer to do a job the runner has only ever failed is an
> offer to fail in front of somebody. The gate is per workflow and not per
> tenant: one workflow's first failure must not silence every sibling that
> has simply never been run. And a job that has never run at all is served,
> because it has not failed anything -- it has sat no test.
>
> Nothing after that gate is fatal either. A workflow that cites evidence
> the store no longer holds, or that starts on an origin its own evidence
> never names, is skipped where it stands. This is asked by every browser on
> every gesture cache miss, and one bad row emptying the panel is the whole
> tenant losing its jobs over one of them.
>
> `now` is the caller's clock, passed on to `counsel` and never read in
> here, so a test can move it. Nothing writes, so nothing commits: the
> caller owns the session.
>
> The tally is one read for the whole tenant, before the loop. It was
> `for_workflow` per proven workflow, which loads every run ever recorded
> with all of its steps to arrive at two integers. Counted against real
> Postgres, three workflows of four runs: this function issued 14
> statements, 6 of them against the runs tables; it now issues 9 and 1. The
> 6 were linear in total run rows, so a tenant with a year of use would have
> read ~100k run rows and ~500k step rows here -- and this is the read every
> browser makes on every gesture cache miss, so it degraded exactly as a
> customer succeeded. The rig used two index counts; `tallies` is those,
> batched.

## `ServeShapes.execute`, [line 20](../../../../../../../backend/src/sro/application/skill/serve_shapes.py#L20): Comment

Code: `async with self._uow as uow:`

> `shapes_for` reads repositories, and a `UnitOfWork` has none until
> its session opens on entry -- so the block is opened here and not
> inside the function, whose other callers already hold one. Nothing
> commits: the read-only promise this module makes is untouched.

## `shapes_for`, [line 43](../../../../../../../backend/src/sro/application/skill/serve_shapes.py#L43): Comment

Code: `_, held = tallied.get(workflow.id, (0, 0))`

> Absent means never run, which is not the same as run and never held.

## `shapes_for`, [line 47](../../../../../../../backend/src/sro/application/skill/serve_shapes.py#L47): Comment

Code: `if not wanted:`

> Not a null check -- `shape_of` makes one of those below, over the
> same emptiness. This is the round trip: `gestures_for` with no ids
> is `IN ()` against Postgres, asked once per cite-less workflow by
> every browser on every cache miss.
