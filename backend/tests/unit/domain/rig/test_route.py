"""Where a step leaves the browser, when leaving it somewhere is all it does."""

from __future__ import annotations

from dataclasses import replace

from sro.domain.execution.evidence import route_for
from sro.domain.observation.gesture import Gesture
from sro.domain.skill.workflow import Step
from tests.unit.domain.rig.conftest import gestures as _gestures

WAREHOUSE = "https://wms.example/portal?siteId=SG#wm.config/wm.config.warehouse.warehouse////"
CUSTOMERS = "https://wms.example/portal?siteId=SG#wm.config/wm.config.partners.customers.types////"


def _clicked(gesture_id: str, page: str) -> Gesture:
    """A click the operator made on that page."""
    one = next(g for g in _gestures() if g.action.kind == "click")
    one = replace(one, id=gesture_id, url=page, page_url=page)
    one.action = replace(one.action, value=None)
    return one


def _typed(gesture_id: str, page: str) -> Gesture:
    one = next(g for g in _gestures() if g.action.kind == "type")
    one = replace(one, id=gesture_id, url=page, page_url=page)
    return one


def _step(order: int, cites: list[str]) -> Step:
    return Step(order=order, says="s", system=None, cites=cites)


def test_the_destination_is_where_the_next_step_happened() -> None:
    """A gesture records the page it happened ON, never the page it led to. The
    click that opens the Customer Types screen is recorded on the Warehouse
    screen -- read as a destination it sends the browser back where it began,
    which is what the first version of this did.

    One step along, the answer is there: the next step was performed somewhere,
    and that somewhere is where this one arrived.
    """
    by_id = {"a": _clicked("a", WAREHOUSE), "b": _clicked("b", CUSTOMERS)}

    assert route_for(_step(0, ["a"]), _step(1, ["b"]), by_id) == CUSTOMERS


def test_a_step_that_types_is_not_a_step_that_arrives() -> None:
    """ "Does not write" is not "only arrives": the step that types a customer
    type into a field writes nothing and is emphatically not a navigation. The
    suite said so the first time this was tried -- a run navigated instead of
    filling in the form."""
    by_id = {"a": _typed("a", WAREHOUSE), "b": _clicked("b", CUSTOMERS)}

    assert route_for(_step(0, ["a"]), _step(1, ["b"]), by_id) is None


def test_a_step_that_moved_nothing_is_not_navigated_to() -> None:
    """The next step is on the same page, so this step did not move the browser
    and a navigate would be a command that changes nothing."""
    by_id = {"a": _clicked("a", CUSTOMERS), "b": _clicked("b", CUSTOMERS)}

    assert route_for(_step(0, ["a"]), _step(1, ["b"]), by_id) is None


def test_the_last_step_has_nowhere_recorded_to_arrive() -> None:
    by_id = {"a": _clicked("a", WAREHOUSE)}

    assert route_for(_step(0, ["a"]), None, by_id) is None


def test_a_step_with_no_evidence_names_no_route() -> None:
    assert route_for(_step(0, []), _step(1, []), {}) is None


def test_two_screens_of_one_application_are_not_the_same_page() -> None:
    """`page_of` drops the fragment, and this application keeps its routes
    there -- so every screen compared equal to every other, and a rule built on
    it would report arriving somewhere it never went."""
    from sro.domain.shared.hosts import page_of, same_screen

    assert page_of(WAREHOUSE) == page_of(CUSTOMERS), "the trap this exists for"
    assert not same_screen(WAREHOUSE, CUSTOMERS)
    assert same_screen(CUSTOMERS, CUSTOMERS.replace("siteId=SG", "siteId=SG&_dc=17894"))
    assert not same_screen(CUSTOMERS, None)
