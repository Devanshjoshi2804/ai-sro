"""One task, done four different ways, is still one task.

An operator added four carrier cross references in a real WMS. Sometimes they
filled every field, sometimes a few; one doing included a whole address lookup
the others skipped. Induction aligned two of the four and produced a skill with
two steps -- both the same button -- while correctly deriving four parameters
from all four. It named `cod_address_id` and had no step that could fill it.

The variation is the work, not noise in it. What separates a step of the task
from a fumble is how often it appears, not whether two particular doings
happened to share it.
"""

from __future__ import annotations

import json
import logging

import pytest

from sro.application.context import RequestContext
from sro.application.induction.diff import (
    Parameterisation,
    Substitution,
    _longest_common,
    align_all,
)
from sro.application.induction.errors import InductionFailed
from sro.application.induction.induce_skill import InduceSkill, _at_reference
from sro.application.induction.sites import ActionValueSite
from sro.application.knowledge.open_questions import AskAbout
from sro.application.knowledge.record_claim import RecordClaims
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.shared.identifiers import RecordingId
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.skill import SkillVersion
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


def _click(control: str) -> InputAction:
    """A press on a named control, carrying no value and no request of its
    own -- an operator finding their way, not evidence of anything. `f.frame`
    would otherwise hand every step the same default request, which would
    make `_same` pair unrelated controls on their shared URL rather than on
    the control they actually touched."""
    return InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name=control))


def _run(*controls: str) -> tuple[ActionFrame, ...]:
    """A doing, as the sequence of controls it touched."""
    return tuple(
        f.frame(index, action=_click(control), requests=())
        for index, control in enumerate(controls)
    )


def _typed(index: int, control: str, value: str) -> ActionFrame:
    """A step that entered something -- the address lookup one doing made
    that the others skipped. A plain click carries no evidence of itself by
    design; this one does, the way the real gesture did, so it is the one
    `align_all` must refuse to drop."""
    action = InputAction(
        kind=ActionKind.TYPE, target=f.fingerprint(accessible_name=control), value=value
    )
    return f.frame(index, action=action, requests=())


def _control_of(frame: ActionFrame) -> str | None:
    """The control a step's action named -- what a test asserts against,
    rather than diff.py's own internal identity string."""
    target = frame.action.target
    return target.accessible_name if target else None


def test_a_step_every_doing_made_is_seen_by_all_of_them() -> None:
    found = align_all(
        [
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
        ]
    )

    assert [_control_of(frame) for frame in found.reference] == ["Add", "Carrier", "Save"]
    assert set(found.seen.values()) == {3}


def test_a_step_only_one_doing_made_is_counted_once_not_dropped() -> None:
    """The whole defect in one assertion. Today the address lookup vanishes
    because two of four doings did not contain it; here it survives with its
    count, and a later task decides what that count means."""
    lookup_run = (
        *_run("Add", "Carrier"),
        _typed(2, "COD Address", "123 Main St"),
        f.frame(3, action=_click("Save"), requests=()),
    )
    found = align_all(
        [
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
            lookup_run,
        ]
    )

    controls = [_control_of(frame) for frame in found.reference]
    assert "COD Address" in controls, controls
    assert found.seen[controls.index("COD Address")] == 1
    assert found.seen[controls.index("Add")] == 3


def test_the_reference_is_the_doing_others_agree_with_most() -> None:
    """Not the longest, and not the most recent. The longest may be the one
    where somebody wandered; the most recent is an accident of ordering."""
    found = align_all(
        [
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
            _run("OK", "Add", "Wander", "Carrier", "Save"),
        ]
    )

    assert [_control_of(frame) for frame in found.reference][:3] == ["Add", "Carrier", "Save"]


def test_agreement_decides_it_even_when_the_winner_is_neither_first_nor_longest() -> None:
    """The test above ties every run on raw agreement, so it is entirely
    decided by the length tie-break -- a `_pick_reference` that ignored
    agreement and always returned the first run would pass it too, because
    the first run there already is the right answer. Here the winner is
    third in the list and shorter than a decoy that opens it, so only real
    agreement -- not position, not length -- explains the result."""
    first_but_unrelated = _run("Alpha", "Beta", "Gamma")
    longest_but_unrelated = _run("Zulu", "Yankee", "Xray", "Whiskey", "Victor")
    found = align_all(
        [
            first_but_unrelated,
            longest_but_unrelated,
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
        ]
    )

    assert [_control_of(frame) for frame in found.reference] == ["Add", "Carrier", "Save"]


def test_one_doing_alone_is_still_an_alignment() -> None:
    """A task demonstrated once has nothing to disagree with it. Every step is
    seen by everything there is."""
    found = align_all([_run("Add", "Save")])

    assert len(found.reference) == 2
    assert set(found.seen.values()) == {1}


def test_nothing_at_all_refuses_rather_than_returning_an_empty_task() -> None:
    from pytest import raises

    from sro.application.induction.errors import InductionFailed

    with raises(InductionFailed):
        align_all([])


# --- The whole way through: four doings become one skill ----------------------
#
# Above is the counting on its own. This is the induction that reads it, in the
# shape the real failure had: the pair proves the parameters, one other doing
# has the step that fills one of them, and until now that doing's steps were
# read for nothing at all.

_SAVE = f.fingerprint(role="button", accessible_name="Save")
_URL = "https://wms.test/api/carrierCrossReferences"


def _fills(index: int, field: str, value: str) -> ActionFrame:
    return f.frame(
        index,
        action=InputAction(
            kind=ActionKind.TYPE,
            target=f.fingerprint(role="textbox", accessible_name=field),
            value=value,
        ),
        requests=(),
    )


def _saves(index: int, **sent: object) -> ActionFrame:
    return f.frame(
        index,
        action=InputAction(kind=ActionKind.CLICK, target=_SAVE),
        requests=(f.request(method="POST", url=_URL, request_body=f.body(json.dumps(sent))),),
    )


def _short(carrier: str, level: str) -> tuple[ActionFrame, ...]:
    """A cross reference somebody added without touching the address."""
    return (
        _fills(0, "Carrier", carrier),
        _fills(1, "Service Level", level),
        _saves(2, carrier=carrier, serviceLevel=level, codAddressId=""),
    )


def _picked(carrier: str, level: str, address: str) -> tuple[ActionFrame, ...]:
    """The doing that sent an address without typing one.

    The operator chose it out of a picker, so the value reaches the write and
    no keystroke in this recording binds to it. That is what made the real
    `cod_address_id` a parameter the pair could prove and no step could fill.
    """
    return (
        _fills(0, "Carrier", carrier),
        _fills(1, "Service Level", level),
        f.frame(
            2,
            action=InputAction(
                kind=ActionKind.CLICK,
                target=f.fingerprint(role="button", accessible_name="COD Address"),
            ),
            requests=(),
        ),
        _saves(3, carrier=carrier, serviceLevel=level, codAddressId=address),
    )


def _looked_up(carrier: str, level: str, address: str) -> tuple[ActionFrame, ...]:
    """The doing with the address lookup in it -- the one whose steps were
    discarded while its value survived."""
    return (
        _fills(0, "Carrier", carrier),
        _fills(1, "Service Level", level),
        _fills(2, "COD Address", address),
        _saves(3, carrier=carrier, serviceLevel=level, codAddressId=address),
    )


async def _induce(*runs: tuple[ActionFrame, ...]) -> SkillVersion:
    uow = FakeUnitOfWork()
    named = [(f"rec-{index}", frames) for index, frames in enumerate(runs)]
    for ident, frames in named:
        recording = f.recording(frames=0, id=RecordingId(ident))
        for frame in frames:
            recording.append_frame(frame)
        recording.seal(f.at(300))
        await uow.recordings.add(recording)

    clock = FakeClock()
    await InduceSkill(
        uow,
        clock,
        FakeIdFactory(),
        AskAbout(uow, RecordClaims(uow, clock, FakeIdFactory(), FakeEmbedder())),
    ).execute(
        CTX,
        first=RecordingId("rec-0"),
        second=RecordingId("rec-1"),
        others=tuple(RecordingId(ident) for ident, _ in named[2:]),
    )
    return next(iter(uow.skills.rows.values())).versions[-1]


def _typed_by(version: SkillVersion) -> set[str]:
    """Every parameter some step of this skill can actually enter on a screen."""
    return {
        step.ui_plan.value.raw.removeprefix("${").removesuffix("}")
        for step in version.steps
        if step.ui_plan is not None
        and step.ui_plan.value is not None
        and step.ui_plan.value.raw.startswith("${")
    }


async def _four_carrier_cross_references() -> SkillVersion:
    """The real case, in the smallest shape that has all of it.

    Two doings are the pair -- one of them sent an address it never typed, so
    `cod_address_id` is a parameter the diff proves and neither run of the pair
    can fill. A third is another short one. The fourth typed the address, and
    its steps used to reach nothing.
    """
    return await _induce(
        _picked("ACZRD", "T", "A0001"),
        _short("005", "LT"),
        _short("010", "LT"),
        _looked_up("020", "T", "A0009"),
    )


async def test_no_parameter_is_named_that_no_step_can_fill() -> None:
    """The defect stated as a rule. The induced skill declared
    `cod_address_id` and had no gesture that could enter one: the doing that
    demonstrated the lookup went to `parameterise` as history, which reads
    values and never steps, and left again."""
    version = await _four_carrier_cross_references()

    # Every input, not `version.inputs` -- that leaves out the optional ones,
    # and the parameter this whole thing is about is optional. A field somebody
    # may leave empty still needs a gesture for the runs where they do not.
    asked_for = {
        parameter.name for parameter in version.parameters if parameter.kind is ParameterKind.INPUT
    }
    assert asked_for <= _typed_by(version), (sorted(asked_for), sorted(_typed_by(version)))


async def test_the_lookup_step_says_which_value_brings_it_about(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Kept, and kept honestly: the address is entered only on the runs where
    somebody supplies one, which is what `when` has meant since it existed.

    And kept with nothing to check, which is also said out loud. The gesture's
    own calls are dropped -- one observation is not two runs agreeing -- so
    there is no evidence to build an assertion from and the step cannot be
    verified after it runs. A reviewer reading a skill that is mostly these
    should be told, not left to notice.
    """
    with caplog.at_level(logging.INFO, logger="sro.application.induction.induce_skill"):
        version = await _four_carrier_cross_references()

    assert "is a gesture with nothing to check: type, when cod_address_id" in caplog.text

    conditional = [step for step in version.steps if step.when]
    assert [step.when for step in conditional] == ["cod_address_id"]
    assert conditional[0].ui_plan is not None
    assert conditional[0].ui_plan.value is not None
    assert conditional[0].ui_plan.value.raw == "${cod_address_id}"


async def test_the_steps_are_not_what_two_of_the_doings_happened_to_share() -> None:
    """The count is the point. Three is the longest common subsequence of any
    two of these four -- and it is what induction produced no matter which two
    it was handed, because the fourth doing's steps were never read."""
    version = await _four_carrier_cross_references()

    runs = (
        _picked("ACZRD", "T", "A0001"),
        _short("005", "LT"),
        _short("010", "LT"),
        _looked_up("020", "T", "A0009"),
    )
    shared = max(
        len(_longest_common(one, other))
        for index, one in enumerate(runs)
        for other in runs[index + 1 :]
    )
    assert shared == 3
    assert len(version.steps) == 4


async def test_the_lookup_survives_the_reference_being_neither_run_of_the_pair() -> None:
    """A guard on the fixture above, not a rule of its own.

    The three tests before this are only load-bearing on the index
    reconciliation while `align_all` picks a reference that is *not* run A --
    the run every `Parameterisation` index counts. It does here, and this says
    so out loud, so that a change to `_pick_reference` that quietly made run A
    the reference again would fail here rather than turn three tests into ones
    an unreconciled index space would also pass.
    """
    runs = [
        _picked("ACZRD", "T", "A0001"),
        _short("005", "LT"),
        _short("010", "LT"),
        _looked_up("020", "T", "A0009"),
    ]
    reference = align_all(runs).reference

    assert reference is not runs[0]
    assert [_control_of(frame) for frame in reference] == [
        "Carrier",
        "Service Level",
        "COD Address",
        "Save",
    ]


async def _four_carrier_cross_references_nobody_ever_typed() -> SkillVersion:
    """The other half of the real defect, and the one task 3 cannot reach.

    Every doing here picked the address out of a dialog -- a click with no
    value in it -- or left the field alone entirely; none of the four ever
    typed one. Task 3 fixed the pairing above by reading every doing's steps
    instead of just the pair's, and it is right about every doing it can read
    a step out of. It has nothing to read here: `align_all` sees the click
    the same way it would see a stray one, and drops it as noise the way
    `test_a_step_nothing_accounts_for_is_dropped_and_the_reason_written_down`
    already shows it doing. `cod_address_id` still comes out of the pair as a
    proven, optional field -- the pair disagrees on whether an address was
    sent at all -- and there is still no step anywhere that can supply one.
    """
    return await _induce(
        _picked("ACZRD", "T", "A0001"),
        _short("005", "LT"),
        _short("010", "LT"),
        _picked("030", "T", "A0099"),
    )


async def test_a_skill_that_cannot_fill_what_it_asks_for_is_refused() -> None:
    """The rule enforced, not merely made unreachable. The panel now induces
    silently on a press and shows an operator whatever comes back, so a
    version naming a field nothing can fill is not a row in a database for
    somebody to eventually notice -- it is a skill somebody is about to be
    offered, and it must never reach that screen.

    The message is asserted verbatim, not just the type: this sentence is
    what lands in the panel's toast through the teach-refusal path, and a
    refusal an operator cannot read is not the refusal this task is for. It
    names no field, no parameter, nothing internal -- an operator doing
    warehouse work has never heard of `cod_address_id` and should not have to
    learn it to understand why the button did not just work.
    """
    with pytest.raises(InductionFailed) as excinfo:
        await _four_carrier_cross_references_nobody_ever_typed()

    message = str(excinfo.value)
    assert message == (
        "this skill would ask for something no step of it can actually type or choose "
        "on the screen. Demonstrate that value being entered directly, not just picked "
        "another way, so there is a step that can fill it in"
    )
    assert "cod_address_id" not in message
    assert "parameter" not in message


def _wandered(carrier: str, level: str) -> tuple[ActionFrame, ...]:
    """A short doing with somebody typing into a box that reached nothing.

    A note to themselves, a search they abandoned: it typed a value, so
    `align_all` refuses to drop it and hands it on with its count of one, and
    nothing in any write accounts for it.
    """
    return (
        _fills(0, "Carrier", carrier),
        _fills(1, "Service Level", level),
        _fills(2, "Notes", "remember to check this"),
        _saves(3, carrier=carrier, serviceLevel=level, codAddressId=""),
    )


async def test_a_step_nothing_accounts_for_is_dropped_and_the_reason_written_down(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The other half of the rule, and the half that keeps this from being
    union: a rare step with no supplied value behind it is a fumble. It goes,
    and it says so where somebody asked "why is that not in the skill" can
    read the answer."""
    with caplog.at_level(logging.INFO, logger="sro.application.induction.induce_skill"):
        version = await _induce(
            _short("005", "LT"),
            _short("010", "LT"),
            _short("015", "T"),
            _wandered("020", "T"),
        )

    assert len(version.steps) == 3
    assert "dropping a step 1 of the doings made" in caplog.text


def test_a_gesture_that_would_gate_on_two_supplied_values_is_refused() -> None:
    """`SkillStep.when` is one string. A gesture whose typing filled two fields
    that some doing each left empty cannot be written down as one, and picking
    either would run the step on half its condition -- so this refuses, which
    is what `Parameterisation.conditional_on` says the wiring must do rather
    than choose for it."""
    two = Parameterisation(
        parameters=(
            Parameter(name="first", kind=ParameterKind.INPUT, absent_as="null"),
            Parameter(name="second", kind=ParameterKind.INPUT, absent_as="null"),
        ),
        substitutions={
            0: (
                Substitution(site=ActionValueSite(), parameter="first"),
                Substitution(site=ActionValueSite(), parameter="second"),
            )
        },
    )

    with pytest.raises(InductionFailed, match="cannot be written down"):
        _at_reference(two, {0: (0,)}, {})


# --- A loop, and more doings than the pair -----------------------------------
#
# The interaction the first pass cleared on a case analysis that only held for
# one history run. `keep` truncates the pair to its prefix and one iteration;
# `history` arrives whole. Every other doing's second and third turns round the
# block are evidential frames with nowhere to go, so they are spliced onto the
# reference -- and they *agree with each other*, so their count climbs with the
# number of doings rather than staying at one. Every existing loop test uses two
# runs, where there is no history at all and none of this can happen.

_ORDER = "https://wms.test/api/orders/55"


def _opens(lines: list[str]) -> ActionFrame:
    """The read that says which lines are short. Its answer is the list."""
    return f.frame(
        0,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Open")),
        requests=(
            f.request(
                method="GET",
                url=_ORDER,
                status=200,
                response_body=f.body(
                    json.dumps({"data": {"lines": [{"lineId": line} for line in lines]}})
                ),
            ),
        ),
    )


def _adjusts(index: int, line: str) -> ActionFrame:
    return f.frame(
        index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Adjust")),
        requests=(
            f.request(
                method="POST",
                url=f"https://wms.test/api/lines/{line}/adjust",
                status=200,
                request_body=f.body(json.dumps({"lineId": line})),
            ),
        ),
    )


def _every_short_line(*lines: str) -> tuple[ActionFrame, ...]:
    """One doing of "adjust every short line on this order"."""
    return (_opens(list(lines)), *(_adjusts(at + 1, line) for at, line in enumerate(lines)))


async def test_a_loop_is_not_taught_extra_iterations_by_the_doings_around_it() -> None:
    """Seven doings of a looping task, five of them past the pair.

    The pair is two lengths of one block and `keep` cuts it to the prefix and
    one iteration. The five others are whole recordings, and their *second*
    adjust matches every other doing's second adjust -- five of seven, which is
    over two thirds, which is `ALWAYS`. It carries the block's write, so it is
    a step neither demonstration made that nothing diffed: the pair used to
    induce this and would now be refused outright.

    The loop's own body is one step and it stays one step. What the counts can
    say about a run that did the block five times is nothing, so they are not
    asked.
    """
    version = await _induce(
        _every_short_line("1", "2"),
        _every_short_line("1", "2", "3"),
        *[_every_short_line("1", "2") for _ in range(5)],
    )

    loop = version.loops[0]
    assert len(version.steps) == 2, [step.intent for step in version.steps]
    assert (loop.first_step, loop.last_step) == (1, 1)
