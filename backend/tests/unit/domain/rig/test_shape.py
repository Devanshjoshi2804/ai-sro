import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from sro.application.capture.rig_wire import Gesture as WireGesture
from sro.application.observation.correlate import as_action
from sro.domain.observation.gesture import Gesture, Target
from sro.domain.observation.identity import containment, jaccard, shape_key, target_identity
from sro.domain.skill.shape import where_steps_moved
from sro.domain.skill.workflow import Step
from tests.unit.domain.rig.conftest import gestures as _gestures


def test_an_extjs_control_is_named_by_its_item_id() -> None:
    typed = next(g for g in _gestures() if g.action.kind == "type" and not g.action.secret)

    assert target_identity(typed) == "clientCode"


def test_a_plain_control_falls_back_to_its_name() -> None:
    """The fixture's select carries a name and no role, so it keys by name.
    Asserted exactly: `== "role|Dock" or "Dock" in identity` passes on either
    outcome and so distinguishes neither."""
    select = next(g for g in _gestures() if g.action.kind == "select")

    assert target_identity(select) == "name|Dock"


# -- an accessible name is free text off the page, not an identifier ----------
#
# Measured on the deployment, 2026-09-15. An operator read the mail telling them
# what to create, clicked in it, and went and created it: the first real
# cross-system job this system ever mined. Chrome's accessible name for that div
# is the whole instruction, and it went into the shape whole --
#
#     name|a customer type :- GGD\ndescription :- leaning new SRO type 01
#
# -- which is two defects at once. A shape keyed on the words of ONE mail cannot
# match the next one, so the job could never be recognised again however many
# times it was done. And `shape.py` opens by promising that nothing in a shape
# carries a typed value, while `/v1/shapes` served an operator's own mail to
# every browser in the tenant.
#
# The rule already existed and already said why -- `_names_a_control`, no
# newline and at most forty characters -- and was applied to `innerText` alone.


def _clicked(
    *,
    name: str | None = None,
    role: str | None = None,
    text: str | None = None,
    test_id: str | None = None,
) -> Gesture:
    """A click on something with no developer-assigned identity on it: no
    component, which is how every ordinary web page arrives."""
    one = copy.deepcopy(_gestures()[0])
    one.action = replace(
        one.action,
        kind="click",
        target=Target(tag="div", name=name, role=role, text=text, test_id=test_id),
    )
    return one


MAIL = "a customer type :- GGD\ndescription :- leaning new SRO type 01"


def test_the_words_of_one_mail_are_not_what_a_control_is_called() -> None:
    assert target_identity(_clicked(name=MAIL)) == "anon|click"


def test_a_role_does_not_rescue_a_paragraph() -> None:
    """`role|<paragraph>` is as unmatchable as `name|<paragraph>`, and carries
    the same words to the same browsers."""
    assert target_identity(_clicked(name=MAIL, role="textbox")) == "anon|click"


def test_a_long_single_line_name_is_a_sentence_too() -> None:
    """Forty characters, the same forty the innerText rule uses. A control is
    called `Save`; forty-one characters of prose is what a page says, not what
    a control is named."""
    assert target_identity(_clicked(name="x" * 40)) == "name|" + "x" * 40
    assert target_identity(_clicked(name="x" * 41)) == "anon|click"


def test_a_real_control_name_still_names_it() -> None:
    """The whole value of this branch. `name` is the best identity a plain page
    offers, and the guard is only meant to refuse the ones that are not names."""
    assert target_identity(_clicked(name="Save")) == "name|Save"
    assert (
        target_identity(_clicked(name="Customer Type", role="textbox")) == "textbox|Customer Type"
    )


def test_what_is_left_when_the_name_is_a_paragraph_is_still_tried() -> None:
    """Refusing the name falls THROUGH to what is left rather than giving up:
    a `data-testid` is a developer-assigned identifier and is exactly what this
    case wants."""
    assert target_identity(_clicked(name=MAIL, test_id="compose-body")) == "test|compose-body"


def test_a_paragraph_is_refused_by_both_doors() -> None:
    """The mail arrives as `name` AND as `text` -- Chrome computes the same
    string for both -- so guarding one and not the other would have changed
    nothing at all on the gesture that found this."""
    assert target_identity(_clicked(name=MAIL, text=MAIL)) == "anon|click"


def test_a_scroll_has_no_target_and_is_named_anyway() -> None:
    """A scroll carries no target at all. It must still key.

    The committed fixture holds no scroll, so one is built rather than skipped:
    a test that skips is a test that does not run, and twelve of the eighty-one
    real acme gestures are scrolls."""
    scroll = copy.deepcopy(_gestures()[0])
    scroll.action = replace(scroll.action, kind="scroll", target=None)

    assert target_identity(scroll) == "anon|scroll"


def test_the_key_never_uses_a_css_path_or_an_xpath() -> None:
    """Both encode document position and change when the page is restyled.
    A key built on them is the brittleness this replaces."""
    keys = [target_identity(g) for g in _gestures()]

    assert not any("nth-of-type" in k or k.startswith("/html") for k in keys)

    # The fixture's own cssPaths are plain -- `input#client`, `select#dock` --
    # so the line above proves only the xpath half: a cssPath fallback passes
    # it. Build the positional shapes the fixture lacks, the way the scroll
    # test builds the scroll it lacks.
    positioned = copy.deepcopy(_gestures()[0])
    positioned.action = replace(
        positioned.action,
        target=Target(
            css_path="div:nth-of-type(2) > input#foo",
            xpath="/html/body/div[2]/input",
        ),
    )

    assert target_identity(positioned) == "anon|type"


def test_the_key_is_the_same_for_the_same_doing_twice() -> None:
    """Two doings of one job cite entirely disjoint gesture ids, which is the
    whole reason this key exists -- so it must survive new ids, a later day and
    a different order of calls. Comparing a list against a copy of the same
    list proves none of that."""
    first = _gestures()
    again = copy.deepcopy(first)
    for n, gesture in enumerate(again):
        gesture.id = f"ges_again_{n}"
        gesture.at = gesture.at + 86_400.0
        gesture.requests.reverse()

    assert {g.id for g in again}.isdisjoint({g.id for g in first})
    assert shape_key(again) == shape_key(first)


def test_containment_sees_a_small_job_inside_a_big_one() -> None:
    """Jaccard would call these different; a three-step job really does sit
    inside the twelve-step job that contains it."""
    small = {("a", "x", "click"), ("a", "y", "type")}
    big = small | {("b", f"z{n}", "click") for n in range(10)}

    assert containment(small, big) == 1.0
    assert jaccard(small, big) < 0.25


def test_containment_of_disjoint_sets_is_zero() -> None:
    assert containment({("a", "x", "click")}, {("b", "y", "type")}) == 0.0


def test_containment_of_empty_sets_does_not_divide_by_zero() -> None:
    assert containment(set(), set()) == 0.0
    assert containment({("a", "x", "click")}, set()) == 0.0


FIXTURE = Path(__file__).resolve().parents[5] / "new-chrome-extension/fixtures/shape-identity.json"


def test_the_python_identity_agrees_with_the_shared_fixture() -> None:
    """The rule lives twice -- here and in the extension's generated twin --
    so it is held to one fixture rather than to two readings of one sentence."""
    if not FIXTURE.is_file():
        # mutmut copies this package into `backend/mutants/` and runs there;
        # the fixture sits beside the extension, outside the copy. The JS
        # half of this contract runs in `make test-extension` either way.
        pytest.skip("the shared identity fixture is not in this checkout")
    for case in json.loads(FIXTURE.read_text()):
        wire = WireGesture.model_validate(
            {"kind": case["kind"], "target": case["target"], "at": 0.0, "value": None}
        )
        gesture = Gesture(
            id="g",
            tenant="t",
            stream_id="s",
            batch_id="b",
            at=0.0,
            url=None,
            system=None,
            tab_id=None,
            frame_url=None,
            action=as_action(wire),
        )
        assert target_identity(gesture) == case["identity"], case["name"]


# -- a job that grows keeps its learning ---------------------------------------
#
# A stored job's steps never grew, and that is half of why a field two doings
# varied could not become a parameter: `parameters_across` compares the stored
# job with the proposal, and the stored job is one doing that never reached the
# control. Measured on the deployment 2026-09-21 -- an operator filled
# `Department` and `Manufacturer` in two doings, with different values both
# times, and the job went on holding two parameters.


def _step(order: int, cites: list[str]) -> Step:
    return Step(order=order, says=f"step {order}", system=None, cites=cites)


def test_a_step_that_moves_takes_its_number_with_it() -> None:
    """What the growth is for: the locator a run last found, the mark that a
    step is about to break and what the job taught itself are all keyed on the
    step's number, and a step that becomes step 3 takes them along or they now
    describe somebody else's step."""
    day = {one.id: one for one in _gestures()}
    ids = [one.id for one in sorted(day.values(), key=lambda g: g.at)]
    was = [_step(0, [ids[0]]), _step(1, [ids[2]])]
    # The same two things done, with one more done in between them.
    now = [_step(0, [ids[0]]), _step(1, [ids[1]]), _step(2, [ids[2]])]

    assert where_steps_moved(was, now, day) == {0: 0, 1: 2}


def test_a_step_the_new_doing_does_not_have_is_left_behind() -> None:
    """Its learning goes with it. A locator for a step nobody performs is a
    locator nobody can check."""
    day = {one.id: one for one in _gestures()}
    ids = [one.id for one in sorted(day.values(), key=lambda g: g.at)]

    moved = where_steps_moved([_step(0, [ids[0]]), _step(1, [ids[1]])], [_step(0, [ids[0]])], day)

    assert moved == {0: 0}


def test_a_job_that_does_one_thing_twice_keeps_both() -> None:
    """Matched first-unclaimed rather than by value, so two steps that did the
    same thing do not fold onto one."""
    day = {one.id: one for one in _gestures()}
    ids = [one.id for one in sorted(day.values(), key=lambda g: g.at)]
    twice = [_step(0, [ids[0]]), _step(1, [ids[0]])]
    now = [_step(0, [ids[0]]), _step(1, [ids[1]]), _step(2, [ids[0]])]

    assert where_steps_moved(twice, now, day) == {0: 0, 1: 2}


def test_steps_are_matched_by_what_they_did_and_not_by_what_they_are_called() -> None:
    """The prose is written freshly every mining and a step index is the
    model's opinion. Two steps are the same step when their cited gestures
    have the same shape."""
    day = {one.id: one for one in _gestures()}
    ids = [one.id for one in sorted(day.values(), key=lambda g: g.at)]
    was = [Step(order=0, says="type the client code", system=None, cites=[ids[0]])]
    now = [Step(order=0, says="enter a code for the client", system=None, cites=[ids[0]])]

    assert where_steps_moved(was, now, day) == {0: 0}
