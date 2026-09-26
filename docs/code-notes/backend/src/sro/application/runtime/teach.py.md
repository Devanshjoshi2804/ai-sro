# Notes for `backend/src/sro/application/runtime/teach.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/teach.py`](../../../../../../../backend/src/sro/application/runtime/teach.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `Teach`, [line 20](../../../../../../../backend/src/sro/application/runtime/teach.py#L20): Class

> Each lane teaches the one above (spec §6.3), per step and in data:
>
> - **A lane failed.** `(step, lane, fingerprint)` joins the known-broken
>   list with the step's `cites` key, so the next run starts at the first
>   lane still trusted and a new doing of the job clears it.
> - **A lane succeeded.** Its known-broken entries are mended.
> - **Sight succeeded.** The hit-tested locator, with its `frame_path`, is
>   saved on the step (`found_by="sight"`) and the UI lane is mended: the
>   next run succeeds on the UI lane (the repair).
> - **UI succeeded on a write its own call confirmed**, and the step has a
>   confirming read: the endpoint joins the verified-write ledger
>   (`verified_by="status"`), so a step whose API lane is not broken starts
>   on the API lane next run (the promotion). The promotion never mends a
>   broken API lane: only that lane's own success, or a new demonstration
>   that changes the step's cites, clears it.

## `Teach.learn`, [line 37](../../../../../../../backend/src/sro/application/runtime/teach.py#L37): Note

Code: `won = tried[-1] if tried and tried[-1].verdict in ("done", "read") else None`

> Only `done` or `read` is a success. An `unknown` is a write nobody
> confirmed; it mends nothing and teaches nothing.

## `Teach.learn`, [line 40](../../../../../../../backend/src/sro/application/runtime/teach.py#L40): Note

Code: `if result.verdict == "failed" and result.fingerprint and not result.expired:`

> An `expired` failure is the session's problem, not the lane's (X8 M4:
> `missing_header` never breaks a lane), and a failure with no fingerprint
> has nothing to be known by.

## `Teach.learn`, [line 66](../../../../../../../backend/src/sro/application/runtime/teach.py#L66): Note

Code: `own = next(`

> Promotion needs a read-back because the API lane cannot confirm a write
> without one (§6.2): a replay whose status is its only proof is a write
> sent blind. The call promoted is the write's own -- `same_call`, the UI
> lane's own rule: its frame, its host, the recorded method and path shape,
> and every recorded body key. No composed field is in play here
> (`Adding()`), so a call with a key beyond the recorded ones is not the
> write's own and never teaches (§6.6.4): a write that followed a field the
> recorded body lacks is not offered the API lane (§6.6.7). The pattern is
> learned from the call this run sent, with this run's values and the
> recorded URL (`learned_pattern`), so a path that names the record becomes
> `{id}` and a segment the recording holds fixed stays fixed.

## `_sighted`, [line 131](../../../../../../../backend/src/sro/application/runtime/teach.py#L131): Function

> The locator the sight lane learned from the element that satisfied the
> check (X7 ruling), or nothing: a learned map without a `frame_path` is
> never stored (X2 ruling). Nor is a query that holds a value filled this
> run -- a name read off a prefilled control would steer every later run to
> that record, and the learned locator is tried first -- nor one longer than
> `K_NAME`, the cap `learned_from` keeps (refused, not cut: a cut locator
> matches nothing, or something else).

## `Teach.learn_field`, [line 89](../../../../../../../backend/src/sro/application/runtime/teach.py#L89): Docstring

> A composed field the save's own call confirmed becomes part of the job: `grew`
> with `with_field`'s result, then its locator (`found_by` `composed` from the
> page code, `sight` from sight), in one unit of work that reads the job
> itself -- never a copy read earlier, which a sibling's `finish` may have
> grown since. A field a step of the job already fills is not learned twice
> (a retried `finish`, or a sibling that learned it first); a field whose step
> a regrowth lost is learned again, under its one parameter. A locator that
> would carry the value is not kept.

## `Teach.learn_field`, [line 105](../../../../../../../backend/src/sro/application/runtime/teach.py#L105): Note

Code: `runs = await uow.workflow_runs.for_workflow(ctx.tenant_id, workflow.id)`

> Never while another run of the job is still going: growing renumbers the steps
> under it, and a run whose `progress.step` and marks point at the old numbers
> could perform a write twice. The field is not lost: the next run with that
> value composes it again from the outline and learns it then.
>
> **Ceiling.** The check and the growth are two statements, so a run that starts
> in between is not seen. The upgrade is a shape version on the run, checked by
> `step`. A mining pass that grows a job (`_grow`) has no such check at all.
