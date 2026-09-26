# Notes for `backend/src/sro/application/runtime/run_steps.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/run_steps.py`](../../../../../../../backend/src/sro/application/runtime/run_steps.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `RunSteps`, [line 57](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L57): Class

> A Steel run's activities (spec §7.2): prepare, acquire, one step per call,
> finish, release, beat. Each loads the run and its `progress` afresh, so a
> Temporal retry of any of them is safe: `progress` guards every write. It is
> written only through `record_progress` (D1); `save` carries the steps and
> the outcome. None of them acts on a run that is no longer `running`. A code
> change here is live only after the worker restarts (AGENTS.md).

## `RunSteps.step`, [line 139](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L139): Note

Code: `if progress.in_doubt(step.order):`

> A write marked `sending` (or settled `unknown`) by an earlier attempt is
> never sent again by any path: a retried step runs no lane, it settles the
> write by the API lane's read-back -- signed in afresh when the mark says the
> session had expired, credited to the lane that sent it -- else it asks.

## `RunSteps.step`, [line 164](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L164): Note

Code: `except (NeedsAPerson, AccountBusy, PageGone) as why:`

> The executor raises these carrying the lanes it tried; what they taught is
> learned before anything else. A person is asked; a busy account (another
> run's sign-in is parked on a person) and a lost page are raised again for
> the activity to retry. `Superseded` is raised untouched: another attempt
> holds the run.

## `RunSteps.step`, [line 190](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L190): Note

Code: `await self._teach.learn(ctx, workflow, by_id, step, tried, run_id=run_id, values=values)`

> Taught after the step is recorded, so a teaching failure never turns a
> write proven done back into one in doubt.

## `RunSteps.finish`, [line 193](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L193): Note

Code: `async def finish(self, ctx: RequestContext, run_id: str) -> str:`

> Runs on every path out of the workflow, so a run is never left `running`:
> `held` only when every step was reached and each is held or withheld;
> an outcome already set (a stop's `aborted`) is kept.

## `RunSteps.beat`, [line 272](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L272): Note

Code: `if progress.lease and not await self._broker.beat(ctx, progress.lease, holder=run_id):`

> A beat the lease no longer answers is a lost lease: the lost-page path.

## `RunSteps._keep_tab`, [line 321](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L321): Note

Code: `except BaseException:`

> A tab this attempt opened but could not record is closed at once; a retry
> would open another, and nothing would ever release the first.

## `RunSteps._sending`, [line 364](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L364): Note

Code: `if again and wrote == "sending":`

> The same lane run again after a re-sign-in (X8) marks the write it already
> marked; any other mark means another attempt got there first, and this one
> sends nothing.

## `RunSteps._settled`, [line 371](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L371): Note

Code: `async def _settled(`

> Settling an `unknown` write is this class's job (X8): a read-back first,
> signed in afresh when the result says the session expired; nothing to read
> back means a person is asked and the mark stays in doubt.

## `RunSteps._advance`, [line 417](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L417): Note

Code: `progress.step, progress.asking = index + 1, {}`

> A step that settles after asking withdraws its own question: the held row
> follows the unclear one, and D5 takes an answer to a withdrawn question as
> already answered.

## `RunSteps._ask`, [line 433](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L433): Note

Code: `async def _ask(`

> Every question is also a step row (`failed`, or `unclear` for a write
> nobody can confirm) with the question as its reason, so the console shows
> where and why the run stopped. Asked from prepare and acquire too, at the
> step the run stands on.

## `RunSteps._write`, [line 525](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L525): Note

Code: `ctx.tenant_id, run.id, now, was=run.progress`

> A compare-and-set: progress is written only over the progress this attempt
> loaded. Temporal can start a retry while the attempt it gave up on still
> runs (a missed heartbeat, a partition); whichever writes second finds it
> changed and stops with `Superseded`, so one write is never sent twice and
> a step is never skipped.

## `RunSteps._run`, [line 540](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L540): Note

Code: `raise Stopped(f"run {run_id} is not known")`

> A run this tenant does not hold is a stop: nothing more may be done for it,
> and retrying cannot bring it back.

## `RunSteps.finish`, [line 196](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L196): Note

Code: `last = {one.of_step: one.verdict for one in sorted(run.steps, key=lambda s: s.order)}`

> Judged by each step's last row: an `unclear` a read-back later settled as
> `held` is history, not the step's result.

## `RunSteps._write`, [line 518](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L518): Note

Code: `if (index is not None and loaded.step != index) or (`

> The one guard every step write passes, beside the compare-and-set: an
> attempt only records a step's result or question while the run still
> stands on that step, and a question only while the step is not done. A
> zombie whose lane fails after the retry already held the step asks nothing
> and adds no row.

## `RunSteps.release`, [line 221](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L221): Note

Code: `if run.outcome == "running" and waits == "code":`

> A waiting run holds nothing (spec §7.4): its tab is closed while it waits
> and a browser is taken again after the answer. The one exception is a
> one-time code. The code belongs to the page that asked for it, so that tab
> and its WAITING lease are kept across the release and resumed on the answer
> (`SessionBroker.resume`).
>
> A run that has ended (its answer never came in time, it was stopped, or
> its question was withdrawn under the wait) closes its tab and ends its own
> park, whatever kind it is, so the account is not held for a person nobody
> is waiting on any more. Decided by the lease, not by whether a question
> still stands: WAITING, and parked by this run (the lease's `holder`, which
> `_park` sets and no sibling's beat renames). A lease is per account, so a
> park another run made on it is that run's to end. The park is ended after
> the tab is closed: an ended park is no longer live and its tab could not
> be reached.

## `RunSteps.answered`, [line 241](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L241): Note

Code: `if asking.get("id") != question_id or not asking.get("answered"):`

> The answer is read from the run, where `AnswerRun` kept it; the signal
> only woke the workflow. A question no longer standing, or not answered,
> changes nothing: the step has moved on, or is asked again.

## `RunSteps.answered`, [line 245](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L245): Note

Code: `await self._broker.unpark(ctx, progress.lease, "password")`

> A refused re-sign-in parks the account's lease WAITING so queued runs wait
> on the one question. Once the person has stored a new password the park is
> ended at once, never waited out, and the next acquire signs in afresh.

## `RunSteps._acquire`, [line 286](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L286): Note

Code: `if kept.lease.state is not LeaseState.WAITING:`

> A tab still held after an answer is a one-time code's page on a WAITING
> lease: it is resumed (the person dealt with the code there), never used as
> it is. A code the page still asks for, or a password page in its place, is
> asked again.

## `RunSteps._ask`, [line 452](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L452): Note

Code: `if isinstance(asked, WaitingForAPerson):`

> A one-time code keeps the page that asked for it; recording that tab and
> lease as the run's own is what lets `release` keep it and `acquire` resume
> it. The question is said in the operator's thread only after it is written,
> so an attempt another one superseded says nothing. Its id is random, so an
> answer cannot be sent ahead for a question not yet asked.

## `RunSteps.finish`, [line 201](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L201): Note

Code: `run.awaiting = None`

> A run started from a mail waits on that mail's conversation for a reply.
> Once it has finished with nothing left to ask, a reply there is a new
> request again, as the extension's `perform` settles it.

## `RunSteps.answered`, [line 247](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L247): Note

Code: `if kind == "step" and verdict:`

> The operator's verdict on the step the run asked about. `done` settles it
> done by the operator and the run moves on: no lane runs it again. `not_done`
> records the write as never sent, which is the one thing that lets the lanes
> try a write that was in doubt again.
## `RunSteps.step`, [line 115](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L115): Note

Code: `absent = [name for name in step.parameters if not values.get(name, "").strip()]`

> A step whose parameters nobody gave (spec §6.6.6). A required one is asked
> for (`kind="value"`) before any lane acts -- a lane would otherwise have
> nothing to type, and the recording's value is never a substitute. When
> every parameter of the step is optional and absent, the step is skipped:
> recorded `skipped`, which `finish` counts as kept. A step that carries some
> of its values is performed with those.

## `_demanded`, [line 555](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L555): Note

> The job's required parameter names, by the same `demanded` rule the press
> and the mail reading use.

## `RunSteps.stopped`, [line 208](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L208): Note

Code: `async def stopped(self, ctx: RequestContext, run_id: str) -> None:`

> The one place a stopped run is recorded `aborted`: the workflow calls it
> after the operator's cancel, and `acquire` calls it when the stop arrived
> while it was signing in. A run the step already closed (a lane raised
> `Stopped`, or it held) is left as it is.

## `RunSteps.prepare`, [line 79](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L79): Note

Code: `for one in ordered[progress.step :]`

> The start page and the account are those of the first browser step still to
> run. A run that takes over a job part way through (spec §7.6) begins at its
> first progress's `step`, so Steel opens on the page that step was recorded
> on rather than on a form the operator already saved.
