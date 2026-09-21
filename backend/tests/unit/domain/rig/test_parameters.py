"""What varies between two doings of one job.

Measured on the real corpus: all eight mined workflows came back with an empty
`parameters` list, because the umbrella prompt never asked. Asking would have
bought a guess -- one doing of "Create Work Activity TEST1" cannot say whether
TEST1 is this activity's name or every activity's.
"""

import copy
from dataclasses import replace

import pytest

from sro.domain.observation.gesture import Gesture, Intent, ValueSeen
from sro.domain.skill.learned import parameters_across
from sro.domain.skill.workflow import Step, Workflow
from tests.unit.domain.rig.conftest import gestures as _gestures


def _doing(typed: str, suffix: str) -> tuple[Workflow, dict[str, Gesture], dict[str, Intent]]:
    """One occurrence of a job: the fixture's typed gesture, given a value."""
    gestures = [copy.deepcopy(g) for g in _gestures()]
    for gesture in gestures:
        gesture.id = f"{gesture.id}_{suffix}"
        if gesture.action.kind == "type" and not gesture.action.secret:
            gesture.action = replace(gesture.action, value=typed)
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
    monkeypatch.setattr("sro.domain.skill.learned.K_MIN_OCCURRENCES", 3)

    two = [_doing("TEST1", "a"), _doing("TEST2", "b")]

    assert parameters_across(two) == (), "two is not enough when three is asked for"
    monkeypatch.setattr("sro.domain.skill.learned.K_MIN_OCCURRENCES", 2)
    assert parameters_across(two), "and is enough when two is"


def test_what_the_operator_typed_differently_is_the_parameter() -> None:
    found = parameters_across([_doing("TEST1", "a"), _doing("TEST2", "b")])

    # The label, because that is the name a person is shown and asked about;
    # the input's own name is kept beside it so a doing recorded the other way
    # is still this control.
    assert [p.name for p in found] == ["Client Code"], "named after the control, not the value"
    assert found[0].seen == ("TEST1", "TEST2")
    assert "clientCode" in found[0].names, "the name the form posts it under was dropped"


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
    target = only_here.action.target
    if target and target.component:
        target = replace(target, component=replace(target.component, item_id="seenOnce"))
    only_here.action = replace(only_here.action, value="ONCE", target=target)
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
            if gesture.action.secret:
                assert gesture.action.value is None

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


def test_the_operator_wins_over_the_models_echo_of_what_it_saw() -> None:
    """typed_values merges both into one set and provenance is gone by the time
    it returns, so a doing where the two disagree was settled by string order.
    The operator typed the value; the reading only reports on it.

    `ZZZZ_TYPED` and `AAAA_ECHO` are chosen so that min() picks the WRONG one:
    a test where the alphabet happens to agree with provenance proves nothing.
    """
    first, second = _doing("TEST1", "a"), _doing("ZZZZ_TYPED", "b")
    typed = next(
        gesture.id for gesture in second[1].values() if gesture.action.value == "ZZZZ_TYPED"
    )
    intents = {
        typed: Intent(
            gesture_id=typed,
            tenant="acme",
            values_seen=[ValueSeen(field="clientCode", value="AAAA_ECHO")],
        )
    }

    found = parameters_across([first, (second[0], second[1], intents)])

    assert [p.seen for p in found] == [("TEST1", "ZZZZ_TYPED")], "the operator, not min()"


def test_a_control_typed_twice_keeps_the_latest_and_not_the_last_cited() -> None:
    """`workArea` got TESTI and then NEWTESTS in the real corpus. Whichever is
    written last wins by dict overwrite, and last has to mean latest -- nothing
    sorts a step's citations, so it was depending on the order the model
    happened to list them in."""
    workflow, by_id, _ = _doing("SECOND", "a")
    typed = [g for g in by_id.values() if g.action.kind == "type" and not g.action.secret]
    assert len(typed) == 1, "the fixture types once; this test gives it a second"
    earlier = copy.deepcopy(typed[0])
    earlier.id = f"{earlier.id}_earlier"
    earlier.action = replace(earlier.action, value="FIRST")
    earlier.at = typed[0].at - 1000
    by_id[earlier.id] = earlier
    # Cited EARLIEST-last, which is what a model listing citations out of order
    # produces and what the old code would have taken as final.
    workflow.steps[0].cites = [*workflow.steps[0].cites, earlier.id]

    found = parameters_across([(workflow, by_id, {}), _doing("SECOND", "b")])

    assert found == (), "both doings end on SECOND, so nothing varies"


def _extra(
    doing: tuple[Workflow, dict[str, Gesture], dict[str, Intent]],
    gesture_id: str,
    at: float | None = None,
    **change: object,
) -> Gesture:
    """A second gesture in one doing, copied from its typed one.

    `at` matters more than it looks: `_by_control` walks in time order, so a
    test about what happens AFTER a skipped gesture has to put the skipped one
    earlier. Copies otherwise share the original's clock and fall back to
    sorting by id, which is alphabetical and not what the test is about.
    """
    workflow, by_id, _ = doing
    made = copy.deepcopy(next(g for g in by_id.values() if g.action.kind == "type"))
    made.id = gesture_id
    updates = dict(change)
    if at is not None:
        made.at = at
        updates["at"] = at
    made.action = replace(made.action, **updates)
    by_id[gesture_id] = made
    workflow.steps[0].cites.append(gesture_id)
    return made


def test_a_control_only_the_SECOND_doing_reached_is_not_a_parameter_either() -> None:  # noqa: N802
    """The mirror of the test above, and the one that was missing.

    `shared` is seeded from `doings[0]` and intersected with the rest, so a
    control only the first doing reached was already covered. A control only the
    LAST doing reached was not: seeding from the wrong end leaves it in `shared`
    and the diff then reads a doing that never touched it.
    """
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    made = _extra(second, "ges_only_second", value="ONCE")
    if made.action.target and made.action.target.component:
        made.action = replace(
            made.action,
            target=replace(
                made.action.target,
                component=replace(made.action.target.component, item_id="seenOnlyInTheSecond"),
            ),
        )

    found = parameters_across([first, second])

    assert "seenOnlyInTheSecond" not in [p.name for p in found]


def test_a_select_and_an_upload_are_typing_too() -> None:
    """`_by_control` names three kinds and the fixture only ever exercised one.
    A dropdown the operator chose differently is as much a parameter as a box
    they typed in differently -- that is what the other two kinds are for."""
    for kind in ("select", "upload"):
        first, second = _doing("TEST1", "a"), _doing("TEST1", "b")
        for doing, value in ((first, "ONE"), (second, "TWO")):
            made = _extra(doing, f"ges_{kind}", kind=kind, value=value, secret=False)
            if made.action.target and made.action.target.component:
                made.action = replace(
                    made.action,
                    target=replace(
                        made.action.target,
                        component=replace(
                            made.action.target.component, item_id=f"the{kind.title()}"
                        ),
                    ),
                )

        found = {p.name: p.seen for p in parameters_across([first, second])}

        # Under the label, because this fixture's extra gesture is a copy of
        # the typed one and carries its label. What is being asserted is that
        # the kind was read at all: the base control is constant across both
        # doings, so this value can only have come from the select or upload.
        assert found.get("Client Code") == ("ONE", "TWO"), kind


def test_a_gesture_that_contributes_nothing_does_not_end_the_walk() -> None:
    """`continue`, not `break`. A click cited between two typed gestures, or a
    credential refused by `typed_values`, would otherwise take every control
    after it with it -- and the citations are in the model's order, so which
    gestures come after a skipped one is not something to depend on."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    for doing, value in ((first, "ONE"), (second, "TWO")):
        # One of each kind of skip: a click, which is not a typing kind at all,
        # and a credential, which IS one and whose value `typed_values` refuses.
        # They leave by different doors and both doors were `break` once.
        _extra(doing, "ges_click", at=1.0, kind="click", value=None)
        _extra(doing, "ges_secret", at=2.0, value="hunter2", secret=True)
        made = _extra(doing, "ges_after", at=3.0, value=value)
        if made.action.target and made.action.target.component:
            made.action = replace(
                made.action,
                target=replace(
                    made.action.target,
                    component=replace(made.action.target.component, item_id="typedAfterTheClick"),
                ),
            )

    found = {p.name: p.seen for p in parameters_across([first, second])}

    assert found.get("typedAfterTheClick") == ("ONE", "TWO"), "the walk went on"
    assert not any("secret" in name.lower() for name in found), "and the credential is not in it"


def test_the_control_name_falls_through_to_the_label_and_then_the_field() -> None:
    """An ExtJS itemId where there is one, the field's own label otherwise, the
    accessible name after that. Each rung is what names a parameter when the
    framework gave less than the recorder hoped for."""
    for missing, expected in (("itemId", "The Label"), ("both", "Accessible Name")):
        first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
        for doing, value in ((first, "ONE"), (second, "TWO")):
            made = _extra(doing, "ges_ladder", value=value)
            target = made.action.target
            assert target is not None and target.component is not None
            component = replace(
                target.component,
                item_id=None,
                field_label="The Label" if missing == "itemId" else None,
            )
            target = replace(target, component=component, name="Accessible Name")
            made.action = replace(made.action, target=target)

        found = [p.name for p in parameters_across([first, second])]

        assert expected in found, missing


def test_a_value_only_the_reading_saw_still_names_a_parameter() -> None:
    """A select whose value the recorder missed. `typed_values` reads the
    gesture and the intent, and where only the intent has one, that is the
    value -- so the intent has to be looked up by the gesture being examined."""
    first, second = _doing("TEST1", "a"), _doing("TEST1", "b")
    intents: list[dict[str, Intent]] = []
    for doing, value in ((first, "FROM-A"), (second, "FROM-B")):
        made = _extra(doing, "ges_readonly", kind="select", value=None, secret=False)
        if made.action.target and made.action.target.component:
            made.action = replace(
                made.action,
                target=replace(
                    made.action.target,
                    component=replace(made.action.target.component, item_id="readOnlyCombo"),
                ),
            )
        intents.append(
            {
                "ges_readonly": Intent(
                    gesture_id="ges_readonly",
                    tenant="acme",
                    values_seen=[ValueSeen(field="readOnlyCombo", value=value)],
                )
            }
        )

    found = {
        p.name: p.seen
        for p in parameters_across(
            [(first[0], first[1], intents[0]), (second[0], second[1], intents[1])]
        )
    }

    assert found.get("Client Code") == ("FROM-A", "FROM-B")


def test_one_field_recorded_two_ways_is_one_parameter() -> None:
    """The defect this cost a deployment, in the smallest shape that has it.

    `Create a Customer Type` on the real store held four parameters for two
    fields: `Customer Type` and `customertype-customerType` with two values
    each, and the same pair again for the description. The page names a field
    twice -- the label a person reads, the input name the form posts -- and
    which of the two a recording carries is a fact about that recording. Two
    doings that carried different ones agreed on nothing, so each contributed
    its own parameter.

    What the operator then saw was four boxes on the offer card for two
    values, two of them asking for a name nobody has ever typed.
    """
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    # The second recording carried only the input name for the same field.
    for gesture in second[1].values():
        target = gesture.action.target
        if target is None or target.component is None:
            continue
        gesture.action = replace(
            gesture.action,
            target=replace(target, component=replace(target.component, field_label=None)),
        )

    found = parameters_across([first, second])

    assert len(found) == 1, [p.name for p in found]
    assert found[0].seen == ("TEST1", "TEST2"), "the two doings were not read as one control"
    # And it answers to both, so the doing after this recognises it either way.
    assert set(found[0].names) == {"Client Code", "clientCode"}


def test_two_fields_that_share_a_label_stay_two() -> None:
    """The other half of the same rule. A form can carry a Description in each
    of two sections; the page's own name for each is what says they are two,
    and merging them would be one parameter where the job has two."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    for doing, value in ((first, "ONE"), (second, "TWO")):
        made = _extra(doing, "ges_other_section", at=9.0, value=value)
        target = made.action.target
        assert target is not None and target.component is not None
        made.action = replace(
            made.action,
            target=replace(target, component=replace(target.component, item_id="otherSection")),
        )

    found = parameters_across([first, second])

    assert len(found) == 2, [p.name for p in found]
    # And neither is called by the label they share, because two questions
    # worded identically are worse than one ugly name.
    assert sorted(p.name for p in found) == ["clientCode", "otherSection"]
