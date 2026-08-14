"""Which signals are worth replaying by, decided from two runs rather than one.

Every case here is drawn from what this WMS actually produced: ids assigned in
render order, no accessible role, and a grid cell whose text is the record being
worked on rather than the name of a control.
"""

from __future__ import annotations

from sro.application.induction.locators import build_locators
from sro.domain.recording.element import ComponentIdentity, ElementFingerprint
from sro.domain.skill.locator import LocatorStrategy

COMPONENT = ComponentIdentity(
    framework="extjs",
    query="rpFilterableViews rpFilterComboBox#filterComboBox",
    xtype="rpFilterComboBox",
    item_id="filterComboBox",
)


def test_the_component_query_outranks_the_dom_path() -> None:
    target = ElementFingerprint(
        css_path="td#ext-gen5673 > div.x-grid-cell-inner",
        component=COMPONENT,
        role="textbox",
        accessible_name="Quantity*",
    )

    strategies = [locator.strategy for locator in build_locators(target)]

    assert strategies[0] is LocatorStrategy.COMPONENT
    assert LocatorStrategy.CSS_PATH not in strategies, "ext-gen ids are render order, not identity"


def test_text_that_differs_between_runs_becomes_the_parameter() -> None:
    """The demonstrator clicked the row for the LPN they were adjusting. That
    text names the record, so replaying run one's would work on the wrong one."""
    run_a = ElementFingerprint(text="00000776442003824546", css_path="div.x-grid-cell")
    run_b = ElementFingerprint(text="00000776442003821590", css_path="div.x-grid-cell")

    locators = build_locators(run_a, run_b, value_placeholder="${input_value}")
    text = next(loc for loc in locators if loc.strategy is LocatorStrategy.TEXT)

    assert text.query.raw == "${input_value}"
    assert text.placeholders == {"input_value"}


def test_text_that_differs_and_was_never_parameterised_is_dropped() -> None:
    run_a = ElementFingerprint(text="Adjusted 08:14", css_path="div.x-status")
    run_b = ElementFingerprint(text="Adjusted 09:02", css_path="div.x-status")

    locators = build_locators(run_a, run_b)

    assert all(loc.strategy is not LocatorStrategy.TEXT for loc in locators), (
        "pinning run one's timestamp would look like a locator and behave like a bug"
    )


def test_a_step_with_nothing_stable_produces_no_locators() -> None:
    assert build_locators(ElementFingerprint(css_path="div#ext-gen4443")) == ()
