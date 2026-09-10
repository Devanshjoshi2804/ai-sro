"""Naming the boxes an operator filled in, when there is only one demonstration.

With nothing to diff against, a typed value is the clearest evidence in the
recording that the next run wants a different answer -- so those become the
skill's parameters. They are named from the control that carried them, and the
rest of the induction has already handed out names by then.

It was passing an empty set of taken names, so a typed value whose control
suggested a name a parameter already had either merged the two -- one box
filling another box's value -- or collided outright and failed the induction
with "parameter names must be unique".
"""

from __future__ import annotations

from sro.application.induction.diff import typed_values
from sro.domain.recording.events import ActionKind, InputAction
from tests import factories as f


def _typed(index: int, value: str, label: str, url: str) -> object:
    """A frame where somebody entered ``value`` into a box called ``label``,
    and the call that carried it away."""
    return f.frame(
        index,
        action=InputAction(
            kind=ActionKind.TYPE,
            target=f.fingerprint(accessible_name=label),
            value=value,
        ),
        requests=(f.request(method="POST", url=url, request_body=f.body(f'{{"v": "{value}"}}')),),
    )


def test_a_typed_value_is_offered_as_a_parameter() -> None:
    run = (_typed(0, "SUP-9", "Supplier number", "https://wms.test/api/suppliers"),)

    choices = typed_values(run)

    assert [choice.value for choice in choices] == ["SUP-9"]


def test_it_does_not_take_a_name_the_induction_has_already_given_out() -> None:
    """Taking one means two parameters with one name, which the skill refuses
    to be built with -- so the whole induction failed rather than the naming."""
    run = (_typed(0, "SUP-9", "Supplier number", "https://wms.test/api/suppliers"),)
    theirs = {choice.field for choice in typed_values(run)}

    choices = typed_values(run, taken=set(theirs))

    assert {choice.field for choice in choices}.isdisjoint(theirs)
