"""Running "adjust every short-shipped line on this order".

The count is the system's own answer, arriving partway through the run: the
order is opened, the WMS says which lines are short, and the body is performed
once for each. Nothing about how many is decided before that answer, and
nothing about it is decided twice -- what the run started with is what it
finishes with, which is what makes a run that resumes after a restart the same
run rather than a different task with the same id.
"""

from __future__ import annotations

import json

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import (
    ExecuteSkill,
    ExecutionRequest,
    NotRunnable,
    StartRun,
)
from sro.domain.execution.run import Medium, RunStatus, StepDisposition
from sro.domain.execution.safety import MAX_ITEMS_PER_BATCH
from sro.domain.skill.loop import Binding, Loop
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import Template
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _skill(uow: FakeUnitOfWork) -> None:
    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(
                    method="GET", url=Template("https://wms.test/api/orders/55"), body=None
                ),
            ),
            f.step(
                index=1,
                network_plan=f.network_plan(
                    method="POST",
                    url=Template("https://wms.test/api/lines/${line_id}/adjust"),
                    body=Template('{"lineId": "${line_id}"}'),
                ),
            ),
        ),
        parameters=(
            Parameter(
                name="line_id",
                kind=ParameterKind.ITERATED,
                source_step_index=0,
                source_pointer="/lineId",
            ),
        ),
        loops=(
            Loop(
                over_step_index=0,
                over_pointer="/data/lines",
                first_step=1,
                last_step=1,
                binds=(Binding(parameter="line_id", pointer="/lineId"),),
            ),
        ),
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)


def _lines(*ids: str) -> str:
    return json.dumps({"data": {"lines": [{"lineId": line, "short": True} for line in ids]}})


async def _run(uow: FakeUnitOfWork, http: FakeHttpCaller) -> object:
    return await ExecuteSkill(
        uow, http, FakeCredentialVault(), FakeClock(), FakeIdFactory(), servers={}
    ).execute(
        CTX,
        ExecutionRequest(skill_id=f.skill().id, parameters={}, authorized_by="supervisor"),
    )


async def test_the_body_is_performed_once_for_each_thing_the_system_listed() -> None:
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    http.answer(status_code=200, text=_lines("7", "8", "9"))
    for _ in range(3):
        http.answer(status_code=200, text="{}")

    run = await _run(uow, http)

    assert [call["url"] for call in http.sent[1:]] == [
        "https://wms.test/api/lines/7/adjust",
        "https://wms.test/api/lines/8/adjust",
        "https://wms.test/api/lines/9/adjust",
    ]
    assert [json.loads(call["body"])["lineId"] for call in http.sent[1:]] == ["7", "8", "9"]
    assert run.status is RunStatus.SUCCEEDED

    # The run says which step of the plan each position was, and which time
    # round: "four steps" would be a log nobody can read against a two-step
    # skill.
    steps = run.steps
    assert [(s.index, s.step_index, s.iteration) for s in steps] == [
        (0, 0, 0),
        (1, 1, 0),
        (2, 1, 1),
        (3, 1, 2),
    ]


async def test_an_order_with_nothing_short_does_nothing_and_succeeds() -> None:
    """Not a failure, and not one adjust with no line to adjust: the task was
    to fix what is short, and nothing was."""
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    http.answer(status_code=200, text=_lines())

    run = await _run(uow, http)

    assert len(http.sent) == 1
    assert run.status is RunStatus.SUCCEEDED


async def test_a_list_longer_than_a_person_would_approve_stops_before_the_first_write() -> None:
    """A loop is unbounded writes, which is what the blast radius exists for.
    Refused before the body starts rather than discovered halfway through with
    fifty adjustments already sent -- and by the same limit a batch of the same
    size would meet, because it is the same question.
    """
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    http.answer(status_code=200, text=_lines(*[str(n) for n in range(MAX_ITEMS_PER_BATCH + 1)]))

    run = await _run(uow, http)

    assert len(http.sent) == 1, "nothing was adjusted"
    assert run.status is RunStatus.FAILED
    detail = run.steps[0].detail or ""
    assert f"more than {MAX_ITEMS_PER_BATCH} in one run is a decision for a person" in detail


async def test_an_answer_without_the_list_fails_the_step_that_should_have_carried_it() -> None:
    """The system changed under the skill. Nothing is done a guessed number of
    times; the step says what it could not read."""
    uow, http = FakeUnitOfWork(), FakeHttpCaller()
    await _skill(uow)
    http.answer(status_code=200, text=json.dumps({"data": {"order": "55"}}))

    run = await _run(uow, http)

    assert len(http.sent) == 1
    assert run.steps[0].disposition is StepDisposition.FAILED
    assert "no /data/lines to act on" in (run.steps[0].detail or "")


async def test_a_looping_skill_is_refused_at_the_rungs_that_cannot_read_a_list() -> None:
    """L2 clicks and L3 looks; neither reads a response, so neither can know
    how many things there are. Refused, rather than performed once."""
    uow = FakeUnitOfWork()
    await _skill(uow)

    with pytest.raises(NotRunnable, match="only the network rung can read"):
        await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
            CTX,
            ExecutionRequest(
                skill_id=f.skill().id,
                parameters={},
                authorized_by="supervisor",
                medium=Medium.UI,
            ),
        )
