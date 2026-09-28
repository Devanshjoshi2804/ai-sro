# Notes for `backend/src/sro/application/execution/workflow_runs.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/workflow_runs.py`](../../../../../../../backend/src/sro/application/execution/workflow_runs.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L1): Docstring

> The press. A person opened a door and chose live or dry.
>
> Ported from `start_run` in `new_agent_arch/src/rig/api.py:1021`. Nothing here
> starts a run on its own: the rig has no scheduler for these and neither does
> this, because a run drives an operator's own browser against their own
> warehouse and there is nobody at the screen when nobody pressed anything.
>
> **The order of the refusals is the rig's, and every position is an argument.**
>
> * No model, first, and before a session is opened: a run plans every step on a
>   model, so a deployment with none must not claim a row it can never drive.
> * The cap, second and still before the browser is asked anything: a day that
>   has spent its cap starts no run.
> * The browser, third, and *before the workflow is looked up*. "your browser is
>   not connected" is the answer a person can act on, and it holds whatever they
>   asked for. A browser already driving a run is refused in the same place and
>   for the same reason -- one browser, one hand: two runs driving the same
>   window interleave their clicks into a form neither of them can then read
>   back. That holds for a press that names its browser. A start that names
>   none (a chat yes, S2) needs the job first, because a mail-only job needs
>   no browser at all; its browser is picked and checked right after.
> * Then the job, then the values, then which step to start on.
>
> **The busy check is the answer, and it is not the guarantee.** Between reading
> `in_flight` and the row existing there are two more awaits, and on one event
> loop a second press can be scheduled in either of them: run against real
> Postgres, two `asyncio.gather`ed presses produced two rows and zero refusals.
> What makes "one browser, one hand" true is the UNIQUE partial index migration
> 0043 builds, which `SqlWorkflowRunRepository.save` turns into the same
> `Conflict`, in the same words, out of `already_running`. The read stays because
> it is the friendly answer and it names the run already driving; the index is
> what holds when the read was right at the moment it was made and wrong by the
> time the row was written.
>
> **The row is claimed and committed here, not by the task.** Written inside
> `run_workflow`, the `running` row appears only once the spawned task gets its
> first slice, and a second press arriving in that window reads no busy run and
> puts a second hand on the same browser. `run_workflow` says the same thing from
> its own side and reads the row back as the authority for what was asked.
>
> **`started_by` is the authenticated caller and never a name in a body.** A
> request that says who authorised it is a signature nobody checked, and the
> audit trail on a warehouse write is worth more than that.
>
> Where the shape of the request is checked and where its meaning is:
> `StartWorkflowRunRequest` refuses a body that is not an object of strings and a
> `from_step` that is not honestly an integer, because both are facts about the
> wire and pydantic already answers them -- the bool trap in particular can only
> be caught before coercion, since `True` *is* an `int` by the time it reaches
> here. What values a run may be performed *with*, and which steps a job has, are
> this module's: trimming, dropping a value that is blank once trimmed, and the
> range of `from_step` all need the workflow, and they live beside the refusal
> that reads it.
>
> **And the two reads of what the press left behind**, at the foot of the file:
> `ListWorkflowRuns` (`api.py:1152`) and `GetWorkflowRun` (`api.py:1217`). They
> are here rather than in a file of their own because the row they answer with
> is the one `StartWorkflowRun` claims, and a reader asking what a run looks
> like on the way out should not have to find a second module to learn what put
> it there.
>
> **And the stop button under them**, `AbortWorkflowRun` (`api.py:1237`), for the
> same reason: the run it interrupts is the one claimed at the top of this file,
> and the register it sets is the one `StartWorkflowRun` hands the task.
>
> **And the Yes beside it**, `ApproveWorkflowStep` (`api.py:1270`), which is the
> other half of the same seam: the stop button releases the approval wait to end
> a run, and this one releases it to let the write out. Both reach the register
> `StartWorkflowRun` handed the task, and neither of them is `/v1/confirmations`
> -- that approves a *confirmation*, keyed on the confirmation and not the run.

## module, [line 88](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L88): Note on the line above

Code: `DraftsForTheAsker = Callable[[RequestContext, str, Pending], Awaitable[bool]]`

> Write a mail to whoever asked, for a run that came up short.
>
> A callable rather than the use case, for `GatherValues`' reason: this object
> is built once per request and the drafter needs the request's own tenant and
> operator. Optional throughout -- a deployment with no mailbox runs exactly as
> it did, stopping with the question and asking nobody else.

## module, [line 91](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L91): Note on the line above

Code: `K_EVERY_FORM = 400`

> How many create forms one lookup asks for.
>
> Every one, rather than a search: `search` matches terms against a claim's title
> and key, and a form's key is its route -- so a lookup for `customerType` finds
> nothing at all, which is how this was first built and why it said nothing.
> Measured on QA 2026-09-16: 88 forms, 756 fields, 0.09 seconds for the lot.
> Four hundred is room for a base four times that size before a write stops
> seeing the screen it is writing to.

## `_asking`, [line 94](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L94): Docstring

> The sentence that opens the question, in the words of what went wrong.
>
> Two different things bring a run here and they want two different
> questions. A value nobody could find is "I could not find X". A value that
> would not fit is "X holds 28 characters" -- and asking that one the first
> way gets the same value back, because nothing has told the person their
> description is twice the length the box takes. The browser did not say so:
> it truncated in silence, which is why the limit had to be discovered at
> all.

## `StartWorkflowRun`, [line 108](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L108): Docstring

> Claim the row for one press, then drive it.
>
> Two halves on purpose, and the seam between them is the answer to the
> caller: `execute` refuses or claims and returns, and `perform` is what the
> spawned task awaits. A run in somebody's own browser is the one a person
> sits and watches, and they could not if the id only arrived when the last
> step landed.

## `ListWorkflowRuns`, [line 660](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L660): Docstring

> The most recent runs, newest first, as the rig listed them.
>
> Ported from `runs` in `new_agent_arch/src/rig/api.py:1152`.
>
> **Newest first, and that is deliberately not `for_workflow`'s order.**
> `for_workflow` is oldest first because `proofs` reads a job's writes
> forward through time. This is the list a person opens, and what they are
> looking for is what happened last -- which is also the shape the extension
> and the console will be written against. The port used to justify its
> ascending order by citing the rig, whose list says the opposite; the
> citation is corrected and the rig's order lives here, under `recent`.
>
> **`awaiting=true` is the supervisor's queue**, narrowed to the runs parked
> on a write nobody has let out yet -- from any browser, not the one the run
> is in. Narrowed by the ids `awaiting` gives and then capped, in that order:
> a cap applied first would answer "nothing is waiting" out of the busiest
> tenant, which is the one that needs the queue.
>
> **`limit` caps the rows and not that set, and this is the one unbounded
> thing on this read.** Every parked run id of the tenant is interpolated
> into the `IN (...)`. What bounds it is migration 0043 rather than a number
> here: one running run per browser, and only a running run can be parked, so
> the set is at most one id per browser the tenant has. A bound in code would
> have to be a cap on `awaiting` itself, which would drop parked runs out of
> the queue silently -- the thing the ruling below exists to refuse.
>
> The whole row comes back rather than the rig's one line each, so every
> parked step is already on the wire. The rig reported the deepest parked
> step of each run and this reports all of them, `ord` ascending -- plan 4b's
> ruling, recorded here and on `WorkflowRunRepository.awaiting`: anyone may
> answer a parked run, and a queue that hides all but the deepest step hides
> work from the person who could clear it.

## `GetWorkflowRun`, [line 684](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L684): Docstring

> One run, whole, or the 404 that will not say which kind of missing.
>
> Ported from `read_run` in `new_agent_arch/src/rig/api.py:1217`.
>
> The repository answers `None` rather than raising -- "every caller answers
> 404 itself" -- and this is that caller. A run of another tenant takes the
> same path as one that never existed, because a 403 confirms the id exists:
> run ids are unguessable and the answer to "is this yours" must not differ
> from the answer to "does this exist".
>
> The rig also hung `approved_at` and `approved_by` off each step out of the
> approvals table. Not here: `/v1/audit` already serves the approvals of
> every run of the tenant, and a second place that says when a write was let
> out is a second place for the two to disagree.

## `AbortWorkflowRun`, [line 726](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L726): Docstring

> Ask a run of a mined job, in somebody's own browser, to stop.
>
> Ported from `abort_run` in `new_agent_arch/src/rig/api.py:1237`, and it
> closes phase 4a's carried item 1: `run_workflow` has asked `Stops` between
> every step since it was written, and nothing outside this process could set
> it.
>
> **A sibling of `StopRun`, not a branch on it.** That one is the SKILL run's
> half and resolves through `uow.runs` on a `RunId`; this resolves through
> `uow.workflow_runs` on a plain `str`. `new_run_id` says why the two id
> spaces stay apart: "a string that round-trips through the wrong repository
> will be looked up, found missing, and read as a run that does not exist
> rather than as a type error". Its two refusals are copied because they are
> right for both, and both the `CannotStop` class and the sentence of the
> second one are imported rather than redeclared, so neither the `code` nor
> the words a console renders can drift into two.
>
> **The flag first, then the release**, which is the rig's order. A run parked
> on a person is not between steps and would sit out `K_APPROVAL_WAIT_S`
> before it noticed the flag; releasing the wait lets the loop see it now. The
> release is not a yes -- `run_workflow` asks `Stops` on the way out of
> `wait_for` and aborts rather than writing.
>
> Written in that order and not testable in it: nothing is awaited between the
> two lines, so on one event loop the woken task cannot be scheduled between
> them and the reverse order would behave identically today. It is written the
> safe way round because the day something is awaited in between is the day it
> stops being identical, and that day will not come with a test attached.
>
> **Nothing here writes the row.** The task driving the browser is the only
> thing that knows whether the gesture it was mid-way through landed, and it
> closes the run on its way out. A route that marked the row `aborted` would
> race the task it just interrupted.
>
> Nothing here talks to the browser either. The loop sends `kind="abort"` the
> moment it reads the flag, and it now does so on BOTH of its readings -- the
> one between steps and the one on the way out of the approval wait, which
> had none until this route made that path reachable. So the rig's own
> best-effort send is made unnecessary rather than dropped, and it stays in
> the loop rather than moving here because the loop is what holds the socket
> and knows the run is really over.

## `NotDrivingThisRun`, [line 752](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L752): Docstring

> This browser is not the one driving the run it is trying to release.
>
> 403 and not 404: the caller holds a tenant credential that was accepted and
> a browser secret that checked out, so this is not an enumeration channel --
> they have already been told the run exists by every read on this router.
> `tenant_only` refuses in the same words for the same reason.
>
> A `DomainError` with its own entry in `errors._STATUS_BY_ERROR`, rather
> than a subclass of `call_run_wrong.NotYours` -- which is the nearest thing
> to it and refuses the same shape of caller. That one is about a PERSON and
> this is about a BROWSER: "that is another browser's run" and "that is
> another person's run" are two different sentences to whoever is holding the
> screen, and its own `code` is what keeps them two on the wire.
>
> Not a subclass for a second reason, now historical: when this was written
> neither `NotYours` had a handler registered, so both reached a caller as a
> 500 and inheriting would have inherited it. `0302584` fixed that door.

## `ApproveWorkflowStep`, [line 756](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L756): Docstring

> A person saw the write the panel showed and said go.
>
> Ported from `approve_run` in `new_agent_arch/src/rig/api.py:1270`, and it
> is the precondition on anything ever being pressed live: without it a run
> that parks on a person sits out `K_APPROVAL_WAIT_S` and fails for want of
> an answer, however hard anybody taps.
>
> **Two halves, and the durable one goes first.** The row says who let the
> write out; the event is what the parked `run_workflow` task is waiting on.
> The rig fires the event and writes the row after (`api.py:1284` then
> `:1305`) and this is deliberately the other way round. The asymmetry is not
> symmetric: event first and a failed write is a live warehouse write with no
> record of who authorised it, which `routers/runs.py` has already ruled
> against -- "the audit trail on a warehouse write is worth more than that";
> row first and a failed release is a run that stays parked, times out and
> aborts, and an operator who taps again. A lost tap is recoverable.
>
> **The rig's own order was safe where the rig ran, and that is exactly why
> it must not be copied here.** An earlier revision of this docstring claimed
> it raced the task it woke; it does not, and the claim was checked and
> withdrawn. `Approvals.approve` there is a sync `event.set()`
> (`rig/runner.py:90-94`), `store.query` and `store.execute` are sync sqlite
> (`rig/store.py:447-453`), and there is no `await` anywhere between the two
> -- so the woken task cannot be scheduled in between, and the rig's read of
> which step to record always ran before the task could touch it.
>
> What the rig had, then, was an insert that could not be preceded by a
> yield and a store with no commit to fail. This has both: `uow.commit()` is
> an awaited round trip to Postgres that can raise, and the release is a
> separate act after it. The asymmetry therefore bites HARDER here than it
> ever did there -- the failure the rig's shape merely permitted in theory is
> one this shape can actually produce -- which is the whole reason the order
> is inverted rather than ported.
>
> **The order is what the 409 costs.** The rig got "nothing is awaiting" from
> `Approvals.approve` returning False, which is not available before the
> event is fired. This asks the run's own steps instead, with the predicate
> `WorkflowRunRepository.awaiting` already carries -- a `running` run with a
> step whose verdict is `awaiting` -- so the queue and the tap agree about
> what "parked" means. The two are not identical and the difference falls the
> safe way: `run_workflow` registers on `Approvals` BEFORE it saves the
> parked step, so in the window between them the event exists and the row
> does not. The rig would have released the wait there and written no
> authorisation; this answers 409 and the operator taps again a moment later.
>
> **The deepest parked step is the one a tap authorises**, `ORDER BY ord DESC
> LIMIT 1`, and that is deliberately NOT `awaiting`'s rule. That one returns
> every parked step of every run, `ord` ascending, because anyone may answer
> a parked run and a queue hiding all but the deepest hides work from the
> person who could clear it. It answers "what is waiting"; this answers
> "which step does THIS tap let out", and a run is parked at its deepest.
>
> **`WorkflowRunRepository.approve` is tenant-blind on purpose** -- the run
> id is the only thing the panel has -- and the lookup at the top of this
> method is the whole of what stands between that and a cross-tenant write.
> A run of another tenant takes the same path as one that never existed, for
> `GetWorkflowRun`'s reason: a 403 confirms the id exists.
>
> **A caller that NAMES a browser answers for the run that browser is
> driving and no other**, checked before anything is written and before the
> event is set. `asking` is the browser that proved itself with
> `X-Device-Secret` beside `?device_id=`, so it can never be a claim -- the
> rig had to rank a token's own device above a `device_id` in the body, and
> here there is no body to rank it against.
>
> **Say what that is, because the rig's sentence for it promises more.** The
> rig wrote "one compromised browser must not be able to satisfy every other
> browser's human-in-the-loop gate", and neither the rig nor this delivers
> it: a caller who names no browser at all skips the check, and here the
> extension holds the tenant's bearer, so a compromised one can simply omit
> the pair. What this check IS: a browser that identifies itself is bound to
> its own run, so a panel cannot answer for a window it is not driving, and
> an id lifted from one browser's screen buys nothing against another's. What
> it is NOT: a barrier against a caller holding the tenant's credential --
> which already starts, stops and reads every run of the tenant.
>
> Refusing `asking is None` would close that, and it is deliberately not
> done: `awaiting` and `GET /v1/workflow-runs?awaiting=true` exist so that
> ANYBODY may answer a parked run, across browsers, and the reader they were
> built for is a supervisor's console holding the tenant's credential and no
> extension of its own. A device-only tap would delete the supervisor's
> queue. The row then names no browser rather than one nobody proved, which
> is the honest record of a console tap.
>
> The return says which step was authorised and whether THIS tap was the one
> that authorised it. The first tap wins: a write rescued to the second rung
> parks at the same step and takes a second tap, and the first authorisation
> is the one in the audit. A second tap is not refused, though -- the run
> really is parked again, and a 409 would leave it sitting out five minutes.

## `StartWorkflowRun.runs_on_steel`, [line 146](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L146): Note

> The rollout switch (spec §9): a tenant listed in `Settings.steel_tenants`
> has its runs started on the server, on Steel, through Temporal; every other
> tenant's runs are driven by the extension as before. Decided here, once,
> because every door that starts a mined job -- the press, a trigger (through
> the dispatcher's POST to the press), a confirmation, and a sure mail --
> comes through this class. No durable execution wired means no Steel, so a
> process built without Temporal cannot route a run to nowhere.

## `StartWorkflowRun.execute`, [line 172](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L172): Note

Code: `steel = self.runs_on_steel(ctx) and built_in(workflow_id, ctx.tenant_id.value) is None`

> A Steel run holds no browser of the operator's, so the connected-browser
> and one-run-per-browser refusals are the extension's alone. Its row stores
> `executor="steel"` and an empty `device_id`: which browser drives it is the
> lease's business (the session broker), not the press's. `device_id` may be
> `None` for exactly that reason -- a mail that starts a run has no browser to
> name. Off Steel, a start with no device (a chat yes, S2 round 1) runs on the
> executor the tenant has: a mail-only job on the Gmail tool with no browser
> (`executor="extension"`, empty `device_id`, which `perform` sends down
> `_a_mail_job`), anything else in the starter's own connected browser
> (`_their_browser`). Nothing to run it on is "none of your browsers is
> connected".

## `StartWorkflowRun.start_on_steel`, [line 341](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L341): Note

> A Steel run is handed to Temporal: the workflow `workflow-run-{run_id}` owns
> the steps, its own deadline and the finish. The budget comes from the job's
> recorded timing (`run_budget`). No in-process loop, no mail-job drafting, no
> approval here. Answers whether the hand-off happened: a refusal closes the
> row with the reason and answers False, so a caller that reports the start
> (a mail) can leave the request standing instead of saying it runs. `perform`
> calls it for every stored Steel run, so a process without Temporal closes
> such a run rather than driving it in a browser.

## `StartWorkflowRun.execute`, [line 149](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L149): Docstring

> The claimed row, or the refusal that stopped it being claimed.
>
> `undoes_run` is the run this one takes back, where a press on a result
> card started it. Refused where that run has already been taken back by
> a run that held: an undo pressed twice is a second delete addressed to
> a record the first one removed, and the warehouse's answer to that is
> nobody's idea of a good surprise.
>
> `conversation` is the outside thread this run answers to, where it came
> from one -- a request read out of somebody's mail. A run that comes up
> short can then be found again by a reply to that mail, which is the one
> address the panel does not have: the person who knows the missing value
> is usually whoever sent the request, and they are not sitting in front
> of this. See `domain/execution/waiting.py`.

## `StartWorkflowRun._a_mail_job`, [line 312](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L312): Docstring

> The job, where every step of it happened in the mailbox.

## `StartWorkflowRun.perform`, [line 365](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L365): Docstring

> Drive a run whose caller has already been answered.
>
> Nobody is awaiting this, so nobody would see it raise. A refusal or a
> broken session mid-run would leave the row saying `running` for as long
> as the process lived -- swept only by `fail_orphans` at the next start,
> which is a restart away and not a moment away -- and the console
> watching it would count the seconds forever.
>
> `run_workflow` closes its own row on the way out of its `finally`, and
> this is the backstop for the two cases that never reach it: what is
> raised before it starts, and a failure that took the session down with
> it so its own save could not land either.
>
> Everything the run is performed with comes off the claimed row rather
> than off this frame, so there is one answer to "what is this run doing"
> and not two that can drift -- `run_workflow` reads the same row back and
> refuses the pair if they disagree.
>
> **Four of these arguments are dead on this path, and they are passed
> anyway.** `run_workflow.py:343` does `values, live, allow_focus =
> run.values, run.live, run.allow_focus` off the row it read back, and
> `started_by` is read only on the branch where no row was found -- which
> `perform` can never take, because it always names one. So none of those
> four decides anything here, and a reader must not spend a minute
> believing otherwise: they are not controls, they are what the callee's
> signature requires, and the row is the authority downstream.
>
> They are the ROW's values rather than a repeat of the request's, and
> that is the part worth keeping. It costs nothing, it is what the one
> path that would read them should read, and if `run_workflow` ever
> stopped finding the row -- swept, deleted, a different tenant -- the
> arguments it fell back on would still describe this run instead of
> whatever a route happened to be holding.


> `secrets.finished()` runs after the loop returned and before the wait is
> settled (task 10 fix round, 2026-09-24): a sign-in whose last submit left
> the form's host is a success only once the run is over and the form never
> came back. It is not called when the run raised.
## `StartWorkflowRun._settle_the_wait`, [line 427](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L427): Docstring

> A run that came out whole is not waiting to hear anything.
>
> The address was written at the start, before anybody knew how the run
> would end, so the end is where it is either kept or let go. Kept is the
> interesting half and needs no writing: the row already says which
> conversation this run answers to, and a reply arriving there is the
> answer to a question that is still open.
>
> Let go is this. A job that found everything and wrote its record has
> nothing outstanding, and a mail arriving on that thread a week later --
> "thanks", or a fresh request -- must not be read as an answer to it.
> Cleared rather than left to expire, because seven days of a finished
> run claiming every reply to its own thread is seven days of the next
> request being swallowed by the last one.

## `StartWorkflowRun._ask_for_values`, [line 448](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L448): Docstring

> Turn a run that came up short into a question somebody can answer.
>
> The alternative, and what this replaces, is a row reading "nobody gave
> a value for Customer Type, and your mail does not say either" -- true,
> and the end of it. The operator had already said yes; what they get for
> it is a dead card and a job to start again from the beginning.
>
> One question, for one value, in their own conversation. What is
> established so far rides on the decision, so the answer is readable off
> the thread rather than out of a session nothing survives, and the last
> answer starts the job on the yes they already gave.
>
> `ids` is optional for the same reason the rest of this object's
> collaborators are: a deployment that has not wired it runs exactly as
> it did before, stopping with the sentence and asking nobody.

## `StartWorkflowRun._mail_hand`, [line 536](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L536): Docstring

> How a run writes and sends a mail through the connector the gather
> rung already reads with. None where there is no connector.

## `StartWorkflowRun._gathering`, [line 565](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L565): Docstring

> Bound to this request's own tenant and operator.
>
> A closure for `_known_fields`' reason -- `run_workflow` has no
> `RequestContext` -- and for one more that matters here: a mailbox is
> reached as ONE person, and the person is the one this run is for.

## `StartWorkflowRun._known_fields`, [line 579](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L579): Docstring

> What the dictionary says about these body keys, by key.
>
> Bound to the request's own tenant, which is the whole of why this is a
> closure rather than the retriever handed down: `Retrieve` is
> tenant-scoped and `run_workflow` has no `RequestContext` to scope it
> with.
>
> `kinds=(FIELD,)` and the keys as terms, because `search` matches terms
> against a claim's title and key. The body key IS the claim's key --
> `customerType` is stored under `customerType` -- so this is a lookup
> rather than a search, and nothing here asks a vector store a question
> it cannot answer without embeddings. Measured on QA 2026-09-16: 404
> field claims, 0 embeddings, and the lookup answers.
>
> **And the FORM, which disagrees with the dictionary and is right.** The
> dictionary is what the vendor DOCUMENTS; a form model was captured from
> the real form an operator uses, which is why its claims are `OBSERVED`
> and the dictionary's are `ASSERTED`. Measured on QA 2026-09-16: the
> dictionary says `customerType` holds 60 characters, the Customer Types
> create form says 4, and the ledger's own gotcha -- somebody's
> measurement -- says `csttyp truncates at 4 chars`. Two of the three
> agree, and the card was reading the third: a request for `NEWSROTEST`
> would have been sent, truncated to `NEWS`, answered 201, and read back
> as the record the system actually made, with nothing to say so.
>
> So the form's numbers win where it has one, and what it says is
> REQUIRED comes back too -- a field the form marks required and the
> write does not carry is the other fact worth a line.

## `StartWorkflowRun._forms`, [line 601](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L601): Docstring

> What the real create form for THIS screen says about its fields.
>
> By the screen and never by the body key. A key does not name a form:
> measured on QA 2026-09-16, `customerType` is posted by two of them --
> Customer Types and Existing Customers -- so a lookup by key would lend
> one screen's required fields to another screen's write and say that a
> customer number nobody asked for was missing.
>
> A form claim's key IS its route, `#wm.config/wm.config.partners.customers.types////`,
> and the step's own screen is the url the demonstrations agree on. One
> contains the other, which is the whole join.
>
> Every form, once, rather than a search: `search` matches terms against
> a claim's title and key, and neither carries the body keys -- a lookup
> for `customerType` finds nothing at all. Measured: 88 forms, 756
> fields, 0.09s for the lot, which is cheaper than being wrong.
>
> Silent where the screen matches no form. A write whose screen nothing
> documents is one the dictionary still describes field by field, and a
> guess between two forms is how this would start inventing missing
> fields.

## `StartWorkflowRun._close`, [line 633](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L633): Docstring

> Mark a row nobody is driving any more, on a session of its own.
>
> The same shape as the orphan sweep -- the reason lands on the last step,
> or on a new one where the run never reached one -- because a reader has
> one place to look for why a run stopped. Left alone where the row is
> already finished: `run_workflow` may well have closed it on its way out,
> and a second close would overwrite the verdict it wrote with this one.

## `GetWorkflowRun.undo_for`, [line 695](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L695): Docstring

> Which of this tenant's jobs takes back what this run made, if any.
>
> Asked only of a run that is over and made something: a run still going
> may make more, and a run that made nothing has nothing to take back --
> and this is a read of every job's evidence, on a door the panel polls.
>
> Answers WHAT and never starts anything: the job that takes it back, and
> the one record it would address. The second half is what this said it
> lacked -- *a mapping this has no evidence for, and a wrong mapping
> deletes the wrong record* -- and the evidence arrived with `made_by`: a
> step that created something records what the warehouse called it.
>
> `addresses` refuses anything but one record named one way, for the
> reason that sentence gives. A run that made two would need two deletes,
> and an undo that takes back half of what a run did is worse than none.

## `ApproveWorkflowStep.execute`, [line 762](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L762): Docstring

> (the step authorised, whether this tap was the one, whether anything woke).

## `StartWorkflowRun.__init__`, [line 133](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L133): Comment

Code: `self._vault = vault`

> Where a password comes from when a step types one. `None` is a
> deployment with no vault configured: the run still happens, and a
> step that needs a password refuses with the key it wanted rather
> than typing a blank into a login form.

## `StartWorkflowRun.__init__`, [line 135](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L135): Comment

Code: `self._retrieve = retrieve`

> What the knowledge base knows about a field. `None` is a deployment
> with no retriever built, which is not a degraded mode: a run then
> says nothing about its fields, exactly as every run did before the
> claims were ingested.

## `StartWorkflowRun.__init__`, [line 136](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L136): Comment

Code: `self._gather = gather`

> Where a value comes from when nobody typed one. `None` is a
> deployment with no connector, and a run with missing values then
> refuses exactly as it always did.

## `StartWorkflowRun.__init__`, [line 137](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L137): Comment

Code: `self._ids = ids`

> What names a message when a run that came up short asks for what it
> could not find. `None` is a deployment that has not wired it: the run
> still stops with its sentence, and nobody is asked.

## `StartWorkflowRun.__init__`, [line 139](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L139): Comment

Code: `self._asker = asker`

> `Asker | None` rather than through `asker_or_refuse` in the container,
> for `ReadChat`'s reason: a factory that raised would make the factory
> itself unbuildable, and a deployment with no key would fail at
> construction instead of at the one call that needs a model.

## `StartWorkflowRun.execute`, [line 170](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L170): Comment

Code: `asker_or_refuse(self._asker)`

> Before the session is opened: neither refusal needs a database, and a
> 503 that first took a connection is a 503 that made the outage
> slightly worse.

## `StartWorkflowRun.execute`, [line 179](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L179): Comment

Code: `workflow = await uow.workflows.get(ctx.tenant_id, workflow_id)`

> After both, so a workflow_id naming nothing does not answer a
> person whose real problem is a browser that went away.

## `StartWorkflowRun.execute`, [line 187](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L187): Comment

Code: `given = {name: value.strip() for name, value in values.items() if value.strip()}`

> Trimmed, and a value that is blank once trimmed is no value:
> `required` on the page passes a space, and a job run with " " as
> its client code is a job run with somebody else's. Dropped rather
> than refused here so the check below sees it as the absent value
> it is.

## `StartWorkflowRun.execute`, [line 188](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L188): Comment

Code: `things = (`

> The things this job is to be done for, trimmed the same way and
> with the run's own values under each. A job with no repeat is
> handed none of them: performing its steps once per thing would do
> the whole job three times over, which is not what "add these
> three" means for a job that adds one thing per run.

## `StartWorkflowRun.execute`, [line 198](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L198): Comment

Code: `supplied = [{**given, **thing} for thing in things] or [given]`

> Every parameter the workflow declares must arrive with one. The
> planner falls back to the value the recording happened to contain
> when a step has none -- right for a step nobody parameterised, and
> for a declared parameter left blank it would quietly perform the
> job with somebody else's client code. Named, never echoed.
> Every declared parameter must arrive for every thing this run
> will do. With no things that is the run's own values, as it
> always was; with three, a parameter two of them named and the
> third did not is a run that would perform the third with
> somebody else's code.

## `StartWorkflowRun.execute`, [line 206](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L206): Comment

Code: `blank = sorted(`

> Refused only where nothing could go and find them.
>
> A person pressing start with a field empty should be told, and
> that is what this has always done. A deployment that can read the
> operator's mailbox has a second answer: the run goes and looks,
> and refuses at the step if the mailbox does not hold it either.
> Held here rather than downstream so the refusal still arrives at
> the press, in front of the person who can fix it, for every
> deployment that cannot gather.
>
> A list is a different matter and keeps the old rule whatever is
> configured: "add these three" where the third names no code is a
> run that would perform it with somebody else's, and a gather
> cannot tell which of three rows a mailbox meant.
> A parameter somebody TYPED blank is refused whatever else is
> configured. `given` strips an empty value out, so by here " " and
> "never mentioned" look identical -- and they are not the same
> fact. A person who typed a space has said something, and reading
> their mailbox instead would overrule them; a person who said
> nothing has left the question open for somebody to answer.

## `StartWorkflowRun.execute`, [line 214](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L214): Comment

Code: `if absent and (self._gather is None or things):`

> Refused only where nothing could go and find them.
>
> `absent` counts only REQUIRED values, on Steel and browser runs alike
> (F1 round 3, item 11; controller ruling): an optional one nobody gave
> never blocks a start -- it skips its step (`RunSteps`, spec §6.6.6, and
> `run_workflow._skippable`), and `value_for` never types the recording for
> a parameter. Before this a browser press refused a job whose optional
> fields a chat answer had left out, which F1 promises the run goes without.
> A required one that gets past here is asked for, never typed from the
> recording. Blank values and a list with a thing missing are still refused.
>
> A person pressing start with a field absent should be told, and
> that is what this has always done. A deployment that can read the
> operator's mailbox has a second answer: the run goes and looks,
> and refuses at the step if the mailbox does not hold it either.
> Held here rather than downstream so the refusal still arrives at
> the press, in front of the person who can fix it, for every
> deployment that cannot gather.
>
> A list keeps the old rule whatever is configured: "add these
> three" where the third names no code is a run that would perform
> it with somebody else's, and a gather cannot tell which of three
> rows a mailbox meant.

## `StartWorkflowRun.execute`, [line 180](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L180): Comment

Code: `cited = await uow.gestures.gestures_for(`

> What a browser matched is GESTURES, and what this field means is
> STEPS. A shape entry is one cited gesture, so a step of four
> gestures is four entries, and `recognise.match` answers with how
> many entries the tail matched -- 19 and 6 on this deployment's own
> job. The extension sent that straight in as `from_step` and every
> step under it was recorded done-by-the-operator and never
> performed: at k=5 on a six-step job, the step that types the code
> was skipped and the run went on to the description. Over the step
> count it was refused outright, which is the same mistake wearing
> the more obvious face.
>
> Converted here, where the evidence is, rather than asked of a
> browser that has the shape but not the steps behind it.

## `StartWorkflowRun.execute`, [line 220](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L220): Comment

Code: `last = max(step.order for step in workflow.steps)`

> A bool is not a step number, and `isinstance(True, int)` is why it
> has to be said. `StartWorkflowRunRequest` refuses `true` at the
> wire, where the coercion it would otherwise survive happens; this
> is the same rule for a caller that is not a request body.
>
> The bound is the job's own highest order and not `len(steps) - 1`:
> a model numbers its own steps and keeps that numbering, so a job
> whose steps run 1..6 has a last step nothing could resume at while
> this counted positions.

## `StartWorkflowRun.execute`, [line 255](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L255): Comment

Code: `if undoes_run.strip():`

> After `from_step`, because which steps have to be performable is
> what the press just decided. The runner asks this same question
> of one step at a time, mid-run, once a browser is open and the
> earlier steps are already sent -- so a job whose evidence has
> gone is one an operator presses Yes on and watches stop half way.
> It is a stored row going bad rather than a bad row being stored:
> the workflow outlives the gestures it cites, and no check at mine
> time can see that coming.
> An undo already taken. Refused here rather than reported by the
> card, because the card is one browser's copy and a second window
> holds another -- and what two presses buy is a second delete
> addressed to a record the first one removed.
>
> Only against a run that HELD. One that failed left the record
> where it was, and refusing a second attempt because the first did
> not work is refusing the one attempt that might.

## `StartWorkflowRun.execute`, [line 276](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L276): Comment

Code: `watched=watched,`

> Whether somebody is standing in front of it. A press in an open
> panel means "show me"; a trigger at three in the morning means
> "just do it". See `WorkflowRun.watched`.

## `StartWorkflowRun.execute`, [line 280](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L280): Comment

Code: `awaiting=as_said(waiting_on(*conversation, now=now)),`

> Recorded at the start rather than at the stop, because the
> stop is not the only thing that can want it and a run that
> crashed still came from somewhere. Cleared below where the
> run ends with nothing outstanding: a finished job is not
> waiting to hear anything.

## `StartWorkflowRun.execute`, [line 281](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L281): Comment

Code: `undoes_run=undoes_run.strip() or None,`

> The run this one takes back, where it is an undo of one. An
> id and never a status: whether it worked is this run's own
> outcome, read where every other outcome is read.

## `StartWorkflowRun.execute`, [line 286](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L286): Comment

Code: `await uow.workflow_runs.save(run)`

> Raises `Conflict` -- the same one the read above gives, in the
> same words -- where the unique partial index refuses a second
> running run for this browser. Nothing is caught here: it is
> already the refusal this door means, and translating it twice is
> how the two sentences would drift apart.

## `StartWorkflowRun.execute`, [line 289](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L289): Comment

Code: `await uow.commit()`

> Committed before the caller is answered and before anything is
> spawned. A `running` row that only exists inside the task's first
> slice is a row a second press cannot see.

## `StartWorkflowRun.perform`, [line 371](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L371): Comment

Code: `mail = await self._a_mail_job(ctx, run)`

> A job that is nothing but mail is written, not clicked. See
> `domain/execution/mail_job.py`: it is drafted through the
> mailbox's API and waits for the operator's press, and none of
> what follows a driven run -- settling the wait, asking for
> values -- applies to a draft nobody has sent yet.

## `StartWorkflowRun.perform`, [line 388](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L388): Comment

Code: `learned = await uow.workflows.learned_writes(ctx.tenant_id)`

> The hand-kept ledger, and what this deployment has watched
> for itself. Two sources for one gate: the file is a research
> project's and a tenant cannot add to it, so without the
> second a job whose write this system had confirmed eight
> times still clicked Save the ninth. Read per run rather than
> cached with the file: it grows while the process is up, and
> the run that grows it is usually the one before this.

## `StartWorkflowRun.perform`, [line 393](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L393): Comment

Code: `cap_usd=self._cap_usd,`

> The same cap the press was judged against, so the run can
> keep asking. Read once and never again, one press on a
> long list could spend the rest of the tenant's day.

## `StartWorkflowRun.perform`, [line 424](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L424): Comment

Code: `await self._settle_the_wait(ctx, done)`

> Outside the unit of work, because asking opens its own: the run
> is over and its row is written, and a question that shared the
> run's transaction would be a question that vanishes with it.

## `StartWorkflowRun._settle_the_wait`, [line 431](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L431): Comment

Code: `saved = await uow.workflow_runs.get(ctx.tenant_id, run.id)`

> The committed row and not the copy in hand, which is what
> `run_workflow` handed back and may be a step behind what it
> saved. Whether anything is still outstanding is a question about
> the row a reply would find, so it is asked of that row.

## `StartWorkflowRun._settle_the_wait`, [line 436](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L436): Comment

Code: `await uow.commit()`

> And committed. Without this the clear is rolled back when the
> unit of work exits, and the row goes on naming a conversation it
> is no longer waiting on -- for seven days, swallowing every reply
> to that thread as an answer to a job that finished.
>
> The unit tests passed: `FakeUnitOfWork` does not require a commit
> to have happened, so it agreed with the code rather than with the
> store. Measured on the deployment 2026-09-18 -- a run held, needs
> empty, `awaiting` still set.

## `StartWorkflowRun._ask_for_values`, [line 451](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L451): Comment

Code: `async with self._uow as uow:`

> What the boxes behind these names will hold, where a run has found
> out. A question that asks for a value again without saying why the
> last one would not do gets the same value back -- the person has no
> way to know the field stops at 28 characters, because the browser
> never said so and neither did we.

## `StartWorkflowRun._ask_for_values`, [line 454](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L454): Comment

Code: `cited = (`

> Which of this job's steps wrote, so the resumed one can be told
> where it may safely start over. Read here rather than inferred
> from the run's own record: what a STEP does is a fact about the
> job and its evidence, and a run that stopped early performed too
> few of them to say.

## `StartWorkflowRun._ask_for_values`, [line 464](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L464): Comment

Code: `declared = await declared_limits(`

> And what the vendor's own dictionary says, for the fields no run
> has hit yet. A job whose first request is too long would
> otherwise learn that by sending it.

## `StartWorkflowRun._ask_for_values`, [line 472](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L472): Comment

Code: `field_classes(workflow, by_id, {one.ord: one for one in learnt}, declared)`

> C2's field classes, for the options each missing field's box
> offers: the question carries every missing required field with its
> limits and options (F1), which is the shape design 3's one form is
> drawn from (`asking.asks`).

## `StartWorkflowRun._ask_for_values`, [line 476](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L476): Comment

Code: `operator = PrincipalId(run.started_by) if run.started_by else ctx.principal_id`

> The person this run was for, not whoever is at the door: a
> question in the wrong conversation is worse than none. Their
> current thread is read here because it is the one
> `SayWhatHappened` writes into: `still_to_ask` drops what they said
> they do not have and what that thread already offered, and a
> required field they do not have ends the ask with a note
> (`cannot_without`) rather than a question that loops (F1).

## `StartWorkflowRun._ask_for_values`, [line 487](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L487): Comment

Code: `offered=offerable(workflow.parameters, run.values) if workflow else (),`

> And what it could ALSO set, which nothing has to answer.
>
> Since 2026-09-22 a field the page does not ask for no longer
> stops a run, and the step that fills it is skipped where nothing
> was given. Skipping it silently is the other half of the old
> mistake: a field the operator did want goes unfilled and nothing
> says it was ever possible. So it is offered, once, in the
> opening, beside what it was last time.

## `StartWorkflowRun._ask_for_values`, [line 488](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L488): Comment

Code: `from_step=(`

> Where the run the answer starts has to begin.
>
> Not the step that stopped, which is where this started: that one
> re-types a field into whatever is on the screen a minute later,
> and the operator may well have navigated off the half-filled form
> by then. So it goes back to the beginning of the block that BUILT
> that screen -- pressing Add, opening the tab, the typing before
> it -- and rebuilds the form the value is going into.
>
> `begins_again_at` partitions at the last write for the reason
> everything here does: a write that may have landed is not a step
> to try again, and nothing it returns is on the far side of one.

## `StartWorkflowRun._ask_for_values`, [line 511](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L511): Comment

Code: `text=_asking(pending.missing, title, limits)`

> The offer between the two, for `opening`'s reason: the question
> is what the next sentence answers, and a question buried above an
> offer gets the offer's answer.

## `StartWorkflowRun._ask_for_values`, [line 514](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L514): Comment

Code: `speaker=Speaker.ASSISTANT,`

> A question, not an announcement: `pending_job` reads back what the
> ASSISTANT last decided, so this is what makes the answer findable.

## `StartWorkflowRun._ask_for_values`, [line 522](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L522): Comment

Code: `"watched": pending.watched,`

> Which way the job will be done when it runs. The person is
> in the panel answering questions, so they are watching -- but
> it is carried rather than assumed, because a run started by a
> trigger that asked and was answered hours later is not.

## `StartWorkflowRun._ask_for_values`, [line 524](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L524): Comment

Code: `"offered": [list(one) for one in pending.offered],`

> Carried so a second browser reading the thread offers the
> same fields, and so an answer arriving minutes later is
> still an answer to this. The state is the thread.

## `StartWorkflowRun._ask_for_values`, [line 530](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L530): Comment

Code: `if self._asker_drafts is not None:`

> And whoever sent the request, where there is one and a way to reach
> them.
>
> The question above goes to the operator, which is right and usually
> enough. It is not enough for the case this whole path was built
> around: a mail asking for a customer type by description, no code in
> it, none in the thread, and an operator who did not write the request
> and has no way of knowing. The person who does is whoever sent it.
>
> Drafted, never sent. What leaves here is words in the operator's own
> conversation with a press under them, and the press is the only thing
> that reaches a mailbox.
>
> Nothing here can stop the question that has already been asked: a
> deployment with no connector, a thread that cannot be read, a run
> nobody can trace to a request -- all of them mean no draft and none
> of them means no question.

## `StartWorkflowRun._known_fields.look`, [line 590](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L590): Comment

Code: `known: dict[str, dict[str, object]] = {`

> Keyed by the claim's own key and only where it is one of the body
> keys asked about. `search` is an OR over the terms, so a lookup
> for two fields answers with claims for either -- and a claim for
> a field this write does not fill must not be read as one it does.

## `ListWorkflowRuns.execute`, [line 673](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L673): Comment

Code: `async with self._uow as uow:`

> No defaults. The route passes all three, so a default here is
> unreachable -- and a `limit` default would be a second copy of the
> page size, in the one of the two places that never reaches
> `openapi.json`.

## `ListWorkflowRuns.execute`, [line 676](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L676): Comment

Code: `parked = frozenset(`

> No early return on an empty queue, which is what the rig
> did. Its `id IN ()` would have been a syntax error with no
> ids to interpolate; here an empty set is a filter that
> matches nothing, said once in `recent` and kept by the
> contract suite. A branch here would be a second statement of
> the same rule that no test can tell from its absence -- it
> was written, and the mutation that deleted it passed 59
> tests.

## `GetWorkflowRun.undo_for`, [line 696](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L696): Comment

Code: `if run.outcome == "running" or not any(step.made or wrote(step) for step in run.steps):`

> A run still going may make more; a run that wrote nothing has
> nothing to take back.
>
> `wrote` beside `made`: a write performed on the page carries the
> marker and no record, because the browser sees a call's status and
> never what came back. Read on `made` alone this returned None for
> every run that did the job through the form -- which is every run a
> person watched.

## `GetWorkflowRun.undo_for`, [line 709](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L709): Comment

Code: `undo_job = next(one for one in known if one.id == takes_back)`

> And which record. Without it the panel can name a job and not
> press it, which is where this has stood since it was written.
>
> `identifies` reads the undo's own delete for the field it
> addresses a record by -- the key in its body whose value is the
> segment in its path. Measured on the deployment 2026-09-19: the
> pair was found and not one of ninety-two runs could offer the
> button, because each run's `made` carries the two slots the
> read-back confirmed and a record named two ways is a record this
> cannot name. `None` where the delete does not say, which is the
> old rule exactly.

## `GetWorkflowRun.undo_for`, [line 715](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L715): Comment

Code: `typed = str(run.values.get(asks, "")).strip()`

> A write performed on the PAGE has no record to read.
>
> `made` is filled from a response body, and the browser sees a
> call's status and never what came back -- deliberately, a
> create's answer is a row of somebody's data. So a run that
> typed into the form and pressed Save knows exactly what it
> wrote and carries no `made` at all. Measured on the
> deployment 2026-09-19, run `run_b31b610d`: `POST
> /data/WM/wm/customerTypes returned 201`, held by the status
> belt, `made = {}` -- and no undo could be offered for a
> record whose code is on the card in front of the operator.
>
> What the run was ASKED for, then, under the name the undo
> asks by. Not a guess about the warehouse: it is the value a
> person supplied, the write held, and the card already says
> it. Where the form transformed what was typed -- the ledger's
> own `csttyp truncates at 4 chars` -- the delete addresses a
> record that is not there and answers 404, which is the safe
> way round.

## `GetWorkflowRun.undo_for`, [line 721](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L721): Comment

Code: `if asks is None:`

> Under the name the UNDO asks for, not the one the warehouse
> answers with. `Delete a Customer Type` declares one parameter and
> it is called `Customer Type`; the record it removes is keyed
> `customerType` in the body. A press that sent the body key would
> name a parameter the job does not have, and the run would refuse
> it as a value nobody supplied.

## `AbortWorkflowRun.execute`, [line 738](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L738): Comment

Code: `if run is None:`

> A run of another tenant takes the same path as one that never
> existed, for `GetWorkflowRun`'s reason: a 403 confirms the id exists.

## `AbortWorkflowRun.execute`, [line 742](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L742): Note

Code: `if run.executor == "steel":`

> A Steel run is stopped by cancelling its workflow (spec §7.4), never through
> `Stops`: no browser of the operator's drives it. The row answered still says
> `running`; the step that was running finishes its current primitive and the
> workflow records the run `aborted` (`run.stopped`) before it releases.

## `AbortWorkflowRun.execute`, [line 745](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L745): Comment

Code: `if not run.device_id:`

> `WorkflowRun.device_id` is a non-null `str` where the skill run's is
> `DeviceId | None`, so the empty string is what "no browser" looks like
> here. Kept for `StopRun`'s reason rather than because this system
> writes such a row: what a stop control must never do is answer
> "stopping" for a run nothing in this process is driving.

## `AbortWorkflowRun.execute`, [line 749](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L749): Comment (debt)

Code: `return run`

> ponytail: in-process only. A run and the socket it drives live in one
> worker, so stopping must land there too -- sticky-route by device_id
> if this is ever run with more than one.

## `ApproveWorkflowStep.execute`, [line 772](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L772): Comment

Code: `if run.outcome != "running" or not parked:`

> `running` beside the verdict, which is `awaiting`'s own second
> predicate: a step left `awaiting` on a run that was aborted or
> failed is not waiting on anybody, and a tap on it would record a
> person letting out a write nothing is holding open.

## `ApproveWorkflowStep.execute`, [line 781](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L781): Comment

Code: `await uow.commit()`

> Committed inside the block and the release outside it, so the row
> is durable before anything can act on the event. The other order
> would let a write out on a transaction that then rolled back.

## `ApproveWorkflowStep.execute`, [line 782](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L782): Comment

Code: `resumed = self._approvals.approve(run.id)`

> Whether anything was waiting is REPORTED and never refused, and the
> distinction is the whole of this line. Refusing would answer "nothing
> was awaiting" about a row that exists: the authorisation is committed
> above, and the person really did say go.
>
> But silence is worse. An operator tapped Approve on a real login
> step, got a 200, and watched the browser sit on the same screen until
> they gave up -- the process holding that run had restarted, so there
> was no event to set and nothing to resume. The 200 was true about the
> authorisation and silent about the only thing they cared about.
>
> Two ways it comes back false. The wait timed out: `wait_for` pops its
> event after `K_APPROVAL_WAIT_S`, so a run can stop waiting between
> the 409 check above and this line. Or the process that was waiting is
> gone, which `fail_orphans` cleans up at the next start and cannot
> reach while this one is live.

## `StartWorkflowRun.perform`, [line 389](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L389): Note on the line above

Code: `secrets = RunSecrets(self._vault, self._one_time_secrets, run_id=run.id)`

> One per run: the lookup `run_workflow` asks for passwords, and -- through
> `WatchingChannel`, which wraps the channel handed to it on line 260 -- the
> place that learns what the run typed and what the page showed after it --
> and, through `step_ended` on line 283, which steps held outside signing in:
> the one thing the engine tells it directly, because only the engine knows a
> step's verdict (fix round 5).

## `StartWorkflowRun.execute`, [line 196](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L196): Note

Code: `if steel and things:`

> A Steel run does one thing: `RunSteps` walks the steps once with the run's
> values and has no repeat. A list pressed onto it would do the first thing,
> or none, and a per-thing value missing from `values` is exactly the one
> nothing would supply. Refused with a reason until repeat support exists.

## `StartWorkflowRun.execute`, [line 245](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L245): Note

Code: `elif steel and from_step and matched is None:`

> A Steel run starts part way through only as a takeover: a browser's press
> with the span of the operator's own gestures (`took_over`), so what they
> already wrote is read from their uploads. A start that says only how far
> they got would otherwise send their writes a second time, so it is
> refused, never started from 0 in silence. The words follow what was sent:
> with no `matched` the step came from a question a browser run asked
> before it stopped (a chat answer, S2 review M1), so the remedy is asking
> for the job afresh; a press that counted its gestures but sent no span is
> told to update the extension.

## `StartWorkflowRun.execute`, [line 227](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L227): Note

Code: `refuse_unless_itself(device, device_secret, device_id)`

> Whose gestures a takeover reads is proven, not claimed: the press carries
> the browser's own `X-Device-Secret`, and the browser must be the pressing
> operator's. A body naming a colleague's browser would otherwise let their
> saves mark this run's writes done, and those writes would never be made.
> The same 404 an unknown browser gets.

## `StartWorkflowRun.execute`, [line 232](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L232): Note

Code: `stream_id=device_id.value,`

> An upload's `stream_id` is the browser that recorded it, and the read goes
> through the (tenant, stream, at) index rather than every browser's day.
> `after` is strict and the doing's first gesture sits exactly at `since`, so
> the next float below it makes the bound inclusive without widening it.

## `StartWorkflowRun.execute`, [line 242](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L242): Note

Code: `check_from = (`

> The steps the run will replay must have evidence a browser can act on, from
> the first one it replays. A job the operator finished leaves nothing to
> check.

## module, [line 105](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L105): Note

Code: `STILL_UPLOADING = "your recent work is still uploading; press again in a moment"`

> The one reason a takeover press is refused while the operator's own work is
> still on its way. The extension says the same words when its own bounded
> upload gives up and it does not press at all.

## `StartWorkflowRun.execute`, [line 235](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L235): Note

Code: `if not any(one.at >= took_over.newest for one in seen):`

> A press is taken over only once the server holds the newest gesture the
> browser recorded before it, on any tab. The server cannot see what has not
> arrived: a save made in a popup, or past the offer, and still in the upload
> queue reads as never made, and Steel would make it a second time. So it is
> never guessed at -- the press is refused until the uploads catch up, and
> the extension's own wait is only the first line of this.
> A Steel run starts at step 0: `RunSteps` begins at progress 0 and never
> reads `from_step`. A press that says the operator already did the first k
> steps (`matched`) would otherwise send their writes a second time. Refused
> by name until takeover (D7) exists, never started from 0 in silence.

## `StartWorkflowRun.execute`, [line 282](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L282): Note

Code: `offer=offer.strip() or None,`

> The offer this run answers, recorded on the row so the store's unique index
> makes a second start of it a refusal. The one start path: `POST
> /v1/workflow-runs` and the mail's own start both come through here.

## `StartWorkflowRun.execute`, [line 259](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L259): Comment

Code: `(facts,) = await job_facts(`

> The one runnable gate, inside the start, so every start path passes it: the
> panel's press, the console's Run button, a trigger, a mail's answer. Callers
> filter only what they offer. It compiles with the run's given values and D7's
> `check_from`, so X10b's value-aware field rule and the takeover's start point
> hold here exactly as they did in the deleted `unperformable`.

## `StartWorkflowRun.answered`, [line 323](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L323): Docstring

> `AnswerRun`'s resume for a drafted run: load the run's own job and evidence
> again and redraft it. A run that is not a mail job, or has no answered
> question, is left alone.

## `StartWorkflowRun._no_longer_waiting`, [line 438](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L438): Docstring

> The run stopped for a value its own ask was told the operator does not
> have (F1 round 1, I4). It is over, not waiting on a person: `needs` and
> `awaiting` are cleared in one unit of work, the way
> `_settle_the_wait` clears a wait, so nothing counts it as a question
> still open. The outcome is not touched -- the run already ended.

## `StartWorkflowRun._ask_for_values`, [line 503](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L503): Comment

Code: `said, noted = cannot_without(pending, ran=True)`

> "stopped — it needs X to run": this run did start, so the chat door's
> "nothing was started" would be false here.

## `StartWorkflowRun.execute`, [line 288](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L288): Comment

Code: `await then(uow, run)`

> What the caller writes in the same transaction as the run it claimed.
> `Converse._start_it` writes the "Running" message here, so a run and the
> message naming it commit together: never a message about a run that does
> not exist, and never a run the thread does not name. Called after the
> row is inserted -- the offer's unique index has already refused a second
> start -- and before the commit; whatever it raises rolls the run back.

## `StartWorkflowRun._free`, [line 292](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L292): Docstring

> The browser is connected and not already driving a run: one browser, one
> hand. The same two refusals for a browser a press named and one this start
> picked.

## `StartWorkflowRun._their_browser`, [line 299](../../../../../../../backend/src/sro/application/execution/workflow_runs.py#L299): Docstring

> The browser a start that named none runs in: one of the STARTER's own
> devices, online on the socket now and not revoked, the one seen last where
> there are several. The tenant's other devices are never candidates -- a run
> in a colleague's window is one operator driving another's hand (invariant
> 5). This is what the deleted `resumeTheJob` did from inside the browser,
> now decided where every door can reach it.

## `StartWorkflowRun.execute`, [line 149](../../../../../../backend/src/sro/application/execution/workflow_runs.py#L149): Note

> A built-in mail action never runs on Steel, whatever the tenant: it is the
> draft path the user tested on QA -- written, shown, sent on the press. A
> mined mail-only job keeps S2's rule and runs where the tenant runs.
