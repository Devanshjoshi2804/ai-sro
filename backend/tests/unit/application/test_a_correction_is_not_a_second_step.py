"""People mistype. That is not a different task.

An operator typed a code, looked at it, cleared it and typed it again. `align`
pairs one of those typings and finds the other unpaired, carrying a value, and
refuses the pair: "the second run did something the other did not: type on
Warehouse Equipment Type". What that reads as in the panel is *"I've watched
this a few times but the doings differ too much for me to be sure -- do one
more and I'll try again."*

On the real deployment it was every pair of four doings of one task -- 0 and 1,
0 and 2, 0 and 3, 1 and 2, 1 and 3, 2 and 3 -- so a task done four times taught
nothing, and the fifth doing would have been refused the same way.

The sibling of `test_exploration_is_not_the_task`: there the noise is a field
clicked twice, here it is a field typed into twice.
"""

from __future__ import annotations

from typing import Any

from sro.application.induction.diff import align, settled
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from tests import factories as f

CREATE = "https://wms.test/data/WM/wm/warehouseEquipmentType"
KEEPALIVE = "https://wms.test/refs/data/api/v1/rp/admin/sessionKeepAlive"


def _frame(index: int, kind: ActionKind, name: str, **overrides: Any) -> ActionFrame:
    return f.frame(
        index=index,
        action=InputAction(
            kind=kind,
            target=f.fingerprint(accessible_name=name, css_path=f"#{name}"),
            value=overrides.pop("value", None),
        ),
        **overrides,
    )


def _type(index: int, name: str, value: str) -> ActionFrame:
    return _frame(index, ActionKind.TYPE, name, value=value, requests=())


def _click(index: int, name: str, **overrides: Any) -> ActionFrame:
    return _frame(index, ActionKind.CLICK, name, **overrides)


def _write(index: int, name: str = "Save", url: str = CREATE) -> ActionFrame:
    return _click(index, name, requests=(f.request(method="POST", url=url, status=201),))


def _typed_it_twice() -> tuple[ActionFrame, ...]:
    return (
        _click(0, "Add", requests=()),
        _type(1, "Warehouse Equipment Type", "8SITDWN"),
        _type(2, "Warehouse Equipment Type", "8SITDOWN"),  # the correction
        _type(3, "Voice Code", "82"),
        _write(4),
    )


def _typed_it_once() -> tuple[ActionFrame, ...]:
    return (
        _click(0, "Add", requests=()),
        _type(1, "Warehouse Equipment Type", "8STANDUP"),
        _type(2, "Voice Code", "83"),
        _write(3),
    )


def test_the_value_that_survives_is_the_one_the_form_was_sent_with() -> None:
    kept = settled(_typed_it_twice())

    typed = [frame.action.value for frame in kept if frame.action.kind == ActionKind.TYPE]
    assert typed == ["8SITDOWN", "82"], "the correction was thrown away and the mistake kept"


def test_a_run_that_corrected_a_field_pairs_with_one_that_did_not() -> None:
    # The refusal this exists to end. Both runs did the same task; one of the
    # operators mistyped a code first.
    pairs = align(settled(_typed_it_twice()), settled(_typed_it_once()))

    assert len(pairs) == 4, "a mistyped code still made two doings into two tasks"


def test_the_same_field_filled_again_after_a_write_is_a_second_thing_submitted() -> None:
    """Two rows added, not one row corrected. The write between them is what
    makes the difference, and both fills are kept."""
    twice = (
        _type(0, "Warehouse Equipment Type", "8SITDOWN"),
        _write(1),
        _type(2, "Warehouse Equipment Type", "8STANDUP"),
        _write(3),
    )

    assert settled(twice) == twice


def test_a_keep_alive_between_two_typings_does_not_make_them_two_submissions() -> None:
    """Background traffic lands on whichever gesture is open. Counting it as a
    write would leave the correction in, which is the refusal all over again."""
    corrected = (
        _type(0, "Voice Code", "8"),
        _click(1, "Voice Code", requests=(f.request(method="POST", url=KEEPALIVE, status=200),)),
        _type(2, "Voice Code", "82"),
        _write(3),
    )

    kept = settled(corrected)

    assert [frame.action.value for frame in kept if frame.action.kind == ActionKind.TYPE] == ["82"]


def test_two_different_fields_are_never_each_other_s_correction() -> None:
    assert settled(_typed_it_once()) == _typed_it_once()


def test_a_credential_typed_twice_is_left_exactly_alone() -> None:
    """A password carries no value to be superseded by, and a run that types
    one twice is a run that failed to sign in once. `domain/skill/passwords`
    has the evidence to judge that; this does not."""
    signing_in = (
        f.frame(
            index=0,
            action=InputAction(
                kind=ActionKind.TYPE,
                target=f.fingerprint(accessible_name="Password", css_path="#password"),
                secret=True,
            ),
            requests=(),
        ),
        f.frame(
            index=1,
            action=InputAction(
                kind=ActionKind.TYPE,
                target=f.fingerprint(accessible_name="Password", css_path="#password"),
                secret=True,
            ),
            requests=(),
        ),
    )

    assert settled(signing_in) == signing_in


def _select(index: int, name: str, value: str) -> ActionFrame:
    return _frame(index, ActionKind.SELECT, name, value=value, requests=())


def _upload(index: int, name: str, value: str) -> ActionFrame:
    return _frame(index, ActionKind.UPLOAD, name, value=value, requests=())


def test_a_dropdown_picked_twice_is_the_second_pick() -> None:
    """The same self-correction one control down. Replaying both picks would do
    the work of the mistake and then the work of the correction."""
    corrected = (
        _select(0, "Carrier Type", "PARCEL"),
        _select(1, "Carrier Type", "FREIGHT"),
        _write(2),
    )

    kept = settled(corrected)

    assert [frame.action.value for frame in kept if frame.action.kind == ActionKind.SELECT] == [
        "FREIGHT"
    ]


def test_a_file_attached_twice_is_the_second_file() -> None:
    corrected = (
        _upload(0, "Document", "old-invoice.pdf"),
        _upload(1, "Document", "invoice.pdf"),
        _write(2),
    )

    assert [frame.action.value for frame in settled(corrected)][:1] == ["invoice.pdf"]


def test_a_button_pressed_twice_is_two_presses() -> None:
    """Deliberately not in the set. Two clicks on one control are two presses
    of a button -- an increment, a row added twice -- and `align` already lets
    a click through as exploration when it changed nothing."""
    twice = (
        _click(0, "Add row", requests=()),
        _click(1, "Add row", requests=()),
        _write(2),
    )

    assert settled(twice) == twice
