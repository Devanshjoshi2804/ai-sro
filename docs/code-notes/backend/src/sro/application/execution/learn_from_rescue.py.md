# Notes for `backend/src/sro/application/execution/learn_from_rescue.py`

Comments and docstrings moved out of [`backend/src/sro/application/execution/learn_from_rescue.py`](../../../../../../../backend/src/sro/application/execution/learn_from_rescue.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/execution/learn_from_rescue.py#L1): Docstring

> Take the operator's own repair of a failed step as the lesson for it.
>
> `sro.domain.execution.rescued` holds the rule and the argument for it. This is
> the pass that feeds it: before a run reads what earlier runs learned, it asks
> whether the last one failed and whether somebody fixed that step by hand
> afterwards.
>
> **Here rather than in a sweep.** The only reader of a learned locator is a run,
> so a lesson learned the moment before one starts is a lesson learned in time,
> and a loop in the worker would be a second clock to keep. The operator who
> repairs a step by hand and presses the job again is the whole case this exists
> for, and that press is exactly when this runs.

## `learn_from_the_rescue`, [line 16](../../../../../../../backend/src/sro/application/execution/learn_from_rescue.py#L16): Docstring

> What the operator taught this job by hand since its last run failed.
>
> Only a step whose control was never FOUND. Measured on the deployment
> 2026-09-19: `Delete a Customer Type` failed five times running, every one
> of them with `matched_by = component` -- the browser found the filter
> dropdown by the job's own recorded identity and pressed it, and the screen
> belt then judged from a digest of the top nav bar that nothing had opened.
> Four of the five rescues that followed are that same control again, which
> the rule refuses because the job already says it; the fifth is a click on
> the grid two steps further on, by an operator who had carried on by hand --
> and learning THAT as the first thing to try for step 1 would point a delete
> job's opening click at a row in a table.
>
> A locator is the only thing a rescue can teach, so the only failure it can
> answer is a control nobody could find. A step that was found and pressed
> and then disbelieved did not fail for want of a locator, and the rescue
> after it is somebody getting on with the job, not correcting it.

## `_last_finished`, [line 50](../../../../../../../backend/src/sro/application/execution/learn_from_rescue.py#L50): Docstring

> The job's last run that ended. `for_workflow` is oldest first.

## `_cited_url`, [line 54](../../../../../../../backend/src/sro/application/execution/learn_from_rescue.py#L54): Docstring

> Where the step's own evidence happened, for a row that recorded no url.
>
> A run stopped before it looked at anything writes no `before_url`, and step
> 0 of a job that never got off the ground is exactly that case.

## `learn_from_the_rescue`, [line 46](../../../../../../../backend/src/sro/application/execution/learn_from_rescue.py#L46): Comment

Code: `await uow.workflows.remember_locator(workflow.id, learned, by_run=last.id)`

> `by_run` is the run that FAILED, which is what the history row should
> say: this is what somebody taught the job after that run, and the run
> about to start has taught nothing yet.
