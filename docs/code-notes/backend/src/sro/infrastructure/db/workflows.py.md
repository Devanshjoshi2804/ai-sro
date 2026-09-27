# Notes for `backend/src/sro/infrastructure/db/workflows.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/workflows.py`](../../../../../../../backend/src/sro/infrastructure/db/workflows.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L1): Docstring

> Mined workflows on Postgres: their steps, their passes, and what they earned.
>
> The rules here are the rig's -- ``rig/workflows.py``, ``rig/effects.py``, the
> ``passes`` insert and the ``rekey`` update in ``rig/mine.py``, the
> ``workflow_stale`` insert and delete in ``rig/runner.py``, and the stale count
> in ``rig/api.py``. They were SQLite there. What had to be translated rather
> than copied is marked where it happens:
>
> * ``INSERT OR REPLACE`` becomes ``ON CONFLICT DO UPDATE`` on a named conflict
>   target, as in ``workflow_runs``. SQLite's form swallows *every* constraint;
>   naming the target means a different constraint failing is still an error
>   rather than a silent no-op.
> * The clocks are ``timestamptz`` where the rig kept text, because both indexes
>   order on one and an offset-less string sorts beside an offset-bearing one
>   with neither wrong. The records still carry ISO strings, so this converts on
>   both edges.
> * ``earned`` was a boolean the store computed. Here the store assembles the
>   evidence -- one ``RunProof`` per live held run -- and ``earned_from`` in
>   ``sro.domain.execution.belts`` decides. The rule about how many runs and
>   which belts count is the domain's; walking the rows is this file's.
> * The gate on ``record_effect`` is likewise the domain's ``state_verified``
>   rather than a second copy of the belt list. A picture is not an effect, and
>   that must be one sentence in one place.
>
> The row-to-record mapping lives here rather than in ``mappers.py``: a
> repository's mapping belongs with the repository, and these shapes are read by
> nothing else.

## `SqlWorkflowRepository.remember_limit`, [line 387](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L387): Docstring

> What this step's box will take, learnt once.
>
> Its own method rather than a field on `remember_locator`, because the
> two are learnt at different moments and about different things: a
> locator is learnt when the recorded identity failed, and a limit is
> learnt on a step whose locator matched perfectly well. Writing them
> together would mean a truncation erasing a locator, or a locator
> erasing a limit -- so each writes only its own columns, and a step can
> carry both.

## `SqlWorkflowRepository._keep_what_changed`, [line 449](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L449): Docstring

> Append what this step just learned that it did not already know.
>
> Read-then-write, and deliberately not a transaction of its own: it runs
> inside the run's, so a history row and the learned row it describes
> arrive together or not at all. A history that disagrees with the thing
> it is a history of is worse than none.
>
> Silent on every failure. This is a record FOR somebody, and a run that
> fell over because it could not write one would have turned reading into
> a reason to stop working.

## `SqlWorkflowRepository.taught_itself`, [line 475](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L475): Docstring

> What this job has changed its mind about, newest first.
>
> The one query the history is for. A history nobody can read in one page
> is a log, which is why there is a limit and why it is small.

## `SqlWorkflowRepository._steps_of`, [line 753](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L753): Docstring

> One query for every workflow's steps rather than one per workflow.

## `_row_to_step`, [line 86](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L86): Comment

Code: `uses=list(row.uses or []),`

> An older row has no `uses` at all, and a job that predates the column
> used nothing -- which is what an absent one honestly means.

## `SqlWorkflowRepository.save`, [line 167](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L167): Comment

Code: `async with self._session.begin_nested():`

> One job, one savepoint: its row and its steps go in together, or neither
> does. A step insert that fails (on the server, or in the driver before it,
> which leaves the transaction alive) rolls the job's row back with it. The
> mining pass's `finally` commits whatever the transaction holds, to keep
> the bill; before this it could commit a job row with no steps. Jobs saved
> earlier in the same pass are outside this savepoint and survive.

## `SqlWorkflowRepository.save`, [line 173](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L173): Comment

Code: `set_={`

> Every column but the key and ``created_at`` (changed 2026-09-24). A job's
> creation time never changes: a re-save by identity resolution, a learnt
> parameter or a healing pass is not a new job, so it keeps its place in
> ``known`` and is not "noticed" again by the summary. The rig this once
> matched (INSERT OR REPLACE moved a re-saved job to the end) is gone.
>
> Except ``retired_at``: the domain workflow does not carry it, so the
> insert's value is always NULL, and copying it over would bring a
> retired job back the next time anything re-saved the row -- a
> healing pass, a parameter learnt, a growth.
>
> And only the columns the insert supplied (M1 round 1). `same_as` stays in
> the schema with nothing mapping it (GC 17); copying every table column
> wrote NULL over what an old row held.

## `SqlWorkflowRepository.save`, [line 180](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L180): Comment

Code: `await self._session.execute(`

> Deleted and reinserted rather than upserted one by one: a step the
> merge dropped has to leave the store with it, and an upsert would
> leave it behind.

## `SqlWorkflowRepository.known`, [line 194](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L194): Comment

Code: `.order_by(WorkflowRow.created_at, WorkflowRow.id)`

> The id breaks a tie the rig never had to: two workflows of one
> pass are saved microseconds apart there and can share an instant
> here, and an order that is not total is an order that changes
> between reads.

## `SqlWorkflowRepository.known`, [line 193](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L193): Comment

Code: `.where(WorkflowRow.tenant_id == tenant_id.value, WorkflowRow.retired_at.is_(None))`

> A retired job is not known: not to the miner's list of jobs already proven,
> not to the shapes a browser is offered, not to a chat asked what it can do.
> `get` refuses it the same way, so a run or a trigger naming it is a 404.
> Filtered here, once, rather than at every caller of the two.

## `SqlWorkflowRepository.retire`, [line 252](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L252): Docstring

> Retire a live job of this tenant's, or NotFound -- for another tenant's
> job, an id nobody minted and a job already retired alike: the first
> retirement's instant is the one kept.

## `SqlWorkflowRepository.place`, [line 266](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L266): Docstring

> Record gestures a job has explained without citing them: a doing folded
> into it, or the doing a growth replaced. First placement wins; a gesture
> is placed once per tenant.

## `SqlWorkflowRepository.placed`, [line 282](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L282): Docstring

> Every gesture any job of this tenant cites, retired jobs included, and every
> gesture `place` recorded. What
> the mining pass does not read again: a gesture a job already explains is
> not new work, and a retired job's gestures read again would be mined
> straight back into the job the operator dropped.

## `SqlWorkflowRepository.known`, [line 195](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L195): Comment

Code: `.execution_options(populate_existing=True)`

> ``save`` upserts with a Core statement, so a row this session had
> already loaded would otherwise come back at its pre-save state.

## `SqlWorkflowRepository.add_pass`, [line 330](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L330): Comment

Code: `try:`

> A plain insert, as in the rig, and no ON CONFLICT: a pass id is
> minted per reading, so a second row under one id would be one model
> call billed twice. Reported as a Conflict rather than escaping as an
> IntegrityError out of somebody else's commit.

## `SqlWorkflowRepository.mark_stale`, [line 371](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L371): Comment

Code: `statement = pg_insert(WorkflowStaleRow).values(`

> The rig's INSERT OR REPLACE: one row per step, so a job run every
> morning reports the same weak step once rather than daily. The later
> notice wins, because the last rung a step matched on is the current
> answer about that step.

## `SqlWorkflowRepository.remember_limit`, [line 390](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L390): Comment

Code: `already = next(`

> A limit is learnt on a step whose locator matched perfectly well, so
> what is compared here carries the locator this step already has --
> otherwise every measured limit would read as a locator being erased.

## `SqlWorkflowRepository.remember_limit`, [line 407](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L407): Comment

Code: `strategy="",`

> Empty rather than absent, for a step that has never needed a
> locator learnt: the columns are not null, and "" is honestly what
> is known about a locator nobody has had to find.

## `SqlWorkflowRepository.remember_locator`, [line 426](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L426): Comment

Code: `await self._keep_what_changed(workflow_id, learned, by_run=by_run)`

> Before the upsert, because the upsert is what destroys the answer it
> is compared against.

## `SqlWorkflowRepository.remember_locator`, [line 427](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L427): Comment

Code: `statement = pg_insert(WorkflowLearnedRow).values(`

> The stale row's shape, and for its reason: one row per step, the
> later notice winning, because the last locator that worked is the
> current answer about that step.

## `SqlWorkflowRepository._keep_what_changed`, [line 461](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L461): Comment

Code: `id=f"lrn_{workflow_id}_{change.ord}_{change.about}_{at.timestamp()}"[:64],`

> The step and the moment, which is what makes it
> unique: one step cannot change its mind twice in the
> same microsecond, and a uuid here would be a second
> thing to explain.

## `SqlWorkflowRepository.grew`, [line 614](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L614): Comment

Code: `keyed_by_ord: tuple[type[Any], ...] = (`

> Read, delete, reinsert -- rather than an UPDATE per row. The key is
> `(workflow_id, ord)` and a growth renumbers several at once, so an
> update that moved 3 to 5 while 5 was still there would collide on a
> primary key for no reason but the order the rows came back in.

## `SqlWorkflowRepository.grew`, [line 637](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L637): Comment

Code: `if kept:`

> A step the new shape does not have is a step nobody performs,
> and a locator for it is one nobody can check. Dropped with it.

## `SqlWorkflowRepository.remember_write`, [line 653](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L653): Comment

Code: `if not state_verified(verified_by):`

> The same gate `record_effect` keeps, kept here for the same reason:
> once, by the repository, so no caller can forget it. A model reading
> a picture is not evidence that an endpoint works, and this is the
> fact that licenses sending one without a click.

## `SqlWorkflowRepository.remember_write`, [line 665](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L665): Comment

Code: `await self._session.execute(`

> First proof wins and later ones change nothing. The row says which
> run first earned the endpoint, which is what somebody asking "why is
> this being sent without a click" needs in order to go and read it.

## `SqlWorkflowRepository.record_effect`, [line 680](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L680): Comment

Code: `if not state_verified(verified_by):`

> The gate, before the write: a verdict that did not see the state
> itself is not an effect, and a screenshot is not evidence anything
> was written. Dropped rather than stored-and-filtered, so nothing
> downstream has to remember to ask again.

## `SqlWorkflowRepository.record_effect`, [line 689](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L689): Comment

Code: `await self._session.execute(`

> One write of one run of one job is one effect however many times it
> is verified -- a write rescued to the second rung verifies at the
> same step, and that is not two proofs.

## `SqlWorkflowRepository.forget_effects`, [line 700](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L700): Comment

Code: `gone = await self._session.execute(`

> RETURNING rather than ``rowcount``, as everywhere else here: how many
> a job had earned is the answer the caller wants, and a driver's
> rowcount is not the same promise across drivers.

## `SqlWorkflowRepository.proofs`, [line 724](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L724): Comment

Code: `wrote: defaultdict[str, set[int]] = defaultdict(set)`

> Three queries whatever the number of runs, rather than two per run.

## `SqlWorkflowRepository.proofs`, [line 731](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L731): Comment

Code: `if result and result.get("wrote"):`

> The step's own marker, set by the runner at send time: SQL cannot
> ask ``writes()``, and the evidence a later reader would have to
> ask it about may have been re-mined by then. Read for truth here
> rather than as ``->>'wrote' = 'true'`` in the WHERE, so the
> predicate stays the rig's own -- truthy on whatever the runner
> marks with -- rather than a narrower one that would silently miss
> a writer emitting 1 or "yes".

## `SqlWorkflowRepository.broken_for`, [line 515](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L515): Note

> A lane known broken holds only while the step still cites the doing it
> broke on: each row keeps the step's `cites_key` from then, and only rows
> whose key equals the step's current one are answered. A new doing of
> the job (new evidence, so new cites) gives every lane a fresh chance
> without anyone deleting a row. The filter is in Python: a job has a
> handful of rows.

## `SqlWorkflowRepository.grew`, [line 618](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L618): Note

Code: `KnownBrokenRow,`

> A lane known broken on a step moves with it too: left behind, it would skip a
> working lane on the step that now has that number, and leave the moved step
> retrying one that is known not to work.

## `workflow_json`, [line 113](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L113): Docstring

> A job as its own rows: the `workflows` row's columns (bar `created_at`) and
> its `workflow_steps` rows, the encoding `save` and `get` already use. A run's
> pin is stored this way, and migration 0082's backfill writes the same shape
> from the rows themselves (`to_jsonb`), so there is one encoding of a step and a
> repeat, not three that could drift -- a drift here would quietly make every
> pinned run differ from its job and turn its learning off.
>
> A pin outlives the schema it was written under. Decoding keeps only the
> keys that are still columns (`_known`), so a migration that drops a column
> from `workflows` or `workflow_steps` leaves every stored pin loadable; it
> does not need to rewrite `workflow_runs.pinned`. A column added later is
> absent from an older pin and takes the row's default.

## `SqlWorkflowRepository.confirm_recipient`, [line 560](../../../../../../../backend/src/sro/infrastructure/db/workflows.py#L560): Docstring

> One row per tenant, job and address; a later answer naming the same address
> replaces who and when.
