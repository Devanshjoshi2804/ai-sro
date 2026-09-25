# Notes for `backend/src/sro/application/runtime/run_steps.py`

Comments and docstrings moved out of [`backend/src/sro/application/runtime/run_steps.py`](../../../../../../../backend/src/sro/application/runtime/run_steps.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `RunSteps`, [line 55](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L55): Class

> A Steel run's activities (spec §7.2): prepare, acquire, one step per call,
> finish, release, beat. Each loads the run and its `progress` afresh, so a
> Temporal retry of any of them is safe: `progress` guards every write. It is
> written only through `record_progress` (D1); `save` carries the steps and
> the outcome. None of them acts on a run that is no longer `running`. A code
> change here is live only after the worker restarts (AGENTS.md).

## `RunSteps.step`, [line 122](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L122): Note

Code: `if progress.in_doubt(step.order):`

> A write marked `sending` (or settled `unknown`) by an earlier attempt is
> never sent again by any path: a retried step runs no lane, it settles the
> write by the API lane's read-back -- signed in afresh when the mark says the
> session had expired, credited to the lane that sent it -- else it asks.

## `RunSteps.step`, [line 144](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L144): Note

Code: `except (NeedsAPerson, AccountBusy, PageGone) as why:`

> The executor raises these carrying the lanes it tried; what they taught is
> learned before anything else. A person is asked; a busy account (another
> run's sign-in is parked on a person) and a lost page are raised again for
> the activity to retry. `Superseded` is raised untouched: another attempt
> holds the run.

## `RunSteps.step`, [line 170](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L170): Note

Code: `await self._teach.learn(ctx, workflow, by_id, step, tried, run_id=run_id, values=values)`

> Taught after the step is recorded, so a teaching failure never turns a
> write proven done back into one in doubt.

## `RunSteps.finish`, [line 173](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L173): Note

Code: `async def finish(self, ctx: RequestContext, run_id: str) -> str:`

> Runs on every path out of the workflow, so a run is never left `running`:
> `held` only when every step was reached and each is held or withheld;
> an outcome already set (a stop's `aborted`) is kept.

## `RunSteps.beat`, [line 218](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L218): Note

Code: `if progress.lease and not await self._broker.beat(ctx, progress.lease, holder=run_id):`

> A beat the lease no longer answers is a lost lease: the lost-page path.

## `RunSteps._keep_tab`, [line 265](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L265): Note

Code: `except BaseException:`

> A tab this attempt opened but could not record is closed at once; a retry
> would open another, and nothing would ever release the first.

## `RunSteps._sending`, [line 308](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L308): Note

Code: `if again and wrote == "sending":`

> The same lane run again after a re-sign-in (X8) marks the write it already
> marked; any other mark means another attempt got there first, and this one
> sends nothing.

## `RunSteps._settled`, [line 315](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L315): Note

Code: `async def _settled(`

> Settling an `unknown` write is this class's job (X8): a read-back first,
> signed in afresh when the result says the session expired; nothing to read
> back means a person is asked and the mark stays in doubt.

## `RunSteps._advance`, [line 361](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L361): Note

Code: `progress.step, progress.asking = index + 1, {}`

> A step that settles after asking withdraws its own question: the held row
> follows the unclear one, and D5 takes an answer to a withdrawn question as
> already answered.

## `RunSteps._ask`, [line 377](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L377): Note

Code: `async def _ask(`

> Every question is also a step row (`failed`, or `unclear` for a write
> nobody can confirm) with the question as its reason, so the console shows
> where and why the run stopped. Asked from prepare and acquire too, at the
> step the run stands on.

## `RunSteps._write`, [line 473](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L473): Note

Code: `ctx.tenant_id, run.id, now, was=run.progress`

> A compare-and-set: progress is written only over the progress this attempt
> loaded. Temporal can start a retry while the attempt it gave up on still
> runs (a missed heartbeat, a partition); whichever writes second finds it
> changed and stops with `Superseded`, so one write is never sent twice and
> a step is never skipped.

## `RunSteps._run`, [line 488](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L488): Note

Code: `raise Stopped(f"run {run_id} is not known")`

> A run this tenant does not hold is a stop: nothing more may be done for it,
> and retrying cannot bring it back.

## `RunSteps.finish`, [line 176](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L176): Note

Code: `last = {one.of_step: one.verdict for one in sorted(run.steps, key=lambda s: s.order)}`

> Judged by each step's last row: an `unclear` a read-back later settled as
> `held` is history, not the step's result.

## `RunSteps._write`, [line 466](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L466): Note

Code: `if (index is not None and loaded.step != index) or (`

> The one guard every step write passes, beside the compare-and-set: an
> attempt only records a step's result or question while the run still
> stands on that step, and a question only while the step is not done. A
> zombie whose lane fails after the retry already held the step asks nothing
> and adds no row.

## `RunSteps.release`, [line 192](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L192): Note

Code: `run.outcome == "running" and progress.asking.get("kind") == "code"`

> A waiting run holds nothing (spec §7.4): its tab is closed while it waits
> and a browser is taken again after the answer. The one exception is a
> one-time code. The code belongs to the page that asked for it, so that tab
> and its WAITING lease are kept across the release and resumed on the answer
> (`SessionBroker.resume`). Once the run is no longer running the code tab is
> closed like any other; the WAITING lease runs out at its own deadline.

## `RunSteps.answered`, [line 207](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L207): Note

Code: `if asking.get("id") != question_id:`

> An answer to a question that is no longer standing changes nothing. A
> question can be withdrawn under a waiting workflow: an earlier attempt's
> write was confirmed by its own call, the step settled done and its stale
> ask was cleared (D2). The step has moved on, so the run carries on from the
> next one and never runs that step again.

## `RunSteps.answered`, [line 212](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L212): Note

Code: `await self._broker.unpark(ctx, progress.lease)`

> A refused re-sign-in parks the account's lease WAITING so queued runs wait
> on the one question. Once the person has stored a new password the park is
> ended at once, never waited out, and the next acquire signs in afresh.

## `RunSteps._acquire`, [line 230](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L230): Note

Code: `if kept.lease.state is not LeaseState.WAITING:`

> A tab still held after an answer is a one-time code's page on a WAITING
> lease: it is resumed (the person dealt with the code there), never used as
> it is. A code the page still asks for, or a password page in its place, is
> asked again.

## `RunSteps._ask`, [line 396](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L396): Note

Code: `if isinstance(asked, WaitingForAPerson):`

> A one-time code keeps the page that asked for it; recording that tab and
> lease as the run's own is what lets `release` keep it and `acquire` resume
> it. The question is said in the operator's thread only after it is written,
> so an attempt another one superseded says nothing.

## `RunSteps.finish`, [line 181](../../../../../../../backend/src/sro/application/runtime/run_steps.py#L181): Note

Code: `run.awaiting = None`

> A run started from a mail waits on that mail's conversation for a reply.
> Once it has finished with nothing left to ask, a reply there is a new
> request again, as the extension's `perform` settles it.
