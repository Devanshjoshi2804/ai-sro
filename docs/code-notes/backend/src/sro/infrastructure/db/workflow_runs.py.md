# Notes for `backend/src/sro/infrastructure/db/workflow_runs.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/db/workflow_runs.py`](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L1): Docstring

> Runs of a mined workflow on Postgres: their steps, and the approvals on them.
>
> The rules here are the rig's -- ``rig/runs.py`` plus the approval insert and
> the awaiting query in ``rig/api.py`` -- and they were SQLite there. What had to
> be translated rather than copied is marked where it happens:
>
> * ``INSERT OR REPLACE`` on a run and ``INSERT OR IGNORE`` on an approval become
>   ``ON CONFLICT DO UPDATE`` and ``ON CONFLICT DO NOTHING`` on a named conflict
>   target. SQLite's forms swallow *every* constraint; naming the target means a
>   different constraint failing is still an error rather than a silent no-op.
>   On the approval it also buys the answer: ``RETURNING`` says whether this tap
>   was the one that authorised the step, where SQLite gave a rowcount.
> * The rig kept every clock as text. ``started_at`` and ``finished_at`` are
>   ``timestamptz`` here because both indexes order on ``started_at`` and an
>   offset-less string sorts beside an offset-bearing one with neither wrong. The
>   records still carry ISO strings, so this converts on both edges.
> * ``fail_orphans`` sweeps every tenant, which is not an oversight: it runs once
>   at startup with nobody making the request, and a run left ``running`` in one
>   tenant goes on 409-ing its browser however healthy the others are.
>
> The row-to-record mapping lives here rather than in ``mappers.py``: a
> repository's mapping belongs with the repository, and these three shapes are
> read by nothing else.

## module, [line 150](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L150): Note on the line above

Code: `executor=cast(Executor, row.executor),`

> Trusted because `ck_workflow_runs_executor` is: the column reads back as a
> bare `str` from SQLAlchemy, and `WorkflowRun.executor` is the narrower
> `Literal["extension", "steel"]` the rest of this task's rules are keyed on.
> Nothing else can be in this column -- a value outside those two was refused
> at INSERT -- so the cast trusts the constraint rather than re-checking it
> in Python on every read.

## module, [line 154](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L154): Note on the line above

Code: `_ONE_RUNNING = "uq_workflow_runs_one_running_per_device"`

> The one constraint on `workflow_runs` whose violation this module has a
> sentence for. Matched as a substring of the driver's own message: asyncpg and
> psycopg both name the index there, and `orig.diag.constraint_name` is spelled
> differently on each.

## `SqlWorkflowRunRepository.driving_windows`, [line 315](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L315): Docstring

> Three columns rather than whole runs.
>
> The caller wants to know whether a browser was being driven at an
> instant, and a run row carries its steps, its withheld writes and
> everything a model said about it. Reading those to compare two
> timestamps would make a check that exists to be cheap the most
> expensive thing in a mining pass.

## `SqlWorkflowRunRepository.waiting_on`, [line 342](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L342): Docstring

> Against the expression index 0062 adds, and never on a blank.
>
> Only a run that is actually waiting on a person counts: stopped with
> `needs`, or running and parked on a question (`progress.asking`). The
> same rule as `waiting.asks_a_person`, which the fake uses. A run still
> working its steps, or finished with nothing asked, keeps its `awaiting`
> for the reply it will send, but a later mail on that thread -- a
> "thanks!", a colleague's reply-all -- is not an answer to anything, and
> routing it to the run would start the job again.
>
> `waiting_on` refuses to build a wait with no conversation in it, so
> nothing WRITES a blank thread -- but a hand edit, a restore, or a row
> from a deployment that did can leave one, and without this guard a
> caller asking about `""` matches it. That is one run answering a reply
> to something else entirely, which is a warehouse record written from
> somebody's unrelated sentence.

## `SqlWorkflowRunRepository._with_steps`, [line 444](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L444): Docstring

> One query for every run's steps rather than one per run.

## `SqlWorkflowRunRepository.save`, [line 166](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L166): Comment

Code: `index_elements=["id"],`

> The id, and only the id. A second running run for a
> browser that already has one violates
> `uq_workflow_runs_one_running_per_device`, which is NOT
> this conflict target, so it raises rather than quietly
> updating somebody else's row -- which is the whole point
> of naming the target instead of swallowing every
> constraint the way SQLite's INSERT OR REPLACE did.

## `SqlWorkflowRunRepository.save`, [line 167](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L167): Comment

Code: `set_={`

> Every column but the key and `progress` takes the new value, which is what
> INSERT OR REPLACE did before this task: a run was written whole after every
> step, so the later write superseded the earlier one. `progress` is the one
> exception, because the run it is written whole FROM is not always the run
> that last touched `progress` -- an API path can load a run, wait on a mail
> reply, and save its copy back long after a worker settled a step on the
> same row. Excluded from this `UPDATE SET`, it is left exactly as the row
> already has it; `record_progress` is the only path that ever changes it.

## `SqlWorkflowRunRepository.save`, [line 176](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L176): Comment

Code: `raise`

> Some OTHER constraint. Every integrity violation used to be
> reported as "that browser is already running a run this press
> cannot see" -- a sentence about a different problem, naming a
> run that would be `None` because there isn't one, with the
> caller's transaction already rolled back underneath it so the
> real cause could not be recovered from the response. There is
> no second constraint a legal save can violate today, which is
> exactly why nobody would find this the day one is added.

## `SqlWorkflowRunRepository.save`, [line 177](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L177): Comment

Code: `await self._session.rollback()`

> One browser, one hand -- enforced here because the caller's own
> `in_flight` read cannot enforce it: between that read and this
> there are awaits, and two presses on one event loop both read
> free. The session is finished either way, so it is rolled back
> before the sentence is composed, which is also what makes the
> read below possible: the winner's row is visible once this
> transaction is gone.

## `SqlWorkflowRunRepository.save`, [line 186](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L186): Comment

Code: `index_elements=["run_id", "ord"],`

> Upserted by `(run_id, ord)` rather than deleted and reinserted, same reason
> as `progress`: the run this call carries is not always the run that last
> touched a later step. A worker appends step 2 and saves; an API path holding
> a copy from before that -- steps 0 and 1 only -- saves its own change
> afterwards. Delete-then-insert would remove step 2 along with it, an
> operator-visible step vanishing under a save that never claimed to touch
> it. Upserting only ever adds or updates a step this call actually carries,
> so the second save of a run still does not double its first step -- the
> rule this replaced -- but a step this call is silent about is left alone
> rather than swept away with everything else.

## `SqlWorkflowRunRepository.record_progress`, [line 195](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L195): Docstring

> A bare `UPDATE ... SET progress`, and the only place this column is
> written after a run's first insert. `save` takes a whole in-memory
> `WorkflowRun` and can be built from a copy loaded before a worker last
> touched this row's progress; writing that copy back through `save` must
> never carry a stale `progress` over the worker's own writes. This method
> is how a worker settles a step -- load, mark, `record_progress` -- without
> going through the whole-row path at all.
>
> Scoped by `tenant_id`, like every read, and answers with whether a row
> actually matched: a bare `UPDATE` that touches zero rows is not an error at
> the SQL level, and a worker that believed a `False` return was a silent
> success would carry on thinking a mark was durable when the run it named
> does not exist, or belongs to somebody else's tenant.

## `SqlWorkflowRunRepository.for_workflow`, [line 228](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L228): Comment

Code: `query.order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)`

> The id breaks a tie the rig never had to. Two runs of one
> workflow routinely start in the same instant -- one form
> submits them -- and `started_at` alone leaves Postgres free to
> return them in heap order, which is an order that changes
> between reads. `proofs` has always broken the tie this way.

## `SqlWorkflowRunRepository.recent`, [line 241](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L241): Comment

Code: `query = self._rows().where(WorkflowRunRow.tenant_id == tenant_id.value)`

> The rig's list query (`api.py:1152`), filters and all: tenant, then
> the job if one was named, then the named set `awaiting=true` narrows
> to -- and the cap last, after every predicate, because a cap applied
> before them answers "nothing is waiting" out of a busy tenant.

## `SqlWorkflowRunRepository.recent`, [line 245](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L245): Comment

Code: `query = query.where(WorkflowRunRow.id.in_(sorted(ids)))`

> An empty set is not "no filter": it is "nothing matches", and
> `in_` of nothing is exactly that.

## `SqlWorkflowRunRepository.recent`, [line 248](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L248): Comment

Code: `query.order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc()).limit(`

> `since`'s order, and for `for_workflow`'s reason: reversed,
> id and all, so a page boundary falls in the same place twice.

## `SqlWorkflowRunRepository.taken_back_by`, [line 256](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L256): Comment

Code: `found = await self._session.scalar(`

> Only a run that HELD. One that failed left the record where it was,
> and refusing a second attempt because the first did not work is
> refusing the one attempt that might.

## `SqlWorkflowRunRepository.failures`, [line 266](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L266): Comment

Code: `query = (`

> One count for the tenant, beside `tallies` and for the same reason it
> is batched. `stopped` and `aborted` are deliberately not here: a run
> that stopped to ask is the job asking, and one a person aborted is a
> person changing their mind.

## `SqlWorkflowRunRepository.tallies`, [line 278](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L278): Comment

Code: `query = (`

> The rig's two counts off the runs index, batched: it asked
> ``COUNT(*), SUM(outcome = 'held')`` per workflow, and this asks the
> tenant once. ``count(*) FILTER`` rather than SQLite's ``SUM`` of a
> boolean, which has no meaning in Postgres -- and it counts rows, so
> a tenant with no held runs gets 0 where the SUM would have given
> NULL. No ``ORDER BY``: the answer is a mapping and the caller looks
> each workflow up by id.

## `SqlWorkflowRunRepository.since`, [line 291](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L291): Comment

Code: `query = self._rows().where(`

> Newest first, unlike ``for_workflow``: this is the audit's order, and
> a person reading what happened reads back from now. No limit --
> paging belongs to the route, which is where the rig's was.

## `SqlWorkflowRunRepository.since`, [line 297](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L297): Comment

Code: `query.order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc())`

> Reversed, id and all: the audit's order has to be total for
> the same reason `for_workflow`'s does, and every sibling read
> here breaks its tie the same way -- `offers.since` on
> `seq DESC`, `known` on the id.

## `SqlWorkflowRunRepository.in_flight`, [line 329](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L329): Comment

Code: `busy: str | None = await self._session.scalar(`

> A read the caller acts on, and no longer the only thing standing
> between two presses and one browser: migration 0043 added the UNIQUE
> partial index on (tenant_id, device_id) WHERE outcome = 'running'
> that the note here used to ask a future worker for.
>
> This stays because it is the answer a person can act on -- it names
> the run already driving, where the index can only refuse. The index
> is the backstop for the race this read cannot see: there are two
> awaits between it and the commit, and two gathered presses against
> real Postgres both claimed the browser before it existed.

## `SqlWorkflowRunRepository.in_flight`, [line 337](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L337): Comment

Code: `.order_by(WorkflowRunRow.started_at, WorkflowRunRow.id)`

> Total, so that a device somehow driving two runs at one instant
> names the same one of them on every read rather than whichever
> Postgres happens to hand back first.
>
> 0043 makes that state unreachable through this schema, so the
> ordering is now defensive rather than load-bearing, and the test
> that planted two running rows to prove the tie-break went with it.
> Kept anyway: a hand-typed INSERT, a restore from a dump taken
> before 0043, or a future outcome value that is not 'running' but
> means it would each put two rows here, and a query that returns
> "whichever" in that state is worse than one that returns the same
> one twice.

## `SqlWorkflowRunRepository.in_flight`, [line 335](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L335): Comment

Code: `WorkflowRunRow.executor == "extension",`

> The one-device rule was written three ways -- this read, the unique index,
> and the startup sweep -- and only two of them were narrowed to Steel when
> `executor` arrived. A Steel run has no device, so without this a caller
> asking "is `dev_1` busy" could be answered by a Steel run that happens to
> have been saved with `device_id = "dev_1"` by a bug elsewhere, when the
> index and the sweep would both already treat that row as none of their
> concern.

## `SqlWorkflowRunRepository.waiting_on`, [line 362](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L362): Comment

Code: `.order_by(WorkflowRunRow.started_at.desc(), WorkflowRunRow.id.desc())`

> The last question asked about this conversation is the live one.

## `SqlWorkflowRunRepository.awaiting`, [line 390](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L390): Comment

Code: `WorkflowRunRow.outcome == "running",`

> Only a run still in flight. The rig gated this list on the
> runner's in-process `Approvals.waiting()` set, which is plan
> 3's half; the storage half is this predicate, and without it
> a step left `awaiting` on a run that was aborted or failed
> sits in the supervisor's queue forever, asking for a tap that
> can no longer let anything out.

## `SqlWorkflowRunRepository.awaiting`, [line 393](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L393): Comment

Code: `.order_by(WorkflowRunRow.started_at, WorkflowRunRow.id, WorkflowRunStepRow.ord)`

> Oldest wait first: this is the queue a supervisor works down, and
> the run that has been parked longest is the one holding up a job.
> The run id between the two, because two runs of one tenant can
> be started in the same instant and their parked steps would
> otherwise interleave differently on every read.

## `SqlWorkflowRunRepository.approve`, [line 399](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L399): Comment

Code: `tapped = await self._session.execute(`

> DO NOTHING, the rig's OR IGNORE: a write rescued to the second rung
> parks at the same step and takes a second tap, and the first
> authorisation stands -- with the first approver's browser on it.
> RETURNING rather than a rowcount, because whether this tap was the
> one that authorised the step is the answer the caller wants.

## `SqlWorkflowRunRepository.fail_orphans`, [line 419](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L419): Comment

Code: `WorkflowRunRow.outcome == "running", WorkflowRunRow.executor == "extension"`

> Spec §7.4: API restarts lose nothing. This sweep runs once at API startup
> and fails every run it finds still `running`, because a browser-driven run
> lived in this same process and a restart is that process dying under it.
> A Steel run lives in the worker, driven by a Temporal workflow that
> survives the API restarting beside it -- sweeping it here would fail a job
> that is still actually running. Narrowed to `executor == "extension"` so
> only the runs this sweep was ever about are touched.

## `SqlWorkflowRunRepository.fail_orphans`, [line 432](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L432): Comment

Code: `run.steps.append(`

> The reason has to land somewhere the panel shows it, and a
> run that died before its first step has nowhere.

## `SqlWorkflowRunRepository._rows`, [line 442](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L442): Comment

Code: `return select(WorkflowRunRow).execution_options(populate_existing=True)`

> ``save`` upserts with a Core statement, so a row this session had
> already loaded would otherwise come back at its pre-save state.

## `SqlWorkflowRunRepository.started_on`, [line 369](../../../../../../../backend/src/sro/infrastructure/db/workflow_runs.py#L369): Note

> Every mail-started run keeps its conversation in `awaiting` from the insert
> on, whatever becomes of the run, so that column answers "did this thread
> already start one".
