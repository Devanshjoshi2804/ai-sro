"""What a job earns by writing, and what one bad write costs it.

Ported from `new_agent_arch/tests/test_effects.py`. Plan 1 already carried all
nine of those names into `tests/unit/domain/rig/test_belts.py`, against
hand-built `RunProof` rows -- and four of them arrive there saying much less
than they said in the rig, because a `RunProof` is the answer to the questions
they ask. "A dry run never earns anything" becomes "two proofs is not three";
"another tenant's run does not earn this one's" becomes "one proof is not
three"; "a held run that wrote nothing" and "a step that never sent anything"
become statements about a `frozenset` somebody typed. The runs themselves --
live or not, held or not, whose, and what each step actually sent -- are only
real one layer up, which is here.

So eight of the nine travel again with their names unchanged, against real runs
through the fake repository. The ninth --
`test_the_number_of_runs_autonomy_costs_is_the_one_a_person_agreed_to` -- stays
in `test_belts.py`, where it asserts `K_EARNED_RUNS == 3` against the constant
itself and there is nothing for this layer to add to it.

Beside them are thirteen guards that are new. Every one came from mutating an
argument at the call site rather than the rule it feeds: that the belt, the
step and the clock the caller gave all reach the register; that an effect is
filed against the workflow and not against the run; that a write the verifier
did not decide un-earns exactly as a refused one does, which the rig recorded
only in a comment; that a step which failed without writing leaves the register
alone; that a dry run neither earns nor un-earns; and that a run whose browser
went away with a step in flight -- a failed verdict on a step with no stored
result at all, which is the only call that hands `wrote` a `None` -- takes
nothing away from the job, because that step sent nothing.
"""

from copy import deepcopy

from sro.application.execution.effects import earned, forget_effects, record_effect
from sro.domain.execution.workflow_run import RunStep, WorkflowRun
from sro.domain.shared.identifiers import TenantId
from tests.unit.fakes import FakeWorkflowRepository, FakeWorkflowRunRepository

_TENANT = TenantId("acme")
_OTHER = TenantId("someone-else")
_WORKFLOW = "wfl_1"
# Never today: a fixture dated "now" passes on the day it is written and stops
# meaning anything the day after.
_STARTED = "2026-03-04T10:00:00+00:00"
_FINISHED = "2026-03-04T10:01:00+00:00"
_AT = "2026-03-04T10:00:30+00:00"


def _wrote(
    order: int = 1, *, verdict: str = "held", by: str = "status", status: int = 201
) -> RunStep:
    """A step that sent something the warehouse may have kept."""
    return RunStep(
        order=order,
        says="save the count",
        verdict=verdict,
        verdict_by=by,
        result={"ok": True, "status": status, "matched_by": None, "wrote": True},
    )


def _read(order: int = 1, *, verdict: str = "held", by: str = "read") -> RunStep:
    """A step that only looked. No `wrote` marker at all, as the runner leaves
    it -- the marker is written only when the step may have changed something."""
    return RunStep(
        order=order,
        says="open the list",
        verdict=verdict,
        verdict_by=by,
        result={"ok": True, "status": 200, "matched_by": None},
    )


def _skipped(order: int = 2) -> RunStep:
    """A step that never sent anything: no stored result at all."""
    return RunStep(order=order, says="nothing to do", verdict="skipped", result=None)


def _fell_over(order: int = 2) -> RunStep:
    """The step the runner writes when the run did not get to finish it.

    A failed verdict and no stored result at all -- the shape `_fell_over`
    leaves behind when a browser goes away mid-run, and the shape of an
    in-flight step whose send raised. It is the one step that reaches the
    un-earning predicate with a `K_UNEARNING` verdict AND a `None` result,
    which is the only call that asks `wrote` what it does with nothing.
    """
    return RunStep(order=order, says="", verdict="failed", verdict_by="none", result=None)


def _run(
    run_id: str,
    steps: list[RunStep],
    *,
    live: bool = True,
    outcome: str = "held",
    tenant: str = "acme",
    workflow_id: str = _WORKFLOW,
) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        tenant=tenant,
        workflow_id=workflow_id,
        device_id="dev_test",
        values={},
        started_by="offer",
        live=live,
        allow_focus=True,
        started_at=_STARTED,
        finished_at=_FINISHED,
        outcome=outcome,
        steps=steps,
    )


def _store() -> tuple[FakeWorkflowRepository, FakeWorkflowRunRepository]:
    runs = FakeWorkflowRunRepository()
    return FakeWorkflowRepository(runs), runs


async def _ran(
    workflows: FakeWorkflowRepository,
    runs: FakeWorkflowRunRepository,
    run: WorkflowRun,
) -> WorkflowRun:
    """One finished run: stored, then every step offered to the register."""
    await runs.save(run)
    for step in run.steps:
        await record_effect(workflows, run, step, at=_AT)
    await forget_effects(workflows, run)
    return run


async def _proven(
    workflows: FakeWorkflowRepository, runs: FakeWorkflowRunRepository, how_many: int
) -> None:
    for i in range(how_many):
        await _ran(workflows, runs, _run(f"run_{i}", [_wrote()]))


async def test_three_live_runs_whose_writes_all_verified_by_state_earn_autonomy() -> None:
    """Written with a literal three rather than `K_EARNED_RUNS`: a loop phrased
    in terms of the constant earns at two the day somebody sets it to two,
    which is the one thing this test exists to notice."""
    workflows, runs = _store()

    await _proven(workflows, runs, 1)
    assert await earned(workflows, _TENANT, _WORKFLOW) is False
    await _proven(workflows, runs, 2)
    assert await earned(workflows, _TENANT, _WORKFLOW) is False
    await _proven(workflows, runs, 3)
    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_screen_only_verification_is_not_an_effect() -> None:
    """A model reading a picture is not evidence anything was written, so the
    verdict never reaches the register and three such runs earn nothing."""
    workflows, runs = _store()
    for i in range(3):
        await _ran(workflows, runs, _run(f"run_{i}", [_wrote(by="screen")]))

    assert workflows.effects == {}
    assert await earned(workflows, _TENANT, _WORKFLOW) is False


async def test_a_run_with_one_unverified_write_does_not_count() -> None:
    """Two writes, one of them decided by a picture. Every write of a run has
    to be in the register, not merely one of them."""
    workflows, runs = _store()
    for i in range(3):
        await _ran(workflows, runs, _run(f"run_{i}", [_wrote(1), _wrote(3, by="screen")]))

    assert await earned(workflows, _TENANT, _WORKFLOW) is False


async def test_a_failed_write_starts_the_earning_again() -> None:
    workflows, runs = _store()
    await _proven(workflows, runs, 3)
    assert await earned(workflows, _TENANT, _WORKFLOW) is True

    # A write that went out and could not be shown to have held -- which is
    # what un-earning is for. NOT one the server refused: `by="status"` on a
    # failure is a 4xx, and a warehouse that answered 422 wrote nothing. See
    # `may_have_landed`.
    spoiled = _run("run_bad", [_wrote(verdict="failed", by="screen")])
    await runs.save(spoiled)
    assert await forget_effects(workflows, spoiled) == 3
    assert await earned(workflows, _TENANT, _WORKFLOW) is False


async def test_a_failed_write_empties_the_register_of_the_workflow_not_of_the_run() -> None:
    """The job starts from zero, not the run that spoiled it. The three earning
    runs kept their rows under any narrower reading of the rule, and the fourth
    had none of its own to lose."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)
    kept = deepcopy(workflows.effects)
    assert {run_id for _, run_id, _ in kept} == {"run_0", "run_1", "run_2"}

    spoiled = _run("run_bad", [_wrote(verdict="failed", by="screen")])
    await runs.save(spoiled)
    await forget_effects(workflows, spoiled)

    assert workflows.effects == {}


async def test_a_write_the_verifier_could_not_decide_un_earns_as_a_refused_one_does() -> None:
    """`unclear` counts with `failed`: a live write nobody could show held is
    exactly the state the tap exists for."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    unsure = _run("run_unsure", [_wrote(verdict="unclear", by="none")])
    await runs.save(unsure)
    assert await forget_effects(workflows, unsure) == 3
    assert await earned(workflows, _TENANT, _WORKFLOW) is False


async def test_a_step_that_failed_without_writing_leaves_the_register_alone() -> None:
    """A step that could not earn cannot un-earn. A read that failed changed
    nothing in the warehouse, and taking a job's autonomy for it would mean a
    job could never keep any."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    looked = _run("run_read", [_read(verdict="failed", by="none"), _skipped()])
    await runs.save(looked)
    assert await forget_effects(workflows, looked) == 0
    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_run_that_died_on_a_step_that_had_sent_nothing_takes_nothing_away() -> None:
    """The browser went away with a step in flight that had not sent yet.

    The runner marks that step failed and leaves it with no stored result at
    all, so it is the one step that reaches the un-earning predicate as a
    `K_UNEARNING` verdict with nothing to read -- the only call that hands
    `wrote` a `None`. Nothing went out, so nothing is taken away: a job whose
    browser is closed on it must not pay for that with everything it earned.
    """
    workflows, runs = _store()
    await _proven(workflows, runs, 3)
    kept = deepcopy(workflows.effects)

    broke = _run("run_broke", [_wrote(1), _fell_over(2)])
    await runs.save(broke)
    assert await forget_effects(workflows, broke) == 0
    assert workflows.effects == kept
    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_run_that_died_before_it_did_anything_at_all_takes_nothing_away() -> None:
    """The same, for the run whose first step never started: the runner appends
    one blank failed step and there is nothing else in the record to read."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    broke = _run("run_broke", [_fell_over(1)])
    await runs.save(broke)
    assert await forget_effects(workflows, broke) == 0
    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_dry_run_never_earns_anything() -> None:
    """A dry run sent nothing, so its write is not a write: nothing is
    registered however state-verified the verdict says it was."""
    workflows, runs = _store()
    for i in range(3):
        await _ran(workflows, runs, _run(f"run_{i}", [_wrote()], live=False))

    assert workflows.effects == {}
    assert await earned(workflows, _TENANT, _WORKFLOW) is False


async def test_a_dry_runs_failed_write_takes_nothing_away() -> None:
    """The other half of the same sentence. A withheld write that came back
    wrong is a rehearsal, not a wrong write, and un-earning on it would let a
    dry run cost a job everything it had."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    rehearsed = _run("run_dry", [_wrote(verdict="failed", by="status")], live=False)
    await runs.save(rehearsed)
    assert await forget_effects(workflows, rehearsed) == 0
    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_run_that_did_not_hold_does_not_count_toward_the_three() -> None:
    """Its verified write is still on the register -- the step held even though
    the run did not -- and the run itself is no proof."""
    workflows, runs = _store()
    await _proven(workflows, runs, 2)
    await _ran(workflows, runs, _run("run_2", [_wrote()], outcome="failed"))

    assert len(workflows.effects) == 3
    assert await earned(workflows, _TENANT, _WORKFLOW) is False


async def test_a_held_run_that_wrote_nothing_proves_nothing_about_writing() -> None:
    workflows, runs = _store()
    for i in range(3):
        await _ran(workflows, runs, _run(f"run_{i}", [_read()]))

    assert workflows.effects == {}
    assert await earned(workflows, _TENANT, _WORKFLOW) is False


async def test_another_tenants_run_does_not_earn_this_ones_autonomy() -> None:
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    assert await earned(workflows, _TENANT, _WORKFLOW) is True
    assert await earned(workflows, _OTHER, _WORKFLOW) is False


async def test_a_job_earns_nothing_from_another_jobs_verified_writes() -> None:
    """Three proven runs of one workflow, and the workflow beside it has
    earned nothing at all."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    assert await earned(workflows, _TENANT, _WORKFLOW) is True
    assert await earned(workflows, _TENANT, "wfl_2") is False


async def test_a_step_that_never_sent_anything_is_not_read_as_a_write() -> None:
    """A skipped step has no stored result at all. It is not a write the run
    has to have verified, and it must not stop one that did."""
    workflows, runs = _store()
    for i in range(3):
        await _ran(workflows, runs, _run(f"run_{i}", [_wrote(1), _skipped(2)]))

    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_write_that_did_not_hold_is_never_registered_as_an_effect() -> None:
    """The register is of writes that were shown to have happened. A refused
    one is not one, and it is not filed and then filtered later.

    Deliberately not routed through `_ran`: a run carrying a failed write also
    un-earns, so an empty register at the end of one proves only that
    `forget_effects` ran. `record_effect` is asked on its own, and the register
    has to be empty before anything has had a chance to clear it.
    """
    workflows, runs = _store()
    run = _run("run_0", [_wrote(verdict="failed", by="status")])
    await runs.save(run)
    await record_effect(workflows, run, run.steps[0], at=_AT)

    assert workflows.effects == {}


async def test_a_write_nobody_could_decide_is_never_registered_either() -> None:
    """The other verdict a live write can come back with. `unclear` is not
    `held`, and a write nobody could show held is the state the tap exists
    for -- registering it would buy autonomy with the doubt itself.

    Carries a state belt on purpose. Today's verifier only ever returns
    `unclear` by `screen` or by `none`, which the repository's own gate would
    drop whatever this one did -- so a belt of `none` here would pass with the
    `held` gate deleted, and prove nothing about it. `status` leaves the
    verdict as the only thing that can stop the write.
    """
    workflows, runs = _store()
    run = _run("run_0", [_wrote(verdict="unclear", by="status")])
    await runs.save(run)
    await record_effect(workflows, run, run.steps[0], at=_AT)

    assert workflows.effects == {}


async def test_the_register_keeps_the_belt_the_step_and_the_clock_it_was_given() -> None:
    """Which write, decided by which belt, and when. All three come from the
    caller, and a register that invents any of them is a register that cannot
    tell one run's write from another's."""
    workflows, runs = _store()
    run = _run("run_0", [_wrote(4, by="read")])
    await _ran(workflows, runs, run)

    assert workflows.effects == {(_WORKFLOW, "run_0", 4): ("read", _AT)}


async def test_an_effect_is_filed_against_the_workflow_and_not_against_the_run() -> None:
    """What is earned belongs to the job, not to the run that earned it -- the
    next run of the same job is what spends it."""
    workflows, runs = _store()
    await _ran(workflows, runs, _run("run_0", [_wrote()]))

    assert [key[0] for key in workflows.effects] == [_WORKFLOW]


async def test_one_write_verified_twice_is_one_effect() -> None:
    """A write rescued to the second rung verifies at the same step of the same
    run, and that is not two proofs."""
    workflows, runs = _store()
    run = _run("run_0", [_wrote(1, by="status")])
    await runs.save(run)
    await record_effect(workflows, run, run.steps[0], at=_AT)
    await record_effect(workflows, run, _wrote(1, by="read"), at=_AT)

    assert workflows.effects == {(_WORKFLOW, "run_0", 1): ("read", _AT)}


# -- and only where the write may really have landed ---------------------------


def _never_sent(order: int = 1, *, kind: str = "unreachable") -> RunStep:
    """A write the browser never performed: unreachable, no tab on the system,
    no control found, or an approval nobody gave inside five minutes. The
    runner marks the step as a write at SEND time, so the marker is there and
    the command never left the machine."""
    return RunStep(
        order=order,
        says="save the count",
        verdict="failed",
        verdict_by="none",
        result={"ok": False, "status": None, "error_kind": kind, "wrote": True},
    )


async def test_a_write_the_browser_never_performed_costs_the_job_nothing() -> None:
    """Measured on the deployment 2026-09-19: `Create a Customer Type` had
    twenty live runs whose write held by a state belt and ONE row in its
    register, because seventeen other runs failed a write and each wiped it
    whole. Ten of those seventeen never wrote anything -- five `Failed to
    fetch`, one with no CSRF token, one with no tab, one with no control, two
    approvals that timed out. The job could never reach `K_EARNED_RUNS`, so
    every run ever done asked a person to tap approve."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    fumbled = _run("run_never", [_never_sent()])
    await runs.save(fumbled)

    assert await forget_effects(workflows, fumbled) == 0
    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_write_the_server_refused_costs_the_job_nothing() -> None:
    """A warehouse that answered 422 did not write the record, and the run is
    free to try again -- which is the same reading the rescue gate makes two
    lines away."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    refused = _run("run_422", [_wrote(verdict="failed", by="status", status=422)])
    await runs.save(refused)

    assert await forget_effects(workflows, refused) == 0
    assert await earned(workflows, _TENANT, _WORKFLOW) is True


async def test_a_server_that_broke_half_way_still_un_earns() -> None:
    """A `5xx` is not a refusal. The server may have written and then failed,
    or a proxy may have given up on an answer that was already on its way --
    which is the state the register exists to be careful about."""
    workflows, runs = _store()
    await _proven(workflows, runs, 3)

    broke = _run("run_500", [_wrote(verdict="failed", by="status", status=500)])
    await runs.save(broke)

    assert await forget_effects(workflows, broke) == 3
    assert await earned(workflows, _TENANT, _WORKFLOW) is False
