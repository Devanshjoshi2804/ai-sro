"""A value one system answers and another is sent, in that system's own format.

The diff recognised a data dependency by exact equality, so a value handed over
unchanged was bound to the step that produced it and a value *reformatted* on
the way was not. `42` answered by the WMS and `LPN-00042` sent to the ERP looked
like a value nobody could account for: it became a question for an operator who
does not know where the number comes from either, and a skill that asks for
something the previous step already knew is a skill nobody runs twice.

That is the ordinary shape of work crossing two systems -- which is to say, the
shape of every workflow taught by `TeachWorkflow`. See
docs/16-what-others-have-solved.md.
"""

from __future__ import annotations

import json

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteStep, ExecutionRequest, StartRun
from sro.application.induction.diff import parameterise
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import Template
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.transform import Transform
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

CLOSE = "https://wms.test/api/waves/close"
RECEIPT = "https://erp.test/api/receipts"


def _close(index: int, wave: str) -> ActionFrame:
    """The WMS half: closing the wave, which answers with the wave's own id."""
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Close")),
        requests=(
            f.request(
                method="POST",
                url=CLOSE,
                status=200,
                request_body=Body(text=json.dumps({"data": {"site": "DC01"}})),
                response_body=Body(text=json.dumps({"data": {"waveId": wave}})),
            ),
        ),
    )


def _record(index: int, reference: str) -> ActionFrame:
    """The ERP half: the same wave, written the way the ERP writes references."""
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="POST",
                url=RECEIPT,
                status=201,
                request_body=Body(text=json.dumps({"data": {"reference": reference}})),
            ),
        ),
    )


def test_a_reformatted_id_is_bound_to_the_step_that_produced_it() -> None:
    result = parameterise(
        (_close(0, "42"), _record(1, "LPN-00042")),
        (_close(0, "77"), _record(1, "LPN-00077")),
    )

    derived = [p for p in result.parameters if p.kind is ParameterKind.DERIVED]
    assert len(derived) == 1, "the reference is still a question for an operator"
    assert (derived[0].source_step_index, derived[0].source_pointer) == (0, "/data/waveId")
    assert derived[0].transform is not None
    assert derived[0].transform.apply("77") == "LPN-00077"

    # Nothing is left for a person to supply: both halves of the job are known
    # once the wave is closed.
    assert [p.name for p in result.parameters if p.kind is ParameterKind.INPUT] == []


def test_the_reviewer_is_told_what_was_done_to_it() -> None:
    """A description reading "produced by step 0" reads as verbatim. Somebody
    approving a write into a second system has to be able to disagree with the
    reformatting by eye."""
    result = parameterise(
        (_close(0, "42"), _record(1, "LPN-00042")),
        (_close(0, "77"), _record(1, "LPN-00077")),
    )

    derived = next(p for p in result.parameters if p.kind is ParameterKind.DERIVED)
    assert "padded to 5 with '0'" in derived.description
    assert "prefixed with 'LPN-'" in derived.description


def test_a_rewriting_that_explains_only_one_run_is_refused() -> None:
    """The rule that keeps this evidence rather than pattern-matching.

    The second run's reference has nothing to do with its wave. A rule read off
    the first pair alone would fit -- rules always fit one pair -- and would
    send `LPN-00077` where the operator sent something else entirely.
    """
    result = parameterise(
        (_close(0, "42"), _record(1, "LPN-00042")),
        (_close(0, "77"), _record(1, "LPN-99999")),
    )

    assert [p.kind for p in result.parameters] == [ParameterKind.INPUT] * len(result.parameters)
    assert any(p.kind is ParameterKind.INPUT for p in result.parameters)


def test_a_value_handed_over_unchanged_is_still_read_as_unchanged() -> None:
    """Verbatim first, always: a value that was copied must not acquire a story
    about padding that happens to fit."""
    result = parameterise(
        (_close(0, "42"), _record(1, "42")),
        (_close(0, "77"), _record(1, "77")),
    )

    derived = next(p for p in result.parameters if p.kind is ParameterKind.DERIVED)
    assert derived.transform is None


def test_where_two_steps_could_explain_it_the_one_that_says_it_outright_wins() -> None:
    """Both explanations fit and only one is true.

    The wave is closed, a label is printed and answers with the reference in the
    ERP's own format, and the receipt sends that reference. Step 0 could explain
    it too -- pad the wave id and prefix it -- and would keep working right up
    until the day the ERP changes how it writes a reference, at which point a
    skill that was *reading* the reference all along starts inventing one.
    """

    def _label(index: int, reference: str) -> ActionFrame:
        return f.frame(
            index=index,
            action=InputAction(
                kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Print")
            ),
            requests=(
                f.request(
                    method="POST",
                    url="https://wms.test/api/labels",
                    status=200,
                    response_body=Body(text=json.dumps({"data": {"reference": reference}})),
                ),
            ),
        )

    result = parameterise(
        (_close(0, "42"), _label(1, "LPN-00042"), _record(2, "LPN-00042")),
        (_close(0, "77"), _label(1, "LPN-00077"), _record(2, "LPN-00077")),
    )

    derived = next(p for p in result.parameters if p.kind is ParameterKind.DERIVED)
    assert (derived.source_step_index, derived.source_pointer) == (1, "/data/reference")
    assert derived.transform is None


async def test_the_run_sends_the_value_in_the_format_the_second_system_wants() -> None:
    """The other half of it. A transformation discovered and then not applied
    would send `42` where the ERP was demonstrated to want `LPN-00042` -- a
    write rejected, or worse accepted against whatever record `42` names there.
    """
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    version = f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(
                    method="POST", url=Template(CLOSE), body=Template("{}")
                ),
            ),
            f.step(
                index=1,
                network_plan=f.network_plan(
                    method="POST",
                    url=Template(RECEIPT),
                    body=Template('{"reference": "${wave_id}"}'),
                ),
            ),
        ),
        parameters=(
            Parameter(
                name="wave_id",
                kind=ParameterKind.DERIVED,
                source_step_index=0,
                source_pointer="/data/waveId",
                transform=Transform(ops=(("pad", "5", "0"), ("prefix", "LPN-"))),
            ),
        ),
    )
    skill = f.skill(versions=0)
    skill.add_version(version)
    for stage in (PromotionStage.SHADOW, PromotionStage.ASSISTED):
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    http.answer(status_code=200, text=json.dumps({"data": {"waveId": "77"}}))
    http.answer(status_code=201, text="{}")

    run = await StartRun(uow, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(skill_id=skill.id, parameters={}, authorized_by="supervisor"),
    )
    step = ExecuteStep(uow, http, vault, servers={})
    await step.execute(CTX, run_id=run.id, index=0)
    await step.execute(CTX, run_id=run.id, index=1)

    assert json.loads(http.sent[1]["body"]) == {"reference": "LPN-00077"}
