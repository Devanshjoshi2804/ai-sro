"""Both operators picked the same address. That proves nothing about the task.

Two runs agreeing on a value is not evidence that the value is fixed -- it is
evidence that two people made the same choice, which is what people teaching the
same task do. Replaying it writes every supplier to one address; parameterising
it prompts for a field nobody thinks about. Both are guesses, so it is asked.
"""

from __future__ import annotations

import json

from sro.application.induction.diff import parameterise
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.skill.parameter import ParameterKind
from tests import factories as f

ADDRESSES = "https://wms.test/data/WM/wm/addresses"
LIST = f"{ADDRESSES}?siteId=SG"


def _screen() -> ActionFrame:
    """The screen listing the addresses somebody is about to choose between."""
    return f.frame(
        index=0,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Address")),
        requests=(
            f.request(
                method="GET",
                url=LIST,
                status=200,
                response_body=Body(
                    text=json.dumps({"data": [{"addressId": "A1"}, {"addressId": "A2"}]})
                ),
            ),
        ),
    )


def _save(supplier: str) -> ActionFrame:
    """Save addresses the chosen record in the path and repeats it in the body."""
    return f.frame(
        index=1,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Save")),
        requests=(
            f.request(
                method="PUT",
                url=f"{ADDRESSES}/A1",
                status=200,
                request_body=Body(
                    text=json.dumps({"data": {"addressId": "A1", "supplierNumber": supplier}})
                ),
            ),
        ),
    )


def _runs() -> tuple[tuple[ActionFrame, ...], tuple[ActionFrame, ...]]:
    return (_screen(), _save("SUP1")), (_screen(), _save("SUP2"))


def test_a_value_chosen_off_the_screen_twice_becomes_a_question() -> None:
    run_a, run_b = _runs()

    result = parameterise(run_a, run_b)

    assert [(c.field, c.value, c.seen_at) for c in result.choices] == [("address_id", "A1", 0)]


def test_nothing_changes_until_somebody_answers() -> None:
    """The skill runs exactly as it was demonstrated while the question waits."""
    run_a, run_b = _runs()

    result = parameterise(run_a, run_b)

    assert [p.name for p in result.parameters] == ["supplier_number"]
    assert result.for_step(1) == {next(iter(result.substitutions[1])).site: "${supplier_number}"}


def test_answering_ask_each_time_makes_it_an_input() -> None:
    run_a, run_b = _runs()

    result = parameterise(run_a, run_b, ask_for=frozenset({"address_id"}))

    chosen = next(p for p in result.parameters if p.name == "address_id")
    assert chosen.kind is ParameterKind.INPUT
    assert chosen.observed_values == ("A1",)
    # Path and body together: one answer, every place the call sends it.
    assert sorted(result.for_step(1).values()) == [
        "${address_id}",
        "${address_id}",
        "${supplier_number}",
    ]


def test_a_value_nobody_could_have_chosen_is_not_asked_about() -> None:
    """Nothing listed it, so it was not picked off a screen -- it was typed, or
    it is simply what this deployment sends."""
    bare = (_save("SUP1"),), (_save("SUP2"),)

    assert parameterise(*bare).choices == ()
