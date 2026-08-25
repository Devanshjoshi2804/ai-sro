"""Inducing "adjust every short-shipped line on this order".

The task the system could not express. A skill is a flat list of steps, so two
honest demonstrations -- an order with two short lines, an order with three --
disagreed about how many steps the task has, and the pair was refused with a
sentence that was certainly wrong: *the runs are not two runs of one task*.

What comes out now is one skill whose body is done once per line the system
itself says is short, and the line id is a parameter nobody is ever asked for.
"""

from __future__ import annotations

import json

import pytest

from sro.application.context import RequestContext
from sro.application.induction.errors import InductionFailed
from sro.application.induction.induce_skill import InduceSkill
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.recording.events import ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.shared.identifiers import RecordingId
from sro.domain.skill.parameter import ParameterKind
from sro.domain.skill.skill import SkillVersion
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)
ORDER = "https://wms.test/api/orders/55"


def _open(lines: list[str]) -> object:
    return f.frame(
        index=0,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Open")),
        requests=(
            f.request(
                method="GET",
                url=ORDER,
                status=200,
                response_body=Body(
                    text=json.dumps(
                        {"data": {"lines": [{"lineId": line, "short": True} for line in lines]}}
                    )
                ),
            ),
        ),
    )


def _adjust(index: int, line: str) -> object:
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Adjust")),
        requests=(
            f.request(
                method="POST",
                url=f"https://wms.test/api/lines/{line}/adjust",
                status=200,
                request_body=Body(text=json.dumps({"lineId": line, "reason": "SHORT"})),
            ),
        ),
    )


async def _induce(first: list[str], second: list[str]) -> SkillVersion:
    uow = FakeUnitOfWork()
    for ident, lines in (("rec-a", first), ("rec-b", second)):
        recording = f.recording(frames=0, id=RecordingId(ident))
        recording.append_frame(_open(lines))
        for index, line in enumerate(lines):
            recording.append_frame(_adjust(index + 1, line))
        recording.seal(f.at(300))
        await uow.recordings.add(recording)

    await InduceSkill(
        uow,
        FakeClock(),
        FakeIdFactory(),
        AskAbout(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())),
    ).execute(CTX, first=RecordingId("rec-a"), second=RecordingId("rec-b"))

    skill = next(iter(uow.skills.rows.values()))
    return skill.versions[-1]


async def test_two_lengths_of_one_task_induce_as_a_loop() -> None:
    version = await _induce(["1", "2"], ["7", "8", "9"])

    # One iteration of the body is what the skill keeps: the rest were the same
    # block again, and reading them is what the loop is.
    assert len(version.steps) == 2
    loop = version.loops[0]
    assert (loop.first_step, loop.last_step) == (1, 1)
    assert loop.describe() == "once for each lines step 0 found"


async def test_the_line_it_acts_on_is_never_asked_of_an_operator() -> None:
    version = await _induce(["1", "2"], ["7", "8", "9"])

    iterated = [p for p in version.parameters if p.kind is ParameterKind.ITERATED]
    assert [p.name for p in iterated] == ["line_id"]
    assert version.inputs == (), "the system already said which lines are short"

    # And the body sends it, in both the places the demonstration sent it.
    plan = version.steps[1].network_plan
    assert plan is not None
    assert plan.url.raw == "https://wms.test/api/lines/${line_id}/adjust"
    assert plan.body is not None
    assert json.loads(plan.body.raw)["lineId"] == "${line_id}"
    # What did not vary between iterations stays exactly as demonstrated.
    assert json.loads(plan.body.raw)["reason"] == "SHORT"


async def test_a_pair_that_is_not_a_loop_is_refused_exactly_as_before() -> None:
    """The refusal this replaces is still the right answer nearly always: two
    runs that did different work are not two runs of one task, and reading a
    loop into them would be the worst kind of wrong."""
    uow = FakeUnitOfWork()
    for ident, lines in (("rec-a", ["1", "2"]), ("rec-b", ["7", "8", "9"])):
        recording = f.recording(frames=0, id=RecordingId(ident))
        recording.append_frame(_open(lines))
        for index, line in enumerate(lines):
            recording.append_frame(_adjust(index + 1, line))
        if ident == "rec-b":
            # And then did something else entirely, once.
            recording.append_frame(
                f.frame(
                    index=4,
                    action=InputAction(
                        kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Close order")
                    ),
                    requests=(f.request(method="POST", url=f"{ORDER}/close", status=200),),
                )
            )
        recording.seal(f.at(300))
        await uow.recordings.add(recording)

    with pytest.raises(InductionFailed, match="not two runs of one task"):
        await InduceSkill(
            uow,
            FakeClock(),
            FakeIdFactory(),
            AskAbout(uow, RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder())),
        ).execute(CTX, first=RecordingId("rec-a"), second=RecordingId("rec-b"))
