from __future__ import annotations

from sro.application.ports.repositories import WorkflowRepository
from sro.domain.execution.belts import earned_from
from sro.domain.execution.verified_writes import learned_pattern
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.hosts import origin_of
from sro.domain.shared.identifiers import TenantId

K_UNEARNING = ("failed", "unclear")


def wrote(step: RunStep) -> bool:
    return bool((step.result or {}).get("wrote"))


async def record_effect(
    workflows: WorkflowRepository,
    run: WorkflowRun,
    step: RunStep,
    *,
    at: str,
    recorded: str | None = None,
) -> None:
    if not (run.live and step.verdict == "held" and wrote(step)):
        return
    await workflows.record_effect(
        run.workflow_id,
        run_id=run.id,
        ord_=step.order,
        verified_by=step.verdict_by,
        at=at,
    )
    await _remember_the_write(workflows, run, step, at=at, recorded=recorded)


async def _remember_the_write(
    workflows: WorkflowRepository,
    run: WorkflowRun,
    step: RunStep,
    *,
    at: str,
    recorded: str | None,
) -> None:
    watched = (step.result or {}).get("called")
    sent = (step.sent or {}).get("payload")
    call = watched if isinstance(watched, dict) else sent
    url = str(call.get("url", "")) if isinstance(call, dict) else ""
    method = str(call.get("method", "")) if isinstance(call, dict) else ""
    pattern = learned_pattern(url, run.values, recorded) if url and method else None
    if pattern is None:
        return
    await workflows.remember_write(
        TenantId(run.tenant),
        method=method,
        path_pattern=pattern,
        origin=origin_of(url),
        run_id=run.id,
        workflow_id=run.workflow_id,
        verified_by=step.verdict_by,
        at=at,
    )


def may_have_landed(step: RunStep) -> bool:
    result = step.result or {}
    if result.get("ok") is False:
        return False
    if result.get("refuted") is True:
        return False
    status = result.get("status")
    return not (isinstance(status, int) and 400 <= status < 500)


def can_try_again(run: WorkflowRun) -> bool:
    if run.outcome in ("running", "held"):
        return False
    return not any(wrote(step) and may_have_landed(step) for step in run.steps)


async def forget_effects(workflows: WorkflowRepository, run: WorkflowRun) -> int:
    if not (
        run.live
        and any(
            step.verdict in K_UNEARNING and wrote(step) and may_have_landed(step)
            for step in run.steps
        )
    ):
        return 0
    return await workflows.forget_effects(run.workflow_id)


async def earned(workflows: WorkflowRepository, tenant_id: TenantId, workflow_id: str) -> bool:
    return earned_from(await workflows.proofs(tenant_id, workflow_id))
