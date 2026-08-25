"""The loop: a block of steps done once for each thing in a list.

What is under test is what a loop refuses to be. Its shape is decided at
induction from two demonstrations, and everything here is the domain saying no
to a shape that would mean something nobody has decided -- because a version
that means two things at run time is worse than a version that refuses to exist.
"""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.loop import Binding, Loop
from sro.domain.skill.parameter import Parameter, ParameterKind
from sro.domain.skill.plan import Template
from tests import factories as f

LINE = Binding(parameter="line_id", pointer="/lineId")


def _plain(index: int) -> object:
    """A step that names no parameters, so the version's own checks are not what
    fires in tests about loops."""
    return f.step(
        index=index,
        network_plan=f.network_plan(url=Template("https://wms.test/api/lines"), body=None),
    )


def _loop(**over: object) -> Loop:
    defaults: dict[str, object] = {
        "over_step_index": 0,
        "over_pointer": "/data/lines",
        "first_step": 1,
        "last_step": 2,
        "binds": (LINE,),
    }
    return Loop(**{**defaults, **over})  # type: ignore[arg-type]


def test_a_loop_iterates_over_a_list_an_earlier_step_produced() -> None:
    """The count comes from the system's own answer at run time. A loop over a
    list produced by a step inside it, or by itself, would be a count nobody
    can know before starting."""
    with pytest.raises(InvariantViolation, match="is not before"):
        _loop(over_step_index=1)


def test_a_loop_that_binds_nothing_is_refused() -> None:
    """It would send the same call once per element -- the same write, N times,
    which is not a task anybody demonstrated and is the worst possible thing to
    infer from evidence that two runs did a block a different number of times."""
    with pytest.raises(InvariantViolation, match="binds nothing"):
        _loop(binds=())


def test_a_body_that_ends_before_it_begins_is_refused() -> None:
    with pytest.raises(InvariantViolation, match="ends before it begins"):
        _loop(first_step=3, last_step=2)


def test_a_version_refuses_overlapping_loops() -> None:
    """Which is how nesting is refused too: what a nested loop means at run
    time -- and what the breaker should count as its blast radius -- is a
    decision nobody has had to make yet."""
    with pytest.raises(InvariantViolation, match="may not overlap"):
        f.skill_version(
            steps=(_plain(0), _plain(1), _plain(2)),
            parameters=(Parameter(name="line_id", kind=ParameterKind.INPUT),),
            loops=(_loop(first_step=1, last_step=2), _loop(first_step=2, last_step=2)),
        )


def test_a_version_refuses_a_loop_that_runs_off_the_end() -> None:
    with pytest.raises(InvariantViolation, match="this version has"):
        f.skill_version(
            steps=(_plain(0), _plain(1)),
            parameters=(Parameter(name="line_id", kind=ParameterKind.INPUT),),
            loops=(_loop(first_step=1, last_step=4),),
        )


def test_a_version_refuses_a_loop_binding_a_parameter_nobody_declared() -> None:
    """Otherwise the body renders `${line_id}` from nothing and sends the
    literal placeholder to a warehouse."""
    with pytest.raises(InvariantViolation, match="undeclared parameters: line_id"):
        f.skill_version(
            steps=(_plain(0), _plain(1)),
            parameters=(),
            loops=(_loop(first_step=1, last_step=1),),
        )


def test_a_version_says_which_loop_a_step_belongs_to_and_which_it_feeds() -> None:
    version = f.skill_version(
        steps=(_plain(0), _plain(1), _plain(2)),
        parameters=(Parameter(name="line_id", kind=ParameterKind.INPUT),),
        loops=(_loop(),),
    )

    assert version.loop_at(0) is None, "the step that produced the list is not in the body"
    assert version.loop_at(2) is not None
    # Read when step 0 finishes: that is the moment the list, and the number of
    # iterations, exists at all.
    assert version.loop_from(0) is not None
    assert version.loop_from(1) is None
    assert version.loops[0].describe() == "once for each lines step 0 found"
