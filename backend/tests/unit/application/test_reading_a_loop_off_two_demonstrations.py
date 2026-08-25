"""Two demonstrations that did the same block a different number of times.

"Adjust every short-shipped line on this order" is one task, and it was the one
task induction could not express: a skill is a flat list of steps, so an order
with two short lines and an order with three disagreed about how many steps the
task has -- and the pair was refused, saying the runs were not two runs of one
task. They were.

Most of what is here is what this refuses. A wrong loop is a warehouse doing
something once per row of a list nobody meant, so the bar is the one the rest of
induction keeps: read the rule off one run, then require it to explain the other
one too, from the same place in the same response.
"""

from __future__ import annotations

import json

from sro.application.induction.loops import detect
from sro.domain.recording.events import ActionFrame, ActionKind, InputAction
from sro.domain.recording.network import Body
from sro.domain.skill.parameter import ParameterKind
from tests import factories as f

ORDER = "https://wms.test/api/orders/55"


def _open(index: int, lines: list[str], key: str = "lines") -> ActionFrame:
    """The step that asks which lines are short. Its answer is the list."""
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Open")),
        requests=(
            f.request(
                method="GET",
                url=ORDER,
                status=200,
                response_body=Body(
                    text=json.dumps(
                        {"data": {key: [{"lineId": line, "short": True} for line in lines]}}
                    )
                ),
            ),
        ),
    )


def _adjust(index: int, line: str) -> ActionFrame:
    return f.frame(
        index=index,
        action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Adjust")),
        requests=(
            f.request(
                method="POST",
                url=f"https://wms.test/api/lines/{line}/adjust",
                status=200,
                request_body=Body(text=json.dumps({"lineId": line})),
            ),
        ),
    )


def _runs(
    first: list[str], second: list[str]
) -> tuple[tuple[ActionFrame, ...], tuple[ActionFrame, ...]]:
    run_a = (_open(0, first), *(_adjust(i + 1, line) for i, line in enumerate(first)))
    run_b = (_open(0, second), *(_adjust(i + 1, line) for i, line in enumerate(second)))
    return run_a, run_b


def test_the_block_the_two_runs_did_a_different_number_of_times_is_the_loop() -> None:
    found = detect(*_runs(["1", "2"], ["7", "8", "9"]))

    assert found is not None
    assert (found.loop.first_step, found.loop.last_step) == (1, 1)
    # The count is the system's own answer, not a number anybody guessed.
    assert (found.loop.over_step_index, found.loop.over_pointer) == (0, "/data/lines")
    assert [(b.parameter, b.pointer) for b in found.loop.binds] == [("line_id", "/lineId")]
    # The skill keeps one iteration: the rest are the same block again and have
    # nothing left to prove.
    assert found.keep == 2


def test_the_value_it_binds_is_a_parameter_nobody_is_ever_asked_for() -> None:
    found = detect(*_runs(["1", "2"], ["7", "8", "9"]))

    assert found is not None
    assert [p.kind for p in found.parameters] == [ParameterKind.ITERATED]
    assert found.parameters[0].observed_values == ("1", "2")
    # Substituted where it was sent -- both places, one parameter: the id is in
    # the path and in the body, and two parameters holding one value is how a
    # reviewer ends up reading a plan that looks like a mis-binding.
    assert len(found.substitutions[1]) == 2


def test_two_runs_that_did_the_same_number_of_things_are_not_a_loop() -> None:
    """A task that happens to do three similar things. The ordinary diff has
    always read that correctly, and calling it a loop would make it iterate over
    a list nobody counted."""
    assert detect(*_runs(["1", "2"], ["7", "8"])) is None


def test_a_list_that_is_not_as_long_as_the_work_done_is_not_the_source() -> None:
    """The whole rule in one case: the response has a list, the runs did a
    different number of things, and the two numbers have nothing to do with each
    other. A page of results happens to have three rows in the run that did
    three things.

    Two independent checks enforce this -- the search for the source, and the
    bindings that are read out of it -- and this fails only when both are gone,
    which is what it is here to protect.
    """
    run_a, run_b = _runs(["1", "2"], ["7", "8", "9"])
    # Run B's list says four lines are short; only three were adjusted.
    run_b = (_open(0, ["7", "8", "9", "10"]), *run_b[1:])

    assert detect(run_a, run_b) is None


def test_a_binding_that_explains_one_run_and_not_the_other_is_refused() -> None:
    """The speculate-and-validate rule. Run B's second line was adjusted against
    an id that is not in its list at all -- so nothing about the element
    explains what was sent, and the honest answer is that this is not a loop."""
    run_a, run_b = _runs(["1", "2"], ["7", "8", "9"])
    run_b = (*run_b[:2], _adjust(2, "999"), *run_b[3:])

    assert detect(run_a, run_b) is None


def test_a_block_of_several_steps_is_read_whole() -> None:
    """One iteration is open-the-line then adjust-it. The body is both steps,
    not the last one."""

    def _line(index: int, line: str) -> tuple[ActionFrame, ActionFrame]:
        opened = f.frame(
            index=index,
            action=InputAction(kind=ActionKind.CLICK, target=f.fingerprint(accessible_name="Line")),
            requests=(
                f.request(method="GET", url=f"https://wms.test/api/lines/{line}", status=200),
            ),
        )
        return opened, _adjust(index + 1, line)

    run_a = (_open(0, ["1", "2"]), *[frame for line in ["1", "2"] for frame in _line(0, line)])
    run_b = (
        _open(0, ["7", "8", "9"]),
        *[frame for line in ["7", "8", "9"] for frame in _line(0, line)],
    )

    found = detect(run_a, run_b)

    assert found is not None
    assert (found.loop.first_step, found.loop.last_step) == (1, 2)
    assert found.keep == 3
