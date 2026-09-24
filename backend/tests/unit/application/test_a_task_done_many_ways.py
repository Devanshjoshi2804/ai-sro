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

from sro.application.context import RequestContext
from sro.application.induction.diff import (
    align_all,
)
from sro.application.induction.errors import InductionFailed
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from tests import factories as f

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


def test_the_run_count_is_recorded_not_inferred_from_the_counts() -> None:
    """Five doings, and the busiest step was in three of them.

    Two operators here wandered somewhere else entirely, and nothing they
    touched carried evidence of itself, so nothing they did reaches the
    reference -- but they are still two of the five doings this task was
    demonstrated in, and every share `standing_of` computes is a share of
    five. Reading the denominator back out of the counts, as the largest of
    them, would say three: the two wanderers would vanish from the
    denominator as well as from the reference, and a step three of five
    doings made would come out unanimous.

    Pinned at the source and not only at the arithmetic. `align_all` is the
    only thing here that knows how many runs it was handed, and a later
    reader tempted to derive the number from `seen` -- which agrees with it
    in every fixture where somebody made every step -- has to fail this.
    """
    found = align_all(
        [
            _run("Alpha", "Beta", "Gamma"),
            _run("Zulu", "Yankee", "Xray"),
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
            _run("Add", "Carrier", "Save"),
        ]
    )

    assert found.doings == 5
    assert max(found.seen.values()) == 3


def test_one_doing_alone_is_still_an_alignment() -> None:
    """A task demonstrated once has nothing to disagree with it. Every step is
    seen by everything there is."""
    found = align_all([_run("Add", "Save")])

    assert len(found.reference) == 2
    assert set(found.seen.values()) == {1}


def test_nothing_at_all_refuses_rather_than_returning_an_empty_task() -> None:
    from pytest import raises

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
