"""A skill says what it does, because that is how it will be found."""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.parameter import ParameterKind
from sro.domain.skill.template import Template
from tests import factories as f

ADJUST = f.network_plan(
    method="PUT",
    url=Template("https://wms.test/data/WM/wm/inventory/adjust?siteId=SG"),
    body=Template('{"quantity": "${quantity}"}'),
)


async def test_a_version_cannot_be_left_undescribed() -> None:
    version = f.skill_version()

    with pytest.raises(InvariantViolation):
        version.describe(summary="   ", when_to_use="anything")


async def test_rewording_changes_what_finds_it_and_nothing_else() -> None:
    version = f.skill_version()
    before = version.steps

    version.describe(summary="Cycle count correction", when_to_use="After a physical count")

    assert version.summary == "Cycle count correction"
    assert version.steps is before
    assert version.parameters[0].kind is ParameterKind.INPUT
