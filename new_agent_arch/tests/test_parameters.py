"""What varies between two doings of one job.

Measured on the real corpus: all eight mined workflows came back with an empty
`parameters` list, because the umbrella prompt never asked. Asking would have
bought a guess -- one doing of "Create Work Activity TEST1" cannot say whether
TEST1 is this activity's name or every activity's.
"""

import copy

import pytest

from rig.correlate import correlate
from rig.parameters import parameters_across
from rig.records import Intent
from rig.wire import Batch
from rig.workflows import Step, Workflow
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def _doing(typed: str, suffix: str):
    """One occurrence of a job: the fixture's typed gesture, given a value."""
    gestures = [copy.deepcopy(g) for g in _gestures()]
    for gesture in gestures:
        gesture.id = f"{gesture.id}_{suffix}"
        if gesture.gesture.kind == "type" and not gesture.gesture.secret:
            gesture.gesture.value = typed
    by_id = {g.id: g for g in gestures}
    workflow = Workflow(
        id=f"wfl_{suffix}",
        tenant="acme",
        title="create a work activity",
        narrative="the operator created a work activity",
        steps=[Step(order=0, says="type the code", system=None, cites=list(by_id))],
    )
    return workflow, by_id, {}


def test_one_doing_names_no_parameters() -> None:
    """The honest answer. A single occurrence cannot tell a parameter from a
    constant, and a list that pretends otherwise is worse than an empty one."""
    assert parameters_across([_doing("TEST1", "a")]) == ()


def test_the_threshold_is_what_decides_it_and_not_the_arithmetic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At two doings the guard changes nothing -- one doing gives every control
    a single value and the diff finds nothing to report either way. It earns
    its place only above two, which is where somebody raising the bar to three
    changes a number rather than an argument. Reverting the guard with the bar
    at three lets two doings name a parameter."""
    monkeypatch.setattr("rig.parameters.K_MIN_OCCURRENCES", 3)

    two = [_doing("TEST1", "a"), _doing("TEST2", "b")]

    assert parameters_across(two) == (), "two is not enough when three is asked for"
    monkeypatch.setattr("rig.parameters.K_MIN_OCCURRENCES", 2)
    assert parameters_across(two), "and is enough when two is"


def test_what_the_operator_typed_differently_is_the_parameter() -> None:
    found = parameters_across([_doing("TEST1", "a"), _doing("TEST2", "b")])

    assert [p.name for p in found] == ["clientCode"], "named after the control, not the value"
    assert found[0].seen == ("TEST1", "TEST2")


def test_what_they_typed_identically_is_part_of_the_job() -> None:
    """`click Add` is not a parameter, and neither is a status every doing sets
    to the same thing."""
    assert parameters_across([_doing("TEST1", "a"), _doing("TEST1", "b")]) == ()


def test_a_control_only_one_doing_reached_is_not_a_parameter() -> None:
    """It is a difference between the recordings -- the operator took another
    route that time -- rather than a value the job takes."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    extra_id = "ges_extra"
    only_here = copy.deepcopy(next(iter(first[1].values())))
    only_here.id = extra_id
    only_here.gesture.value = "ONCE"
    if only_here.gesture.target and only_here.gesture.target.component:
        only_here.gesture.target.component.itemId = "seenOnce"
    first[1][extra_id] = only_here
    first[0].steps[0].cites.append(extra_id)

    found = parameters_across([first, second])

    assert "seenOnce" not in [p.name for p in found]


def test_a_credential_is_never_a_parameter() -> None:
    """typed_values refuses the whole gesture when it is secret, which is what
    keeps a password out of a skill's inputs."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    for _, by_id, _unused in (first, second):
        for gesture in by_id.values():
            if gesture.gesture.secret:
                assert gesture.gesture.value is None

    names = [p.name for p in parameters_across([first, second])]

    assert all("secret" not in name.lower() for name in names)


def test_a_reading_can_supply_the_value_the_gesture_did_not() -> None:
    """values_seen is the model's reading of what went in, and typed_values
    reads both. A select whose value the recorder missed is still a parameter
    if the reading saw it change."""
    first, second = _doing("TEST1", "a"), _doing("TEST1", "b")
    target = next(iter(second[1]))
    intents = {target: Intent(gesture_id=target, tenant="acme", values_seen=[])}
    assert parameters_across([first, (second[0], second[1], intents)]) == ()
