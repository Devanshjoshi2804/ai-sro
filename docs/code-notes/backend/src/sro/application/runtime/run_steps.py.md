# Notes for `backend/src/sro/application/runtime/run_steps.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/run_steps.py`](../../../../../../../backend/src/sro/application/runtime/run_steps.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `RunSteps`, [line 80](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L80): Class

> A Steel run's activities (spec §7.2): prepare, acquire, one step per call,
> finish, release, beat. Each loads the run and its `progress` afresh, so a
> Temporal retry of any of them is safe: `progress` guards every write. It is
> written only through `record_progress` (D1); `save` carries the steps and
> the outcome. None of them acts on a run that is no longer `running`. A code
> change here is live only after the worker restarts (AGENTS.md).

## `RunSteps.step`, [line 210](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L210): Note

Code: `if progress.in_doubt(step.order):`

> A write marked `sending` (or settled `unknown`) by an earlier attempt is
> never sent again by any path: a retried step runs no lane, it settles the
> write by the API lane's read-back -- signed in afresh when the mark says the
> session had expired, credited to the lane that sent it -- else it asks.

## `RunSteps.step`, [line 248](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L248): Note

Code: `except (NeedsAPerson, AccountBusy, PageGone) as why:`

> The executor raises these carrying the lanes it tried; what they taught is
> learned before anything else. A person is asked; a busy account (another
> run's sign-in is parked on a person) and a lost page are raised again for
> the activity to retry. `Superseded` is raised untouched: another attempt
> holds the run.

## `RunSteps.step`, [line 282](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L282): Note

Code: `await self._teach.learn(ctx, workflow, by_id, step, tried, run_id=run_id, values=values)`

> Taught after the step is recorded, so a teaching failure never turns a
> write proven done back into one in doubt.

## `RunSteps.finish`, [line 285](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L285): Note

Code: `async def finish(self, ctx: RequestContext, run_id: str) -> str:`

> Runs on every path out of the workflow, so a run is never left `running`:
> `held` only when every step was reached and each is held or withheld;
> an outcome already set (a stop's `aborted`) is kept.

## `RunSteps.beat`, [line 424](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L424): Note

Code: `if progress.lease and not await self._broker.beat(ctx, progress.lease, holder=run_id):`

> A beat the lease no longer answers is a lost lease: the lost-page path.

## `RunSteps._keep_tab`, [line 473](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L473): Note

Code: `except BaseException:`

> A tab this attempt opened but could not record is closed at once; a retry
> would open another, and nothing would ever release the first.

## `RunSteps._sending`, [line 527](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L527): Note

Code: `if again and wrote == "sending":`

> The same lane run again after a re-sign-in (X8) marks the write it already
> marked; any other mark means another attempt got there first, and this one
> sends nothing.

## `RunSteps._settled`, [line 534](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L534): Note

Code: `async def _settled(`

> Settling an `unknown` write is this class's job (X8): a read-back first,
> signed in afresh when the result says the session expired; nothing to read
> back means a person is asked and the mark stays in doubt.

## `RunSteps._advance`, [line 580](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L580): Note

Code: `progress.step, progress.asking = index + 1, {}`

> A step that settles after asking withdraws its own question: the held row
> follows the unclear one, and D5 takes an answer to a withdrawn question as
> already answered.

## `RunSteps._ask`, [line 597](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L597): Note

Code: `async def _ask(`

> Every question is also a step row (`failed`, or `unclear` for a write
> nobody can confirm) with the question as its reason, so the console shows
> where and why the run stopped. Asked from prepare and acquire too, at the
> step the run stands on.

## `RunSteps._write`, [line 860](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L860): Note

Code: `ctx.tenant_id, run.id, now, was=run.progress`

> A compare-and-set: progress is written only over the progress this attempt
> loaded. Temporal can start a retry while the attempt it gave up on still
> runs (a missed heartbeat, a partition); whichever writes second finds it
> changed and stops with `Superseded`, so one write is never sent twice and
> a step is never skipped.

## `RunSteps._run`, [line 881](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L881): Note

Code: `raise Stopped(f"run {run_id} is not known")`

> A run this tenant does not hold is a stop: nothing more may be done for it,
> and retrying cannot bring it back.

## `RunSteps.finish`, [line 305](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L305): Note

Code: `last = {one.of_step: one.verdict for one in sorted(run.steps, key=lambda s: s.order)}`

> Judged by each step's last row: an `unclear` a read-back later settled as
> `held` is history, not the step's result.

## `RunSteps._write`, [line 853](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L853): Note

Code: `if (index is not None and loaded.step != index) or (`

> The one guard every step write passes, beside the compare-and-set: an
> attempt only records a step's result or question while the run still
> stands on that step, and a question only while the step is not done. A
> zombie whose lane fails after the retry already held the step asks nothing
> and adds no row.

## `RunSteps.release`, [line 349](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L349): Note

Code: `if run.outcome == "running" and waits == "code":`

> A waiting run holds nothing (spec §7.4): its tab is closed while it waits
> and a browser is taken again after the answer. The one exception is a
> one-time code. The code belongs to the page that asked for it, so that tab
> and its WAITING lease are kept across the release and resumed on the answer
> (`SessionBroker.resume`).
>
> Every other wait, and a run that has ended, closes its tab, ends its own
> park, whatever kind it is, and forgets its lease: the run holds no tab, no
> park and no lease id while a person is asked, so another holder on the
> account attaches or signs in at once, and the answered run takes a browser
> through `acquire` exactly as a new run would (L1: a run asking about a step
> held the account for as long as nobody answered). The lease id is forgotten
> too, not only the tab: the activity's beat would find the lease ended by the
> wait (or by the sweep, hours later) and abandon the answered run's acquire.
> A READY lease is not ended: siblings share it as their own tabs, and nobody
> beating it lets it lapse on its own.
>
> Which park is ended is decided by the lease, not by the question: WAITING,
> and parked by this run (the lease's `holder`, which `_park` sets and no
> sibling's beat renames). A lease is per account, so a park another run made
> on it is that run's to end. This also ends a code park the run no longer
> waits on (its page asked for a password instead). The park is ended after
> the tab is closed: an ended park is no longer live and its tab could not be
> reached. A second release finds nothing to do.

## `RunSteps.answered`, [line 370](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L370): Note

Code: `if asking.get("id") != question_id or not asking.get("answered"):`

> The answer is read from the run, where `AnswerRun` kept it; the signal
> only woke the workflow. A question no longer standing, or not answered,
> changes nothing: the step has moved on, or is asked again.

## `RunSteps.answered`, [line 374](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L374): Note

Code: `await self._broker.unpark(ctx, progress.lease, "password")`

> A refused re-sign-in parks the account's lease WAITING for the moment
> between the question and `release`, which ends it (L1: nobody's account is
> held while a person is asked). This unpark is for a release that never ran:
> once the person has stored a new password the park is ended at once, never
> waited out, and the next acquire signs in afresh.

## `RunSteps._acquire`, [line 438](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L438): Note

Code: `if kept.lease.state is not LeaseState.WAITING:`

> A tab still held after an answer is a one-time code's page on a WAITING
> lease: it is resumed (the person dealt with the code there), never used as
> it is. A code the page still asks for, or a password page in its place, is
> asked again.

## `RunSteps._ask`, [line 618](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L618): Note

Code: `if isinstance(asked, WaitingForAPerson):`

> A one-time code keeps the page that asked for it; recording that tab and
> lease as the run's own is what lets `release` keep it and `acquire` resume
> it. The question is said in the operator's thread only after it is written,
> so an attempt another one superseded says nothing. Its id is random, so an
> answer cannot be sent ahead for a question not yet asked.

## `RunSteps.finish`, [line 314](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L314): Note

Code: `run.awaiting = None`

> A run started from a mail waits on that mail's conversation for a reply.
> Once it has finished with nothing left to ask, a reply there is a new
> request again, as the extension's `perform` settles it.

## `RunSteps.answered`, [line 399](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L399): Note

Code: `if kind == "step" and verdict:`

> The operator's verdict on the step the run asked about. `done` settles it
> done by the operator and the run moves on: no lane runs it again. `not_done`
> records the write as never sent, which is the one thing that lets the lanes
> try a write that was in doubt again.
## `RunSteps.step`, [line 184](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L184): Note

Code: `absent = [name for name in step.parameters if not values.get(name, "").strip()]`

> A step whose parameters nobody gave (spec §6.6.6). A required one is asked
> for (`kind="value"`) before any lane acts -- a lane would otherwise have
> nothing to type, and the recording's value is never a substitute. When
> every parameter of the step is optional and absent, the step is skipped:
> recorded `skipped`, which `finish` counts as kept. A step that carries some
> of its values is performed with those.

## `_demanded`, [line 941](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L941): Note

> The job's required parameter names, by the same `demanded` rule the press
> and the mail reading use.

## `RunSteps.stopped`, [line 336](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L336): Note

Code: `async def stopped(self, ctx: RequestContext, run_id: str) -> None:`

> The one place a stopped run is recorded `aborted`: the workflow calls it
> after the operator's cancel, and `acquire` calls it when the stop arrived
> while it was signing in. A run the step already closed (a lane raised
> `Stopped`, or it held) is left as it is.

## `RunSteps.prepare`, [line 106](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L106): Note

Code: `for one in ordered[progress.step :]`

> The start page and the account are those of the first browser step still to
> run. A run that takes over a job part way through (spec §7.6) begins at its
> first progress's `step`, so Steel opens on the page that step was recorded
> on rather than on a form the operator already saved.

## `RunSteps.prepare`, [line 109](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L109): Note

Code: `and primary_gesture(one, by_id) is not None`

> The run's start page is the first browser step's page; a learned field step
> has none of its own, so it is passed over here.

## `RunSteps.prepare`, [line 119](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L119): Note

Code: `if fresh := [one for one in fresh if one["name"] not in known]:`

> The fields composed from the run's values (X10), each placed before the write
> whose screen shows its label. `prepare` runs again after every answer, so a
> field already composed (or placed by an answer) is kept as it is.

## `RunSteps.step`, [line 155](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L155): Note

Code: `if index == 0:`

> A value no field on the form is labelled by, or more than one is, is asked
> about before any step runs (`kind="field"`, choices the form's labels): the
> operator chooses the field or leaves the value out, and nothing is guessed.

## `RunSteps.finish`, [line 285](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L285): Note

Code: `async def finish(self, ctx: RequestContext, run_id: str) -> str:`

> Learning happens here, after the last step, because growing the job renumbers
> its steps: done mid-run it would move the steps under this run's own
> `progress.step`. The fields are learned from the last write back, so each
> insertion leaves the earlier ones' orders alone.

## `RunSteps.finish`, [line 310](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L310): Note

Code: `and len(confirmed) == len(progress.composed)`

> A run that filled a field the save did not carry is not `held`: the operator
> asked for the value and it was not saved, whatever the write's own verdict.

## `RunSteps.answered`, [line 377](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L377): Note

Code: `if kind == "field":`

> "" leaves the value out: it leaves the run's values and is named `unasked`,
> as a name the job has no parameter for always was. An option replaces the
> value. After a fill that failed, choosing the field again tries it again.
> Any other choice is one of `choices`, each naming exactly one field, and
> places the name there.

## `RunSteps._fill_for`, [line 667](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L667): Note

> Before a write, every field composed for it is filled on the page. A fill
> that asks becomes the question and the write is not started; a fill that
> fails asks as an ordinary step question. A filled field is recorded `unknown`
> before the write, because a fill alone never confirms anything (spec §6.2).
> The write then carries an `Adding`: the learned field steps just before it by
> their known key, and every field's held value, so only the save's own call
> carrying that value can confirm it.
>
> A write tried again (it already has a row: it failed, asked, or the page
> was reloaded under it) fills its learned fields again too, as it does its
> composed ones: the value that was on the page may be gone.

## `RunSteps._fill_step`, [line 740](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L740): Note

> A learned field step: filled by its learned locator on the form of the next
> write, recorded `unknown` until that write's own call carries its key. A
> step whose save is already marked sent, or in doubt (an earlier field's
> sight fill pressed Save, or an activity retried after `_sending`), is not
> filled at all: it is recorded `unknown` and the save's own in-doubt check
> settles it -- another fill could press Save a second time. A run
> with no value for it passes over it the way it passes over any step whose
> optional values are all absent (`skipped`).

## `RunSteps._fill_asks`, [line 781](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L781): Note

> What a fill that could not be made asks; every such question can be
> answered "leave it out". A dropdown without the option, or with two options
> equal but for case, asks for one of its options. A label missing from the
> live page, or on it twice, asks for another field (never the same one
> again). A fill that failed otherwise -- and anything on a learned field
> step, which has no composed field to re-place -- offers the field itself,
> to try again. The question never carries the value.

## `_fields_for`, [line 981](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L981): Note

> The learned field steps filled this run just before the write at `index`.

## `_settle_fields`, [line 993](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L993): Note

> Each field filled for this write takes `done` and its key only when the write
> is `done` and its own call carried the key; it becomes `failed` when the write
> failed, and otherwise stays `unknown`. A composed field a `done` save did not
> carry gets its own `unclear` row, so a run that fails for it says why.

## `RunSteps._not_filled`, [line 724](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L724): Note

> A fill that sent the write (sight pressed Save, or Enter submitted the form)
> is not a field that failed: the write is marked sent and goes down its own
> in-doubt path -- read back, else a step question with `done`/`not_done` --
> and is never offered "try again" or "leave it out", both of which would send
> it a second time. On a learned field step the field step is recorded
> `unknown` and the next write is the one in doubt.

## `RunSteps.prepare`, [line 112](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L112): Note

Code: `resume = ordered[progress.step].order if progress.step < len(ordered) else math.inf`

> Fields are composed only for writes at or after the resume point, and never
> for a write the operator's mark is on (done or in doubt) -- `take_over`
> resumes at the first write not done, so a later one can be theirs already.
> Their save decided its fields, and a value the mail carried for one of them
> is out of scope. Composing it anyway left a field nothing would ever fill,
> and `finish` then failed a run whose every write held.

## `RunSteps.finish`, [line 289](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L289): Note

Code: `version = workflow`

> Latest field first, so each grow leaves the earlier fields' `before` true.
> Each `learn_field` is its own compare-and-set against the version this run's
> earlier fields make of its pin (`with_field`, whether or not that grow was
> this attempt's), so a retried `finish` skips the fields already learned and
> learns the rest; once another writer has moved the job, every later field is
> refused.

## `RunSteps._lane_context`, [line 487](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L487): Note

Code: `learned = await self._teach.locators(ctx, workflow)`

> Locators are keyed by the job's own step numbers. A run whose pinned steps
> the job has grown past would read another step's locator under its own
> number -- a field's locator on a save, say -- so it reads none, and its lanes
> find their controls from the evidence as a first run would.

## `RunSteps._load`, [line 891](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L891): Note

Code: `if run.pinned is not None`

> A pinned run never reads the live job: retired mid-run, it still finishes on
> its pin (only its learning is skipped). Every activity of a run -- prepare, step, finish, a read-back, an answer --
> reads the job through here, so every one of them reads the run's pinned
> version. `progress.step` is an index and the marks are keyed by step number;
> read against a job grown since, the index names another step and a write
> already sent has no mark, and is sent again.

## `RunSteps.answered`, [line 395](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L395): Comment

Code: `if kind == "recipient":`

> The operator named who the mail goes to: each address is kept on the job
> (`keep_the_named`, with who and when), and the step is tried again, so the
> draft is written anew and this time may go there -- as will the job's next
> run. It is an upsert, so an answer carried out twice (a crash before the
> question closes) keeps one row.

## `RunSteps.answered`, [line 394](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L394): Comment

Code: `taught = JobAlias(name, hit.label, by, self._clock.now(), role)`

> Only the reader's own question teaches the job a word (spec §4.2): the one
> asked before the first step because `compose` could not place a wording
> (`wording=True` on `_ask`). The same `no_field`/`ambiguous` question from
> `_fill_asks` is the live page lacking a field this run, not a doubt about
> the wording, so the operator's pick there moves this run's value and teaches
> nothing. Nor does leaving it out, an option (`no_option`, a value, not a
> field), a `failed` retry, a wording that is already a label on the form (it
> would shadow that label forever), or a generic word (`teaches`,
> `K_GENERIC`). The alias is the answering operator's (`by`, which
> `AnswerRun` keeps with the choice), not the run's starter's. It stores the
> form's label, plus the role when the choice had to tell two same labels
> apart, so the next run places it on that one without asking again.

## `RunSteps._write`, [line 866](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L866): Comment

Code: `await uow.workflows.confirm_alias(ctx.tenant_id, run.workflow_id, taught)`

> The alias is written in the answer's own unit of work, inside the
> compare-and-set that closes the question: an answer another attempt moved
> past (`Superseded`) teaches nothing, and one carried out twice finds the
> question already closed the second time. A crash before the commit loses
> both, and the answer is carried out again. `confirm_alias` is an upsert per
> normalised wording either way. This is the only writer of an alias
> (`tests/unit/test_only_an_answer_writes_an_alias.py`).

## `RunSteps._ask`, [line 636](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L636): Comment

Code: `if wording:`

> Marks the question as the reader's "which field does this wording mean",
> the only question whose answer may become an alias (`RunSteps.answered`).

## `RunSteps.finish`, [line 321](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L321): Note

Code: `await announce.answered_elsewhere(ctx, run)`

> The run ends; if its question is still open and a reply reached only a
> colleague's mailbox, the starter is told (`SayWhatHappened.answered_elsewhere`;
> S1 rounds 1 and 2).

>
> And every run says how it ended, once, the first time it finishes: "Done:
> <job> (<values>)" or "<job> did not finish -- it stopped at '<step>': <why>".
> Before this the thread said "Running ... now" and then nothing, whichever
> way the run went (greyorange, 2026-09-28).

## `RunSteps.answered`, [line 397](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L397): Note

Code: `if kind == MAIL_BODY:`

> The starter's words for the mail go on the run (`Progress.told`) and the step
> runs again: the lane writes the mail with them as part of the request (S4
> round 1, I1).

## `RunSteps._lane_context`, [line 515](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L515): Note

Code: `if sends_mail(step, by_id)`

> The request is read only for a step that sends mail: no other lane reads it,
> and it costs a thread read (S4 round 1, M1).

## `RunSteps.step`, [line 271](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L271): Note

Code: `elif last.refused:`

> A write the system refused ends the run; it does not park it on a person.
> PJ26 (greyorange, 2026-09-30): the save was refused and the run sat on
> "check it and answer" while the mail card said Running. Nothing a person
> answers about THIS run can make the same values go in: what changes the
> outcome is a new value, and a new value is a new run.
>
> So the step is kept as failed, in the system's own words, the names the
> refusal is about become `run.needs`, and `awaiting` is let go -- a reply on
> the mail thread is taken by the question, not by a run that has ended. The
> question itself is asked by `finish` (`AsksForValues`, wired to
> `StartWorkflowRun.ask_for_values`): the one asker that already puts a run's
> missing values in a chat of its own and drafts to whoever sent the mail. The
> answer starts one new run (its question's message id is the offer); this one
> stays as history.
