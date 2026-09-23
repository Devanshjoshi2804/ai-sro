from __future__ import annotations

from sro.domain.recording.element import ElementFingerprint
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.template import Template

_GENERATED_ID = ("ext-gen", "ext-element", "ext-comp")


def build_locators(
    target: ElementFingerprint | None,
    other: ElementFingerprint | None = None,
    *,
    value_placeholder: str | None = None,
) -> tuple[ControlLocator, ...]:
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
    if other is None or observed == other:
        return observed
    return value_placeholder


def _name_of(fingerprint: ElementFingerprint | None) -> str | None:
    return fingerprint.accessible_name if fingerprint else None


def _is_generated(query: str) -> bool:
    return any(marker in query for marker in _GENERATED_ID)
