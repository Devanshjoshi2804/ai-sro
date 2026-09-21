"""The register of verified writes, and what it buys a job.

Ported from `new_agent_arch/src/rig/effects.py`, over the `WorkflowRepository`
port -- and with it the two gates the rig's runner kept around those calls,
which are the half of the rule that decides which of a run's steps reach the
register and which empty it.

The rule itself is `sro.domain.execution.belts` and is not restated here:
`state_verified` is the gate the repository keeps, `RunProof` is what it
assembles out of the runs, and `earned_from` counts them.

D2 of the autonomous-workflows design: autonomy is earned by verified effect,
not by counting runs. A write counts only when the verifier decided `held` by
state -- a status the server answered, or a read that showed the record -- and
never by a picture, because a model reading a screenshot is not evidence
anything was written. `K_EARNED_RUNS` live runs that held, each with every
write of theirs in the register, is what a job pays for the right to write
without asking a person first.

And one failed write empties the register for the WORKFLOW, not for the run
that made it. A job that has ever written wrongly starts earning again from
zero, and the next runs ask for a tap.
"""

from __future__ import annotations

from sro.application.ports.repositories import WorkflowRepository
from sro.domain.execution.belts import earned_from
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import TenantId

K_UNEARNING = ("failed", "unclear")
"""The verdicts on a write that un-earn the job. `unclear` counts with
`failed`: a live write nobody could show held is exactly the state the tap
exists for."""


def wrote(step: RunStep) -> bool:
    """Whether this step sent something that may have changed the warehouse.

    The step's own marker, which the runner set at send time out of the same
    `may_write` the tap and the rescue gate use -- SQL cannot ask `writes()`,
    and the evidence a later reader would have to ask it about may have been
    re-mined by then. So a step marked `wrote` is a step that can earn, and the
    same predicate is what un-earns: a step that could not earn cannot un-earn.

    A skipped step has no stored result at all, so it is not a write. It is not
    something a run has to have verified, and it must not stop one that did.
    """
    return bool((step.result or {}).get("wrote"))


async def record_effect(
    workflows: WorkflowRepository, run: WorkflowRun, step: RunStep, *, at: str
) -> None:
    """Register one write of this run that the verifier saw hold by state.

    Three gates, read off the record rather than off the runner's locals so
    that a second caller cannot forget one: the run was live, because a dry run
    sent nothing and proves nothing about writing; the step held; and the step
    wrote. The fourth -- that the verdict came from a state belt and not from a
    picture -- is `state_verified`, which is kept once, by the repository.
    """
    if not (run.live and step.verdict == "held" and wrote(step)):
        return
    await workflows.record_effect(
        run.workflow_id,
        run_id=run.id,
        ord_=step.order,
        verified_by=step.verdict_by,
        at=at,
    )


def may_have_landed(step: RunStep) -> bool:
    """Whether a write this step made might actually be in the warehouse.

    The question `forget_effects` has always meant to ask and could not: its
    own docstring says *a write that went out and did not hold*, and the marker
    it had says only *this step was going to write*. The two are different for
    most of the ways a step fails, and the difference is the whole of item 7's
    approval fatigue.

    Measured on the deployment 2026-09-19. `Create a Customer Type` had
    **twenty live runs whose write held by a state belt** and exactly **one**
    row in its effects register, because seventeen other runs failed a write
    and each one wiped the register whole. Of those seventeen, ten never wrote
    anything at all: five `TypeError: Failed to fetch`, one with no CSRF token
    on the page, one with no tab open on the system, one whose control was
    never found, and two where nobody approved the write inside five minutes.
    The job could therefore never reach `K_EARNED_RUNS`, and every run this
    system has ever done asked a person to tap approve.

    Two readings, and each is one the rescue gate two lines away already makes:

    **The browser answered `ok: false`** -- it never performed the command:
    unreachable, no tab on the system, no control found, the approval that
    timed out. Nothing left the machine, so nothing can be in the warehouse.

    **The server itself refused it** -- a `4xx`. A warehouse that answered 422
    did not write the record, and the deployment's own register was emptied by
    one of those.

    A `5xx` is NOT that case and must go on un-earning: a server that broke
    half way may have written and then failed, and "the state is unknown after
    a write" is exactly what the register is for. Everything else is a write
    that went out and could not be shown to have held, which is likewise what
    must cost a job its autonomy.

    A step with no result at all never reaches here: `wrote` reads the marker
    off the result, and the step `_fell_over` stamps has neither. That is the
    rule this file has always had, and `test_effects.py` says so by name.
    """
    result = step.result or {}
    if result.get("ok") is False:
        return False
    status = result.get("status")
    return not (isinstance(status, int) and 400 <= status < 500)


def can_try_again(run: WorkflowRun) -> bool:
    """Whether this run can be started again with one press.

    A run stops for reasons that have nothing to do with the job -- a session
    that expired, a tab closed, a browser that could not be reached -- and the
    offer that started it is spent, so the request sits there until somebody
    notices. On a job started from a mailbox that can be hours.

    **Only where nothing it did may have landed.** Every step that wrote either
    never left the browser or was refused by the warehouse: `may_have_landed`,
    the same reading that decides whether a failed write costs a job its
    autonomy, asked here about the other half of the same danger. A second
    press after a write that might be in the warehouse is how a customer gets
    two of something, and no button is better than that.

    Nothing to try again on a run that held, and nothing to press on one still
    going.
    """
    if run.outcome in ("running", "held"):
        return False
    return not any(wrote(step) and may_have_landed(step) for step in run.steps)


async def forget_effects(workflows: WorkflowRepository, run: WorkflowRun) -> int:
    """A write that went out and did not hold un-earns the whole job.

    Everything the WORKFLOW had earned, not this run's own rows: a job that has
    ever written wrongly starts again from zero.

    Asked of a finished run rather than from the step that failed, because the
    step body is not reached when a browser goes away mid-write -- and that run
    wrote, was never shown to have held, and would otherwise have kept its
    autonomy.

    And only where the write MAY have landed. A step whose command the browser
    never performed changed nothing, and punishing a job for it is how a job
    with twenty verified writes ends up with one row in its register and a
    person tapping approve on every run. See `may_have_landed`.

    Returns how many effects were forgotten, and zero when this run un-earned
    nothing.
    """
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
    """Whether this job may write without asking a person first.

    Task 1's `tallies` is deliberately not asked here, and not because it is
    the more expensive read: it cannot answer this question at all. It counts
    runs and runs that held, and has no notion of a verified effect -- a job
    with a hundred held runs and nothing in its register has earned nothing.
    Only `proofs` carries what the rule compares.
    """
    return earned_from(await workflows.proofs(tenant_id, workflow_id))
