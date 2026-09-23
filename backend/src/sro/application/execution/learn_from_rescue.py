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
    await uow.workflows.remember_locator(workflow.id, learned, by_run=last.id)
    return learned


def _last_finished(runs: Sequence[WorkflowRun]) -> WorkflowRun | None:
    return next((run for run in reversed(runs) if run.finished_at), None)


def _cited_url(step: Step, by_id: Mapping[str, Gesture]) -> str:
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
