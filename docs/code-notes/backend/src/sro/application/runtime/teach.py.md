# Notes for `backend/src/sro/application/runtime/teach.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/teach.py`](../../../../../../../backend/src/sro/application/runtime/teach.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `Teach`, [line 21](../../../../../../../backend/src/sro/application/runtime/teach.py#L21): Class

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

## `Teach.learn`, [line 38](../../../../../../../backend/src/sro/application/runtime/teach.py#L38): Note

Code: `won = tried[-1] if tried and tried[-1].verdict in ("done", "read") else None`

> Only `done` or `read` is a success. An `unknown` is a write nobody
> confirmed; it mends nothing and teaches nothing.

## `Teach.learn`, [line 43](../../../../../../../backend/src/sro/application/runtime/teach.py#L43): Note

Code: `if result.verdict == "failed" and result.fingerprint and not result.expired:`

> An `expired` failure is the session's problem, not the lane's (X8 M4:
> `missing_header` never breaks a lane), and a failure with no fingerprint
> has nothing to be known by.

## `Teach.learn`, [line 69](../../../../../../../backend/src/sro/application/runtime/teach.py#L69): Note

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

## `_sighted`, [line 146](../../../../../../../backend/src/sro/application/runtime/teach.py#L146): Function

> The locator the sight lane learned from the element that satisfied the
> check (X7 ruling), or nothing: a learned map without a `frame_path` is
> never stored (X2 ruling). Nor is a query that holds a value filled this
> run -- a name read off a prefilled control would steer every later run to
> that record, and the learned locator is tried first -- nor one longer than
> `K_NAME`, the cap `learned_from` keeps (refused, not cut: a cut locator
> matches nothing, or something else).

## `Teach.learn_field`, [line 98](../../../../../../../backend/src/sro/application/runtime/teach.py#L98): Docstring

> A composed field the save's own call confirmed becomes part of the job: `grew`
> with `with_field`'s result, then its locator (`found_by` `composed` from the
> page code, `sight` from sight), in one unit of work that reads the job
> itself under its row lock. `pinned` is the version whose numbering the
> field's `before` is in, and the grow happens only while the job still is it.
> A field a step of the job already fills is not learned twice (a retried
> `finish`, or a sibling that learned it first); a field whose step a regrowth
> lost is learned again, under its one parameter. A locator that would carry the value is not kept.

## `Teach.learn_field`, [line 111](../../../../../../../backend/src/sro/application/runtime/teach.py#L111): Note

Code: `workflow = await _still(uow, ctx, pinned)`

> A compare-and-set against the run's own version, under the job's row lock.
> The field's `before` is a step number of that version, so it is placed only
> while the job still is that version. A run still going is no reason to wait:
> it reads its pin, never the grown steps, so growing
> under it cannot make it skip a step or send a write twice. A field refused
> here is not lost: the next run with that value composes it again against the
> job as it then is, and learns it then.

## `Teach.learn`, [line 40](../../../../../../../backend/src/sro/application/runtime/teach.py#L40): Note

Code: `if await _still(uow, ctx, workflow) is None:`

> What `learn` writes -- broken lanes, mends, locators -- is keyed by the job's
> step numbers, and `workflow` here is the run's pinned version. It teaches only
> while that is still the job's numbering; a run the job has grown past teaches
> nothing, rather than a locator under a number that is now another step's. The
> row lock keeps a grow from renumbering the job between this check and the
> writes.

## `Teach.locators`, [line 92](../../../../../../../backend/src/sro/application/runtime/teach.py#L92): Docstring

> The job's learned locators, for a run whose steps are `workflow`: all of them
> while the job still has those steps, none once it has grown past them (or was
> retired). The check and the read share the row lock, so a grow cannot commit
> between them and hand the run the new numbering's locators.

## `_still`, [line 138](../../../../../../../backend/src/sro/application/runtime/teach.py#L138): Docstring

> The job, read under its row lock, if it still has `workflow`'s steps; None if
> it has been renumbered or retired since. Everything this class learns or reads
> by step number goes through here, and so does every grow's own read (`_grow`,
> `learn_parameters`, `fill_in_passwords` take the same lock).

## `Teach.learn_field`, [line 116](../../../../../../../backend/src/sro/application/runtime/teach.py#L116): Comment

Code: `await decide_sign_ins(uow, ctx.tenant_id, [grown])`

> A learnt field changes the steps, so the verdict is decided again from the
> job it made (F3), in the same transaction and under the same row lock.
