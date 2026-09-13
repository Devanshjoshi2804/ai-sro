"""What a browser is served, and what it is not.

Ported from `new_agent_arch/tests/test_shapes.py`. Plan 1 took the arithmetic
-- given the cited pairs, the held tally and a counsel, what shape comes out
-- into `tests/unit/domain/rig/test_shapes.py`. What is here is everything
that needed the store: the loop over a tenant's workflows, the held gate and the per-workflow reads
behind each shape. The rekeying pass moved with its function to
`tests/unit/application/rig/test_mine.py`, names unchanged. Six of these
carry the names the rig gave them, because plan 1 deferred them by name; the
seventh is the counsel-query half of a test whose shape half is in the domain
file.

Two things every fixture below is arranged against, both of them bugs that
have already shipped on this branch:

* **The clock is the caller's.** `NOW` is a day in February 2025 and never
  today, so a use case that reads `datetime.now(UTC)` instead of its `now`
  cannot agree with these fixtures by the calendar. Task 5 of this plan
  shipped exactly that and was green for one day.
* **An order is planted against itself.** `known()` is oldest first, and
  where the served order is asserted the workflows are saved in an order
  their ids disagree with, so an implementation that sorted by id -- or that
  Postgres handed back in reverse insertion order on a tie -- is not
  satisfied by the plant.
"""

from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from sro.application.skill.record_offer import record_offer
from sro.application.skill.serve_shapes import shapes_for
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.observation.gesture import Gesture
from sro.domain.shared.identifiers import DeviceId, TenantId
from sro.domain.skill.offers import K_OFFER_AFTER
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures
from tests.unit.fakes import FakeUnitOfWork

TENANT = TenantId("acme")
DEVICE = DeviceId("dev_1")
SECOND = DeviceId("dev_2")
HOST = "http://127.0.0.1:63319"

NOW = datetime(2025, 2, 11, 23, tzinfo=UTC)
"""The rig's clock through all of this, and deliberately not today.

Every rule here that reads a clock reads it through `counsel`, which rests a
job for a day after the browser's last refusal. Dated today, a fixture lets a
`shapes_for` that ignores its `now` pass by coincidence."""


def _evidence() -> dict[str, Gesture]:
    return {g.id: deepcopy(g) for g in _gestures()}


def _typed(by_id: dict[str, Gesture]) -> Gesture:
    return next(
        g for g in by_id.values() if g.action.kind == "type" and g.action.value == "ACME-4471"
    )


def _saver(by_id: dict[str, Gesture]) -> Gesture:
    """The click on Save, by its control and not by position."""
    return next(
        g
        for g in by_id.values()
        if g.action.target
        and g.action.target.component
        and g.action.target.component.item_id == "saveButton"
    )


def _workflow(by_id: dict[str, Gesture], wid: str = "wfl_1") -> Workflow:
    return Workflow(
        id=wid,
        tenant=TENANT.value,
        title="create a client",
        narrative="n",
        systems=[HOST],
        steps=[
            Step(
                order=0,
                says="type the code",
                system=None,
                cites=[_typed(by_id).id],
                parameters=["clientCode"],
            ),
            Step(order=1, says="save", system=None, cites=[_saver(by_id).id]),
        ],
        parameters=[{"name": "clientCode", "seen_values": ["ACME-4471"]}],
    )


def _saver_first(by_id: dict[str, Gesture], wid: str) -> Workflow:
    """A workflow that begins on the click rather than the typing, so an edit
    to the typed gesture's `page_url` does not touch where it starts.

    Two cited gestures and not one: `shape_of` refuses a walk shorter than
    `K_OFFER_AFTER`, which `recognise.js` could never match at any k.
    """
    other = next(
        g
        for g in by_id.values()
        if g.action.kind == "press" and g.id not in {_saver(by_id).id, _typed(by_id).id}
    )
    return Workflow(
        id=wid,
        tenant=TENANT.value,
        title="save it",
        narrative="n",
        systems=[HOST],
        steps=[
            Step(order=0, says="save", system=None, cites=[_saver(by_id).id]),
            Step(order=1, says="confirm", system=None, cites=[other.id]),
        ],
    )


def _four_gestures(by_id: dict[str, Gesture], wid: str) -> Workflow:
    """Four cited gestures, so `counsel`'s threshold has room to show through
    the cap at the last gesture but one."""
    ordered = sorted(by_id.values(), key=lambda g: g.at)
    return Workflow(
        id=wid,
        tenant=TENANT.value,
        title="four gestures",
        narrative="n",
        systems=[HOST],
        steps=[
            Step(order=i, says=f"step {i}", system=None, cites=[gesture.id])
            for i, gesture in enumerate(ordered[:4])
        ],
    )


async def _plant(uow: FakeUnitOfWork, by_id: dict[str, Gesture], *workflows: Workflow) -> None:
    await uow.gestures.add_gestures(tuple(by_id.values()))
    for workflow in workflows:
        await uow.workflows.save(workflow)


async def _run(uow: FakeUnitOfWork, run_id: str, workflow_id: str, outcome: str) -> None:
    await uow.workflow_runs.save(
        WorkflowRun(
            id=run_id,
            tenant=TENANT.value,
            workflow_id=workflow_id,
            device_id=DEVICE.value,
            values={},
            started_by="form",
            live=True,
            allow_focus=True,
            started_at="2025-02-11T10:00:00+00:00",
            finished_at="2025-02-11T10:01:00+00:00",
            outcome=outcome,
        )
    )


async def _offers(
    uow: FakeUnitOfWork,
    workflow_id: str,
    fate: str,
    *,
    k: int,
    times: int,
    device: DeviceId = DEVICE,
) -> None:
    for i in range(times):
        await record_offer(
            uow,
            tenant_id=TENANT,
            workflow_id=workflow_id,
            device_id=device,
            k=k,
            fate=fate,
            run_id=None,
            at=(NOW - timedelta(minutes=times - i)).isoformat(),
            now=NOW,
        )


async def _served(uow: FakeUnitOfWork, device: DeviceId | None = None) -> list[str]:
    return [
        shape.id for shape in await shapes_for(uow, tenant_id=TENANT, device_id=device, now=NOW)
    ]


# --------------------------------------------------------------------------
# the loop and its gates


async def test_an_unproven_workflow_is_not_served() -> None:
    uow = FakeUnitOfWork()
    by_id = _evidence()
    workflow = _workflow(by_id)
    workflow.unproven = ["the save was never confirmed"]
    await _plant(uow, by_id, workflow)

    assert await shapes_for(uow, tenant_id=TENANT, now=NOW) == []


async def test_the_held_gate_is_per_workflow_and_never_silences_one_that_never_ran() -> None:
    """One workflow's failure must not withdraw every sibling in the tenant."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    # Saved against their own ids: `known` is oldest first, so a served order
    # of wfl_3 then wfl_1 is the insertion order and disagrees with both the
    # id order and the reverse of it.
    await _plant(
        uow,
        by_id,
        _workflow(by_id, "wfl_3"),
        _workflow(by_id, "wfl_1"),
        _workflow(by_id, "wfl_2"),
    )
    await _run(uow, "run_1", "wfl_1", "held")
    await _run(uow, "run_2", "wfl_2", "failed")

    served = await shapes_for(uow, tenant_id=TENANT, now=NOW)

    assert [shape.id for shape in served] == ["wfl_3", "wfl_1"], (
        "wfl_2 has been run and never held; wfl_3 has never been run at all"
    )
    assert {shape.id: shape.held_runs for shape in served} == {"wfl_3": 0, "wfl_1": 1}


async def test_a_run_that_held_after_one_that_failed_serves_the_job_again() -> None:
    """The gate asks whether the job has *ever* held, not how the last run
    went: a job that failed once and has held since is a job that works."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    await _plant(uow, by_id, _workflow(by_id))
    await _run(uow, "run_1", "wfl_1", "failed")
    await _run(uow, "run_2", "wfl_1", "held")

    [shape] = await shapes_for(uow, tenant_id=TENANT, now=NOW)

    assert shape.id == "wfl_1" and shape.held_runs == 1
    # `shapes_for` is a read, and it is answered inside a request that may be
    # holding writes nobody has finished. A commit here flushes theirs.
    assert uow.commits == 0, "serving a shape writes nothing and commits nothing"


async def test_the_held_gate_counts_only_this_tenant_s_runs() -> None:
    """A run of a workflow id that belongs to somebody else is not this job's
    evidence, in either direction."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    await _plant(uow, by_id, _workflow(by_id))
    await uow.workflow_runs.save(
        WorkflowRun(
            id="run_elsewhere",
            tenant="other-corp",
            workflow_id="wfl_1",
            device_id=DEVICE.value,
            values={},
            started_by="form",
            live=True,
            allow_focus=True,
            started_at="2025-02-11T10:00:00+00:00",
            outcome="failed",
        )
    )

    [shape] = await shapes_for(uow, tenant_id=TENANT, now=NOW)

    assert shape.held_runs == 0, "never run, as far as this tenant is concerned"


async def test_a_workflow_that_cannot_be_served_never_withdraws_the_ones_behind_it() -> None:
    """Three reasons to skip one job, and a fourth job that is fine. Each skip
    is that job's alone: a tenant's whole offer list must not end at the first
    workflow that is unproven, unevidenced, or starts somewhere unproven."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    unproven = _workflow(by_id, "wfl_unproven")
    unproven.unproven = ["the save was never confirmed"]
    uncited = Workflow(
        id="wfl_uncited",
        tenant=TENANT.value,
        title="cites nothing the store holds",
        narrative="n",
        steps=[Step(order=0, says="s", system=None, cites=["ges_remined_away"])],
    )
    elsewhere = _workflow(by_id, "wfl_elsewhere")
    fine = _saver_first(by_id, "wfl_fine")
    # The tab was on one origin while the frame that recorded the gesture was
    # on another. `wfl_fine` starts on the save, which is untouched.
    _typed(by_id).page_url = "https://other.example/x"
    await _plant(uow, by_id, unproven, uncited, elsewhere, fine)

    assert await _served(uow) == ["wfl_fine"]


async def test_the_tenant_s_runs_are_tallied_once_and_never_once_per_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The N+1 this read used to be, pinned as a call count rather than as an
    answer -- the per-workflow shape gave the same three shapes, so an
    assertion on what is served cannot tell the two apart.

    `for_workflow` loads every run of a workflow with all of its steps, and
    was asked once per proven workflow to arrive at two integers: flatly
    linear in total run rows, measured at 0.391s for 10k against these fakes,
    on the read every browser makes on every gesture cache miss.
    """
    uow = FakeUnitOfWork()
    by_id = _evidence()
    # Planted against their own ids, as the sibling above: three proven
    # workflows is what makes "once" tell a batch from a loop.
    await _plant(
        uow,
        by_id,
        _workflow(by_id, "wfl_3"),
        _workflow(by_id, "wfl_1"),
        _workflow(by_id, "wfl_2"),
    )
    await _run(uow, "run_1", "wfl_1", "held")
    await _run(uow, "run_2", "wfl_2", "held")
    tallies, loads = 0, 0
    counting, loading = uow.workflow_runs.tallies, uow.workflow_runs.for_workflow

    async def counted(tenant_id: TenantId) -> Mapping[str, tuple[int, int]]:
        nonlocal tallies
        tallies += 1
        return await counting(tenant_id)

    async def loaded(tenant_id: TenantId, workflow_id: str) -> tuple[WorkflowRun, ...]:
        nonlocal loads
        loads += 1
        return await loading(tenant_id, workflow_id)

    monkeypatch.setattr(uow.workflow_runs, "tallies", counted)
    monkeypatch.setattr(uow.workflow_runs, "for_workflow", loaded)

    served = await shapes_for(uow, tenant_id=TENANT, now=NOW)

    assert sorted(shape.id for shape in served) == ["wfl_1", "wfl_2", "wfl_3"]
    assert tallies == 1, "one tally for the tenant, not one per workflow"
    assert loads == 0, "no run is loaded with its steps to be counted"


async def test_a_workflow_with_no_cites_is_never_asked_for_its_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`gestures_for` with no ids is `IN ()` -- a round trip to Postgres that
    nothing can come back from, asked once per cite-less workflow by every
    browser on every cache miss. The guard that skips it is not a null check:
    `shape_of` makes one of those anyway, one statement later."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    nothing = Workflow(id="wfl_0", tenant=TENANT.value, title="cites nothing", narrative="n")
    await _plant(uow, by_id, nothing)
    reads = 0
    asked = uow.gestures.gestures_for

    async def counted(*args: object, **kwargs: object) -> tuple[Gesture, ...]:
        nonlocal reads
        reads += 1
        return await asked(*args, **kwargs)

    monkeypatch.setattr(uow.gestures, "gestures_for", counted)

    assert await shapes_for(uow, tenant_id=TENANT, now=NOW) == []
    assert reads == 0


# --------------------------------------------------------------------------
# this job's own counsel


async def test_a_resting_job_is_served_marked_for_the_browser_that_refused_it() -> None:
    """The shape half of this is in the domain suite; what is here is the
    query behind it -- that the browser asking is the browser counsel is asked
    about, and that the clock it is asked with is the caller's."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    await _plant(uow, by_id, _workflow(by_id))
    await _offers(uow, "wfl_1", "dismissed", k=2, times=3, device=DEVICE)

    [for_refuser] = await shapes_for(uow, tenant_id=TENANT, device_id=DEVICE, now=NOW)
    [for_other] = await shapes_for(uow, tenant_id=TENANT, device_id=SECOND, now=NOW)
    [for_nobody] = await shapes_for(uow, tenant_id=TENANT, now=NOW)

    assert for_refuser.quiet_until is not None, "still served, marked"
    assert for_other.quiet_until is None and for_nobody.quiet_until is None
    assert for_refuser.as_json()["quiet_until"] == for_refuser.quiet_until


async def test_a_job_rests_only_until_the_caller_s_own_clock_says_it_may_be_offered() -> None:
    """The same three refusals, read a day later. A `shapes_for` that reads
    the wall clock instead of its `now` cannot tell these two calls apart."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    await _plant(uow, by_id, _workflow(by_id))
    await _offers(uow, "wfl_1", "dismissed", k=2, times=3, device=DEVICE)

    [tomorrow] = await shapes_for(
        uow, tenant_id=TENANT, device_id=DEVICE, now=NOW + timedelta(days=2)
    )

    assert tomorrow.quiet_until is None, "the rest is a day, and the day is over"


async def test_the_offers_that_move_one_job_s_threshold_leave_the_others_alone() -> None:
    """`offer_after` comes off this job's own offers. Read per tenant instead
    of per workflow, a job nobody has ever diverged on would be pushed past
    the k it is recognised at and never offered."""
    uow = FakeUnitOfWork()
    by_id = _evidence()
    await _plant(uow, by_id, _workflow(by_id), _four_gestures(by_id, "wfl_4"))
    await _offers(uow, "wfl_4", "diverged", k=5, times=3)

    served = {shape.id: shape for shape in await shapes_for(uow, tenant_id=TENANT, now=NOW)}

    assert len(served["wfl_4"].shape) == 4
    assert served["wfl_4"].offer_after == 3, "past where it diverged, capped at the last but one"
    assert served["wfl_1"].offer_after == K_OFFER_AFTER, "nobody has diverged on this one"
