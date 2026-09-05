"""A workflow the rig mined, adopted into the skill library.

The seam where a person joins in: the rig knows a title, the systems a job
touched and a shape key, and a `Skill` needs an `ObjectiveKey`. Naming what a
job is FOR is not derivable from the evidence, so somebody does it -- and the
two contributions have to stay distinguishable afterwards.
"""

import pytest

from sro.application.context import RequestContext
from sro.application.skill.adopt_rig_workflow import RIG, AdoptRigWorkflow
from sro.domain.shared.errors import DomainError
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

EXTJS = {
    "role": "textbox",
    "name": "Activity Code",
    "cssPath": "div#x > input",
    "component": {"xtype": "textfield", "itemId": "activityCode", "query": "#activityCode"},
}
WORKFLOW = {
    "title": "Create a work activity",
    "narrative": "the operator created a work activity",
    "systems": ["wms.example"],
    "steps": [{"order": 0, "says": "Type the code, then save.", "cites": ["a", "b"]}],
    "parameters": [{"name": "activityCode", "seen_values": ["TEST1", "TEST2"]}],
}
GESTURES = {
    "a": {"kind": "type", "value": "TEST1", "url": "https://wms.example/x", "target": EXTJS},
    "b": {"kind": "click", "url": "https://wms.example/x", "target": EXTJS},
}
REQUESTS = {
    "a": [
        {
            "request_id": "req_1",
            "method": "POST",
            "url": "https://wms.example/data/WM/wm/activities",
            "resource_type": "xhr",
            "started_at": "2026-09-05T10:00:00.000Z",
            "request_headers": {"authorization": "«redacted»"},
            "request_body": {"text": '{"activityCode":"TEST1"}'},
            "status": 201,
        }
    ]
}


def _adopt(uow: FakeUnitOfWork) -> AdoptRigWorkflow:
    return AdoptRigWorkflow(uow, FakeClock(f.T0), FakeIdFactory())


async def test_a_mined_workflow_becomes_a_skill_under_a_name_a_person_chose() -> None:
    uow = FakeUnitOfWork()

    adopted = await _adopt(uow).execute(
        CTX,
        workflow=WORKFLOW,
        gestures=GESTURES,
        recordings=["str_1"],
        objective=f.objective(),
    )

    assert adopted.created_the_skill
    stored = await uow.skills.get(f.TENANT, adopted.skill_id)
    assert stored.objective_key == f.objective()
    assert stored.latest.version == 1
    assert [step.intent for step in stored.latest.steps] == ["Type the code, then save."] * 2


async def test_the_rig_wrote_the_steps_and_a_person_named_the_job() -> None:
    """`Provenance.induced_by` says who PRODUCED the version, and its own
    docstring puts `drift-repair` there where the system did the work and "does
    not pretend to be" a person. A model reading 170 hours of capture is the
    same kind of author. What the person contributed -- the objective -- is the
    one part of this version nobody derived from evidence, so it is recorded
    where a reviewer reads it rather than left implicit."""
    uow = FakeUnitOfWork()

    adopted = await _adopt(uow).execute(
        CTX,
        workflow=WORKFLOW,
        gestures=GESTURES,
        recordings=["str_1"],
        objective=f.objective(),
    )

    provenance = adopted.version.provenance
    assert provenance.induced_by == RIG, "not the person who pressed adopt"
    assert str(f.OPERATOR) in provenance.note
    assert f.objective().slug() in provenance.note
    assert "the operator created a work activity" in provenance.note, "and the rig's own words"


async def test_nothing_arrives_promoted() -> None:
    """The objective is a person's reading of a title and the steps are a
    model's reading of a day. Neither has been checked against the other."""
    uow = FakeUnitOfWork()

    adopted = await _adopt(uow).execute(
        CTX,
        workflow=WORKFLOW,
        gestures=GESTURES,
        recordings=["str_1"],
        objective=f.objective(),
    )

    assert adopted.version.stage is PromotionStage.RECORDED
    stored = await uow.skills.get(f.TENANT, adopted.skill_id)
    assert stored.runnable is None, "and the runner refuses it until somebody looks"


async def test_the_rig_watching_the_same_job_twice_is_a_second_version() -> None:
    """Evidence, not a duplicate. Existing versions are what runs are judged
    against, so a second reading appends rather than replaces."""
    uow = FakeUnitOfWork()
    adopt = _adopt(uow)

    first = await adopt.execute(
        CTX, workflow=WORKFLOW, gestures=GESTURES, recordings=["str_1"], objective=f.objective()
    )
    second = await adopt.execute(
        CTX, workflow=WORKFLOW, gestures=GESTURES, recordings=["str_2"], objective=f.objective()
    )

    assert second.skill_id == first.skill_id
    assert second.created_the_skill is False
    stored = await uow.skills.get(f.TENANT, first.skill_id)
    assert [v.version for v in stored.versions] == [1, 2]


async def test_the_facility_comes_from_the_objective_and_not_from_a_second_argument() -> None:
    """A credential reference is a vault key scoped per system and facility,
    and the objective is the only place this system records which facility a
    job belongs to. Two arguments could disagree, and then a Bengaluru job's
    credentials are filed under Singapore."""
    uow = FakeUnitOfWork()

    adopted = await _adopt(uow).execute(
        CTX,
        workflow=WORKFLOW,
        gestures=GESTURES,
        recordings=["str_1"],
        objective=f.objective(facility="BLR1"),
        requests=REQUESTS,
    )

    call = next(s.network_plan for s in adopted.version.steps if s.network_plan)
    assert [h.credential_ref for h in call.headers if h.credential_ref] == [
        "wms.example/BLR1/authorization"
    ]


async def test_a_workflow_with_nothing_runnable_in_it_is_refused_and_stores_nothing() -> None:
    """A skill with no version is a skill nobody can look at, and an empty one
    would sit in the library looking adoptable."""
    uow = FakeUnitOfWork()

    with pytest.raises(DomainError):
        await _adopt(uow).execute(
            CTX, workflow=WORKFLOW, gestures={}, recordings=["str_1"], objective=f.objective()
        )

    assert await uow.skills.find_by_objective(f.TENANT, f.objective()) is None


async def test_a_workflow_with_no_recording_behind_it_is_refused() -> None:
    """`Provenance` requires one, and minting an id from something to hand
    would lie to `from_one_demonstration` -- which decides whether a write
    skill's values were ever diffed."""
    uow = FakeUnitOfWork()

    with pytest.raises(DomainError):
        await _adopt(uow).execute(
            CTX, workflow=WORKFLOW, gestures=GESTURES, recordings=[], objective=f.objective()
        )
