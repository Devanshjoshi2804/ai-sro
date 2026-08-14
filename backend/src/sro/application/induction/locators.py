"""Which of a fingerprint's signals are worth replaying by, in what order.

The fingerprint records everything about a control at one moment. Most of it is
worthless tomorrow: an ExtJS DOM id is assigned in render order, bounds move
with the window, and a grid cell's text is the record being worked on rather
than the control's name. What survives is the component the application itself
addresses, a test id where a team put one, an accessible role and name where the
framework emits them, and stable visible text.

Two runs are available here, which is what makes this more than a guess: a
signal that differs between the runs is a property of the record, not of the
control, so it becomes a parameter rather than a literal or is dropped.
"""

from __future__ import annotations

from sro.domain.recording.element import ElementFingerprint
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.template import Template

_GENERATED_ID = ("ext-gen", "ext-element", "ext-comp")
"""Id prefixes a framework hands out in render order. Never worth recording."""


def build_locators(
    target: ElementFingerprint | None,
    other: ElementFingerprint | None = None,
    *,
    value_placeholder: str | None = None,
) -> tuple[ControlLocator, ...]:
    """Locators for one control, strongest first.

    ``other`` is the same step's target from the second demonstration. Where a
    signal differs between the two it is describing the record rather than the
    control: ``value_placeholder`` -- the parameter the diff already created for
    that step's value -- is used in its place if it matches, and otherwise the
    signal is dropped rather than pinned to run one's data.
    """
    if target is None:
        return ()

    locators: list[ControlLocator] = []
    component = target.component

    if component is not None and not _is_generated(component.query):
        locators.append(
            ControlLocator(strategy=LocatorStrategy.COMPONENT, query=Template(component.query))
        )

    if target.test_id:
        locators.append(
            ControlLocator(strategy=LocatorStrategy.TEST_ID, query=Template(target.test_id))
        )

    if target.role and target.accessible_name:
        name = _stable(target.accessible_name, _name_of(other), value_placeholder)
        if name is not None:
            locators.append(
                ControlLocator(
                    strategy=LocatorStrategy.ROLE_AND_NAME,
                    query=Template(f"{target.role}|{name}"),
                )
            )

    if target.text:
        text = _stable(target.text, other.text if other else None, value_placeholder)
        if text is not None:
            locators.append(ControlLocator(strategy=LocatorStrategy.TEXT, query=Template(text)))

    if target.css_path and not _is_generated(target.css_path):
        locators.append(
            ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template(target.css_path))
        )

    return tuple(locators)


def _stable(observed: str, other: str | None, value_placeholder: str | None) -> str | None:
    """The value to record for a signal, or ``None`` to drop it.

    Identical across both runs means it belongs to the control. Different means
    it belongs to the record: usable only if the diff already named that value,
    in which case the locator carries the parameter and finds the right row for
    whatever the run is about.
    """
    if other is None or observed == other:
        return observed
    return value_placeholder


def _name_of(fingerprint: ElementFingerprint | None) -> str | None:
    return fingerprint.accessible_name if fingerprint else None


def _is_generated(query: str) -> bool:
    return any(marker in query for marker in _GENERATED_ID)
