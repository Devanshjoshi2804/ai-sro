# Notes for `backend/src/sro/interface/http/v1/routers/threads.py`

Comments and docstrings moved out of [`backend/src/sro/interface/http/v1/routers/threads.py`](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `run_from_thread`, [line 81](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L81): Comment

Code: `raise InvariantViolation("a run started from a thread must name a skill_id")`

> Caught here, before any workflow starts: without this, a missing
> skill_id started a durable run against no skill at all, and the only
> sign of it was a 404 from the *next* line -- one whose real cause was
> already off running as an orphaned workflow.

## `run_from_thread`, [line 83](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L83): Comment

Code: `skill = await container.get_skill().execute(ctx, skill_id=skill_id)`

> Read before the workflow starts, not after: a skill id that names nothing
> answered 404 from below while the workflow it had already scheduled went
> off to fail on its own, out of sight of the request that caused it.

## `run_from_thread`, [line 84](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L84): Comment

Code: `await container.start_run().check(`

> Refused here or not at all. This answers before the run begins, so a
> refusal raised inside the workflow -- a skill at a stage that may not run,
> a breaker asking for a person -- reached nobody: the request had already
> answered 201 with the id of a run that was never created, and the console
> sat on "opening the connection" for a run that had been stopped on
> purpose.

## `run_from_thread`, [line 93](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L93): Comment

Code: `run_id = container.ids.new_run_id()`

> Named before it starts, so the console can watch the steps land instead
> of holding this request open for as long as the warehouse takes.

## `pursue`, [line 131](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L131): Comment

Code: `if (busy := container.pursuits.working()) is not None:`

> One screen, one pursuit. The provider behind this deployment has a single
> browser, so a second pursuit does not get a second screen -- it drives the
> same one, mid-task, and both navigate it out from under each other. Two
> pursuits then report, separately and truthfully, that the screen would not
> respond to anything they did.

## `pursue`, [line 138](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L138): Comment

Code: `if goal.changes_the_system and not body.authorized_by:`

> Answered here as well as refused inside, because 202 with a pursuit that
> fails a second later reads as "it tried and could not" rather than "you
> have not confirmed this".

## `pursue.drive`, [line 166](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L166): Comment

Code: `await container.converse().note(`

> The thread outlives the process; the progress does not. What
> happened has to end up somewhere an operator can read tomorrow.

## `say`, [line 218](../../../../../../../../../backend/src/sro/interface/http/v1/routers/threads.py#L218): Comment

Code: `last = thread.messages[-1] if thread.messages else None`

> What this system made of what they said, in the thread's own vocabulary.
>
> `nothing` where the answer carried no decision at all -- the words went
> in and the thread went on as it was. Measured on the deployment
> 2026-09-20: an operator was asked for an Address, typed one, and the
> thread read the sentence as a fresh request and offered a different job
> while the first card went on waiting. Nothing anywhere recorded that
> their answer had not been taken as one.
