"""A step performed through a connector, and why it is allowed to be clean.

A gesture step can never reach `CLEAN`, so a skill whose mail half is clicks
stays assisted forever -- not as a policy but by construction. A tool call is
the only kind of step the ladder can promote, which is the whole reason this
exists.

What it is not is a demonstration. Nobody watched `send_message` work, so a
tool step's post-conditions are somebody's writing rather than two runs
agreeing. That is not special-cased here: it is answered by the rule every
other step meets -- a write with no assertion makes the version unverifiable,
and an unverifiable version never reaches the top of the ladder.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.application.ports.tools import ToolResult
from sro.domain.execution.escalation import FailureKind, next_medium
from sro.domain.execution.run import Medium, StepDisposition
from sro.domain.execution.verdict import Verdict, judge
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.plan import ToolPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillStep
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeToolCaller,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
SENT = ToolResult(text='{"id": "msg-1", "status": "sent"}')
SUPPLIER = f.parameter(name="supplier", observed_values=("a@b.test", "c@d.test"))
CHECKED = (
    Assertion(
        kind=AssertionKind.RESPONSE_FIELD_EQUALS,
        expected=Template("sent"),
        pointer="/status",
    ),
)


def _step(*, writes: bool = True, asserts: bool = True) -> SkillStep:
    return SkillStep(
        index=0,
        intent="reply to the supplier",
        tool_plan=ToolPlan(
            server="mail",
            tool="send_message",
            arguments=(("to", Template("${supplier}")), ("body", Template("acknowledged"))),
            writes=writes,
        ),
        assertions=CHECKED if asserts else (),
    )


async def _run(
    tools: FakeToolCaller,
    *,
    step: SkillStep | None = None,
    uow: FakeUnitOfWork | None = None,
    parameters: dict[str, str] | None = None,
) -> tuple[FakeUnitOfWork, object]:
    uow = uow or FakeUnitOfWork()
    version = f.skill_version(steps=(step or _step(),), parameters=(SUPPLIER,))
    skill = f.skill(versions=0)
    skill.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(700), f.OPERATOR)
    version.promote(PromotionStage.ASSISTED, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    await ExecuteSkill(
        uow,
        FakeHttpCaller(),
        FakeCredentialVault(),
        FakeClock(),
        FakeIdFactory(),
        tools=tools,
    ).execute(
        CTX,
        ExecutionRequest(
            skill_id=skill.id,
            parameters=parameters or {"supplier": "dispatch@supplier.test"},
            authorized_by="supervisor",
        ),
    )
    return uow, next(iter(uow.runs.rows.values()))


async def test_a_step_mapped_onto_a_connector_is_performed_by_calling_it() -> None:
    tools = FakeToolCaller({"send_message": SENT})

    _, run = await _run(tools)

    assert tools.calls == [
        ("mail", "send_message", {"to": "dispatch@supplier.test", "body": "acknowledged"})
    ]
    outcome = run.steps[0]  # type: ignore[attr-defined]
    assert outcome.medium is Medium.TOOL
    assert outcome.disposition is StepDisposition.PERFORMED
    assert outcome.assertion_failures == ()


async def test_a_run_of_calls_is_clean_and_can_therefore_earn_its_way_up() -> None:
    """The point of the whole thing. A gesture makes a run degraded, a degraded
    run resets the streak, and a skill that cannot hold a streak can never be
    promoted -- so a mail half taught by clicking is assisted forever."""
    tools = FakeToolCaller({"send_message": SENT})

    _, run = await _run(tools)

    assert judge(run) is Verdict.CLEAN  # type: ignore[arg-type]


async def test_a_tool_that_says_no_is_an_answer_and_not_a_crash() -> None:
    tools = FakeToolCaller({"send_message": ToolResult(text="", failed=True, detail="no mailbox")})

    _, run = await _run(tools)

    assert run.steps[0].disposition is StepDisposition.FAILED  # type: ignore[attr-defined]
    assert "no mailbox" in run.steps[0].detail  # type: ignore[attr-defined]


async def test_a_deployment_with_no_connector_says_so_rather_than_failing_the_skill() -> None:
    """Not a claim about the skill, so the run is not held against it -- the
    same rule a WMS that was not there gets."""
    _, run = await _run(FakeToolCaller(available=False))

    outcome = run.steps[0]  # type: ignore[attr-defined]
    assert outcome.disposition is StepDisposition.FAILED
    assert outcome.unreachable is True


async def test_a_write_is_not_sent_twice_even_across_two_runs() -> None:
    """A network write is protected within its run: an answered POST is never
    retried. Nothing protected a connector call across runs -- the same trigger
    firing twice, a workflow replayed after a crash, an operator pressing the
    button again because the first press seemed to hang. For a mail that is one
    message becoming two, and there is no taking it back.
    """
    tools = FakeToolCaller({"send_message": SENT})
    uow = FakeUnitOfWork()

    await _run(tools, uow=uow)
    # The same run id, because `FakeIdFactory` counts from zero each time --
    # which is exactly the replayed run this guards against.
    await _run(tools, uow=uow)

    assert len(tools.calls) == 1
    refused = [
        run for run in uow.runs.rows.values() if run.steps[0].disposition is StepDisposition.FAILED
    ]
    assert "may have landed" in refused[0].steps[0].detail


async def test_a_read_through_a_connector_is_not_claimed_at_all() -> None:
    """Only a write is worth refusing twice. A lookup that cannot be repeated
    is a lookup that fails the second time somebody asks the same question."""
    tools = FakeToolCaller({"send_message": SENT})
    uow = FakeUnitOfWork()
    reading = _step(writes=False)

    await _run(tools, step=reading, uow=uow)
    await _run(tools, step=reading, uow=uow)

    assert len(tools.calls) == 2
    assert uow.tool_calls.claimed == {}


def test_a_tool_step_that_writes_and_checks_nothing_blocks_autonomy() -> None:
    """No special case for tool steps. Nobody demonstrated this call, so its
    assertions are somebody's writing -- and a write with no assertion has
    always made a version unverifiable."""
    version = f.skill_version(steps=(_step(asserts=False),), parameters=(SUPPLIER,))

    assert version.changes_the_system is True
    assert version.unchecked_writes == (0,)
    assert version.verifiable is False


def test_a_skill_of_tool_steps_does_not_need_a_person() -> None:
    """`needs_a_person` reads "no network plan" as "performed by clicking".
    A tool step has no network plan either and is not a click."""
    version = f.skill_version(steps=(_step(),), parameters=(SUPPLIER,))

    assert version.needs_a_person is False


@pytest.mark.parametrize(
    "failure",
    [
        FailureKind.TOOL_UNAVAILABLE,
        FailureKind.STATUS_MISMATCH,
        FailureKind.ASSERTION_FAILED,
        FailureKind.UNREACHABLE,
        FailureKind.CREDENTIAL_MISSING,
    ],
)
def test_a_failed_tool_call_never_falls_back_to_clicking(failure: FailureKind) -> None:
    """The gesture this step replaced was mapped away on purpose. Falling back
    to it would perform by clicking a step somebody decided should be a call --
    and for the refusals, would do again what the connector just refused."""
    rule = next_medium(failure, Medium.TOOL)

    assert rule is not None, f"{failure} at the tool rung has no decided answer"
    assert rule.then is None
