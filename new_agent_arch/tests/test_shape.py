import copy
import json
from pathlib import Path

import pytest

from rig.correlate import correlate
from rig.records import Gesture
from rig.shape import containment, jaccard, shape_key, target_identity
from rig.wire import Batch, Target
from rig.wire import Gesture as WireGesture
from tests.fixtures import BATCH


def _gestures():
    gestures, _, _, _ = correlate(Batch.model_validate(BATCH), "acme")
    return gestures


def test_an_extjs_control_is_named_by_its_item_id() -> None:
    typed = next(g for g in _gestures() if g.gesture.kind == "type" and not g.gesture.secret)

    assert target_identity(typed) == "clientCode"


def test_a_plain_control_falls_back_to_its_name() -> None:
    """The fixture's select carries a name and no role, so it keys by name.
    Asserted exactly: `== "role|Dock" or "Dock" in identity` passes on either
    outcome and so distinguishes neither."""
    select = next(g for g in _gestures() if g.gesture.kind == "select")

    assert target_identity(select) == "name|Dock"


def test_a_scroll_has_no_target_and_is_named_anyway() -> None:
    """A scroll carries no target at all. It must still key.

    The committed fixture holds no scroll, so one is built rather than skipped:
    a test that skips is a test that does not run, and twelve of the eighty-one
    real acme gestures are scrolls."""
    scroll = copy.deepcopy(_gestures()[0])
    scroll.gesture.kind = "scroll"
    scroll.gesture.target = None

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
    positioned.gesture.target = Target(
        cssPath="div:nth-of-type(2) > input#foo",
        xpath="/html/body/div[2]/input",
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


FIXTURE = Path(__file__).resolve().parents[2] / "new-chrome-extension/fixtures/shape-identity.json"


def test_the_python_identity_agrees_with_the_shared_fixture() -> None:
    """The rule lives twice -- here and in the extension's generated twin --
    so it is held to one fixture rather than to two readings of one sentence."""
    if not FIXTURE.is_file():
        # mutmut copies this package into `mutants/` and runs there; the
        # fixture sits beside the extension, two directories up, and is not
        # in the copy. The JS half of this contract runs in `make
        # test-extension` either way.
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
            gesture=wire,
        )
        assert target_identity(gesture) == case["identity"], case["name"]
