"""What varies between two doings of one job.

Measured on the real corpus: all eight mined workflows came back with an empty
`parameters` list, because the umbrella prompt never asked. Asking would have
bought a guess -- one doing of "Create Work Activity TEST1" cannot say whether
TEST1 is this activity's name or every activity's.
"""

import copy
from dataclasses import replace

import pytest

from sro.domain.observation.gesture import Component, Gesture, Intent, ValueSeen
from sro.domain.skill.learned import (
    LearnedParameter,
    demanded,
    offerable,
    parameters_across,
)
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


def test_one_doing_makes_every_typed_value_a_parameter() -> None:
    """Decided 2026-09-27 from the greyorange baseline: one doing cannot tell a
    parameter from a constant, and the model, left to guess, called every
    typed value fixed text. So a typed value is a parameter until the evidence
    says it is constant."""
    found = {p.name: p.seen for p in parameters_across([_doing("TEST1", "a")])}

    assert found == {"Client Code": ("TEST1",), "Dock": ("D3",), "Manifest": ("manifest.csv",)}


def test_the_threshold_decides_when_an_identical_value_is_a_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two doings that typed the same value make it part of the job; raising
    the bar to three keeps it a parameter until a third doing agrees."""
    two = [_doing("TEST1", "a"), _doing("TEST1", "b")]
    monkeypatch.setattr("sro.domain.skill.learned.K_MIN_OCCURRENCES", 3)

    assert [p.name for p in parameters_across(two)] == ["Client Code", "Dock", "Manifest"]
    monkeypatch.setattr("sro.domain.skill.learned.K_MIN_OCCURRENCES", 2)
    assert parameters_across(two) == ()


def test_what_the_operator_typed_differently_is_the_parameter() -> None:
    found = parameters_across([_doing("TEST1", "a"), _doing("TEST2", "b")])

    # The label, because that is the name a person is shown and asked about;
    # the input's own name is its key, never a name, and is what tells a doing
    # recorded the other way that it is still this control.
    assert [p.name for p in found] == ["Client Code"], "named after the control, not the value"
    assert found[0].seen == ("TEST1", "TEST2")
    assert found[0].key == "clientCode" and "clientCode" not in found[0].names


def test_what_they_typed_identically_is_part_of_the_job() -> None:
    """`click Add` is not a parameter, and neither is a status every doing sets
    to the same thing."""
    assert parameters_across([_doing("TEST1", "a"), _doing("TEST1", "b")]) == ()


def test_a_control_only_one_doing_reached_is_a_parameter_not_every_run_needs() -> None:
    """It was not typed identically in every doing, so it is not a constant;
    and a route that never reached it is not short of anything."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    extra_id = "ges_extra"
    only_here = copy.deepcopy(next(iter(first[1].values())))
    only_here.id = extra_id
    target = only_here.action.target
    if target and target.component:
        target = replace(
            target,
            name="seenOnce",
            component=replace(target.component, item_id="seenOnce", field_label="seenOnce"),
        )
    only_here.action = replace(only_here.action, value="ONCE", target=target)
    first[1][extra_id] = only_here
    first[0].steps[0].cites.append(extra_id)

    found = {p.name: p for p in parameters_across([first, second])}

    assert found["seenOnce"].seen == ("ONCE",) and found["seenOnce"].in_all is False


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


def test_a_control_only_the_SECOND_doing_reached_is_a_parameter_too() -> None:  # noqa: N802
    """The mirror of the test above: every doing's controls are looked at, not
    only the first one's."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    made = _extra(second, "ges_only_second", value="ONCE")
    if made.action.target and made.action.target.component:
        made.action = replace(
            made.action,
            target=replace(
                made.action.target,
                name="seenOnlyInTheSecond",
                component=replace(
                    made.action.target.component,
                    item_id="seenOnlyInTheSecond",
                    field_label="seenOnlyInTheSecond",
                ),
            ),
        )

    found = {p.name: p for p in parameters_across([first, second])}

    assert found["seenOnlyInTheSecond"].in_all is False


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
                    name="typedAfterTheClick",
                    component=replace(
                        made.action.target.component,
                        item_id="typedAfterTheClick",
                        field_label="typedAfterTheClick",
                    ),
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
    # Its key is what the two recordings share; a name it is never given.
    assert found[0].names == ("Client Code",) and found[0].key == "clientCode"


def test_two_fields_that_share_a_label_stay_two() -> None:
    """The other half of the same rule. A form can carry a Description in each
    of two sections; the page's own key for each is what says they are two,
    and merging them would be one parameter where the job has two. The one
    with an accessible name of its own is asked for by it."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    for doing, value in ((first, "ONE"), (second, "TWO")):
        made = _extra(doing, "ges_other_section", at=9.0, value=value)
        target = made.action.target
        assert target is not None and target.component is not None
        made.action = replace(
            made.action,
            target=replace(
                target,
                name="Other Section",
                component=replace(target.component, item_id="otherSection"),
            ),
        )

    found = parameters_across([first, second])

    assert sorted(p.name for p in found) == ["Client Code", "Other Section"]


def test_two_fields_nothing_but_their_key_tells_apart_stay_fixed() -> None:
    """Never named by the page's id for them (M3 round 1), and one name for two
    fields would type one answer into both. They stay fixed text, which the
    console shows through `fixed_values`."""
    first, second = _doing("TEST1", "a"), _doing("TEST2", "b")
    for doing, value in ((first, "ONE"), (second, "TWO")):
        made = _extra(doing, "ges_other_section", at=9.0, value=value)
        target = made.action.target
        assert target is not None and target.component is not None
        made.action = replace(
            made.action,
            target=replace(target, component=replace(target.component, item_id="otherSection")),
        )

    assert parameters_across([first, second]) == ()


# -- a field the first doing never touched -----------------------------------
#
# Asked on the deployment 2026-09-21, and true at the time: an operator does a
# job on Monday, and on Tuesday fills a field that was on the form all along
# but nobody had typed into -- then on Wednesday fills it again, with something
# else. Two doings varied it, which is this system's whole bar for a
# parameter. It was never even looked at, because the search iterated the
# FIRST doing's controls and a stored job's steps never grow. The field could
# not become a parameter however many times it was used.


def _doing_with(extra: str | None, typed: str, suffix: str) -> tuple[Workflow, dict, dict]:
    """A doing that also types `extra` into a second control, or does not."""
    workflow, by_id, intents = _doing(typed, suffix)
    if extra is None:
        return workflow, by_id, intents
    template = next(g for g in by_id.values() if g.action.kind == "type")
    another = copy.deepcopy(template)
    another.id = f"ges_dock_{suffix}"
    another.at = template.at + 1
    was = template.action.target
    assert was is not None, "the fixture's typed gesture lost its target"
    another.action = replace(
        template.action,
        value=extra,
        target=replace(was, component=Component(item_id="inboundDock", field_label="Inbound Dock")),
    )
    by_id[another.id] = another
    workflow.steps = [
        Step(order=0, says="type the code", system=None, cites=list(by_id)),
    ]
    return workflow, by_id, intents


def test_a_control_two_later_doings_varied_is_a_parameter() -> None:
    monday = _doing_with(None, "TEST1", "a")
    tuesday = _doing_with("DOCK-1", "TEST2", "b")
    wednesday = _doing_with("DOCK-2", "TEST3", "c")

    found = parameters_across([monday, tuesday, wednesday])

    names = {one.name for one in found}
    assert "Inbound Dock" in names, f"the field was never looked at: {sorted(names)}"


def test_a_control_not_every_doing_reached_does_not_ask_every_run_for_a_value() -> None:
    """Learning a field must not cost the job the ability to run without it.
    Monday's route never reached this control, so a run taking that route is
    not short of anything -- see `_not_given`, which is where it is felt."""
    found = parameters_across(
        [
            _doing_with(None, "TEST1", "a"),
            _doing_with("DOCK-1", "TEST2", "b"),
            _doing_with("DOCK-2", "TEST3", "c"),
        ]
    )

    dock = next(one for one in found if one.name == "Inbound Dock")
    code = next(one for one in found if one.name != "Inbound Dock")
    assert dock.in_all is False
    assert code.in_all is True, "a control every doing typed is still asked for"


def test_one_appearance_is_a_parameter_since_one_value_is_no_constant() -> None:
    """One value cannot be told from a constant, and since 2026-09-27 that
    doubt makes it a parameter rather than fixed text."""
    found = parameters_across(
        [
            _doing_with(None, "TEST1", "a"),
            _doing_with("DOCK-1", "TEST2", "b"),
        ]
    )

    assert "Inbound Dock" in {one.name for one in found}


# --- what the PAGE said about a control, as opposed to what the operator did --


def test_a_field_the_form_starred_is_required() -> None:
    """The form marks its mandatory fields, the recorder captured the mark in
    the label, and it has been sitting in `names` since the day the job was
    demonstrated. Read off the deployment 2026-09-22:

        Customer Type  ["Customer Type", "customertype-customerType", "Customer Type*"]
    """
    starred = LearnedParameter(
        name="Customer Type",
        seen=("GGD", "GKB"),
        names=("Customer Type", "customertype-customerType", "Customer Type*"),
    )

    assert starred.required is True


def test_a_field_the_form_did_not_mark_is_not_required() -> None:
    """Measured the same night, on the same job. Nothing on the form asks for
    Manufacturer, and the job refused to run without it because two
    demonstrations happened to fill it."""
    plain = LearnedParameter(
        name="Manufacturer",
        seen=("OUTSIDE", "testing"),
        names=("Manufacturer", "customertype-manufacturerId"),
        # The state that used to make it mandatory. It says what the operator
        # did, not what the form demands.
        in_all=True,
    )

    assert plain.required is False
    assert plain.in_all is True, "the two are different questions and both are kept"


def test_a_control_nobody_named_is_not_required() -> None:
    """Unknown reads as optional, and the failure modes are why. A required
    field treated as optional reaches Save, the form refuses, and the screen
    belt says so -- one failed run, and something learnt. An optional field
    treated as required cannot run at all without a value the operator may not
    have."""
    unnamed = LearnedParameter(name="something", seen=("a", "b"))

    assert unnamed.required is False


def test_the_mark_is_read_off_the_end_of_a_name_and_not_from_anywhere_in_it() -> None:
    """A label that merely CONTAINS a star is not a label that ends with one.
    `Rate (per kg) * quantity` is a field name, not a demand."""
    multiplied = LearnedParameter(name="Rate", seen=("1", "2"), names=("Rate (per kg) * quantity",))

    assert multiplied.required is False


def test_a_mark_survives_the_space_a_page_leaves_after_it() -> None:
    """Labels come off the page as the page wrote them, trailing whitespace
    and all, and a rule that missed `"Customer Type* "` would be a rule that
    worked on one form and not the next."""
    spaced = LearnedParameter(name="Customer Type", seen=("A", "B"), names=("Customer Type* ",))

    assert spaced.required is True


def test_what_a_job_can_also_fill_is_what_nobody_has_to_and_nobody_gave() -> None:
    """The offer is the fields the page does not ask for, minus the ones this
    run already has a value for. Offering a field somebody has answered is
    asking them the same thing twice."""
    stored = [
        {"name": "Customer Type", "names": ["Customer Type*"], "seen_values": ["GGD"]},
        {"name": "Department", "names": ["Department"], "seen_values": ["IN", "new"]},
        {"name": "Manufacturer", "names": ["Manufacturer"], "seen_values": ["OUTSIDE", "testing"]},
    ]

    assert offerable(stored, {"Customer Type": "NRT2"}) == (
        ("Department", "new"),
        ("Manufacturer", "testing"),
    )
    assert offerable(stored, {"Department": "IN"}) == (("Manufacturer", "testing"),)


def test_the_value_offered_is_the_most_recent_and_not_the_whole_history() -> None:
    """`seen` is in the order the occurrences were seen. An offer somebody
    reads in one line is a suggestion; "Department was IN, new, IN, OUTSIDE"
    is a history."""
    stored = [{"name": "Department", "names": ["Department"], "seen_values": ["IN", "new", "last"]}]

    assert offerable(stored, {}) == (("Department", "last"),)


def test_a_field_the_job_has_never_filled_is_still_offered() -> None:
    """It is still a field this job can fill. The offer simply has nothing to
    suggest."""
    stored = [{"name": "Pallet Building", "names": ["Pallet Building"], "seen_values": []}]

    assert offerable(stored, {}) == (("Pallet Building", ""),)


def test_the_rule_the_runner_and_the_question_share_is_one_rule() -> None:
    """`demanded` is read by the runner, deciding what stops a run, and by the
    question, deciding what to offer instead of demand. A rule kept in two
    places is a rule that drifts."""
    assert demanded({"name": "x", "names": ["Customer Type*"]}) is True
    assert demanded({"name": "x", "names": ["Department"]}) is False
    # The flag wins where both speak: a later pass may have learnt from a
    # refusal what no label ever said.
    assert demanded({"name": "x", "names": ["Department"], "required": True}) is True
    assert demanded({"name": "x", "names": ["Customer Type*"], "required": False}) is False


def test_what_the_page_said_beats_what_the_label_looked_like() -> None:
    """Three signals, and the star is the weakest of them: screen readers skip
    it as punctuation, which is why `aria-required` and the HTML5 attribute
    exist at all. Where a recording carried one of those, it is the answer.
    """
    said_no = LearnedParameter(name="x", seen=("a", "b"), names=("Looks Required*",), said=False)
    said_yes = LearnedParameter(name="y", seen=("a", "b"), names=("Looks Optional",), said=True)

    assert said_no.required is False, "a star is not a page saying required"
    assert said_yes.required is True, "a page said so and no star was needed"


def test_a_recording_that_said_nothing_falls_back_to_the_label() -> None:
    """Every parameter learnt before the recorder captured this has `said`
    None, and the evidence already in the store has to go on answering."""
    older = LearnedParameter(name="x", seen=("a", "b"), names=("Customer Type*",))

    assert older.said is None
    assert older.required is True
