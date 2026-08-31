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

from sro.application.induction.diff import align_all
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from tests import factories as f


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
