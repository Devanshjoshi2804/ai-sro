"""Take the operator's own repair of a failed step as the lesson for it.

`sro.domain.execution.rescued` holds the rule and the argument for it. This is
the pass that feeds it: before a run reads what earlier runs learned, it asks
whether the last one failed and whether somebody fixed that step by hand
afterwards.

**Here rather than in a sweep.** The only reader of a learned locator is a run,
so a lesson learned the moment before one starts is a lesson learned in time,
and a loop in the worker would be a second clock to keep. The operator who
repairs a step by hand and presses the job again is the whole case this exists
for, and that press is exactly when this runs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from sro.application.ports.repositories import UnitOfWork
from sro.domain.execution.evidence import primary_gesture
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.rescued import K_SOON, rescued_by
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Step, Workflow


async def learn_from_the_rescue(
    uow: UnitOfWork,
    tenant_id: TenantId,
    workflow: Workflow,
    by_id: Mapping[str, Gesture],
) -> LearnedStep | None:
    """What the operator taught this job by hand since its last run failed.

    Only a step whose control was never FOUND. Measured on the deployment
    2026-09-19: `Delete a Customer Type` failed five times running, every one
    of them with `matched_by = component` -- the browser found the filter
    dropdown by the job's own recorded identity and pressed it, and the screen
    belt then judged from a digest of the top nav bar that nothing had opened.
    Four of the five rescues that followed are that same control again, which
    the rule refuses because the job already says it; the fifth is a click on
    the grid two steps further on, by an operator who had carried on by hand --
    and learning THAT as the first thing to try for step 1 would point a delete
    job's opening click at a row in a table.

    A locator is the only thing a rescue can teach, so the only failure it can
    answer is a control nobody could find. A step that was found and pressed
    and then disbelieved did not fail for want of a locator, and the rescue
    after it is somebody getting on with the job, not correcting it.
    """
    last = _last_finished(await uow.workflow_runs.for_workflow(tenant_id, workflow.id))
    if last is None or last.finished_at is None:
        return None
    failed = next((one for one in last.steps if one.verdict == "failed"), None)
    if failed is None or failed.matched_by:
        return None
    step = next((one for one in workflow.steps if one.order == failed.of_step), None)
    if step is None:
        return None
    since = _epoch(last.finished_at)
    if since is None:
        return None
    where = failed.before_url or _cited_url(step, by_id)
    if not where:
        return None
    learned = rescued_by(
        step,
        where,
        since,
        await uow.gestures.gestures_for(tenant_id, after=since, before=since + K_SOON),
        by_id,
    )
    if learned is None:
        return None
    # `by_run` is the run that FAILED, which is what the history row should
    # say: this is what somebody taught the job after that run, and the run
    # about to start has taught nothing yet.
    await uow.workflows.remember_locator(workflow.id, learned, by_run=last.id)
    return learned


def _last_finished(runs: Sequence[WorkflowRun]) -> WorkflowRun | None:
    """The job's last run that ended. `for_workflow` is oldest first."""
    return next((run for run in reversed(runs) if run.finished_at), None)


def _cited_url(step: Step, by_id: Mapping[str, Gesture]) -> str:
    """Where the step's own evidence happened, for a row that recorded no url.

    A run stopped before it looked at anything writes no `before_url`, and step
    0 of a job that never got off the ground is exactly that case.
    """
    gesture = primary_gesture(step, by_id)
    if gesture is None:
        return ""
    return gesture.url or gesture.system or ""


def _epoch(when: str) -> float | None:
    try:
        return datetime.fromisoformat(when).timestamp()
    except ValueError:
        return None


__all__ = ["learn_from_the_rescue"]
